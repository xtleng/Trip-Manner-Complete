<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { Location, Clock, Ticket } from '@element-plus/icons-vue'

const appStore = useAppStore()

const detailVisible = ref(false)
const selectedRecord = ref(null)

const mockRecords = ref([
  {
    id: 1,
    date: '2026-04-26',
    city: 'Tokyo',
    algorithm: 'EKD-Trip',
    isMock: true,
    pois: [
      { name: '浅草寺', duration: '1.5小时', description: '东京最古老的寺庙' },
      { name: '东京塔', duration: '1小时', description: '东京标志性建筑' },
      { name: '新宿御苑', duration: '2小时', description: '东京最大的公园之一' },
    ],
    summary: '东京经典一日游，涵盖历史文化、现代地标与自然风光。',
  },
  {
    id: 2,
    date: '2026-04-25',
    city: 'Los Angeles',
    algorithm: 'CrossTrip',
    isMock: true,
    pois: [
      { name: 'Hollywood Sign', duration: '1小时', description: '好莱坞标志' },
      { name: 'Santa Monica Pier', duration: '2小时', description: '圣莫尼卡码头' },
      { name: 'Griffith Observatory', duration: '1.5小时', description: '格里菲斯天文台' },
    ],
    summary: '洛杉矶经典景点跨城规划，囊括娱乐与自然体验。',
  },
  {
    id: 3,
    date: '2026-04-24',
    city: '北京',
    algorithm: 'DeepSeek-Agent',
    isMock: false,
    pois: [
      { name: '故宫博物院', duration: '3小时', description: '中国古代宫殿建筑群' },
      { name: '天坛', duration: '2小时', description: '明清皇帝祭天场所' },
      { name: '南锣鼓巷', duration: '1.5小时', description: '北京最古老的胡同之一' },
    ],
    summary: '北京文化深度游，探索历史古迹与胡同文化。',
  },
  {
    id: 4,
    date: '2026-04-23',
    city: 'Glasgow',
    algorithm: 'EKD-Trip',
    isMock: true,
    pois: [
      { name: 'Glasgow Cathedral', duration: '1小时', description: '中世纪大教堂' },
      { name: 'Kelvingrove Museum', duration: '2小时', description: '艺术与自然博物馆' },
    ],
    summary: '格拉斯哥文化之旅，感受苏格兰历史与艺术。',
  },
  {
    id: 5,
    date: '2026-04-22',
    city: 'San Francisco',
    algorithm: 'CrossTrip',
    isMock: true,
    pois: [
      { name: 'Golden Gate Bridge', duration: '1小时', description: '旧金山地标' },
      { name: "Fisherman's Wharf", duration: '2小时', description: '渔人码头' },
      { name: 'Alcatraz Island', duration: '2小时', description: '恶魔岛' },
    ],
    summary: '旧金山经典景点之旅，体验海湾城市魅力。',
  },
])

const isMockMode = computed(() => appStore.useMockData)

const records = computed(() => {
  if (isMockMode.value) {
    return mockRecords.value
  }
  return []
})

function getAlgorithmTagType(algorithm) {
  if (algorithm.includes('EKD')) return 'success'
  if (algorithm.includes('Cross') || algorithm.includes('LLMCPR')) return ''
  if (algorithm.includes('DeepSeek')) return 'warning'
  return 'info'
}

function handleRowClick(row) {
  selectedRecord.value = row
  detailVisible.value = true
}
</script>

<template>
  <div class="history-view">
    <div class="history-container">
      <h2 class="page-title">历史记录</h2>

      <el-card shadow="hover">
        <el-table
          v-if="records.length > 0"
          :data="records"
          stripe
          style="width: 100%"
          @row-click="handleRowClick"
          class="clickable-table"
        >
          <el-table-column prop="date" label="日期" width="140" />
          <el-table-column prop="city" label="城市" width="160" />
          <el-table-column prop="algorithm" label="算法" width="200">
            <template #default="{ row }">
              <el-tag :type="getAlgorithmTagType(row.algorithm)" size="small">
                {{ row.algorithm }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数据模式" width="120">
            <template #default="{ row }">
              <el-tag :type="row.isMock ? 'info' : 'success'" size="small" effect="plain">
                {{ row.isMock ? 'Mock' : 'Real' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="摘要">
            <template #default="{ row }">
              <span class="summary-text">{{ row.summary }}</span>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else description="暂无历史记录" />
      </el-card>

      <!-- Detail Dialog -->
      <el-dialog
        v-model="detailVisible"
        :title="selectedRecord ? `${selectedRecord.city} - 路线详情` : '路线详情'"
        width="600px"
        destroy-on-close
      >
        <template v-if="selectedRecord">
          <div class="detail-meta">
            <el-tag :type="getAlgorithmTagType(selectedRecord.algorithm)" size="small">
              {{ selectedRecord.algorithm }}
            </el-tag>
            <el-tag :type="selectedRecord.isMock ? 'info' : 'success'" size="small" effect="plain" style="margin-left: 8px;">
              {{ selectedRecord.isMock ? 'Mock' : 'Real' }}
            </el-tag>
            <span class="detail-date">{{ selectedRecord.date }}</span>
          </div>

          <p class="detail-summary">{{ selectedRecord.summary }}</p>

          <el-divider content-position="left">景点列表</el-divider>

          <div class="poi-list">
            <div
              v-for="(poi, index) in selectedRecord.pois"
              :key="index"
              class="poi-item"
            >
              <div class="poi-index">{{ index + 1 }}</div>
              <div class="poi-content">
                <div class="poi-name">{{ poi.name }}</div>
                <div class="poi-desc">{{ poi.description }}</div>
                <div class="poi-duration">
                  <el-icon><Clock /></el-icon>
                  {{ poi.duration }}
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.history-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: #f5f7fa;
}

.history-container {
  max-width: 1000px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 24px;
}

.clickable-table :deep(tbody tr) {
  cursor: pointer;
}

.summary-text {
  color: #606266;
  font-size: 13px;
}

.detail-meta {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.detail-date {
  margin-left: auto;
  color: #909399;
  font-size: 14px;
}

.detail-summary {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 8px;
}

.poi-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.poi-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.poi-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.poi-content {
  flex: 1;
}

.poi-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.poi-desc {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.poi-duration {
  font-size: 13px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
