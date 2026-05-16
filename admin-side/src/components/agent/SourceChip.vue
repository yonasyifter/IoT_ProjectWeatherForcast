<template>
  <span class="source-chip">
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" stroke-width="2"/></svg>
    {{ source }}
  </span>
</template>

<script setup>
defineProps(['source'])
</script>

<style scoped>
.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  font-size: 0.65rem;
  color: #60a5fa;
  font-family: 'JetBrains Mono', monospace;
  cursor: help;
  transition: all 0.2s;
}
.source-chip:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: #3b82f6;
  transform: scale(1.05);
}
</style>
