export type ReservationStatus = 'requested' | 'confirmed' | 'on_hold' | 'cancelled'

export interface Reservation {
  id: string
  room_name: string
  status: ReservationStatus
  starts_at: string
  ends_at: string
  cancel_reason: string | null
}

export interface Profile {
  id: string
  email: string
  display_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ProblemFieldError {
  loc: string[]
  msg: string
  type: string
}

/** Error body returned by the API (see API_CONTRACT.md). */
export interface Problem {
  type: string
  title: string
  status: number
  detail: string
  code: string
  instance: string
  errors: ProblemFieldError[] | null
}
