// The access token lives in sessionStorage: it survives a page refresh but is
// dropped when the tab closes. Storage can be unavailable (private mode,
// blocked site data), so every access is guarded and falls back to memory only.
const TOKEN_KEY = 'client-app:access-token'

export function loadToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function saveToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Keep working with the in-memory token.
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // Nothing to clear.
  }
}
