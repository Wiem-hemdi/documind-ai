import { useId } from 'react'
import { FileUp, LoaderCircle, UploadCloud } from 'lucide-react'
import useFileUpload from './useFileUpload.js'
import './UploadDropzone.css'

const acceptedFormats = '.pdf,.docx,.txt,.md,.csv,.xlsx,.pptx'

function UploadDropzone({ isUploading, onFilesSelected, uploadingName }) {
  const inputId = useId()
  const {
    inputRef,
    isDragging,
    onDragLeave,
    onDragOver,
    onDrop,
    onInputChange,
    openFilePicker,
    validationMessage,
  } = useFileUpload(onFilesSelected)

  return (
    <div className="upload-area-wrap">
      <div
        className={`upload-dropzone${isDragging ? ' is-dragging' : ''}${isUploading ? ' is-uploading' : ''}`}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          id={inputId}
          accept={acceptedFormats}
          className="upload-input"
          multiple
          onChange={onInputChange}
          type="file"
        />
        <span className="upload-icon">
          {isUploading ? <LoaderCircle className="upload-spinner" size={25} /> : <UploadCloud size={25} />}
        </span>
        <h3>{isUploading ? 'Import en cours…' : 'Déposez vos fichiers ici'}</h3>
        <p>{isUploading && uploadingName ? `Envoi de ${uploadingName}` : 'ou choisissez des documents depuis votre appareil'}</p>
        <button className="choose-files-button" disabled={isUploading} onClick={openFilePicker} type="button">
          <FileUp size={16} /> Parcourir les fichiers
        </button>
        <span className="upload-limits">PDF, DOCX, XLSX, PPTX, CSV et fichiers texte · 20 Mo max. par fichier</span>
      </div>
      {validationMessage && <p className="upload-validation" role="alert">{validationMessage}</p>}
    </div>
  )
}

export default UploadDropzone
