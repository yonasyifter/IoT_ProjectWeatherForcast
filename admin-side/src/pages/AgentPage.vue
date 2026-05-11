<template>
  <div class="agent-page p-4">
    <div class="container-lg">
      <!-- Header -->
      <div class="mb-5">
        <h1 class="h2 mb-2">
          <i class="bi bi-cpu me-2 text-primary"></i>AI Agent Data Explorer
        </h1>
        <p class="text-muted">
          Query park sensor data and device intelligence using natural language.
          Powered by RCMS Edge OpenAPI + InfluxDB multi-agent analysis.
        </p>
      </div>

      <!-- Query Input -->
      <div class="card shadow-sm mb-4 border-0">
        <div class="card-body p-4">
          <div class="input-group input-group-lg">
            <input
              type="text"
              class="form-control border-end-0"
              placeholder="Ask the AI (e.g. 'Show temperature trends', 'Which devices are online?', 'Generate a park status report')"
              v-model="userQuery"
              @keyup.enter="submitQuery"
              :disabled="loading"
              aria-label="Query input"
            />
            <button
              class="btn btn-primary px-4"
              @click="submitQuery"
              :disabled="loading || !userQuery.trim()"
            >
              <span v-if="loading" class="spinner-border spinner-border-sm me-2" role="status"></span>
              <i v-else class="bi bi-send-fill me-2"></i>
              {{ loading ? 'Thinking...' : 'Ask AI' }}
            </button>
          </div>
          <small class="form-text text-muted mt-2 d-block">
            <strong>Examples:</strong>
            "Show rainfall trends for the last 7 days" &nbsp;·&nbsp;
            "Which devices are online?" &nbsp;·&nbsp;
            "Any active alerts?" &nbsp;·&nbsp;
            "Compare temperature and humidity"
          </small>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center p-5">
        <div class="spinner-border text-primary mb-3" role="status"></div>
        <p class="text-muted">{{ loadingMessage }}</p>
      </div>

      <!-- Error -->
      <div v-if="error" class="alert alert-danger alert-dismissible fade show" role="alert">
        <i class="bi bi-exclamation-triangle-fill me-2"></i>
        <strong>Error:</strong> {{ error }}
        <button type="button" class="btn-close" @click="error = null"></button>
      </div>

      <!-- AI Response -->
      <div v-if="aiResponse && !loading" class="card shadow-sm border-0 mt-4">
        <div class="card-header border-0 py-3 response-header">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0 text-white">
              <i class="bi bi-robot me-2"></i>AI Response
            </h5>
            <span class="badge bg-white text-primary" v-if="aiResponse.language">
              {{ aiResponse.language.toUpperCase() }}
            </span>
          </div>
        </div>
        <div class="card-body p-4">

          <!-- Chart -->
          <div v-if="isChartResponse" class="chart-container">
            <h3 class="h5 mb-2">{{ aiResponse.chart.title }}</h3>
            <p class="text-muted small mb-3">{{ aiResponse.chart.description || aiResponse.answer }}</p>
            <div class="chart-wrapper">
              <canvas ref="chartCanvas" :key="chartKey"></canvas>
            </div>
          </div>

          <!-- Text -->
          <div v-else class="text-response">
            <pre class="ai-answer">{{ aiResponse.answer }}</pre>
            <div v-if="aiResponse.weather_prediction" class="alert alert-info mt-3">
              <i class="bi bi-cloud-sun-fill me-2"></i>
              <strong>Weather:</strong> {{ aiResponse.weather_prediction }}
              <span v-if="aiResponse.prediction_confidence" class="ms-2 text-muted">
                ({{ Math.round(aiResponse.prediction_confidence) }}% confidence)
              </span>
            </div>
          </div>

          <!-- Transcript -->
          <div v-if="aiResponse.transcript" class="mt-4 pt-3 border-top">
            <details class="small">
              <summary class="cursor-pointer text-muted">
                <i class="bi bi-mic-fill me-1"></i>Transcript
              </summary>
              <pre class="mt-2 p-2 bg-light rounded text-break">{{ aiResponse.transcript }}</pre>
            </details>
          </div>

          <!-- ═══ REPORT PROMPT SECTION ═══ -->
          <div v-if="!reportMode && !reportContent" class="mt-4 pt-3 border-top report-prompt-section">
            <div class="d-flex align-items-start gap-3">
              <div class="report-icon">
                <i class="bi bi-file-earmark-text display-6 text-primary opacity-75"></i>
              </div>
              <div class="flex-grow-1">
                <p class="mb-2 fw-semibold">Would you like a detailed report of this analysis?</p>
                <p class="text-muted small mb-3">
                  The AI crew can generate a comprehensive report — including device inventory,
                  anomaly findings, system health, and recommendations — that you can download
                  as <strong>PDF</strong> or <strong>Word</strong>.
                </p>
                <div class="d-flex gap-2 flex-wrap">
                  <button class="btn btn-primary btn-sm" @click="generateReport" :disabled="reportLoading">
                    <span v-if="reportLoading" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="bi bi-file-earmark-pdf me-1"></i>
                    Yes, generate report
                  </button>
                  <button class="btn btn-outline-secondary btn-sm" @click="dismissReport">
                    <i class="bi bi-x me-1"></i>No thanks
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Report loading -->
          <div v-if="reportLoading" class="mt-3 text-center py-3">
            <div class="spinner-border text-primary mb-2" role="status"></div>
            <p class="text-muted small">Generating comprehensive report… this may take up to 60 seconds.</p>
          </div>
        </div>
      </div>

      <!-- ═══ REPORT OUTPUT SECTION ═══ -->
      <div v-if="reportContent && !reportLoading" class="card shadow-sm border-0 mt-4">
        <div class="card-header border-0 py-3 report-header">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0 text-white">
              <i class="bi bi-file-earmark-text me-2"></i>Smart Park Analysis Report
            </h5>
            <div class="d-flex gap-2">
              <button class="btn btn-light btn-sm" @click="downloadPDF" :disabled="downloadingPDF">
                <span v-if="downloadingPDF" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-file-earmark-pdf-fill me-1 text-danger"></i>
                {{ downloadingPDF ? 'Generating…' : 'Download PDF' }}
              </button>
              <button class="btn btn-light btn-sm" @click="downloadWord" :disabled="downloadingWord">
                <span v-if="downloadingWord" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-file-earmark-word-fill me-1 text-primary"></i>
                {{ downloadingWord ? 'Generating…' : 'Download Word' }}
              </button>
            </div>
          </div>
        </div>
        <div class="card-body p-4">
          <div class="report-content" v-html="renderedReport"></div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && !error && !aiResponse" class="text-center p-5 text-muted">
        <i class="bi bi-chat-left-text display-1 mb-3 d-block opacity-25"></i>
        <p>Ask a question about the park's environmental data or device status to get started.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { api } from '@/utils/api';
