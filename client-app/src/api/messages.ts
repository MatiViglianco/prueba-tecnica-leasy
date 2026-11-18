import { ApiError } from './client'

// Friendly Spanish copy for the error codes the UI expects. Anything else
// falls back to the API's own `detail`, so new codes still show something useful.
const MESSAGES: Record<string, string> = {
  auth_invalid_credentials: 'Email o contraseña incorrectos.',
  auth_invalid_token: 'Tu sesión expiró. Vuelve a ingresar.',
  auth_not_authenticated: 'Tu sesión expiró. Vuelve a ingresar.',
  reservation_not_found: 'La reserva no existe o ya no está disponible.',
  reservation_invalid_transition: 'Esta reserva ya no se puede cancelar.',
  validation_error: 'Revisa los datos ingresados.',
  network_error: 'No se pudo conectar con el servidor. Intenta de nuevo.',
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.code] ?? error.problem.detail
  }
  return 'Ocurrió un error inesperado.'
}

export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401
}
