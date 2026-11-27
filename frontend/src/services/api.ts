const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export function getToken() { return localStorage.getItem('fraud_access_token') }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `API request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password })
  const response = await fetch(`${API_BASE}/auth/token`, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body,
  })
  if (!response.ok) throw new Error('Incorrect email or password')
  return response.json() as Promise<{ access_token: string; role: string; expires_in: number }>
}

export const websocketUrl = () => {
  const base = API_BASE.replace(/^http/, 'ws').replace(/\/api\/v1$/, '')
  return `${base}/api/v1/ws/transactions`
}
