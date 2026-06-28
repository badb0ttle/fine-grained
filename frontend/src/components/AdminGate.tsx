import { useState, type ReactNode } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock } from '@fortawesome/free-solid-svg-icons'

// Password hash injected at build time via VITE_DASHBOARD_PASSWORD_HASH.
// Generate: echo -n "your_password" | shasum -a 256 | cut -d' ' -f1
const PASSWORD_HASH = import.meta.env.VITE_DASHBOARD_PASSWORD_HASH || ''
const STORAGE_KEY = 'ai_admin_auth'

async function sha256(input: string): Promise<string> {
  const buf = new TextEncoder().encode(input)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

export function useAdminAuth() {
  const stored = sessionStorage.getItem(STORAGE_KEY)
  return stored != null && PASSWORD_HASH !== '' && stored === PASSWORD_HASH
}

export function AdminGate({ children }: { children: ReactNode }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [authenticated, setAuthenticated] = useState(() => useAdminAuth())

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const hash = await sha256(password)
    if (hash === PASSWORD_HASH) {
      sessionStorage.setItem(STORAGE_KEY, PASSWORD_HASH)
      setAuthenticated(true)
      setError(false)
    } else {
      setError(true)
      setPassword('')
    }
  }

  if (authenticated) return <>{children}</>

  return (
    <div className="flex items-center justify-center py-24 px-4">
      <div className="bg-bg-card border border-border-muted rounded-2xl p-8 w-full max-w-sm">
        <div className="text-center mb-6">
          <FontAwesomeIcon icon={faLock} className="text-3xl text-accent mb-3" />
          <h2 className="text-lg font-semibold text-text-primary">管理员验证</h2>
          <p className="text-sm text-text-muted mt-1">此页面仅限管理员访问</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            value={password}
            onChange={e => { setPassword(e.target.value); setError(false) }}
            placeholder="输入管理密码"
            autoFocus
            className="w-full bg-bg-secondary border border-border-default rounded-lg px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 transition-colors"
          />
          {error && (
            <p className="text-xs text-red text-center">密码错误</p>
          )}
          <button
            type="submit"
            disabled={!password}
            className="w-full bg-accent hover:bg-accent-hover disabled:opacity-40 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
          >
            验证
          </button>
        </form>
      </div>
    </div>
  )
}
