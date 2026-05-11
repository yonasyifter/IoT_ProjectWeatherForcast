/**
 * auth-handler.js — compatibility shim
 *
 * The admin app previously used FastAPI-based auth via this file.
 * It now uses Firebase Auth through adminAuthStore (Pinia).
 * This shim keeps any legacy imports from breaking while the
 * store is the single source of truth.
 */
export { useAdminAuthStore } from '@/auth/adminAuthStore'

// Legacy named exports kept for backwards compatibility
export function getUserSession() {
  const s = localStorage.getItem('userSession')
  return s ? JSON.parse(s) : null
}

export function isAuthenticated() {
  const session = getUserSession()
  return !!(session?.isActive && session?.role === 'admin')
}

export function requireAuth() {
  return isAuthenticated()
}

export async function initializeAuth() {
  return isAuthenticated()
}

export function decodeToken(token = null) {
  try {
    const t = token || localStorage.getItem('accessToken')
    if (!t) return null
    const payload = t.split('.')[1]
    const padded = payload + '=='.substring(0, (4 - payload.length % 4) % 4)
    return JSON.parse(atob(padded))
  } catch { return null }
}

export function getUserIdFromToken() {
  const d = decodeToken()
  return d?.sub || d?.uid || d?.user_id || null
}

export function getTokenClaims() {
  return decodeToken()
}

export async function logout() {
  localStorage.clear()
  window.location.reload()
}

export async function getAllUsersData() { return [] }
export async function getUserByEmail() { return null }
export async function getUserData() { return null }
