"""
MedVoice AI - Firebase Client
Handles Firestore operations for call data and transcripts.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)


class FirebaseClient:
    """
    Firebase Firestore client for MedVoice AI.
    Manages call records, transcripts, and stats.
    """

    def __init__(self, project_id: Optional[str] = None):
        """Initialize Firestore client."""
        try:
            self.db = firestore.Client(project=project_id)
            logger.info("Firebase client initialized")
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
            self.db = None

    @property
    def is_connected(self) -> bool:
        """Check if Firebase is connected."""
        return self.db is not None

    # ====================
    # Call Management
    # ====================

    async def create_call(self, call_data: Dict[str, Any]) -> str:
        """
        Create a new call record.

        Args:
            call_data: Call information including call_sid, caller_number, etc.

        Returns:
            The document ID of the created call
        """
        if not self.db:
            logger.warning("Firebase not connected, skipping call creation")
            return call_data.get("call_sid", "")

        try:
            call_ref = self.db.collection("calls").document(call_data.get("call_sid"))
            call_ref.set({
                **call_data,
                "created_at": firestore.SERVER_TIMESTAMP,
                "status": "active"
            })
            logger.info(f"Call created: {call_data.get('call_sid')}")
            return call_data.get("call_sid", "")
        except Exception as e:
            logger.error(f"Error creating call: {e}")
            return ""

    async def update_call(self, call_sid: str, updates: Dict[str, Any]):
        """Update a call record."""
        if not self.db:
            return

        try:
            call_ref = self.db.collection("calls").document(call_sid)
            call_ref.update({
                **updates,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Call updated: {call_sid}")
        except Exception as e:
            logger.error(f"Error updating call: {e}")

    async def end_call(self, call_sid: str, summary: Dict[str, Any]):
        """
        Mark a call as ended and save final summary.

        Args:
            call_sid: The call SID
            summary: End-of-call summary (status, duration, booking_made, etc.)
        """
        if not self.db:
            return

        try:
            call_ref = self.db.collection("calls").document(call_sid)

            # Use provided status or default to "completed"
            status = summary.get("status", "completed")

            call_ref.update({
                "status": status,
                "ended_at": firestore.SERVER_TIMESTAMP,
                **summary
            })
            logger.info(f"Call ended: {call_sid} with status: {status}")
        except Exception as e:
            logger.error(f"Error ending call: {e}")

    async def get_call(self, call_sid: str) -> Optional[Dict[str, Any]]:
        """Get a call record by SID."""
        if not self.db:
            return None

        try:
            call_ref = self.db.collection("calls").document(call_sid)
            doc = call_ref.get()
            if doc.exists:
                return {"call_id": doc.id, **doc.to_dict()}
            return None
        except Exception as e:
            logger.error(f"Error getting call: {e}")
            return None

    async def get_recent_calls(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent calls for the dashboard."""
        if not self.db:
            return []

        try:
            query = (
                self.db.collection("calls")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .offset(offset)
            )

            docs = query.stream()
            calls = []
            for doc in docs:
                data = doc.to_dict()
                calls.append({
                    "call_id": doc.id,
                    "phone_number": data.get("caller_number", "Unknown"),
                    "language": data.get("language", "fr"),
                    "status": data.get("status", "unknown"),
                    "started_at": data.get("created_at"),
                    "ended_at": data.get("ended_at"),
                    "duration_seconds": data.get("duration_seconds", 0),
                    "booking_made": data.get("booking_made", False),
                    "transferred": data.get("transferred", False),
                    "cost_data": data.get("cost_data"),
                    "usage_metrics": data.get("usage_metrics")
                })

            return calls
        except Exception as e:
            logger.error(f"Error getting recent calls: {e}")
            return []

    async def get_active_calls(self) -> List[Dict[str, Any]]:
        """Get currently active calls."""
        if not self.db:
            return []

        try:
            query = (
                self.db.collection("calls")
                .where(filter=FieldFilter("status", "==", "active"))
            )

            docs = query.stream()
            return [{"call_id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Error getting active calls: {e}")
            return []

    # ====================
    # Transcript Management
    # ====================

    async def save_transcript(self, call_sid: str, transcript: List[Dict[str, Any]]):
        """Save the conversation transcript for a call."""
        if not self.db:
            return

        try:
            # Save transcript as subcollection
            transcript_ref = self.db.collection("calls").document(call_sid).collection("transcript")

            batch = self.db.batch()
            for i, entry in enumerate(transcript):
                doc_ref = transcript_ref.document(f"{i:04d}")
                batch.set(doc_ref, entry)

            batch.commit()
            logger.info(f"Transcript saved for call: {call_sid}")
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")

    async def get_transcript(self, call_sid: str) -> List[Dict[str, Any]]:
        """Get the transcript for a call."""
        if not self.db:
            return []

        try:
            transcript_ref = (
                self.db.collection("calls")
                .document(call_sid)
                .collection("transcript")
                .order_by("timestamp")
            )

            docs = transcript_ref.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return []

    # ====================
    # Statistics
    # ====================

    async def get_stats_today(self) -> Dict[str, Any]:
        """Get dashboard statistics for today."""
        if not self.db:
            return {
                "total_calls_today": 0,
                "active_calls": 0,
                "bookings_made": 0,
                "avg_call_duration": 0.0,
                "success_rate": 0.0
            }

        try:
            # Get start of today (UTC)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # Query today's calls
            today_query = (
                self.db.collection("calls")
                .where(filter=FieldFilter("created_at", ">=", today_start))
            )

            today_calls = list(today_query.stream())

            # Calculate stats
            total_calls = len(today_calls)
            active_calls = sum(1 for doc in today_calls if doc.to_dict().get("status") == "active")
            bookings_made = sum(1 for doc in today_calls if doc.to_dict().get("booking_made", False))

            # Calculate average duration for completed calls
            completed_calls = [doc for doc in today_calls if doc.to_dict().get("status") == "completed"]
            total_duration = sum(doc.to_dict().get("duration_seconds", 0) for doc in completed_calls)
            avg_duration = total_duration / len(completed_calls) if completed_calls else 0

            # Success rate = completed calls / total calls (excluding active)
            non_active_calls = total_calls - active_calls
            success_rate = len(completed_calls) / non_active_calls if non_active_calls > 0 else 0.0

            return {
                "total_calls_today": total_calls,
                "active_calls": active_calls,
                "bookings_made": bookings_made,
                "avg_call_duration": avg_duration,
                "success_rate": success_rate
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_calls_today": 0,
                "active_calls": 0,
                "bookings_made": 0,
                "avg_call_duration": 0.0,
                "success_rate": 0.0
            }

    # ====================
    # Appointment Management
    # ====================

    async def create_appointment(self, booking_data: Dict[str, Any]) -> str:
        """
        Create a new appointment record.

        Args:
            booking_data: Appointment information

        Returns:
            The booking_id of the created appointment
        """
        if not self.db:
            logger.warning("Firebase not connected, skipping appointment creation")
            return ""

        try:
            # Generate booking_id if not provided
            booking_id = booking_data.get("booking_id")
            if not booking_id:
                import uuid
                booking_id = str(uuid.uuid4())[:8]

            appt_ref = self.db.collection("appointments").document(booking_id)
            appt_ref.set({
                **booking_data,
                "booking_id": booking_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "status": booking_data.get("status", "confirmed")
            })
            logger.info(f"Appointment created: {booking_id}")
            return booking_id
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return ""

    async def get_appointments(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get appointments within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            status: Optional status filter (confirmed, cancelled)

        Returns:
            List of appointment dictionaries
        """
        if not self.db:
            return []

        try:
            # Convert datetimes to ISO strings for query (since stored as string)
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()

            query = (
                self.db.collection("appointments")
                .where(filter=FieldFilter("appointment_time", ">=", start_iso))
                .where(filter=FieldFilter("appointment_time", "<=", end_iso))
            )

            if status:
                query = query.where(filter=FieldFilter("status", "==", status))

            docs = query.stream()
            appointments = []
            for doc in docs:
                data = doc.to_dict()
                appointments.append({
                    "booking_id": doc.id,
                    **data
                })

            # Sort by appointment time
            appointments.sort(key=lambda x: x.get("appointment_time", datetime.min))
            return appointments
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return []

    async def get_appointment(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Get a single appointment by booking_id."""
        if not self.db:
            return None

        try:
            appt_ref = self.db.collection("appointments").document(booking_id)
            doc = appt_ref.get()
            if doc.exists:
                return {"booking_id": doc.id, **doc.to_dict()}
            return None
        except Exception as e:
            logger.error(f"Error getting appointment: {e}")
            return None

    async def update_appointment(self, booking_id: str, updates: Dict[str, Any]):
        """Update an appointment record."""
        if not self.db:
            return

        try:
            appt_ref = self.db.collection("appointments").document(booking_id)
            appt_ref.update({
                **updates,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Appointment updated: {booking_id}")
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")

    async def cancel_appointment(self, booking_id: str, reason: Optional[str] = None):
        """Cancel an appointment."""
        if not self.db:
            return

        try:
            appt_ref = self.db.collection("appointments").document(booking_id)
            appt_ref.update({
                "status": "cancelled",
                "cancelled_at": firestore.SERVER_TIMESTAMP,
                "cancellation_reason": reason
            })
            logger.info(f"Appointment cancelled: {booking_id}")
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")

    async def get_appointments_for_day(self, date: datetime) -> List[Dict[str, Any]]:
        """Get all appointments for a specific day."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return await self.get_appointments(start_of_day, end_of_day, status="confirmed")

    # ====================
    # Settings Management
    # ====================

    async def get_settings(self, settings_key: str = "voice_agent") -> Dict[str, Any]:
        """
        Get settings from Firestore.

        Args:
            settings_key: The settings document key (default: "voice_agent")

        Returns:
            Settings dictionary or default values
        """
        default_settings = {
            "voice_gender": "female",
            "emotion_level": "medium",
            "response_delay_ms": 2500,
            "enabled": True
        }

        if not self.db:
            return default_settings

        try:
            settings_ref = self.db.collection("settings").document(settings_key)
            doc = settings_ref.get()
            if doc.exists:
                return {**default_settings, **doc.to_dict()}
            return default_settings
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return default_settings

    async def update_settings(self, settings_key: str, updates: Dict[str, Any]) -> bool:
        """
        Update settings in Firestore.

        Args:
            settings_key: The settings document key
            updates: Dictionary of settings to update

        Returns:
            True if successful
        """
        if not self.db:
            logger.warning("Firebase not connected, skipping settings update")
            return False

        try:
            settings_ref = self.db.collection("settings").document(settings_key)
            settings_ref.set({
                **updates,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
            logger.info(f"Settings updated: {settings_key}")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False


# Singleton instance
_firebase_client: Optional[FirebaseClient] = None


def get_firebase_client(project_id: Optional[str] = None) -> FirebaseClient:
    """Get or create the Firebase client singleton."""
    global _firebase_client
    if _firebase_client is None:
        _firebase_client = FirebaseClient(project_id)
    return _firebase_client
