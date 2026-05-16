<template>
  <div class="confidence-meter">
    <div class="meter-info">
      <span class="meter-label">AI Confidence</span>
      <span class="meter-value">{{ confidence }}% ({{ label }})</span>
    </div>
    <div class="meter-track">
      <div class="meter-fill" :style="{ width: confidence + '%' }" :class="colorClass"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps(['confidence'])

const label = computed(() => {
  const c = props.confidence
  if (c < 40) return 'unlikely'
  if (c < 60) return 'possible'
  if (c < 80) return 'likely'
  return 'very likely'
})

const colorClass = computed(() => {
  const c = props.confidence
  if (c < 40) return 'low'
  if (c < 60) return 'med'
  if (c < 80) return 'high'
  return 'very-high'
})
</script>

<style scoped>
.confidence-meter {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.meter-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #7a94b0;
  font-weight: 600;
}
.meter-value {
  font-family: 'JetBrains Mono', monospace;
  color: #e2ecf8;
}
.meter-track {
  height: 6px;
  background: rgba(0,0,0,0.3);
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid rgba(99,133,169,0.1);
}
.meter-fill {
  height: 100%;
  transition: width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.meter-fill.low { background: #ef4444; }
.meter-fill.med { background: #f59e0b; }
.meter-fill.high { background: #3b82f6; }
.meter-fill.very-high { background: #10b981; }
</style>
