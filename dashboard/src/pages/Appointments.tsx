import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addMonths, subMonths, addWeeks, subWeeks, addDays, subDays } from 'date-fns'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
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
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null)

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
    setSelectedAppointment(appointment)
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

      {/* Details Modal */}
      {selectedAppointment && (
        <BookingDetailsModal
          appointment={selectedAppointment}
          onClose={() => setSelectedAppointment(null)}
        />
      )}
    </div>
  )
}

function BookingDetailsModal({ appointment, onClose }: { appointment: Appointment; onClose: () => void }) {
  const { data: details, isLoading } = useQuery({
    queryKey: ['appointment', appointment.booking_id, 'details'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/admin/appointments/${appointment.booking_id}/details`)
      if (!res.ok) throw new Error('Failed to fetch details')
      return res.json()
    }
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="p-6 border-b flex justify-between items-center bg-gray-50 rounded-t-xl">
          <h2 className="text-xl font-bold">Appointment Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6">
          {/* Header Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-500">Patient</label>
              <div className="text-lg font-semibold">{appointment.patient_name}</div>
              <div className="text-sm text-gray-600">{appointment.patient_phone}</div>
            </div>
            <div className="text-right">
              <div className={clsx(
                'inline-block px-3 py-1 rounded-full text-sm font-medium',
                appointment.status === 'cancelled'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-green-100 text-green-800'
              )}>
                {appointment.status.toUpperCase()}
              </div>
              <div className="mt-1 text-sm text-gray-500">
                {appointment.formatted_datetime || format(new Date(appointment.appointment_time), 'PPp')}
              </div>
            </div>
          </div>

          <hr />

          {/* Notes */}
          {appointment.notes && (
            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100">
              <h3 className="text-sm font-semibold text-yellow-900 mb-1">Medical Notes / RAMQ</h3>
              <p className="text-gray-800">{appointment.notes}</p>
            </div>
          )}

          {/* Transcript Section */}
          <div>
            <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
              <span>Call Transcript</span>
              {isLoading && <span className="text-xs font-normal text-gray-500">(Loading...)</span>}
            </h3>

            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 max-h-[300px] overflow-y-auto space-y-3">
              {isLoading ? (
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse"></div>
                </div>
              ) : details?.call_transcript && details.call_transcript.length > 0 ? (
                details.call_transcript.map((entry: any, i: number) => (
                  <div key={i} className={`flex ${entry.speaker === 'user' || entry.speaker === 'caller' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg p-3 ${entry.speaker === 'user' || entry.speaker === 'caller'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-white border border-gray-200 shadow-sm rounded-bl-none'
                      }`}>
                      <div className={`text-xs mb-1 opacity-70 ${entry.speaker === 'user' || entry.speaker === 'caller' ? 'text-blue-100' : 'text-gray-500'
                        }`}>
                        {entry.speaker === 'user' || entry.speaker === 'caller' ? 'Patient' : 'Agent'}
                      </div>
                      <div>{entry.text}</div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center">
                  {appointment.booked_via === 'admin'
                    ? 'Manual booking - no call transcript available.'
                    : 'No transcript available for this booking.'}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="p-4 border-t bg-gray-50 rounded-b-xl flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default Appointments
