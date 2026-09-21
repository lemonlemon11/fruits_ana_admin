import { createLogger } from '../utils/logger'

const logger = createLogger('api')

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object') {
          const record = item as { msg?: unknown; loc?: unknown }
          if (typeof record.msg === 'string') {
            const loc = Array.isArray(record.loc) ? record.loc : []
            const field = loc.length ? loc[loc.length - 1] : null
            return typeof field === 'string' && field !== 'body'
              ? `${field}: ${record.msg}`
              : record.msg
          }
        }
        return String(item)
      })
      .join('；')
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail)
  }
  return String(detail)
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {})
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const method = options.method ?? 'GET'
  let response: Response
  try {
    response = await fetch(path, {
      credentials: 'include',
      ...options,
      headers,
    })
  } catch (caught) {
    logger.error('request error', { path, method, error: caught })
    throw caught
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    logger.error('request failed', {
      path,
      method,
      status: response.status,
      body: data,
    })
    const message =
      typeof data === 'object' && data !== null && 'detail' in data
        ? formatDetail((data as { detail: unknown }).detail)
        : `请求失败（${response.status}）`
    throw new ApiError(response.status, message)
  }

  return data as T
}

export function get<T>(path: string) {
  return api<T>(path)
}

export function post<T>(path: string, body?: unknown) {
  return api<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function patch<T>(path: string, body?: unknown) {
  return api<T>(path, {
    method: 'PATCH',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function put<T>(path: string, body?: unknown) {
  return api<T>(path, {
    method: 'PUT',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function del<T>(path: string) {
  return api<T>(path, { method: 'DELETE' })
}
