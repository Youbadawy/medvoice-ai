import { useState, useEffect } from 'react';
import { DollarSign, Activity, Phone, Cpu } from 'lucide-react';
import { API_URL } from '../config';

interface CostBreakdown {
    telephony: number;
    asr: number;
    tts: number;
    llm: number;
}

interface DailyCost {
    date: string;
    cost: number;
}

interface CostData {
    period_days: number;
    total_cost: number;
    breakdown: CostBreakdown;
    daily_costs: DailyCost[];
}

const Costs = () => {
    const [data, setData] = useState<CostData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchCosts();
    }, []);

    const fetchCosts = async () => {
        try {
            const response = await fetch(`${API_URL}/admin/costs?days=30`);
            if (response.ok) {
                const jsonData = await response.json();
                setData(jsonData);
            }
        } catch (error) {
            console.error('Error fetching costs:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (!data) {
        return <p className="text-gray-500">No cost data available.</p>;
    }

    const getStatusBadge = (cost: number) => {
        if (cost > 10) return { color: 'bg-red-100 text-red-700', label: 'High' };
        if (cost > 2) return { color: 'bg-yellow-100 text-yellow-700', label: 'Moderate' };
        return { color: 'bg-green-100 text-green-700', label: 'Low' };
    };

    const getPercentage = (value: number) => {
        if (data.total_cost === 0) return 0;
        return (value / data.total_cost) * 100;
    };

    return (
        <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-6">Financial Overview (Last 30 Days)</h1>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-primary-100 rounded-lg">
                            <DollarSign className="w-5 h-5 text-primary-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Total Spend</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${data.total_cost.toFixed(2)}</p>
                    <p className="text-xs text-gray-400 mt-1">Last 30 Days</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <Phone className="w-5 h-5 text-purple-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Voice & ASR</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${(data.breakdown.telephony + data.breakdown.asr).toFixed(2)}</p>
                    <p className="text-xs text-gray-400 mt-1">Twilio + Deepgram</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-green-100 rounded-lg">
                            <Cpu className="w-5 h-5 text-green-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">AI Brain</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${data.breakdown.llm.toFixed(2)}</p>
                    <p className="text-xs text-gray-400 mt-1">Gemini / DeepSeek</p>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-orange-100 rounded-lg">
                            <Activity className="w-5 h-5 text-orange-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-500">Synthesis (TTS)</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${data.breakdown.tts.toFixed(2)}</p>
                    <p className="text-xs text-gray-400 mt-1">Google Journey</p>
                </div>
            </div>

            {/* Tables */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Daily Breakdown */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Daily Breakdown</h2>
                    </div>
                    <div className="p-6">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    <th className="pb-3">Date</th>
                                    <th className="pb-3 text-right">Cost (USD)</th>
                                    <th className="pb-3">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {data.daily_costs.map((day) => {
                                    const status = getStatusBadge(day.cost);
                                    return (
                                        <tr key={day.date}>
                                            <td className="py-3 text-sm text-gray-900">{day.date}</td>
                                            <td className="py-3 text-sm font-semibold text-gray-900 text-right">${day.cost.toFixed(2)}</td>
                                            <td className="py-3">
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${status.color}`}>
                                                    {status.label}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                                {data.daily_costs.length === 0 && (
                                    <tr>
                                        <td colSpan={3} className="py-8 text-center text-gray-400">No usage recorded.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Cost Distribution */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Cost Distribution</h2>
                    </div>
                    <div className="p-6 space-y-5">
                        <div>
                            <div className="flex justify-between mb-1.5">
                                <span className="text-sm text-gray-600">Telephony (Twilio)</span>
                                <span className="text-sm font-semibold text-gray-900">${data.breakdown.telephony.toFixed(4)}</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${getPercentage(data.breakdown.telephony)}%` }} />
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between mb-1.5">
                                <span className="text-sm text-gray-600">ASR (Deepgram)</span>
                                <span className="text-sm font-semibold text-gray-900">${data.breakdown.asr.toFixed(4)}</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-purple-500 rounded-full" style={{ width: `${getPercentage(data.breakdown.asr)}%` }} />
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between mb-1.5">
                                <span className="text-sm text-gray-600">LLM Intelligence</span>
                                <span className="text-sm font-semibold text-gray-900">${data.breakdown.llm.toFixed(4)}</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-green-500 rounded-full" style={{ width: `${getPercentage(data.breakdown.llm)}%` }} />
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between mb-1.5">
                                <span className="text-sm text-gray-600">Text-to-Speech</span>
                                <span className="text-sm font-semibold text-gray-900">${data.breakdown.tts.toFixed(4)}</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-orange-500 rounded-full" style={{ width: `${getPercentage(data.breakdown.tts)}%` }} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Costs;
