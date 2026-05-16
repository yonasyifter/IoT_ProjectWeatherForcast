<template>
  <div class="anomaly-block">
    <div class="anomaly-header">
      <span class="rag-badge" :class="statusClass">{{ statusLabel }}</span>
      <span class="anomaly-title">Anomaly Detected</span>
    </div>
    <div class="anomaly-content">
      {{ content }}
    </div>
    <div class="anomaly-action">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 16v-4M12 8v-4M11 4h2M11 20h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      <span>Suggested Action: Perform onsite verification of sensor calibration.</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['content'])

const statusClass = computed(() => {
  if (props.content.includes('CRITICAL')) return 'critical'
  if (props.content.includes('WARNING')) return 'warning'
  return 'info'
})

const statusLabel = computed(() => {
  if (statusClass.value === 'critical') return '🔴 CRITICAL'
  if (statusClass.value === 'warning') return '🟡 WARNING'
  return '🟢 INFO'
})
</script>

<style scoped>
.anomaly-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.anomaly-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rag-badge {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}
.rag-badge.critical { background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid #ef4444; }
.rag-badge.warning { background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid #f59e0b; }
.rag-badge.info { background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid #10b981; }

.anomaly-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}
.anomaly-content {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
.anomaly-action {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: #94a3b8;
  padding: 8px 12px;
  background: rgba(255,255,255,0.05);
  border-radius: 8px;
  border: 1px dashed rgba(99,133,169,0.3);
}
</style>
