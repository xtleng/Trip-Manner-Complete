<script setup>
import { computed } from 'vue'

const props = defineProps({
  sourceCity: {
    type: String,
    default: 'Source',
  },
  targetCity: {
    type: String,
    default: 'Target',
  },
  transferWeights: {
    type: Object,
    default: () => ({}),
  },
  preferenceLabels: {
    type: Array,
    default: () => ['文化探索', '自然风光', '美食体验', '休闲购物'],
  },
})

const arrowColors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C']

const alphaKeys = ['factor_1_alpha', 'factor_2_alpha', 'factor_3_alpha', 'factor_4_alpha']

const flows = computed(() => {
  const maxAlpha = Math.max(
    ...alphaKeys.map((k) => props.transferWeights[k] || 0)
  )
  return alphaKeys.map((key, i) => {
    const alpha = props.transferWeights[key] || 0
    const isStrongest = alpha === maxAlpha && alpha > 0
    return {
      label: props.preferenceLabels[i] || `Factor ${i + 1}`,
      alpha,
      alphaDisplay: alpha.toFixed(2),
      color: arrowColors[i],
      // Arrow height proportional to weight, min 3px, max 14px
      arrowHeight: Math.max(3, Math.round(alpha * 32)),
      isStrongest,
    }
  })
})
</script>

<template>
  <div class="transfer-flow">
    <div class="flow-header">
      <div class="city-label source-city">{{ sourceCity }}</div>
      <div class="arrow-header-label">偏好迁移</div>
      <div class="city-label target-city">{{ targetCity }}</div>
    </div>

    <div class="flow-body">
      <div v-for="(flow, idx) in flows" :key="idx" class="flow-row">
        <div class="factor-label left-label">{{ flow.label }}</div>
        <div class="arrow-area">
          <svg
            class="arrow-svg"
            :viewBox="`0 0 200 ${flow.arrowHeight + 8}`"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient :id="`arrow-grad-${idx}`" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" :stop-color="flow.color" stop-opacity="0.8" />
                <stop offset="100%" :stop-color="flow.color" stop-opacity="0.4" />
              </linearGradient>
              <marker
                :id="`arrowhead-${idx}`"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <polygon
                  points="0 0, 8 4, 0 8"
                  :fill="flow.color"
                  fill-opacity="0.7"
                />
              </marker>
            </defs>
            <rect
              x="0"
              :y="4"
              width="180"
              :height="flow.arrowHeight"
              rx="2"
              :fill="`url(#arrow-grad-${idx})`"
              :class="{ strongest: flow.isStrongest }"
            />
            <line
              x1="175"
              :y1="4 + flow.arrowHeight / 2"
              x2="195"
              :y2="4 + flow.arrowHeight / 2"
              :stroke="flow.color"
              stroke-width="2"
              :marker-end="`url(#arrowhead-${idx})`"
            />
          </svg>
          <div class="alpha-label" :style="{ color: flow.color }">
            &alpha;={{ flow.alphaDisplay }}
          </div>
        </div>
        <div class="factor-label right-label">{{ flow.label }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.transfer-flow {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 4px;
}

.flow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.city-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  min-width: 70px;
}

.source-city {
  text-align: left;
}

.target-city {
  text-align: right;
}

.arrow-header-label {
  font-size: 11px;
  color: #909399;
  text-align: center;
  flex: 1;
}

.flow-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.flow-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.factor-label {
  font-size: 11px;
  color: #606266;
  min-width: 58px;
  flex-shrink: 0;
}

.left-label {
  text-align: right;
}

.right-label {
  text-align: left;
}

.arrow-area {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.arrow-svg {
  width: 100%;
  height: auto;
  max-height: 24px;
}

.alpha-label {
  font-size: 10px;
  font-weight: 600;
  margin-top: -2px;
}

.strongest {
  filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.15));
}
</style>
