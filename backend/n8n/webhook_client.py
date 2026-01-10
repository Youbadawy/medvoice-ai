"""
MedVoice AI - n8n Webhook Client
Triggers n8n workflows for calendar operations and notifications.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class N8nWebhookClient:
    """
    Client for triggering n8n workflows via webhooks.

    Workflows:
    - get_slots: Get available appointment slots
    - book_appointment: Create a calendar booking
    - cancel_appointment: Cancel an existing booking
    - send_notification: Send SMS/email notifications
    - create_task: Create a callback task
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize n8n webhook client.

        Args:
            base_url: Base URL for n8n webhooks (e.g., https://n8n.yourapp.com)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_available_slots(
        self,
        visit_type: str = "general",
        preferred_date: Optional[str] = None,
        days_to_search: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots from Google Calendar.

        Args:
            visit_type: Type of visit (general, followup, vaccination)
            preferred_date: Preferred date (YYYY-MM-DD)
            days_to_search: Number of days to search

        Returns:
            List of available slot dictionaries
        """
        if not preferred_date:
            preferred_date = datetime.utcnow().strftime("%Y-%m-%d")

        payload = {
            "visit_type": visit_type,
            "start_date": preferred_date,
            "days_to_search": days_to_search
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/calendar/slots",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            slots = data.get("available_slots", [])

            logger.info(f"Retrieved {len(slots)} available slots")
            return slots

        except httpx.HTTPError as e:
            logger.error(f"Error fetching slots: {e}")
            return []

    async def book_appointment(
        self,
        slot_id: str,
        patient_name: str,
        patient_phone: str,
        visit_type: str = "general",
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Book an appointment via n8n workflow.

        Args:
            slot_id: ID of the selected slot
            patient_name: Patient's full name
            patient_phone: Patient's phone number
            visit_type: Type of visit
            notes: Optional notes

        Returns:
            Booking confirmation dictionary or None on error
        """
        payload = {
            "slot_id": slot_id,
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "visit_type": visit_type,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat()
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/calendar/book",
                json=payload
            )
            response.raise_for_status()

            confirmation = response.json()
            logger.info(f"Booking confirmed: {confirmation.get('confirmation_number')}")
            return confirmation

        except httpx.HTTPError as e:
            logger.error(f"Error booking appointment: {e}")
            return None

    async def cancel_appointment(
        self,
        confirmation_number: str,
        patient_phone: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Cancel an appointment.

        Args:
            confirmation_number: Booking confirmation number
            patient_phone: Patient phone for verification
            reason: Cancellation reason

        Returns:
            True if cancelled successfully
        """
        payload = {
            "confirmation_number": confirmation_number,
            "patient_phone": patient_phone,
            "reason": reason
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/calendar/cancel",
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Appointment cancelled: {confirmation_number}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Error cancelling appointment: {e}")
            return False

    async def send_confirmation_sms(
        self,
        phone_number: str,
        patient_name: str,
        appointment_time: str,
        confirmation_number: str,
        language: str = "fr"
    ) -> bool:
        """
        Send SMS confirmation via n8n.

        Args:
            phone_number: Patient's phone number
            patient_name: Patient's name
            appointment_time: Formatted appointment time
            confirmation_number: Booking confirmation number
            language: Message language

        Returns:
            True if sent successfully
        """
        payload = {
            "phone_number": phone_number,
            "patient_name": patient_name,
            "appointment_time": appointment_time,
            "confirmation_number": confirmation_number,
            "language": language,
            "type": "booking_confirmation"
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/notify/sms",
                json=payload
            )
            response.raise_for_status()

            logger.info(f"SMS confirmation sent to {phone_number}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    async def notify_transfer(
        self,
        call_sid: str,
        caller_number: str,
        reason: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Notify staff about a call transfer.

        Args:
            call_sid: Call identifier
            caller_number: Caller's phone number
            reason: Reason for transfer
            notes: Additional context

        Returns:
            True if notification sent
        """
        payload = {
            "call_sid": call_sid,
            "caller_number": caller_number,
            "reason": reason,
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/notify/transfer",
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Transfer notification sent for call {call_sid}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Error sending transfer notification: {e}")
            return False

    async def create_callback_task(
        self,
        patient_name: str,
        patient_phone: str,
        reason: str,
        urgency: str = "medium",
        preferred_time: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a callback task for staff.

        Args:
            patient_name: Patient's name
            patient_phone: Patient's phone number
            reason: Reason for callback
            urgency: Task urgency (low, medium, high)
            preferred_time: Preferred callback time

        Returns:
            Task ID or None on error
        """
        payload = {
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "reason": reason,
            "urgency": urgency,
            "preferred_time": preferred_time,
            "created_at": datetime.utcnow().isoformat()
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/webhook/task/create",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            task_id = data.get("task_id")
            logger.info(f"Callback task created: {task_id}")
            return task_id

        except httpx.HTTPError as e:
            logger.error(f"Error creating callback task: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if n8n is reachable."""
        try:
            response = await self.client.get(
                f"{self.base_url}/webhook/health",
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
