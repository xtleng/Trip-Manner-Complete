import { defineStore } from 'pinia'
import { ref } from 'vue'
import { EKD_TRIP_CITIES, CROSS_CITY_CITIES } from '@/utils/constants'

export const useAppStore = defineStore('app', () => {
  const useMockData = ref(true)
  const currentAlgorithm = ref('')
  const supportedCities = ref({
    ekdTrip: EKD_TRIP_CITIES,
    crossCity: CROSS_CITY_CITIES,
  })

  function setUseMockData(value) { useMockData.value = value }
  function setCurrentAlgorithm(algo) { currentAlgorithm.value = algo }
  function toggleMockMode() { useMockData.value = !useMockData.value }

  return { useMockData, currentAlgorithm, supportedCities, setUseMockData, setCurrentAlgorithm, toggleMockMode }
})
