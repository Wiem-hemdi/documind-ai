import { Activity, Bot, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react'
import useAssistant from './useAssistant.js'
import './AssistantPanel.css'

function AssistantPanel() {
  const { checkAvailability, error, serviceName, status } = useAssistant()
  const isChecking = status === 'checking'
  const isAvailable = status === 'available'
  const statusLabel = isChecking
    ? 'Vérification en cours…'
    : isAvailable
      ? 'Service IA joignable'
      : status === 'unavailable'
        ? 'Service IA indisponible'
        : 'Connexion non vérifiée'
  const message = isAvailable
    ? `${serviceName} répond correctement. Ouvrez un document pour consulter son contenu et poser une question à l’assistant.`
    : error || 'Vérifiez que le service IA répond en lançant le test de connexion.'

  return (
    <section className="assistant-panel" aria-labelledby="assistant-title">
      <div className="assistant-heading">
        <span className="assistant-avatar"><Bot size={20} /></span>
        <div>
          <h2 id="assistant-title">Assistant IA</h2>
          <p>{statusLabel}</p>
        </div>
        <span className="assistant-sparkle"><Sparkles size={17} /></span>
      </div>

      <div className="assistant-message" role="status" aria-live="polite">
        <span className="assistant-message-icon"><Bot size={16} /></span>
        <p>{message}</p>
      </div>

      <button
        className="assistant-check-button"
        disabled={isChecking}
        onClick={checkAvailability}
        type="button"
      >
        {isChecking ? <LoaderCircle size={16} className="assistant-spinner" /> : <RefreshCw size={15} />}
        {isChecking ? 'Vérification…' : 'Tester la connexion IA'}
      </button>

      <div className={`assistant-connection-note${isAvailable ? ' connected' : ''}${status === 'unavailable' ? ' failed' : ''}`}>
        <Activity size={15} />
        <span>
          {isAvailable
            ? 'La conversation s’ouvre depuis un document de votre espace.'
            : 'Ce test vérifie uniquement que le service IA est joignable.'}
        </span>
      </div>
    </section>
  )
}

export default AssistantPanel
