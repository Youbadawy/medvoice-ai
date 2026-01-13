"""
MedVoice AI - Admin API Routes
Endpoints for the admin dashboard.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from storage.firebase_client import get_firebase_client
from services.booking import get_booking_service
from services.notification import get_notification_service

router = APIRouter()


class CallSummary(BaseModel):
    """Summary of a call for the dashboard."""
    call_id: str
    phone_number: str
    language: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    booking_made: bool = False
    transferred: bool = False

    class Config:
        from_attributes = True


class TranscriptEntry(BaseModel):
    """A single transcript entry."""
    speaker: str  # "caller" or "assistant"
    text: str
    timestamp: Optional[datetime] = None


class CallDetail(BaseModel):
    """Detailed call information including transcript."""
    call_id: str
    phone_number: str
    language: str
    status: str
    started_at: Optional[datetime] = None
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


# =====================
# Appointment Models
# =====================

class AppointmentResponse(BaseModel):
    """Appointment details response."""
    booking_id: str
    confirmation_number: Optional[str] = None
    patient_name: str
    patient_phone: str
    appointment_time: datetime
    visit_type: str
    provider: str = "Dr. Kamal"
    status: str  # confirmed, cancelled
    booked_via: str = "ai"  # ai, admin
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AppointmentCreateRequest(BaseModel):
    """Request to create an appointment."""
    patient_name: str
    patient_phone: str
    slot_id: str  # YYYYMMDDHHMM format
    visit_type: str = "general"
    ramq_number: Optional[str] = None
    consent_given: bool = False
    notes: Optional[str] = None


class SlotResponse(BaseModel):
    """Time slot response."""
    slot_id: str
    datetime: str
    time_formatted: str
    provider: str
    duration_minutes: int
    is_available: bool
    formatted_datetime: Optional[str] = None


class CalendarDayData(BaseModel):
    """Summary data for a single day in calendar view."""
    date: str
    day_of_week: int
    appointment_count: int
    total_slots: int
    available_slots: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics from Firestore."""
    firebase = get_firebase_client()
    stats = await firebase.get_stats_today()

    return DashboardStats(
        total_calls_today=stats.get("total_calls_today", 0),
        active_calls=stats.get("active_calls", 0),
        bookings_made=stats.get("bookings_made", 0),
        avg_call_duration=stats.get("avg_call_duration", 0.0),
        success_rate=stats.get("success_rate", 0.0)
    )


@router.get("/costs")
async def get_costs(days: int = 30):
    """
    Get financial cost summary for the last N days.
    """
    try:
        firebase = get_firebase_client()
        calls = await firebase.get_recent_calls(limit=500) # Fetch ample history

        total_cost = 0.0
        breakdown = {
            "telephony": 0.0,
            "asr": 0.0,
            "tts": 0.0,
            "llm": 0.0
        }

        daily_costs = {}

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        for call in calls:
            # Check date
            created_at = call.get("created_at")
            if not created_at:
                continue

            # If string, parse it. Firestore client usually returns datetime though.
            if isinstance(created_at, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at)
                except ValueError:
                    continue
            else:
                created_at_dt = created_at

            if created_at_dt < start_date:
                continue

            cost_data = call.get("cost_data", {})
            if not cost_data:
                continue

            c_total = cost_data.get("total_cost", 0.0)
            c_breakdown = cost_data.get("breakdown", {})

            total_cost += c_total
            breakdown["telephony"] += c_breakdown.get("telephony", 0.0)
            breakdown["asr"] += c_breakdown.get("asr", 0.0)
            breakdown["tts"] += c_breakdown.get("tts", 0.0)
            breakdown["llm"] += c_breakdown.get("llm", 0.0)

            # Daily aggregation
            date_str = created_at_dt.strftime("%Y-%m-%d")
            daily_costs[date_str] = daily_costs.get(date_str, 0.0) + c_total

        return {
            "period_days": days,
            "total_cost": round(total_cost, 4),
            "breakdown": {k: round(v, 4) for k, v in breakdown.items()},
            "daily_costs": [{"date": k, "cost": round(v, 4)} for k, v in sorted(daily_costs.items(), reverse=True)]
        }
    except Exception as e:
        print(f"Error calculating costs: {e}")
        # Return empty structure on error to prevent UI crash
        return {
            "period_days": days,
            "total_cost": 0.0,
            "breakdown": {"telephony": 0.0, "asr": 0.0, "tts": 0.0, "llm": 0.0},
            "daily_costs": []
        }


