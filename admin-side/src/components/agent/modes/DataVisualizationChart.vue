<template>
  <div class="ap-chart-section">
    <div class="ap-chart-header">
      <span class="ap-chart-type-badge">{{ chartData.chart_type }}</span>
      <h3 class="ap-chart-title">{{ chartData.title }}</h3>
    </div>
    <div class="ap-chart-wrap">
      <canvas ref="canvasRef" width="900" height="420"></canvas>
    </div>
    <p v-if="chartData.description" class="ap-chart-desc">{{ chartData.description }}</p>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  chartData: { type: Object, required: true },
})

const canvasRef = ref(null)
let chartInstance = null

const canvasBackground = {
  id: 'dataVisualizationCanvasBackground',
  beforeDraw(chart) {
    const { ctx, width, height } = chart
    ctx.save()
    ctx.globalCompositeOperation = 'destination-over'
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.restore()
  },
}

function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
}

function chartDatasets(data, type) {
  const palette = ['#ef4444', '#2563eb', '#16a34a', '#f59e0b', '#7c3aed', '#0891b2']
  const source = Array.isArray(data.datasets) && data.datasets.length
    ? data.datasets
    : [{ label: data.title || 'Data', data: data.data || [] }]

  return source.map((ds, index) => {
    const color = ds.borderColor || palette[index % palette.length]
    return {
      ...ds,
      label: ds.label || `Series ${index + 1}`,
      data: ds.data || [],
      borderColor: color,
      backgroundColor: ds.backgroundColor || `${color}33`,
      borderWidth: ds.borderWidth || 2,
      tension: ds.tension ?? 0.3,
      pointRadius: ds.pointRadius ?? 4,
      pointHoverRadius: ds.pointHoverRadius ?? 6,
      pointBackgroundColor: ds.pointBackgroundColor || color,
      pointBorderColor: ds.pointBorderColor || '#ffffff',
      spanGaps: ds.spanGaps ?? true,
      fill: type === 'line' ? false : ds.fill,
      borderRadius: type === 'bar' ? 6 : ds.borderRadius,
    }
  })
}

async function renderChart() {
  destroyChart()
  await nextTick()
  await new Promise(resolve => requestAnimationFrame(resolve))
  if (!canvasRef.value) return

  const data = props.chartData
  const allowedTypes = new Set(['bar', 'line', 'pie', 'doughnut', 'radar', 'scatter'])
  const type = allowedTypes.has(data.chart_type) ? data.chart_type : 'line'
  const isCircular = ['pie', 'doughnut', 'radar'].includes(type)

  chartInstance = new Chart(canvasRef.value.getContext('2d'), {
    type,
    data: {
      labels: data.labels || [],
      datasets: chartDatasets(data, type),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: '#1f2937', font: { family: 'JetBrains Mono, monospace', size: 11 } },
        },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#111827',
          bodyColor: '#111827',
          borderColor: '#cbd5e1',
          borderWidth: 1,
        },
      },
      scales: isCircular ? {} : {
        y: {
          title: { display: Boolean(data.unit), text: data.unit || '', color: '#1f2937' },
          grid: { color: '#e5e7eb' },
          ticks: { color: '#1f2937', font: { family: 'JetBrains Mono, monospace', size: 11 } },
        },
        x: {
          grid: { color: '#f1f5f9' },
          ticks: { color: '#1f2937', font: { family: 'JetBrains Mono, monospace', size: 10 }, maxRotation: 45 },
        },
      },
    },
    plugins: [canvasBackground],
  })
}

watch(() => props.chartData, renderChart, { immediate: true, deep: true, flush: 'post' })
onBeforeUnmount(destroyChart)
</script>

<style scoped>
.ap-chart-section {
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.16);
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
  background: #dbeafe;
  border: 1px solid #bfdbfe;
  font-size: 0.65rem;
  color: #1d4ed8;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.ap-chart-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  color: #111827;
}

.ap-chart-wrap {
  position: relative;
  height: 360px;
}

.ap-chart-desc {
  font-size: 0.82rem;
  color: #475569;
  margin: 16px 0 0;
  text-align: center;
}
</style>
