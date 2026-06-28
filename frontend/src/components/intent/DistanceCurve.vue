<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TRAVEL_MODES } from '@/utils/constants'

const props = defineProps({
  distanceData: {
    type: Array,
    default: () => [],
  },
  travelMode: {
    type: String,
    default: 'approaching',
  },
})

const chartRef = ref(null)
let chart = null

function getModeColor() {
  const mode = TRAVEL_MODES[props.travelMode]
  return mode ? mode.color : '#409EFF'
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function buildOption() {
  const color = getModeColor()
  const data = props.distanceData || []
  const xLabels = data.map((_, i) => `POI ${i + 1}`)

  return {
    grid: {
      top: 24,
      right: 16,
      bottom: 32,
      left: 48,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: { color: '#303133', fontSize: 12 },
      formatter(params) {
        const p = params[0]
        return `<div style="font-weight:600;">${p.name}</div>
                <div style="margin-top:4px;">距离: <b>${p.value}</b> km</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: xLabels,
      name: 'POI访问顺序',
      nameTextStyle: { fontSize: 11, color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { show: false },
      axisLabel: { fontSize: 11, color: '#606266' },
    },
    yAxis: {
      type: 'value',
      name: '距离 (km)',
      nameTextStyle: { fontSize: 11, color: '#909399' },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f2f5', type: 'dashed' } },
      axisLabel: { fontSize: 11, color: '#909399' },
    },
    series: [
      {
        type: 'line',
        data: data,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: color,
          width: 2.5,
        },
        itemStyle: {
          color: color,
          borderColor: '#fff',
          borderWidth: 2,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexToRgba(color, 0.35) },
            { offset: 1, color: hexToRgba(color, 0.03) },
          ]),
        },
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
  () => [props.distanceData, props.travelMode],
  () => {
    if (chart) {
      chart.setOption(buildOption())
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
  <div class="distance-curve">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.distance-curve {
  height: 100%;
  width: 100%;
  min-height: 180px;
}

.chart-container {
  width: 100%;
  height: 100%;
}
</style>
