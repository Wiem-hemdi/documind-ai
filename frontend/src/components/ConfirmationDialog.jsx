import { useEffect, useRef } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import './ConfirmationDialog.css'

function ConfirmationDialog({
  title,
  description,
  confirmLabel = 'Supprimer',
  isBusy = false,
  error = '',
  onConfirm,
  onCancel,
}) {
  const cancelButtonRef = useRef(null)

  useEffect(() => {
    cancelButtonRef.current?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !isBusy) onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isBusy, onCancel])

  return (
    <div
      className="confirmation-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isBusy) onCancel()
      }}
    >
      <section
        aria-describedby="confirmation-description"
        aria-labelledby="confirmation-title"
        aria-modal="true"
        className="confirmation-dialog"
        role="alertdialog"
      >
        <button
          aria-label="Fermer la confirmation"
          className="confirmation-close"
          disabled={isBusy}
          onClick={onCancel}
          type="button"
        >
          <X size={17} />
        </button>
        <span className="confirmation-icon"><AlertTriangle size={23} /></span>
        <h2 id="confirmation-title">{title}</h2>
        <p id="confirmation-description">{description}</p>
        {error && <p className="confirmation-error" role="alert">{error}</p>}
        <div className="confirmation-actions">
          <button
            className="confirmation-cancel"
            disabled={isBusy}
            onClick={onCancel}
            ref={cancelButtonRef}
            type="button"
          >
            Annuler
          </button>
          <button
            className="confirmation-submit"
            disabled={isBusy}
            onClick={onConfirm}
            type="button"
          >
            {isBusy ? 'Suppression…' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}

export default ConfirmationDialog
