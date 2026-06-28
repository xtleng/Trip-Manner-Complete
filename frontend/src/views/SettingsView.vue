<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const appStore = useAppStore()

const saving = ref(false)

const categoryOptions = [
  '文化古迹',
  '自然风光',
  '美食',
  '购物',
  '娱乐',
  '博物馆',
  '宗教场所',
  '公园',
]

const form = reactive({
  nickname: '',
  interested_categories: [],
  travel_style: '',
  companion_type: '',
  budget_level: '',
})

const username = computed(() => userStore.userInfo?.username || '用户')
const avatarLetter = computed(() => (username.value || 'U').charAt(0).toUpperCase())

onMounted(() => {
  const prefs = userStore.userInfo?.preferences
  if (prefs) {
    form.interested_categories = prefs.interested_categories || []
    form.travel_style = prefs.travel_style || ''
    form.companion_type = prefs.companion_type || ''
    form.budget_level = prefs.budget_level || ''
  }
  form.nickname = userStore.userInfo?.nickname || userStore.userInfo?.username || ''
})

async function handleSave() {
  saving.value = true
  try {
    await userStore.updatePreferences({
      interested_categories: form.interested_categories,
      travel_style: form.travel_style,
      companion_type: form.companion_type,
      budget_level: form.budget_level,
    })
    ElMessage.success('偏好设置已保存')
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || err?.message || '保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="settings-view">
    <div class="settings-container">
      <h2 class="page-title">个人设置</h2>

      <!-- Profile Section -->
      <el-card class="settings-section" shadow="hover">
        <template #header>
          <span class="section-title">个人信息</span>
        </template>
        <div class="profile-row">
          <div class="avatar-placeholder">
            {{ avatarLetter }}
          </div>
          <div class="profile-info">
            <el-form label-width="80px">
              <el-form-item label="昵称">
                <el-input v-model="form.nickname" placeholder="输入昵称" style="max-width: 300px;" />
              </el-form-item>
            </el-form>
          </div>
        </div>
      </el-card>

      <!-- Travel Preferences Section -->
      <el-card class="settings-section" shadow="hover">
        <template #header>
          <span class="section-title">旅行偏好</span>
        </template>
        <el-form label-width="100px" label-position="top">
          <el-form-item label="兴趣类别">
            <el-checkbox-group v-model="form.interested_categories">
              <el-checkbox
                v-for="cat in categoryOptions"
                :key="cat"
                :label="cat"
                :value="cat"
              >
                {{ cat }}
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="出行风格">
            <el-radio-group v-model="form.travel_style">
              <el-radio value="深度游">深度游</el-radio>
              <el-radio value="打卡游">打卡游</el-radio>
              <el-radio value="休闲游">休闲游</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="同行人">
            <el-radio-group v-model="form.companion_type">
              <el-radio value="独自">独自</el-radio>
              <el-radio value="情侣">情侣</el-radio>
              <el-radio value="家庭">家庭</el-radio>
              <el-radio value="朋友">朋友</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="预算级别">
            <el-radio-group v-model="form.budget_level">
              <el-radio value="经济">经济</el-radio>
              <el-radio value="舒适">舒适</el-radio>
              <el-radio value="高端">高端</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="saving" @click="handleSave">
              保存偏好
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Developer Section -->
      <el-card class="settings-section" shadow="hover">
        <template #header>
          <span class="section-title">开发者选项</span>
        </template>
        <el-form label-width="100px" label-position="top">
          <el-form-item label="数据模式">
            <div class="mode-switch-row">
              <el-switch
                :model-value="appStore.useMockData"
                @change="(val) => appStore.setUseMockData(val)"
                size="large"
                active-text="Mock"
                inactive-text="Real"
                inline-prompt
                style="--el-switch-on-color: #e6a23c; --el-switch-off-color: #67c23a;"
              />
              <span class="mode-status">
                {{ appStore.useMockData ? 'Mock 数据' : '真实算法' }}
              </span>
            </div>
            <p class="mode-desc">
              Mock 模式使用预置模拟数据，无需连接后端。切换为 Real 模式需确保后端服务运行。
            </p>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: #f5f7fa;
}

.settings-container {
  max-width: 800px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 24px;
}

.settings-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.profile-row {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar-placeholder {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
}

.mode-switch-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.mode-status {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.mode-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
  margin: 0;
}
</style>