import Chart from 'chart.js/auto';

// ── State ──────────────────────────────────────────────────────────────────
const userQuery        = ref('');
const loading          = ref(false);
const loadingMessage   = ref('Processing your query...');
const error            = ref(null);
const aiResponse       = ref(null);
const chartCanvas      = ref(null);
const chartKey         = ref(0);
const weatherCondition = ref('');
const deviceHealthStatus = ref('');
const userLocalization = ref('');
const mobilityStatus   = ref('');
let chartInstance      = null;

// Report state
const reportMode     = ref(false);   // true = user dismissed report prompt
const reportContent  = ref('');      // raw Markdown from /api/crew/report
const reportLoading  = ref(false);
const downloadingPDF  = ref(false);
const downloadingWord = ref(false);

// Cached form data for re-use in report generation
let cachedFormData = null;

// ── Computed ───────────────────────────────────────────────────────────────
const isChartResponse = computed(() =>
  Boolean(aiResponse.value?.chart?.chart_type)
);

const renderedReport = computed(() => {
  if (!reportContent.value) return '';
  // Simple Markdown → HTML renderer (no external lib needed)
  let html = reportContent.value
    // headings
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // tables — convert | header | -> <table>
    .replace(/(\|.+\|\n\|[-| :]+\|\n(?:\|.+\|\n?)+)/g, (match) => {
      const rows = match.trim().split('\n');
      const header = rows[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
      const body = rows.slice(2).map(r =>
        '<tr>' + r.split('|').filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join('') + '</tr>'
      ).join('\n');
      return `<table class="table table-bordered table-sm my-3"><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
    })
    // bullet lists
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    // numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
  return `<div class="md-report"><p>${html}</p></div>`;
});

// ── Helpers ────────────────────────────────────────────────────────────────
async function buildFormData(query) {
  const contextData = {
    weather_condition:   weatherCondition.value.trim() || null,
    device_health_status: deviceHealthStatus.value.trim() || null,
    user_localization:   userLocalization.value.trim() || null,
    mobility_status:     mobilityStatus.value.trim() || null,
  };

  let deviceData = null;
  try {
    const snapshot = await api.get('/api/weather/forecast/?minutes=60');
    if (Array.isArray(snapshot) && snapshot.length) deviceData = snapshot;
  } catch (e) {
    console.warn('Could not fetch weather snapshot:', e);
  }

  const fd = new FormData();
  fd.append('user_query', query);
  fd.append('language', 'en');
  fd.append('context_data', JSON.stringify(contextData));
  if (deviceData) fd.append('device_data', JSON.stringify(deviceData));
  return fd;
}

// ── Query submission ───────────────────────────────────────────────────────
const submitQuery = async () => {
  if (!userQuery.value.trim()) return;

  loading.value = true;
  loadingMessage.value = 'Processing your query…';
  error.value = null;
  aiResponse.value = null;
  reportMode.value = false;
  reportContent.value = '';
  destroyChart();

  try {
    cachedFormData = await buildFormData(userQuery.value);

    loadingMessage.value = 'Consulting AI agents…';
    const response = await api.post('/api/crew/chat', cachedFormData);

    if (response?.answer || response?.chart) {
      aiResponse.value = response;
    } else {
      error.value = 'No response from AI. Please try again.';
    }
  } catch (err) {
    console.error('Error fetching AI response:', err);
    if (err.message?.includes('401'))        error.value = 'Session expired. Please log in again.';
    else if (err.message?.includes('403'))   error.value = 'Admin access required.';
    else if (err.message?.includes('fetch')) error.value = 'Cannot connect to backend. Is it running?';
    else                                     error.value = err.message || 'Failed to get AI response.';
  } finally {
    loading.value = false;
  }
};

// ── Report generation ──────────────────────────────────────────────────────
const generateReport = async () => {
  reportLoading.value = true;
  try {
    // Build a fresh FormData for the report endpoint
    const fd = cachedFormData
      ? cachedFormData
      : await buildFormData(userQuery.value || 'Generate a full Smart Park analysis report.');

    // Clone and swap query for report endpoint
    const reportFd = new FormData();
    for (const [k, v] of fd.entries()) reportFd.append(k, v);
    // Override user_query to instruct report mode
    reportFd.set('user_query', userQuery.value || 'Generate a full Smart Park analysis report.');

    const resp = await api.post('/api/crew/report', reportFd);
    reportContent.value = resp.report || 'Report content unavailable.';
    reportMode.value = true;
  } catch (err) {
    console.error('Report error:', err);
    error.value = 'Failed to generate report: ' + (err.message || 'Unknown error');
  } finally {
    reportLoading.value = false;
  }
};

const dismissReport = () => {
  reportMode.value = true;
};

// ── Download helpers ───────────────────────────────────────────────────────
const downloadPDF = async () => {
  downloadingPDF.value = true;
  try {
    const { jsPDF } = await import('jspdf');
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    // Strip markdown to plain text for PDF
    const plain = reportContent.value
      .replace(/#{1,4} /g, '')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/\|/g, '  ')
      .replace(/[-]{3,}/g, '')
      .split('\n')
      .filter(l => l.trim());

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.text('Smart Park Analysis Report', 14, 20);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);

    let y = 32;
    const pageH = doc.internal.pageSize.getHeight();
    const margin = 14;
    const maxW = doc.internal.pageSize.getWidth() - margin * 2;

    for (const line of plain) {
      // Detect heading lines
      const isHeading = /^(#{1,4} )/.test(line) || reportContent.value.includes(`# ${line}`);

      if (isHeading) {
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(12);
      } else {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10);
      }

      const wrapped = doc.splitTextToSize(line, maxW);
      for (const wl of wrapped) {
        if (y > pageH - 15) {
          doc.addPage();
          y = 20;
        }
        doc.text(wl, margin, y);
        y += isHeading ? 7 : 5;
      }
    }

    doc.save('SmartPark_Report.pdf');
  } catch (err) {
    console.error('PDF error:', err);
    // Fallback: print to PDF via browser
    const w = window.open('', '_blank');
    if (w) {
      w.document.write(`
        <html><head><title>Smart Park Report</title>
        <style>body{font-family:Arial,sans-serif;padding:2rem;max-width:900px;margin:auto;}
        h1,h2,h3,h4{color:#1a1a2e;} table{border-collapse:collapse;width:100%;}
        th,td{border:1px solid #ccc;padding:6px 10px;} pre{white-space:pre-wrap;}</style>
        </head><body>${renderedReport.value}</body></html>`);
      w.document.close();
      w.print();
    }
  } finally {
    downloadingPDF.value = false;
  }
};

const downloadWord = async () => {
  downloadingWord.value = true;
  try {
    // Build a simple HTML-based .doc that Word can open
    const htmlContent = `
<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
  <meta charset="utf-8">
  <title>Smart Park Report</title>
  <!--[if gte mso 9]>
  <xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml>
  <![endif]-->
  <style>
    body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; margin: 2.5cm; }
    h1 { font-size: 20pt; color: #1a237e; }
    h2 { font-size: 15pt; color: #283593; border-bottom: 1px solid #9fa8da; }
    h3 { font-size: 13pt; color: #3949ab; }
    h4 { font-size: 11pt; color: #3f51b5; }
    table { border-collapse: collapse; width: 100%; margin: 12pt 0; }
    th { background: #3f51b5; color: white; padding: 6pt 10pt; font-weight: bold; }
    td { border: 1pt solid #c5cae9; padding: 5pt 8pt; }
    tr:nth-child(even) { background: #e8eaf6; }
    p { margin: 6pt 0; }
    li { margin: 3pt 0; }
    .badge-critical { color: #b71c1c; font-weight: bold; }
    .badge-warning  { color: #e65100; font-weight: bold; }
    .badge-info     { color: #1565c0; }
  </style>
</head>
<body>
${renderedReport.value}
</body>
</html>`;

    const blob = new Blob([htmlContent], {
      type: 'application/msword;charset=utf-8'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'SmartPark_Report.doc';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Word download error:', err);
    error.value = 'Failed to generate Word document.';
  } finally {
    downloadingWord.value = false;
  }
};

// ── Chart rendering ────────────────────────────────────────────────────────
const renderChart = async (chart) => {
  destroyChart();
  await nextTick();
  if (!chartCanvas.value) return;
  try {
    const ctx = chartCanvas.value.getContext('2d');
    if (!ctx) return;

    const datasets = Array.isArray(chart.datasets) && chart.datasets.length
      ? chart.datasets.map((ds, idx) => ({
          label: ds.label || `Series ${idx + 1}`,
          data: ds.data || [],
          backgroundColor: ds.backgroundColor || `rgba(${80 + idx * 40}, ${130 + idx * 20}, 246, 0.65)`,
          borderColor: ds.borderColor || `rgba(${37 + idx * 20}, ${99 + idx * 10}, 235, 1)`,
          borderWidth: 2, tension: 0.3, pointRadius: 4,
          borderRadius: chart.chart_type === 'bar' ? 8 : 0,
        }))
      : [{
          label: chart.title || 'Data',
          data: chart.data || [],
          backgroundColor: 'rgba(59, 130, 246, 0.65)',
          borderColor: 'rgba(37, 99, 235, 1)',
          borderWidth: 2, fill: chart.chart_type === 'bar',
          tension: 0.3, pointRadius: 4,
          pointBackgroundColor: 'rgba(37, 99, 235, 1)',
          borderRadius: chart.chart_type === 'bar' ? 8 : 0,
        }];

    const allowedTypes = new Set(['bar', 'line', 'pie', 'doughnut', 'radar']);
    const chartType = chart.chart_type === 'time-series' ? 'line'
      : allowedTypes.has(chart.chart_type) ? chart.chart_type : 'line';

    chartInstance = new Chart(ctx, {
      type: chartType,
      data: { labels: chart.labels || [], datasets },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: true, position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.2)' } },
          x: { grid: { display: false } },
        },
      },
    });
  } catch (err) {
    console.error('Chart render error:', err);
    error.value = 'Failed to render chart.';
  }
};

