# MedVoice AI

**Bilingual AI Phone Receptionist for Quebec Medical Clinics**

MedVoice AI is an AI-powered voice agent that answers calls in French and English, books appointments directly into Google Calendar, and routes urgent cases to humans.

## Features

- **Bilingual Voice Support**: French-Canadian and English with automatic language detection
- **Appointment Booking**: Book, reschedule, and cancel appointments with real-time calendar sync
- **FAQ Handling**: Hours, location, services, parking, forms, fees
- **Safe Routing**: Urgent symptoms trigger immediate human transfer
- **Admin Dashboard**: Real-time transcripts, call logs, and analytics

## Architecture

```
[Twilio Voice] → [FastAPI WebSocket] → [Deepgram ASR] → [DeepSeek LLM] → [Azure TTS] → [Twilio]
                        ↓
                   [n8n Workflows] → [Google Calendar]
                        ↓
                   [Firestore] ← [React Dashboard]
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python + FastAPI |
| Voice Pipeline | Twilio Media Streams + WebSocket |
| Speech-to-Text | Deepgram Nova-2 |
| Text-to-Speech | Azure Cognitive Services |
| LLM | DeepSeek V3.2 via OpenRouter |
| Workflow Automation | n8n |
| Database | Firebase Firestore |
| Dashboard | React + TypeScript + Tailwind |
| Hosting | Firebase (Cloud Run + Hosting) |

## Project Structure

```
medical_receptionist/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # Entry point
│   ├── config.py               # Environment config
│   ├── voice/                  # Voice pipeline
│   │   ├── twilio_handler.py   # WebSocket handler
│   │   ├── asr_client.py       # Deepgram ASR
│   │   ├── tts_client.py       # Azure TTS
│   │   ├── audio_utils.py      # Audio conversion
│   │   └── conversation.py     # State machine
│   ├── llm/                    # LLM integration
│   │   ├── client.py           # OpenRouter client
│   │   ├── prompts.py          # Bilingual prompts
│   │   └── function_calls.py   # Tool definitions
│   ├── n8n/                    # Workflow integration
│   ├── models/                 # Pydantic models
│   ├── api/                    # REST endpoints
│   └── storage/                # Firestore client
├── dashboard/                  # React admin dashboard
├── n8n/workflows/              # n8n workflow exports
├── Dockerfile
├── docker-compose.yml
└── firebase.json
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional)
- API Keys: Twilio, Deepgram, Azure Speech, OpenRouter

### 1. Clone and Setup

```bash
cd medical_receptionist
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Dashboard
cd ../dashboard
npm install
```

### 3. Run Locally

```bash
# Option A: Docker Compose (recommended)
docker-compose up

# Option B: Manual
# Terminal 1 - Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 - Dashboard
cd dashboard && npm run dev
```

### 4. Configure Twilio

1. Buy a Canadian phone number (+1 514...)
2. Set Voice webhook to: `https://your-domain/twilio/voice`
3. Enable Media Streams

## Environment Variables

```bash
# Required
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
DEEPGRAM_API_KEY=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=canadacentral
OPENROUTER_API_KEY=
FIREBASE_PROJECT_ID=

# Optional
N8N_WEBHOOK_BASE_URL=
REDIS_URL=
```

## Deployment

### Firebase Hosting (Dashboard)

```bash
cd dashboard
npm run build
firebase deploy --only hosting
```

### Cloud Run (Backend)

```bash
gcloud run deploy medvoice-api \
  --source . \
  --region northamerica-northeast1 \
  --allow-unauthenticated
```

## Demo

Call the demo line: **+1 (514) XXX-XXXX**

Try saying:
- "Bonjour, je voudrais prendre un rendez-vous"
- "What are your hours?"
- "I need to see a doctor tomorrow"

## Cost Estimates

| Service | Monthly Cost |
|---------|-------------|
| Twilio | ~$50 |
| Deepgram | ~$30 |
| Azure Speech | ~$20 |
| OpenRouter (DeepSeek) | ~$5 |
| Firebase | ~$10-20 |
| **Total** | **~$115-125** |

## Safety Rules

The AI will NEVER:
- Give medical advice or diagnosis
- Suggest medications or dosages
- Ignore requests to speak to a human

Emergency keywords (chest pain, bleeding, etc.) trigger immediate safety messages.

## License

Proprietary - All rights reserved

## Support

For support, contact: support@medvoice.ai
