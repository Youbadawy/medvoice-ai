import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download } from 'lucide-react'
import CallList from '../components/CallList'
import TranscriptView from '../components/TranscriptView'

import { API_URL } from '../config'

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

function Calls() {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: calls, isLoading } = useQuery<Call[]>({
    queryKey: ['calls'],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/api/admin/calls`)
      if (!res.ok) throw new Error('Failed to fetch calls')
      return res.json()
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Calls</h1>
          <p className="text-gray-500 mt-1">View and manage call history</p>
        </div>
        <button className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
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
          <Filter className="w-5 h-5 text-gray-400 hidden sm:block" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-auto px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
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
        {/* Call List */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Call History ({filteredCalls?.length || 0})
          </h2>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <CallList
              calls={filteredCalls || []}
              onSelectCall={setSelectedCallId}
              selectedCallId={selectedCallId}
            />
          )}
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
