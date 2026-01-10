"""
MedVoice AI - Firestore Client
Database operations for calls, transcripts, and appointments.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)


class FirestoreClient:
    """
    Firestore client for MedVoice AI data persistence.

    Collections:
    - calls: Call metadata and status
    - transcripts: Conversation transcripts
    - appointments: Booked appointments
    - tasks: Callback requests and tasks
    """

    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize Firestore client.

        Args:
            project_id: Firebase project ID
            credentials_path: Path to service account JSON
        """
        self.project_id = project_id
        self._initialize_firebase(credentials_path)
        self.db = firestore.client()

    def _initialize_firebase(self, credentials_path: Optional[str] = None):
        """Initialize Firebase Admin SDK if not already initialized."""
        try:
            # Check if already initialized
            firebase_admin.get_app()
        except ValueError:
            # Initialize with credentials
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': self.project_id
                })
            else:
                # Use default credentials (for Cloud Run)
                firebase_admin.initialize_app(options={
                    'projectId': self.project_id
                })

            logger.info("Firebase Admin SDK initialized")

    # ==================== Calls ====================

    async def create_call(self, call_data: Dict[str, Any]) -> str:
        """
        Create a new call record.

        Args:
            call_data: Call metadata

        Returns:
            Document ID
        """
        call_data["created_at"] = datetime.utcnow()
        call_data["status"] = "active"

        doc_ref = self.db.collection("calls").document(call_data.get("call_sid"))
        doc_ref.set(call_data)

        logger.info(f"Created call record: {doc_ref.id}")
        return doc_ref.id

    async def update_call(self, call_sid: str, updates: Dict[str, Any]):
        """Update a call record."""
        doc_ref = self.db.collection("calls").document(call_sid)
        updates["updated_at"] = datetime.utcnow()
        doc_ref.update(updates)

    async def end_call(self, call_sid: str, duration_seconds: int):
        """Mark a call as ended."""
        await self.update_call(call_sid, {
            "status": "completed",
            "ended_at": datetime.utcnow(),
            "duration_seconds": duration_seconds
        })

    async def get_call(self, call_sid: str) -> Optional[Dict]:
        """Get a call by SID."""
        doc = self.db.collection("calls").document(call_sid).get()
        return doc.to_dict() if doc.exists else None

    async def get_recent_calls(self, limit: int = 50) -> List[Dict]:
        """Get recent calls for the dashboard."""
        query = (
            self.db.collection("calls")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )

        docs = query.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    async def get_active_calls(self) -> List[Dict]:
        """Get currently active calls."""
        query = (
            self.db.collection("calls")
            .where(filter=FieldFilter("status", "==", "active"))
        )

        docs = query.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    # ==================== Transcripts ====================

    async def save_transcript(self, call_sid: str, transcript: List[Dict[str, Any]]):
        """
        Save conversation transcript.

        Args:
            call_sid: Call identifier
            transcript: List of transcript entries
        """
        doc_ref = self.db.collection("transcripts").document(call_sid)
        doc_ref.set({
            "call_sid": call_sid,
            "entries": transcript,
            "created_at": datetime.utcnow()
        })

        logger.info(f"Saved transcript for call: {call_sid}")

    async def get_transcript(self, call_sid: str) -> Optional[List[Dict]]:
        """Get transcript for a call."""
        doc = self.db.collection("transcripts").document(call_sid).get()
        if doc.exists:
            return doc.to_dict().get("entries", [])
        return None

    async def append_to_transcript(self, call_sid: str, entry: Dict[str, Any]):
        """Append an entry to an existing transcript."""
        doc_ref = self.db.collection("transcripts").document(call_sid)
        doc_ref.update({
            "entries": firestore.ArrayUnion([entry]),
            "updated_at": datetime.utcnow()
        })

    # ==================== Appointments ====================

    async def create_appointment(self, appointment_data: Dict[str, Any]) -> str:
        """
        Create a new appointment record.

        Args:
            appointment_data: Appointment details

        Returns:
            Document ID
        """
        appointment_data["created_at"] = datetime.utcnow()
        appointment_data["status"] = "confirmed"

        doc_ref = self.db.collection("appointments").add(appointment_data)

        logger.info(f"Created appointment: {doc_ref[1].id}")
        return doc_ref[1].id

    async def get_appointments_for_date(self, date: datetime) -> List[Dict]:
        """Get appointments for a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        query = (
            self.db.collection("appointments")
            .where(filter=FieldFilter("appointment_time", ">=", start_of_day))
            .where(filter=FieldFilter("appointment_time", "<", end_of_day))
            .order_by("appointment_time")
        )

        docs = query.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    async def cancel_appointment(self, appointment_id: str, reason: str):
        """Cancel an appointment."""
        doc_ref = self.db.collection("appointments").document(appointment_id)
        doc_ref.update({
            "status": "cancelled",
            "cancelled_at": datetime.utcnow(),
            "cancellation_reason": reason
        })

    # ==================== Tasks ====================

    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Create a callback task or request.

        Args:
            task_data: Task details

        Returns:
            Document ID
        """
        task_data["created_at"] = datetime.utcnow()
        task_data["status"] = "pending"

        doc_ref = self.db.collection("tasks").add(task_data)

        logger.info(f"Created task: {doc_ref[1].id}")
        return doc_ref[1].id

    async def get_pending_tasks(self) -> List[Dict]:
        """Get all pending tasks."""
        query = (
            self.db.collection("tasks")
            .where(filter=FieldFilter("status", "==", "pending"))
            .order_by("created_at")
        )

        docs = query.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    # ==================== Statistics ====================

    async def get_daily_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific day.

        Args:
            date: Date to get stats for (defaults to today)

        Returns:
            Dictionary with stats
        """
        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Get calls for the day
        calls_query = (
            self.db.collection("calls")
            .where(filter=FieldFilter("created_at", ">=", start_of_day))
            .where(filter=FieldFilter("created_at", "<", end_of_day))
        )

        calls = list(calls_query.stream())
        total_calls = len(calls)

        # Calculate stats
        completed_calls = [c for c in calls if c.to_dict().get("status") == "completed"]
        bookings = [c for c in calls if c.to_dict().get("booking_made")]

        total_duration = sum(
            c.to_dict().get("duration_seconds", 0)
            for c in completed_calls
        )

        return {
            "date": date.isoformat(),
            "total_calls": total_calls,
            "completed_calls": len(completed_calls),
            "bookings_made": len(bookings),
            "avg_duration_seconds": total_duration / len(completed_calls) if completed_calls else 0,
            "success_rate": len(bookings) / total_calls if total_calls > 0 else 0
        }
