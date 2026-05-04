# MindPulse - AI-Powered Knowledge Blog

MindPulse is a modern blog platform that uses **Groq AI** to generate curated articles on Technology, Science, Business, Health, and Society. All content is automatically populated into a **PostgreSQL (Neon)** database on a configurable schedule.

---

## ✨ Features

| Feature | Description |
|---|---|
| **AI Content Generation** | Uses `llama-3.1-8b-instant` via Groq API to create rich, structured blog articles |
| **5 Topic Categories** | Technology, Science, Business, Health, and Society |
| **Automated Publishing** | APScheduler runs every N seconds (configurable) to publish new articles |
| **Modern Blog UI** | Clean, readable design with hero section, category filters, and article cards |
| **REST API** | Full JSON API for programmatic access |
| **Category Browsing** | Filter articles by category at `/insights?category=Technology` |
| **About Page** | Learn more about the platform |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- A free [Groq API key](https://console.groq.com/keys)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and fill in:
```env
GROQ_API_KEY=***
DATABASE_URL=postgresql://neondb_owner:***@host/neondb?sslmode=require&channel_binding=require
POPULATE_INTERVAL_SECONDS=300   # every 5 minutes
ENTRIES_PER_RUN=3               # 3 articles per run
```

### 4. Run the server
```bash
python app.py
```

Open **http://localhost:8000** — your MindPulse blog is now live!

---

## 📁 Project Structure

```
ai-system/
├── app.py          # FastAPI web server + routes
├── database.py     # PostgreSQL pool + schema + queries
├── ai_engine.py    # Groq AI content generation
├── scheduler.py    # APScheduler periodic job
├── templates/
│   ├── index.html  # Blog homepage with hero, featured, and article grid
│   ├── detail.html # Individual article page with related posts
│   └── about.html  # About page with platform stats
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📡 Blog Pages

| Route | Description |
|---|---|
| `/` | Homepage with hero, featured article, and latest posts |
| `/insight/{id}` | Individual article detail page |
| `/insights?category=XYZ` | Browse articles filtered by category |
| `/latest` | Latest 20 articles |
| `/about` | About page with platform statistics |

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `DATABASE_URL` | *(required)* | Neon PostgreSQL connection string |
| `POPULATE_INTERVAL_SECONDS` | `300` | How often (seconds) to generate new articles |
| `ENTRIES_PER_RUN` | `3` | How many articles to create each run |
| `PORT` | `8000` | Web server port |

---

## 🗄️ Database Schema

```sql
ai_insights      -- Generated AI blog articles
system_logs      -- Event log for system actions
scheduler_runs   -- History of scheduled publication runs
```

---

## 🎨 Design

MindPulse features a clean, modern blog design:
- **Hero section** with tagline and value proposition
- **Article cards** with category tags, summaries, and read time
- **Category filters** for easy browsing
- **Sidebar** with trending topics, newsletter signup (demo), and tags
- **Responsive layout** that works on mobile and desktop
- **Typography** using Inter for body text and Playfair Display for headings

---

## 📄 License

MIT