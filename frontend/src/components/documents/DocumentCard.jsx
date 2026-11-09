import { Eye, FileSpreadsheet, FileText, Presentation, Trash2 } from 'lucide-react'
import useDocumentFile from './useDocumentFile.js'
import './DocumentCard.css'

function renderFileIcon(extension) {
  if (['XLS', 'XLSX', 'CSV'].includes(extension)) {
    return <FileSpreadsheet size={20} strokeWidth={1.8} />
  }
  if (['PPT', 'PPTX'].includes(extension)) {
    return <Presentation size={20} strokeWidth={1.8} />
  }
  if (['PNG', 'JPG', 'JPEG'].includes(extension)) {
    return <Image size={20} strokeWidth={1.8} />
  }
  return <FileText size={20} strokeWidth={1.8} />
}

function DocumentCard({ document, isDeleting, onDelete, onOpen }) {
  const { createdAt, extension, fileSize, status, statusLabel } = useDocumentFile(document)

  return (
    <article className="document-card">
      <span className={`document-file-icon file-${extension.toLowerCase()}`}>
        {renderFileIcon(extension)}
      </span>
      <button className="document-info document-open-button" onClick={onOpen} type="button">
        <h3 title={document.originalName}>{document.originalName}</h3>
        <p>{extension} <span aria-hidden="true">·</span> {fileSize} <span aria-hidden="true">·</span> {createdAt}</p>
      </button>
      <span className={`document-status status-${status}`}>{statusLabel}</span>
      <div className="document-actions">
        <button
          aria-label={`Ouvrir ${document.originalName}`}
          className="document-action-button"
          onClick={onOpen}
          title="Lire et poser une question"
          type="button"
        >
          <Eye size={16} />
        </button>
        <button
          aria-label={`Supprimer ${document.originalName}`}
          className="document-action-button delete"
          disabled={isDeleting}
          onClick={onDelete}
          title="Supprimer le document"
          type="button"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </article>
  )
}

export default DocumentCard
