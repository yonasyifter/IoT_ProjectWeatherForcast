<template>
  <div class="agent-page">
    <!-- ═══════════════════════════════════════════════════
         HEADER
    ════════════════════════════════════════════════════ -->
    <div class="ap-header">
      <div class="ap-header-left">
        <div class="ap-logo">
          <div class="ap-logo-ring">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="3" fill="currentColor"/>
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              <path d="M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
        <div>
          <h1 class="ap-title">Park Intelligence</h1>
          <p class="ap-subtitle">Della Silla Smart Park · AI Analysis Suite</p>
        </div>
      </div>
      <div class="ap-header-right">
        <div class="ap-status-pill" :class="crewStatus">
          <span class="ap-status-dot"></span>
          {{ crewStatusLabel }}
        </div>
        <div class="ap-lang-switcher">
          <button
            v-for="l in supportedLangs"
            :key="l.code"
            :class="['ap-lang-btn', { active: lang === l.code }]"
            @click="lang = l.code"
            :title="l.label"
          >{{ l.flag }}</button>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         CAPABILITY CARDS (quick-launch)
    ════════════════════════════════════════════════════ -->
    <div class="ap-caps">
      <button
        v-for="cap in capabilities"
        :key="cap.id"
        :class="['ap-cap-card', { active: activeMode === cap.id }]"
        @click="activateMode(cap)"
      >
        <div class="ap-cap-icon" :style="{ background: cap.color }">
          <span v-html="cap.icon"></span>
        </div>
        <div class="ap-cap-body">
          <div class="ap-cap-name">{{ cap.name }}</div>
          <div class="ap-cap-desc">{{ cap.desc }}</div>
        </div>
        <div class="ap-cap-arrow" v-if="activeMode === cap.id">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </button>
    </div>

    <!-- ═══════════════════════════════════════════════════
         MAIN WORKSPACE
    ════════════════════════════════════════════════════ -->
    <div class="ap-workspace">

      <!-- ── LEFT: INPUT PANEL ────────────────────────── -->
      <div class="ap-input-panel">

        <!-- Query input -->
        <div class="ap-input-section">
          <label class="ap-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2"/></svg>
            Query
          </label>
          <div class="ap-query-wrap">
            <textarea
              v-model="userQuery"
              class="ap-textarea"
              :placeholder="activeCap?.placeholder || 'Ask anything about the park…'"
              rows="4"
              @keydown.ctrl.enter="handleSubmit"
              :disabled="loading"
            ></textarea>
            <div class="ap-textarea-footer">
              <span class="ap-hint">Ctrl+Enter to send</span>
              <span class="ap-char-count" :class="{ warn: userQuery.length > 400 }">
                {{ userQuery.length }}/500
              </span>
            </div>
          </div>
        </div>

        <!-- Example queries -->
        <div class="ap-examples-section">
          <label class="ap-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" stroke="currentColor" stroke-width="1.8"/></svg>
            Example queries
          </label>
          <div class="ap-examples">
            <button
              v-for="ex in activeCap?.examples || defaultExamples"
              :key="ex"
              class="ap-example-chip"
              @click="userQuery = ex"
            >{{ ex }}</button>
          </div>
        </div>

        <!-- Options row -->
        <div class="ap-options-row">
          <!-- Voice input -->
          <div class="ap-option-group">
            <label class="ap-label">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" stroke="currentColor" stroke-width="2"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              Voice
            </label>
            <button
              :class="['ap-voice-btn', { recording: isRecording }]"
              @pointerdown="startRecording"
              @pointerup="stopRecording"
              @pointercancel="stopRecording"
              :disabled="loading"
              :title="isRecording ? 'Release to send' : 'Hold to speak'"
            >
              <svg v-if="!isRecording" width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" stroke="currentColor" stroke-width="2"/><path d="M19 10v2a7 7 0 0 1-14 0v-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/></svg>
              <span>{{ isRecording ? 'Recording…' : 'Hold to speak' }}</span>
            </button>
            <p v-if="transcript" class="ap-transcript">🎙 {{ transcript }}</p>
          </div>

          <!-- Analysis window -->
          <div class="ap-option-group">
            <label class="ap-label">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              Time window
            </label>
            <select v-model="timeWindow" class="ap-select">
              <option value="">Auto-detect from query</option>
              <option value="1h">Last 1 hour</option>
              <option value="2h">Last 2 hours</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
            </select>
          </div>
        </div>

        <!-- Math / LaTeX toggle -->
        <div class="ap-toggle-row">
          <label class="ap-toggle-label">
            <input type="checkbox" v-model="requestMath" class="ap-toggle-input"/>
            <span class="ap-toggle-track"></span>
            <span>Show LaTeX formulas for computed values</span>
          </label>
          <label class="ap-toggle-label">
            <input type="checkbox" v-model="requestChart" class="ap-toggle-input"/>
            <span class="ap-toggle-track"></span>
            <span>Prefer chart visualisation</span>
          </label>
        </div>

        <!-- Submit -->
        <button
          class="ap-submit-btn"
          @click="handleSubmit"
          :disabled="loading || (!userQuery.trim() && !transcript)"
        >
          <span v-if="loading" class="ap-spinner"></span>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          {{ loading ? loadingPhase : submitLabel }}
        </button>

        <!-- Error -->
        <div v-if="error" class="ap-error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          {{ error }}
        </div>
      </div>

      <!-- ── RIGHT: OUTPUT PANEL ───────────────────────── -->
      <div class="ap-output-panel">

        <Transition name="ap-fade-slide" mode="out-in">

          <!-- 1. Loading state — checked FIRST -->
          <div v-if="loading" key="loading" class="ap-loading-state">
            <div class="ap-loading-icon">
              <div class="ap-pulse-ring"></div>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" fill="#60a5fa"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="#60a5fa" stroke-width="1.8" stroke-linecap="round"/></svg>
            </div>
            <p class="ap-loading-phase">{{ loadingPhase }}</p>
            <div class="ap-loading-steps">
              <TransitionGroup name="ap-step-fade">
                <div v-for="(step, i) in loadingSteps" :key="step" :class="['ap-loading-step', { done: i < loadingStep, active: i === loadingStep }]">
                  <span class="ap-step-dot"></span>
                  <span class="ap-step-text">{{ step }}</span>
                </div>
              </TransitionGroup>
            </div>
          </div>

          <!-- 2. Empty state -->
          <div v-else-if="!response && !reportContent" key="empty" class="ap-empty-state">
            <div class="ap-empty-orb"></div>
            <p class="ap-empty-title">Ready to analyse</p>
            <p class="ap-empty-sub">Select a capability and ask a question.<br>The AI crew will query live sensor data, RCMS device health,<br>and InfluxDB history to answer.</p>
            <div class="ap-empty-chips">
              <span v-for="tag in ['InfluxDB', 'RCMS EG5120', 'Firebase', 'LaTeX math', 'Chart JSON']" :key="tag" class="ap-tag">{{ tag }}</span>
            </div>
          </div>

          <!-- 3. Chat response -->
          <div v-else-if="response && activeMode !== 'report'" key="response" class="ap-response">

            <!-- Source citation bar -->
            <div class="ap-source-bar">
              <span v-for="src in responseSources" :key="src" class="ap-source-chip">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" stroke-width="2"/></svg>
                {{ src }}
              </span>
            </div>

            <!-- Chart response -->
            <div v-if="chartData" class="ap-chart-section">
              <div class="ap-chart-header">
                <span class="ap-chart-type-badge">{{ chartData.chart_type }}</span>
                <h3 class="ap-chart-title">{{ chartData.title }}</h3>
              </div>
              <div class="ap-chart-wrap">
                <canvas ref="chartCanvas" :key="chartKey"></canvas>
              </div>
              <p v-if="chartData.description" class="ap-chart-desc">{{ chartData.description }}</p>
            </div>

            <!-- Text / LaTeX response -->
            <div v-if="response.answer" class="ap-answer-block">
              <!-- LaTeX formulas detected -->
              <div v-if="hasLatex" class="ap-latex-notice">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                Mathematical expressions rendered below
              </div>

              <!-- Render paragraphs, LaTeX blocks, and inline math -->
              <div class="ap-answer-content" v-html="renderedAnswer"></div>

              <!-- Weather prediction callout -->
              <div v-if="response.weather_prediction" class="ap-weather-callout">
                <div class="ap-weather-icon">{{ weatherIcon(response.weather_prediction) }}</div>
                <div>
                  <div class="ap-weather-label">Weather Forecast</div>
                  <div class="ap-weather-val">{{ response.weather_prediction }}</div>
                  <div v-if="response.prediction_confidence" class="ap-weather-conf">
                    Confidence: {{ Math.round(response.prediction_confidence) }}%
                    <div class="ap-conf-bar">
                      <div class="ap-conf-fill" :style="{ width: response.prediction_confidence + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Transcript -->
            <details v-if="response.transcript" class="ap-transcript-details">
              <summary>🎙 Voice transcript</summary>
              <pre>{{ response.transcript }}</pre>
            </details>

            <!-- ── REPORT PROMPT ─────────────── -->
            <div v-if="!reportDismissed && !reportContent" class="ap-report-prompt">
              <div class="ap-report-prompt-left">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="#60a5fa" stroke-width="1.8"/><polyline points="14,2 14,8 20,8" stroke="#60a5fa" stroke-width="1.8"/><line x1="16" y1="13" x2="8" y2="13" stroke="#60a5fa" stroke-width="1.8" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" stroke="#60a5fa" stroke-width="1.8" stroke-linecap="round"/><polyline points="10,9 9,9 8,9" stroke="#60a5fa" stroke-width="1.8"/></svg>
                <div>
                  <p class="ap-report-prompt-title">Generate a full analysis report?</p>
                  <p class="ap-report-prompt-sub">Device inventory · Statistical analysis with LaTeX · Anomaly findings · Recommendations · Delivery via email or WhatsApp</p>
                </div>
              </div>
              <div class="ap-report-prompt-actions">
                <button class="ap-btn-primary" @click="generateReport" :disabled="reportLoading">
                  <span v-if="reportLoading" class="ap-spinner sm"></span>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2"/><polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2"/></svg>
                  {{ reportLoading ? reportLoadingPhase : 'Generate report' }}
                </button>
                <button class="ap-btn-ghost" @click="reportDismissed = true">No thanks</button>
              </div>
            </div>
          </div>

          <!-- 4. Report output -->
          <div v-else-if="reportContent" key="report" class="ap-report-output">
            <div class="ap-report-header">
              <div class="ap-report-header-left">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2"/><polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2"/></svg>
                <span>Smart Park Analysis Report</span>
              </div>
              <div class="ap-report-actions">
                <button class="ap-action-btn" @click="downloadPDF" :disabled="downloadingPDF" title="Download PDF">
                  <span v-if="downloadingPDF" class="ap-spinner sm"></span>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  PDF
                </button>
                <button class="ap-action-btn" @click="downloadWord" :disabled="downloadingWord" title="Download Word">
                  <span v-if="downloadingWord" class="ap-spinner sm"></span>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  Word
                </button>
                <button class="ap-action-btn danger" @click="clearReport" title="Close report">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                </button>
              </div>
            </div>

            <div ref="reportExportRef" class="ap-report-export">
              <!-- Report visual charts -->
              <div v-if="reportCharts.length" class="ap-report-visuals">
                <div class="ap-report-hero">
                  <div>
                    <div class="ap-report-kicker">Live Visual Appendix</div>
                    <h2>Environmental Intelligence Snapshot</h2>
                    <p>Charts are generated from the same sensor snapshot used for the report, then embedded into PDF and Word exports.</p>
                  </div>
                  <div class="ap-report-stat-strip">
                    <div v-for="stat in reportStats" :key="stat.label" class="ap-report-stat">
                      <span>{{ stat.label }}</span>
                      <strong>{{ stat.value }}</strong>
                    </div>
                  </div>
                </div>

                <div class="ap-report-chart-grid">
                  <section v-for="(chart, index) in reportCharts" :key="chart.id" class="ap-report-chart-card">
                    <div class="ap-report-chart-head">
                      <span class="ap-report-chart-type">{{ chart.type }}</span>
                      <h3>{{ chart.title }}</h3>
                    </div>
                    <div class="ap-report-chart-wrap">
                      <canvas :ref="el => assignReportChartCanvas(el, index)" :aria-label="chart.title"></canvas>
                    </div>
                    <p>{{ chart.description }}</p>
                  </section>
                </div>
              </div>

              <!-- Report body -->
              <div class="ap-report-body" v-html="renderedReport"></div>
            </div>

            <!-- Delivery prompt block -->
            <div v-if="showDeliveryPrompt" class="ap-delivery-section">
              <div class="ap-delivery-header">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2"/></svg>
                Send this report
              </div>

              <div v-if="!deliveryChoice" class="ap-delivery-options">
                <button class="ap-delivery-btn email" @click="deliveryChoice = 'email'">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2"/><polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2"/></svg>
                  📧 Email
                </button>
                <button class="ap-delivery-btn whatsapp" @click="deliveryChoice = 'whatsapp'">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="2"/></svg>
                  💬 WhatsApp
                </button>
                <button class="ap-delivery-btn skip" @click="showDeliveryPrompt = false">
                  ❌ No thanks
                </button>
              </div>

              <!-- Email form -->
              <div v-if="deliveryChoice === 'email'" class="ap-delivery-form">
                <label class="ap-label">Email address</label>
                <div class="ap-delivery-input-row">
                  <input
                    v-model="deliveryEmail"
                    type="email"
                    class="ap-input"
                    placeholder="admin@smartpark.it"
                    @keyup.enter="sendDelivery"
                  />
                  <button class="ap-btn-primary sm" @click="sendDelivery" :disabled="deliverySending">
                    <span v-if="deliverySending" class="ap-spinner sm"></span>
                    <span v-else>Send</span>
                  </button>
                  <button class="ap-btn-ghost sm" @click="deliveryChoice = null">Back</button>
                </div>
              </div>

              <!-- WhatsApp form -->
              <div v-if="deliveryChoice === 'whatsapp'" class="ap-delivery-form">
                <label class="ap-label">Phone number (international format)</label>
                <div class="ap-delivery-input-row">
                  <input
                    v-model="deliveryPhone"
                    type="tel"
                    class="ap-input"
                    placeholder="+39 333 1234567"
                    @keyup.enter="sendDelivery"
                  />
                  <button class="ap-btn-primary sm" @click="sendDelivery" :disabled="deliverySending">
                    <span v-if="deliverySending" class="ap-spinner sm"></span>
                    <span v-else>Send</span>
                  </button>
                  <button class="ap-btn-ghost sm" @click="deliveryChoice = null">Back</button>
                </div>
              </div>

              <!-- Delivery result -->
              <div v-if="deliveryResult" :class="['ap-delivery-result', deliveryResult.type]">
                {{ deliveryResult.message }}
              </div>
            </div>
          </div>

        </Transition>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         HISTORY SIDEBAR
    ════════════════════════════════════════════════════ -->
    <div class="ap-history-bar">
      <div class="ap-history-label">Recent queries</div>
      <div class="ap-history-list">
        <button
          v-for="h in history"
          :key="h.id"
          class="ap-history-item"
          @click="replayHistory(h)"
        >
          <span class="ap-history-mode" :style="{ background: h.color }">{{ h.modeIcon }}</span>
          <span class="ap-history-q">{{ h.query }}</span>
          <span class="ap-history-ts">{{ h.ts }}</span>
        </button>
        <div v-if="!history.length" class="ap-history-empty">No history yet</div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { api } from '@/utils/api'
