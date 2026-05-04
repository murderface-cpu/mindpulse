"""
ai_engine.py – Groq-powered content generation engine
"""
import os
import json
import random
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Groq client ────────────────────────────────────────────────────────────────
def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError("GROQ_API_KEY is not configured. Check your .env file.")
    return Groq(api_key=api_key)


MODEL = "llama-3.1-8b-instant"   # fast, free-tier friendly

# ── Topic bank – the AI cycles through these ───────────────────────────────────
TOPICS = {
    "Technology": [
        "Artificial Intelligence trends", "Quantum computing breakthroughs",
        "Edge computing and IoT", "Cybersecurity best practices",
        "Blockchain applications", "5G network impact", "Open-source software",
        "Cloud-native architectures", "WebAssembly future", "Low-code platforms",
    ],
    "Science": [
        "Climate change research", "Space exploration missions",
        "Gene editing with CRISPR", "Neuroscience discoveries",
        "Renewable energy innovations", "Ocean biodiversity",
        "Particle physics experiments", "Vaccine development",
        "Nanotechnology applications", "Earthquake prediction methods",
    ],
    "Business": [
        "Remote work productivity", "Supply chain resilience",
        "Startup funding strategies", "ESG investing",
        "Digital transformation", "Consumer behaviour shifts",
        "Circular economy models", "Gig economy trends",
        "Corporate AI adoption", "Global trade dynamics",
    ],
    "Health": [
        "Mental health awareness", "Personalised medicine",
        "Nutrition and gut microbiome", "Wearable health tech",
        "Telemedicine growth", "Sleep science",
        "Exercise and longevity", "Air quality and health",
        "Digital therapeutics", "Ageing population challenges",
    ],
    "Society": [
        "Digital privacy rights", "Misinformation and media literacy",
        "Urban planning and smart cities", "Education technology",
        "Social media mental health effects", "Accessibility and inclusion",
        "Future of work", "Cultural heritage preservation",
        "Food security", "Water scarcity solutions",
    ],
}

ALL_CATEGORIES = list(TOPICS.keys())


def pick_topic() -> tuple[str, str]:
    """Return a random (category, topic) pair."""
    category = random.choice(ALL_CATEGORIES)
    topic = random.choice(TOPICS[category])
    return category, topic


SYSTEM_PROMPT = """You are an expert knowledge curator. When given a topic, you produce a 
structured, factual, and insightful article entry. Respond ONLY with valid JSON in exactly 
this shape (no markdown fences, no extra keys):

{
  "topic": "<exact topic string>",
  "summary": "<1-2 sentence plain-English summary>",
  "full_content": "<well-structured 3-5 paragraph article with real facts, trends, and takeaways>",
  "key_points": ["point 1", "point 2", "point 3"]
}"""


def generate_insight(topic: str, category: str) -> dict:
    """
    Call Groq to generate a knowledge entry for the given topic.
    Returns a dict with keys: summary, full_content, key_points, tokens_used, model
    """
    client = get_client()

    user_prompt = (
        f"Write a knowledge entry about: **{topic}** (Category: {category}). "
        "Be informative, accurate, and concise. Use current knowledge."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens if response.usage else 0

    # Strip markdown fences if the model wrapped them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Groq returned non-JSON; wrapping raw text.")
        data = {
            "topic": topic,
            "summary": raw[:200],
            "full_content": raw,
            "key_points": [],
        }

    return {
        "summary": data.get("summary", ""),
        "full_content": data.get("full_content", ""),
        "key_points": data.get("key_points", []),
        "tokens_used": tokens_used,
        "model": MODEL,
    }


def generate_batch(n: int = 3) -> list[dict]:
    """Generate n distinct insights and return them as a list of row-ready dicts."""
    results = []
    seen_topics: set[str] = set()

    attempts = 0
    while len(results) < n and attempts < n * 3:
        attempts += 1
        category, topic = pick_topic()
        if topic in seen_topics:
            continue
        seen_topics.add(topic)

        try:
            insight = generate_insight(topic, category)
            insight["topic"] = topic
            insight["category"] = category
            results.append(insight)
            logger.info(f"Generated insight: [{category}] {topic}")
        except Exception as e:
            logger.error(f"Failed to generate insight for '{topic}': {e}")

    return results
