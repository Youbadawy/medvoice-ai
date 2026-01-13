import clsx from 'clsx'
import { Check, X, Clock, AlertCircle } from 'lucide-react'

export type StatusType = 'completed' | 'failed' | 'active' | 'pending' | 'transferred' | 'no_interaction'

interface StatusBadgeProps {
    status: string
    size?: 'sm' | 'md'
}

const statusConfig: Record<string, { color: string, icon: any, label: string }> = {
    completed: {
        color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        icon: Check,
        label: 'Completed'
    },
    failed: {
        color: 'bg-red-50 text-red-700 border-red-200',
        icon: X,
        label: 'Failed'
    },
    active: {
        color: 'bg-primary-50 text-primary-700 border-primary-200',
        icon: Clock,
        label: 'Active'
    },
    pending: {
        color: 'bg-amber-50 text-amber-700 border-amber-200',
        icon: Clock,
        label: 'Pending'
    },
    transferred: {
        color: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        icon: AlertCircle,
        label: 'Transferred'
    },
    no_interaction: {
        color: 'bg-gray-50 text-gray-600 border-gray-200',
        icon: AlertCircle,
        label: 'No Interaction'
    }
}

const StatusBadge = ({ status, size = 'sm' }: StatusBadgeProps) => {
    // Normalize status key
    const normalizedStatus = status?.toLowerCase() || 'pending'
    const config = statusConfig[normalizedStatus] || statusConfig.pending
    const Icon = config.icon

    return (
        <span className={clsx(
            "inline-flex items-center gap-1.5 border rounded-full font-medium transition-colors",
            config.color,
            size === 'sm' ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-sm"
        )}>
            <Icon className={size === 'sm' ? "w-3 h-3" : "w-4 h-4"} />
            {config.label}
        </span>
    )
}

export default StatusBadge
