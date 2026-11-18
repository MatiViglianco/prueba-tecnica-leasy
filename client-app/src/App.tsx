import { useState } from 'react'
import { LoginPage } from './components/LoginPage'
import { ReservationsPage } from './components/ReservationsPage'
import { clearToken, loadToken, saveToken } from './session'

export default function App() {
  const [token, setToken] = useState<string | null>(loadToken)
  const [notice, setNotice] = useState<string | null>(null)

  function handleLoggedIn(newToken: string) {
    saveToken(newToken)
    setNotice(null)
    setToken(newToken)
  }

  function handleLogout(reason?: string) {
    clearToken()
    setNotice(reason ?? null)
    setToken(null)
  }

  if (!token) {
    return <LoginPage notice={notice} onLoggedIn={handleLoggedIn} />
  }

  return <ReservationsPage token={token} onLogout={handleLogout} />
}
