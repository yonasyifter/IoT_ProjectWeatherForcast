<script setup>
import { ref, onMounted } from 'vue'
import { useAdminAuthStore } from '@/auth/adminAuthStore'

// Existing pages
import SensorDashboardPage from './pages/SensorDashboardPage.vue'
import GroupMembersPage    from './pages/GroupMembersPage.vue'
import WeatherPage         from './pages/WeatherPage.vue'
import HelpPage            from './pages/HelpPage.vue'
import DocsPage            from './pages/DocsPage.vue'
import ChartPage           from './components/SideNavEffect/ChartPage.vue'
import GearPage            from './components/SideNavEffect/GearPage.vue'
import GridPage            from './components/SideNavEffect/GridPage.vue'
import UploadPage          from './components/SideNavEffect/UploadPage.vue'
import AgentPage           from './pages/AgentPage.vue'
import ChatbotAssistant    from './components/ChatbotAssistant.vue'
import Sidebar             from './components/layout/SidebarNav.vue'

// NEW RCMS pages
import RcmsDashboardPage   from './pages/RcmsDashboardPage.vue'
import RcmsAlertsPage      from './pages/RcmsAlertsPage.vue'
import RcmsGpsPage         from './pages/RcmsGpsPage.vue'
import RcmsDevicesPage     from './pages/RcmsDevicesPage.vue'

// Auth view
import AdminLoginView from './views/AdminLoginView.vue'

const store       = useAdminAuthStore()
const currentPage = ref('dashboard')

onMounted(async () => { await store.init() })

function navigateTo(page) { currentPage.value = page }

async function handleLogout() { await store.logout() }
</script>

<template>
  <!-- Loading splash while Firebase resolves -->
  <div v-if="store.loading" class="auth-loading">
    <div class="spinner-border text-light" role="status"></div>
    <p class="mt-3 text-secondary">Connecting to Smart Park...</p>
  </div>

  <!-- Not authenticated → show login -->
  <AdminLoginView
    v-else-if="!store.isLoggedIn"
    @login-success="currentPage = 'dashboard'"
  />

  <!-- Authenticated admin → show dashboard -->
  <div v-else class="d-flex" style="min-height:100vh">
    <Sidebar @navigate="navigateTo" />

    <div class="flex-grow-1">
      <!-- Top nav -->
      <nav class="navbar navbar-dark bg-dark border-bottom">
        <div class="container-fluid">
          <span class="navbar-brand mb-1 h4">
            <i class="bi bi-cloud-sun-fill me-2"></i>IOT-Smart Park
          </span>

          <div class="d-flex gap-2 align-items-center flex-wrap">
            <button @click="navigateTo('dashboard')"
              :class="['btn btn-sm', currentPage==='dashboard' ? 'btn-primary' : 'btn-outline-light']">
              <i class="bi bi-speedometer2 me-1"></i>{{ $t('common.dashboard') }}
            </button>
            <button @click="navigateTo('weather')"
              :class="['btn btn-sm', currentPage==='weather' ? 'btn-primary' : 'btn-outline-light']">
              <i class="bi bi-cloud-sun me-1"></i>{{ $t('sidebar.weather_map') }}
            </button>

            <!-- RCMS dropdown group -->
            <div class="btn-group">
              <button
                :class="['btn btn-sm', ['rcms-dashboard','rcms-alerts','rcms-gps','rcms-devices'].includes(currentPage) ? 'btn-warning' : 'btn-outline-warning']"
                @click="navigateTo('rcms-dashboard')">
                <i class="bi bi-router me-1"></i>RCMS
              </button>
              <button type="button"
                :class="['btn btn-sm dropdown-toggle dropdown-toggle-split', ['rcms-dashboard','rcms-alerts','rcms-gps','rcms-devices'].includes(currentPage) ? 'btn-warning' : 'btn-outline-warning']"
                data-bs-toggle="dropdown">
                <span class="visually-hidden">Toggle Dropdown</span>
              </button>
              <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end">
                <li><button class="dropdown-item" @click="navigateTo('rcms-dashboard')">
                  <i class="bi bi-speedometer2 me-2"></i>Device Dashboard</button></li>
                <li><button class="dropdown-item" @click="navigateTo('rcms-alerts')">
                  <i class="bi bi-bell me-2"></i>Alerts & Alarms</button></li>
                <li><button class="dropdown-item" @click="navigateTo('rcms-gps')">
                  <i class="bi bi-geo-alt me-2"></i>GPS Tracking</button></li>
                <li><button class="dropdown-item" @click="navigateTo('rcms-devices')">
                  <i class="bi bi-hdd-network me-2"></i>Device Management</button></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item" href="https://rcms-cloud.robustel.net/rcms/index" target="_blank">
                  <i class="bi bi-box-arrow-up-right me-2"></i>Open RCMS Portal</a></li>
              </ul>
            </div>

            <button @click="navigateTo('agent')"
              :class="['btn btn-sm', currentPage==='agent' ? 'btn-primary' : 'btn-outline-light']">
              <i class="bi bi-robot me-1"></i>{{ $t('sidebar.ai_agent') }}
            </button>

            <!-- Admin badge + logout -->
            <div style="width:1px;height:24px;background:rgba(255,255,255,0.15);margin:0 4px"></div>
            <span class="badge bg-success d-none d-md-inline-flex align-items-center gap-1">
              <i class="bi bi-shield-check"></i> {{ store.displayName }}
            </span>
            <button class="btn btn-sm btn-outline-danger" @click="handleLogout">
              <i class="bi bi-box-arrow-right me-1"></i>{{ $t('common.logout') }}
            </button>
          </div>
        </div>
      </nav>

      <!-- Page content -->
      <SensorDashboardPage v-if="currentPage === 'dashboard'" />
      <WeatherPage         v-else-if="currentPage === 'weather'" />
      <GroupMembersPage    v-else-if="currentPage === 'members'" />
      <HelpPage            v-else-if="currentPage === 'help'" />
      <DocsPage            v-else-if="currentPage === 'docs'" />
      <ChartPage           v-else-if="currentPage === 'chart'" />
      <GearPage            v-else-if="currentPage === 'gear'" />
      <GridPage            v-else-if="currentPage === 'grid'" />
      <UploadPage          v-else-if="currentPage === 'upload'" />
      <AgentPage           v-else-if="currentPage === 'agent'" />

      <!-- RCMS pages -->
      <RcmsDashboardPage   v-else-if="currentPage === 'rcms-dashboard'" />
      <RcmsAlertsPage      v-else-if="currentPage === 'rcms-alerts'" />
      <RcmsGpsPage         v-else-if="currentPage === 'rcms-gps'" />
      <RcmsDevicesPage     v-else-if="currentPage === 'rcms-devices'" />
    </div>

    <ChatbotAssistant />
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}
.auth-loading {
  min-height: 100vh;
  background: linear-gradient(135deg, #020d18 0%, #052a45 50%, #061f33 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
</style>
