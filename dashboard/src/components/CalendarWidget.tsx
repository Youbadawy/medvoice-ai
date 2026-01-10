import { format } from 'date-fns'
import { Calendar, Clock, User } from 'lucide-react'

interface Appointment {
  id: string
  patient_name: string
  appointment_time: Date | string
  visit_type: string
}

interface CalendarWidgetProps {
  appointments: Appointment[]
  title?: string
}

const visitTypeColors: Record<string, string> = {
  general: 'border-l-blue-500',
  followup: 'border-l-purple-500',
  vaccination: 'border-l-green-500',
}

function CalendarWidget({ appointments, title = "Today's Appointments" }: CalendarWidgetProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <span className="text-sm text-gray-500">
          {format(new Date(), 'MMMM d, yyyy')}
        </span>
      </div>

      {appointments.length > 0 ? (
        <div className="space-y-3">
          {appointments.map((apt) => (
            <div
              key={apt.id}
              className={`flex items-center gap-4 p-3 bg-gray-50 rounded-lg border-l-4 ${visitTypeColors[apt.visit_type] || 'border-l-gray-300'}`}
            >
              <div className="flex items-center gap-1 text-sm font-medium text-gray-900 w-16">
                <Clock className="w-4 h-4 text-gray-400" />
                {format(new Date(apt.appointment_time), 'HH:mm')}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900">
                    {apt.patient_name}
                  </span>
                </div>
                <span className="text-xs text-gray-500 capitalize">
                  {apt.visit_type}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <Calendar className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p>No appointments today</p>
        </div>
      )}
    </div>
  )
}

export default CalendarWidget
