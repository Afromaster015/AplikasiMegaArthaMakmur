export type ApiResult<T> = { ok: boolean; data: T; meta?: unknown }

const state = { csrf: sessionStorage.getItem('csrf') || '' }

export function setCsrf(token: string) {
  state.csrf = token
  sessionStorage.setItem('csrf', token)
}

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (options.method && options.method !== 'GET' && state.csrf) headers.set('X-CSRF-Token', state.csrf)
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin' })
  const payload = await response.json().catch(() => ({ ok: false, error: { message: 'Respons server tidak valid.' } }))
  if (!response.ok || !payload.ok) {
    const error = new Error(payload.error?.message || 'Operasi gagal.') as Error & { status?: number; fields?: Record<string,string> }
    error.status = response.status
    error.fields = payload.error?.fields || {}
    throw error
  }
  return (payload as ApiResult<T>).data
}
