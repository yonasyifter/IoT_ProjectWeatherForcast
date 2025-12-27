// Updated App.vue with Help and Docs pages
<script setup>
import { ref } from 'vue'
import SensorDashboardPage from './pages/SensorDashboardPage.vue'
import GroupMembersPage from './pages/GroupMembersPage.vue'
import WeatherPage from './pages/WeatherPage.vue'
import HelpPage from './pages/HelpPage.vue'
import DocsPage from './pages/DocsPage.vue'
import Sidebar from './components/layout/SidebarNav.vue' // Adjust path as needed

const currentPage = ref('dashboard')

function navigateTo(page) {
  currentPage.value = page
}
</script>

<template>
  <div class="d-flex">
    <!-- Sidebar -->
    <Sidebar @navigate="navigateTo" />

    <!-- Main Content Area -->
    <div class="flex-grow-1">
      <!-- Top Navigation -->
      <nav class="navbar navbar-dark bg-dark border-bottom">
        <div class="container-fluid">
          <span class="navbar-brand mb-0 h5">
            <i class="bi bi-cloud-sun-fill me-2"></i>
            IOT-Smart Park
          </span>
          <div class="d-flex gap-2">
            <button 
              @click="navigateTo('dashboard')"
              :class="['btn btn-sm', currentPage === 'dashboard' ? 'btn-primary' : 'btn-outline-light']"
            >
              <i class="bi bi-speedometer2 me-1"></i>
              Dashboard
            </button>
            <button 
              @click="navigateTo('weather')"
              :class="['btn btn-sm', currentPage === 'weather' ? 'btn-primary' : 'btn-outline-light']"
            >
              <i class="bi bi-cloud-sun me-1"></i>
              Weather
            </button>
            <button 
              @click="navigateTo('help')"
              :class="['btn btn-sm', currentPage === 'help' ? 'btn-primary' : 'btn-outline-light']"
            >
              <i class="bi bi-question-circle me-1"></i>
              Help
            </button>
            <button 
              @click="navigateTo('docs')"
              :class="['btn btn-sm', currentPage === 'docs' ? 'btn-primary' : 'btn-outline-light']"
            >
              <i class="bi bi-book me-1"></i>
              Docs
            </button>
            <button 
              @click="navigateTo('members')"
              :class="['btn btn-sm', currentPage === 'members' ? 'btn-primary' : 'btn-outline-light']"
            >
              <i class="bi bi-people-fill me-1"></i>
              Team
            </button>            
          </div>
        </div>
      </nav>

      <!-- Page Content -->
      <SensorDashboardPage v-if="currentPage === 'dashboard'" />
      <WeatherPage v-if="currentPage === 'weather'" />
      <GroupMembersPage v-if="currentPage === 'members'" />
      <HelpPage v-if="currentPage === 'help'" />
      <DocsPage v-if="currentPage === 'docs'" />
    </div>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
}
</style>