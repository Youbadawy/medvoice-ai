import clsx from 'clsx'
import { Calendar, CalendarDays, CalendarRange } from 'lucide-react'

export type CalendarView = 'month' | 'week' | 'day'

interface ViewToggleProps {
  view: CalendarView
  onViewChange: (view: CalendarView) => void
}

const views: { id: CalendarView; label: string; icon: typeof Calendar }[] = [
  { id: 'month', label: 'Month', icon: Calendar },
  { id: 'week', label: 'Week', icon: CalendarRange },
  { id: 'day', label: 'Day', icon: CalendarDays },
]

export function ViewToggle({ view, onViewChange }: ViewToggleProps) {
  return (
    <div className="flex bg-gray-100 rounded-lg p-1">
      {views.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onViewChange(id)}
          className={clsx(
            'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            view === id
              ? 'bg-white text-primary-700 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </div>
  )
}
