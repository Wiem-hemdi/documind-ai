import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function useDashboard() {
  const navigate = useNavigate()

  useEffect(() => {
    document.title = 'Mes documents | DocuMind AI'
    return () => { document.title = 'Connexion | DocuMind AI' }
  }, [])

  let user = null

  try {
    user = JSON.parse(localStorage.getItem('documind_user') || 'null')
  } catch {
    user = null
  }

  const signOut = () => {
    localStorage.removeItem('documind_token')
    localStorage.removeItem('documind_user')
    navigate('/login', { replace: true })
  }

  const firstName = user?.firstName || 'là'
  const today = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date())

  return { firstName, signOut, today, user }
}

export default useDashboard
