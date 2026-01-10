"""
MedVoice AI - Function Calling Tools
Tool definitions for appointment booking and management.
"""

from typing import List, Dict, Any

# Tool definitions for OpenAI-compatible function calling
BOOKING_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Get available appointment slots for a given date range and visit type. Call this when a patient wants to book an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "visit_type": {
                        "type": "string",
                        "enum": ["general", "followup", "vaccination"],
                        "description": "Type of visit: general (examen général), followup (suivi), or vaccination"
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "Preferred date in YYYY-MM-DD format. If not specified, use today's date."
                    },
                    "days_to_search": {
                        "type": "integer",
                        "description": "Number of days to search for availability. Default is 7.",
                        "default": 7
                    }
                },
                "required": ["visit_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment slot for a patient. Call this after the patient confirms their slot selection and provides their information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {
                        "type": "string",
                        "description": "The ID of the selected time slot from get_available_slots"
                    },
                    "patient_name": {
                        "type": "string",
                        "description": "Full name of the patient"
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number for confirmation"
                    },
                    "visit_type": {
                        "type": "string",
                        "enum": ["general", "followup", "vaccination"],
                        "description": "Type of visit"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the appointment"
                    }
                },
                "required": ["slot_id", "patient_name", "patient_phone", "visit_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment. Requires identity verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_number": {
                        "type": "string",
                        "description": "The appointment confirmation number"
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number for verification"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for cancellation"
                    }
                },
                "required": ["confirmation_number", "patient_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedule an existing appointment to a new time slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_number": {
                        "type": "string",
                        "description": "The current appointment confirmation number"
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number for verification"
                    },
                    "new_slot_id": {
                        "type": "string",
                        "description": "The ID of the new time slot"
                    }
                },
                "required": ["confirmation_number", "patient_phone", "new_slot_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfer the call to a human receptionist. Use when the patient requests it or when the request is too complex.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": ["patient_request", "complex_request", "emergency", "complaint"],
                        "description": "Reason for transfer"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes for the human receptionist about the situation"
                    }
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_callback_request",
            "description": "Create a request for staff to call the patient back. Use when booking isn't possible but patient needs follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Patient's name"
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for callback request"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Patient's preferred time for callback"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Urgency level of the callback"
                    }
                },
                "required": ["patient_name", "patient_phone", "reason"]
            }
        }
    }
]


# Helper function to format slots for speech
def format_slots_for_speech(slots: List[Dict], language: str = "fr") -> str:
    """
    Format available slots for text-to-speech.

    Args:
        slots: List of slot dictionaries with datetime, provider_name
        language: Language code

    Returns:
        Formatted string for TTS
    """
    if not slots:
        if language == "fr":
            return "Je suis désolé, il n'y a pas de disponibilités pour cette période. Voulez-vous essayer une autre date?"
        else:
            return "I'm sorry, there are no availabilities for this period. Would you like to try another date?"

    # Take first 3 slots
    slots_to_show = slots[:3]

    if language == "fr":
        intro = "Voici les prochaines disponibilités: "
        slot_texts = []
        for i, slot in enumerate(slots_to_show, 1):
            # Format: "Premier, mardi le 15 janvier à 10h30"
            ordinal = ["Premier", "Deuxième", "Troisième"][i-1]
            slot_texts.append(f"{ordinal}, {slot.get('formatted_datetime', slot.get('datetime'))}")

        return intro + ". ".join(slot_texts) + ". Lequel préférez-vous?"

    else:
        intro = "Here are the next available slots: "
        slot_texts = []
        for i, slot in enumerate(slots_to_show, 1):
            ordinal = ["First", "Second", "Third"][i-1]
            slot_texts.append(f"{ordinal}, {slot.get('formatted_datetime', slot.get('datetime'))}")

        return intro + ". ".join(slot_texts) + ". Which one would you prefer?"


def format_booking_confirmation(booking: Dict, language: str = "fr") -> str:
    """
    Format booking confirmation for speech.

    Args:
        booking: Booking details dictionary
        language: Language code

    Returns:
        Formatted confirmation string for TTS
    """
    conf_num = booking.get("confirmation_number", "")
    datetime_str = booking.get("formatted_datetime", "")
    patient_name = booking.get("patient_name", "")

    if language == "fr":
        return (
            f"Parfait {patient_name}, votre rendez-vous est confirmé pour {datetime_str}. "
            f"Votre numéro de confirmation est {conf_num}. "
            "Vous recevrez un SMS de rappel. Y a-t-il autre chose que je peux faire pour vous?"
        )
    else:
        return (
            f"Perfect {patient_name}, your appointment is confirmed for {datetime_str}. "
            f"Your confirmation number is {conf_num}. "
            "You'll receive an SMS reminder. Is there anything else I can help you with?"
        )
