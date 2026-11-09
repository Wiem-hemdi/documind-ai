import { useEffect, useRef, useState } from 'react'
import { Bot, Download, FileText, LoaderCircle, Send, Trash2, X } from 'lucide-react'
import { readApiResponse } from '../../services/api.js'
import ConfirmationDialog from '../ConfirmationDialog.jsx'
import './DocumentViewer.css'

function DocumentViewer({ document, onClose }) {
  const [previewUrl, setPreviewUrl] = useState('')
  const [isLoadingPreview, setIsLoadingPreview] = useState(true)
  const [previewError, setPreviewError] = useState('')
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [isAsking, setIsAsking] = useState(false)
  const [chatError, setChatError] = useState('')
  const [isConfirmingHistoryClear, setIsConfirmingHistoryClear] = useState(false)
  const [isClearingHistory, setIsClearingHistory] = useState(false)
  const messagesEndRef = useRef(null)
  const documentId = document.id || document._id
  const extension = (document.extension || '').replace('.', '').toLowerCase()

  useEffect(() => {
    const controller = new AbortController()
    let objectUrl = ''
    const loadPreview = async () => {
      try {
        const token = localStorage.getItem('documind_token')
        const response = await fetch(`/api/documents/${documentId}/file`, {
          headers: { Authorization: ['Bearer', token || ''].join(' ') },
          signal: controller.signal,
        })
        if (!response.ok) await readApiResponse(response)
        const fileBlob = await response.blob()
        objectUrl = URL.createObjectURL(fileBlob)
        setPreviewUrl(objectUrl)
      } catch (error) {
        if (!controller.signal.aborted) {
          setPreviewError(error.message || 'Impossible d’ouvrir le document.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoadingPreview(false)
      }
    }

    loadPreview()
    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [documentId])

  useEffect(() => {
    const controller = new AbortController()
    const loadHistory = async () => {
      try {
        const token = localStorage.getItem('documind_token')
        const response = await fetch(`/api/documents/${documentId}/history`, {
          headers: { Authorization: ['Bearer', token || ''].join(' ') },
          signal: controller.signal,
        })
        const result = await readApiResponse(response)
        setMessages((result.data || []).map((message) => ({
          id: message._id,
          role: message.role,
          text: message.content,
          createdAt: message.createdAt,
        })))
        setHistoryError('')
      } catch (error) {
        if (!controller.signal.aborted) {
          setHistoryError(error.message || 'Impossible de charger l’historique.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoadingHistory(false)
      }
    }

    loadHistory()
    return () => controller.abort()
  }, [documentId])

  useEffect(() => {
    const previousOverflow = window.document.body.style.overflow
    window.document.body.style.overflow = 'hidden'
    return () => {
      window.document.body.style.overflow = previousOverflow
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !isAsking && !isConfirmingHistoryClear) onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isAsking, isConfirmingHistoryClear, onClose])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages])

  const askQuestion = async (event) => {
    event.preventDefault()
    const prompt = question.trim()
    if (!prompt || isAsking) return

    const token = localStorage.getItem('documind_token')
    setChatError('')
    setIsAsking(true)

    try {
      const response = await fetch(`/api/documents/${documentId}/chat`, {
        method: 'POST',
        headers: {
          Authorization: ['Bearer', token || ''].join(' '),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: prompt }),
      })
      const result = await readApiResponse(response)
      const history = result.data.history || []
      const latestAssistantId = [...history].reverse().find((message) => message.role === 'assistant')?._id
      setMessages(history.map((message) => ({
        id: message._id,
        role: message.role,
        text: message.content,
        createdAt: message.createdAt,
        truncated: message._id === latestAssistantId && result.data.truncated,
      })))
      setQuestion('')
    } catch (error) {
      setChatError(error.message || 'La question n’a pas pu être traitée.')
    } finally {
      setIsAsking(false)
    }
  }

  const clearHistory = async () => {
    setIsClearingHistory(true)
    setChatError('')
    try {
      const token = localStorage.getItem('documind_token')
      const response = await fetch(`/api/documents/${documentId}/history`, {
        method: 'DELETE',
        headers: { Authorization: ['Bearer', token || ''].join(' ') },
      })
      await readApiResponse(response)
      setMessages([])
      setHistoryError('')
      setIsConfirmingHistoryClear(false)
    } catch (error) {
      setChatError(error.message || 'Impossible de supprimer l’historique.')
    } finally {
      setIsClearingHistory(false)
    }
  }

  return (
    <div className="document-viewer-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !isAsking && !isConfirmingHistoryClear) onClose()
    }}>
      <section
        aria-labelledby="document-viewer-title"
        aria-modal="true"
        className="document-viewer"
        role="dialog"
      >
        <header className="document-viewer-header">
          <div className="document-viewer-title">
            <span className="document-viewer-icon"><FileText size={18} /></span>
            <div>
              <h2 id="document-viewer-title" title={document.originalName}>{document.originalName}</h2>
            <p>Document original · Assistant IA</p>
            </div>
          </div>
          <button
            className="document-history-clear"
            disabled={!messages.length || isLoadingHistory || isAsking || isClearingHistory}
            onClick={() => setIsConfirmingHistoryClear(true)}
            type="button"
          >
            <Trash2 size={14} /> Vider l’historique
          </button>
          <button
            aria-label="Fermer la fenêtre"
            className="document-viewer-close"
            disabled={isAsking || isClearingHistory}
            onClick={onClose}
            type="button"
          >
            <X size={19} />
          </button>
        </header>

        <div className="document-viewer-body">
          <section aria-labelledby="document-content-title" className="document-content-pane">
            <h3 id="document-content-title">Contenu du document</h3>
            {isLoadingPreview ? (
              <div className="document-viewer-loading" role="status">
                <LoaderCircle className="assistant-spinner" size={20} />
                <span>Ouverture du document…</span>
              </div>
            ) : previewError ? (
              <p className="document-viewer-error" role="alert">{previewError}</p>
            ) : ['pdf', 'txt', 'md', 'csv'].includes(extension) ? (
              <iframe
                className="document-original-preview"
                src={previewUrl}
                title={`Aperçu de ${document.originalName}`}
              />
            ) : ['png', 'jpg', 'jpeg'].includes(extension) ? (
              <div className="document-image-preview">
                <img alt={document.originalName} src={previewUrl} />
              </div>
            ) : (
              <div className="document-preview-download">
                <span className="document-viewer-icon"><FileText size={22} /></span>
                <strong>Aperçu non disponible dans le navigateur</strong>
                <p>Le fichier original est prêt à être téléchargé pour l’ouvrir dans son application.</p>
                <a download={document.originalName} href={previewUrl}>
                  <Download size={15} /> Télécharger le fichier original
                </a>
              </div>
            )}
          </section>

          <section aria-labelledby="document-chat-title" className="document-chat-pane">
            <div className="document-chat-heading">
              <span className="assistant-avatar"><Bot size={18} /></span>
              <div>
                <h3 id="document-chat-title">Assistant sur ce document</h3>
                <p>Les réponses s’appuient sur le texte extrait.</p>
              </div>
            </div>

            <div aria-live="polite" className="document-chat-messages" role="log">
              {isLoadingHistory && (
                <div className="document-chat-pending" role="status">
                  <LoaderCircle className="assistant-spinner" size={16} /> Chargement de l’historique…
                </div>
              )}
              {historyError && <p className="document-chat-error" role="alert">{historyError}</p>}
              {!isLoadingHistory && !messages.length && (
                <p className="document-chat-empty">
                  Aucun échange enregistré. Posez une question, par exemple : « Quels sont les points principaux ? »
                </p>
              )}
              {messages.map((message, index) => (
                <article className={`document-chat-message ${message.role}`} key={message.id || `${index}-${message.role}`}>
                  <p>{message.text}</p>
                  {message.truncated && (
                    <small>La réponse utilise une partie seulement du document.</small>
                  )}
                  {message.createdAt && (
                    <time dateTime={message.createdAt}>
                      {new Intl.DateTimeFormat('fr-FR', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      }).format(new Date(message.createdAt))}
                    </time>
                  )}
                </article>
              ))}
              {isAsking && (
                <div className="document-chat-pending" role="status">
                  <LoaderCircle className="assistant-spinner" size={16} /> Analyse en cours…
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {chatError && <p className="document-chat-error" role="alert">{chatError}</p>}
            <form className="document-chat-form" onSubmit={askQuestion}>
              <textarea
                aria-label="Question sur le document"
                disabled={isLoadingHistory || isAsking}
                maxLength={2000}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Posez une question sur ce document…"
                value={question}
              />
              <button
                aria-label="Envoyer la question"
                disabled={!question.trim() || isAsking || isLoadingHistory}
                type="submit"
              >
                {isAsking ? <LoaderCircle className="assistant-spinner" size={17} /> : <Send size={16} />}
              </button>
            </form>
            <p className="document-chat-disclaimer">
              Le modèle peut se tromper. Vérifiez les informations importantes dans le document.
            </p>
          </section>
        </div>
      </section>
      {isConfirmingHistoryClear && (
        <ConfirmationDialog
          confirmLabel="Vider l’historique"
          description={`Les échanges enregistrés pour « ${document.originalName} » seront supprimés définitivement. Le fichier ne sera pas supprimé.`}
          error={chatError}
          isBusy={isClearingHistory}
          onCancel={() => setIsConfirmingHistoryClear(false)}
          onConfirm={clearHistory}
          title="Effacer cette conversation ?"
        />
      )}
    </div>
  )
}

export default DocumentViewer
