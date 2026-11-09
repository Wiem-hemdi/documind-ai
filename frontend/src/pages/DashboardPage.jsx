import { useState } from 'react'
import { FileText, Files, LogOut, MessageSquareText, ShieldCheck, Sparkles, Upload } from 'lucide-react'
import AssistantPanel from '../components/assistant/AssistantPanel.jsx'
import ConfirmationDialog from '../components/ConfirmationDialog.jsx'
import DocumentCard from '../components/documents/DocumentCard.jsx'
import DocumentViewer from '../components/documents/DocumentViewer.jsx'
import UploadDropzone from '../components/documents/UploadDropzone.jsx'
import useDocuments from '../hooks/useDocuments.js'
import useDashboard from './useDashboard.js'
import './DashboardPage.css'

function formatTotalSize(documents) {
  const totalBytes = documents.reduce((total, document) => total + (document.size || 0), 0)
  if (totalBytes < 1024 * 1024) return `${(totalBytes / 1024).toFixed(0)} Ko`
  return `${(totalBytes / (1024 * 1024)).toFixed(1)} Mo`
}

function DashboardPage() {
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [pendingDeleteDocument, setPendingDeleteDocument] = useState(null)
  const { firstName, signOut, today, user } = useDashboard()
  const {
    deleteDocument,
    deleteError,
    deletingId,
    documents,
    error,
    isLoading,
    isUploading,
    uploadingName,
    uploadFiles,
  } = useDocuments()
  const initials = `${user?.firstName?.[0] || ''}${user?.lastName?.[0] || ''}`.toUpperCase() || 'U'
  const readyDocuments = documents.filter((document) => document.status === 'ready').length

  const confirmDeleteDocument = async () => {
    if (!pendingDeleteDocument) return
    const documentId = pendingDeleteDocument.id || pendingDeleteDocument._id
    const deleted = await deleteDocument(documentId)
    if (deleted && (selectedDocument?.id || selectedDocument?._id) === documentId) {
      setSelectedDocument(null)
    }
    if (deleted) setPendingDeleteDocument(null)
  }

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <span className="dashboard-brand-mark"><FileText size={19} /></span>
          <span>documind<span className="brand-dot">.</span></span>
        </div>

        <p className="sidebar-label">Espace de travail</p>
        <nav className="sidebar-nav" aria-label="Navigation principale">
          <div className="sidebar-nav-item active" aria-current="page">
            <Files size={17} /> Mes documents
          </div>
          <div className="sidebar-nav-item">
            <MessageSquareText size={17} /> Assistant IA
          </div>
        </nav>

        <div className="sidebar-bottom">
          <ShieldCheck size={16} />
          <p>Vos fichiers sont privés et associés à votre compte.</p>
        </div>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="breadcrumb">Espace de travail <span aria-hidden="true">/</span> <strong>Mes documents</strong></div>
          <div className="account-controls">
            <div className="account-user">
              <span className="account-avatar" aria-hidden="true">{initials}</span>
              <span className="account-name">{user?.firstName} {user?.lastName}</span>
            </div>
            <button className="signout-button" onClick={signOut} type="button" title="Se déconnecter">
              <LogOut size={15} /> <span>Déconnexion</span>
            </button>
          </div>
        </header>

        <main className="dashboard-content">
          <section className="dashboard-greeting">
            <div>
              <p className="dashboard-date">{today}</p>
              <h1>Bonjour, <span>{firstName}</span> 👋</h1>
              <p className="dashboard-subtitle">Importez vos documents pour les retrouver au même endroit.</p>
            </div>
            <div className="dashboard-badge"><span /> Assistant IA prêt pour vos fichiers</div>
          </section>

          <section className="dashboard-stats" aria-label="Résumé de votre espace">
            <article className="stat-card">
              <span className="stat-icon"><Files size={19} /></span>
              <span><strong className="stat-value">{documents.length}</strong><small className="stat-label">Document{documents.length > 1 ? 's' : ''} importé{documents.length > 1 ? 's' : ''}</small></span>
            </article>
            <article className="stat-card">
              <span className="stat-icon green"><ShieldCheck size={19} /></span>
              <span><strong className="stat-value">{formatTotalSize(documents)}</strong><small className="stat-label">Espace utilisé</small></span>
            </article>
            <article className="stat-card">
              <span className="stat-icon orange"><Sparkles size={19} /></span>
              <span><strong className="stat-value">{readyDocuments}</strong><small className="stat-label">Prêts à consulter</small></span>
            </article>
          </section>

          <div className="workspace-grid">
            <div className="dashboard-panel">
              <div className="panel-heading">
                <div>
                  <h2>Ajouter des documents</h2>
                  <p>Importez un ou plusieurs fichiers pour commencer.</p>
                </div>
                <Upload size={18} color="#7669cf" />
              </div>
              <UploadDropzone
                isUploading={isUploading}
                onFilesSelected={uploadFiles}
                uploadingName={uploadingName}
              />
              {error && <p className="upload-error" role="alert">{error}</p>}

              <section className="documents-section" aria-labelledby="documents-title">
                <div className="panel-heading documents-heading">
                  <div>
                    <h2 id="documents-title">Documents récents</h2>
                    <p>Vos fichiers importés sont conservés dans votre espace.</p>
                  </div>
                  <span className="document-count">{documents.length}</span>
                </div>

                {isLoading ? (
                  <div className="documents-loading" role="status"><p>Chargement de vos documents…</p></div>
                ) : documents.length ? (
                  <div className="documents-list">
                    {documents.map((document) => (
                      <DocumentCard
                        document={document}
                        isDeleting={deletingId === (document.id || document._id)}
                        key={document.id || document._id}
                        onDelete={() => setPendingDeleteDocument(document)}
                        onOpen={() => setSelectedDocument(document)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="documents-empty">
                    <FileText size={23} />
                    <strong>Votre espace est encore vide</strong>
                    <p>Les documents importés apparaîtront ici.</p>
                  </div>
                )}
              </section>
            </div>

            <AssistantPanel documentCount={documents.length} />
          </div>
        </main>
      </div>
      {selectedDocument && (
        <DocumentViewer
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}
      {pendingDeleteDocument && (
        <ConfirmationDialog
          confirmLabel="Supprimer le fichier"
          description={`« ${pendingDeleteDocument.originalName} » et son historique de conversation seront supprimés définitivement.`}
          error={deleteError}
          isBusy={deletingId === (pendingDeleteDocument.id || pendingDeleteDocument._id)}
          onCancel={() => setPendingDeleteDocument(null)}
          onConfirm={confirmDeleteDocument}
          title="Supprimer ce document ?"
        />
      )}
    </div>
  )
}

export default DashboardPage
