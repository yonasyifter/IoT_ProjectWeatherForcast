<template>
  <div class="chatbot-wrapper">
    <!-- Floating FAB -->
    <button
      class="chat-fab btn btn-primary rounded-circle shadow-lg"
      @click="toggleChat"
      :title="isOpen ? 'Close chat' : 'Open chat'"
      aria-label="Toggle chatbot"
    >
      <i class="bi" :class="isOpen ? 'bi-x-lg' : 'bi-chat-dots-fill'"></i>
    </button>

    <!-- Chat Container -->
    <transition name="slide-up">
      <div v-if="isOpen" class="card chat-container shadow-lg border-0">

        <!-- Header -->
        <div class="card-header bg-gradient text-white d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0">
              <i class="bi bi-chat-dots-fill me-2"></i>{{ t.title }}
            </h5>
            <small class="opacity-75">{{ t.groqPowered }}</small>
          </div>
          <div class="d-flex gap-2">
            <button class="btn btn-sm btn-outline-light"
              @click="toggleLanguage"
              :title="`Switch to ${currentLanguage === 'en' ? 'Italian' : 'English'}`"
            >
              <span>{{ currentLanguage === 'en' ? '🇬🇧' : '🇮🇹' }}</span>
            </button>
            <button class="btn btn-sm btn-outline-light" @click="clearChat" :title="t.clearChat">
              <i class="bi bi-trash"></i>
            </button>
            <button class="btn btn-sm btn-outline-light" @click="toggleChat">
              <i class="bi bi-chevron-down"></i>
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div class="chat-messages" ref="messagesEl">
          <div v-if="messages.length === 0" class="text-center text-muted p-4">
            <i class="bi bi-chat-left display-6 mb-3 d-block opacity-25"></i>
            <p>{{ t.greeting }}</p>
            <small>{{ t.helpText }}</small>
          </div>

          <div v-for="msg in messages" :key="msg.id" class="message-group p-3">
            <div :class="['message', msg.role === 'user' ? 'user-message' : 'assistant-message']">
              <div class="message-content">{{ msg.content }}</div>
              <details v-if="msg.transcript" class="mt-2">
                <summary class="small cursor-pointer">
                  <i class="bi bi-mic-fill me-1"></i>{{ t.whisperTranscript }}
                </summary>
                <pre class="transcript-box mt-2 mb-0">{{ msg.transcript }}</pre>
              </details>
              <div v-if="msg.error" class="mt-2 small text-danger">
                <i class="bi bi-exclamation-triangle-fill me-1"></i>{{ msg.error }}
              </div>
            </div>
          </div>

          <div v-if="loading" class="text-muted small fst-italic p-3">
            <span class="spinner-grow spinner-grow-sm me-2"></span>{{ t.thinking }}
          </div>
        </div>

        <!-- Input Footer -->
        <div class="card-footer bg-white border-top-0 p-3">
          <div v-if="isRecording" class="recording-banner text-center text-danger small mb-2 fw-semibold">
            <i class="bi bi-record-circle-fill me-1"></i>
            {{ t.recordingFormat }} {{ currentLanguage.toUpperCase() }} — {{ t.willTranscribe }}
          </div>
          <div class="input-group input-group-sm">
            <!-- Mic hold-to-talk -->
            <button
              class="btn btn-outline-secondary"
              :class="{ 'btn-danger text-white': isRecording }"
              @pointerdown="onMicDown"
              @pointerup="onMicUp"
              @pointercancel="onMicUp"
              @pointerleave="onMicUp"
              :disabled="loading"
              :title="isRecording ? t.releaseToSend : t.holdToSpeak"
            >
              <i class="bi" :class="isRecording ? 'bi-stop-circle-fill' : 'bi-mic-fill'"></i>
            </button>

            <input
              type="text"
              class="form-control"
              :placeholder="t.askPlaceholder"
              v-model="userInput"
              @keyup.enter="sendText"
              :disabled="loading || isRecording"
            />

            <button
              class="btn btn-primary"
              @click="sendText"
              :disabled="loading || !userInput.trim() || isRecording"
              :title="t.sendMessage"
            >
              <i class="bi bi-send-fill"></i>
            </button>
          </div>
        </div>

      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import { api } from '@/utils/api'

const isOpen    = ref(false)
const messages  = ref([])
const userInput = ref('')
const loading   = ref(false)
const currentLanguage = ref('en')
const messagesEl = ref(null)
const isRecording = ref(false)

let mediaStream   = null
let mediaRecorder = null
let audioChunks   = []
let deviceContext = ref([])
let _idCounter    = 0

// ── Translations ──────────────────────────────────────────────────────────
const translations = {
  en: {
    title: 'Park AI Assistant',
    groqPowered: 'Powered by Groq',
    clearChat: 'Clear chat',
    thinking: 'Groq AI is thinking…',
    whisperTranscript: '🎙️ Groq Whisper Transcript',
    holdToSpeak: 'Hold to speak',
    releaseToSend: 'Release to send',
    askPlaceholder: 'Ask about park conditions…',
    sendMessage: 'Send message',
    helpText: 'Lightning-fast responses with Groq. Hold mic to record or type to chat.',
    greeting: 'Hello! Ask me about the parks sensor data.',
    recordingFormat: 'Recording in',
    willTranscribe: 'Groq Whisper will transcribe it.',
    serverError: 'Could not reach the server. Please try again.',
  },
  it: {
    title: 'Assistente AI del Parco',
    groqPowered: 'Powered by Groq',
    clearChat: 'Cancella chat',
    thinking: 'Groq AI sta pensando…',
    whisperTranscript: '🎙️ Trascrizione Groq Whisper',
    holdToSpeak: 'Tieni premuto per parlare',
    releaseToSend: 'Rilascia per inviare',
    askPlaceholder: 'Chiedi informazioni sul parco…',
    sendMessage: 'Invia messaggio',
    helpText: 'Risposte rapide con Groq. Tieni premuto il microfono o scrivi.',
    greeting: 'Ciao! Chiedimi dei dati dei sensori del parco.',
    recordingFormat: 'Registrazione in',
    willTranscribe: 'Groq Whisper lo trascriverà.',
    serverError: 'Impossibile raggiungere il server. Riprova.',
  },
}

