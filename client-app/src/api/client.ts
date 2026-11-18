import type { Problem } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

/**
 * Error thrown for every failed request. It always carries a Problem, even when
 * the server is unreachable or answers with something that is not JSON, so the
 * UI only has to handle one error shape.
 */
export class ApiError extends Error {
  readonly problem: Problem

  constructor(problem: Problem) {
    super(problem.detail)
    this.name = 'ApiError'
    this.problem = problem
  }

  get status(): number {
    return this.problem.status
  }

  get code(): string {
    return this.problem.code
  }

  /** First validation message for a body field, e.g. fieldError('reason'). */
  fieldError(field: string): string | undefined {
    return this.problem.errors?.find((error) => error.loc.at(-1) === field)?.msg
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  token?: string | null
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token } = options
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(localProblem(0, 'network_error', 'No se pudo conectar con el servidor.', path))
  }

  const payload: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      isProblem(payload)
        ? payload
        : localProblem(response.status, 'unexpected_error', 'Ocurrió un error inesperado.', path),
    )
  }

  return payload as T
}

function isProblem(value: unknown): value is Problem {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    'detail' in value &&
    'status' in value
  )
}

function localProblem(status: number, code: string, detail: string, path: string): Problem {
  return {
    type: `urn:client:problem:${code}`,
    title: 'Client Error',
    status,
    detail,
    code,
    instance: path,
    errors: null,
  }
}
