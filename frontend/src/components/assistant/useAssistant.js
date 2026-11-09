import { useState } from 'react'

function useAssistant() {
  const [status, setStatus] = useState('unchecked')
  const [serviceName, setServiceName] = useState('')
  const [error, setError] = useState('')

  const checkAvailability = async () => {
    setStatus('checking')
    setError('')

    try {
      const response = await fetch('/ai-api/health', {
        headers: { Accept: 'application/json' },
      })

      if (!response.ok) {
        throw new Error(`Le service IA a répondu avec une erreur HTTP ${response.status}.`)
      }

      const result = await response.json()
      if (!result || typeof result !== 'object' || Array.isArray(result)) {
        throw new Error('Le service IA a renvoyé une réponse invalide.')
      }

      setServiceName(result.service || 'Service IA')
      setStatus('available')
    } catch (checkError) {
      setStatus('unavailable')
      setError(
        checkError instanceof TypeError
          ? 'Impossible de joindre le service IA. Vérifiez qu’il est démarré.'
          : checkError.message || 'La vérification du service IA a échoué.',
      )
    }
  }

  return {
    checkAvailability,
    error,
    serviceName,
    status,
  }
}

export default useAssistant
