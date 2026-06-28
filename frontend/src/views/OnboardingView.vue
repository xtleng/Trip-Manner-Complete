<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const saving = ref(false)
const currentStep = ref(0)

const form = reactive({
  interested_categories: [],
  travel_style: '',
  companion_type: '',
  budget_level: '',
})

const categoryOptions = [
  { label: '文化古迹', icon: '🏛️', value: '文化古迹' },
  { label: '自然风光', icon: '🏔️', value: '自然风光' },
  { label: '美食', icon: '🍜', value: '美食' },
  { label: '购物', icon: '🛍️', value: '购物' },
  { label: '娱乐', icon: '🎡', value: '娱乐' },
  { label: '博物馆', icon: '🖼️', value: '博物馆' },
  { label: '宗教场所', icon: '⛩️', value: '宗教场所' },
  { label: '公园', icon: '🌳', value: '公园' },
]

const styleOptions = [
  { label: '深度游', desc: '慢节奏，深入体验当地文化', value: '深度游' },
  { label: '打卡游', desc: '高效率，必去景点一个不落', value: '打卡游' },
  { label: '休闲游', desc: '随心所欲，享受度假时光', value: '休闲游' },
]

const companionOptions = [
  { label: '独自', desc: '一个人的自由旅行', value: '独自' },
  { label: '情侣', desc: '浪漫的二人世界', value: '情侣' },
  { label: '家庭', desc: '温馨的家庭出游', value: '家庭' },
  { label: '朋友', desc: '欢乐的好友之旅', value: '朋友' },
]

const budgetOptions = [
  { label: '经济', desc: '精打细算，高性价比', value: '经济' },
  { label: '舒适', desc: '适度消费，品质体验', value: '舒适' },
  { label: '高端', desc: '追求极致，不计预算', value: '高端' },
]

const steps = [
  { title: '兴趣偏好', desc: '选择你感兴趣的旅行类型' },
  { title: '出行风格', desc: '你更喜欢怎样的旅行节奏' },
  { title: '同行伙伴', desc: '通常和谁一起旅行' },
  { title: '预算偏好', desc: '你的旅行预算倾向' },
]

const canProceed = computed(() => {
  if (currentStep.value === 0) return form.interested_categories.length > 0
  if (currentStep.value === 1) return !!form.travel_style
  if (currentStep.value === 2) return !!form.companion_type
  if (currentStep.value === 3) return !!form.budget_level
  return false
})

function toggleCategory(value) {
  const idx = form.interested_categories.indexOf(value)
  if (idx >= 0) {
    form.interested_categories.splice(idx, 1)
  } else {
    form.interested_categories.push(value)
  }
}

