/**
 * Centralized HTTP client for PreBrief frontend ↔ FastAPI backend.
 * - Always sends credentials (anonymous session cookie)
 * - JSON + multipart + blob downloads
 * - Timeouts via AbortController
 * - Standardized error parsing
 */

const RAW_BASE = (import.meta.env?.VITE_API_BASE_URL as string | undefined)?.trim()

export const API_BASE = RAW_BASE ? RAW_BASE.replace(/\/$/, '') : ''

export const isBackendConfigured = Boolean(API_BASE)

export class ApiError extends Error {
  status: number
  code?: string
  requestId?: string
  body?: unknown

  constructor(message: string, status: number, opts?: { code?: string; requestId?: string; body?: unknown }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = opts?.code
    this.requestId = opts?.requestId
    this.body = opts?.body
  }
}

export async function parseApiError(res: Response): Promise<ApiError> {
  let body: unknown
  let message = res.statusText || `HTTP ${res.status}`
  let code: string | undefined
  let requestId: string | undefined
  try {
    body = await res.json()
    const err = (body as { error?: { message?: string; code?: string; requestId?: string }; detail?: string })
      ?.error
    if (err?.message) message = err.message
    else if ((body as { detail?: string })?.detail) message = String((body as { detail: string }).detail)
    code = err?.code
    requestId = err?.requestId ?? res.headers.get('X-Request-Id') ?? undefined
  } catch {
    requestId = res.headers.get('X-Request-Id') ?? undefined
  }
  return new ApiError(message, res.status, { code, requestId, body })
}

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface RequestOptions {
  method?: HttpMethod
  body?: unknown
  formData?: FormData
  signal?: AbortSignal
  timeoutMs?: number
  headers?: Record<string, string>
  /** Return response as Blob (PDF, file download) */
  asBlob?: boolean
  /** Return raw Response */
  raw?: boolean
}

function ensureConfigured(): void {
  if (!API_BASE) {
    throw new ApiError(
      'Backend is not configured. Set VITE_API_BASE_URL (e.g. http://127.0.0.1:8000/api/v1) in frontend/.env',
      0,
      { code: 'config_error' },
    )
  }
}

export async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  ensureConfigured()
  const method = opts.method ?? (opts.body || opts.formData ? 'POST' : 'GET')
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`

  const headers: Record<string, string> = { ...(opts.headers || {}) }
  let body: BodyInit | undefined
  if (opts.formData) {
    body = opts.formData
    // Let browser set multipart boundary
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
    body = typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body)
  }

  const controller = new AbortController()
  const timeout = opts.timeoutMs ?? 120_000
  const timer = setTimeout(() => controller.abort(), timeout)
  const onAbort = () => controller.abort()
  if (opts.signal) {
    if (opts.signal.aborted) controller.abort()
    else opts.signal.addEventListener('abort', onAbort)
  }

  try {
    const res = await fetch(url, {
      method,
      headers,
      body,
      credentials: 'include',
      signal: controller.signal,
    })
    if (opts.raw) return res as unknown as T
    if (!res.ok) throw await parseApiError(res)
    if (opts.asBlob) return (await res.blob()) as unknown as T
    if (res.status === 204) return undefined as unknown as T
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) return (await res.json()) as T
    return (await res.text()) as unknown as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    if ((err as Error)?.name === 'AbortError') {
      throw new ApiError(opts.signal?.aborted ? 'aborted' : 'Request timed out', 0, { code: 'timeout' })
    }
    throw new ApiError(
      (err as Error)?.message || 'Network error — is the backend running?',
      0,
      { code: 'network_error' },
    )
  } finally {
    clearTimeout(timer)
    if (opts.signal) opts.signal.removeEventListener('abort', onAbort)
  }
}

export const http = {
  get: <T = unknown>(path: string, opts?: Omit<RequestOptions, 'method' | 'body' | 'formData'>) =>
    request<T>(path, { ...opts, method: 'GET' }),
  post: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'POST', body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'PUT', body }),
  patch: <T = unknown>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'PATCH', body }),
  delete: <T = unknown>(path: string, opts?: Omit<RequestOptions, 'method' | 'body' | 'formData'>) =>
    request<T>(path, { ...opts, method: 'DELETE' }),
  upload: <T = unknown>(path: string, formData: FormData, opts?: Omit<RequestOptions, 'method' | 'formData'>) =>
    request<T>(path, { ...opts, method: 'POST', formData }),
  blob: (path: string, opts?: Omit<RequestOptions, 'asBlob'>) =>
    request<Blob>(path, { ...opts, asBlob: true }),
}

/** Health check helpers */
export async function checkHealth(): Promise<{ status: string; api?: string }> {
  return http.get('/health', { timeoutMs: 8_000 })
}

export async function checkReady(): Promise<{
  status: string
  checks?: Record<string, string>
}> {
  return http.get('/health/ready', { timeoutMs: 8_000 })
}
