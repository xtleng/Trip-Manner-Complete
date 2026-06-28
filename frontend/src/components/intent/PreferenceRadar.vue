<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  preferenceFactors: {
    type: Object,
    default: () => ({}),
  },
  cityGroupPreference: {
    type: Object,
    default: () => ({}),
  },
})

const chartRef = ref(null)
let chart = null

const factorKeys = computed(() =>
  Object.keys(props.preferenceFactors).sort()
)

const indicatorLabels = computed(() =>
  factorKeys.value.map((k) => props.preferenceFactors[k]?.label || k)
)

const personalValues = computed(() =>
  factorKeys.value.map((k) => props.preferenceFactors[k]?.weight || 0)
)

// Map city group keys to factor order
const cityGroupKeys = ['cultural', 'nature', 'food', 'shopping']

const cityGroupValues = computed(() =>
  cityGroupKeys.map((k) => props.cityGroupPreference[k] || 0)
)

function buildOption() {
  const maxVal = 0.6
  const indicators = indicatorLabels.value.map((label) => ({
    name: label,
    max: maxVal,
  }))

  return {
    legend: {
      bottom: 0,
      itemWidth: 14,
      itemHeight: 10,
      textStyle: { fontSize: 11, color: '#606266' },
      data: ['个人偏好', '城市群体偏好'],
    },
    radar: {
      center: ['50%', '45%'],
      radius: '60%',
      indicator: indicators,
      axisName: {
        color: '#606266',
        fontSize: 11,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(64, 158, 255, 0.04)', 'rgba(64, 158, 255, 0.08)'],
        },
      },
      splitLine: {
        lineStyle: { color: '#e4e7ed' },
      },
      axisLine: {
        lineStyle: { color: '#dcdfe6' },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            name: '个人偏好',
            value: personalValues.value,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { color: '#409EFF', width: 2 },
            areaStyle: { color: 'rgba(64, 158, 255, 0.2)' },
            itemStyle: { color: '#409EFF' },
          },
          {
            name: '城市群体偏好',
            value: cityGroupValues.value,
            symbol: 'diamond',
            symbolSize: 6,
            lineStyle: { color: '#E6A23C', width: 2, type: 'dashed' },
            areaStyle: { color: 'rgba(230, 162, 60, 0.12)' },
            itemStyle: { color: '#E6A23C' },
          },
        ],
      },
    ],
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: { color: '#303133', fontSize: 12 },
    },
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
  () => [props.preferenceFactors, props.cityGroupPreference],
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
  <div class="preference-radar">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.preference-radar {
  height: 100%;
  width: 100%;
  min-height: 200px;
}

.chart-container {
  width: 100%;
  height: 100%;
}
</style>
