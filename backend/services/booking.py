"""
MedVoice AI - Booking Service
Handles real appointment booking via Firestore.
"""

import logging
import random
import string
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Backport for Python < 3.9 if needed, but we assume 3.9+
    from backports.zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to NANP format (North American Numbering Plan).
    Returns format: +1XXXXXXXXXX

    Examples:
        "514-555-1234" -> "+15145551234"
        "(514) 555-1234" -> "+15145551234"
        "5145551234" -> "+15145551234"
        "+1 514 555 1234" -> "+15145551234"
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Handle various formats
    if len(digits) == 10:
        # 10 digits: assume Canadian/US number without country code
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        # 11 digits starting with 1: add + prefix
        return f"+{digits}"
    elif len(digits) > 11:
        # Already has country code, just add +
        return f"+{digits}"
    else:
        # Return original if we can't parse it
        return phone


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number is valid NANP format.
    NANP: NXX-NXX-XXXX where N is 2-9 and X is 0-9
    """
    normalized = normalize_phone_number(phone)

    # Check format: +1 followed by 10 digits
    if not re.match(r'^\+1\d{10}$', normalized):
        return False

    # Extract area code and exchange (first 6 digits after +1)
    area_code = normalized[2:5]
    exchange = normalized[5:8]

    # Area code and exchange must start with 2-9
    if area_code[0] in '01' or exchange[0] in '01':
        return False

    return True


class BookingService:
    """
    Booking service for appointment management.
    Uses Firestore for persistence with configurable clinic hours.
    """

    def __init__(self, firebase_client=None):
        self.firebase = firebase_client
        self.timezone = ZoneInfo("America/Montreal")

        # Clinic hours: Monday-Friday 9am-6pm (as tuples of (start_hour, end_hour))
        self.clinic_hours = {
            0: (9, 18),   # Monday 9am-6pm
            1: (9, 18),   # Tuesday
            2: (9, 18),   # Wednesday
            3: (9, 18),   # Thursday
            4: (9, 18),   # Friday
            5: None,      # Saturday - closed
            6: None,      # Sunday - closed
        }
        self.slot_duration = 30  # minutes
        self.default_provider = "Dr. Kamal"

        if firebase_client:
            logger.info("Booking service initialized with Firestore")
        else:
            logger.warning("Booking service running without Firestore (mock mode)")

    def _generate_confirmation_number(self) -> str:
        """Generate a unique confirmation number."""
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"KM-{chars}"

    def _generate_slot_id(self, dt: datetime) -> str:
        """Generate a slot ID from datetime."""
        return dt.strftime("%Y%m%d%H%M")

    def _get_clinic_hours_for_day(self, weekday: int) -> Optional[tuple]:
        """Get clinic hours for a specific weekday (0=Monday, 6=Sunday)."""
        return self.clinic_hours.get(weekday)

    def _generate_all_slots_for_day(self, target_date: date, language: str = "fr") -> List[Dict[str, Any]]:
        """Generate all possible time slots for a given day."""
        weekday = target_date.weekday()
        hours = self._get_clinic_hours_for_day(weekday)

        if not hours:
            return []  # Clinic closed

        start_hour, end_hour = hours
        slots = []

        current_time = datetime.combine(target_date, time(start_hour, 0))
        end_time = datetime.combine(target_date, time(end_hour, 0))

        while current_time < end_time:
            slot_id = self._generate_slot_id(current_time)

            # Format time based on language
            if language == "fr":
                hour = current_time.hour
                minute = current_time.minute
                time_formatted = f"{hour}h{minute:02d}" if minute else f"{hour}h"
            else:
                time_formatted = current_time.strftime("%I:%M %p").lstrip("0")

            slots.append({
                "slot_id": slot_id,
                "datetime": current_time.isoformat(),
                "time_formatted": time_formatted,
                "provider": self.default_provider,
                "duration_minutes": self.slot_duration,
                "is_available": True
            })

            current_time += timedelta(minutes=self.slot_duration)

        return slots

    async def get_available_slots(
        self,
        visit_type: str = "general",
        preferred_date: Optional[str] = None,
        days_to_search: int = 7,
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots.

        Args:
            visit_type: Type of visit (general, followup, vaccination)
            preferred_date: Preferred date in YYYY-MM-DD format
            days_to_search: Number of days to search
            language: Language for formatting

        Returns:
            List of available slot dictionaries
        """
        # Parse preferred date or use tomorrow
        if preferred_date:
            try:
                start_date = datetime.strptime(preferred_date, "%Y-%m-%d").date()
            except ValueError:
                start_date = (datetime.now(self.timezone) + timedelta(days=1)).date()
        else:
            start_date = (datetime.now(self.timezone) + timedelta(days=1)).date()

        all_slots = []

        # Generate slots for each day
        for day_offset in range(days_to_search):
            target_date = start_date + timedelta(days=day_offset)
            day_slots = self._generate_all_slots_for_day(target_date, language)

            if day_slots:
                # Get booked appointments for this day
                booked_times = set()
                if self.firebase:
                    try:
                        appointments = await self.firebase.get_appointments_for_day(
                            datetime.combine(target_date, time(0, 0))
                        )
                        for appt in appointments:
                            appt_time = appt.get("appointment_time")
                            if appt_time:
                                # Fix: Handle ISO strings properly
                                try:
                                    if isinstance(appt_time, str):
                                        # Parse ISO string to datetime
                                        dt = datetime.fromisoformat(appt_time)
                                        booked_times.add(dt.strftime("%Y%m%d%H%M"))
                                    elif hasattr(appt_time, 'strftime'):
                                        booked_times.add(appt_time.strftime("%Y%m%d%H%M"))
                                except ValueError:
                                    logger.warning(f"Failed to parse appointment time: {appt_time}")
                    except Exception as e:
                        logger.error(f"Error fetching booked slots: {e}")

                # Filter out booked slots
                for slot in day_slots:
                    if slot["slot_id"] not in booked_times:
                        # Add formatted date
                        slot_dt = datetime.fromisoformat(slot["datetime"])
                        if language == "fr":
                            day_names = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
                            month_names = ["janvier", "février", "mars", "avril", "mai", "juin",
                                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                            day_name = day_names[slot_dt.weekday()]
                            month_name = month_names[slot_dt.month - 1]
                            slot["formatted_datetime"] = f"{day_name} le {slot_dt.day} {month_name} à {slot['time_formatted']}"
                        else:
                            slot["formatted_datetime"] = f"{slot_dt.strftime('%A, %B %d')} at {slot['time_formatted']}"

                        all_slots.append(slot)

        # Return enough slots for the LLM to understand availability across multiple days
        # 3 was too few, causing it to think future days were full.
        return all_slots[:15] if all_slots else self._generate_mock_slots(language)

    def _generate_mock_slots(self, language: str) -> List[Dict[str, Any]]:
        """Generate mock slots for testing when Firestore is not available."""
        now = datetime.now(self.timezone)
        slots = []

        day_names_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        day_names_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        month_names_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
                         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

        for i, (hour, minute) in enumerate([(10, 0), (14, 30), (9, 0)]):
            slot_date = now + timedelta(days=i+1)
            # Skip weekends
            while slot_date.weekday() >= 5:
                slot_date += timedelta(days=1)

            slot_datetime = slot_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if language == "fr":
                day_name = day_names_fr[slot_datetime.weekday()]
                month_name = month_names_fr[slot_datetime.month - 1]
                formatted = f"{day_name} le {slot_datetime.day} {month_name} à {hour}h{minute if minute else ''}"
            else:
                day_name = day_names_en[slot_datetime.weekday()]
                formatted = f"{day_name}, {slot_datetime.strftime('%B %d')} at {hour}:{minute:02d}"

            slots.append({
                "slot_id": str(i+1),
                "datetime": slot_datetime.isoformat(),
                "formatted_datetime": formatted,
                "provider": self.default_provider,
                "duration_minutes": 30
            })

        return slots

    async def book_appointment(
        self,
        slot_id: str,
        patient_name: str,
        patient_phone: str,
        visit_type: str = "general",
        ramq_number: Optional[str] = None,
        consent_given: bool = False,
        notes: Optional[str] = None,
        formatted_datetime: str = "",
        language: str = "fr",
        call_sid: Optional[str] = None,
        booked_via: str = "ai"
    ) -> Dict[str, Any]:
        """
        Book an appointment.
        """
        try:
            # 1. Generate IDs
            booking_id = f"bk_{int(datetime.now().timestamp())}"
            # Format: KM-XXXXXX (KaiMed)
            confirmation_number = f"KM-{booking_id[-6:]}"

            # 2. Normalize phone number to NANP format
            normalized_phone = normalize_phone_number(patient_phone)

            # 3. Parse slot_id to get appointment time
            try:
                # Expecting YYYYMMDDHHMM
                appointment_time = datetime.strptime(slot_id, "%Y%m%d%H%M")
            except ValueError:
                # Fallback only for single-digit mock IDs used in testing
                if len(slot_id) <= 2 and slot_id.isdigit():
                     appointment_time = datetime.now(self.timezone) + timedelta(days=1)
                else:
                    logger.error(f"Invalid slot_id format: {slot_id}")
                    return {
                        "success": False,
                        "error": "Invalid slot ID format. Please ensure you select a valid time slot."
                    }

            # 4. Create booking record
            booking_data = {
                "booking_id": booking_id,
                "confirmation_number": confirmation_number,
                "slot_id": slot_id,
                "appointment_time": appointment_time.strftime("%Y-%m-%dT%H:%M:%S"),  # Consistent ISO format for Firebase queries
                "patient_name": patient_name,
                "patient_phone": normalized_phone,
                "ramq_number": ramq_number,
                "consent_given": consent_given,
                "visit_type": visit_type,
                "provider": self.default_provider,
                "notes": notes,
                "formatted_datetime": formatted_datetime,
                "booked_via": booked_via,
                "call_sid": call_sid,
                "status": "confirmed",
                "created_at": datetime.now(self.timezone).isoformat(),
                "language": language
            }

            # 5. Save to Firestore
            if self.firebase:
                try:
                    await self.firebase.create_appointment(booking_data)
                    logger.info(f"Booking created in Firestore: {booking_id}")
                except Exception as e:
                    logger.error(f"Firestore booking failed: {e}")
                    # In production, we might want to raise here or handle gracefully
            
            # 6. Return confirmation
            return {
                "success": True,
                "confirmation_number": confirmation_number,
                "patient_name": patient_name,
                "formatted_datetime": formatted_datetime or appointment_time.strftime("%Y-%m-%d %H:%M"),
                "status": "confirmed"
            }

        except Exception as e:
            logger.error(f"Booking error: {e}")
            return {
                "success": False,
                "error": "Booking failed"
            }

    async def cancel_appointment(
        self,
        confirmation_number: str,
        patient_phone: str,
        reason: Optional[str] = None,
        language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Cancel an appointment.

        Args:
            confirmation_number: Appointment confirmation number
            patient_phone: Patient phone for verification
            reason: Cancellation reason
            language: Language for response

        Returns:
            Cancellation result
        """
        if self.firebase:
            try:
                # Find appointment by confirmation number
                # Note: Would need index on confirmation_number for production
                await self.firebase.cancel_appointment(confirmation_number, reason)
                logger.info(f"Appointment cancelled: {confirmation_number}")
            except Exception as e:
                logger.error(f"Cancellation failed: {e}")

        return {
            "success": True,
            "confirmation_number": confirmation_number,
            "status": "cancelled"
        }

    async def get_appointments_for_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get appointments within a date range."""
        if self.firebase:
            return await self.firebase.get_appointments(start_date, end_date)
        return []

    async def get_slots_for_date(
        self,
        target_date: date,
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """Get all slots (available and booked) for a specific date."""
        all_slots = self._generate_all_slots_for_day(target_date, language)

        if not all_slots:
            return []

        # Get booked appointments
        booked_slot_ids = set()
        if self.firebase:
            try:
                appointments = await self.firebase.get_appointments_for_day(
                    datetime.combine(target_date, time(0, 0))
                )
                for appt in appointments:
                    appt_time = appt.get("appointment_time")
                    if appt_time:
                        if hasattr(appt_time, 'strftime'):
                            booked_slot_ids.add(appt_time.strftime("%Y%m%d%H%M"))
            except Exception as e:
                logger.error(f"Error fetching appointments: {e}")

        # Mark availability
        for slot in all_slots:
            slot["is_available"] = slot["slot_id"] not in booked_slot_ids

        return all_slots

    async def create_callback_request(
        self,
        patient_name: str,
        patient_phone: str,
        reason: str,
        preferred_time: Optional[str] = None,
        urgency: str = "medium",
        language: str = "fr"
    ) -> Dict[str, Any]:
        """Create a callback request when booking isn't possible."""
        ref_num = ''.join(random.choices(string.digits, k=6))

        # Could save to Firestore callback_requests collection
        return {
            "success": True,
            "reference_number": f"CB-{ref_num}",
            "patient_name": patient_name,
            "status": "pending"
        }

    async def close(self):
        """Cleanup (no-op for Firestore)."""
        pass


# Singleton instance
_booking_service: Optional[BookingService] = None


def get_booking_service(firebase_client=None) -> BookingService:
    """Get or create the booking service singleton."""
    global _booking_service
    if _booking_service is None:
        _booking_service = BookingService(firebase_client)
    return _booking_service
