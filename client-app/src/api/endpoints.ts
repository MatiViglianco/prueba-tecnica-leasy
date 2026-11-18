import { apiRequest } from './client'
import type { Profile, Reservation, TokenResponse } from './types'

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
  })
}

export function getProfile(token: string): Promise<Profile> {
  return apiRequest<Profile>('/auth/me', { token })
}

export function listReservations(token: string): Promise<Reservation[]> {
  return apiRequest<Reservation[]>('/reservations/', { token })
}

export function cancelReservation(
  token: string,
  reservationId: string,
  reason: string,
): Promise<Reservation> {
  return apiRequest<Reservation>(`/reservations/${reservationId}/cancel`, {
    method: 'POST',
    body: { reason },
    token,
  })
}
