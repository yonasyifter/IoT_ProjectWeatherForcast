<script setup>
import { ref, computed, nextTick, onBeforeUnmount } from "vue";

const isOpen = ref(false);
const messages = ref([]);
const userInput = ref("");
const loading = ref(false);

const deviceContext = ref([]);
const contextLoading = ref(false);
const contextError = ref("");
const lastContextAt = ref(null);

// Audio
const isRecording = ref(false);
const recorderMime = ref("");
let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];

// DOM refs
const messagesEl = ref(null);

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/** ---------- Helpers ---------- */
function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
function pushMessage(role, content, extra = {}) {
  messages.value.push({
    id: uid(),
    role,
    content,
    timestamp: nowTime(),
    ...extra, // transcript, error, etc
  });
}
async function scrollToBottom() {
  await nextTick();
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

const sensorReady = computed(() => Array.isArray(deviceContext.value) && deviceContext.value.length > 0);
const canSend = computed(() => !loading.value && (userInput.value.trim().length > 0) && sensorReady.value);

/** ---------- Fetch sensors ---------- */
async function fetchDeviceContext() {
  contextLoading.value = true;
  contextError.value = "";

  try {
    const res = await fetch(`${API_BASE}/api/weather/forecast/?minutes=60`);
    if (!res.ok) throw new Error(`Sensor API failed (${res.status})`);
    const data = await res.json();

    deviceContext.value = data;
    lastContextAt.value = new Date();
    return data;
  } catch (e) {
    console.error("Database Error:", e);
    contextError.value = "Could not load sensor data.";
    deviceContext.value = [];
    return [];
  } finally {
    contextLoading.value = false;
  }
}

/** ---------- Backend call (ALWAYS multipart/form-data) ---------- */
async function callRag({ text, audioFileOrBlob }) {
  // Ensure we have fresh-ish context (you can change the refresh behavior if you like)
  const currentData = await fetchDeviceContext();
  if (!Array.isArray(currentData) || currentData.length === 0) {
    throw new Error("Missing device_data (sensor rows). Cannot send to RAG.");
  }

  const formData = new FormData();
  formData.append("device_data", JSON.stringify(currentData));

  if (text && text.trim().length) formData.append("user_query", text.trim());

  if (audioFileOrBlob) {
    // If it’s a Blob, give it a filename so FastAPI sees it as UploadFile nicely
    if (audioFileOrBlob instanceof Blob && !(audioFileOrBlob instanceof File)) {
      const ext =
        recorderMime.value.includes("ogg") ? "ogg" :
        recorderMime.value.includes("webm") ? "webm" : "bin";
      formData.append("audio_file", audioFileOrBlob, `recording.${ext}`);
    } else {
      formData.append("audio_file", audioFileOrBlob);
    }
  }

  const res = await fetch(`${API_BASE}/api/rag/chat`, {
    method: "POST",
    body: formData, // ✅ do NOT set Content-Type manually
  });

  let data;
  try {
    data = await res.json();
  } catch {
    data = { response: "Server returned a non-JSON response." };
  }

  if (!res.ok) {
    const detail = data?.detail ? JSON.stringify(data.detail) : "Unknown server error";
    throw new Error(`RAG API error (${res.status}): ${detail}`);
  }

  // Support both backend formats:
  // - new: { transcript, answer }
  // - old: { response }
  const transcript = data?.transcript ?? "";
  const answer = data?.answer ?? data?.response ?? "";

  return { transcript, answer };
}

/** ---------- Text send ---------- */
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  pushMessage("user", text);
  userInput.value = "";
  loading.value = true;

  try {
    const { transcript, answer } = await callRag({ text });
    pushMessage("assistant", answer || "(empty response)", { transcript });
  } catch (e) {
    pushMessage("assistant", "Offline: Could not reach the server or the model.", {
      error: String(e?.message || e),
    });
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}

/** ---------- Recording (press & hold) ---------- */
function pickBestMimeType() {
  // Prefer OGG/Opus if supported; otherwise default will likely be webm/opus
  const candidates = ["audio/ogg;codecs=opus", "audio/webm;codecs=opus", "audio/webm"];
  for (const c of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(c)) return c;
  }
  return ""; // let browser decide
}

