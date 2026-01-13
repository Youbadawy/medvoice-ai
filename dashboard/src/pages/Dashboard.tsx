import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Phone,
  Calendar,
  PhoneIncoming,
  CheckCircle,
  AlertCircle,
  MessageSquare
} from 'lucide-react'
import StatsCard from '../components/StatsCard'
import CallList from '../components/CallList'
import TranscriptView from '../components/TranscriptView'
import { API_URL, STATS_REFRESH_INTERVAL, CALLS_REFRESH_INTERVAL } from '../config'

interface Stats {
  total_calls_today: number
  active_calls: number
  bookings_made: number
  avg_call_duration: number
  success_rate: number
}

interface Call {
  call_id: string
  phone_number: string
  language: string
  status: string
  started_at: string
  ended_at?: string
  duration_seconds: number
  booking_made?: boolean
  transferred?: boolean
}

function Dashboard() {
  // State for selected call
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null)

  // Fetch stats from API
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/admin/stats`)
      if (!res.ok) throw new Error('Failed to fetch stats')
      return res.json()
    },
    refetchInterval: STATS_REFRESH_INTERVAL,
  })

  // Fetch active calls
  const { data: activeCalls, isLoading: activeCallsLoading } = useQuery<Call[]>({
    queryKey: ['activeCalls'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/admin/calls/active`)
      if (!res.ok) throw new Error('Failed to fetch active calls')
      return res.json()
    },
    refetchInterval: CALLS_REFRESH_INTERVAL,
  })

  // Fetch recent calls
  const { data: recentCalls, isLoading: recentCallsLoading } = useQuery<Call[]>({
    queryKey: ['recentCalls'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/admin/calls?limit=10`)
      if (!res.ok) throw new Error('Failed to fetch recent calls')
      return res.json()
    },
    refetchInterval: STATS_REFRESH_INTERVAL,
  })

  // Auto-select active call when one becomes active
  useEffect(() => {
    if (activeCalls && activeCalls.length > 0) {
      // Auto-select the first active call if none selected or current selection is not active
      const activeCallIds = activeCalls.map(c => c.call_id)
      if (!selectedCallId || !activeCallIds.includes(selectedCallId)) {
        setSelectedCallId(activeCalls[0].call_id)
      }
    }
  }, [activeCalls, selectedCallId])

  // Handle call selection
  const handleSelectCall = (callId: string) => {
    setSelectedCallId(callId === selectedCallId ? null : callId)
  }

  // Show error state if API fails
  if (statsError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-500">
        <AlertCircle className="w-16 h-16 mb-4 text-amber-500" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection Error</h2>
        <p className="text-center max-w-md">
          Unable to connect to the API server. Make sure the backend is running at:
        </p>
        <code className="mt-2 px-3 py-1 bg-gray-100 rounded text-sm">{API_URL}</code>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of KaiMed AI activity</p>
      </div>

      {/* Stats Grid */}
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Calls Today"
          value={statsLoading ? '...' : stats?.total_calls_today || 0}
          icon={Phone}
          trend="neutral"
          trendValue="Today"
        />
        <StatsCard
          title="Active Calls"
          value={statsLoading ? '...' : stats?.active_calls || 0}
          icon={PhoneIncoming}
          highlight={true}
          suffix="Live now"
        />
        <StatsCard
          title="Bookings Made"
          value={statsLoading ? '...' : stats?.bookings_made || 0}
          icon={Calendar}
          trend={stats && stats.bookings_made > 0 ? "up" : "neutral"}
          trendValue="Target: 10"
        />
        <StatsCard
          title="Success Rate"
          value={statsLoading ? '...' : `${Math.round((stats?.success_rate || 0) * 100)}%`}
          icon={CheckCircle}
          trend={stats && stats.success_rate > 0.8 ? "up" : "down"}
          trendValue="Goal: 80%"
        />
      </div>

      {/* Active Calls & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Calls */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Active Calls
            {activeCalls && activeCalls.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                {activeCalls.length} live
              </span>
            )}
          </h2>
          {activeCallsLoading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : activeCalls && activeCalls.length > 0 ? (
            <CallList
              calls={activeCalls}
              onSelectCall={handleSelectCall}
              selectedCallId={selectedCallId}
            />
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Phone className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No active calls</p>
            </div>
          )}
        </div>

        {/* Recent Calls */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Calls
          </h2>
          {recentCallsLoading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : recentCalls && recentCalls.length > 0 ? (
            <CallList
              calls={recentCalls}
              onSelectCall={handleSelectCall}
              selectedCallId={selectedCallId}
            />
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Phone className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No recent calls</p>
            </div>
          )}
        </div>
      </div>

      {/* Transcript View - show for any selected call */}
      {selectedCallId && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">
              {activeCalls?.some(c => c.call_id === selectedCallId) ? 'Live Transcript' : 'Call Transcript'}
            </h2>
            {activeCalls?.some(c => c.call_id === selectedCallId) && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full pulse" />
                Live
              </span>
            )}
          </div>
          <TranscriptView
            callId={selectedCallId}
            isActiveCall={activeCalls?.some(c => c.call_id === selectedCallId) ?? false}
          />
        </div>
      )}
    </div>
  )
}

export default Dashboard
