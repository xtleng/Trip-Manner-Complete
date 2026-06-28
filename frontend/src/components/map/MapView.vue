<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import L from 'leaflet'

const props = defineProps({
  pois: {
    type: Array,
    default: () => [],
  },
  center: {
    type: Array,
    default: () => [35.68, 139.76],
  },
  zoom: {
    type: Number,
    default: 12,
  },
})

const mapContainer = ref(null)

// CRITICAL: Plain variable for Leaflet map — NOT reactive
let map = null
let markers = []
let polylines = []
let prevPoisLength = 0

function getMarkerColor(poi, totalCount) {
  if (poi.visit_order === 1) return '#67C23A'
  if (poi.visit_order === totalCount) return '#F56C6C'
  return '#409EFF'
}

function createMarkerIcon(number, color) {
  return L.divIcon({
    className: 'poi-marker-wrapper',
    html: `<div class="poi-marker" style="background-color: ${color};">${number}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  })
}

function addMarker(poi, totalCount) {
  if (!map) return
  const color = getMarkerColor(poi, totalCount)
  const icon = createMarkerIcon(poi.visit_order, color)
  const marker = L.marker([poi.latitude, poi.longitude], { icon })
    .addTo(map)

  const popupContent = `
    <div style="min-width: 160px; padding: 4px 0;">
      <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px; color: #303133;">
        ${poi.visit_order}. ${poi.name}
      </div>
      <div style="font-size: 12px; color: #606266; margin-bottom: 4px;">
        <span style="color: #909399;">类别:</span> ${poi.category}
      </div>
      <div style="font-size: 12px; color: #606266;">
        <span style="color: #909399;">建议游览:</span> ${poi.recommended_duration_min} 分钟
      </div>
    </div>
  `
  marker.bindPopup(popupContent)
  markers.push(marker)
}

function addPolyline(from, to) {
  if (!map) return
  const line = L.polyline(
    [
      [from.latitude, from.longitude],
      [to.latitude, to.longitude],
    ],
    {
      color: '#409EFF',
      weight: 2.5,
      opacity: 0.7,
      dashArray: '8, 6',
    }
  ).addTo(map)
  polylines.push(line)
}

function fitMapBounds() {
  if (!map || markers.length === 0) return
  const group = L.featureGroup(markers)
  map.flyToBounds(group.getBounds(), {
    padding: [40, 40],
    maxZoom: 15,
    duration: 0.8,
  })
}

function clearMap() {
  markers.forEach((m) => m.remove())
  polylines.forEach((p) => p.remove())
  markers = []
  polylines = []
  prevPoisLength = 0
}

function initMap() {
  if (!mapContainer.value) return
  map = L.map(mapContainer.value, {
    center: props.center,
    zoom: props.zoom,
    zoomControl: true,
  })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map)
}

watch(
  () => props.pois,
  (newPois) => {
    if (!map || !newPois) return

    const newLen = newPois.length
    const totalCount = newPois.length

    if (newLen > prevPoisLength) {
      // Update the color of the previous last marker (it may have been red)
      if (prevPoisLength > 0 && markers.length >= prevPoisLength) {
        const prevLastIdx = prevPoisLength - 1
        const prevLastPoi = newPois[prevLastIdx]
        if (prevLastPoi) {
          const oldMarker = markers[prevLastIdx]
          if (oldMarker) {
            const newColor = getMarkerColor(prevLastPoi, totalCount)
            oldMarker.setIcon(createMarkerIcon(prevLastPoi.visit_order, newColor))
          }
        }
      }

      // Add new POIs
      for (let i = prevPoisLength; i < newLen; i++) {
        addMarker(newPois[i], totalCount)
        if (i > 0) {
          addPolyline(newPois[i - 1], newPois[i])
        }
      }

      prevPoisLength = newLen
      nextTick(() => fitMapBounds())
    } else if (newLen === 0) {
      clearMap()
    }
  },
  { deep: true }
)

watch(
  () => props.center,
  (newCenter) => {
    if (map && newCenter) {
      map.setView(newCenter, props.zoom)
    }
  }
)

onMounted(() => {
  initMap()
  // Render any initial POIs
  if (props.pois && props.pois.length > 0) {
    const totalCount = props.pois.length
    props.pois.forEach((poi) => addMarker(poi, totalCount))
    for (let i = 1; i < props.pois.length; i++) {
      addPolyline(props.pois[i - 1], props.pois[i])
    }
    prevPoisLength = props.pois.length
    nextTick(() => fitMapBounds())
  }
})

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
  markers = []
  polylines = []
})

defineExpose({ clearMap })
</script>

<template>
  <div class="map-view">
    <div ref="mapContainer" class="map-container"></div>
  </div>
</template>

<style scoped>
.map-view {
  height: 100%;
  width: 100%;
  position: relative;
}

.map-container {
  height: 100%;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}
</style>

<style>
/* Global styles for Leaflet markers — not scoped */
.poi-marker-wrapper {
  background: transparent !important;
  border: none !important;
}

.poi-marker {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  animation: poiPopIn 0.3s ease-out;
}

@keyframes poiPopIn {
  from {
    transform: scale(0);
  }
  to {
    transform: scale(1);
  }
}

/* Fix Leaflet popup close button */
.leaflet-popup-content-wrapper {
  border-radius: 8px !important;
  box-shadow: 0 3px 14px rgba(0, 0, 0, 0.15) !important;
}
</style>
