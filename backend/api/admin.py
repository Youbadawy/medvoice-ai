"""
MedVoice AI - Admin API Routes
Endpoints for the admin dashboard.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


class CallSummary(BaseModel):
    """Summary of a call for the dashboard."""
    call_id: str
    phone_number: str
    language: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    booking_made: bool = False
    transferred: bool = False


class TranscriptEntry(BaseModel):
    """A single transcript entry."""
    speaker: str  # "caller" or "assistant"
    text: str
    timestamp: datetime


class CallDetail(BaseModel):
    """Detailed call information including transcript."""
    call_id: str
    phone_number: str
    language: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    booking_made: bool = False
    transferred: bool = False
    transcript: List[TranscriptEntry] = []


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_calls_today: int
    active_calls: int
    bookings_made: int
    avg_call_duration: float
    success_rate: float


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    # TODO: Implement with Firestore
    return DashboardStats(
        total_calls_today=0,
        active_calls=0,
        bookings_made=0,
        avg_call_duration=0.0,
        success_rate=0.0
    )


@router.get("/calls", response_model=List[CallSummary])
async def get_recent_calls(limit: int = 50, offset: int = 0):
    """Get recent calls for the dashboard."""
    # TODO: Implement with Firestore
    return []


@router.get("/calls/{call_id}", response_model=CallDetail)
async def get_call_detail(call_id: str):
    """Get detailed information about a specific call."""
    # TODO: Implement with Firestore
    raise HTTPException(status_code=404, detail="Call not found")


@router.get("/calls/{call_id}/transcript", response_model=List[TranscriptEntry])
async def get_call_transcript(call_id: str):
    """Get transcript for a specific call."""
    # TODO: Implement with Firestore
    return []


@router.post("/kill-switch")
async def activate_kill_switch():
    """
    Emergency kill switch - stops accepting new calls.
    Existing calls continue until completion.
    """
    # TODO: Implement kill switch logic
    return {"status": "activated", "message": "Kill switch activated. No new calls will be accepted."}


@router.delete("/kill-switch")
async def deactivate_kill_switch():
    """Deactivate the kill switch - resume accepting calls."""
    # TODO: Implement kill switch logic
    return {"status": "deactivated", "message": "Kill switch deactivated. Calls will be accepted."}