@router.get("/costs/analytics")
async def get_cost_analytics(days: int = 30):
    """
    Get comprehensive cost analytics with breakdowns by provider, status, and trends.
    """
    try:
        firebase = get_firebase_client()
        calls = await firebase.get_recent_calls(limit=500)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Initialize aggregation structures
        totals = {"cost": 0.0, "calls": 0}
        by_provider = {
            "telephony": 0.0,
            "asr": 0.0,
            "tts": 0.0,
            "llm": 0.0
        }
        by_status = {}
        daily_trend = {}
        top_calls = []

        for call in calls:
            created_at = call.get("created_at")
            if not created_at:
                continue

            if isinstance(created_at, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at)
                except ValueError:
                    continue
            else:
                created_at_dt = created_at

            if created_at_dt < start_date:
                continue

            cost_data = call.get("cost_data", {})
            c_total = cost_data.get("total_cost", 0.0) if cost_data else 0.0
            c_breakdown = cost_data.get("breakdown", {}) if cost_data else {}

            # Totals
            totals["cost"] += c_total
            totals["calls"] += 1

            # By provider
            by_provider["telephony"] += c_breakdown.get("telephony", 0.0)
            by_provider["asr"] += c_breakdown.get("asr", 0.0)
            by_provider["tts"] += c_breakdown.get("tts", 0.0)
            by_provider["llm"] += c_breakdown.get("llm", 0.0)

            # By status
            status = call.get("status", "unknown")
            if status not in by_status:
                by_status[status] = {"count": 0, "cost": 0.0}
            by_status[status]["count"] += 1
            by_status[status]["cost"] += c_total

            # Daily trend
            date_str = created_at_dt.strftime("%Y-%m-%d")
            if date_str not in daily_trend:
                daily_trend[date_str] = {"cost": 0.0, "calls": 0}
            daily_trend[date_str]["cost"] += c_total
            daily_trend[date_str]["calls"] += 1

            # Track for top expensive calls
            top_calls.append({
                "call_sid": call.get("call_id", call.get("call_sid", "")),
                "caller_number": call.get("caller_number", call.get("phone_number", "Unknown")),
                "cost": c_total,
                "duration": call.get("duration_seconds", 0),
                "status": status,
                "booking_made": call.get("booking_made", False),
                "created_at": created_at_dt.isoformat() if isinstance(created_at_dt, datetime) else str(created_at_dt)
            })

        # Calculate derived metrics
        avg_per_call = totals["cost"] / totals["calls"] if totals["calls"] > 0 else 0.0
        actual_days = len(daily_trend) if daily_trend else 1
        avg_per_day = totals["cost"] / actual_days if actual_days > 0 else 0.0

        # Calculate provider percentages
        provider_breakdown = {}
        for provider, cost in by_provider.items():
            provider_breakdown[provider] = {
                "cost": round(cost, 4),
                "percentage": round((cost / totals["cost"] * 100) if totals["cost"] > 0 else 0, 1)
            }

        # Round status costs
        status_breakdown = {}
        for status, data in by_status.items():
            status_breakdown[status] = {
                "count": data["count"],
                "cost": round(data["cost"], 4)
            }

        # Sort and format daily trend
        trend_list = [
            {"date": k, "cost": round(v["cost"], 4), "calls": v["calls"]}
            for k, v in sorted(daily_trend.items(), reverse=True)
        ]

        # Get top 5 most expensive calls
        top_calls.sort(key=lambda x: x["cost"], reverse=True)
        top_expensive = top_calls[:5]
        for call in top_expensive:
            call["cost"] = round(call["cost"], 4)

        return {
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": days
            },
            "totals": {
                "cost": round(totals["cost"], 4),
                "calls": totals["calls"],
                "avg_per_call": round(avg_per_call, 4),
                "avg_per_day": round(avg_per_day, 4)
            },
            "by_provider": provider_breakdown,
            "by_status": status_breakdown,
            "daily_trend": trend_list,
            "top_expensive_calls": top_expensive
        }
    except Exception as e:
        print(f"Error in cost analytics: {e}")
        return {
            "period": {"start": "", "end": "", "days": days},
            "totals": {"cost": 0.0, "calls": 0, "avg_per_call": 0.0, "avg_per_day": 0.0},
            "by_provider": {},
            "by_status": {},
            "daily_trend": [],
            "top_expensive_calls": []
        }


