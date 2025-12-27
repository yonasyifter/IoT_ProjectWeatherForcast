<script setup>
import { ref } from 'vue'
import SensorDashboardPage from './pages/SensorDashboardPage.vue'
import GroupMembersPage from './pages/GroupMembersPage.vue'
import WeatherPage from './pages/WeatherPage.vue'

const currentPage = ref('dashboard')

function navigateTo(page) {
  currentPage.value = page
}
</script>

<template>
  <div>
    <!-- Navigation -->
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
  </div>
</template>