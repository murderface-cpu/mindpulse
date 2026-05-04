"""
database.py – PostgreSQL connection pool + schema bootstrap
"""
import os
import logging
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set in .env")
        _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=dsn)
        logger.info("PostgreSQL connection pool created.")
    return _pool


def get_conn():
    return get_pool().getconn()


def release_conn(conn):
    get_pool().putconn(conn)


# ── Schema bootstrap ───────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_insights (
    id          SERIAL PRIMARY KEY,
    topic       TEXT        NOT NULL,
    category    TEXT        NOT NULL,
    summary     TEXT        NOT NULL,
    full_content TEXT       NOT NULL,
    model       TEXT        NOT NULL,
    tokens_used INTEGER     DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_logs (
    id          SERIAL PRIMARY KEY,
    level       TEXT        NOT NULL,  -- INFO | WARNING | ERROR
    event       TEXT        NOT NULL,
    message     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheduler_runs (
    id              SERIAL PRIMARY KEY,
    run_at          TIMESTAMPTZ DEFAULT NOW(),
    entries_created INTEGER     DEFAULT 0,
    status          TEXT        NOT NULL,  -- success | partial | failed
    duration_ms     INTEGER     DEFAULT 0
);
"""


def bootstrap_schema():
    """Create tables if they don't exist yet."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
        logger.info("Database schema bootstrapped successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Schema bootstrap failed: {e}")
        raise
    finally:
        release_conn(conn)


# ── Helper queries ─────────────────────────────────────────────────────────────

def insert_insight(topic: str, category: str, summary: str,
                   full_content: str, model: str, tokens_used: int) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ai_insights
                   (topic, category, summary, full_content, model, tokens_used)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (topic, category, summary, full_content, model, tokens_used)
            )
            row_id = cur.fetchone()[0]
        conn.commit()
        return row_id
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)


def log_event(level: str, event: str, message: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO system_logs (level, event, message) VALUES (%s, %s, %s)",
                (level, event, message)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Could not write system log: {e}")
    finally:
        release_conn(conn)


def record_run(entries_created: int, status: str, duration_ms: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO scheduler_runs (entries_created, status, duration_ms)
                   VALUES (%s, %s, %s)""",
                (entries_created, status, duration_ms)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Could not record scheduler run: {e}")
    finally:
        release_conn(conn)


def fetch_insights(limit: int = 50, offset: int = 0, category: str | None = None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    """SELECT id, topic, category, summary, full_content, model, tokens_used, created_at
                       FROM ai_insights WHERE category = %s
                       ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (category, limit, offset)
                )
            else:
                cur.execute(
                    """SELECT id, topic, category, summary, full_content, model, tokens_used, created_at
                       FROM ai_insights ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    (limit, offset)
                )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)


def fetch_insight_detail(insight_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ai_insights WHERE id = %s", (insight_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None
    finally:
        release_conn(conn)


def fetch_stats():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ai_insights")
            total_insights = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM scheduler_runs")
            total_runs = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM scheduler_runs WHERE status = 'success'"
            )
            successful_runs = cur.fetchone()[0]

            cur.execute(
                "SELECT category, COUNT(*) as cnt FROM ai_insights GROUP BY category ORDER BY cnt DESC"
            )
            categories = [{"category": r[0], "count": r[1]} for r in cur.fetchall()]

            cur.execute(
                "SELECT SUM(tokens_used) FROM ai_insights"
            )
            total_tokens = cur.fetchone()[0] or 0

            cur.execute(
                "SELECT run_at, entries_created, status, duration_ms FROM scheduler_runs ORDER BY run_at DESC LIMIT 10"
            )
            recent_runs = [
                {"run_at": r[0], "entries_created": r[1], "status": r[2], "duration_ms": r[3]}
                for r in cur.fetchall()
            ]

        return {
            "total_insights": total_insights,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "categories": categories,
            "total_tokens": total_tokens,
            "recent_runs": recent_runs,
        }
    finally:
        release_conn(conn)


def fetch_logs(limit: int = 100):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT level, event, message, created_at FROM system_logs ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        release_conn(conn)
