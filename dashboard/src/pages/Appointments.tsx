import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addMonths, subMonths, addWeeks, subWeeks, addDays, subDays } from 'date-fns'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { API_URL } from '../config'
import {
  ViewToggle,
  CalendarView,
  MonthGrid,
  WeekView,
  DayView,
  Appointment,
  NewBookingModal,
  BookingFormData
} from '../components/calendar'

interface Slot {
  slot_id: string
  datetime: string
  time_formatted: string
  provider: string
  duration_minutes: number
  is_available: boolean
}

interface CalendarDay {
  date: string
  day_of_week: number
  appointment_count: number
  total_slots: number
  available_slots: number
}

// API functions
async function fetchAppointments(start: string, end: string): Promise<Appointment[]> {
  const res = await fetch(`${API_URL}/api/admin/appointments?start=${start}&end=${end}`)
  if (!res.ok) throw new Error('Failed to fetch appointments')
  return res.json()
}

async function fetchSlots(start: string, end: string): Promise<Slot[]> {
  const res = await fetch(`${API_URL}/api/admin/slots?start=${start}&end=${end}`)
  if (!res.ok) throw new Error('Failed to fetch slots')
  return res.json()
}

async function fetchCalendarData(month: string): Promise<CalendarDay[]> {
  const res = await fetch(`${API_URL}/api/admin/calendar?month=${month}`)
  if (!res.ok) throw new Error('Failed to fetch calendar data')
  return res.json()
}

async function createAppointment(data: BookingFormData): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/appointments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error('Failed to create appointment')
}

function Appointments() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<CalendarView>('week')
  const [currentDate, setCurrentDate] = useState(new Date())
  const [bookingModal, setBookingModal] = useState<{ slot: Slot; date: Date } | null>(null)

  // Calculate date ranges based on view
  const dateRange = useMemo(() => {
    if (view === 'month') {
      const start = startOfMonth(currentDate)
      const end = endOfMonth(currentDate)
      return {
        start: format(start, 'yyyy-MM-dd'),
        end: format(end, 'yyyy-MM-dd'),
        month: format(currentDate, 'yyyy-MM')
      }
    } else if (view === 'week') {
      const start = startOfWeek(currentDate, { weekStartsOn: 0 })
      const end = endOfWeek(currentDate, { weekStartsOn: 0 })
      return {
        start: format(start, 'yyyy-MM-dd'),
        end: format(end, 'yyyy-MM-dd'),
        month: format(currentDate, 'yyyy-MM')
      }
    } else {
      return {
        start: format(currentDate, 'yyyy-MM-dd'),
        end: format(currentDate, 'yyyy-MM-dd'),
        month: format(currentDate, 'yyyy-MM')
      }
    }
  }, [view, currentDate])

  // Fetch appointments for current view
  const { data: appointments = [], isLoading: loadingAppointments, refetch: refetchAppointments } = useQuery({
    queryKey: ['appointments', dateRange.start, dateRange.end],
    queryFn: () => fetchAppointments(dateRange.start, dateRange.end),
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  // Fetch calendar data for month view
  const { data: calendarData = [] } = useQuery({
    queryKey: ['calendar', dateRange.month],
    queryFn: () => fetchCalendarData(dateRange.month),
    enabled: view === 'month'
  })

  // Fetch slots for day/week view
  const { data: slots = [] } = useQuery({
    queryKey: ['slots', dateRange.start, dateRange.end],
    queryFn: () => fetchSlots(dateRange.start, dateRange.end),
    enabled: view === 'day' || view === 'week'
  })

  // Create appointment mutation
  const createMutation = useMutation({
    mutationFn: createAppointment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['slots'] })
    }
  })

  // Navigation handlers
  const goToPrevious = () => {
    if (view === 'month') setCurrentDate(subMonths(currentDate, 1))
    else if (view === 'week') setCurrentDate(subWeeks(currentDate, 1))
    else setCurrentDate(subDays(currentDate, 1))
  }

  const goToNext = () => {
    if (view === 'month') setCurrentDate(addMonths(currentDate, 1))
    else if (view === 'week') setCurrentDate(addWeeks(currentDate, 1))
    else setCurrentDate(addDays(currentDate, 1))
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  // View title
  const viewTitle = useMemo(() => {
    if (view === 'month') {
      return format(currentDate, 'MMMM yyyy')
    } else if (view === 'week') {
      const start = startOfWeek(currentDate, { weekStartsOn: 0 })
      const end = endOfWeek(currentDate, { weekStartsOn: 0 })
      return `${format(start, 'MMM d')} - ${format(end, 'MMM d, yyyy')}`
    } else {
      return format(currentDate, 'EEEE, MMMM d, yyyy')
    }
  }, [view, currentDate])

  // Handle day click from month view
  const handleDayClick = (date: Date) => {
    setCurrentDate(date)
    setView('day')
  }

  // Handle slot click for booking
  const handleSlotClick = (slot: Slot, date?: Date) => {
    setBookingModal({ slot, date: date || currentDate })
  }

  // Handle appointment click
  const handleAppointmentClick = (appointment: Appointment) => {
    // Could open a detail modal here in the future
    console.log('Appointment clicked:', appointment)
  }

  // Handle booking submit
  const handleBookingSubmit = async (data: BookingFormData) => {
    await createMutation.mutateAsync(data)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
          <p className="text-gray-500 mt-1">
            Manage appointments and availability
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => refetchAppointments()}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5 text-gray-500" />
          </button>
          <ViewToggle view={view} onViewChange={setView} />
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrevious}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goToNext}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
            <button
              onClick={goToToday}
              className="px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
            >
              Today
            </button>
          </div>

          <h2 className="text-lg font-semibold text-gray-900">
            {viewTitle}
          </h2>

          <div className="text-sm text-gray-500">
            {loadingAppointments ? (
              'Loading...'
            ) : (
              `${appointments.length} appointment${appointments.length !== 1 ? 's' : ''}`
            )}
          </div>
        </div>
      </div>

      {/* Calendar Views */}
      {view === 'month' && (
        <MonthGrid
          currentDate={currentDate}
          calendarData={calendarData}
          onDayClick={handleDayClick}
        />
      )}

      {view === 'week' && (
        <WeekView
          currentDate={currentDate}
          appointments={appointments}
          slots={slots}
          onSlotClick={handleSlotClick}
          onAppointmentClick={handleAppointmentClick}
        />
      )}

      {view === 'day' && (
        <DayView
          currentDate={currentDate}
          appointments={appointments.filter(apt => {
            const aptDate = format(new Date(apt.appointment_time), 'yyyy-MM-dd')
            return aptDate === format(currentDate, 'yyyy-MM-dd')
          })}
          slots={slots}
          onSlotClick={handleSlotClick}
          onAppointmentClick={handleAppointmentClick}
        />
      )}

      {/* Booking Modal */}
      {bookingModal && (
        <NewBookingModal
          slot={bookingModal.slot}
          date={bookingModal.date}
          onClose={() => setBookingModal(null)}
          onSubmit={handleBookingSubmit}
        />
      )}
    </div>
  )
}

export default Appointments
