import { useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { User, Bot, Volume2 } from 'lucide-react'
import clsx from 'clsx'

interface TranscriptEntry {
  speaker: 'caller' | 'assistant'
  text: string
  timestamp: string
  language?: string
}

interface TranscriptViewProps {
  callId: string
}

// Mock transcript data for demo
const mockTranscript: TranscriptEntry[] = [
  {
    speaker: 'assistant',
    text: 'Bonjour, Clinique Médicale Saint-Laurent, comment puis-je vous aider?',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'caller',
    text: 'Bonjour, je voudrais prendre un rendez-vous s\'il vous plaît.',
    timestamp: new Date(Date.now() - 110000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'assistant',
    text: 'Certainement! Quel type de visite souhaitez-vous? Un examen général, un suivi, ou une vaccination?',
    timestamp: new Date(Date.now() - 100000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'caller',
    text: 'Un examen général.',
    timestamp: new Date(Date.now() - 90000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'assistant',
    text: 'Parfait. Voici les prochaines disponibilités: Premier, mardi le 15 janvier à 10h. Deuxième, mardi le 15 janvier à 14h30. Troisième, mercredi le 16 janvier à 9h. Lequel préférez-vous?',
    timestamp: new Date(Date.now() - 80000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'caller',
    text: 'Le premier, s\'il vous plaît.',
    timestamp: new Date(Date.now() - 70000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'assistant',
    text: 'Excellent choix. Puis-je avoir votre nom complet?',
    timestamp: new Date(Date.now() - 60000).toISOString(),
    language: 'fr'
  },
  {
    speaker: 'caller',
    text: 'Marie Tremblay.',
    timestamp: new Date(Date.now() - 50000).toISOString(),
    language: 'fr'
  },
]

function TranscriptView({ callId }: TranscriptViewProps) {
  const [transcript, setTranscript] = useState<TranscriptEntry[]>(mockTranscript)
  const [isLive, setIsLive] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcript])

  // Simulate live transcript updates (for demo)
  useEffect(() => {
    if (!isLive) return

    const interval = setInterval(() => {
      // Add a random new message occasionally for demo
      const random = Math.random()
      if (random > 0.8) {
        const newEntry: TranscriptEntry = {
          speaker: random > 0.9 ? 'caller' : 'assistant',
          text: random > 0.9
            ? '514-555-1234.'
            : 'Et votre numéro de téléphone?',
          timestamp: new Date().toISOString(),
          language: 'fr'
        }
        setTranscript(prev => [...prev, newEntry])
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [isLive])

  return (
    <div className="h-96 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-200">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Call ID: {callId}</span>
          {isLive && (
            <span className="flex items-center gap-1 text-green-600">
              <span className="w-2 h-2 bg-green-500 rounded-full pulse" />
              Live
            </span>
          )}
        </div>
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

      {/* Transcript */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 space-y-4"
      >
        {transcript.map((entry, index) => (
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
              </p>
            </div>

            {entry.speaker === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default TranscriptView
