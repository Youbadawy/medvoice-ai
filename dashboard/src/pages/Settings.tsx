import { useState } from 'react'
import {
  Building,
  Globe,
  Bell,
  Save,
  AlertTriangle
} from 'lucide-react'
import KillSwitch from '../components/KillSwitch'

function SettingsPage() {
  const [clinicName, setClinicName] = useState('Clinique Médicale Saint-Laurent')
  const [clinicAddress, setClinicAddress] = useState('1234 Rue Saint-Laurent, Montréal QC')
  const [clinicHours, setClinicHours] = useState('Lundi-Vendredi 8h-17h, Samedi 9h-12h')
  const [defaultLanguage, setDefaultLanguage] = useState('fr')
  const [smsNotifications, setSmsNotifications] = useState(true)
  const [emailNotifications, setEmailNotifications] = useState(true)

  const handleSave = () => {
    // TODO: Save settings to backend
    alert('Settings saved!')
  }

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure MedVoice AI settings</p>
      </div>

      {/* Kill Switch - Most Important */}
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-red-900">Emergency Kill Switch</h2>
            <p className="text-sm text-red-700 mt-1 mb-4">
              Immediately stop accepting new calls. Existing calls will continue until completion.
            </p>
            <KillSwitch />
          </div>
        </div>
      </div>

      {/* Clinic Information */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <Building className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Clinic Information</h2>
            <p className="text-sm text-gray-500">Basic clinic details for the AI</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Clinic Name
            </label>
            <input
              type="text"
              value={clinicName}
              onChange={(e) => setClinicName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Address
            </label>
            <input
              type="text"
              value={clinicAddress}
              onChange={(e) => setClinicAddress(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Business Hours
            </label>
            <input
              type="text"
              value={clinicHours}
              onChange={(e) => setClinicHours(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>

      {/* Language Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <Globe className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Language Settings</h2>
            <p className="text-sm text-gray-500">Default language for greetings</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Default Greeting Language
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="language"
                value="fr"
                checked={defaultLanguage === 'fr'}
                onChange={(e) => setDefaultLanguage(e.target.value)}
                className="w-4 h-4 text-primary-600"
              />
              <span>Français (Quebec)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="language"
                value="en"
                checked={defaultLanguage === 'en'}
                onChange={(e) => setDefaultLanguage(e.target.value)}
                className="w-4 h-4 text-primary-600"
              />
              <span>English (Canada)</span>
            </label>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            The AI will automatically switch languages based on the caller's speech.
          </p>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <Bell className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Notifications</h2>
            <p className="text-sm text-gray-500">Configure alert settings</p>
          </div>
        </div>

        <div className="space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <div className="font-medium text-gray-900">SMS Confirmations</div>
              <div className="text-sm text-gray-500">Send SMS to patients after booking</div>
            </div>
            <input
              type="checkbox"
              checked={smsNotifications}
              onChange={(e) => setSmsNotifications(e.target.checked)}
              className="w-5 h-5 text-primary-600 rounded"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <div className="font-medium text-gray-900">Email Notifications</div>
              <div className="text-sm text-gray-500">Email staff on transfers and issues</div>
            </div>
            <input
              type="checkbox"
              checked={emailNotifications}
              onChange={(e) => setEmailNotifications(e.target.checked)}
              className="w-5 h-5 text-primary-600 rounded"
            />
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors"
        >
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>
    </div>
  )
}

export default SettingsPage
