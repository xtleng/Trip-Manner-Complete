<script setup>
import { computed } from 'vue'
import { ALGORITHM_TYPES } from '@/utils/constants'
import TravelModeViz from './TravelModeViz.vue'
import DistanceCurve from './DistanceCurve.vue'
import PreferenceRadar from './PreferenceRadar.vue'
import TransferFlow from './TransferFlow.vue'
import CityPreference from './CityPreference.vue'

const props = defineProps({
  algorithmType: {
    type: String,
    default: '',
  },
  intentData: {
    type: Object,
    default: null,
  },
  sourceCity: {
    type: String,
    default: '',
  },
  targetCity: {
    type: String,
    default: '',
  },
  collapsed: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle'])

const isEKDTrip = computed(
  () =>
    props.algorithmType === ALGORITHM_TYPES.EKD_TRIP &&
    props.intentData &&
    props.intentData.travel_mode
)

const isCrossCity = computed(
  () =>
    props.algorithmType === ALGORITHM_TYPES.CROSS_CITY &&
    props.intentData &&
    props.intentData.preference_factors
)

const isDeepSeek = computed(
  () =>
    props.algorithmType === ALGORITHM_TYPES.DEEPSEEK &&
    props.intentData &&
    props.intentData.agent_reasoning
)

const showPanel = computed(() => isEKDTrip.value || isCrossCity.value || isDeepSeek.value)

const panelTitle = computed(() => {
  if (isEKDTrip.value) return '用户出行意图分析'
  if (isCrossCity.value) return '跨城市偏好意图分析'
  if (isDeepSeek.value) return 'AI Agent 推理过程'
  return ''
})

// CrossCity: extract preference labels in order
const preferenceLabels = computed(() => {
  if (!isCrossCity.value || !props.intentData.preference_factors) return []
  const factors = props.intentData.preference_factors
  return Object.keys(factors)
    .sort()
    .map((k) => factors[k].label)
})

function handleToggle() {
  emit('toggle')
}
</script>

<template>
  <Transition name="intent-fade">
    <div v-if="showPanel" class="intent-panel" :class="{ collapsed: collapsed }">
      <div class="panel-header">
        <div class="panel-title">{{ panelTitle }}</div>
        <button class="toggle-btn" @click="handleToggle" :title="collapsed ? '展开' : '收起'">
          <span class="toggle-icon">{{ collapsed ? '▲' : '▼' }}</span>
          <span class="toggle-text">{{ collapsed ? '展开' : '收起' }}</span>
        </button>
      </div>

      <template v-if="!collapsed">
        <!-- EKD-Trip: TravelMode + DistanceCurve -->
        <div v-if="isEKDTrip" class="panel-body ekd-layout">
          <div class="viz-block mode-block">
            <TravelModeViz
              :mode="intentData.travel_mode"
              :confidence="intentData.travel_mode_confidence || 0"
            />
          </div>
          <div class="viz-block curve-block">
            <DistanceCurve
              :distance-data="intentData.distance_to_destination_curve || []"
              :travel-mode="intentData.travel_mode"
            />
          </div>
        </div>

        <!-- CrossCity: Radar + TransferFlow + CityPreference -->
        <div v-if="isCrossCity" class="panel-body cross-city-layout">
          <div class="viz-block">
            <PreferenceRadar
              :preference-factors="intentData.preference_factors"
              :city-group-preference="intentData.city_group_preference || {}"
            />
          </div>
          <div class="viz-block">
            <TransferFlow
              :source-city="sourceCity"
              :target-city="targetCity"
              :transfer-weights="intentData.transfer_weights || {}"
              :preference-labels="preferenceLabels"
            />
          </div>
          <div class="viz-block">
            <CityPreference
              :city-group-preference="intentData.city_group_preference || {}"
              :reliability-score="intentData.reliability_score || 0"
              :blend-weight-eta="intentData.blend_weight_eta || 0.5"
            />
          </div>
        </div>

        <!-- DeepSeek-Agent: Reasoning steps -->
        <div v-if="isDeepSeek" class="panel-body deepseek-layout">
          <div class="reasoning-block">
            <div class="reasoning-list">
              <div
                v-for="(step, idx) in intentData.agent_reasoning"
                :key="idx"
                class="reasoning-step"
              >
                <span class="step-number">{{ idx + 1 }}</span>
                <span class="step-text">{{ step }}</span>
              </div>
            </div>
          </div>
          <div class="stats-block">
            <div class="stat-item">
              <span class="stat-label">置信度</span>
              <span class="stat-value">{{ Math.round((intentData.confidence || 0) * 100) }}%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">路线类型</span>
              <span class="stat-value">{{ intentData.route_type || '-' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">预计游览</span>
              <span class="stat-value">{{ intentData.estimated_total_time_hours || '-' }}h</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">交通耗时</span>
              <span class="stat-value">{{ intentData.estimated_transport_time_min || '-' }}min</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </Transition>
</template>

<style scoped>
.intent-panel {
  height: var(--intent-panel-height, 220px);
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: height 0.3s ease;
}

.intent-panel.collapsed {
  height: 40px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid #f0f2f5;
  flex-shrink: 0;
}

.collapsed .panel-header {
  border-bottom: none;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #f5f7fa;
  cursor: pointer;
  font-size: 12px;
  color: #606266;
  transition: background 0.2s, border-color 0.2s;
}

.toggle-btn:hover {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

.toggle-icon {
  font-size: 10px;
}

.toggle-text {
  font-size: 12px;
}

.panel-body {
  flex: 1;
  min-height: 0;
  display: flex;
  padding: 8px 12px;
  gap: 12px;
}

.viz-block {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

/* EKD layout: mode panel is narrower */
.ekd-layout .mode-block {
  flex: 0 0 170px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ekd-layout .curve-block {
  flex: 1;
}

/* CrossCity layout: equal thirds */
.cross-city-layout .viz-block {
  flex: 1;
}

/* DeepSeek layout */
.deepseek-layout {
  flex-direction: row;
}

.reasoning-block {
  flex: 2;
  overflow-y: auto;
}

.reasoning-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reasoning-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.step-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #409EFF;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-text {
  font-size: 12px;
  color: #303133;
  line-height: 1.5;
}

.stats-block {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 6px 16px;
  border-left: 1px solid #ebeef5;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

/* Fade-in transition */
.intent-fade-enter-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.intent-fade-leave-active {
  transition: opacity 0.25s ease;
}

.intent-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.intent-fade-leave-to {
  opacity: 0;
}
</style>
