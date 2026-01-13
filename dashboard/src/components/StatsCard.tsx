import { LucideIcon, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import clsx from 'clsx'

interface StatsCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  highlight?: boolean
  suffix?: string
}

const StatsCard = ({
  title,
  value,
  icon: Icon,
  trend,
  trendValue,
  highlight = false,
  suffix
}: StatsCardProps) => {
  return (
    <div className={clsx(
      "relative overflow-hidden rounded-2xl p-6 transition-all duration-300",
      highlight
        ? "bg-primary-600 text-white shadow-lg shadow-primary-500/20 ring-1 ring-primary-500"
        : "bg-white text-gray-900 shadow-soft border border-gray-100 hover:shadow-lg hover:translate-y-[-2px]"
    )}>
      {/* Background decoration for highlighted card */}
      {highlight && (
        <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-white/10 rounded-full blur-2xl"></div>
      )}

      <div className="flex justify-between items-start mb-4">
        <div className={clsx(
          "p-3 rounded-xl",
          highlight ? "bg-white/20 text-white" : "bg-primary-50 text-primary-600"
        )}>
          <Icon className="w-6 h-6" />
        </div>

        {trend && (
          <div className={clsx(
            "flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full",
            highlight
              ? "bg-white/20 text-white"
              : trend === 'up'
                ? "bg-green-50 text-green-700"
                : trend === 'down'
                  ? "bg-red-50 text-red-700"
                  : "bg-gray-50 text-gray-600"
          )}>
            {trend === 'up' && <ArrowUpRight className="w-3 h-3" />}
            {trend === 'down' && <ArrowDownRight className="w-3 h-3" />}
            {trend === 'neutral' && <Minus className="w-3 h-3" />}
            <span>{trendValue}</span>
          </div>
        )}
      </div>

      <div>
        <p className={clsx(
          "text-sm font-medium mb-1",
          highlight ? "text-primary-100" : "text-gray-500"
        )}>
          {title}
        </p>
        <div className="flex items-baseline gap-1">
          <h3 className="text-3xl font-display font-bold tracking-tight">
            {value}
          </h3>
          {suffix && (
            <span className={clsx(
              "text-sm font-medium",
              highlight ? "text-primary-200" : "text-gray-400"
            )}>
              {suffix}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default StatsCard
