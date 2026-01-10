import { useState } from 'react'
import { Power, AlertTriangle, CheckCircle } from 'lucide-react'
import clsx from 'clsx'

function KillSwitch() {
  const [isActive, setIsActive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const handleToggle = async () => {
    if (!isActive) {
      // Show confirmation before activating
      setShowConfirm(true)
      return
    }

    // Deactivating - no confirmation needed
    await performToggle()
  }

  const performToggle = async () => {
    setIsLoading(true)
    setShowConfirm(false)

    try {
      // TODO: Call actual API
      if (isActive) {
        // await fetch('/api/admin/kill-switch', { method: 'DELETE' })
      } else {
        // await fetch('/api/admin/kill-switch', { method: 'POST' })
      }

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))

      setIsActive(!isActive)
    } catch (error) {
      console.error('Kill switch error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Status Indicator */}
      <div className={clsx(
        'flex items-center gap-3 p-3 rounded-lg',
        isActive ? 'bg-red-100' : 'bg-green-100'
      )}>
        {isActive ? (
          <>
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span className="font-medium text-red-700">
              Kill switch is ACTIVE - No new calls being accepted
            </span>
          </>
        ) : (
          <>
            <CheckCircle className="w-5 h-5 text-green-600" />
            <span className="font-medium text-green-700">
              System is accepting calls normally
            </span>
          </>
        )}
      </div>

      {/* Toggle Button */}
      <button
        onClick={handleToggle}
        disabled={isLoading}
        className={clsx(
          'flex items-center justify-center gap-2 w-full py-3 rounded-lg font-medium transition-colors',
          isActive
            ? 'bg-green-600 hover:bg-green-700 text-white'
            : 'bg-red-600 hover:bg-red-700 text-white',
          isLoading && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Power className="w-5 h-5" />
        {isLoading
          ? 'Processing...'
          : isActive
            ? 'Deactivate Kill Switch'
            : 'Activate Kill Switch'
        }
      </button>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Activate Kill Switch?
                </h3>
                <p className="text-sm text-gray-500">
                  This will stop accepting new calls
                </p>
              </div>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to activate the kill switch? The AI will stop
              answering new calls. Existing calls will continue until completion.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-2 border border-gray-200 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={performToggle}
                className="flex-1 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
              >
                Yes, Activate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default KillSwitch
