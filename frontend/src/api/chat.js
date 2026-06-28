import request from '@/utils/request'

export function sendMessage(dialogId, data) {
  return request.post(`/chat/${dialogId}/message`, data)
}

export function getDialogs() {
  return request.get('/chat/dialogs')
}

export function getDialog(dialogId) {
  return request.get(`/chat/dialogs/${dialogId}`)
}
