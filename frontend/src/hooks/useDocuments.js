import { useCallback, useEffect, useState } from 'react'
import { readApiResponse } from '../services/api.js'

function useDocuments() {
  const [documents, setDocuments] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadingName, setUploadingName] = useState('')
  const [deletingId, setDeletingId] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let isActive = true

    const fetchDocuments = async () => {
      try {
        const token = localStorage.getItem('documind_token')
        const response = await fetch('/api/documents', {
          headers: { Authorization: `Bearer ${token || ''}` },
        })
        const result = await readApiResponse(response)
        if (isActive) {
          setDocuments(result.data || [])
          setError('')
        }
      } catch (loadError) {
        if (isActive) setError(loadError.message || 'Impossible de charger les documents.')
      } finally {
        if (isActive) setIsLoading(false)
      }
    }

    fetchDocuments()
    return () => { isActive = false }
  }, [])

  const uploadFiles = useCallback(async (files) => {
    const token = localStorage.getItem('documind_token')
    if (!token) {
      setError('Votre session a expiré. Reconnectez-vous pour importer des documents.')
      return
    }

    setError('')
    setIsUploading(true)
    let uploadedCount = 0

    try {
      for (const file of files) {
        setUploadingName(file.name)
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch('/api/documents', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })
        const result = await readApiResponse(response)
        setDocuments((currentDocuments) => [result.data, ...currentDocuments])
        uploadedCount += 1
      }
    } catch (uploadError) {
      setError(uploadError.message || 'Le transfert a échoué. Réessayez.')
    } finally {
      setUploadingName('')
      setIsUploading(false)
    }

    return uploadedCount
  }, [])

  const deleteDocument = useCallback(async (documentId) => {
    const token = localStorage.getItem('documind_token')
    if (!token) {
      setError('Votre session a expiré. Reconnectez-vous pour supprimer des documents.')
      return false
    }

    setError('')
    setDeleteError('')
    setDeletingId(documentId)
    try {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE',
        headers: { Authorization: ['Bearer', token].join(' ') },
      })
      await readApiResponse(response)
      setDocuments((currentDocuments) =>
        currentDocuments.filter((document) => (document.id || document._id) !== documentId),
      )
      return true
    } catch (deleteError) {
      setDeleteError(deleteError.message || 'Impossible de supprimer ce document.')
      setError(deleteError.message || 'Impossible de supprimer ce document.')
      return false
    } finally {
      setDeletingId('')
    }
  }, [])

  return {
    deleteDocument,
    deleteError,
    deletingId,
    documents,
    error,
    isLoading,
    isUploading,
    uploadingName,
    uploadFiles,
  }
}

export default useDocuments
