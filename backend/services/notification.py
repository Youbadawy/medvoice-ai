"""
MedVoice AI - Notification Service
Handles sending notifications (SMS, Email) to patients and staff.
"""

import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications via Twilio and other providers.
    """

    def __init__(self):
        settings = get_settings()
        self.twilio_number = settings.twilio_phone_number
        self.client = None
        
        try:
            if settings.twilio_account_sid and settings.twilio_auth_token:
                self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                logger.info("Twilio client initialized for notifications")
            else:
                logger.warning("Twilio credentials missing - notifications disabled")
        except Exception as e:
            logger.error(f"Error initializing Twilio client: {e}")

    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send an SMS message.
        
        Args:
            to_number: Recipient phone number in E.164 format
            message: Message body
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.client:
            logger.warning("Cannot send SMS: Twilio client not initialized")
            return False

        try:
            # Ensure number is E.164 (basic check)
            if not to_number.startswith('+'):
                # Default to US/Canada +1 if missing
                to_number = f"+1{to_number.lstrip('1')}"

            message = self.client.messages.create(
                body=message,
                from_=self.twilio_number,
                to=to_number
            )
            logger.info(f"SMS sent to {to_number}: {message.sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS to {to_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return False

    async def send_booking_confirmation(
        self, 
        patient_phone: str, 
        patient_name: str, 
        appointment_time: str,
        confirmation_code: str,
        language: str = "fr"
    ) -> bool:
        """
        Send booking confirmation SMS.
        """
        if language == "fr":
            msg = (
                f"Bonjour {patient_name}, votre rendez-vous chez Clinique KaiMed est confirmé pour le "
                f"{appointment_time}. Votre code de confirmation est: {confirmation_code}. "
                f"Merci!"
            )
        else:
            msg = (
                f"Hello {patient_name}, your appointment at KaiMed Clinic is confirmed for "
                f"{appointment_time}. Your confirmation code is: {confirmation_code}. "
                f"Thank you!"
            )

        return self.send_sms(patient_phone, msg)


# Singleton
_notification_service = None

def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