async function startRecording() {
  if (isRecording.value || loading.value) return;

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mime = pickBestMimeType();
    recorderMime.value = mime || "audio/webm";

    mediaRecorder = mime
      ? new MediaRecorder(mediaStream, { mimeType: mime })
      : new MediaRecorder(mediaStream);

    audioChunks = [];
    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.start();
    isRecording.value = true;
  } catch (e) {
    console.error(e);
    pushMessage("assistant", "Mic permission denied or recording failed.", { error: String(e?.message || e) });
    isRecording.value = false;
    cleanupMedia();
    await scrollToBottom();
  }
}

async function stopRecording() {
  if (!isRecording.value || !mediaRecorder) return;

  isRecording.value = false;

  const stopped = new Promise((resolve) => {
    mediaRecorder.onstop = resolve;
  });

  try {
    mediaRecorder.stop();
    await stopped;
  } catch {}

  try {
    const blobType = recorderMime.value || audioChunks[0]?.type || "audio/webm";
    const audioBlob = new Blob(audioChunks, { type: blobType });

    // Show user bubble
    pushMessage("user", isWebm(blobType) ? "(sent voice message — webm)" : "(sent voice message)");
    loading.value = true;

    const { transcript, answer } = await callRag({ audioFileOrBlob: audioBlob });
    pushMessage("assistant", answer || "(empty response)", { transcript });

  } catch (e) {
    pushMessage("assistant", "Offline: Could not reach the server or the model.", {
      error: String(e?.message || e),
    });
  } finally {
    loading.value = false;
    cleanupMedia();
    await scrollToBottom();
  }
}

function isWebm(mime) {
  return (mime || "").toLowerCase().includes("webm");
}

function cleanupMedia() {
  try {
    if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
  } catch {}
  mediaStream = null;
  mediaRecorder = null;
  audioChunks = [];
}

/** Works on desktop + mobile */
function onMicDown(e) {
  e.preventDefault?.();
  startRecording();
}
function onMicUp(e) {
  e.preventDefault?.();
  stopRecording();
}

function toggleChat() {
  isOpen.value = !isOpen.value;

  if (isOpen.value && messages.value.length === 0) {
    pushMessage("assistant", "Welcome to the Park! Ask me anything or hold the mic to speak.");
    // prefetch sensor data when opening
    fetchDeviceContext().finally(scrollToBottom);
  }
}

function clearChat() {
  messages.value = [];
  pushMessage("assistant", "Chat cleared. Ask me anything or hold the mic to speak.");
  scrollToBottom();
}

onBeforeUnmount(() => cleanupMedia());
</script>

