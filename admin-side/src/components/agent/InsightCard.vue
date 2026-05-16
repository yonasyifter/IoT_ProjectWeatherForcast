<template>
  <div class="insight-card" :class="`type-${type}`">
    <div class="insight-card-header">
      <slot name="header"></slot>
    </div>
    <div class="insight-card-body">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.insight-card {
  background: rgba(20, 30, 48, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(99, 133, 169, 0.2);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fade-in-up 0.5s ease-out forwards;
}

.insight-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.insight-card-header {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-math { border-left: 4px solid #8b5cf6; }
.type-anomaly { border-left: 4px solid #ef4444; }
.type-gap { border-left: 4px solid #f59e0b; }
.type-text { border-left: 4px solid #3b82f6; }

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
