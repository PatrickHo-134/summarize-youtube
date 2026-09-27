import { fetchAuthSession, getCurrentUser, signOut } from 'aws-amplify/auth'

export async function getAuthToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession()
    return session.tokens?.idToken?.toString() ?? null
  } catch {
    return null
  }
}

export async function checkIsAuthenticated(): Promise<boolean> {
  try {
    await getCurrentUser()
    return true
  } catch {
    return false
  }
}

export async function handleSignOut(): Promise<void> {
  await signOut({ global: true })
  for (const storage of [localStorage, sessionStorage]) {
    const keysToRemove = Object.keys(storage).filter(
      (k) => k.startsWith('CognitoIdentityServiceProvider') || k.startsWith('amplify-')
    )
    keysToRemove.forEach((k) => storage.removeItem(k))
  }
}
