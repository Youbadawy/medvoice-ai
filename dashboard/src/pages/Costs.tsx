import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subDays } from 'date-fns';
import {
    DollarSign,
    Phone as PhoneIcon,
    Cpu,
    Activity,
    TrendingUp,
    TrendingDown,
    ChevronDown,
    ChevronUp,
    Calendar,
    Clock,
    CheckCircle,
    XCircle,
    ArrowUpRight,
    Filter
} from 'lucide-react';
import { API_URL } from '../config';

interface ProviderBreakdown {
    cost: number;
    percentage: number;
}

interface StatusBreakdown {
    count: number;
    cost: number;
}

interface DailyTrend {
    date: string;
    cost: number;
    calls: number;
}

interface TopCall {
    call_sid: string;
    caller_number: string;
    cost: number;
    duration: number;
    status: string;
    booking_made: boolean;
    created_at: string;
}

interface AnalyticsData {
    period: {
        start: string;
        end: string;
        days: number;
    };
    totals: {
        cost: number;
        calls: number;
        avg_per_call: number;
        avg_per_day: number;
    };
    by_provider: Record<string, ProviderBreakdown>;
    by_status: Record<string, StatusBreakdown>;
    daily_trend: DailyTrend[];
    top_expensive_calls: TopCall[];
}

interface CallCost {
    call_sid: string;
    caller_number: string;
    created_at: string;
    duration_seconds: number;
    status: string;
    booking_made: boolean;
    language: string;
    cost_data: {
        total_cost: number;
        breakdown: Record<string, number>;
    };
}

interface CallsResponse {
    calls: CallCost[];
    summary: {
        total_calls: number;
        total_cost: number;
        avg_cost_per_call: number;
    };
}

const PROVIDER_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
    telephony: { bg: 'bg-blue-100', text: 'text-blue-700', bar: 'bg-blue-500' },
    asr: { bg: 'bg-purple-100', text: 'text-purple-700', bar: 'bg-purple-500' },
    tts: { bg: 'bg-orange-100', text: 'text-orange-700', bar: 'bg-orange-500' },
    llm: { bg: 'bg-green-100', text: 'text-green-700', bar: 'bg-green-500' },
};

const PROVIDER_LABELS: Record<string, string> = {
    telephony: 'Twilio Voice',
    asr: 'Deepgram ASR',
    tts: 'Google TTS',
    llm: 'LLM (Gemini/DeepSeek)',
};

const STATUS_COLORS: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    transferred: 'bg-indigo-100 text-indigo-700',
    failed: 'bg-red-100 text-red-700',
    no_interaction: 'bg-gray-100 text-gray-600',
    active: 'bg-blue-100 text-blue-700',
};

