#!/bin/bash
# MedVoice AI - Backend Deployment Script
# Deploys the FastAPI backend to Google Cloud Run
# IMPORTANT: This script preserves existing API keys/secrets

set -e

PROJECT_ID="medvoice-ai-qc"
REGION="northamerica-northeast1"
SERVICE_NAME="medvoice-api"

echo "=== MedVoice AI Backend Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list 2>&1 | grep -q "ACTIVE"; then
    echo "Please authenticate with gcloud first:"
    echo "  gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    texttospeech.googleapis.com \
    firestore.googleapis.com \
    --quiet

# Build and deploy to Cloud Run
# Using --update-env-vars to PRESERVE existing secrets (API keys)
# Only updates non-secret config values
echo ""
echo "Building and deploying to Cloud Run..."
echo "NOTE: Preserving existing API keys (TWILIO, DEEPGRAM, OPENROUTER)"
cd "$(dirname "$0")/../backend"

gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --update-env-vars "ENVIRONMENT=production" \
    --update-env-vars "FIREBASE_PROJECT_ID=$PROJECT_ID" \
    --update-env-vars "OPENROUTER_MODEL_PRIMARY=google/gemini-3-flash-preview" \
    --update-env-vars "OPENROUTER_MODEL_FALLBACK=deepseek/deepseek-v3.2" \
    --update-env-vars "DEFAULT_LANGUAGE=fr" \
    --update-env-vars "CLINIC_NAME=Clinique Medicale Saint-Laurent" \
    --min-instances 0 \
    --max-instances 10 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 80

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Configure Twilio webhook to: $SERVICE_URL/twilio/voice"
echo "2. Update dashboard API_URL to: $SERVICE_URL"
echo "3. Test the health endpoint: curl $SERVICE_URL/health"
