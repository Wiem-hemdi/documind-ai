import { useRef, useState } from 'react'

const MAX_FILE_SIZE = 20 * 1024 * 1024
const SUPPORTED_EXTENSIONS = new Set([
  'pdf', 'docx', 'txt', 'md', 'csv', 'xlsx', 'pptx',
])

function getExtension(fileName) {
  return fileName.split('.').pop()?.toLowerCase() || ''
}

function useFileUpload(onFilesSelected) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [validationMessage, setValidationMessage] = useState('')

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || [])
    const acceptedFiles = []
    const rejectedFiles = []

    for (const file of files) {
      const extension = getExtension(file.name)
      if (!SUPPORTED_EXTENSIONS.has(extension)) {
        rejectedFiles.push(`${file.name} : format non pris en charge`)
      } else if (file.size > MAX_FILE_SIZE) {
        rejectedFiles.push(`${file.name} : dépasse la limite de 20 Mo`)
      } else {
        acceptedFiles.push(file)
      }
    }

    setValidationMessage(rejectedFiles.join('. '))
    if (acceptedFiles.length) onFilesSelected(acceptedFiles)
  }

  const onDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  const onDragOver = (event) => {
    event.preventDefault()
    setIsDragging(true)
  }

  const onDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) setIsDragging(false)
  }

  const onInputChange = (event) => {
    handleFiles(event.target.files)
    event.target.value = ''
  }

  return {
    inputRef,
    isDragging,
    onDragLeave,
    onDragOver,
    onDrop,
    onInputChange,
    openFilePicker: () => inputRef.current?.click(),
    validationMessage,
  }
}

export default useFileUpload
