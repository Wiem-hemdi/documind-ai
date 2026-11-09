import { useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  LockKeyhole,
  Mail,
  ScanText,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { readApiResponse } from '../../services/api.js'

const initialFields = {
  firstName: '',
  lastName: '',
  email: '',
  password: '',
  confirmPassword: '',
}

function getStoredUser() {
  try {
    const savedUser = localStorage.getItem('documind_user')
    return savedUser ? JSON.parse(savedUser) : null
  } catch {
    return null
  }
}

function AuthForm({ mode }) {
  const navigate = useNavigate()
  const isRegister = mode === 'register'
  const [fields, setFields] = useState(initialFields)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [user, setUser] = useState(getStoredUser)

  const updateField = (event) => {
    const { name, value } = event.target
    setFields((currentFields) => ({ ...currentFields, [name]: value }))
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (isRegister && fields.password !== fields.confirmPassword) {
      setError('Les mots de passe ne correspondent pas.')
      return
    }

    setIsSubmitting(true)

    try {
      const requestBody = isRegister
        ? {
            firstName: fields.firstName.trim(),
            lastName: fields.lastName.trim(),
            email: fields.email.trim(),
            password: fields.password,
          }
        : { email: fields.email.trim(), password: fields.password }

      const response = await fetch(`/api/auth/${isRegister ? 'register' : 'login'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      const result = await readApiResponse(response)
      if (!result.data?.token || !result.data?.user) {
        throw new Error('La réponse de connexion est incomplète. Vérifiez la configuration du backend.')
      }

      localStorage.setItem('documind_token', result.data.token)
      localStorage.setItem('documind_user', JSON.stringify(result.data.user))
      navigate('/documents')
    } catch (requestError) {
      setError(
        requestError.message ||
          'Impossible de contacter le serveur. Vérifiez votre connexion et réessayez.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('documind_token')
    localStorage.removeItem('documind_user')
    setUser(null)
  }

  return (
    <main className="auth-page">
      <aside className="auth-aside" aria-label="Présentation de DocuMind">
        <Link className="brand" to="/login" aria-label="DocuMind, accueil">
          <span className="brand-icon"><FileText size={22} strokeWidth={2.2} /></span>
          <span>documind<span className="brand-dot">.</span></span>
        </Link>

        <div className="aside-content">
          <span className="eyebrow"><Sparkles size={14} /> Votre espace documentaire intelligent</span>
          <h1>Vos documents.<br />Enfin <span>à portée de sens.</span></h1>
          <p className="aside-description">
            Retrouvez, comprenez et exploitez vos documents dans un espace conçu pour vous.
          </p>

          <div className="feature-list">
            <div className="feature-item">
              <span className="feature-icon"><ScanText size={18} /></span>
              <span><strong>Tout retrouver</strong><small>Vos informations, au même endroit</small></span>
            </div>
            <div className="feature-item">
              <span className="feature-icon"><Sparkles size={18} /></span>
              <span><strong>Aller à l’essentiel</strong><small>Des réponses claires à vos questions</small></span>
            </div>
            <div className="feature-item">
              <span className="feature-icon"><ShieldCheck size={18} /></span>
              <span><strong>Garder le contrôle</strong><small>Un espace personnel et sécurisé</small></span>
            </div>
          </div>
        </div>

        <p className="aside-footer">Un espace plus clair pour vos idées et vos documents.</p>
        <span className="decor decor-one" aria-hidden="true" />
        <span className="decor decor-two" aria-hidden="true" />
      </aside>

      <section className="auth-main">
        <div className="auth-card">
          <Link className="brand brand-mobile" to="/login" aria-label="DocuMind, accueil">
            <span className="brand-icon"><FileText size={20} strokeWidth={2.2} /></span>
            <span>documind<span className="brand-dot">.</span></span>
          </Link>

          {user ? (
            <div className="success-state" role="status">
              <span className="success-icon"><CheckCircle2 size={30} /></span>
              <p className="form-eyebrow">Session active</p>
              <h2>Ravi de vous retrouver, {user.firstName}.</h2>
              <p className="form-description">Vous êtes connecté avec {user.email}.</p>
              <Link className="submit-button" to="/documents">
                Ouvrir mes documents <ArrowRight size={17} />
              </Link>
              <button className="submit-button" type="button" onClick={handleLogout}>
                Se déconnecter <ArrowRight size={17} />
              </button>
            </div>
          ) : (
            <>
              <div className="form-heading">
                <p className="form-eyebrow">{isRegister ? 'Commencez ici' : 'Bon retour parmi nous'}</p>
                <h2>{isRegister ? 'Créez votre compte' : 'Connectez-vous'}</h2>
                <p className="form-description">
                  {isRegister
                    ? 'Quelques informations et votre espace sera prêt.'
                    : 'Accédez à votre espace documentaire.'}
                </p>
              </div>

              <form className="auth-form" onSubmit={handleSubmit}>
                {isRegister && (
                  <div className="name-fields">
                    <label className="field-group">
                      <span>Prénom</span>
                      <span className="input-wrap">
                        <UserRound size={17} aria-hidden="true" />
                        <input
                          autoComplete="given-name"
                          name="firstName"
                          onChange={updateField}
                          placeholder="Camille"
                          required
                          value={fields.firstName}
                        />
                      </span>
                    </label>
                    <label className="field-group">
                      <span>Nom</span>
                      <span className="input-wrap">
                        <input
                          autoComplete="family-name"
                          name="lastName"
                          onChange={updateField}
                          placeholder="Martin"
                          required
                          value={fields.lastName}
                        />
                      </span>
                    </label>
                  </div>
                )}

                <label className="field-group">
                  <span>Adresse e-mail</span>
                  <span className="input-wrap">
                    <Mail size={17} aria-hidden="true" />
                    <input
                      autoComplete="email"
                      name="email"
                      onChange={updateField}
                      placeholder="vous@exemple.fr"
                      required
                      type="email"
                      value={fields.email}
                    />
                  </span>
                </label>

                <label className="field-group">
                  <span>Mot de passe</span>
                  <span className="input-wrap">
                    <LockKeyhole size={17} aria-hidden="true" />
                    <input
                      autoComplete={isRegister ? 'new-password' : 'current-password'}
                      minLength={isRegister ? 8 : undefined}
                      name="password"
                      onChange={updateField}
                      placeholder={isRegister ? '8 caractères minimum' : 'Votre mot de passe'}
                      required
                      type="password"
                      value={fields.password}
                    />
                  </span>
                </label>

                {isRegister && (
                  <label className="field-group">
                    <span>Confirmer le mot de passe</span>
                    <span className="input-wrap">
                      <LockKeyhole size={17} aria-hidden="true" />
                      <input
                        autoComplete="new-password"
                        minLength={8}
                        name="confirmPassword"
                        onChange={updateField}
                        placeholder="Saisissez-le à nouveau"
                        required
                        type="password"
                        value={fields.confirmPassword}
                      />
                    </span>
                  </label>
                )}

                {error && <p className="form-error" role="alert">{error}</p>}

                <button className="submit-button" disabled={isSubmitting} type="submit">
                  {isSubmitting
                    ? 'Veuillez patienter…'
                    : isRegister
                      ? 'Créer mon compte'
                      : 'Se connecter'}
                  {!isSubmitting && <ArrowRight size={17} />}
                </button>
              </form>

              <p className="auth-switch">
                {isRegister ? 'Vous avez déjà un compte ?' : 'Pas encore de compte ?'}{' '}
                <Link to={isRegister ? '/login' : '/register'}>
                  {isRegister ? 'Se connecter' : 'Créer un compte'}
                </Link>
              </p>
              <p className="privacy-note"><ShieldCheck size={15} /> Vos données restent protégées.</p>
            </>
          )}
        </div>
        <p className="mobile-footer">© {new Date().getFullYear()} DocuMind AI</p>
      </section>
    </main>
  )
}

export default AuthForm