import Chart from 'chart.js/auto'
import { parseAgentResponse } from '@/utils/agent-parser'
import InsightCard from '@/components/agent/InsightCard.vue'
import MathBlock from '@/components/agent/MathBlock.vue'
import AnomalyBlock from '@/components/agent/AnomalyBlock.vue'
import ConfidenceMeter from '@/components/agent/ConfidenceMeter.vue'
import SourceChip from '@/components/agent/SourceChip.vue'

// ── Language ──────────────────────────────────────────────────────────────
const lang = ref('en')
const supportedLangs = [
  { code: 'en', flag: '🇬🇧', label: 'English' },
  { code: 'it', flag: '🇮🇹', label: 'Italiano' },
  { code: 'fr', flag: '🇫🇷', label: 'Français' },
  { code: 'de', flag: '🇩🇪', label: 'Deutsch' },
  { code: 'es', flag: '🇪🇸', label: 'Español' },
]

// ── Capability modes ──────────────────────────────────────────────────────
const capabilities = [
  {
    id: 'chat',
    name: 'Conversational Q&A',
    desc: 'Natural language questions with source citations',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="white" stroke-width="2"/></svg>',
    color: 'linear-gradient(135deg,#3b82f6,#1d4ed8)',
    placeholder: 'Ask about park conditions, device status, weather…',
    examples: [
      'What is the current temperature and humidity at the park?',
      'Which devices are online right now?',
      'Is the noise level within safe limits today?',
      'What is the weather prediction and confidence?',
    ],
  },
  {
    id: 'math',
    name: 'Statistical Analysis',
    desc: 'LaTeX formulas · averages · Δ-diff · rate-of-change',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M4 12h10M4 17h6" stroke="white" stroke-width="2" stroke-linecap="round"/><path d="M18 14l2 2-2 2M22 16h-4" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>',
    color: 'linear-gradient(135deg,#8b5cf6,#6d28d9)',
    placeholder: 'Ask for computed metrics with formulas…',
    examples: [
      'What is the average temperature over the last 2 hours with formula?',
      'Calculate the highest temperature difference in the past week',
      'Show me the rate of change of humidity over the last hour',
      'What was the minimum pressure recorded this week?',
    ],
  },
  {
    id: 'chart',
    name: 'Data Visualisation',
    desc: 'Bar, line, pie, radar, scatter charts',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 19V5" stroke="white" stroke-width="2" stroke-linecap="round"/><path d="M7 16l4-4 4 3 5-7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    color: 'linear-gradient(135deg,#10b981,#059669)',
    placeholder: 'Request a chart or graph…',
    examples: [
      'Show a bar chart of temperature per device',
      'Plot humidity trend over the last 6 hours',
      'Compare temperature and noise across all sensors',
      'Show device status breakdown as a pie chart',
    ],
  },
  {
    id: 'device',
    name: 'Device Health',
    desc: 'RCMS EG5120 · firmware · CPU/RAM · alerts',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><rect x="2" y="8" width="20" height="8" rx="2" stroke="white" stroke-width="2"/><circle cx="6" cy="12" r="1.5" fill="white"/><path d="M10 12h8" stroke="white" stroke-width="1.5" stroke-linecap="round"/><path d="M12 8V5M8 8V6M16 8V6" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>',
    color: 'linear-gradient(135deg,#f59e0b,#d97706)',
    placeholder: 'Ask about devices, firmware, connectivity…',
    examples: [
      'How many devices are currently online?',
      'Show firmware versions for all devices',
      'Are there any active alerts or anomalies?',
      'What is the Edge device CPU and RAM usage?',
    ],
  },
  {
    id: 'anomaly',
    name: 'Anomaly Detection',
    desc: 'Threshold breaches · sensor drift · CRITICAL alerts',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="white" stroke-width="2"/><line x1="12" y1="9" x2="12" y2="13" stroke="white" stroke-width="2" stroke-linecap="round"/><line x1="12" y1="17" x2="12.01" y2="17" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>',
    color: 'linear-gradient(135deg,#ef4444,#b91c1c)',
    placeholder: 'Ask about anomalies, warnings, critical findings…',
    examples: [
      'Are there any sensor readings outside safe ranges?',
      'Show me all WARNING and CRITICAL anomalies',
      'Has the temperature spiked unusually in the last hour?',
      'Any offline devices or connectivity issues?',
    ],
  },
  {
    id: 'report',
    name: 'Full Report',
    desc: 'Comprehensive Markdown · PDF · Word · email / WhatsApp',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="white" stroke-width="2"/><polyline points="14,2 14,8 20,8" stroke="white" stroke-width="2"/><line x1="16" y1="13" x2="8" y2="13" stroke="white" stroke-width="1.8" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" stroke="white" stroke-width="1.8" stroke-linecap="round"/></svg>',
    color: 'linear-gradient(135deg,#0ea5e9,#0369a1)',
    placeholder: 'Describe what the report should cover…',
    examples: [
      'Generate a full park status report for today',
      'Create a weekly environmental monitoring report',
      'Report on device health and all active anomalies',
      'Full analysis: sensors + devices + recommendations',
    ],
  },
]

