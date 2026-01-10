"""
MedVoice AI - Webhook Routes
Endpoints for n8n and external service callbacks.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class BookingConfirmation(BaseModel):
    """Booking confirmation from n8n."""
    booking_id: str
    slot_id: str
    patient_name: str
    patient_phone: str
    appointment_time: datetime
    provider_name: Optional[str] = None
    confirmation_number: str
    google_event_id: Optional[str] = None


class SlotInfo(BaseModel):
    """Available appointment slot."""
    slot_id: str
    datetime: datetime
    provider_name: str
    duration_minutes: int = 30


class SlotsResponse(BaseModel):
    """Response from n8n get_slots workflow."""
    available_slots: List[SlotInfo]
    date_range_start: datetime
    date_range_end: datetime


@router.post("/n8n/booking-confirmed")
async def n8n_booking_confirmed(confirmation: BookingConfirmation):
    """
    Callback from n8n when a booking is confirmed.
    Updates Firestore and notifies active call if still in progress.
    """
    logger.info(f"📅 Booking confirmed: {confirmation.confirmation_number}")

    # TODO: Update Firestore with booking details
    # TODO: Notify active call handler if call still in progress

    return {"status": "received", "booking_id": confirmation.booking_id}


@router.post("/n8n/booking-failed")
async def n8n_booking_failed(request: Request):
    """
    Callback from n8n when a booking fails.
    Triggers fallback flow (e.g., create task, send email).
    """
    data = await request.json()
    logger.warning(f"⚠️ Booking failed: {data}")

    # TODO: Handle booking failure - create task, notify staff

    return {"status": "received", "action": "task_created"}


@router.post("/n8n/slots-response")
async def n8n_slots_response(response: SlotsResponse):
    """
    Callback from n8n with available slots.
    Used when async slot fetching is needed.
    """
    logger.info(f"📋 Received {len(response.available_slots)} available slots")

    # TODO: Forward to active call handler

    return {"status": "received", "slot_count": len(response.available_slots)}


@router.post("/calendar/event-updated")
async def calendar_event_updated(request: Request):
    """
    Webhook for Google Calendar event updates.
    Syncs changes back to our system.
    """
    data = await request.json()
    logger.info(f"📆 Calendar event updated: {data}")

    # TODO: Sync calendar changes to Firestore

    return {"status": "received"}
