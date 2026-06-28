<script setup>
import { RouterView, useRoute } from 'vue-router'
import NavBar from '@/components/common/NavBar.vue'
import { useUserStore } from '@/stores/user'
import { computed } from 'vue'

const userStore = useUserStore()
const route = useRoute()
const showNavBar = computed(() => userStore.isLoggedIn && !['login', 'register', 'onboarding'].includes(route.name))
</script>

<template>
  <div class="app-container">
    <NavBar v-if="showNavBar" />
    <main :class="{ 'with-navbar': showNavBar }">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

main {
  flex: 1;
  overflow: hidden;
}

main.with-navbar {
  height: calc(100vh - var(--navbar-height));
}
</style>
