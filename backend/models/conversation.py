"""
MedVoice AI - Conversation Models
Pydantic models for conversation data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class TranscriptEntry(BaseModel):
    """A single entry in the conversation transcript."""
    speaker: Literal["caller", "assistant"]
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    language: str = "fr"
    confidence: Optional[float] = None


class ConversationModel(BaseModel):
    """Full conversation data model."""
    call_sid: str
    caller_number: str
    language: str = "fr"
    status: Literal["active", "completed", "transferred", "failed"] = "active"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: List[TranscriptEntry] = []
    booking_made: bool = False
    transferred: bool = False
    intent_detected: Optional[str] = None
    slots_extracted: dict = {}


class CallSummary(BaseModel):
    """Summary of a call for listings."""
    call_sid: str
    caller_number: str
    language: str
    status: str
    started_at: datetime
    duration_seconds: Optional[int] = None
    booking_made: bool = False
    transferred: bool = False


class ConversationState(BaseModel):
    """Current state of an active conversation."""
    call_sid: str
    state: str
    language: str
    last_intent: Optional[str] = None
    pending_tool_call: Optional[str] = None
    slots: dict = {}
    message_count: int = 0