const activeMode    = ref('chat')
const activeCap     = computed(() => capabilities.find(c => c.id === activeMode.value))
const defaultExamples = capabilities[0].examples

function activateMode (cap) {
  activeMode.value = cap.id
  if (cap.examples?.length) userQuery.value = ''
}

// ── Form state ────────────────────────────────────────────────────────────
const userQuery    = ref('')
const timeWindow   = ref('')
const requestMath  = ref(false)
const requestChart = ref(false)

// ── Voice ─────────────────────────────────────────────────────────────────
const isRecording  = ref(false)
const transcript   = ref('')
let mediaRecorder  = null
let mediaStream    = null
let audioChunks    = []

async function startRecording () {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(mediaStream)
    audioChunks = []
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data)
    mediaRecorder.start()
    isRecording.value = true
  } catch (e) {
    error.value = 'Microphone access denied: ' + e.message
  }
}

function stopRecording () {
  if (!mediaRecorder || !isRecording.value) return
  mediaRecorder.onstop = () => {
    const blob = new Blob(audioChunks, { type: 'audio/webm' })
    handleAudioSubmit(blob)
    mediaStream?.getTracks().forEach(t => t.stop())
  }
  mediaRecorder.stop()
  isRecording.value = false
}

onBeforeUnmount(() => {
  mediaStream?.getTracks().forEach(t => t.stop())
  destroyReportCharts()
})

// ── Loading phases ────────────────────────────────────────────────────────
const loadingSteps = [
  'Sensor Analyst: Computing statistical metrics...',
  'Edge Officer: Cross-referencing RCMS & InfluxDB...',
  'Context Builder: Mapping confidence levels...',
  'Diagnostics Analyst: Evaluating threshold breaches...',
  'Reasoning Agent: Synthesising final analysis...',
]
const loadingStep   = ref(0)
const loadingPhase  = ref('')
let phaseTimer      = null

const reportLoadingSteps = [
  'Analyzing agent-led insights...',
  'Structuring final report...',
  'Compiling statistical summaries...',
  'Formatting LaTeX expressions...',
  'Finalizing document layout...',
]
const reportLoadingStep = ref(0)

function startLoadingAnimation () {
  loadingStep.value  = 0
  loadingPhase.value = loadingSteps[0]
  phaseTimer = setInterval(() => {
    if (loadingStep.value < loadingSteps.length - 1) {
      loadingStep.value++
      loadingPhase.value = loadingSteps[loadingStep.value]
    }
  }, 2200)
}

function stopLoadingAnimation () {
  clearInterval(phaseTimer)
  loadingStep.value  = 0
  loadingPhase.value = ''
}

function startReportLoadingAnimation () {
  reportLoadingStep.value = 0
  reportLoadingPhase.value = reportLoadingSteps[0]
  phaseTimer = setInterval(() => {
    if (reportLoadingStep.value < reportLoadingSteps.length - 1) {
      reportLoadingStep.value++
      reportLoadingPhase.value = reportLoadingSteps[reportLoadingStep.value]
    }
  }, 1800)
}

function stopReportLoadingAnimation () {
  clearInterval(phaseTimer)
  reportLoadingStep.value = 0
  reportLoadingPhase.value = ''
}

// ── Status ────────────────────────────────────────────────────────────────
const crewStatus      = ref('idle')
const crewStatusLabel = computed(() => ({
  idle:    'Ready',
  loading: 'Analysing…',
  ok:      'Response received',
  error:   'Error',
}[crewStatus.value]))

// ── Output state ──────────────────────────────────────────────────────────
const loading        = ref(false)
const error          = ref('')
const response       = ref(null)
const chartData      = ref(null)
const chartCanvas    = ref(null)
const chartKey       = ref(0)
let   chartInstance  = null
const CHAT_REQUEST_TIMEOUT_MS = 55000
const REPORT_REQUEST_TIMEOUT_MS = 130000
const SNAPSHOT_REQUEST_TIMEOUT_MS = 10000

const reportContent      = ref('')
const reportLoading      = ref(false)
const reportLoadingPhase = ref('')
const reportDismissed    = ref(false)
const downloadingPDF     = ref(false)
const downloadingWord    = ref(false)
const reportSnapshot     = ref([])
const reportCharts       = ref([])
const reportExportRef    = ref(null)
const reportChartCanvases = ref([])
let   reportChartInstances = []

const showDeliveryPrompt = ref(false)
const deliveryChoice     = ref(null)
const deliveryEmail      = ref('')
const deliveryPhone      = ref('')
const deliverySending    = ref(false)
const deliveryResult     = ref(null)

// ── History ───────────────────────────────────────────────────────────────
const history = ref([])
let   histId  = 0

function pushHistory (query, mode) {
  const cap = capabilities.find(c => c.id === mode)
  history.value.unshift({
    id: ++histId,
    query: query.slice(0, 60) + (query.length > 60 ? '…' : ''),
    modeIcon: mode[0].toUpperCase(),
    color: cap?.color || '#4b5563',
    ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  })
  if (history.value.length > 10) history.value.pop()
}

function replayHistory (h) {
  userQuery.value = h.query
}

