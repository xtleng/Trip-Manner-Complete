<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  cityGroupPreference: {
    type: Object,
    default: () => ({}),
  },
  reliabilityScore: {
    type: Number,
    default: 0,
  },
  blendWeightEta: {
    type: Number,
    default: 0.5,
  },
})

const chartRef = ref(null)
let chart = null

const reliabilityPercent = computed(() =>
  Math.round(props.reliabilityScore * 100)
)

const etaPercent = computed(() =>
  Math.round(props.blendWeightEta * 100)
)

const groupPercent = computed(() => 100 - etaPercent.value)

const blendDescription = computed(() =>
  `路线中${etaPercent.value}%基于您的个人偏好，${groupPercent.value}%参考了当地热门趋势`
)

const categoryMap = {
  cultural: { label: '文化', color: '#409EFF' },
  nature: { label: '自然', color: '#67C23A' },
  food: { label: '美食', color: '#E6A23C' },
  shopping: { label: '购物', color: '#F56C6C' },
}

function buildOption() {
  const pref = props.cityGroupPreference
  const data = Object.entries(categoryMap).map(([key, cfg]) => ({
    name: cfg.label,
    value: pref[key] || 0,
    itemStyle: { color: cfg.color },
  }))

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: { color: '#303133', fontSize: 12 },
      formatter: '{b}: {d}%',
    },
    series: [
      {
        type: 'pie',
        radius: ['42%', '68%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          fontSize: 11,
          color: '#606266',
          formatter: '{b}\n{d}%',
        },
        labelLine: {
          length: 8,
          length2: 6,
          lineStyle: { color: '#c0c4cc' },
        },
        emphasis: {
          scaleSize: 6,
          label: { fontWeight: 'bold' },
        },
        data,
      },
    ],
    graphic: [
      {
        type: 'group',
        left: 'center',
        top: 'middle',
        children: [
          {
            type: 'text',
            style: {
              text: `${reliabilityPercent.value}%`,
              fontSize: 18,
              fontWeight: 'bold',
              fill: '#303133',
              textAlign: 'center',
            },
            left: 'center',
            top: -8,
          },
          {
            type: 'text',
            style: {
              text: '可靠性',
              fontSize: 10,
              fill: '#909399',
              textAlign: 'center',
            },
            left: 'center',
            top: 14,
          },
        ],
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
}

function handleResize() {
  if (chart) chart.resize()
}

watch(
  () => [props.cityGroupPreference, props.reliabilityScore],
  () => {
    if (chart) {
      chart.setOption(buildOption(), true)
    }
  },
  { deep: true }
)

onMounted(() => {
  nextTick(() => initChart())
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<template>
  <div class="city-preference">
    <!-- Section 1: Donut Chart -->
    <div class="donut-section">
      <div ref="chartRef" class="chart-container"></div>
      <div class="reliability-badge">
        数据可靠性: {{ reliabilityPercent }}%
      </div>
    </div>

    <!-- Section 2: Blend Ratio Bar -->
    <div class="blend-section">
      <div class="blend-label">个人 / 群体 偏好融合比</div>
      <div class="blend-bar">
        <div
          class="blend-segment personal"
          :style="{ width: etaPercent + '%' }"
        >
          <span v-if="etaPercent > 15" class="segment-text">{{ etaPercent }}%</span>
        </div>
        <div
          class="blend-segment group"
          :style="{ width: groupPercent + '%' }"
        >
          <span v-if="groupPercent > 15" class="segment-text">{{ groupPercent }}%</span>
        </div>
      </div>
      <div class="blend-legend">
        <span class="legend-item">
          <span class="legend-dot personal-dot"></span> 个人偏好 (&eta;)
        </span>
        <span class="legend-item">
          <span class="legend-dot group-dot"></span> 群体趋势 (1-&eta;)
        </span>
      </div>
      <div class="blend-description">{{ blendDescription }}</div>
    </div>
  </div>
</template>

<style scoped>
.city-preference {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.donut-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.chart-container {
  width: 100%;
  flex: 1;
  min-height: 160px;
}

.reliability-badge {
  font-size: 11px;
  color: #409EFF;
  background: rgba(64, 158, 255, 0.08);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 12px;
  padding: 2px 12px;
  margin-top: 4px;
}

.blend-section {
  padding: 8px 12px 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.blend-label {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}

.blend-bar {
  display: flex;
  height: 20px;
  border-radius: 10px;
  overflow: hidden;
  background: #f0f2f5;
}

.blend-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.5s ease;
}

.blend-segment.personal {
  background: linear-gradient(90deg, #409EFF, #66b1ff);
}

.blend-segment.group {
  background: linear-gradient(90deg, #E6A23C, #f0c78a);
}

.segment-text {
  font-size: 11px;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.blend-legend {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: #606266;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.personal-dot {
  background: #409EFF;
}

.group-dot {
  background: #E6A23C;
}

.blend-description {
  font-size: 11px;
  color: #909399;
  line-height: 1.5;
}
</style>
