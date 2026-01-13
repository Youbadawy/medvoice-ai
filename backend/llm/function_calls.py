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
                    "ramq_number": {
                        "type": "string",
                        "description": "Health Insurance Number (RAMQ) - Optional. asking 'Do you have a RAMQ card?' is preferred."
                    },
                    "consent_given": {
                        "type": "boolean",
                        "description": "Whether the patient gave consent for Bill 25 data privacy"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the appointment (e.g. 'No RAMQ', 'Needs wheelchair', etc.)"
                    }
                },
                "required": ["slot_id", "patient_name", "patient_phone", "visit_type", "consent_given"]
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
    Format available slots for natural, conversational speech.

    Args:
        slots: List of slot dictionaries with datetime, provider_name
        language: Language code

    Returns:
        Formatted string for TTS - sounds natural, no lists
    """
    if not slots:
        if language == "fr":
            return "Hmm, je ne vois pas de disponibilités pour cette période. On peut regarder une autre date si vous voulez?"
        else:
            return "Hmm, I'm not seeing any openings for that time. Would you like me to check a different date?"

    # Take first 2-3 slots max for conversational delivery
    slots_to_show = slots[:3]

    if language == "fr":
        if len(slots_to_show) == 1:
            return f"J'ai {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))} de disponible. Ça vous conviendrait?"
        elif len(slots_to_show) == 2:
            return (
                f"On a {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))} "
                f"ou {slots_to_show[1].get('formatted_datetime', slots_to_show[1].get('datetime'))}. "
                f"Lequel vous irait le mieux?"
            )
        else:
            return (
                f"On a {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))}, "
                f"{slots_to_show[1].get('formatted_datetime', slots_to_show[1].get('datetime'))}, "
                f"ou {slots_to_show[2].get('formatted_datetime', slots_to_show[2].get('datetime'))}. "
                f"Lequel vous conviendrait?"
            )

    else:
        if len(slots_to_show) == 1:
            return f"I have {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))} available. Would that work for you?"
        elif len(slots_to_show) == 2:
            return (
                f"We have {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))} "
                f"or {slots_to_show[1].get('formatted_datetime', slots_to_show[1].get('datetime'))}. "
                f"Which one works better for you?"
            )
        else:
            return (
                f"We have {slots_to_show[0].get('formatted_datetime', slots_to_show[0].get('datetime'))}, "
                f"{slots_to_show[1].get('formatted_datetime', slots_to_show[1].get('datetime'))}, "
                f"or {slots_to_show[2].get('formatted_datetime', slots_to_show[2].get('datetime'))}. "
                f"Which one would you prefer?"
            )


def format_booking_confirmation(booking: Dict, language: str = "fr") -> str:
    """
    Format booking confirmation for natural, warm speech.

    Args:
        booking: Booking details dictionary
        language: Language code

    Returns:
        Formatted confirmation string for TTS - warm and conversational
    """
    conf_num = booking.get("confirmation_number", "")
    datetime_str = booking.get("formatted_datetime", "")
    patient_name = booking.get("patient_name", "").split()[0]  # Use first name only for warmth

    if language == "fr":
        return (
            f"Excellent {patient_name}! C'est tout réservé pour {datetime_str}. "
            f"Votre numéro de confirmation est {conf_num}. "
            f"On vous enverra un petit rappel par texto. Est-ce qu'il y a autre chose que je peux faire pour vous?"
        )
    else:
        return (
            f"Wonderful {patient_name}! You're all set for {datetime_str}. "
            f"Your confirmation number is {conf_num}. "
            f"We'll send you a reminder text. Is there anything else I can help you with today?"
        )