<template>
  <div class="rag-wrapper">
    <!-- Floating button -->
    <button
      v-if="!isOpen"
      class="chat-fab btn btn-primary rounded-circle shadow-lg d-flex align-items-center justify-content-center"
      @click="toggleChat"
      aria-label="Open chat"
    >
      <i class="bi bi-robot fs-1"></i>
    </button>

    <!-- Chat window -->
    <div v-if="isOpen" class="chat-container card shadow-lg border-0">
      <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-3">
        <div class="d-flex flex-column">
          <h6 class="mb-0">
            <i class="bi bi-robot me-2"></i> Park AI Assistant
          </h6>
          <small class="opacity-75">
            Sensors:
            <span v-if="contextLoading" class="ms-1">loading…</span>
            <span v-else-if="sensorReady" class="ms-1">OK ({{ deviceContext.length }})</span>
            <span v-else class="ms-1">missing</span>
            <span v-if="lastContextAt" class="ms-2">• {{ lastContextAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }}</span>
          </small>
        </div>

        <div class="d-flex gap-2 align-items-center">
          <button class="btn btn-sm btn-light" @click="clearChat" title="Clear chat">
            <i class="bi bi-trash"></i>
          </button>
          <button class="btn-close btn-close-white" @click="isOpen = false" aria-label="Close"></button>
        </div>
      </div>

      <div ref="messagesEl" class="card-body chat-messages p-3 bg-light">
        <div
          v-for="m in messages"
          :key="m.id"
          :class="['d-flex mb-3', m.role === 'user' ? 'justify-content-end' : 'justify-content-start']"
        >
          <div
            :class="[
              'p-3 rounded-4 shadow-sm max-w-75',
              m.role === 'user' ? 'bg-primary text-white' : 'bg-white text-dark border'
            ]"
          >
            <div class="small opacity-75 mb-1 d-flex justify-content-between gap-3">
              <span>{{ m.role === 'user' ? 'You' : 'Assistant' }}</span>
              <span>{{ m.timestamp }}</span>
            </div>

            <div>{{ m.content }}</div>

            <!-- transcript (if returned by backend) -->
            <details v-if="m.transcript" class="mt-2">
              <summary class="small">Transcript</summary>
              <pre class="transcript-box mt-2 mb-0">{{ m.transcript }}</pre>
            </details>

            <!-- error (if any) -->
            <div v-if="m.error" class="mt-2 small text-danger">
              {{ m.error }}
            </div>
          </div>
        </div>

        <div v-if="loading" class="text-muted small fst-italic">
          <span class="spinner-grow spinner-grow-sm me-2"></span> Gemini is thinking...
        </div>

        <div v-if="contextError" class="text-danger small mt-2">
          {{ contextError }}
        </div>

        <div v-if="recorderMime && recorderMime.includes('webm')" class="text-warning small mt-2">
          ⚠️ Recording format is <code>{{ recorderMime }}</code>. If your backend/model rejects it, prefer uploading/recording OGG or WAV.
        </div>
      </div>

      <div class="card-footer bg-white border-top-0 p-3">
        <div class="input-group">
          <!-- Mic: press and hold (pointer events work for mouse + touch) -->
          <button
            class="btn btn-outline-secondary"
            :class="{ 'btn-danger text-white': isRecording }"
            @pointerdown="onMicDown"
            @pointerup="onMicUp"
            @pointercancel="onMicUp"
            @pointerleave="onMicUp"
            :disabled="loading"
            title="Hold to speak"
          >
            <i class="bi" :class="isRecording ? 'bi-mic-fill' : 'bi-mic'"></i>
          </button>

          <input
            v-model="userInput"
            @keyup.enter="sendMessage"
            class="form-control border-start-0"
            placeholder="Ask about the weather..."
            :disabled="loading"
          />

          <button class="btn btn-primary px-3" @click="sendMessage" :disabled="loading || !sensorReady || !userInput.trim()">
            <i class="bi bi-send-fill"></i>
          </button>
        </div>

        <div v-if="!sensorReady && !contextLoading" class="small text-warning mt-2">
          ⚠️ Sensor data (<code>device_data</code>) is required by FastAPI. Click open again or ensure <code>/api/weather/forecast</code> works.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-fab {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 70px;
  height: 70px;
  z-index: 9999;
  transition: transform 0.2s ease;
}
.chat-fab:hover { transform: scale(1.05); }

.chat-container {
  position: fixed;
  bottom: 110px;
  right: 30px;
  width: 380px;
  height: 550px;
  z-index: 9999;
  border-radius: 20px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
}

.max-w-75 { max-width: 80%; }

.chat-messages::-webkit-scrollbar { width: 5px; }
.chat-messages::-webkit-scrollbar-thumb { background: #dee2e6; border-radius: 10px; }

.transcript-box {
  background: #0b1020;
  color: #e7e7e7;
  padding: 10px;
  border-radius: 10px;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
