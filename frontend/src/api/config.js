import request from '@/utils/request'

export function getMockStatus() {
  return request.get('/config/mock-status')
}

export function setMockStatus(enabled) {
  return request.put('/config/mock-status', { enabled })
}

export function getSupportedCities() {
  return request.get('/config/cities')
}
