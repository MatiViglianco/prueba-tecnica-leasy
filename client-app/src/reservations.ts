import type { Reservation, ReservationStatus } from './api/types'

export const STATUS_LABELS: Record<ReservationStatus, string> = {
  requested: 'Solicitada',
  confirmed: 'Confirmada',
  on_hold: 'En espera',
  cancelled: 'Cancelada',
}

// Mirrors RESERVATION_CANCELLABLE_STATUSES in the backend. It only decides
// whether to show the button; the API remains the source of truth.
const CANCELLABLE_STATUSES: ReadonlySet<ReservationStatus> = new Set([
  'requested',
  'confirmed',
  'on_hold',
])

export function canCancel(reservation: Reservation): boolean {
  return CANCELLABLE_STATUSES.has(reservation.status)
}

const dateTimeFormat = new Intl.DateTimeFormat('es-PE', {
  dateStyle: 'medium',
  timeStyle: 'short',
})
const timeFormat = new Intl.DateTimeFormat('es-PE', { timeStyle: 'short' })

export function formatSchedule(reservation: Reservation): string {
  const start = new Date(reservation.starts_at)
  const end = new Date(reservation.ends_at)
  return `${dateTimeFormat.format(start)} – ${timeFormat.format(end)}`
}
