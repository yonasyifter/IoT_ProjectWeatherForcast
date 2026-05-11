import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  onAuthStateChanged,
} from 'firebase/auth'
import { doc, getDoc } from 'firebase/firestore'
import { auth, db } from '@/utils/firebase'

export const useAdminAuthStore = defineStore('adminAuth', () => {
  const user = ref(null)          // Firebase user object
  const profile = ref(null)       // Firestore user doc
  const loading = ref(true)       // waiting for onAuthStateChanged
  const initialised = ref(false)

  const isLoggedIn = computed(() => !!user.value && profile.value?.role === 'admin')
  const displayName = computed(() => profile.value?.displayName || user.value?.email || 'Admin')
  const email = computed(() => user.value?.email || '')

  // ── Bootstrap: restore session from Firebase onAuthStateChanged ──────────
  function init() {
    return new Promise((resolve) => {
      const unsub = onAuthStateChanged(auth, async (firebaseUser) => {
        if (firebaseUser) {
          user.value = firebaseUser
          await fetchProfile(firebaseUser.uid)
          // Always keep a fresh token in localStorage so legacy code still works
          try {
            const fresh = await firebaseUser.getIdToken()
            localStorage.setItem('accessToken', fresh)
          } catch (e) {
            console.warn('Could not refresh token on init:', e)
          }
        } else {
          user.value = null
          profile.value = null
        }
        loading.value = false
        initialised.value = true
        unsub()
        resolve()
      })
    })
  }

  async function fetchProfile(uid) {
    try {
      const snap = await getDoc(doc(db, 'users', uid))
      profile.value = snap.exists() ? snap.data() : null
    } catch (e) {
      console.error('fetchProfile error:', e)
      profile.value = null
    }
  }

  // ── Login ─────────────────────────────────────────────────────────────────
  async function login(email, password) {
    const credential = await signInWithEmailAndPassword(auth, email, password)
    user.value = credential.user
    await fetchProfile(credential.user.uid)

    if (profile.value?.role !== 'admin') {
      await signOut(auth)
      user.value = null
      profile.value = null
      throw new Error('not-admin')
    }

    // Persist fresh token for FastAPI calls
    const token = await credential.user.getIdToken()
    localStorage.setItem('accessToken', token)
    localStorage.setItem('userSession', JSON.stringify({
      email: credential.user.email,
      uid: credential.user.uid,
      displayName: profile.value?.displayName || credential.user.email,
      role: 'admin',
      token,
      isActive: true,
    }))
  }

  // ── Logout ────────────────────────────────────────────────────────────────
  async function logout() {
    try { await signOut(auth) } catch (_) {}
    user.value = null
    profile.value = null
    localStorage.clear()
  }

  // ── Reset password ─────────────────────────────────────────────────────────
  async function resetPassword(emailAddress) {
    await sendPasswordResetEmail(auth, emailAddress)
  }

  return { user, profile, loading, initialised, isLoggedIn, displayName, email, init, login, logout, resetPassword }
})
