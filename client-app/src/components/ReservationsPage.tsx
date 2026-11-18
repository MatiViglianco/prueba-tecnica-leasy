import { useCallback, useEffect, useState } from 'react'
import { getProfile, listReservations } from '../api/endpoints'
import { errorMessage, isAuthError } from '../api/messages'
import type { Profile, Reservation } from '../api/types'
import { canCancel, formatSchedule, STATUS_LABELS } from '../reservations'
import { CancelReservationDialog } from './CancelReservationDialog'

interface ReservationsPageProps {
  token: string
  onLogout: (reason?: string) => void
}

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; profile: Profile; reservations: Reservation[] }

const SESSION_EXPIRED = 'Tu sesión expiró. Vuelve a ingresar.'

export function ReservationsPage({ token, onLogout }: ReservationsPageProps) {
  const [state, setState] = useState<LoadState>({ status: 'loading' })
  const [cancelling, setCancelling] = useState<Reservation | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const handleError = useCallback(
    (error: unknown) => {
      if (isAuthError(error)) {
        onLogout(SESSION_EXPIRED)
        return
      }
      setState({ status: 'error', message: errorMessage(error) })
    },
    [onLogout],
  )

  const load = useCallback(async () => {
    const [profile, reservations] = await Promise.all([
      getProfile(token),
      listReservations(token),
    ])
    return { profile, reservations }
  }, [token])

  useEffect(() => {
    // Ignore a response that arrives after unmount (or StrictMode's re-run).
    let ignore = false
    load()
      .then((data) => {
        if (!ignore) setState({ status: 'ready', ...data })
      })
      .catch((error: unknown) => {
        if (!ignore) handleError(error)
      })
    return () => {
      ignore = true
    }
  }, [load, handleError])

  function reload() {
    setState({ status: 'loading' })
    load()
      .then((data) => setState({ status: 'ready', ...data }))
      .catch(handleError)
  }

  function handleCancelled(updated: Reservation) {
    // The API returns the updated reservation, so the list is patched locally
    // instead of being fetched again.
    setState((current) =>
      current.status === 'ready'
        ? {
            ...current,
            reservations: current.reservations.map((reservation) =>
              reservation.id === updated.id ? updated : reservation,
            ),
          }
        : current,
    )
    setCancelling(null)
    setNotice(`Reserva en ${updated.room_name} cancelada.`)
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Mis reservas</h1>
          {state.status === 'ready' && <p className="muted">{state.profile.display_name}</p>}
        </div>
        <button className="btn" type="button" onClick={() => onLogout()}>
          Cerrar sesión
        </button>
      </header>

      {notice && (
        <p className="alert alert--success" role="status">
          {notice}
        </p>
      )}

      {state.status === 'loading' && <p className="muted">Cargando reservas…</p>}

      {state.status === 'error' && (
        <div className="alert alert--error stack" role="alert">
          <p>{state.message}</p>
          <div>
            <button className="btn" type="button" onClick={reload}>
              Reintentar
            </button>
          </div>
        </div>
      )}

      {state.status === 'ready' && state.reservations.length === 0 && (
        <p className="card muted">No tienes reservas.</p>
      )}

      {state.status === 'ready' && state.reservations.length > 0 && (
        <ul className="reservation-list">
          {state.reservations.map((reservation) => (
            <li key={reservation.id} className="card reservation">
              <div className="reservation__info">
                <strong>{reservation.room_name}</strong>
                <span className="muted">{formatSchedule(reservation)}</span>
                {reservation.cancel_reason && (
                  <span className="muted">Motivo: {reservation.cancel_reason}</span>
                )}
              </div>
              <div className="reservation__actions">
                <span className={`badge badge--${reservation.status}`}>
                  {STATUS_LABELS[reservation.status] ?? reservation.status}
                </span>
                {canCancel(reservation) && (
                  <button
                    className="btn btn--danger"
                    type="button"
                    onClick={() => {
                      setNotice(null)
                      setCancelling(reservation)
                    }}
                  >
                    Cancelar reserva
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {cancelling && (
        <CancelReservationDialog
          token={token}
          reservation={cancelling}
          onClose={() => setCancelling(null)}
          onCancelled={handleCancelled}
          onSessionExpired={() => onLogout(SESSION_EXPIRED)}
          onStale={() => {
            setCancelling(null)
            reload()
          }}
        />
      )}
    </main>
  )
}
