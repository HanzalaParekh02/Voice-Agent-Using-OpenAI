# 🎙️ Voice Intelligent Platform — Backend (PoC)

FastAPI backend for an AI Voice Agent supporting niche prompts, agent configuration,
voice interaction, transcription, summary, and sentiment analysis.

---

## 📁 Folder Structure

```
voice-agent-backend/
│
├── main.py                  # FastAPI app, CORS, middleware, router registration
├── config.py                # Env variable loader (OPENAI_API_KEY etc.)
├── requirements.txt
├── .env.example             # Copy to .env and add your key
│
├── routes/
│   ├── niches.py            # GET /niches, GET /niches/{name}
│   ├── agent.py             # POST /agent/configure, POST /agent/talk
│   ├── transcription.py     # POST /transcribe
│   └── analysis.py          # POST /analyze
│
├── services/
│   ├── ai_service.py        # OpenAI wrapper + mock fallback + in-memory config
│   └── niche_data.py        # Niche prompt template definitions
│
└── schemas/
    └── models.py            # All Pydantic request/response models
```

---

## ⚡ Quick Start

```bash
# 1. Clone / unzip the project
cd voice-agent-backend

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment
cp .env.example .env
# Edit .env and paste your OpenAI API key

# 5. Run the server
uvicorn main:app --reload
```

Interactive docs → http://localhost:8000/docs

---

## 🔑 Environment Variables

| Variable         | Required | Description                        |
|------------------|----------|------------------------------------|
| `OPENAI_API_KEY` | Yes*     | Your OpenAI API key                |
| `APP_ENV`        | No       | `development` (default)            |
| `APP_VERSION`    | No       | `1.0.0` (default)                  |

> *If missing, all AI features fall back to **mock responses** so the PoC still runs.

---

## 📡 API Reference & Example Requests

### GET / — Health Check
```http
GET http://localhost:8000/
```
```json
{ "message": "AI Voice Agent Backend Running", "version": "1.0.0", "docs": "/docs" }
```

---

### GET /niches — List Niches
```http
GET http://localhost:8000/niches
```
```json
{ "niches": ["healthcare", "finance", "sales", "booking"] }
```

---

### GET /niches/{niche_name} — Get Prompt Template
```http
GET http://localhost:8000/niches/sales
```
```json
{
  "niche": "sales",
  "prompt_template": "You are a persuasive, friendly, and results-driven sales voice agent..."
}
```

---

### POST /agent/configure — Configure Agent
```http
POST http://localhost:8000/agent/configure
Content-Type: application/json

{
  "dialect": "US",
  "language": "English",
  "gender": "Male",
  "prompt": "You are a professional sales agent. Focus on value and empathy."
}
```
```json
{
  "status": "success",
  "message": "Agent configured successfully. Ready to accept voice interactions.",
  "config": { "dialect": "US", "language": "English", "gender": "Male", "prompt": "..." }
}
```

---

### POST /agent/talk — Voice Interaction
```http
POST http://localhost:8000/agent/talk
Content-Type: application/json

{
  "audio_input": "Hello, I am interested in your premium plan pricing.",
  "enable_summary": true,
  "enable_sentiment": true
}
```
```json
{
  "transcript": "Hello, I am interested in your premium plan pricing.",
  "agent_response_text": "Great question! Our premium plan starts at $49/month and includes...",
  "summary": "The customer enquired about premium plan pricing. The agent provided details.",
  "sentiment": "Positive"
}
```

> **Tip:** `audio_input` accepts plain text (mock) OR a base64-encoded audio blob.

---

### POST /transcribe — Transcribe Audio File
```http
POST http://localhost:8000/transcribe
Content-Type: multipart/form-data

file=@/path/to/recording.webm
```
```json
{
  "transcript": "I would like to book an appointment for next Tuesday.",
  "source": "openai_whisper"
}
```

---

### POST /analyze — Summary & Sentiment
```http
POST http://localhost:8000/analyze
Content-Type: application/json

{
  "transcript": "The customer called to ask about refund policies. They were frustrated but calmed down after the agent explained the 30-day return window.",
  "summary_enabled": true,
  "sentiment_enabled": true
}
```
```json
{
  "summary": "The customer enquired about the refund policy and was reassured by the agent about the 30-day return window.",
  "sentiment": "Neutral"
}
```

Disable one toggle:
```json
{ "transcript": "...", "summary_enabled": false, "sentiment_enabled": true }
// → { "summary": null, "sentiment": "Positive" }
```

---

## 🔌 Swapping to Real AI (Production Checklist)

- [ ] Set `OPENAI_API_KEY` in `.env`
- [ ] In `services/ai_service.py` change model from `gpt-4o-mini` → `gpt-4o` if needed
- [ ] Replace in-memory config store with Redis or a database
- [ ] Tighten CORS origins in `main.py`
- [ ] Adjust rate limits in `main.py` (`"60/minute"` → your production limits)
- [ ] Add auth (API key header or OAuth) to sensitive endpoints

---

## 🛡️ Rate Limiting

Default: **60 requests / minute / IP** via [slowapi](https://github.com/laurentS/slowapi).
Change the limit string in `main.py`:
```python
Limiter(key_func=get_remote_address, default_limits=["100/minute"])
```