function nextStep() {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

async function handleFinish() {
  saving.value = true
  try {
    await userStore.updatePreferences({
      interested_categories: form.interested_categories,
      travel_style: form.travel_style,
      companion_type: form.companion_type,
      budget_level: form.budget_level,
    })
    // Mark onboarding as complete
    if (userStore.userInfo) {
      userStore.userInfo.onboarded = true
      localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    }
    ElMessage.success('偏好设置完成！开始你的旅程吧')
    router.push('/')
  } catch (err) {
    // Even if API fails, mark onboarding as done so user can proceed
    if (userStore.userInfo) {
      userStore.userInfo.preferences = { ...form }
      userStore.userInfo.onboarded = true
      localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    }
    router.push('/')
  } finally {
    saving.value = false
  }
}

function handleSkip() {
  if (userStore.userInfo) {
    userStore.userInfo.onboarded = true
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
  }
  router.push('/')
}
</script>

<template>
  <div class="onboarding-view">
    <div class="onboarding-container">
      <!-- Header -->
      <div class="onboarding-header">
        <h1 class="brand">TripManner</h1>
        <p class="welcome-text">欢迎加入！让我们了解你的旅行偏好</p>
        <div class="step-indicator">
          <div
            v-for="(step, idx) in steps"
            :key="idx"
            class="step-dot"
            :class="{ active: idx === currentStep, done: idx < currentStep }"
          />
        </div>
      </div>

      <!-- Step Content -->
      <div class="step-content">
        <!-- Step 0: Categories -->
        <div v-if="currentStep === 0" class="step-panel">
          <h2 class="step-title">{{ steps[0].title }}</h2>
          <p class="step-desc">{{ steps[0].desc }}（可多选）</p>
          <div class="category-grid">
            <div
              v-for="cat in categoryOptions"
              :key="cat.value"
              class="category-card"
              :class="{ selected: form.interested_categories.includes(cat.value) }"
              @click="toggleCategory(cat.value)"
            >
              <span class="category-icon">{{ cat.icon }}</span>
              <span class="category-label">{{ cat.label }}</span>
            </div>
          </div>
        </div>

        <!-- Step 1: Travel Style -->
        <div v-if="currentStep === 1" class="step-panel">
          <h2 class="step-title">{{ steps[1].title }}</h2>
          <p class="step-desc">{{ steps[1].desc }}</p>
          <div class="option-list">
            <div
              v-for="opt in styleOptions"
              :key="opt.value"
              class="option-card"
              :class="{ selected: form.travel_style === opt.value }"
              @click="form.travel_style = opt.value"
            >
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </div>
        </div>

        <!-- Step 2: Companion -->
        <div v-if="currentStep === 2" class="step-panel">
          <h2 class="step-title">{{ steps[2].title }}</h2>
          <p class="step-desc">{{ steps[2].desc }}</p>
          <div class="option-list">
            <div
              v-for="opt in companionOptions"
              :key="opt.value"
              class="option-card"
              :class="{ selected: form.companion_type === opt.value }"
              @click="form.companion_type = opt.value"
            >
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </div>
        </div>

        <!-- Step 3: Budget -->
        <div v-if="currentStep === 3" class="step-panel">
          <h2 class="step-title">{{ steps[3].title }}</h2>
          <p class="step-desc">{{ steps[3].desc }}</p>
          <div class="option-list">
            <div
              v-for="opt in budgetOptions"
              :key="opt.value"
              class="option-card"
              :class="{ selected: form.budget_level === opt.value }"
              @click="form.budget_level = opt.value"
            >
              <span class="option-label">{{ opt.label }}</span>
              <span class="option-desc">{{ opt.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="onboarding-footer">
        <el-button v-if="currentStep > 0" @click="prevStep" size="large">
          上一步
        </el-button>
        <el-button v-else text @click="handleSkip" size="large" class="skip-btn">
          跳过
        </el-button>

        <el-button
          v-if="currentStep < steps.length - 1"
          type="primary"
          size="large"
          :disabled="!canProceed"
          @click="nextStep"
        >
          下一步
        </el-button>
        <el-button
          v-else
          type="primary"
          size="large"
          :disabled="!canProceed"
          :loading="saving"
          @click="handleFinish"
        >
          开始旅程
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.onboarding-view {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.onboarding-container {
  width: 100%;
  max-width: 560px;
  padding: 40px 36px 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.onboarding-header {
  text-align: center;
  margin-bottom: 32px;
}

.brand {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.welcome-text {
  font-size: 14px;
  color: #909399;
  margin-bottom: 20px;
}

.step-indicator {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.step-dot {
  width: 32px;
  height: 4px;
  border-radius: 2px;
  background-color: #dcdfe6;
  transition: all 0.3s;
}

.step-dot.active {
  background-color: #409EFF;
  width: 48px;
}

.step-dot.done {
  background-color: #67C23A;
}

.step-content {
  min-height: 300px;
}

.step-panel {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.step-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 24px;
}

/* Category Grid */
.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.category-card:hover {
  border-color: #c0c4cc;
  background-color: #f5f7fa;
}

.category-card.selected {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.category-icon {
  font-size: 28px;
}

.category-label {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

/* Option List */
.option-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 20px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.option-card:hover {
  border-color: #c0c4cc;
  background-color: #f5f7fa;
}

.option-card.selected {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.option-label {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.option-desc {
  font-size: 13px;
  color: #909399;
}

/* Footer */
.onboarding-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 32px;
}

.skip-btn {
  color: #909399;
}
</style>
