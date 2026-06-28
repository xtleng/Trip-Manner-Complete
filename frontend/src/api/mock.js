import { EKD_TRIP_CITIES, CROSS_CITY_CITIES, CITY_TO_MOCK_FILE, CROSS_CITY_MOCK_FILES, ALGORITHM_TYPES } from '@/utils/constants'

export async function loadMockRoutes(city) {
  const fileName = CITY_TO_MOCK_FILE[city]
  if (fileName) {
    const response = await fetch(`/mock/${fileName}.json`)
    return response.json()
  }
  return null
}

export async function loadCrossCityMockRoutes(sourceCity, targetCity) {
  const key = `${sourceCity}_${targetCity}`
  const fileName = CROSS_CITY_MOCK_FILES[key]
  if (fileName) {
    const response = await fetch(`/mock/${fileName}.json`)
    return response.json()
  }
  // Try reverse order
  const reverseKey = `${targetCity}_${sourceCity}`
  const reverseFileName = CROSS_CITY_MOCK_FILES[reverseKey]
  if (reverseFileName) {
    const response = await fetch(`/mock/${reverseFileName}.json`)
    return response.json()
  }
  return null
}

export function determineMockAlgorithm(destinationCity, sourceCity = null) {
  if (EKD_TRIP_CITIES.includes(destinationCity)) return ALGORITHM_TYPES.EKD_TRIP
  if (sourceCity && CROSS_CITY_CITIES.includes(destinationCity)) return ALGORITHM_TYPES.CROSS_CITY
  if (!sourceCity && CROSS_CITY_CITIES.includes(destinationCity)) return ALGORITHM_TYPES.CROSS_CITY
  return ALGORITHM_TYPES.DEEPSEEK
}