const Costs = () => {
    const [days, setDays] = useState(30);
    const [expandedCall, setExpandedCall] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('');

    // Fetch analytics data
    const { data: analytics, isLoading: analyticsLoading } = useQuery<AnalyticsData>({
        queryKey: ['cost-analytics', days],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/api/admin/costs/analytics?days=${days}`);
            return res.json();
        },
        refetchInterval: 60000, // Refresh every minute
    });

    // Fetch per-call costs
    const { data: callsData, isLoading: callsLoading } = useQuery<CallsResponse>({
        queryKey: ['calls-costs', days, statusFilter],
        queryFn: async () => {
            const start = format(subDays(new Date(), days), 'yyyy-MM-dd');
            const end = format(new Date(), 'yyyy-MM-dd');
            let url = `${API_URL}/api/admin/calls/costs?start=${start}&end=${end}&limit=50`;
            if (statusFilter) url += `&status=${statusFilter}`;
            const res = await fetch(url);
            return res.json();
        },
        refetchInterval: 60000,
    });

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const formatCurrency = (value: number, decimals = 2) => {
        return `$${value.toFixed(decimals)}`;
    };

    if (analyticsLoading) {
        return (
            <div className="flex justify-center items-center h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Financial Overview</h1>
                    <p className="text-gray-500 text-sm mt-1">
                        {analytics?.period.start} to {analytics?.period.end}
                    </p>
                </div>
                <div className="flex gap-2">
                    {[7, 14, 30, 90].map((d) => (
                        <button
                            key={d}
                            onClick={() => setDays(d)}
                            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                                days === d
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                        >
                            {d}d
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2.5 bg-primary-100 rounded-xl">
                            <DollarSign className="w-5 h-5 text-primary-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Total Spend</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">
                        {formatCurrency(analytics?.totals.cost || 0)}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">Last {days} days</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2.5 bg-blue-100 rounded-xl">
                            <PhoneIcon className="w-5 h-5 text-blue-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Total Calls</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">
                        {analytics?.totals.calls || 0}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                        Avg {formatCurrency(analytics?.totals.avg_per_call || 0, 4)}/call
                    </p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2.5 bg-green-100 rounded-xl">
                            <TrendingUp className="w-5 h-5 text-green-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Avg/Day</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">
                        {formatCurrency(analytics?.totals.avg_per_day || 0)}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">Daily average</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2.5 bg-purple-100 rounded-xl">
                            <Cpu className="w-5 h-5 text-purple-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">LLM Cost</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">
                        {formatCurrency(analytics?.by_provider?.llm?.cost || 0)}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                        {analytics?.by_provider?.llm?.percentage || 0}% of total
                    </p>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Daily Trend */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-5 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Daily Cost Trend</h2>
                    </div>
                    <div className="p-5">
                        <div className="space-y-2">
                            {analytics?.daily_trend.slice(0, 10).map((day) => (
                                <div key={day.date} className="flex items-center gap-3">
                                    <span className="text-sm text-gray-500 w-24">{day.date}</span>
                                    <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-primary-500 rounded-full flex items-center justify-end pr-2"
                                            style={{
                                                width: `${Math.min(100, (day.cost / (analytics?.totals.avg_per_day || 1)) * 50)}%`,
                                                minWidth: '40px'
                                            }}
                                        >
                                            <span className="text-xs font-medium text-white">
                                                {formatCurrency(day.cost)}
                                            </span>
                                        </div>
                                    </div>
                                    <span className="text-xs text-gray-400 w-16 text-right">
                                        {day.calls} calls
                                    </span>
                                </div>
                            ))}
                            {(!analytics?.daily_trend || analytics.daily_trend.length === 0) && (
                                <p className="text-gray-400 text-center py-8">No data available</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Provider Breakdown */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-5 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Cost by Provider</h2>
                    </div>
                    <div className="p-5 space-y-4">
                        {analytics?.by_provider && Object.entries(analytics.by_provider).map(([provider, data]) => (
                            <div key={provider}>
                                <div className="flex justify-between mb-1.5">
                                    <span className="text-sm font-medium text-gray-700">
                                        {PROVIDER_LABELS[provider] || provider}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-semibold text-gray-900">
                                            {formatCurrency(data.cost, 4)}
                                        </span>
                                        <span className={`text-xs px-1.5 py-0.5 rounded ${PROVIDER_COLORS[provider]?.bg} ${PROVIDER_COLORS[provider]?.text}`}>
                                            {data.percentage}%
                                        </span>
                                    </div>
                                </div>
                                <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full rounded-full ${PROVIDER_COLORS[provider]?.bar}`}
                                        style={{ width: `${data.percentage}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Status Breakdown & Top Calls */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Cost by Status */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-5 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Cost by Call Status</h2>
                    </div>
                    <div className="p-5">
                        <div className="space-y-3">
                            {analytics?.by_status && Object.entries(analytics.by_status).map(([status, data]) => (
                                <div key={status} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'}`}>
                                            {status}
                                        </span>
                                        <span className="text-sm text-gray-600">{data.count} calls</span>
                                    </div>
                                    <span className="text-sm font-semibold text-gray-900">
                                        {formatCurrency(data.cost)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Top Expensive Calls */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-5 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Most Expensive Calls</h2>
                    </div>
                    <div className="p-5">
                        <div className="space-y-2">
                            {analytics?.top_expensive_calls.map((call, idx) => (
                                <div key={call.call_sid} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                                    <span className="w-6 h-6 flex items-center justify-center bg-primary-100 text-primary-700 text-xs font-bold rounded-full">
                                        {idx + 1}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">
                                            {call.caller_number}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {formatDuration(call.duration)} • {call.status}
                                            {call.booking_made && ' • Booked'}
                                        </p>
                                    </div>
                                    <span className="text-sm font-bold text-red-600">
                                        {formatCurrency(call.cost)}
                                    </span>
                                </div>
                            ))}
                            {(!analytics?.top_expensive_calls || analytics.top_expensive_calls.length === 0) && (
                                <p className="text-gray-400 text-center py-4">No calls yet</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Per-Call Details Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="px-5 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <h2 className="text-lg font-semibold text-gray-900">Call Cost Details</h2>
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-gray-400" />
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                            <option value="">All Statuses</option>
                            <option value="completed">Completed</option>
                            <option value="transferred">Transferred</option>
                            <option value="failed">Failed</option>
                        </select>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-100">
                                <th className="px-5 py-3">Date & Caller</th>
                                <th className="px-5 py-3">Duration</th>
                                <th className="px-5 py-3">Status</th>
                                <th className="px-5 py-3">Booking</th>
                                <th className="px-5 py-3 text-right">Total Cost</th>
                                <th className="px-5 py-3"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {callsLoading ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-8 text-center">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600 mx-auto"></div>
                                    </td>
                                </tr>
                            ) : callsData?.calls.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                                        No calls found
                                    </td>
                                </tr>
                            ) : (
                                callsData?.calls.map((call) => (
                                    <>
                                        <tr
                                            key={call.call_sid}
                                            className="hover:bg-gray-50 cursor-pointer"
                                            onClick={() => setExpandedCall(expandedCall === call.call_sid ? null : call.call_sid)}
                                        >
                                            <td className="px-5 py-3">
                                                <div>
                                                    <p className="text-sm font-medium text-gray-900">{call.caller_number}</p>
                                                    <p className="text-xs text-gray-500">
                                                        {format(new Date(call.created_at), 'MMM d, h:mm a')}
                                                    </p>
                                                </div>
                                            </td>
                                            <td className="px-5 py-3">
                                                <div className="flex items-center gap-1.5 text-sm text-gray-600">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    {formatDuration(call.duration_seconds)}
                                                </div>
                                            </td>
                                            <td className="px-5 py-3">
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[call.status] || 'bg-gray-100 text-gray-600'}`}>
                                                    {call.status}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                {call.booking_made ? (
                                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                                ) : (
                                                    <XCircle className="w-5 h-5 text-gray-300" />
                                                )}
                                            </td>
                                            <td className="px-5 py-3 text-right">
                                                <span className="text-sm font-semibold text-gray-900">
                                                    {formatCurrency(call.cost_data.total_cost, 4)}
                                                </span>
                                            </td>
                                            <td className="px-5 py-3">
                                                {expandedCall === call.call_sid ? (
                                                    <ChevronUp className="w-4 h-4 text-gray-400" />
                                                ) : (
                                                    <ChevronDown className="w-4 h-4 text-gray-400" />
                                                )}
                                            </td>
                                        </tr>
                                        {expandedCall === call.call_sid && (
                                            <tr className="bg-gray-50">
                                                <td colSpan={6} className="px-5 py-4">
                                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                                        {Object.entries(call.cost_data.breakdown).map(([provider, cost]) => (
                                                            <div key={provider} className="bg-white rounded-lg p-3 border border-gray-200">
                                                                <p className="text-xs text-gray-500 mb-1">
                                                                    {PROVIDER_LABELS[provider] || provider}
                                                                </p>
                                                                <p className={`text-sm font-semibold ${PROVIDER_COLORS[provider]?.text || 'text-gray-900'}`}>
                                                                    {formatCurrency(cost, 4)}
                                                                </p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Costs;
