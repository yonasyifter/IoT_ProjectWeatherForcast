<template>
  <div class="auth-wrapper">
    <!-- Animated background blobs -->
    <div class="bg-blob blob-1"></div>
    <div class="bg-blob blob-2"></div>

    <Transition name="card" mode="out-in">

      <!-- ── LOGIN CARD ─────────────────────────────── -->
      <div v-if="view === 'login'" key="login" class="auth-card">
        <div class="text-center mb-4">
          <div class="logo-icon mx-auto mb-3">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" stroke="white" stroke-width="1.5"/>
              <path d="M12 2v20M3 7l9 5 9-5" stroke="white" stroke-width="1" opacity=".4"/>
            </svg>
          </div>
          <h1 class="card-title">IOT Smart Park</h1>
          <p class="card-subtitle">Park Administration System</p>
        </div>

        <div v-if="error" class="alert-error mb-3">
          <IconAlert />
          {{ error }}
        </div>

        <div class="mb-3">
          <label class="form-label">Email</label>
          <div class="input-wrapper">
            <IconUser class="input-icon" />
            <input v-model="loginEmail" type="email" class="form-input"
              placeholder="admin@smartpark.it" @keyup.enter="handleLogin"
              autocomplete="email" />
          </div>
        </div>

        <div class="mb-4">
          <label class="form-label">Password</label>
          <div class="input-wrapper">
            <IconLock class="input-icon" />
            <input v-model="loginPassword" :type="showPw ? 'text' : 'password'"
              class="form-input" placeholder="••••••••"
              @keyup.enter="handleLogin" autocomplete="current-password" />
            <button class="toggle-pw" @click="showPw = !showPw" type="button">
              <IconEye v-if="!showPw" /><IconEyeOff v-else />
            </button>
          </div>
        </div>

        <button class="btn-primary w-100 mb-3" @click="handleLogin" :disabled="loading">
          <span v-if="loading" class="spinner me-2"></span>
          {{ loading ? 'Signing in...' : 'Sign In' }}
        </button>

        <p class="text-center register-link">
          <button class="link-btn" @click="view = 'reset'">Forgot password?</button>
          <span class="mx-2 opacity-25">|</span>
          <button class="link-btn" @click="view = 'register'">Create account</button>
        </p>
      </div>

      <!-- ── RESET PASSWORD CARD ────────────────────── -->
      <div v-else-if="view === 'reset'" key="reset" class="auth-card">
        <div class="text-center mb-4">
          <div class="logo-icon mx-auto mb-3" style="background: linear-gradient(135deg, #e67e22, #c0392b)">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="11" width="18" height="11" rx="2" stroke="white" stroke-width="1.5"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="1.5" fill="white"/>
            </svg>
          </div>
          <h1 class="card-title">Reset Password</h1>
          <p class="card-subtitle">We'll send a reset link to your email</p>
        </div>

        <div v-if="resetError" class="alert-error mb-3"><IconAlert />{{ resetError }}</div>
        <div v-if="resetSuccess" class="alert-success mb-3">
          <IconCheck />
          Reset link sent! Check your inbox.
        </div>

        <div class="mb-4">
          <label class="form-label">Admin Email</label>
          <div class="input-wrapper">
            <IconUser class="input-icon" />
            <input v-model="resetEmail" type="email" class="form-input"
              placeholder="admin@smartpark.it" @keyup.enter="handleReset"
              autocomplete="email" />
          </div>
        </div>

        <button class="btn-primary w-100 mb-3" @click="handleReset" :disabled="resetLoading || resetSuccess">
          <span v-if="resetLoading" class="spinner me-2"></span>
          {{ resetLoading ? 'Sending...' : 'Send Reset Link' }}
        </button>

        <p class="text-center register-link">
          <button class="link-btn" @click="view = 'login'">← Back to login</button>
        </p>
      </div>

      <!-- ── REGISTER CARD ────────────────────── -->
      <div v-else-if="view === 'register'" key="register" class="auth-card">
        <div v-if="regSuccess" class="text-center">
          <div class="logo-icon mx-auto mb-3" style="background: linear-gradient(135deg, #2f9e44, #1e7a34); border-radius: 50%;">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6 9 17l-5-5"/>
            </svg>
          </div>
          <h1 class="card-title mb-2">Account Created!</h1>
          <p class="card-subtitle mb-4" style="text-transform:none;letter-spacing:0;font-size:0.95rem;color:rgba(255,255,255,0.6);">
            Your park admin account is ready. You can now sign in.
          </p>
          <button class="btn-primary w-100" @click="view = 'login'">
            Go to Login
          </button>
        </div>

        <template v-else>
          <div class="text-center mb-4">
            <div class="logo-icon mx-auto mb-3">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" stroke="white" stroke-width="1.5"/>
                <path d="M12 2v20M3 7l9 5 9-5" stroke="white" stroke-width="1" opacity=".4"/>
              </svg>
            </div>
            <h1 class="card-title">Create Account</h1>
            <p class="card-subtitle">Register as a Park Administrator</p>
          </div>

          <div v-if="regError" class="alert-error mb-3">
            <IconAlert />
            {{ regError }}
          </div>

          <div class="mb-3">
            <label class="form-label">Username</label>
            <div class="input-wrapper">
              <IconUser class="input-icon" />
              <input v-model="regUsername" type="text" class="form-input"
                placeholder="Choose a username" autocomplete="username" />
            </div>
            <p class="text-secondary small opacity-50" style="font-size: 0.7rem; margin-top: 4px;">Minimum 3 characters</p>
          </div>

          <div class="mb-2">
            <label class="form-label">Password</label>
            <div class="input-wrapper">
              <IconLock class="input-icon" />
              <input v-model="regPassword" :type="regShowPw ? 'text' : 'password'"
                class="form-input" placeholder="Create a password"
                autocomplete="new-password" />
              <button class="toggle-pw" @click="regShowPw = !regShowPw" type="button">
                <IconEye v-if="!regShowPw" /><IconEyeOff v-else />
              </button>
            </div>
          </div>

          <div v-if="regPassword" class="d-flex align-items-center gap-2 mb-3">
            <div class="flex-grow-1" style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;">
              <div :style="{ width: (getPasswordStrength(regPassword).level / 4 * 100) + '%', background: getPasswordStrength(regPassword).color }"
                style="height:100%; transition: width 0.3s ease, background 0.3s ease;"></div>
            </div>
            <span class="small fw-bold" :style="{ color: getPasswordStrength(regPassword).color, fontSize: '0.7rem' }">
              {{ getPasswordStrength(regPassword).label }}
            </span>
          </div>

          <div class="mb-4">
            <label class="form-label">Confirm Password</label>
            <div class="input-wrapper">
              <IconLock class="input-icon" />
              <input v-model="regConfirmPassword" type="password" class="form-input"
                :class="{ 'border-success': regConfirmPassword && regConfirmPassword === regPassword, 'border-danger': regConfirmPassword && regConfirmPassword !== regPassword }"
                placeholder="Repeat your password" autocomplete="new-password"
                @keyup.enter="handleRegister" />
            </div>
          </div>

          <button class="btn-primary w-100 mb-3" @click="handleRegister" :disabled="regLoading">
            <span v-if="regLoading" class="spinner me-2"></span>
            {{ regLoading ? 'Creating account...' : 'Create Account' }}
          </button>

          <p class="text-center register-link">
            Already have an account?
            <button class="link-btn" @click="view = 'login'">Sign in</button>
          </p>
        </template>
      </div>

    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAdminAuthStore } from '@/auth/adminAuthStore'

