import { format } from 'date-fns'
import { User, Phone, Bot, UserCog } from 'lucide-react'
import clsx from 'clsx'

export interface Appointment {
  booking_id: string
  confirmation_number?: string
  patient_name: string
  patient_phone: string
  appointment_time: string
  visit_type: string
  provider: string
  status: string
  booked_via: string
  notes?: string
  formatted_datetime?: string
}

interface AppointmentCardProps {
  appointment: Appointment
  compact?: boolean
  onClick?: () => void
}

const visitTypeLabels: Record<string, string> = {
  general: 'General',
  followup: 'Follow-up',
  vaccination: 'Vaccination',
}

const visitTypeColors: Record<string, string> = {
  general: 'bg-blue-100 text-blue-700 border-blue-200',
  followup: 'bg-purple-100 text-purple-700 border-purple-200',
  vaccination: 'bg-green-100 text-green-700 border-green-200',
}

const bookedViaColors: Record<string, string> = {
  ai: 'bg-accent-100 text-accent-700',
  admin: 'bg-gray-100 text-gray-700',
}

export function AppointmentCard({ appointment, compact = false, onClick }: AppointmentCardProps) {
  const time = new Date(appointment.appointment_time)

  if (compact) {
    return (
      <div
        onClick={onClick}
        className={clsx(
          'text-xs p-1.5 rounded cursor-pointer truncate border-l-2',
          appointment.booked_via === 'ai' ? 'bg-blue-50 border-blue-500' : 'bg-purple-50 border-purple-500',
          appointment.status === 'cancelled' && 'opacity-50 line-through'
        )}
      >
        <span className="font-medium">{format(time, 'h:mm a')}</span>
        <span className="ml-1 text-gray-600">{appointment.patient_name.split(' ')[0]}</span>
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={clsx(
        'p-4 rounded-lg border transition-all cursor-pointer',
        appointment.status === 'cancelled'
          ? 'bg-red-50 border-red-200 opacity-70'
          : 'bg-white border-gray-200 hover:border-primary-300 hover:shadow-sm'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Time */}
          <div className="text-lg font-semibold text-gray-900">
            {format(time, 'h:mm a')}
          </div>

          {/* Patient Name */}
          <div className="flex items-center gap-2 mt-2">
            <User className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="font-medium text-gray-900 truncate">
              {appointment.patient_name}
            </span>
          </div>

          {/* Phone */}
          <div className="flex items-center gap-2 mt-1">
            <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="text-sm text-gray-500">
              {appointment.patient_phone}
            </span>
          </div>

          {/* Notes */}
          {appointment.notes && (
            <div className="mt-2 text-sm text-gray-500 italic">
              {appointment.notes}
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          {/* Visit Type */}
          <span className={clsx(
            'px-2 py-1 rounded-full text-xs font-medium border',
            visitTypeColors[appointment.visit_type] || 'bg-gray-100 text-gray-700 border-gray-200'
          )}>
            {visitTypeLabels[appointment.visit_type] || appointment.visit_type}
          </span>

          {/* Booked Via */}
          <span className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium',
            bookedViaColors[appointment.booked_via]
          )}>
            {appointment.booked_via === 'ai' ? (
              <>
                <Bot className="w-3 h-3" />
                AI Booked
              </>
            ) : (
              <>
                <UserCog className="w-3 h-3" />
                Admin
              </>
            )}
          </span>
        </div>
      </div>
    </div>
  )
}
