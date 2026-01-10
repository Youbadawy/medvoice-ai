"""
MedVoice AI - Booking Models
Pydantic models for appointment booking.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime


class SlotInfo(BaseModel):
    """Available appointment slot."""
    slot_id: str
    datetime: datetime
    provider_name: str = "Dr. Général"
    duration_minutes: int = 30
    visit_type: str = "general"
    formatted_datetime: Optional[str] = None  # Human-readable format


class BookingRequest(BaseModel):
    """Request to book an appointment."""
    slot_id: str
    patient_name: str
    patient_phone: str
    visit_type: Literal["general", "followup", "vaccination"] = "general"
    notes: Optional[str] = None
    call_sid: Optional[str] = None  # Reference to the originating call


class BookingConfirmation(BaseModel):
    """Confirmed appointment details."""
    booking_id: str
    confirmation_number: str
    slot_id: str
    patient_name: str
    patient_phone: str
    appointment_time: datetime
    provider_name: str
    visit_type: str
    duration_minutes: int = 30
    google_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CancellationRequest(BaseModel):
    """Request to cancel an appointment."""
    confirmation_number: str
    patient_phone: str
    reason: Optional[str] = None


class RescheduleRequest(BaseModel):
    """Request to reschedule an appointment."""
    confirmation_number: str
    patient_phone: str
    new_slot_id: str


class AvailabilityQuery(BaseModel):
    """Query for available slots."""
    visit_type: Literal["general", "followup", "vaccination"] = "general"
    preferred_date: Optional[str] = None  # YYYY-MM-DD
    days_to_search: int = 7


class AvailabilityResponse(BaseModel):
    """Response with available slots."""
    available_slots: List[SlotInfo]
    date_range_start: datetime
    date_range_end: datetime
    visit_type: str


class CallbackRequest(BaseModel):
    """Request for staff callback."""
    patient_name: str
    patient_phone: str
    reason: str
    preferred_time: Optional[str] = None
    urgency: Literal["low", "medium", "high"] = "medium"
    call_sid: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
