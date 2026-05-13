import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { bugs as bugsApi, getToken } from '../api'

const isMobile =
  /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
  (navigator.maxTouchPoints > 1 && window.matchMedia('(pointer: coarse)').matches)

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [tokenInput, setTokenInput] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)
  const [qrSrc, setQrSrc] = useState<string | null>(null)
  const [qrLoading, setQrLoading] = useState(false)
  const qrObjectUrl = useRef<string | null>(null)

  // Handle magic-link ?token= from QR scan
  useEffect(() => {
    const urlToken = searchParams.get('token')
    if (urlToken) {
      login(urlToken)
      navigate('/bugs', { replace: true })
    }
  }, [searchParams, login, navigate])

  // Already logged in — redirect
  useEffect(() => {
    if (isAuthenticated) navigate('/bugs', { replace: true })
  }, [isAuthenticated, navigate])

  async function handleSignIn() {
    const t = tokenInput.trim()
    if (!t) return
    setChecking(true)
    setError('')
    login(t)
    try {
      await bugsApi.list({ status: 'open', per_page: 1 })
      navigate('/bugs', { replace: true })
    } catch {
      setError('Invalid token. Please try again.')
      setChecking(false)
    }
  }

  async function handleShowQr() {
    const t = tokenInput.trim() || getToken()
    if (!t) {
      setError('Please enter your token first to generate a QR code.')
      return
    }
    login(t)
    setError('')
    setQrLoading(true)
    try {
      const res = await fetch('/auth/qr', {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!res.ok) throw new Error()
      const blob = await res.blob()
      if (qrObjectUrl.current) URL.revokeObjectURL(qrObjectUrl.current)
      const url = URL.createObjectURL(blob)
      qrObjectUrl.current = url
      setQrSrc(url)
    } catch {
      setError('Failed to generate QR code. Check your token.')
    } finally {
      setQrLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-md w-full max-w-sm p-8 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 text-center">RxBugs</h1>

        {/* QR section */}
        {isMobile ? (
          <div className="text-center text-sm text-gray-500 border border-gray-200 rounded-lg p-4">
            <p className="font-medium text-gray-700 mb-1">Sign in on desktop</p>
            <p>Open RxBugs on a desktop browser, click <strong>Show QR Code</strong>, then scan it with this device.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {qrSrc ? (
              <div className="text-center space-y-2">
                <img src={qrSrc} alt="QR code — scan to sign in" className="mx-auto w-48 h-48" />
                <p className="text-xs text-gray-400">Expires in 5 minutes</p>
              </div>
            ) : (
              <button
                onClick={handleShowQr}
                disabled={qrLoading}
                className="w-full py-2 px-4 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                {qrLoading ? 'Generating…' : 'Show QR Code'}
              </button>
            )}
          </div>
        )}

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs text-gray-400">
            <span className="bg-white px-2">or paste token</span>
          </div>
        </div>

        {/* Token form */}
        <div className="space-y-4">
          <div>
            <label htmlFor="token-input" className="block text-sm font-medium text-gray-700 mb-1">
              Access token
            </label>
            <input
              id="token-input"
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSignIn() }}
              placeholder="Paste your BUGTRACKER_TOKEN"
              autoComplete="current-password"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            onClick={handleSignIn}
            disabled={checking}
            className="w-full py-2 px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {checking ? 'Checking…' : 'Sign in'}
          </button>
        </div>
      </div>
    </div>
  )
}
