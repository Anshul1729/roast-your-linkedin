# 🔥 Roast Your LinkedIn

**Paste a LinkedIn URL. Get absolutely destroyed.**

A fun side project that takes your (or anyone's) LinkedIn profile and generates a brutally honest, AI-powered roast — complete with voice audio. Because sometimes your "thought leader" headline deserves to be called out.

---

## What it does

1. You drop in a LinkedIn profile URL
2. It scrapes the public profile data
3. Claude AI reads your job titles, summary, and work history — and writes a roast in your chosen style (Savage / Funny / Witty / Mix)
4. ElevenLabs turns that roast into a voiced audio clip you can play back (and share)

The whole flow takes about 10–15 seconds. The emotional damage lasts longer.

---

## Why I built this

LinkedIn is full of people taking themselves very seriously. I wanted to flip that — make something that uses real AI to poke fun at the way we all present ourselves professionally. It's also a good stress test for chaining multiple AI APIs together: scraping → LLM → TTS, all in one clean flow.

---

## Tech stack

| Layer | What's powering it |
|---|---|
| Frontend | React 19, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python) |
| AI Roast | Anthropic Claude (claude-sonnet-4-6) |
| Voice | ElevenLabs TTS |
| LinkedIn data | RapidAPI — Fresh LinkedIn Profile Data |
| Database | MongoDB (profile caching) |

---

## Running it locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB running locally or a connection string

### 1. Clone the repo
```bash
git clone https://github.com/Anshul1729/roast-your-linkedin.git
cd roast-your-linkedin
```

### 2. Backend setup
```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=linkedin_roaster
ANTHROPIC_API_KEY=your_anthropic_key
ELEVENLABS_API_KEY=your_elevenlabs_key
RAPIDAPI_KEY=your_rapidapi_key
```

Start the backend:
```bash
uvicorn server:app --reload --port 8000
```

### 3. Frontend setup
```bash
cd frontend
yarn install
```

Create a `.env` file in the `frontend/` folder:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

Start the frontend:
```bash
yarn start
```

App will be at `http://localhost:3000`.

---

## API keys you'll need

| Service | Where to get it | Cost |
|---|---|---|
| Anthropic | console.anthropic.com | Pay per use |
| ElevenLabs | elevenlabs.io | Free tier available |
| RapidAPI (Fresh LinkedIn Profile Data) | rapidapi.com | Free tier available |

---

## Roast styles

- **Savage** — no mercy, maximum damage
- **Funny** — rapid-fire jokes, comedic destruction
- **Witty** — intellectual burns, surgical precision
- **Mix** — all of the above, chaos mode

---

## Features

- Profile caching (7 days) so you're not burning API credits on the same profile twice
- Audio playback in-browser
- Feedback/rating system
- Loading states with appropriately chaotic messages ("Stalking their profile...", "Adding masala to the roast...")

---

Built with Claude Code + a lot of LinkedIn cringe for inspiration.
