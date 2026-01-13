import { useState, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Calendar as CalendarIcon, Clock, User, Phone, Check, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'
import { API_URL } from '../config'

interface ManualBookingModalProps {
    isOpen: boolean
    onClose: () => void
    onSuccess: () => void
}

export default function ManualBookingModal({ isOpen, onClose, onSuccess }: ManualBookingModalProps) {
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Form State
    const [formData, setFormData] = useState({
        patient_name: '',
        patient_phone: '',
        ramq_number: '',
        visit_type: 'general',
        date: format(new Date(), 'yyyy-MM-dd'),
        time: '09:00', // Default time
        notes: '',
        consent_given: false
    })

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setLoading(true)

        try {
            // Construct slot_id from date and time: YYYYMMDDHHMM
            const dateStr = formData.date.replace(/-/g, '')
            const timeStr = formData.time.replace(':', '')
            const slot_id = `${dateStr}${timeStr}`

            const response = await fetch(`${API_URL}/api/admin/appointments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_name: formData.patient_name,
                    patient_phone: formData.patient_phone,
                    slot_id: slot_id,
                    visit_type: formData.visit_type,
                    ramq_number: formData.ramq_number,
                    consent_given: formData.consent_given,
                    notes: formData.notes
                })
            })

            if (!response.ok) {
                throw new Error('Failed to book appointment')
            }

            onSuccess()
            onClose()
            // Reset form
            setFormData({
                patient_name: '',
                patient_phone: '',
                ramq_number: '',
                visit_type: 'general',
                date: format(new Date(), 'yyyy-MM-dd'),
                time: '09:00',
                notes: '',
                consent_given: false
            })
        } catch (err) {
            setError('Failed to create appointment. Please check the details and try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={onClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4 text-center">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all border border-gray-100">

                                <div className="flex items-center justify-between mb-6">
                                    <Dialog.Title as="h3" className="text-lg font-display font-semibold text-gray-900">
                                        Book Appointment
                                    </Dialog.Title>
                                    <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                {error && (
                                    <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm flex items-center gap-2">
                                        <AlertCircle className="w-4 h-4" />
                                        {error}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {/* Personal Info */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1.5 col-span-2">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Patient Name</label>
                                            <div className="relative">
                                                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="text"
                                                    required
                                                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm"
                                                    placeholder="John Doe"
                                                    value={formData.patient_name}
                                                    onChange={e => setFormData({ ...formData, patient_name: e.target.value })}
                                                />
                                            </div>
                                        </div>

                                        <div className="space-y-1.5 col-span-2">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Phone Number</label>
                                            <div className="relative">
                                                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="tel"
                                                    required
                                                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm"
                                                    placeholder="(555) 123-4567"
                                                    value={formData.patient_phone}
                                                    onChange={e => setFormData({ ...formData, patient_phone: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Compliance Fields */}
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">RAMQ Number (Optional)</label>
                                        <input
                                            type="text"
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm uppercase placeholder:normal-case"
                                            placeholder="ABCD 1234 5678"
                                            value={formData.ramq_number}
                                            onChange={e => setFormData({ ...formData, ramq_number: e.target.value.toUpperCase() })}
                                        />
                                    </div>

                                    {/* Scheduling */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</label>
                                            <div className="relative">
                                                <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="date"
                                                    required
                                                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm"
                                                    value={formData.date}
                                                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                                                />
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Time</label>
                                            <div className="relative">
                                                <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="time"
                                                    required
                                                    step="900" // 15 min steps
                                                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm"
                                                    value={formData.time}
                                                    onChange={e => setFormData({ ...formData, time: e.target.value })}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-1.5">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Visit Type</label>
                                        <select
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm bg-white"
                                            value={formData.visit_type}
                                            onChange={e => setFormData({ ...formData, visit_type: e.target.value })}
                                        >
                                            <option value="general">General Checkup</option>
                                            <option value="followup">Follow-up</option>
                                            <option value="vaccination">Vaccination</option>
                                            <option value="emergency">Emergency / Urgent</option>
                                        </select>
                                    </div>

                                    <div className="space-y-1.5">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Notes</label>
                                        <textarea
                                            rows={2}
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-sm resize-none"
                                            placeholder="Additional details..."
                                            value={formData.notes}
                                            onChange={e => setFormData({ ...formData, notes: e.target.value })}
                                        />
                                    </div>

                                    {/* Consent Toggle */}
                                    <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors">
                                        <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors ${formData.consent_given ? 'bg-primary-500 border-primary-500 text-white' : 'border-gray-300 bg-white'}`}>
                                            {formData.consent_given && <Check className="w-3.5 h-3.5" />}
                                        </div>
                                        <input
                                            type="checkbox"
                                            className="hidden"
                                            checked={formData.consent_given}
                                            onChange={e => setFormData({ ...formData, consent_given: e.target.checked })}
                                        />
                                        <div className="space-y-0.5">
                                            <p className="text-sm font-medium text-gray-900">Bill 25 Consent</p>
                                            <p className="text-xs text-gray-500 leading-normal">
                                                Patient has explicitly consented to data collection and processing.
                                            </p>
                                        </div>
                                    </label>

                                    {/* Actions */}
                                    <div className="pt-4 flex items-center justify-end gap-3">
                                        <button
                                            type="button"
                                            onClick={onClose}
                                            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={loading || !formData.consent_given}
                                            className="px-4 py-2 rounded-lg text-sm font-medium bg-primary-600 text-white hover:bg-primary-700 shadow-sm shadow-primary-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                                        >
                                            {loading ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                    Booking...
                                                </>
                                            ) : (
                                                'Confirm Booking'
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition>
    )
}
