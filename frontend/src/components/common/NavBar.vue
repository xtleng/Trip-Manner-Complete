<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const username = computed(() => {
  if (userStore.userInfo) return userStore.userInfo.nickname || userStore.userInfo.username
  return 'User'
})

function handleCommand(command) {
  if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'history') {
    router.push('/history')
  } else if (command === 'admin') {
    router.push('/admin')
  } else if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}

function goHome() {
  router.push('/')
}

function isActive(name) {
  return route.name === name
}
</script>

<template>
  <div class="nav-bar">
    <div class="nav-left" @click="goHome">
      <el-icon :size="22" color="#409EFF"><Position /></el-icon>
      <span class="brand-text">TripManner</span>
    </div>

    <div class="nav-center">
      <span
        class="nav-link"
        :class="{ active: isActive('home') }"
        @click="router.push('/')"
      >
        <el-icon><HomeFilled /></el-icon>
        Home
      </span>
      <span
        class="nav-link"
        :class="{ active: isActive('history') }"
        @click="router.push('/history')"
      >
        <el-icon><Clock /></el-icon>
        History
      </span>
    </div>

    <div class="nav-right">
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-dropdown-trigger">
          <el-avatar :size="28" style="background-color: #409EFF;">
            {{ username.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username-text">{{ username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              Settings
            </el-dropdown-item>
            <el-dropdown-item command="history">
              <el-icon><Clock /></el-icon>
              History
            </el-dropdown-item>
            <el-dropdown-item command="admin" divided>
              <el-icon><Tools /></el-icon>
              Admin
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>
              Logout
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style scoped>
.nav-bar {
  height: var(--navbar-height, 56px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: relative;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.brand-text {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  letter-spacing: -0.3px;
}

.nav-center {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s;
  user-select: none;
}

.nav-link:hover {
  color: #409EFF;
  background-color: #ecf5ff;
}

.nav-link.active {
  color: #409EFF;
  font-weight: 600;
  background-color: #ecf5ff;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-dropdown-trigger:hover {
  background-color: #f5f7fa;
}

.username-text {
  font-size: 14px;
  color: #303133;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
