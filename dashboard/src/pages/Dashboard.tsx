import { useQuery } from '@tanstack/react-query'
import {
  Phone,
  Calendar,
  Clock,
  PhoneIncoming,
  CheckCircle,
  XCircle
} from 'lucide-react'
import StatsCard from '../components/StatsCard'
import CallList from '../components/CallList'
import TranscriptView from '../components/TranscriptView'

// Mock data for development
const mockStats = {
  total_calls_today: 47,
  active_calls: 2,
  bookings_made: 12,
  avg_call_duration: 145,
  success_rate: 0.89,
}

const mockActiveCalls = [
  {
    call_id: 'CA123',
    phone_number: '+1 514-555-1234',
    language: 'fr',
    status: 'active',
    started_at: new Date().toISOString(),
    duration_seconds: 45,
  },
  {
    call_id: 'CA124',
    phone_number: '+1 514-555-5678',
    language: 'en',
    status: 'active',
    started_at: new Date().toISOString(),
    duration_seconds: 120,
  },
]

const mockRecentCalls = [
  {
    call_id: 'CA120',
    phone_number: '+1 514-555-9999',
    language: 'fr',
    status: 'completed',
    started_at: new Date(Date.now() - 3600000).toISOString(),
    duration_seconds: 180,
    booking_made: true,
  },
  {
    call_id: 'CA119',
    phone_number: '+1 514-555-8888',
    language: 'en',
    status: 'completed',
    started_at: new Date(Date.now() - 7200000).toISOString(),
    duration_seconds: 95,
    booking_made: false,
  },
]

function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const res = await fetch('/api/admin/stats')
      // return res.json()
      return mockStats
    },
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of MedVoice AI activity</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Calls Today"
          value={stats?.total_calls_today || 0}
          icon={Phone}
          trend="+12% from yesterday"
          trendUp={true}
        />
        <StatsCard
          title="Active Calls"
          value={stats?.active_calls || 0}
          icon={PhoneIncoming}
          highlight={true}
        />
        <StatsCard
          title="Bookings Made"
          value={stats?.bookings_made || 0}
          icon={Calendar}
          trend="+8% from yesterday"
          trendUp={true}
        />
        <StatsCard
          title="Avg. Duration"
          value={`${Math.floor((stats?.avg_call_duration || 0) / 60)}:${String((stats?.avg_call_duration || 0) % 60).padStart(2, '0')}`}
          icon={Clock}
          suffix="min"
        />
      </div>

      {/* Success Rate */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Success Rate</h2>
          <span className="text-sm text-gray-500">Today</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
            <div
              className="bg-green-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${(stats?.success_rate || 0) * 100}%` }}
            />
          </div>
          <span className="text-2xl font-bold text-gray-900">
            {Math.round((stats?.success_rate || 0) * 100)}%
          </span>
        </div>
        <div className="flex justify-between mt-4 text-sm">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="w-4 h-4" />
            <span>Completed successfully</span>
          </div>
          <div className="flex items-center gap-2 text-gray-500">
            <XCircle className="w-4 h-4" />
            <span>Transferred or dropped</span>
          </div>
        </div>
      </div>

      {/* Active Calls & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Calls */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Active Calls
          </h2>
          {mockActiveCalls.length > 0 ? (
            <CallList calls={mockActiveCalls} showTranscript={true} />
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
          <CallList calls={mockRecentCalls} />
        </div>
      </div>

      {/* Live Transcript (for demo) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Live Transcript
        </h2>
        <TranscriptView callId="CA123" />
      </div>
    </div>
  )
}

export default Dashboard
