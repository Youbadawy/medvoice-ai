import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, isWeekend } from 'date-fns'
import clsx from 'clsx'

interface CalendarDay {
  date: string
  day_of_week: number
  appointment_count: number
  total_slots: number
  available_slots: number
}

interface MonthGridProps {
  currentDate: Date
  calendarData: CalendarDay[]
  onDayClick: (date: Date) => void
}

export function MonthGrid({ currentDate, calendarData, onDayClick }: MonthGridProps) {
  const monthStart = startOfMonth(currentDate)
  const monthEnd = endOfMonth(currentDate)
  const startDate = startOfWeek(monthStart, { weekStartsOn: 0 })
  const endDate = endOfWeek(monthEnd, { weekStartsOn: 0 })

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  // Build a map of date -> calendar data
  const dataByDate = new Map<string, CalendarDay>()
  calendarData.forEach(day => {
    dataByDate.set(day.date, day)
  })

  const rows = []
  let days = []
  let day = startDate

  while (day <= endDate) {
    for (let i = 0; i < 7; i++) {
      const dateStr = format(day, 'yyyy-MM-dd')
      const dayData = dataByDate.get(dateStr)
      const isCurrentMonth = isSameMonth(day, currentDate)
      const isToday = isSameDay(day, new Date())
      const isWeekendDay = isWeekend(day)
      const dayCopy = new Date(day)

      days.push(
        <div
          key={dateStr}
          onClick={() => isCurrentMonth && onDayClick(dayCopy)}
          className={clsx(
            'min-h-[100px] p-2 border-b border-r border-gray-200 transition-colors',
            isCurrentMonth ? 'cursor-pointer hover:bg-gray-50' : 'bg-gray-50 cursor-default',
            isToday && 'bg-primary-50'
          )}
        >
          {/* Day Number */}
          <div className={clsx(
            'text-sm font-medium mb-1',
            isToday && 'text-primary-700',
            !isToday && isCurrentMonth && 'text-gray-900',
            !isCurrentMonth && 'text-gray-400',
            isWeekendDay && isCurrentMonth && !isToday && 'text-gray-500'
          )}>
            {format(day, 'd')}
          </div>

          {/* Appointment indicators */}
          {isCurrentMonth && dayData && (
            <div className="space-y-1">
              {dayData.appointment_count > 0 && (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="text-xs text-gray-600">
                    {dayData.appointment_count} appt{dayData.appointment_count !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
              {dayData.available_slots > 0 && (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <span className="text-xs text-gray-500">
                    {dayData.available_slots} available
                  </span>
                </div>
              )}
              {dayData.total_slots === 0 && (
                <span className="text-xs text-gray-400">Closed</span>
              )}
            </div>
          )}
        </div>
      )
      day = addDays(day, 1)
    }
    rows.push(
      <div key={day.toISOString()} className="grid grid-cols-7">
        {days}
      </div>
    )
    days = []
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="grid grid-cols-7 bg-gray-50 border-b border-gray-200">
        {weekDays.map(dayName => (
          <div
            key={dayName}
            className="px-3 py-2 text-center text-sm font-medium text-gray-500"
          >
            {dayName}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div>
        {rows}
      </div>
    </div>
  )
}
