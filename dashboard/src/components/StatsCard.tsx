import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'
import clsx from 'clsx'

interface StatsCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  trend?: string
  trendUp?: boolean
  suffix?: string
  highlight?: boolean
}

function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  trendUp,
  suffix,
  highlight = false
}: StatsCardProps) {
  return (
    <div className={clsx(
      'rounded-xl border p-6 transition-all',
      highlight
        ? 'bg-primary-600 border-primary-600 text-white'
        : 'bg-white border-gray-200'
    )}>
      <div className="flex items-start justify-between">
        <div>
          <p className={clsx(
            'text-sm font-medium',
            highlight ? 'text-primary-100' : 'text-gray-500'
          )}>
            {title}
          </p>
          <p className={clsx(
            'text-3xl font-bold mt-2',
            highlight ? 'text-white' : 'text-gray-900'
          )}>
            {value}
            {suffix && <span className="text-lg ml-1">{suffix}</span>}
          </p>
        </div>
        <div className={clsx(
          'w-10 h-10 rounded-lg flex items-center justify-center',
          highlight ? 'bg-primary-500' : 'bg-primary-50'
        )}>
          <Icon className={clsx(
            'w-5 h-5',
            highlight ? 'text-white' : 'text-primary-600'
          )} />
        </div>
      </div>

      {trend && (
        <div className={clsx(
          'flex items-center gap-1 mt-4 text-sm',
          highlight ? 'text-primary-100' : (trendUp ? 'text-green-600' : 'text-red-600')
        )}>
          {trendUp ? (
            <TrendingUp className="w-4 h-4" />
          ) : (
            <TrendingDown className="w-4 h-4" />
          )}
          <span>{trend}</span>
        </div>
      )}

      {highlight && (
        <div className="mt-4">
          <span className="inline-flex items-center gap-1 text-xs bg-primary-500 px-2 py-1 rounded-full">
            <span className="w-2 h-2 bg-white rounded-full pulse" />
            Live
          </span>
        </div>
      )}
    </div>
  )
}

export default StatsCard
