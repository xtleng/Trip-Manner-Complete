import request from '@/utils/request'

export function planRoute(data) {
  return request.post('/plan/route', data)
}

export function getHistory() {
  return request.get('/plan/history')
}

export function getPlanDetail(planId) {
  return request.get(`/plan/${planId}`)
}
