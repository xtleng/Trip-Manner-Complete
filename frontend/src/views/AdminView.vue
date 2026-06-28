<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { Monitor, MapLocation, Setting } from '@element-plus/icons-vue'

const appStore = useAppStore()

const isMockMode = computed({
  get: () => appStore.useMockData,
  set: (val) => appStore.setUseMockData(val),
})

const ekdTripCities = ['Glasgow', 'Osaka', 'Toronto', 'Tokyo']
const crossCityCities = ['New York', 'Los Angeles', 'San Francisco']
</script>

<template>
  <div class="admin-view">
    <div class="admin-container">
      <h2 class="page-title">系统管理</h2>

      <div class="cards-grid">
        <!-- Card 1: Mock/Real Mode -->
        <el-card class="admin-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><Monitor /></el-icon>
              <span>数据模式</span>
            </div>
          </template>

          <div class="mode-switch-row">
            <el-switch
              v-model="isMockMode"
              size="large"
              active-text="Mock"
              inactive-text="Real"
              inline-prompt
              style="--el-switch-on-color: #e6a23c; --el-switch-off-color: #67c23a;"
            />
            <span class="mode-status">
              当前模式：{{ isMockMode ? 'Mock数据' : '真实算法' }}
            </span>
          </div>

          <p class="mode-desc">
            <template v-if="isMockMode">
              Mock 模式使用预置的模拟数据，无需连接后端算法服务。适用于前端开发与演示。
            </template>
            <template v-else>
              Real 模式将连接后端真实算法服务（EKD-Trip / CrossTrip / DeepSeek-Agent），需要确保后端服务正常运行。
            </template>
          </p>
        </el-card>

        <!-- Card 2: Supported Cities -->
        <el-card class="admin-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><MapLocation /></el-icon>
              <span>支持城市</span>
            </div>
          </template>

          <div class="cities-columns">
            <div class="city-column">
              <h4 class="city-column-title">EKD-Trip 单城市</h4>
              <div class="city-tags">
                <el-tag
                  v-for="city in ekdTripCities"
                  :key="city"
                  type="success"
                  effect="plain"
                  size="default"
                >
                  {{ city }}
                </el-tag>
              </div>
            </div>

            <el-divider direction="vertical" class="column-divider" />

            <div class="city-column">
              <h4 class="city-column-title">CrossTrip 跨城市</h4>
              <div class="city-tags">
                <el-tag
                  v-for="city in crossCityCities"
                  :key="city"
                  effect="plain"
                  size="default"
                >
                  {{ city }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>

        <!-- Card 3: System Status -->
        <el-card class="admin-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><Setting /></el-icon>
              <span>系统状态</span>
            </div>
          </template>

          <div class="status-list">
            <div class="status-item">
              <span class="status-label">Backend URL</span>
              <span class="status-value">
                <el-link type="primary" :underline="false">http://localhost:8000</el-link>
              </span>
            </div>

            <el-divider style="margin: 12px 0;" />

            <div class="status-item">
              <span class="status-label">API Key 状态</span>
              <span class="status-value">
                <el-tag :type="isMockMode ? 'info' : 'success'" size="small">
                  {{ isMockMode ? '未配置（Mock模式）' : '已配置' }}
                </el-tag>
              </span>
            </div>

            <el-divider style="margin: 12px 0;" />

            <div class="status-item">
              <span class="status-label">数据库</span>
              <span class="status-value">SQLite (开发模式)</span>
            </div>

            <el-divider style="margin: 12px 0;" />

            <div class="status-item">
              <span class="status-label">版本</span>
              <span class="status-value">
                <el-tag type="info" size="small" effect="plain">v1.0.0</el-tag>
              </span>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: #f5f7fa;
}

.admin-container {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 24px;
}

.cards-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.admin-card {
  /* intentionally blank, card styling comes from el-card */
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.mode-switch-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.mode-status {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.mode-desc {
  font-size: 14px;
  color: #909399;
  line-height: 1.6;
}

.cities-columns {
  display: flex;
  gap: 24px;
}

.column-divider {
  height: auto;
}

.city-column {
  flex: 1;
}

.city-column-title {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 12px;
}

.city-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-list {
  /* container for status items */
}

.status-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-label {
  font-size: 14px;
  color: #606266;
}

.status-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
</style>
