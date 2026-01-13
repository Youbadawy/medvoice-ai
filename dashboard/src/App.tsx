import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Routes, Route, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Phone,
  Calendar,
  Settings,
  Plus,
} from 'lucide-react'
import { FiDollarSign } from 'react-icons/fi'
import Dashboard from './pages/Dashboard'
import Calls from './pages/Calls'
import Appointments from './pages/Appointments'
import Costs from './pages/Costs'
import SettingsPage from './pages/Settings'
import ManualBookingModal from './components/ManualBookingModal'
import clsx from 'clsx'
import { Toaster, toast } from 'sonner'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Calls', href: '/calls', icon: Phone },
  { name: 'Appointments', href: '/appointments', icon: Calendar },
  { name: 'Financials', href: '/costs', icon: FiDollarSign },
  { name: 'Settings', href: '/settings', icon: Settings },
]

function App() {
  const queryClient = useQueryClient()
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50/50 font-sans text-gray-900">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-72 bg-white border-r border-gray-200 shadow-soft z-50">
        {/* Logo */}
        <div className="flex items-center gap-4 px-8 py-6">
          <div className="relative">
            <div className="absolute inset-0 bg-primary-200 rounded-xl blur opacity-50"></div>
            <img
              src="/kaimed-logo.png"
              alt="KaiMed Logo"
              className="relative w-10 h-10 rounded-xl object-contain bg-white shadow-sm"
            />
          </div>
          <div>
            <h1 className="font-display font-bold text-xl text-gray-900 tracking-tight">KaiMed AI</h1>
            <p className="text-xs font-medium text-primary-600 tracking-wide uppercase">Admin Portal</p>
          </div>
        </div>

        {/* Primary Action */}
        <div className="px-6 pb-2">
          <button
            onClick={() => setIsBookingModalOpen(true)}
            className="w-full flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-3 rounded-xl font-medium shadow-md shadow-primary-200 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            New Booking
          </button>
        </div>

        {/* Navigation */}
        <nav className="px-4 py-4">
          <ul className="space-y-1.5">
            {navigation.map((item) => (
              <li key={item.name}>
                <NavLink
                  to={item.href}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group',
                      isActive
                        ? 'bg-primary-50 text-primary-700 shadow-sm'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon className={clsx(
                        "w-5 h-5 transition-colors",
                        isActive ? "text-primary-600" : "text-gray-400 group-hover:text-gray-600"
                      )} />
                      {item.name}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Status indicator */}
        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-gray-100 bg-gray-50/50">
          <div className="flex items-center gap-3">
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">System Online</p>
              <p className="text-xs text-gray-500">v1.2.0 • Stable</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="pl-72 transition-all duration-300 ease-in-out">
        <div className="max-w-7xl mx-auto p-8 lg:p-10">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/calls" element={<Calls />} />
            <Route path="/appointments" element={<Appointments />} />
            <Route path="/costs" element={<Costs />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>

      {/* Modals */}
      <ManualBookingModal
        isOpen={isBookingModalOpen}
        onClose={() => setIsBookingModalOpen(false)}
        onSuccess={() => {
          toast.success("Appointment booked successfully")
          queryClient.invalidateQueries({ queryKey: ['appointments'] })
          queryClient.invalidateQueries({ queryKey: ['calendar'] })
          queryClient.invalidateQueries({ queryKey: ['slots'] })
        }}
      />
      <Toaster position="top-right" />
    </div>
  )
}

export default App
