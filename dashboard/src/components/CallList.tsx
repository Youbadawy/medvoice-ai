import { format, formatDistanceToNow } from 'date-fns'
import { Phone, PhoneOff, ArrowRightLeft, Calendar, Clock } from 'lucide-react'
import clsx from 'clsx'
import StatusBadge from './StatusBadge'

interface Call {
  call_id: string
  phone_number: string
  language: string
  status: string
  started_at: string
  duration_seconds?: number
  booking_made?: boolean
  transferred?: boolean
}

interface CallListProps {
  calls: Call[]
  onSelectCall?: (callId: string) => void
  selectedCallId?: string | null
  showTranscript?: boolean
}

function CallList({ calls, onSelectCall, selectedCallId, showTranscript: _showTranscript }: CallListProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Phone className="w-4 h-4 text-primary-500" />
      case 'transferred':
        return <ArrowRightLeft className="w-4 h-4 text-indigo-500" />
      default:
        return <PhoneOff className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (call: Call) => {
    if (call.status === 'active') return <StatusBadge status="active" />
    if (call.transferred) return <StatusBadge status="transferred" />
    if (call.booking_made) return (
      <span className="inline-flex items-center gap-1.5 border rounded-full font-medium transition-colors bg-teal-50 text-teal-700 border-teal-200 px-2.5 py-0.5 text-xs">
        <Calendar className="w-3 h-3" />
        Booked
      </span>
    )

    return <StatusBadge status={call.status} />
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${String(secs).padStart(2, '0')}`
  }

  if (calls.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Phone className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No calls to display</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {calls.map((call) => (
        <div
          key={call.call_id}
          onClick={() => onSelectCall?.(call.call_id)}
          className={clsx(
            'p-4 rounded-lg border transition-all cursor-pointer',
            selectedCallId === call.call_id
              ? 'border-primary-300 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300 bg-white'
          )}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getStatusIcon(call.status)}
              <div>
                <div className="font-medium text-gray-900">
                  {call.phone_number}
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                  <span className="uppercase text-xs font-medium px-1.5 py-0.5 bg-gray-100 rounded">
                    {call.language}
                  </span>
                  <span>•</span>
                  <span>
                    {call.status === 'active'
                      ? formatDistanceToNow(new Date(call.started_at), { addSuffix: false }) + ' ago'
                      : format(new Date(call.started_at), 'h:mm a')}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {call.duration_seconds && (
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <Clock className="w-4 h-4" />
                  {formatDuration(call.duration_seconds)}
                </div>
              )}
              {getStatusBadge(call)}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default CallList
