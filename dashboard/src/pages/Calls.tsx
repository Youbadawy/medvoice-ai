import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download } from 'lucide-react'
import CallList from '../components/CallList'
import TranscriptView from '../components/TranscriptView'

// Mock data
const mockCalls = [
  {
    call_id: 'CA125',
    phone_number: '+1 514-555-1234',
    language: 'fr',
    status: 'completed',
    started_at: new Date().toISOString(),
    duration_seconds: 180,
    booking_made: true,
  },
  {
    call_id: 'CA124',
    phone_number: '+1 514-555-5678',
    language: 'en',
    status: 'completed',
    started_at: new Date(Date.now() - 1800000).toISOString(),
    duration_seconds: 95,
    booking_made: false,
  },
  {
    call_id: 'CA123',
    phone_number: '+1 514-555-9999',
    language: 'fr',
    status: 'transferred',
    started_at: new Date(Date.now() - 3600000).toISOString(),
    duration_seconds: 45,
    booking_made: false,
    transferred: true,
  },
  {
    call_id: 'CA122',
    phone_number: '+1 514-555-4444',
    language: 'fr',
    status: 'completed',
    started_at: new Date(Date.now() - 7200000).toISOString(),
    duration_seconds: 210,
    booking_made: true,
  },
]

function Calls() {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: calls } = useQuery({
    queryKey: ['calls'],
    queryFn: async () => {
      // TODO: Replace with actual API call
      return mockCalls
    },
  })

  const filteredCalls = calls?.filter(call => {
    const matchesSearch = call.phone_number.includes(searchQuery) ||
                         call.call_id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || call.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calls</h1>
          <p className="text-gray-500 mt-1">View and manage call history</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by phone or call ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="active">Active</option>
            <option value="transferred">Transferred</option>
          </select>
        </div>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Call List */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Call History ({filteredCalls?.length || 0})
          </h2>
          <CallList
            calls={filteredCalls || []}
            onSelectCall={setSelectedCallId}
            selectedCallId={selectedCallId}
          />
        </div>

        {/* Transcript */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Transcript
          </h2>
          {selectedCallId ? (
            <TranscriptView callId={selectedCallId} />
          ) : (
            <div className="text-center py-12 text-gray-500">
              <p>Select a call to view transcript</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Calls