async function requestWithTimeout (requestFn, timeoutMs, timeoutMessage) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await requestFn(controller.signal)
  } catch (e) {
    if (e.name === 'AbortError') {
      throw new Error(timeoutMessage)
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

function postWithTimeout (endpoint, body, timeoutMs = CHAT_REQUEST_TIMEOUT_MS) {
  return requestWithTimeout(
    signal => api.post(endpoint, body, { signal }),
    timeoutMs,
    'The AI assistant took too long to respond. Please retry with a shorter prompt.'
  )
}

// ── Submit label ──────────────────────────────────────────────────────────
const submitLabel = computed(() => ({
  report:  'Generate Report',
  chart:   'Build Chart',
  math:    'Compute & Explain',
  anomaly: 'Run Diagnostics',
  device:  'Check Devices',
  chat:    'Ask AI',
}[activeMode.value] || 'Ask AI'))

// ── Build query hint prefix based on mode ─────────────────────────────────
function buildFinalQuery (raw) {
  let q = raw.trim()
  if (!q && transcript.value) q = transcript.value

  if (timeWindow.value && !q.toLowerCase().includes('hour') && !q.toLowerCase().includes('day')) {
    q += ` (time window: ${timeWindow.value})`
  }
  if (requestMath.value && !q.toLowerCase().includes('formula') && !q.toLowerCase().includes('latex')) {
    q += ' — please show the mathematical formula in LaTeX.'
  }
  if (requestChart.value && activeMode.value !== 'chart') {
    q += ' — please show this as a chart.'
  }
  return q
}

// ── Sensor context snapshot ───────────────────────────────────────────────
function minutesForReportWindow () {
  const q = (userQuery.value || '').toLowerCase()
  const selected = timeWindow.value
  const value = selected || (q.includes('week') ? '7d' : q.includes('24') || q.includes('day') ? '24h' : '24h')
  const match = value.match(/^(\d+)([hd])$/)
  if (!match) return 24 * 60
  const amount = Number(match[1])
  return match[2] === 'd' ? amount * 24 * 60 : amount * 60
}

async function fetchSensorSnapshot (minutes = 60) {
  try {
    const data = await requestWithTimeout(
      signal => api.get(`/api/weather/forecast/?minutes=${minutes}`, { signal }),
      SNAPSHOT_REQUEST_TIMEOUT_MS,
      'Sensor snapshot timed out.'
    )
    return Array.isArray(data) ? data : []
  } catch { return [] }
}

// ── Main submit ───────────────────────────────────────────────────────────
async function handleSubmit () {
  const q = buildFinalQuery(userQuery.value)
  if (!q) { error.value = 'Please enter a query or use voice input.'; return }

  loading.value         = true
  crewStatus.value      = 'loading'
  error.value           = ''
  response.value        = null
  chartData.value       = null
  reportDismissed.value = false
  destroyChart()
  startLoadingAnimation()

  pushHistory(q, activeMode.value)

  try {
    const snapshot = await fetchSensorSnapshot(activeMode.value === 'report' ? minutesForReportWindow() : 60)
    const fd = new FormData()
    fd.append('user_query', q)
    fd.append('language', lang.value)
    if (snapshot.length) fd.append('device_data', JSON.stringify(snapshot))

    if (activeMode.value === 'report') {
      const res = await postWithTimeout('/api/crew/report', fd, REPORT_REQUEST_TIMEOUT_MS)
      reportContent.value      = res.report || ''
      reportSnapshot.value     = snapshot
      reportCharts.value       = buildReportCharts(reportSnapshot.value)
      showDeliveryPrompt.value = reportContent.value.includes('delivery_prompt')
      crewStatus.value         = 'ok'
      await nextTick()
      renderReportCharts()
    } else {
      clearReportState()
      const res = await postWithTimeout('/api/crew/chat', fd)
      response.value = res
      if (res.chart?.chart_type) {
        chartData.value = res.chart
      }
      crewStatus.value = 'ok'
    }
  } catch (e) {
    error.value      = e.message || 'Request failed. Is the backend running?'
    crewStatus.value = 'error'
  } finally {
    loading.value = false
    stopLoadingAnimation()
  }
}

// ── Audio submit ──────────────────────────────────────────────────────────
async function handleAudioSubmit (blob) {
  loading.value    = true
  crewStatus.value = 'loading'
  error.value      = ''
  clearReportState()
  startLoadingAnimation()

  try {
    const snapshot = await fetchSensorSnapshot(minutesForReportWindow())
    const fd = new FormData()
    fd.append('audio_file', blob, 'recording.webm')
    fd.append('language', lang.value)
    if (snapshot.length) fd.append('device_data', JSON.stringify(snapshot))

    const res = await postWithTimeout('/api/crew/chat', fd)
    transcript.value = res.transcript || ''
    response.value   = res
    if (res.chart?.chart_type) chartData.value = res.chart
    crewStatus.value = 'ok'
    pushHistory(transcript.value || '(voice)', activeMode.value)
  } catch (e) {
    error.value      = e.message || 'Audio submission failed.'
    crewStatus.value = 'error'
  } finally {
    loading.value = false
    stopLoadingAnimation()
  }
}

// ── Generate report from chat response ────────────────────────────────────
async function generateReport () {
  const q = buildFinalQuery(userQuery.value) || 'Generate a full Smart Park analysis report.'
  reportLoading.value = true
  error.value         = ''
  startReportLoadingAnimation()

  try {
    const snapshot = await fetchSensorSnapshot()
    const fd = new FormData()
    fd.append('user_query', q)
    fd.append('language', lang.value)
    if (snapshot.length) fd.append('device_data', JSON.stringify(snapshot))

    const res = await postWithTimeout('/api/crew/report', fd, REPORT_REQUEST_TIMEOUT_MS)
    reportContent.value      = res.report || ''
    reportSnapshot.value     = snapshot
    reportCharts.value       = buildReportCharts(snapshot)
    showDeliveryPrompt.value = true
    await nextTick()
    renderReportCharts()
  } catch (e) {
    error.value = 'Report generation failed: ' + (e.message || 'Unknown error')
  } finally {
    reportLoading.value = false
    stopReportLoadingAnimation()
  }
}

function clearReport () {
  clearReportState()
}

function clearReportState () {
  reportContent.value      = ''
  reportSnapshot.value     = []
  reportCharts.value       = []
  showDeliveryPrompt.value = false
  deliveryChoice.value     = null
  deliveryResult.value     = null
  destroyReportCharts()
}

// ── Delivery (email / WhatsApp) ───────────────────────────────────────────
async function sendDelivery () {
  const contact = deliveryChoice.value === 'email' ? deliveryEmail.value : deliveryPhone.value
  if (!contact.trim()) { deliveryResult.value = { type: 'error', message: 'Please enter a valid contact.' }; return }

  deliverySending.value = true
  await new Promise(r => setTimeout(r, 1400))
  deliverySending.value = false
  deliveryResult.value  = {
    type: 'success',
    message: deliveryChoice.value === 'email'
      ? `✅ Report queued for delivery to ${deliveryEmail.value}`
      : `✅ Report queued for WhatsApp delivery to ${deliveryPhone.value}`,
  }
}

// ── Rendered text ─────────────────────────────────────────────────────────
function escapeHtml (s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

const parsedInsights = computed(() => {
  if (!response.value?.answer) return []
  return parseAgentResponse(response.value.answer)
})

function renderTextWithCitations (text) {
  if (!text) return ''
  let t = escapeHtml(text)
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong style="color:#fff">$1</strong>')
  t = t.replace(/\(Source:\s*([^)]+)\)/g, '<span class="ap-inline-source">⟨$1⟩</span>')
  t = t.replace(/\n\n/g, '</p><p class="ap-p">').replace(/\n/g, '<br>')
  return `<p class="ap-p">${t}</p>`
}

const renderedAnswer = computed(() => {
  if (!response.value?.answer) return ''
  return renderTextWithCitations(response.value.answer)
})

const hasLatex = computed(() => {
  const a = response.value?.answer || ''
  return a.includes('$$') || a.includes('$')
})

const responseSources = computed(() => {
  if (!response.value?.answer) return []
  const matches = [...response.value.answer.matchAll(/\(Source:\s*([^)]+)\)/g)]
  return [...new Set(matches.map(m => m[1].trim()))]
})

const renderedReport = computed(() => {
  if (!reportContent.value) return ''
  let html = reportContent.value

  html = html.replace(/```delivery_prompt[\s\S]*?```/g, '')

  html = html
    .replace(/^#### (.+)$/gm, '<h4 class="rh4">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="rh3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="rh2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="rh1">$1</h1>')
    .replace(/🟢/g, '<span class="rag green">🟢</span>')
    .replace(/🟡/g, '<span class="rag amber">🟡</span>')
    .replace(/🔴/g, '<span class="rag red">🔴</span>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\$\$(.+?)\$\$/gs, (_, m) => `<div class="ap-latex-block"><code class="ap-latex-code">${m.trim()}</code></div>`)
    .replace(/\$([^$\n]+?)\$/g, (_, m) => `<code class="ap-latex-inline">${m}</code>`)
    .replace(/(\|.+\|\n\|[-| :]+\|\n(?:\|.+\|\n?)+)/g, match => {
      const rows = match.trim().split('\n')
      const header = rows[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('')
      const body = rows.slice(2).map(r =>
        '<tr>' + r.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('') + '</tr>'
      ).join('\n')
      return `<div class="ap-table-wrap"><table class="ap-report-table"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`
    })
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul class="ap-ul">$1</ul>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/```json\n([\s\S]*?)```/g, '<div class="ap-chart-json-block">📊 Chart data embedded</div>')
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre class="ap-code">$1</pre>')
    .replace(/\n{2,}/g, '<br><br>')
    .replace(/\n/g, '<br>')

  return `<div class="ap-report-inner">${html}</div>`
})

// ── Chart rendering ───────────────────────────────────────────────────────
function destroyChart () {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }
}

async function renderChart (data) {
  destroyChart()
  chartKey.value++
  await nextTick()
  if (!chartCanvas.value) return

  const ctx = chartCanvas.value.getContext('2d')
  const allowedTypes = new Set(['bar','line','pie','doughnut','radar','scatter'])
  const type = allowedTypes.has(data.chart_type) ? data.chart_type : 'bar'

  const PALETTE = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4']

  const datasets = Array.isArray(data.datasets) && data.datasets.length
    ? data.datasets.map((ds, i) => ({
        label: ds.label || `Series ${i+1}`,
        data: ds.data || [],
        backgroundColor: ds.backgroundColor || PALETTE[i % PALETTE.length] + 'aa',
        borderColor: ds.borderColor || PALETTE[i % PALETTE.length],
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        fill: type === 'line' ? false : undefined,
        borderRadius: type === 'bar' ? 6 : 0,
      }))
    : [{
        label: data.title || 'Data',
        data: data.data || [],
        backgroundColor: type === 'bar' ? PALETTE[0] + 'aa' : PALETTE.map(c => c + 'cc'),
        borderColor: type === 'bar' ? PALETTE[0] : PALETTE,
        borderWidth: 2,
        tension: 0.35,
        pointRadius: 4,
        borderRadius: type === 'bar' ? 6 : 0,
      }]

  chartInstance = new Chart(ctx, {
    type,
    data: { labels: data.labels || [], datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: true,
          labels: { color: '#cbd5e1', font: { family: 'JetBrains Mono, monospace', size: 11 } },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#94a3b8',
          bodyColor: '#f1f5f9',
          borderColor: '#334155',
          borderWidth: 1,
        },
      },
      scales: ['pie','doughnut','radar'].includes(type) ? {} : {
        y: {
          grid: { color: '#1e293b' },
          ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono, monospace', size: 11 } },
        },
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono, monospace', size: 11 } },
        },
      },
    },
  })
}

