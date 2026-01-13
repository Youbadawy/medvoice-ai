"""
MedVoice AI - Main FastAPI Application
Bilingual AI Phone Receptionist for Quebec Medical Clinics
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import get_settings
from voice.twilio_handler import TwilioMediaStreamHandler
from api.admin import router as admin_router
from api.webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("🚀 MedVoice AI starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Default language: {settings.default_language}")
    logger.info(f"Clinic: {settings.clinic_name}")

    yield

    # Shutdown
    logger.info("👋 MedVoice AI shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MedVoice AI",
    description="Bilingual AI Phone Receptionist for Quebec Medical Clinics",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "MedVoice AI",
        "status": "healthy",
        "version": "1.0.0",
        "clinic": settings.clinic_name
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "services": {
            "twilio": "configured" if settings.twilio_account_sid else "missing",
            "deepgram": "configured" if settings.deepgram_api_key else "missing",
            "google_tts": "configured" if settings.google_application_credentials else "missing",
            "openrouter": "configured" if settings.openrouter_api_key else "missing",
            "firebase": "configured" if settings.firebase_project_id else "missing"
        }
    }


@app.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    """
    Twilio Voice webhook - called when a call is received.
    Returns TwiML to connect the call to a media stream.
    """
    # Extract caller info from Twilio webhook
    form_data = await request.form()
    caller_from = form_data.get("From", "unknown")
    call_sid = form_data.get("CallSid", "unknown")

    logger.info(f"📞 Incoming call received - CallSid: {call_sid}, From: {caller_from}")

    # Get the WebSocket URL for media streaming
    # Cloud Run uses x-forwarded-host header
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")

    # Always use wss:// for production (Cloud Run is always HTTPS)
    is_production = settings.environment == "production"
    protocol = "wss" if is_production else "ws"
    stream_url = f"{protocol}://{host}/twilio/media-stream"

    logger.info(f"📡 Stream URL: {stream_url}")

    # TwiML response with bilingual greeting and media stream connection
    # Pass caller number directly (not using Twilio substitution which can fail)
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="fr-CA" voice="Google.fr-CA-Wavenet-A">Bonjour, bienvenue à la clinique KaiMed, un moment s'il vous plaît.</Say>
    <Pause length="1"/>
    <Say language="en-CA" voice="Google.en-US-Wavenet-D">Hello, welcome to KaiMed Clinic, one moment please.</Say>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="caller" value="{caller_from}" />
        </Stream>
    </Connect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio/media-stream")
async def twilio_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams.
    Handles bidirectional audio streaming for voice AI.
    """
    await websocket.accept()
    logger.info("🔌 WebSocket connection established")

    handler = TwilioMediaStreamHandler(websocket, settings)

    try:
        await handler.handle_stream()
    except WebSocketDisconnect:
        logger.info("📴 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        await handler.cleanup()
        logger.info("🧹 Handler cleaned up")


@app.post("/twilio/status")
async def twilio_status_callback(request: Request):
    """Twilio call status callback."""
    form_data = await request.form()
    call_status = form_data.get("CallStatus")
    call_sid = form_data.get("CallSid")

    logger.info(f"📊 Call {call_sid} status: {call_status}")

    return {"status": "received"}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.environment == "development"
    )
