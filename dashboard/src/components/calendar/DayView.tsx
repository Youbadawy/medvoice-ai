import { format } from 'date-fns'
import clsx from 'clsx'
import { AppointmentCard, Appointment } from './AppointmentCard'
import { Clock, Plus } from 'lucide-react'

interface Slot {
  slot_id: string
  datetime: string
  time_formatted: string
  provider: string
  duration_minutes: number
  is_available: boolean
}

interface DayViewProps {
  currentDate: Date
  appointments: Appointment[]
  slots: Slot[]
  onSlotClick: (slot: Slot) => void
  onAppointmentClick: (appointment: Appointment) => void
}

export function DayView({
  currentDate,
  appointments,
  slots,
  onSlotClick,
  onAppointmentClick
}: DayViewProps) {
  const isWeekend = currentDate.getDay() === 0 || currentDate.getDay() === 6

  // Create a combined timeline from slots and appointments
  const appointmentsBySlotId = new Map<string, Appointment>()
  appointments.forEach(apt => {
    const slotId = format(new Date(apt.appointment_time), 'yyyyMMddHHmm')
    appointmentsBySlotId.set(slotId, apt)
  })

  if (isWeekend) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <div className="text-gray-400 mb-2">
          <Clock className="w-12 h-12 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-gray-700">Clinic Closed</h3>
        <p className="text-gray-500 mt-1">
          The clinic is closed on {format(currentDate, 'EEEE')}s
        </p>
      </div>
    )
  }

  if (slots.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <div className="text-gray-400 mb-2">
          <Clock className="w-12 h-12 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-gray-700">No Slots Available</h3>
        <p className="text-gray-500 mt-1">
          No appointment slots for this day
        </p>
      </div>
    )
  }

  // Count stats
  const totalSlots = slots.length
  const availableSlots = slots.filter(s => s.is_available).length
  const bookedSlots = totalSlots - availableSlots

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Day header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {format(currentDate, 'EEEE, MMMM d, yyyy')}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {slots[0]?.provider || 'Dr. Kamal'}
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-gray-600">{availableSlots} available</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-gray-600">{bookedSlots} booked</span>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="divide-y divide-gray-100">
        {slots.map(slot => {
          const appointment = appointmentsBySlotId.get(slot.slot_id)

          return (
            <div key={slot.slot_id} className="flex">
              {/* Time column */}
              <div className="w-24 flex-shrink-0 p-4 text-right border-r border-gray-200 bg-gray-50">
                <div className="text-sm font-medium text-gray-900">
                  {slot.time_formatted}
                </div>
                <div className="text-xs text-gray-500">
                  {slot.duration_minutes} min
                </div>
              </div>

              {/* Content column */}
              <div className="flex-1 p-4">
                {appointment ? (
                  <AppointmentCard
                    appointment={appointment}
                    onClick={() => onAppointmentClick(appointment)}
                  />
                ) : slot.is_available ? (
                  <button
                    onClick={() => onSlotClick(slot)}
                    className={clsx(
                      'w-full p-4 border-2 border-dashed border-gray-200 rounded-lg',
                      'text-gray-400 hover:text-primary-600 hover:border-primary-300',
                      'hover:bg-primary-50 transition-colors',
                      'flex items-center justify-center gap-2'
                    )}
                  >
                    <Plus className="w-5 h-5" />
                    <span className="text-sm font-medium">Book Appointment</span>
                  </button>
                ) : (
                  <div className="p-4 bg-gray-50 rounded-lg text-gray-400 text-sm text-center">
                    Unavailable
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