watch(chartData, async val => { if (val) await renderChart(val) })

// ── Report chart rendering ────────────────────────────────────────────────
function toNumber (value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function formatReportNumber (value, unit = '') {
  const n = toNumber(value)
  if (n === null) return 'N/A'
  return `${n.toFixed(1)}${unit}`
}

function latestReadingsByDevice (rows) {
  const byDevice = new Map()
  rows.forEach(row => {
    if (!row?.device_id || !row?.time) return
    const current = byDevice.get(row.device_id)
    if (!current || new Date(row.time).getTime() > new Date(current.time).getTime()) {
      byDevice.set(row.device_id, row)
    }
  })
  return [...byDevice.values()].sort((a, b) => String(a.device_id).localeCompare(String(b.device_id)))
}

function trendRows (rows, limit = 24) {
  return rows
    .filter(row => row?.time && (toNumber(row.temperature) !== null || toNumber(row.humidity) !== null))
    .sort((a, b) => new Date(a.time) - new Date(b.time))
    .slice(-limit)
}

function hasValues (values, minCount = 1) {
  return values.filter(value => toNumber(value) !== null).length >= minCount
}

function buildReportCharts (rows) {
  if (!Array.isArray(rows) || rows.length === 0) return []

  const latest = latestReadingsByDevice(rows)
  const trend = trendRows(rows)
  const labels = latest.map(row => `Device ${row.device_id}`)
  const trendLabels = trend.map(row => {
    const date = new Date(row.time)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })

  const charts = []

  const tempTrend = trend.map(row => toNumber(row.temperature))
  const humidityTrend = trend.map(row => toNumber(row.humidity))

  if (trend.length && (hasValues(tempTrend, 2) || hasValues(humidityTrend, 2))) {
    charts.push({
      id: 'temp-humidity-trend',
      type: 'line',
      title: 'Temperature and Humidity Trend',
      description: 'Recent environmental movement across the selected report window.',
      data: {
        labels: trendLabels,
        datasets: [
          {
            label: 'Temperature (deg C)',
            data: tempTrend,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.14)',
            tension: 0.35,
            yAxisID: 'y'
          },
          {
            label: 'Humidity (%)',
            data: humidityTrend,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.14)',
            tension: 0.35,
            yAxisID: 'y1'
          }
        ]
      }
    })
  }

  if (latest.length) {
    const comparisonDatasets = [
      { label: 'Temperature (deg C)', data: latest.map(row => toNumber(row.temperature)), backgroundColor: 'rgba(239, 68, 68, 0.78)' },
      { label: 'Humidity (%)', data: latest.map(row => toNumber(row.humidity)), backgroundColor: 'rgba(37, 99, 235, 0.78)' },
      { label: 'Noise (dB)', data: latest.map(row => toNumber(row.noise)), backgroundColor: 'rgba(245, 158, 11, 0.78)' }
    ].filter(dataset => hasValues(dataset.data))

    if (comparisonDatasets.length) {
      charts.push({
      id: 'device-comparison',
      type: 'bar',
      title: 'Per-Device Environmental Comparison',
      description: 'Latest temperature, humidity, and noise readings by device.',
      data: {
        labels,
        datasets: comparisonDatasets
      }
      })
    }

    const humidityShare = latest.map(row => toNumber(row.humidity) ?? 0)
    if (humidityShare.some(value => value > 0)) {
      charts.push({
      id: 'humidity-share',
      type: 'doughnut',
      title: 'Humidity Distribution by Device',
      description: 'Relative share of the latest humidity readings.',
      data: {
        labels,
        datasets: [{
          label: 'Humidity (%)',
          data: humidityShare,
          backgroundColor: ['#2563eb', '#16a34a', '#f59e0b', '#7c3aed', '#ea580c', '#0f766e'],
          borderColor: '#ffffff',
          borderWidth: 2
        }]
      }
      })
    }

    const scatterPoints = rows
      .map(row => ({ x: toNumber(row.temperature), y: toNumber(row.humidity) }))
      .filter(point => point.x !== null && point.y !== null)
      .slice(-80)

    if (scatterPoints.length >= 2) {
      charts.push({
        id: 'temperature-humidity-scatter',
        type: 'scatter',
        title: 'Temperature vs Humidity Correlation',
        description: 'Scatter plot showing how humidity changes with temperature.',
        data: {
          datasets: [{
            label: 'Sensor samples',
            data: scatterPoints,
            backgroundColor: 'rgba(34, 197, 94, 0.78)',
            borderColor: '#22c55e'
          }]
        }
      })
    }
  }

  return charts
}

const reportStats = computed(() => {
  const latest = latestReadingsByDevice(reportSnapshot.value)
  const values = metric => latest.map(row => toNumber(row[metric])).filter(v => v !== null)
  const avg = metric => {
    const metricValues = values(metric)
    return metricValues.length ? metricValues.reduce((sum, v) => sum + v, 0) / metricValues.length : null
  }
  return [
    { label: 'Devices', value: String(latest.length || 'N/A') },
    { label: 'Avg Temp', value: formatReportNumber(avg('temperature'), ' deg C') },
    { label: 'Avg Humidity', value: formatReportNumber(avg('humidity'), '%') },
    { label: 'Avg Noise', value: formatReportNumber(avg('noise'), ' dB') }
  ]
})

function assignReportChartCanvas (el, index) {
  if (el) reportChartCanvases.value[index] = el
}

function destroyReportCharts () {
  reportChartInstances.forEach(instance => instance?.destroy())
  reportChartInstances = []
  reportChartCanvases.value = []
}

function reportChartOptions (chart) {
  const common = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#1f2937', font: { family: 'Times New Roman', size: 12 }, boxWidth: 12 }
      },
      tooltip: {
        backgroundColor: '#ffffff',
        titleColor: '#111827',
        bodyColor: '#111827',
        borderColor: '#cbd5e1',
        borderWidth: 1
      }
    }
  }

  if (chart.type === 'doughnut') {
    return { ...common, cutout: '62%' }
  }

  if (chart.type === 'scatter') {
    return {
      ...common,
      scales: {
        x: { title: { display: true, text: 'Temperature (deg C)', color: '#1d4ed8', font: { family: 'Times New Roman' } }, grid: { color: '#e2e8f0' }, ticks: { color: '#334155', font: { family: 'Times New Roman' } } },
        y: { title: { display: true, text: 'Humidity (%)', color: '#1d4ed8', font: { family: 'Times New Roman' } }, grid: { color: '#e2e8f0' }, ticks: { color: '#334155', font: { family: 'Times New Roman' } } }
      }
    }
  }

  return {
    ...common,
    scales: {
      x: { grid: { display: false }, ticks: { color: '#334155', font: { family: 'Times New Roman' } } },
      y: { grid: { color: '#e2e8f0' }, ticks: { color: '#334155', font: { family: 'Times New Roman' } } },
      ...(chart.id === 'temp-humidity-trend' ? {
        y1: { position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#1d4ed8', font: { family: 'Times New Roman' } } }
      } : {})
    }
  }
}

async function renderReportCharts () {
  destroyReportCharts()
  await nextTick()
  reportCharts.value.forEach((chart, index) => {
    const canvas = reportChartCanvases.value[index]
    if (!canvas) return
    reportChartInstances[index] = new Chart(canvas.getContext('2d'), {
      type: chart.type,
      data: chart.data,
      options: reportChartOptions(chart)
    })
  })
}

function reportChartImagesHtml () {
  return reportCharts.value.map((chart, index) => {
    const canvas = reportChartCanvases.value[index]
    const src = canvas?.toDataURL('image/png', 1)
    if (!src) return ''
    return `
      <section class="chart-card">
        <h3>${escapeHtml(chart.title)}</h3>
        <img src="${src}" alt="${escapeHtml(chart.title)}" />
        <p>${escapeHtml(chart.description)}</p>
      </section>
    `
  }).join('')
}

// ── PDF download ──────────────────────────────────────────────────────────
async function downloadPDF () {
  downloadingPDF.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const html2canvas = (await import('html2canvas')).default
    const source = reportExportRef.value
    if (!source) throw new Error('Report is not ready for export.')

    const originalMaxHeight = source.style.maxHeight
    const originalOverflow = source.style.overflow
    source.style.maxHeight = 'none'
    source.style.overflow = 'visible'
    await nextTick()

    const canvas = await html2canvas(source, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
      logging: false
    })

    source.style.maxHeight = originalMaxHeight
    source.style.overflow = originalOverflow

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageWidth = doc.internal.pageSize.getWidth()
    const pageHeight = doc.internal.pageSize.getHeight()
    const margin = 8
    const imgWidth = pageWidth - margin * 2
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    const pageCanvasHeight = (canvas.width * (pageHeight - margin * 2)) / imgWidth
    let renderedHeight = 0
    let page = 0

    while (renderedHeight < canvas.height) {
      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = canvas.width
      pageCanvas.height = Math.min(pageCanvasHeight, canvas.height - renderedHeight)
      const ctx = pageCanvas.getContext('2d')
      ctx.drawImage(canvas, 0, renderedHeight, canvas.width, pageCanvas.height, 0, 0, canvas.width, pageCanvas.height)
      const pageImg = pageCanvas.toDataURL('image/png', 1)
      if (page > 0) doc.addPage()
      doc.addImage(pageImg, 'PNG', margin, margin, imgWidth, (pageCanvas.height * imgWidth) / canvas.width)
      renderedHeight += pageCanvasHeight
      page++
    }

    doc.save('SmartPark_Report.pdf')
  } catch (e) {
    error.value = 'PDF download failed: ' + (e.message || 'Unknown error')
  } finally { downloadingPDF.value = false }
}

