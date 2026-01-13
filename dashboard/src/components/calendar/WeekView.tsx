import { format, startOfWeek, addDays, isSameDay } from 'date-fns'
import clsx from 'clsx'
import { AppointmentCard, Appointment } from './AppointmentCard'

interface Slot {
  slot_id: string
  datetime: string
  time_formatted: string
  provider: string
  duration_minutes: number
  is_available: boolean
}

interface WeekViewProps {
  currentDate: Date
  appointments: Appointment[]
  slots: Slot[]
  onSlotClick: (slot: Slot, date: Date) => void
  onAppointmentClick: (appointment: Appointment) => void
}

// Clinic hours: 9am to 6pm
const hours = Array.from({ length: 10 }, (_, i) => 9 + i) // 9, 10, 11, 12, 13, 14, 15, 16, 17, 18

export function WeekView({
  currentDate,
  appointments,
  slots,
  onSlotClick,
  onAppointmentClick
}: WeekViewProps) {
  const weekStart = startOfWeek(currentDate, { weekStartsOn: 0 })
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))

  // Group appointments by day and time
  const appointmentsByDayTime = new Map<string, Appointment[]>()
  appointments.forEach(apt => {
    const aptTime = new Date(apt.appointment_time)
    const key = `${format(aptTime, 'yyyy-MM-dd')}-${aptTime.getHours()}-${Math.floor(aptTime.getMinutes() / 30) * 30}`
    if (!appointmentsByDayTime.has(key)) {
      appointmentsByDayTime.set(key, [])
    }
    appointmentsByDayTime.get(key)!.push(apt)
  })

  // Group slots by day
  const slotsByDay = new Map<string, Map<string, Slot>>()
  slots.forEach(slot => {
    const slotTime = new Date(slot.datetime)
    const dayKey = format(slotTime, 'yyyy-MM-dd')
    const timeKey = `${slotTime.getHours()}-${Math.floor(slotTime.getMinutes() / 30) * 30}`

    if (!slotsByDay.has(dayKey)) {
      slotsByDay.set(dayKey, new Map())
    }
    slotsByDay.get(dayKey)!.set(timeKey, slot)
  })

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header with day names */}
      <div className="grid grid-cols-8 border-b border-gray-200 bg-gray-50">
        <div className="p-3 border-r border-gray-200"></div>
        {weekDays.map(day => {
          const isToday = isSameDay(day, new Date())
          const isWeekend = day.getDay() === 0 || day.getDay() === 6
          return (
            <div
              key={day.toISOString()}
              className={clsx(
                'p-3 text-center border-r border-gray-200',
                isWeekend && 'bg-gray-100'
              )}
            >
              <div className={clsx(
                'text-xs font-medium',
                isToday ? 'text-primary-600' : 'text-gray-500'
              )}>
                {format(day, 'EEE')}
              </div>
              <div className={clsx(
                'text-lg font-semibold mt-1',
                isToday ? 'bg-primary-600 text-white rounded-full w-8 h-8 flex items-center justify-center mx-auto' : 'text-gray-900'
              )}>
                {format(day, 'd')}
              </div>
            </div>
          )
        })}
      </div>

      {/* Time grid */}
      <div className="overflow-y-auto max-h-[600px]">
        {hours.map(hour => (
          <div key={hour} className="grid grid-cols-8 border-b border-gray-100">
            {/* Time label */}
            <div className="p-2 text-xs text-gray-500 text-right pr-3 border-r border-gray-200">
              {format(new Date().setHours(hour, 0), 'h a')}
            </div>

            {/* Day columns */}
            {weekDays.map(day => {
              const dayStr = format(day, 'yyyy-MM-dd')
              const isWeekend = day.getDay() === 0 || day.getDay() === 6

              // Two 30-minute slots per hour
              return (
                <div key={day.toISOString()} className={clsx(
                  'border-r border-gray-200 min-h-[60px]',
                  isWeekend && 'bg-gray-50'
                )}>
                  {[0, 30].map(minutes => {
                    const timeKey = `${hour}-${minutes}`
                    const apptKey = `${dayStr}-${hour}-${minutes}`
                    const daySlots = slotsByDay.get(dayStr)
                    const slot = daySlots?.get(timeKey)
                    const dayAppointments = appointmentsByDayTime.get(apptKey) || []

                    if (dayAppointments.length > 0) {
                      return (
                        <div key={minutes} className="p-1 min-h-[30px]">
                          {dayAppointments.map(apt => (
                            <AppointmentCard
                              key={apt.booking_id}
                              appointment={apt}
                              compact
                              onClick={() => onAppointmentClick(apt)}
                            />
                          ))}
                        </div>
                      )
                    }

                    if (slot && slot.is_available && !isWeekend) {
                      return (
                        <div
                          key={minutes}
                          onClick={() => onSlotClick(slot, day)}
                          className="p-1 min-h-[30px] hover:bg-green-50 cursor-pointer transition-colors border-b border-gray-100 last:border-b-0"
                        >
                          <div className="text-xs text-green-600 opacity-0 hover:opacity-100">
                            + Book
                          </div>
                        </div>
                      )
                    }

                    return (
                      <div
                        key={minutes}
                        className={clsx(
                          'min-h-[30px] border-b border-gray-100 last:border-b-0',
                          isWeekend && 'bg-gray-100'
                        )}
                      />
                    )
                  })}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