const destroyChart = () => {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
};

watch(isChartResponse, async (newVal) => {
  if (newVal && aiResponse.value) {
    chartKey.value += 1;
    await renderChart(aiResponse.value.chart);
  }
});
</script>

<style scoped>
.agent-page {
  background: linear-gradient(to bottom, #f8f9fa 0%, #ffffff 100%);
  min-height: 100vh;
}

.container-lg {
  max-width: 1000px;
  margin: 0 auto;
}

.input-group-lg .form-control,
.input-group-lg .btn {
  font-size: 1rem;
  padding: 0.75rem 1rem;
}

.card {
  border-radius: 0.5rem;
  transition: box-shadow 0.3s ease;
}
.card:hover {
  box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.1) !important;
}

.response-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.report-header {
  background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
}

.chart-wrapper {
  position: relative;
  height: 400px;
  margin-top: 1rem;
}
.chart-wrapper canvas { max-height: 100%; }

.text-response { font-size: 1.05rem; line-height: 1.6; }

.ai-answer {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.55;
}

.report-prompt-section {
  background: #f0f4ff;
  border-radius: 0.5rem;
  padding: 1rem 1.25rem;
}

.report-icon {
  flex-shrink: 0;
  padding-top: 0.25rem;
}

/* Markdown report rendering */
.report-content :deep(h1) { font-size: 1.5rem; color: #1a237e; margin-top: 1.5rem; }
.report-content :deep(h2) { font-size: 1.25rem; color: #283593; border-bottom: 2px solid #9fa8da; padding-bottom: 0.25rem; margin-top: 1.5rem; }
.report-content :deep(h3) { font-size: 1.1rem; color: #3949ab; margin-top: 1.25rem; }
.report-content :deep(h4) { font-size: 1rem; color: #3f51b5; }
.report-content :deep(table) { margin: 0.75rem 0; font-size: 0.9rem; }
.report-content :deep(th) { background: #3f51b5; color: white; }
.report-content :deep(tr:nth-child(even)) { background: #e8eaf6; }
.report-content :deep(ul) { padding-left: 1.5rem; }
.report-content :deep(li) { margin-bottom: 0.25rem; }
.report-content :deep(strong) { color: #1a1a2e; }
.report-content :deep(.md-report p) { margin-bottom: 0.5rem; }

.cursor-pointer { cursor: pointer; }
.cursor-pointer:hover { text-decoration: underline; }
details summary { list-style: none; }
details summary::-webkit-details-marker { display: none; }

@media (max-width: 768px) {
  .agent-page { padding: 1rem !important; }
  .chart-wrapper { height: 300px; }
  .input-group-lg .form-control,
  .input-group-lg .btn { font-size: 0.9rem; padding: 0.6rem 0.8rem; }
}
</style>