async function downloadWord () {
  downloadingWord.value = true
  try {
    const chartsHtml = reportChartImagesHtml()
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Smart Park Report</title>
    <style>
    body{font-family:"Times New Roman",Times,serif;font-size:12pt;margin:2.1cm;background:#ffffff;color:#111827}
    h1{font-family:"Times New Roman",Times,serif;font-size:22pt;color:#111827;border-bottom:3pt solid #2563eb;padding-bottom:8pt}
    h2{font-family:"Times New Roman",Times,serif;font-size:16pt;color:#1d4ed8;border-bottom:1pt solid #bfdbfe;padding-bottom:4pt;margin-top:18pt}
    h3{font-family:"Times New Roman",Times,serif;font-size:13pt;color:#0369a1;margin-top:14pt}
    p{line-height:1.45}table{border-collapse:collapse;width:100%;margin:12pt 0;border:1pt solid #cbd5e1}
    th{background:#1d4ed8;color:#fff;padding:7pt 10pt;text-align:left}
    td{border:1pt solid #dbeafe;padding:6pt 8pt}tr:nth-child(even){background:#eff6ff}
    .visuals{background:#f8fafc;border:1pt solid #bfdbfe;padding:14pt;margin-bottom:18pt}
    .chart-grid{display:block}.chart-card{background:#fff;border:1pt solid #bfdbfe;padding:12pt;margin:12pt 0}
    .chart-card img{width:100%;max-width:640px;display:block;margin:8pt auto}
    </style></head><body><div class="visuals"><h1>Visual Analytics</h1><div class="chart-grid">${chartsHtml}</div></div>${renderedReport.value}</body></html>`
    const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'SmartPark_Report.doc'
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) { error.value = 'Word download failed: ' + e.message }
  finally { downloadingWord.value = false }
}

// ── Weather icon helper ────────────────────────────────────────────────────
function weatherIcon (pred) {
  if (!pred) return '🌤️'
  const p = pred.toLowerCase()
  if (p.includes('clear') || p.includes('sunny')) return '☀️'
  if (p.includes('partly')) return '⛅'
  if (p.includes('cloud') || p.includes('overcast')) return '☁️'
  if (p.includes('rain')) return '🌧️'
  if (p.includes('storm')) return '⛈️'
  if (p.includes('snow')) return '❄️'
  if (p.includes('fog')) return '🌫️'
  return '🌤️'
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Tokens ─────────────────────────────────────────────── */
.agent-page {
  --bg0: #060b14;
  --bg1: #0c1625;
  --bg2: #111e30;
  --bg3: #162236;
  --border: rgba(99,133,169,0.15);
  --border-hi: rgba(99,133,169,0.3);
  --text-primary: #e2ecf8;
  --text-secondary: #7a94b0;
  --text-muted: #4a6180;
  --accent: #3b82f6;
  --accent-dim: rgba(59,130,246,0.15);
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --radius: 10px;
  --radius-sm: 6px;
  font-family: 'Space Grotesk', sans-serif;
  background: var(--bg0);
  min-height: 100vh;
  color: var(--text-primary);
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  grid-template-columns: 1fr;
  gap: 0;
  padding: 0;
}

/* ── Header ──────────────────────────────────────────────── */
.ap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg1);
}
.ap-header-left { display: flex; align-items: center; gap: 14px; }
.ap-logo { width: 44px; height: 44px; }
.ap-logo-ring {
  width: 44px; height: 44px; border-radius: 12px;
  background: var(--accent-dim);
  border: 1px solid rgba(59,130,246,0.3);
  display: flex; align-items: center; justify-content: center;
  color: var(--accent);
}
.ap-title { font-size: 1.1rem; font-weight: 700; margin: 0; line-height: 1.2; }
.ap-subtitle { font-size: 0.72rem; color: var(--text-muted); margin: 0; letter-spacing: 0.04em; }
.ap-header-right { display: flex; align-items: center; gap: 12px; }

.ap-status-pill {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 20px;
  font-size: 0.75rem; font-weight: 600;
  background: var(--bg2); border: 1px solid var(--border);
  color: var(--text-secondary);
  transition: all 0.3s;
}
.ap-status-pill.loading { border-color: var(--accent); color: var(--accent); }
.ap-status-pill.ok { border-color: var(--success); color: var(--success); }
.ap-status-pill.error { border-color: var(--danger); color: var(--danger); }
.ap-status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 2s infinite;
}
.ap-status-pill.loading .ap-status-dot { animation: pulse-dot 0.8s infinite; }

@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.3} }

.ap-lang-switcher { display: flex; gap: 4px; }
.ap-lang-btn {
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg2);
  cursor: pointer; font-size: 1rem;
  transition: all 0.15s;
  display: flex; align-items: center; justify-content: center;
}
.ap-lang-btn.active { border-color: var(--accent); background: var(--accent-dim); }
.ap-lang-btn:hover:not(.active) { border-color: var(--border-hi); }

/* ── Capability cards ────────────────────────────────────── */
.ap-caps {
  display: flex; gap: 8px; padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  overflow-x: auto; background: var(--bg1);
  scrollbar-width: none;
}
.ap-caps::-webkit-scrollbar { display: none; }

.ap-cap-card {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: var(--radius);
  background: var(--bg2); border: 1px solid var(--border);
  cursor: pointer; min-width: 180px;
  transition: all 0.2s; text-align: left;
}
.ap-cap-card:hover { border-color: var(--border-hi); background: var(--bg3); }
.ap-cap-card.active {
  border-color: var(--accent);
  background: var(--accent-dim);
  box-shadow: 0 0 0 1px rgba(59,130,246,0.2);
}
.ap-cap-icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.ap-cap-body { flex: 1; min-width: 0; }
.ap-cap-name { font-size: 0.78rem; font-weight: 600; color: var(--text-primary); white-space: nowrap; }
.ap-cap-desc { font-size: 0.68rem; color: var(--text-muted); margin-top: 1px; white-space: nowrap; }
.ap-cap-arrow { color: var(--accent); flex-shrink: 0; }

/* ── Workspace ───────────────────────────────────────────── */
.ap-workspace {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 0;
  min-height: 0;
  overflow: hidden;
}

/* ── Input panel ─────────────────────────────────────────── */
.ap-input-panel {
  padding: 18px;
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 14px;
  overflow-y: auto; background: var(--bg1);
}
.ap-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.72rem; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 6px;
}
.ap-label svg { opacity: 0.7; }
.ap-input-section { display: flex; flex-direction: column; }
.ap-query-wrap { position: relative; }
.ap-textarea {
  width: 100%; padding: 12px 14px;
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text-primary);
  font-family: 'Space Grotesk', sans-serif; font-size: 0.875rem;
  resize: vertical; min-height: 90px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.ap-textarea:focus { outline: none; border-color: var(--accent); }
.ap-textarea::placeholder { color: var(--text-muted); }
.ap-textarea:disabled { opacity: 0.5; }
.ap-textarea-footer {
  display: flex; justify-content: space-between;
  margin-top: 4px; padding: 0 2px;
}
.ap-hint { font-size: 0.68rem; color: var(--text-muted); }
.ap-char-count { font-size: 0.68rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
.ap-char-count.warn { color: var(--warning); }

/* Examples */
.ap-examples-section { display: flex; flex-direction: column; }
.ap-examples { display: flex; flex-wrap: wrap; gap: 6px; }
.ap-example-chip {
  padding: 5px 10px; border-radius: 20px;
  background: var(--bg2); border: 1px solid var(--border);
  font-size: 0.7rem; color: var(--text-secondary);
  cursor: pointer; transition: all 0.15s; text-align: left;
  font-family: 'Space Grotesk', sans-serif;
}
.ap-example-chip:hover { border-color: var(--accent); color: var(--accent); }

/* Options */
.ap-options-row { display: flex; flex-direction: column; gap: 10px; }
.ap-option-group { display: flex; flex-direction: column; }

.ap-voice-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 14px; border-radius: var(--radius-sm);
  background: var(--bg2); border: 1px solid var(--border);
  color: var(--text-secondary); cursor: pointer;
  font-size: 0.8rem; font-family: 'Space Grotesk', sans-serif;
  transition: all 0.2s; width: 100%; user-select: none;
}
.ap-voice-btn:hover:not(:disabled) { border-color: var(--border-hi); color: var(--text-primary); }
.ap-voice-btn.recording {
  background: rgba(239,68,68,0.15); border-color: var(--danger);
  color: var(--danger); animation: recording-pulse 1s ease-in-out infinite;
}
@keyframes recording-pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }

.ap-transcript {
  font-size: 0.72rem; color: var(--text-muted); margin: 5px 0 0;
  padding: 6px 10px; background: var(--bg2);
  border-radius: 6px; border-left: 2px solid var(--accent);
}

.ap-select {
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: var(--bg2); border: 1px solid var(--border);
  color: var(--text-primary); font-size: 0.8rem;
  font-family: 'Space Grotesk', sans-serif;
  width: 100%; cursor: pointer;
}
.ap-select:focus { outline: none; border-color: var(--accent); }

/* Toggles */
.ap-toggle-row { display: flex; flex-direction: column; gap: 8px; }
.ap-toggle-label {
  display: flex; align-items: center; gap: 10px;
  cursor: pointer; font-size: 0.78rem; color: var(--text-secondary);
}
.ap-toggle-input { display: none; }
.ap-toggle-track {
  width: 32px; height: 18px; border-radius: 9px;
  background: var(--bg3); border: 1px solid var(--border);
  position: relative; transition: background 0.2s; flex-shrink: 0;
}
.ap-toggle-track::after {
  content: ''; position: absolute;
  width: 12px; height: 12px; border-radius: 50%;
  background: var(--text-muted);
  top: 2px; left: 2px; transition: all 0.2s;
}
.ap-toggle-input:checked + .ap-toggle-track { background: var(--accent-dim); border-color: var(--accent); }
.ap-toggle-input:checked + .ap-toggle-track::after { background: var(--accent); transform: translateX(14px); }

/* Submit */
.ap-submit-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 12px 20px; border-radius: var(--radius);
  background: var(--accent); border: none;
  color: #fff; font-size: 0.9rem; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
  font-family: 'Space Grotesk', sans-serif;
  box-shadow: 0 4px 16px rgba(59,130,246,0.25);
}
.ap-submit-btn:hover:not(:disabled) { background: #2563eb; transform: translateY(-1px); box-shadow: 0 6px 20px rgba(59,130,246,0.35); }
.ap-submit-btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none; }

.ap-error {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 10px 14px; border-radius: var(--radius-sm);
  background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3);
  color: #fca5a5; font-size: 0.8rem;
}

/* ── Output panel ────────────────────────────────────────── */
.ap-output-panel {
  padding: 18px;
  overflow-y: auto;
  background: var(--bg0);
  display: flex; flex-direction: column; gap: 16px;
}

/* Empty state */
.ap-empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 100%; text-align: center;
  padding: 40px 20px; gap: 12px;
}
.ap-empty-orb {
  width: 80px; height: 80px; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #1d4ed8, #1e3a5f);
  box-shadow: 0 0 40px rgba(59,130,246,0.2);
  margin-bottom: 8px;
  animation: orb-float 4s ease-in-out infinite;
}
@keyframes orb-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
.ap-empty-title { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.ap-empty-sub { font-size: 0.82rem; color: var(--text-secondary); margin: 0; line-height: 1.6; }
.ap-empty-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 6px; }
.ap-tag {
  padding: 4px 10px; border-radius: 20px;
  background: var(--bg2); border: 1px solid var(--border);
  font-size: 0.7rem; color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

/* Loading */
.ap-loading-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 40px 20px; gap: 16px;
}
.ap-loading-icon { position: relative; width: 56px; height: 56px; display: flex; align-items: center; justify-content: center; }
.ap-pulse-ring {
  position: absolute; inset: 0; border-radius: 50%;
  border: 2px solid var(--accent); opacity: 0.4;
  animation: pulse-ring 1.5s ease-out infinite;
}
@keyframes pulse-ring { 0%{transform:scale(1);opacity:0.4} 100%{transform:scale(1.6);opacity:0} }
.ap-loading-phase { font-size: 0.85rem; color: var(--text-secondary); margin: 0; }
.ap-loading-steps { display: flex; flex-direction: column; gap: 8px; align-self: stretch; max-width: 320px; }
.ap-loading-step {
  display: flex; align-items: center; gap: 10px;
  font-size: 0.78rem; color: var(--text-muted);
  transition: color 0.3s;
}
.ap-loading-step.active { color: var(--accent); }
.ap-loading-step.done { color: var(--success); }
.ap-step-dot {
  width: 8px; height: 8px; border-radius: 50%;
  border: 1.5px solid currentColor; flex-shrink: 0;
  transition: background 0.3s;
}
.ap-loading-step.done .ap-step-dot { background: var(--success); border-color: var(--success); }
.ap-loading-step.active .ap-step-dot { background: var(--accent); border-color: var(--accent); animation: pulse-dot 0.6s infinite; }

/* ── Response ─────────────────────────────────────────────── */
.ap-response {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fade-in-up 0.6s ease-out;
}
.ap-source-bar { display: flex; flex-wrap: wrap; gap: 6px; }

/* Enhanced Chart Visuals */
.ap-chart-section {
  background: rgba(12, 22, 37, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-hi);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
.ap-chart-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.ap-chart-type-badge {
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--accent-dim);
  border: 1px solid rgba(59,130,246,0.3);
  font-size: 0.65rem;
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.ap-chart-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}
.ap-chart-wrap { position: relative; height: 320px; }
.ap-chart-desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 16px;
  font-style: italic;
  text-align: center;
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Answer */
.ap-answer-block {
  background: var(--bg1); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 18px;
}
.ap-latex-notice {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; border-radius: var(--radius-sm);
  background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.25);
  font-size: 0.72rem; color: #c4b5fd;
  margin-bottom: 12px;
}
.ap-answer-content { font-size: 0.875rem; line-height: 1.7; color: var(--text-primary); }

/* ── Weather callout ──────────────────────────────────────── */
.ap-weather-callout {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px 16px; border-radius: var(--radius);
  background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25);
  margin-top: 4px;
}
.ap-weather-icon { font-size: 2rem; line-height: 1; }
.ap-weather-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 600; }
.ap-weather-val { font-size: 1rem; font-weight: 600; color: var(--success); margin: 2px 0; }
.ap-weather-conf { font-size: 0.75rem; color: var(--text-muted); }
.ap-conf-bar { height: 4px; border-radius: 2px; background: var(--bg3); margin-top: 4px; width: 120px; }
.ap-conf-fill { height: 100%; border-radius: 2px; background: var(--success); transition: width 0.6s ease; }

/* Transcript details */
.ap-transcript-details {
  font-size: 0.78rem; color: var(--text-muted);
}
.ap-transcript-details summary { cursor: pointer; padding: 6px; }
.ap-transcript-details pre {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px; font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; white-space: pre-wrap; color: var(--text-secondary);
  margin: 6px 0 0;
}

/* Report prompt */
.ap-report-prompt {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 14px;
  padding: 16px; border-radius: var(--radius);
  background: var(--bg2); border: 1px solid var(--border);
}
.ap-report-prompt-left { display: flex; align-items: flex-start; gap: 14px; }
.ap-report-prompt-title { font-size: 0.875rem; font-weight: 600; margin: 0 0 4px; }
.ap-report-prompt-sub { font-size: 0.75rem; color: var(--text-muted); margin: 0; line-height: 1.5; }
.ap-report-prompt-actions { display: flex; gap: 8px; flex-shrink: 0; align-items: center; }

/* ── Report output ────────────────────────────────────────── */
.ap-report-output {
  background: var(--bg1); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden;
  animation: report-slide-in 0.6s cubic-bezier(0.23, 1, 0.32, 1) forwards;
}
.ap-report-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 18px; border-bottom: 1px solid var(--border);
  background: var(--bg2);
}
.ap-report-header-left { display: flex; align-items: center; gap: 10px; font-size: 0.875rem; font-weight: 600; }
.ap-report-actions { display: flex; gap: 8px; }
.ap-action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: var(--radius-sm);
  background: var(--bg3); border: 1px solid var(--border);
  color: var(--text-secondary); font-size: 0.75rem;
  font-weight: 600; cursor: pointer; transition: all 0.15s;
  font-family: 'Space Grotesk', sans-serif;
}
.ap-action-btn:hover:not(:disabled) { border-color: var(--border-hi); color: var(--text-primary); }
.ap-action-btn.danger:hover { border-color: var(--danger); color: var(--danger); }
.ap-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ap-report-export {
  background: #ffffff;
  color: #111827;
  font-family: 'Times New Roman', Times, serif;
}
.ap-report-body { padding: 20px 24px; max-height: 60vh; overflow-y: auto; }
.ap-report-export .ap-report-body { max-height: none; overflow: visible; }
.ap-report-visuals {
  padding: 24px;
  border-bottom: 1px solid #bfdbfe;
  background: linear-gradient(180deg, #eff6ff, #ffffff);
}
.ap-report-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.ap-report-kicker {
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.ap-report-hero h2 {
  color: #111827;
  font-size: 1.45rem;
  margin: 4px 0 6px;
}
.ap-report-hero p {
  color: #475569;
  margin: 0;
  max-width: 620px;
  font-size: 0.86rem;
  line-height: 1.5;
}
.ap-report-stat-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(110px, 1fr));
  gap: 8px;
  min-width: 260px;
}
.ap-report-stat {
  padding: 10px 12px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #ffffff;
}
.ap-report-stat span {
  display: block;
  color: #1d4ed8;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
}
.ap-report-stat strong {
  display: block;
  color: #111827;
  font-size: 1.05rem;
  margin-top: 2px;
}
.ap-report-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 14px;
}
.ap-report-chart-card {
  min-height: 330px;
  padding: 16px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.1);
}
.ap-report-chart-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.ap-report-chart-head h3 {
  color: #111827;
  font-size: 0.95rem;
  margin: 0;
}
.ap-report-chart-type {
  padding: 3px 8px;
  border-radius: 6px;
  background: #dbeafe;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
}
.ap-report-chart-wrap {
  height: 230px;
  position: relative;
}
.ap-report-chart-card p {
  color: #475569;
  font-size: 0.76rem;
  line-height: 1.45;
  margin: 10px 0 0;
}

/* Delivery */
.ap-delivery-section {
  border-top: 1px solid var(--border); padding: 18px 24px;
  background: var(--bg2);
}
.ap-delivery-header {
  display: flex; align-items: center; gap: 10px;
  font-size: 0.875rem; font-weight: 600;
  color: var(--text-primary); margin-bottom: 14px;
}
.ap-delivery-options { display: flex; gap: 8px; flex-wrap: wrap; }
.ap-delivery-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 16px; border-radius: var(--radius-sm);
  font-size: 0.8rem; font-weight: 600; cursor: pointer;
  border: 1px solid var(--border); background: var(--bg3);
  color: var(--text-secondary); transition: all 0.2s;
  font-family: 'Space Grotesk', sans-serif;
}
.ap-delivery-btn.email:hover { border-color: #3b82f6; color: #3b82f6; background: rgba(59,130,246,0.1); }
.ap-delivery-btn.whatsapp:hover { border-color: #25d366; color: #25d366; background: rgba(37,211,102,0.1); }
.ap-delivery-btn.skip:hover { border-color: var(--danger); color: var(--danger); }
.ap-delivery-form { display: flex; flex-direction: column; gap: 8px; }
.ap-delivery-input-row { display: flex; gap: 8px; }
.ap-input {
  flex: 1; padding: 8px 12px; border-radius: var(--radius-sm);
  background: var(--bg1); border: 1px solid var(--border);
  color: var(--text-primary); font-size: 0.85rem;
  font-family: 'Space Grotesk', sans-serif;
}
.ap-input:focus { outline: none; border-color: var(--accent); }
.ap-delivery-result {
  padding: 8px 12px; border-radius: var(--radius-sm);
  font-size: 0.8rem; margin-top: 6px;
}
.ap-delivery-result.success { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #6ee7b7; }
.ap-delivery-result.error { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #fca5a5; }

/* ── Buttons ──────────────────────────────────────────────── */
.ap-btn-primary {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 16px; border-radius: var(--radius-sm);
  background: var(--accent); border: none;
  color: #fff; font-size: 0.8rem; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
  font-family: 'Space Grotesk', sans-serif;
  white-space: nowrap;
}
.ap-btn-primary.sm { padding: 6px 12px; font-size: 0.75rem; }
.ap-btn-primary:hover:not(:disabled) { background: #2563eb; }
.ap-btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
.ap-btn-ghost {
  padding: 8px 14px; border-radius: var(--radius-sm);
  background: transparent; border: 1px solid var(--border);
  color: var(--text-muted); font-size: 0.8rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s;
  font-family: 'Space Grotesk', sans-serif;
  white-space: nowrap;
}
.ap-btn-ghost.sm { padding: 6px 10px; font-size: 0.75rem; }
.ap-btn-ghost:hover { border-color: var(--border-hi); color: var(--text-primary); }

/* ── Transitions ────────────────────────────────────────────── */
.ap-fade-slide-enter-active, .ap-fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.ap-fade-slide-enter-from, .ap-fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.ap-step-fade-enter-active, .ap-step-fade-leave-active {
  transition: all 0.3s ease;
}
.ap-step-fade-enter-from, .ap-step-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

.ap-answer-content {
  animation: text-reveal 0.8s ease-out forwards;
}
@keyframes text-reveal {
  from { opacity: 0; filter: blur(4px); transform: translateY(5px); }
  to { opacity: 1; filter: blur(0); transform: translateY(0); }
}

@keyframes report-slide-in {
  from { opacity: 0; transform: scale(0.95) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.ap-loading-step.active .ap-step-dot {
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 12px var(--accent);
  animation: pulse-dot 0.6s infinite;
}
.ap-step-text {
  transition: color 0.3s, transform 0.3s;
}
.ap-loading-step.active .ap-step-text {
  transform: translateX(4px);
  color: var(--accent);
}

/* ── History bar ──────────────────────────────────────────── */
.ap-history-bar {
  border-top: 1px solid var(--border);
  background: var(--bg1);
  padding: 10px 24px;
  display: flex; align-items: center; gap: 14px;
  overflow-x: auto; scrollbar-width: none;
}
.ap-history-bar::-webkit-scrollbar { display: none; }
.ap-history-label {
  font-size: 0.68rem; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.06em; flex-shrink: 0;
}
.ap-history-list { display: flex; gap: 6px; }
.ap-history-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 12px; border-radius: 20px;
  background: var(--bg2); border: 1px solid var(--border);
  cursor: pointer; transition: all 0.15s;
  font-family: 'Space Grotesk', sans-serif;
}
.ap-history-item:hover { border-color: var(--border-hi); }
.ap-history-mode {
  width: 18px; height: 18px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.6rem; font-weight: 700; color: #fff; flex-shrink: 0;
}
.ap-history-q { font-size: 0.72rem; color: var(--text-secondary); white-space: nowrap; max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.ap-history-ts { font-size: 0.65rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; flex-shrink: 0; }
.ap-history-empty { font-size: 0.75rem; color: var(--text-muted); }

/* ── Responsive ───────────────────────────────────────────── */
@media (max-width: 900px) {
  .ap-workspace { grid-template-columns: 1fr; }
  .ap-input-panel { border-right: none; border-bottom: 1px solid var(--border); }
  .ap-caps { padding: 10px 16px; }
  .ap-header { padding: 14px 16px; }
}
@media (max-width: 600px) {
  .ap-cap-card { min-width: 150px; }
  .ap-report-prompt { flex-direction: column; }
  .ap-delivery-input-row { flex-direction: column; }
}
</style>

<style>
/* ── Global (v-html rendered content) ────────────────────── */
.ap-p { margin: 0 0 10px; }
.ap-p:last-child { margin-bottom: 0; }
.ap-latex-block {
  margin: 12px 0; padding: 12px 16px;
  background: #f8fafc; border: 1px solid #cbd5e1;
  border-radius: 8px; overflow-x: auto;
}
.ap-latex-code {
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.9rem; color: #1e293b; white-space: pre;
}
.ap-latex-inline {
  font-family: 'Times New Roman', Times, serif;
  font-size: 0.9rem; color: #1d4ed8;
  background: #eff6ff; padding: 1px 6px; border-radius: 4px;
}
.ap-inline-source {
  font-size: 0.68rem; color: #4a6180;
  font-family: 'JetBrains Mono', monospace; margin-left: 4px;
}

/* Report */
.rh1 { font-family: 'Times New Roman', Times, serif; font-size: 1.65rem; font-weight: 700; color: #111827; margin: 24px 0 10px; border-bottom: 2px solid #2563eb; padding-bottom: 6px; }
.rh2 { font-family: 'Times New Roman', Times, serif; font-size: 1.25rem; font-weight: 700; color: #1d4ed8; margin: 20px 0 8px; border-bottom: 1px solid #bfdbfe; padding-bottom: 4px; }
.rh3 { font-family: 'Times New Roman', Times, serif; font-size: 1.05rem; font-weight: 700; color: #0369a1; margin: 14px 0 6px; }
.rh4 { font-family: 'Times New Roman', Times, serif; font-size: 0.95rem; font-weight: 700; color: #334155; margin: 10px 0 4px; }
.rp  { margin: 0 0 8px; font-size: 1rem; line-height: 1.7; color: #1f2937; }
.ap-ul { padding-left: 20px; margin: 6px 0; }
.ap-ul li { font-family: 'Times New Roman', Times, serif; font-size: 1rem; margin-bottom: 4px; color: #1f2937; }
.rag { font-size: 1em; }

.ap-table-wrap { overflow-x: auto; margin: 12px 0; }
.ap-report-table { width: 100%; border-collapse: collapse; font-family: 'Times New Roman', Times, serif; font-size: 0.95rem; border: 1px solid #cbd5e1; }
.ap-report-table th { background: #1d4ed8; color: #ffffff; font-weight: 700; padding: 8px 12px; text-align: left; border: 1px solid #1e40af; }
.ap-report-table td { padding: 7px 12px; border: 1px solid #dbeafe; color: #1f2937; }
.ap-report-table tr:nth-child(even) td { background: #eff6ff; }
.ap-code { background: #0c1625; border: 1px solid rgba(99,133,169,0.2); border-radius: 6px; padding: 10px 14px; font-size: 0.78rem; font-family: 'JetBrains Mono', monospace; color: #94a3b8; overflow-x: auto; white-space: pre; margin: 8px 0; }
.ap-chart-json-block { padding: 8px 12px; background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.2); border-radius: 6px; font-size: 0.78rem; color: #60a5fa; margin: 6px 0; }
.ap-report-inner { color: #1f2937; font-family: 'Times New Roman', Times, serif; }
</style>
