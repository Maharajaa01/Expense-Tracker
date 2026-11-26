/**
 * Thin client for the Expense Tracker whitelisted API.
 *
 * Every endpoint returns `{ ok, data, meta? }` inside Frappe's `message`.
 * Failures are normalised into `ApiError` so callers (and the offline queue)
 * can tell a network failure from an auth problem from a validation error.
 */
import { csrfToken } from './boot'

export type ApiErrorKind =
  | 'network'      // fetch failed: offline, DNS, CORS, aborted
  | 'auth'         // 401/403 with session expired / CSRF failure
  | 'permission'   // 403 PermissionError
  | 'validation'   // 417 ValidationError and friends
  | 'conflict'     // 409 / TimestampMismatchError
  | 'not_found'    // 404 DoesNotExistError
  | 'server'       // 5xx

export class ApiError extends Error {
  constructor(
    public kind: ApiErrorKind,
    message: string,
    public status = 0,
    public excType?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface Envelope<T> {
  ok: boolean
  data: T
  meta?: Record<string, any>
}

function stripHtml(s: string): string {
  return s.replace(/<[^>]*>/g, '').trim()
}

function parseServerMessages(raw?: string): string | null {
  if (!raw) return null
  try {
    const msgs = JSON.parse(raw) as string[]
    const parsed = msgs.map((m) => {
      try {
        const o = JSON.parse(m)
        return stripHtml(o.message ?? '')
      } catch {
        return stripHtml(m)
      }
    })
    return parsed.filter(Boolean).join('\n') || null
  } catch {
    return null
  }
}

function classify(status: number, excType?: string): ApiErrorKind {
  if (excType === 'CSRFTokenError' || excType === 'SessionExpired' || status === 401) return 'auth'
  if (status === 409 || excType === 'TimestampMismatchError') return 'conflict'
  if (status === 403 || excType === 'PermissionError') return 'permission'
  if (status === 404 || excType === 'DoesNotExistError') return 'not_found'
  if (status >= 500) return 'server'
  return 'validation'
}

/**
 * Connectivity signal for the sync engine. navigator.onLine can't be trusted
 * (captive portals, "lie-fi"), so actual request outcomes are reported too.
 */
export function reportConnectivity(online: boolean) {
  window.dispatchEvent(new CustomEvent('et-connectivity', { detail: online }))
}

async function request<T>(
  method: 'GET' | 'POST',
  path: string,
  args: Record<string, any> = {},
): Promise<Envelope<T>> {
  let url = `/api/method/${path}`
  const init: RequestInit = {
    method,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'X-Frappe-CSRF-Token': csrfToken(),
    } as Record<string, string>,
  }
  if (method === 'GET') {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(args)) {
      if (v === undefined || v === null) continue
      qs.set(k, typeof v === 'object' ? JSON.stringify(v) : String(v))
    }
    const q = qs.toString()
    if (q) url += `?${q}`
  } else {
    ;(init.headers as Record<string, string>)['Content-Type'] = 'application/json'
    init.body = JSON.stringify(args)
  }

  let res: Response
  try {
    res = await fetch(url, init)
  } catch (e) {
    reportConnectivity(false)
    throw new ApiError('network', 'You appear to be offline.', 0)
  }
  reportConnectivity(true)

  let body: any = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON (e.g. proxy error page) */
  }

  if (!res.ok) {
    const excType: string | undefined = body?.exc_type
    const msg =
      parseServerMessages(body?._server_messages) ??
      (typeof body?.message === 'string' ? body.message : null) ??
      `Request failed (${res.status})`
    throw new ApiError(classify(res.status, excType), msg, res.status, excType)
  }

  const env = body?.message as Envelope<T> | undefined
  if (!env || env.ok !== true) {
    throw new ApiError('server', 'Unexpected response from server.', res.status)
  }
  return env
}

export const api = {
  /** Returns `data` only. */
  async get<T>(path: string, args?: Record<string, any>): Promise<T> {
    return (await request<T>('GET', path, args)).data
  },
  async post<T>(path: string, args?: Record<string, any>): Promise<T> {
    return (await request<T>('POST', path, args)).data
  },
  /** Returns the full envelope (for paginated lists that carry `meta`). */
  raw: request,
}
