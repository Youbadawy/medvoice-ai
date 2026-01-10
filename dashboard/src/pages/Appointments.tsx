import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, addDays, startOfWeek } from 'date-fns'
import { ChevronLeft, ChevronRight, Calendar, User } from 'lucide-react'
import clsx from 'clsx'

// Mock appointments
const mockAppointments = [
  {
    id: '1',
    patient_name: 'Marie Tremblay',
    patient_phone: '+1 514-555-1234',
    appointment_time: new Date().setHours(9, 0),
    visit_type: 'general',
    status: 'confirmed',
    booked_via: 'ai',
  },
  {
    id: '2',
    patient_name: 'Jean-Pierre Lavoie',
    patient_phone: '+1 514-555-5678',
    appointment_time: new Date().setHours(10, 30),
    visit_type: 'followup',
    status: 'confirmed',
    booked_via: 'ai',
  },
  {
    id: '3',
    patient_name: 'Sarah Johnson',
    patient_phone: '+1 514-555-9999',
    appointment_time: new Date().setHours(14, 0),
    visit_type: 'vaccination',
    status: 'confirmed',
    booked_via: 'ai',
  },
]

const visitTypeLabels: Record<string, string> = {
  general: 'Examen général',
  followup: 'Suivi',
  vaccination: 'Vaccination',
}

const visitTypeColors: Record<string, string> = {
  general: 'bg-blue-100 text-blue-700',
  followup: 'bg-purple-100 text-purple-700',
  vaccination: 'bg-green-100 text-green-700',
}

function Appointments() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const weekStart = startOfWeek(currentDate, { weekStartsOn: 1 })

  const { data: appointments } = useQuery({
    queryKey: ['appointments', format(currentDate, 'yyyy-MM-dd')],
    queryFn: async () => {
      // TODO: Replace with actual API call
      return mockAppointments
    },
  })

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
          <p className="text-gray-500 mt-1">
            View and manage booked appointments
          </p>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setCurrentDate(addDays(currentDate, -7))}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-lg font-semibold">
            {format(weekStart, 'MMMM d')} - {format(addDays(weekStart, 6), 'MMMM d, yyyy')}
          </h2>
          <button
            onClick={() => setCurrentDate(addDays(currentDate, 7))}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Week Days */}
        <div className="grid grid-cols-7 gap-2">
          {weekDays.map((day) => {
            const isToday = format(day, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd')
            return (
              <button
                key={day.toISOString()}
                onClick={() => setCurrentDate(day)}
                className={clsx(
                  'p-3 rounded-lg text-center transition-colors',
                  isToday && 'bg-primary-600 text-white',
                  !isToday && format(day, 'yyyy-MM-dd') === format(currentDate, 'yyyy-MM-dd') && 'bg-primary-50 text-primary-700',
                  !isToday && format(day, 'yyyy-MM-dd') !== format(currentDate, 'yyyy-MM-dd') && 'hover:bg-gray-100'
                )}
              >
                <div className="text-xs opacity-75">{format(day, 'EEE')}</div>
                <div className="text-lg font-semibold">{format(day, 'd')}</div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Appointments List */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">
            {format(currentDate, 'EEEE, MMMM d, yyyy')}
          </h2>
          <span className="text-sm text-gray-500">
            {appointments?.length || 0} appointments
          </span>
        </div>

        {appointments && appointments.length > 0 ? (
          <div className="space-y-4">
            {appointments.map((apt) => (
              <div
                key={apt.id}
                className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
              >
                {/* Time */}
                <div className="w-20 text-center">
                  <div className="text-lg font-semibold text-gray-900">
                    {format(new Date(apt.appointment_time), 'HH:mm')}
                  </div>
                </div>

                {/* Divider */}
                <div className="w-px h-12 bg-gray-200" />

                {/* Details */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-gray-900">
                      {apt.patient_name}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {apt.patient_phone}
                  </div>
                </div>

                {/* Visit Type */}
                <span className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  visitTypeColors[apt.visit_type]
                )}>
                  {visitTypeLabels[apt.visit_type]}
                </span>

                {/* Booked via AI badge */}
                {apt.booked_via === 'ai' && (
                  <span className="px-2 py-1 bg-accent-100 text-accent-700 rounded text-xs font-medium">
                    AI Booked
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No appointments for this day</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Appointments