@router.get("/calls/costs")
async def get_calls_with_costs(
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Max number of calls to return per page"),
    offset: int = Query(0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get per-call cost details with filtering options and pagination.
    """
    try:
        firebase = get_firebase_client()
        # Fetch larger pool to filter from memory (temporary approach until complex indexes)
        calls = await firebase.get_recent_calls(limit=1000)

        # Parse date filters
        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d")
            except ValueError:
                start_date = datetime.now() - timedelta(days=30)
        else:
            start_date = datetime.now() - timedelta(days=30)

        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            except ValueError:
                end_date = datetime.now()
        else:
            end_date = datetime.now()

        filtered_calls = []
        total_cost = 0.0

        for call in calls:
            created_at = call.get("created_at")
            if not created_at:
                continue

            if isinstance(created_at, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at)
                except ValueError:
                    continue
            else:
                created_at_dt = created_at

            # Date filter
            if created_at_dt < start_date or created_at_dt > end_date:
                continue

            # Status filter
            call_status = call.get("status", "unknown")
            if status and call_status != status:
                continue

            cost_data = call.get("cost_data", {})
            c_total = cost_data.get("total_cost", 0.0) if cost_data else 0.0
            
            # Accumulate cost for ALL matching calls (before pagination)
            total_cost += c_total

            filtered_calls.append({
                "call_sid": call.get("call_id", call.get("call_sid", "")),
                "caller_number": call.get("caller_number", call.get("phone_number", "Unknown")),
                "created_at": created_at_dt.isoformat() if isinstance(created_at_dt, datetime) else str(created_at_dt),
                "duration_seconds": call.get("duration_seconds", 0),
                "status": call_status,
                "booking_made": call.get("booking_made", False),
                "language": call.get("language", "fr"),
                "cost_data": {
                    "total_cost": round(c_total, 4),
                    "breakdown": {
                        k: round(v, 4) for k, v in cost_data.get("breakdown", {}).items()
                    } if cost_data else {}
                }
            })

        # Sort by created_at descending
        filtered_calls.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        total_matching_calls = len(filtered_calls)
        paginated_calls = filtered_calls[offset : offset + limit]

        return {
            "calls": paginated_calls,
            "summary": {
                "total_calls": total_matching_calls,
                "total_cost": round(total_cost, 4),
                "avg_cost_per_call": round(total_cost / total_matching_calls, 4) if total_matching_calls > 0 else 0.0
            }
        }
    except Exception as e:
        print(f"Error getting calls with costs: {e}")
        return {
            "calls": [],
            "summary": {"total_calls": 0, "total_cost": 0.0, "avg_cost_per_call": 0.0}
        }


@router.get("/calls", response_model=List[CallSummary])
async def get_recent_calls(limit: int = 50, offset: int = 0):
    """Get recent calls for the dashboard."""
    firebase = get_firebase_client()
    calls = await firebase.get_recent_calls(limit=limit, offset=offset)

    return [CallSummary(**call) for call in calls]


@router.get("/calls/active", response_model=List[CallSummary])
async def get_active_calls():
    """Get currently active calls."""
    firebase = get_firebase_client()
    calls = await firebase.get_active_calls()

    return [CallSummary(
        call_id=call.get("call_id", ""),
        phone_number=call.get("caller_number", "Unknown"),
        language=call.get("language", "fr"),
        status=call.get("status", "active"),
        started_at=call.get("created_at"),
        duration_seconds=call.get("duration_seconds", 0),
        booking_made=call.get("booking_made", False),
        transferred=call.get("transferred", False)
    ) for call in calls]


@router.get("/calls/{call_id}", response_model=CallDetail)
async def get_call_detail(call_id: str):
    """Get detailed information about a specific call."""
    firebase = get_firebase_client()
    call = await firebase.get_call(call_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Get transcript
    transcript_data = await firebase.get_transcript(call_id)
    transcript = [
        TranscriptEntry(
            speaker=entry.get("speaker", "unknown"),
            text=entry.get("text", ""),
            timestamp=entry.get("timestamp")
        )
        for entry in transcript_data
    ]

    return CallDetail(
        call_id=call.get("call_id", ""),
        phone_number=call.get("caller_number", "Unknown"),
        language=call.get("language", "fr"),
        status=call.get("status", "unknown"),
        started_at=call.get("created_at"),
        ended_at=call.get("ended_at"),
        duration_seconds=call.get("duration_seconds", 0),
        booking_made=call.get("booking_made", False),
        transferred=call.get("transferred", False),
        transcript=transcript
    )


@router.get("/calls/{call_id}/transcript", response_model=List[TranscriptEntry])
async def get_call_transcript(call_id: str):
    """Get transcript for a specific call."""
    firebase = get_firebase_client()
    transcript_data = await firebase.get_transcript(call_id)

    return [
        TranscriptEntry(
            speaker=entry.get("speaker", "unknown"),
            text=entry.get("text", ""),
            timestamp=entry.get("timestamp")
        )
        for entry in transcript_data
    ]


@router.post("/kill-switch")
async def activate_kill_switch():
    """
    Emergency kill switch - stops accepting new calls.
    Existing calls continue until completion.
    """
    firebase = get_firebase_client()
    if firebase.is_connected:
        # Store kill switch state in Firestore
        firebase.db.collection("settings").document("kill_switch").set({
            "active": True,
            "activated_at": datetime.utcnow(),
            "activated_by": "admin"
        })

    return {"status": "activated", "message": "Kill switch activated. No new calls will be accepted."}


@router.delete("/kill-switch")
async def deactivate_kill_switch():
    """Deactivate the kill switch - resume accepting calls."""
    firebase = get_firebase_client()
    if firebase.is_connected:
        firebase.db.collection("settings").document("kill_switch").set({
            "active": False,
            "deactivated_at": datetime.utcnow()
        })

    return {"status": "deactivated", "message": "Kill switch deactivated. Calls will be accepted."}


@router.get("/kill-switch")
async def get_kill_switch_status():
    """Get current kill switch status."""
    firebase = get_firebase_client()
    if firebase.is_connected:
        doc = firebase.db.collection("settings").document("kill_switch").get()
        if doc.exists:
            return {"active": doc.to_dict().get("active", False)}

    return {"active": False}


# =====================
# Appointment Endpoints
# =====================

@router.get("/appointments", response_model=List[AppointmentResponse])
async def get_appointments(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get appointments within a date range."""
    firebase = get_firebase_client()

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    appointments = await firebase.get_appointments(start_date, end_date)

    return [
        AppointmentResponse(
            booking_id=appt.get("booking_id", ""),
            confirmation_number=appt.get("confirmation_number"),
            patient_name=appt.get("patient_name", "Unknown"),
            patient_phone=appt.get("patient_phone", ""),
            appointment_time=appt.get("appointment_time"),
            visit_type=appt.get("visit_type", "general"),
            provider=appt.get("provider", "Dr. Kamal"),
            status=appt.get("status", "confirmed"),
            booked_via=appt.get("booked_via", "ai"),
            notes=appt.get("notes"),
            created_at=appt.get("created_at")
        )
        for appt in appointments
    ]


@router.get("/appointments/{booking_id}", response_model=AppointmentResponse)
async def get_appointment(booking_id: str):
    """Get a single appointment by booking ID."""
    firebase = get_firebase_client()
    appt = await firebase.get_appointment(booking_id)

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return AppointmentResponse(
        booking_id=appt.get("booking_id", ""),
        confirmation_number=appt.get("confirmation_number"),
        patient_name=appt.get("patient_name", "Unknown"),
        patient_phone=appt.get("patient_phone", ""),
        appointment_time=appt.get("appointment_time"),
        visit_type=appt.get("visit_type", "general"),
        provider=appt.get("provider", "Dr. Kamal"),
        status=appt.get("status", "confirmed"),
        booked_via=appt.get("booked_via", "ai"),
        notes=appt.get("notes"),
        created_at=appt.get("created_at")
    )


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(booking: AppointmentCreateRequest):
    """Create a new appointment (manual admin booking)."""
    firebase = get_firebase_client()
    booking_service = get_booking_service(firebase)

    result = await booking_service.book_appointment(
        slot_id=booking.slot_id,
        patient_name=booking.patient_name,
        patient_phone=booking.patient_phone,
        visit_type=booking.visit_type,
        ramq_number=booking.ramq_number,
        consent_given=booking.consent_given,
        notes=booking.notes,
        booked_via="admin",
        language="en"
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Failed to create appointment")

    # Parse appointment time from slot_id
    try:
        appointment_time = datetime.strptime(booking.slot_id, "%Y%m%d%H%M")
    except ValueError:
        appointment_time = datetime.utcnow()

    # Send SMS notification
    try:
        notification_service = get_notification_service()
        # Format time for message (e.g. 2023-10-25 14:30)
        formatted_time = appointment_time.strftime("%Y-%m-%d %H:%M")
        
        await notification_service.send_booking_confirmation(
            patient_phone=booking.patient_phone,
            patient_name=booking.patient_name,
            appointment_time=formatted_time,
            confirmation_code=result.get("confirmation_number", ""),
            language="en" # Admin bookings default to English or we could add a field
        )
    except Exception as e:
        # Don't fail the request if SMS fails, just log it
        print(f"Error sending manual booking SMS: {e}")

    return AppointmentResponse(
        booking_id=result.get("confirmation_number", ""),
        confirmation_number=result.get("confirmation_number"),
        patient_name=booking.patient_name,
        patient_phone=booking.patient_phone,
        appointment_time=appointment_time,
        visit_type=booking.visit_type,
        provider="Dr. Kamal",
        status="confirmed",
        booked_via="admin",
        notes=booking.notes
    )


@router.delete("/appointments/{booking_id}")
async def cancel_appointment(booking_id: str, reason: Optional[str] = None):
    """Cancel an appointment."""
    firebase = get_firebase_client()

    # Check if appointment exists
    appt = await firebase.get_appointment(booking_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    await firebase.cancel_appointment(booking_id, reason)

    return {"status": "cancelled", "booking_id": booking_id}


@router.get("/slots", response_model=List[SlotResponse])
async def get_available_slots(
    date: Optional[str] = Query(None, description="Specific Date (YYYY-MM-DD)"),
    start: Optional[str] = Query(None, description="Start Date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End Date (YYYY-MM-DD)"),
    visit_type: str = Query(default="general")
):
    """
    Get all slots (available and booked) for a specific date or date range.
    Provide either 'date' OR 'start' and 'end'.
    """
    firebase = get_firebase_client()
    booking_service = get_booking_service(firebase)

    try:
        if date:
            start_date = datetime.strptime(date, "%Y-%m-%d").date()
            end_date = start_date
        elif start and end:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        else:
             # Default to today if nothing provided
            start_date = datetime.now().date()
            end_date = start_date

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    all_slots = []
    
    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        day_slots = await booking_service.get_slots_for_date(current_date, language="en")
        all_slots.extend(day_slots)
        current_date += timedelta(days=1)

    return [
        SlotResponse(
            slot_id=slot.get("slot_id", ""),
            datetime=slot.get("datetime", ""),
            time_formatted=slot.get("time_formatted", ""),
            provider=slot.get("provider", "Dr. Kamal"),
            duration_minutes=slot.get("duration_minutes", 30),
            is_available=slot.get("is_available", True),
            formatted_datetime=slot.get("formatted_datetime")
        )
        for slot in all_slots
    ]


@router.get("/calendar", response_model=List[CalendarDayData])
async def get_calendar_data(
    month: str = Query(..., description="Month (YYYY-MM)")
):
    """Get calendar summary for a month (appointments count per day)."""
    firebase = get_firebase_client()
    booking_service = get_booking_service(firebase)

    try:
        year, month_num = map(int, month.split("-"))
        start_date = datetime(year, month_num, 1)

        # Calculate end of month
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    # Get all appointments for the month
    appointments = await firebase.get_appointments(start_date, end_date.replace(hour=23, minute=59))

    # Generate calendar data for each day
    calendar_data = []
    current_date = start_date.date()

    # Timezone handling for accurate day grouping
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Montreal")
    except ImportError:
        import pytz
        tz = pytz.timezone("America/Montreal")

    # Build appointment count by date with timezone adjustment
    # Only count confirmed appointments (skip cancelled ones)
    appt_by_date = {}
    for appt in appointments:
        # Skip cancelled appointments in the count
        if appt.get("status") == "cancelled":
            continue
        appt_time = appt.get("appointment_time")
        if appt_time:
            # Convert to local time if timezone aware, otherwise assume UTC and convert
            if isinstance(appt_time, datetime):
                if appt_time.tzinfo:
                    local_time = appt_time.astimezone(tz)
                else:
                    # Assume UTC if naive
                    local_time = appt_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
                date_key = local_time.date().isoformat()
            else:
                # Fallback for strings (shouldn't happen with Firestore client properly typed)
                date_key = str(appt_time)[:10]

            appt_by_date[date_key] = appt_by_date.get(date_key, 0) + 1

    while current_date <= end_date.date():
        date_str = current_date.isoformat()
        weekday = current_date.weekday()

        # Get clinic hours for this day
        hours = booking_service._get_clinic_hours_for_day(weekday)

        if hours:
            start_hour, end_hour = hours
            total_slots = ((end_hour - start_hour) * 60) // booking_service.slot_duration
        else:
            total_slots = 0

        appt_count = appt_by_date.get(date_str, 0)

        calendar_data.append(CalendarDayData(
            date=date_str,
            day_of_week=weekday,
            appointment_count=appt_count,
            total_slots=total_slots,
            available_slots=max(0, total_slots - appt_count)
        ))

        current_date += timedelta(days=1)

    return calendar_data


class AppointmentDetails(AppointmentResponse):
    """Detailed appointment info including transcript."""
    call_transcript: Optional[List[TranscriptEntry]] = None
    call_duration: Optional[int] = None
    call_recording_url: Optional[str] = None


@router.get("/appointments/{booking_id}/details", response_model=AppointmentDetails)
async def get_appointment_details(booking_id: str):
    """Get full appointment details including call transcript."""
    firebase = get_firebase_client()
    
    # Get appointment
    appt = await firebase.get_appointment(booking_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    response = AppointmentDetails(
        booking_id=appt.get("booking_id", ""),
        confirmation_number=appt.get("confirmation_number"),
        patient_name=appt.get("patient_name", "Unknown"),
        patient_phone=appt.get("patient_phone", ""),
        appointment_time=appt.get("appointment_time"),
        visit_type=appt.get("visit_type", "general"),
        provider=appt.get("provider", "Dr. Kamal"),
        status=appt.get("status", "confirmed"),
        booked_via=appt.get("booked_via", "ai"),
        notes=appt.get("notes"),
        created_at=appt.get("created_at")
    )
    
    # Try to find associated call
    call_sid = appt.get("call_sid")
    if call_sid:
        # Get Call details
        call = await firebase.get_call(call_sid)
        if call:
            response.call_duration = call.get("duration_seconds")
            response.call_recording_url = call.get("recording_url")
            
        # Get Transcript
        transcript_data = await firebase.get_transcript(call_sid)
        response.call_transcript = [
            TranscriptEntry(
                speaker=entry.get("speaker", "unknown"),
                text=entry.get("text", ""),
                timestamp=entry.get("timestamp")
            )
            for entry in transcript_data
        ]
        
    return response
