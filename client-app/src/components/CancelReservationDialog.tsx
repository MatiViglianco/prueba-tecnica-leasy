import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { cancelReservation } from '../api/endpoints'
import { errorMessage, isAuthError } from '../api/messages'
import type { Reservation } from '../api/types'
import { formatSchedule } from '../reservations'

const MAX_REASON_LENGTH = 500

// The reservation changed on the server since the list was loaded.
const STALE_CODES = new Set(['reservation_invalid_transition', 'reservation_not_found'])

interface CancelReservationDialogProps {
  token: string
  reservation: Reservation
  onClose: () => void
  onCancelled: (reservation: Reservation) => void
  onSessionExpired: () => void
  onStale: () => void
}

export function CancelReservationDialog({
  token,
  reservation,
  onClose,
  onCancelled,
  onSessionExpired,
  onStale,
}: CancelReservationDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stale, setStale] = useState(false)

  useEffect(() => {
    const dialog = dialogRef.current
    dialog?.showModal()
    return () => dialog?.close()
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = reason.trim()
    if (!trimmed) {
      // Quick feedback only; the API validates the reason as well.
      setError('Ingresa un motivo para cancelar.')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const updated = await cancelReservation(token, reservation.id, trimmed)
      onCancelled(updated)
    } catch (err) {
      if (isAuthError(err)) {
        onSessionExpired()
        return
      }
      const fieldMessage = err instanceof ApiError ? err.fieldError('reason') : undefined
      setError(fieldMessage ?? errorMessage(err))
      setStale(err instanceof ApiError && STALE_CODES.has(err.code))
      setSubmitting(false)
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="dialog"
      aria-labelledby="cancel-title"
      onCancel={(event) => {
        // Escape key: close through React state so it stays the source of truth.
        event.preventDefault()
        if (!submitting) onClose()
      }}
    >
      <form className="stack" onSubmit={handleSubmit} noValidate>
        <div>
          <h2 id="cancel-title">Cancelar reserva</h2>
          <p className="muted">
            {reservation.room_name} · {formatSchedule(reservation)}
          </p>
        </div>

        <label className="field">
          <span>Motivo</span>
          <textarea
            rows={4}
            maxLength={MAX_REASON_LENGTH}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={submitting || stale}
            autoFocus
          />
          <span className="muted hint">
            {reason.length}/{MAX_REASON_LENGTH}
          </span>
        </label>

        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}

        <div className="actions">
          {stale ? (
            <button className="btn btn--primary" type="button" onClick={onStale}>
              Actualizar lista
            </button>
          ) : (
            <>
              <button className="btn" type="button" onClick={onClose} disabled={submitting}>
                Volver
              </button>
              <button className="btn btn--danger" type="submit" disabled={submitting}>
                {submitting ? 'Cancelando…' : 'Confirmar cancelación'}
              </button>
            </>
          )}
        </div>
      </form>
    </dialog>
  )
}