const emit = defineEmits(['login-success'])
const store = useAdminAuthStore()

const view = ref('login')

// Login state
const loginEmail = ref('')
const loginPassword = ref('')
const showPw = ref(false)
const loading = ref(false)
const error = ref('')

// Reset state
const resetEmail = ref('')
const resetLoading = ref(false)
const resetError = ref('')
const resetSuccess = ref(false)

// Registration state
const regUsername = ref('')
const regPassword = ref('')
const regConfirmPassword = ref('')
const regLoading = ref(false)
const regError = ref('')
const regSuccess = ref(false)
const regShowPw = ref(false)

async function handleLogin() {
  error.value = ''
  if (!loginEmail.value || !loginPassword.value) {
    error.value = 'Please enter your email and password.'
    return
  }
  loading.value = true
  try {
    await store.login(loginEmail.value.trim(), loginPassword.value)
    emit('login-success')
  } catch (e) {
    if (e.message === 'not-admin') {
      error.value = 'Access denied. This account does not have admin privileges.'
    } else if (e.code === 'auth/invalid-login-credentials' || e.code === 'auth/wrong-password' || e.code === 'auth/user-not-found') {
      error.value = 'Incorrect email or password.'
    } else if (e.code === 'auth/too-many-requests') {
      error.value = 'Too many failed attempts. Please try again later.'
    } else if (e.code === 'auth/user-disabled') {
      error.value = 'This account has been disabled. Contact a super-admin.'
    } else {
      error.value = `Login failed: ${e.message}`
    }
  } finally {
    loading.value = false
  }
}

function getPasswordStrength(pw) {
  if (!pw) return { level: 0, label: '', color: '' }
  let score = 0
  if (pw.length >= 8) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  const levels = [
    { level: 0, label: '', color: '' },
    { level: 1, label: 'Weak', color: '#ff6b6b' },
    { level: 2, label: 'Fair', color: '#ffa94d' },
    { level: 3, label: 'Good', color: '#69db7c' },
    { level: 4, label: 'Strong', color: '#51cf66' },
  ]
  return levels[score] || levels[0]
}

