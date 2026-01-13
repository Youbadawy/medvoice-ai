import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { User, Bot, Volume2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { API_URL } from '../config'

interface TranscriptEntry {
  speaker: 'caller' | 'assistant'
  text: string
  timestamp: string
  language?: string
}

interface TranscriptViewProps {
  callId: string
  isActiveCall?: boolean
}

function TranscriptView({ callId, isActiveCall = true }: TranscriptViewProps) {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [isLive, setIsLive] = useState(isActiveCall)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Fetch transcript from API
  const fetchTranscript = async () => {
    if (!callId) return

    try {
      const response = await fetch(`${API_URL}/api/admin/calls/${callId}/transcript`)
      if (!response.ok) {
        throw new Error('Failed to fetch transcript')
      }
      const data = await response.json()
      setTranscript(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching transcript:', err)
      setError('Failed to load transcript')
    } finally {
      setIsLoading(false)
    }
  }

  // Update isLive when isActiveCall prop changes
  useEffect(() => {
    setIsLive(isActiveCall)
  }, [isActiveCall])

  // Initial fetch and polling
  useEffect(() => {
    setIsLoading(true)
    fetchTranscript()

    // Poll every 2 seconds for live updates (only for active calls)
    if (isLive && isActiveCall) {
      const interval = setInterval(fetchTranscript, 2000)
      return () => clearInterval(interval)
    }
  }, [callId, isLive, isActiveCall])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcript])

  return (
    <div className="h-96 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-200">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Call ID: {callId.slice(0, 12)}...</span>
          {isLive && (
            <span className="flex items-center gap-1 text-green-600">
              <span className="w-2 h-2 bg-green-500 rounded-full pulse" />
              Live
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchTranscript}
            className="p-2 rounded-lg bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
            title="Refresh transcript"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsLive(!isLive)}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              isLive ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'
            )}
            title={isLive ? 'Pause live updates' : 'Resume live updates'}
          >
            <Volume2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Transcript */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 space-y-4"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            Loading transcript...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500">
            {error}
          </div>
        ) : transcript.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            No transcript available yet. Waiting for conversation...
          </div>
        ) : (
          transcript.map((entry, index) => (
            <div
              key={index}
              className={clsx(
                'flex gap-3 transcript-entry',
                entry.speaker === 'caller' ? 'justify-start' : 'justify-end'
              )}
            >
              {entry.speaker === 'caller' && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-gray-600" />
                </div>
              )}

              <div className={clsx(
                'max-w-[75%] rounded-2xl px-4 py-2',
                entry.speaker === 'caller'
                  ? 'bg-gray-100 text-gray-900 rounded-bl-sm'
                  : 'bg-primary-600 text-white rounded-br-sm'
              )}>
                <p className="text-sm">{entry.text}</p>
                <p className={clsx(
                  'text-xs mt-1',
                  entry.speaker === 'caller' ? 'text-gray-500' : 'text-primary-200'
                )}>
                  {format(new Date(entry.timestamp), 'h:mm:ss a')}
                  {entry.language && ` • ${entry.language.toUpperCase()}`}
                </p>
              </div>

              {entry.speaker === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default TranscriptView
