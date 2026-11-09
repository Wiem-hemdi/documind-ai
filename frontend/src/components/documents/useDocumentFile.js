const STATUS_LABELS = {
  uploaded: 'À interpréter',
  processing: 'Analyse en cours',
  ready: 'Prêt',
  failed: 'À réessayer',
}

function formatFileSize(size) {
  if (size < 1024) return `${size} o`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} Ko`
  return `${(size / (1024 * 1024)).toFixed(1)} Mo`
}

function useDocumentFile(document) {
  const extension = (document.extension || '').replace('.', '').toUpperCase()
  const createdAt = new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(document.createdAt))

  return {
    createdAt,
    extension: extension || 'FICHIER',
    fileSize: formatFileSize(document.size || 0),
    statusLabel: STATUS_LABELS[document.status] || 'Importé',
    status: document.status || 'uploaded',
  }
}

export default useDocumentFile