const t = computed(() => translations[currentLanguage.value] || translations.en)

// ── Helpers ───────────────────────────────────────────────────────────────
function toggleChat ()     { isOpen.value = !isOpen.value }
function toggleLanguage () { currentLanguage.value = currentLanguage.value === 'en' ? 'it' : 'en' }
function clearChat ()      { messages.value = [] }

function pushMessage (role, content, extras = {}) {
  messages.value.push({ id: ++_idCounter, role, content, ...extras })
  nextTick(scrollToBottom)
}

async function scrollToBottom () {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

// ── Sensor context (best-effort) ──────────────────────────────────────────
async function fetchDeviceContext () {
  try {
    const data = await api.get('/api/weather/forecast/?minutes=60')
    if (Array.isArray(data)) deviceContext.value = data
  } catch { /* silent */ }
}

// ── Text send → /api/rag/chat (Groq) ──────────────────────────────────────
async function sendText () {
  const text = userInput.value.trim()
  if (!text || loading.value) return

  pushMessage('user', text)
  userInput.value = ''
  loading.value = true

  try {
    if (!deviceContext.value.length) await fetchDeviceContext()

    const formData = new FormData()
    formData.append('user_query', text)
    formData.append('language',   currentLanguage.value)
    if (deviceContext.value.length)
      formData.append('device_data', JSON.stringify(deviceContext.value))

    const response = await api.post('/api/crew/chat', formData)
    pushMessage('assistant', response.answer || '(No response)')
  } catch (err) {
    console.error('Chat error:', err)
    pushMessage('assistant', t.value.serverError, { error: err.message })
  } finally {
    loading.value = false
  }
}

// ── Audio hold-to-talk → /api/crew/chat with audio_file ───────────────────
async function onMicDown () {
  try {
    mediaStream   = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(mediaStream)
    audioChunks   = []

    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data)
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      await sendAudio(blob)
      mediaStream.getTracks().forEach(t => t.stop())
    }

    mediaRecorder.start()
    isRecording.value = true
  } catch (err) {
    console.error('Mic error:', err)
    pushMessage('assistant', 'Microphone access denied.', { error: err.message })
  }
}

function onMicUp () {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
  }
}

async function sendAudio (audioBlob) {
  loading.value = true
  try {
    if (!deviceContext.value.length) await fetchDeviceContext()

    const formData = new FormData()
    formData.append('audio_file', audioBlob, 'recording.webm')
    formData.append('language',   currentLanguage.value)
    if (deviceContext.value.length)
      formData.append('device_data', JSON.stringify(deviceContext.value))

    const response = await api.post('/api/crew/chat', formData)
    pushMessage('assistant', response.answer || '(No response)', {
      transcript: response.transcript || '',
    })
  } catch (err) {
    console.error('Audio error:', err)
    pushMessage('assistant', 'Failed to process audio.', { error: err.message })
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (mediaStream) mediaStream.getTracks().forEach(t => t.stop())
})
</script>

<style scoped>
.chatbot-wrapper { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }

.chat-fab {
  position: fixed; bottom: 30px; right: 30px;
  width: 70px; height: 70px; z-index: 9999;
  transition: transform .2s, box-shadow .2s;
  border: none; font-size: 1.5rem;
}
.chat-fab:hover { transform: scale(1.05); box-shadow: 0 8px 24px rgba(0,0,0,.2) !important; }

.chat-container {
  position: fixed; bottom: 110px; right: 30px;
  width: 380px; height: 550px; z-index: 9999;
  border-radius: 12px; overflow: hidden; display: flex; flex-direction: column;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem; border: none;
}
.card-header h5 { font-weight: 600; }

.chat-messages { flex: 1; overflow-y: auto; padding: 1rem 0; }
.message-group { display: flex; margin-bottom: .5rem; }
.message {
  max-width: 80%; padding: .75rem 1rem; border-radius: 8px;
  font-size: .95rem; line-height: 1.4; word-wrap: break-word;
}
.user-message {
  background: #667eea; color: white;
  margin-left: auto; margin-right: 1rem; border-bottom-right-radius: 2px;
}
.assistant-message {
  background: #f0f0f0; color: #333;
  margin-left: 1rem; border-bottom-left-radius: 2px;
}
.message-content { word-wrap: break-word; white-space: pre-wrap; }

.transcript-box {
  background: #0f172a; color: #e2e8f0;
  padding: 10px; border-radius: 6px; font-size: .85em;
  overflow: auto; white-space: pre-wrap; word-break: break-word;
  max-height: 150px; border-left: 3px solid #667eea;
}

.recording-banner { color: #dc3545; animation: pulse 1s infinite; }
.cursor-pointer { cursor: pointer; }
details summary { list-style: none; }
details summary::-webkit-details-marker { display: none; }

.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-thumb { background: #dee2e6; border-radius: 10px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }

.slide-up-enter-active, .slide-up-leave-active { transition: all .3s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px); }

@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.5 } }
.btn-danger i { animation: pulse 1s ease-in-out infinite; }

@media (max-width: 576px) {
  .chat-container { right: 15px; left: 15px; width: auto; bottom: 90px; }
  .chat-fab { right: 15px; bottom: 15px; width: 60px; height: 60px; font-size: 1.2rem; }
}
</style>