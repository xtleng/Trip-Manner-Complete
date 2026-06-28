<script setup>
import { computed } from 'vue'
import { TRAVEL_MODES } from '@/utils/constants'

const props = defineProps({
  mode: {
    type: String,
    default: 'approaching',
  },
  confidence: {
    type: Number,
    default: 0,
  },
})

const modeInfo = computed(() => {
  return TRAVEL_MODES[props.mode] || TRAVEL_MODES.irregular
})

const confidencePercent = computed(() => {
  return Math.round(props.confidence * 100)
})

const bgColorLight = computed(() => {
  const color = modeInfo.value.color
  return color + '18'
})

const borderColor = computed(() => {
  return modeInfo.value.color + '40'
})

// SVG circle progress variables
const radius = 20
const circumference = 2 * Math.PI * radius
const strokeOffset = computed(() => {
  return circumference * (1 - props.confidence)
})
</script>

<template>
  <div
    class="travel-mode-viz"
    :style="{
      backgroundColor: bgColorLight,
      borderColor: borderColor,
    }"
  >
    <div class="mode-header">
      <div class="mode-icon" :style="{ color: modeInfo.color }">
        {{ modeInfo.icon }}
      </div>
      <div class="mode-labels">
        <div class="mode-label-zh">{{ modeInfo.label }}</div>
        <div class="mode-label-en">{{ modeInfo.labelEn }}</div>
      </div>
    </div>

    <div class="confidence-section">
      <svg class="confidence-ring" width="56" height="56" viewBox="0 0 56 56">
        <circle
          cx="28"
          cy="28"
          :r="radius"
          fill="none"
          stroke="#e4e7ed"
          stroke-width="4"
        />
        <circle
          cx="28"
          cy="28"
          :r="radius"
          fill="none"
          :stroke="modeInfo.color"
          stroke-width="4"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="strokeOffset"
          transform="rotate(-90 28 28)"
          class="confidence-progress"
        />
        <text
          x="28"
          y="28"
          text-anchor="middle"
          dominant-baseline="central"
          :fill="modeInfo.color"
          font-size="11"
          font-weight="600"
        >
          {{ confidencePercent }}%
        </text>
      </svg>
      <div class="confidence-label">置信度</div>
    </div>

    <div class="mode-description">
      {{ modeInfo.description }}
    </div>
  </div>
</template>

<style scoped>
.travel-mode-viz {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid;
  min-width: 160px;
  gap: 12px;
}

.mode-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.mode-icon {
  font-size: 36px;
  line-height: 1;
}

.mode-labels {
  text-align: center;
}

.mode-label-zh {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.mode-label-en {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.confidence-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.confidence-ring {
  display: block;
}

.confidence-progress {
  transition: stroke-dashoffset 0.6s ease;
}

.confidence-label {
  font-size: 11px;
  color: #909399;
}

.mode-description {
  font-size: 12px;
  color: #606266;
  text-align: center;
  line-height: 1.5;
  padding: 0 4px;
}
</style>