async function handleRegister() {
  regError.value = ''
  if (!regUsername.value.trim()) {
    regError.value = 'Username is required.'
    return
  }
  if (regUsername.value.trim().length < 3) {
    regError.value = 'Username must be at least 3 characters.'
    return
  }
  if (!regPassword.value) {
    regError.value = 'Password is required.'
    return
  }
  if (regPassword.value.length < 6) {
    regError.value = 'Password must be at least 6 characters.'
    return
  }
  if (regPassword.value !== regConfirmPassword.value) {
    regError.value = 'Passwords do not match.'
    return
  }

  regLoading.value = true
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: regUsername.value.trim(),
        password: regPassword.value
      })
    })
    const data = await res.json()
    if (!res.ok) {
      regError.value = data.detail || 'Registration failed. Please try again.'
      return
    }
    regSuccess.value = true
  } catch (e) {
    regError.value = 'Could not connect to the server. Is the backend running?'
  } finally {
    regLoading.value = false
  }
}

async function handleReset() {
  resetError.value = ''
  resetSuccess.value = false
  if (!resetEmail.value || !resetEmail.value.includes('@')) {
    resetError.value = 'Please enter a valid email address.'
    return
  }
  resetLoading.value = true
  try {
    await store.resetPassword(resetEmail.value.trim())
    resetSuccess.value = true
  } catch (e) {
    if (e.code === 'auth/user-not-found') {
      // Don't reveal whether email exists — security best practice
      resetSuccess.value = true
    } else {
      resetError.value = `Could not send reset email: ${e.message}`
    }
  } finally {
    resetLoading.value = false
  }
}

// ── Inline icon components ──────────────────────────────────────────────────
const IconAlert = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" class="me-2" style="flex-shrink:0">
    <circle cx="12" cy="12" r="10" stroke="#ff6b6b" stroke-width="1.5"/>
    <path d="M12 8v4M12 16h.01" stroke="#ff6b6b" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`
}
const IconCheck = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" class="me-2" style="flex-shrink:0">
    <circle cx="12" cy="12" r="10" stroke="#69db7c" stroke-width="1.5"/>
    <path d="M8 12l3 3 5-5" stroke="#69db7c" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`
}
const IconUser = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.5"/>
    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`
}
const IconLock = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" stroke-width="1.5"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`
}
const IconEye = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" stroke="currentColor" stroke-width="1.5"/>
    <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.5"/>
  </svg>`
}
const IconEyeOff = {
  template: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`
}
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #020d18 0%, #052a45 50%, #061f33 100%);
  position: relative;
  overflow: hidden;
  font-family: 'Segoe UI', system-ui, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.12;
  pointer-events: none;
}
.blob-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #1a6fa8, transparent);
  top: -150px; left: -150px;
  animation: drift 12s ease-in-out infinite alternate;
}
.blob-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #0a4a6e, transparent);
  bottom: -100px; right: -100px;
  animation: drift 16s ease-in-out infinite alternate-reverse;
}
@keyframes drift {
  from { transform: translate(0,0) scale(1); }
  to   { transform: translate(40px,40px) scale(1.1); }
}

.auth-card {
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px;
  padding: 2.5rem;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 32px 64px rgba(0,0,0,0.5);
  position: relative;
  z-index: 1;
}

/* Card transition */
.card-enter-active, .card-leave-active { transition: all 0.3s ease; }
.card-enter-from { opacity: 0; transform: translateX(30px); }
.card-leave-to  { opacity: 0; transform: translateX(-30px); }

.logo-icon {
  width: 60px; height: 60px;
  background: linear-gradient(135deg, #1a6fa8, #0a4a6e);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(26,111,168,0.4);
}
.card-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.3px;
  margin: 0;
}
.card-subtitle {
  color: rgba(255,255,255,0.45);
  font-size: 0.85rem;
  margin: 0.25rem 0 0;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.alert-error {
  background: rgba(255,107,107,0.1);
  border: 1px solid rgba(255,107,107,0.3);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  color: #ff9999;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}
.alert-success {
  background: rgba(105,219,124,0.1);
  border: 1px solid rgba(105,219,124,0.3);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  color: #69db7c;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}

.form-label {
  color: rgba(255,255,255,0.6);
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
  display: block;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 14px;
  color: rgba(255,255,255,0.35);
  pointer-events: none;
}
.form-input {
  width: 100%;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 0.75rem 2.8rem;
  color: #fff;
  font-size: 0.925rem;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}
.form-input:focus {
  border-color: rgba(26,111,168,0.7);
  background: rgba(255,255,255,0.09);
}
.form-input::placeholder { color: rgba(255,255,255,0.25); }

.toggle-pw {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  color: rgba(255,255,255,0.35);
  cursor: pointer;
  padding: 4px;
  line-height: 0;
  transition: color 0.2s;
}
.toggle-pw:hover { color: rgba(255,255,255,0.7); }

.btn-primary {
  background: linear-gradient(135deg, #1a6fa8, #0d5280);
  border: none;
  border-radius: 10px;
  padding: 0.85rem;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(26,111,168,0.4);
  letter-spacing: 0.3px;
}
.btn-primary:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

.register-link {
  color: rgba(255,255,255,0.4);
  font-size: 0.875rem;
  margin: 0;
}
.link-btn {
  background: none;
  border: none;
  color: #5ab4e8;
  cursor: pointer;
  padding: 0;
  font-size: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.link-btn:hover { color: #7dc9f5; }

@media (max-width: 480px) {
  .auth-card { margin: 20px; padding: 1.75rem; }
}
</style>
