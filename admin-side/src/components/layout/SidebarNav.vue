<script setup>
import { defineEmits } from 'vue'
import { useI18n } from 'vue-i18n'
const emit = defineEmits(['navigate'])
const { t } = useI18n()

const items = [
  { key: 'grid',      title: t('sidebar.sensor_dashboard') },
  { key: 'weather',        title: t('sidebar.weather_map') },
  { key: 'rcms-dashboard', title: t('sidebar.rcms_dashboard') },
  { key: 'rcms-alerts',    title: t('sidebar.rcms_alerts') },
  { key: 'rcms-gps',       title: t('sidebar.rcms_gps') },
  { key: 'rcms-devices',   title: t('sidebar.rcms_devices') },
  { key: 'chart',          title: t('sidebar.sensor_analytics') },
  { key: 'agent',          title: t('sidebar.ai_agent') },
]
</script>

<template>
  <aside
    class="d-flex flex-column align-items-center border-end"
    style="width:72px; background: linear-gradient(180deg, #052a45 0%, #061f33 100%); border-color: rgba(255,255,255,.06) !important;"
  >
    <!-- Logo -->
    <div class="py-3">
      <div class="rounded-3 d-flex align-items-center justify-content-center"
           style="width:44px;height:44px;background:rgba(255,255,255,.06);">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
          <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" stroke="white" opacity=".9"/>
          <path d="M12 2v20" stroke="white" opacity=".35"/>
          <path d="M3 7l9 5 9-5" stroke="white" opacity=".35"/>
        </svg>
      </div>
    </div>

    <div class="d-flex flex-column gap-2 align-items-center mt-1 overflow-auto" style="flex:1">
      <button
        v-for="it in items"
        :key="it.key"
        @click="emit('navigate', it.key)"
        class="btn btn-outline-light p-0 d-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
        style="width:44px;height:44px; border-color: rgba(255,255,255,.10);"
        :title="it.title"
      >
        <!-- Sensor Dashboard -->
        <svg v-if="it.key==='dashboard'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="white" stroke-width="1.8"/>
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="white" stroke-width="1.8"/>
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="white" stroke-width="1.8"/>
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="white" stroke-width="1.8"/>
        </svg>

        <!-- Weather -->
        <svg v-else-if="it.key==='weather'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v2M4.93 4.93l1.41 1.41M2 12h2M4.93 19.07l1.41-1.41M12 20v2M19.07 19.07l-1.41-1.41M22 12h-2M19.07 4.93l-1.41 1.41" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
          <circle cx="12" cy="12" r="4" stroke="white" stroke-width="1.8"/>
        </svg>

        <!-- RCMS Dashboard (router icon) -->
        <svg v-else-if="it.key==='rcms-dashboard'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <rect x="2" y="8" width="20" height="8" rx="2" stroke="#fbbf24" stroke-width="1.8"/>
          <circle cx="6" cy="12" r="1.2" fill="#fbbf24"/>
          <circle cx="10" cy="12" r="1.2" fill="#fbbf24"/>
          <path d="M14 12h4" stroke="#fbbf24" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M12 8V5M8 8V6M16 8V6" stroke="#fbbf24" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Alerts (bell) -->
        <svg v-else-if="it.key==='rcms-alerts'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 2a7 7 0 0 0-7 7v3l-2 3h18l-2-3V9a7 7 0 0 0-7-7Z" stroke="#f87171" stroke-width="1.8"/>
          <path d="M10 19a2 2 0 0 0 4 0" stroke="#f87171" stroke-width="1.8"/>
        </svg>

        <!-- GPS (location pin) -->
        <svg v-else-if="it.key==='rcms-gps'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 2C8.686 2 6 4.686 6 8c0 4.5 6 13 6 13s6-8.5 6-13c0-3.314-2.686-6-6-6Z" stroke="#34d399" stroke-width="1.8"/>
          <circle cx="12" cy="8" r="2" stroke="#34d399" stroke-width="1.8"/>
        </svg>

        <!-- Devices (hdd) -->
        <svg v-else-if="it.key==='rcms-devices'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <rect x="2" y="6" width="20" height="12" rx="2" stroke="#a78bfa" stroke-width="1.8"/>
          <circle cx="7" cy="12" r="1.5" fill="#a78bfa"/>
          <path d="M11 12h7" stroke="#a78bfa" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Chart -->
        <svg v-else-if="it.key==='chart'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M4 19V5" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M7 16l4-4 4 3 5-7" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>

        <!-- AI Agent -->
        <svg v-else-if="it.key==='agent'" width="20" height="20" viewBox="0 0 24 24" fill="none">
          <rect x="4" y="6" width="16" height="12" rx="3" stroke="white" stroke-width="1.8"/>
          <circle cx="9" cy="12" r="1.5" fill="white"/>
          <circle cx="15" cy="12" r="1.5" fill="white"/>
          <path d="M9 6V4M15 6V4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- Bottom buttons -->
    <div class="pb-3 d-flex flex-column gap-2 align-items-center">
      <button
        @click="emit('navigate', 'help')"
        class="btn btn-outline-light rounded-3 p-0"
        style="width:34px;height:34px;border-color: rgba(255,255,255,.12);"
        :title="$t('sidebar.help')"
      >?</button>
      <button
        @click="emit('navigate', 'docs')"
        class="btn btn-outline-light rounded-3 p-0"
        style="width:34px;height:34px;border-color: rgba(255,255,255,.12);"
        :title="$t('sidebar.docs')"
      >⟂</button>
    </div>
  </aside>
</template>
