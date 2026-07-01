/**
 * AdminGate - 仪表盘密码门组件
 * 
 * 功能：
 *   - 对 /dashboard 路由包裹密码验证（仅在验证通过后渲染子组件）
 *   - 密码哈希存储：构建时通过 VITE_DASHBOARD_PASSWORD_HASH 环境变量注入 SHA-256 哈希
 *   - 会话级认证：验证通过后将哈希存入 sessionStorage（key: ai_admin_auth），刷新页面后需重新验证
 *   - 前端密码验证：使用 Web Crypto API（crypto.subtle.digest）计算 SHA-256 并与哈希比对
 * 
 * 导出：
 *   - AdminGate：包裹受保护路由的组件（已验证 → children，未验证 → 密码输入表单）
 *   - useAdminAuth()：检查当前会话是否已认证（供其他组件判断认证状态）
 */

import { useState, type ReactNode } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock } from '@fortawesome/free-solid-svg-icons'

/** 构建时注入的密码 SHA-256 哈希（通过 VITE_DASHBOARD_PASSWORD_HASH 环境变量） */
const PASSWORD_HASH = import.meta.env.VITE_DASHBOARD_PASSWORD_HASH || ''
/** sessionStorage 中存储认证状态的 key */
const STORAGE_KEY = 'ai_admin_auth'

/** 使用 Web Crypto API 计算输入的 SHA-256 哈希（返回 hex 字符串） */
async function sha256(input: string): Promise<string> {
  const buf = new TextEncoder().encode(input)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

/** useAdminAuth Hook：检查当前 sessionStorage 中是否存在有效认证 */
export function useAdminAuth() {
  const stored = sessionStorage.getItem(STORAGE_KEY)
  return stored != null && PASSWORD_HASH !== '' && stored === PASSWORD_HASH
}

/** AdminGate - 密码验证门组件 */
export function AdminGate({ children }: { children: ReactNode }) {
  /** password：用户输入的密码 */
  const [password, setPassword] = useState('')
  /** error：密码错误标识（控制错误提示显示） */
  const [error, setError] = useState(false)
  /** authenticated：是否已通过验证（初始化时检查 sessionStorage） */
  const [authenticated, setAuthenticated] = useState(() => useAdminAuth())

  /** 提交密码：计算 SHA-256 并与构建时哈希比对 */
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

  // 已验证：直接渲染子组件
  if (authenticated) return <>{children}</>

  // 未验证：渲染密码输入表单
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
