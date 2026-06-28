<script setup>
import { ref, watch, nextTick, computed } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  isStreaming: {
    type: Boolean,
    default: false,
  },
})

const scrollContainer = ref(null)

// Auto-scroll to bottom when messages change
watch(
  () => props.messages.length,
  () => {
    scrollToBottom()
  },
)

// Also watch the last message content for streaming updates
const lastMessageContent = computed(() => {
  if (props.messages.length === 0) return ''
  return props.messages[props.messages.length - 1].content
})

watch(lastMessageContent, () => {
  scrollToBottom()
})

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

function renderContent(text) {
  if (!text) return ''
  // Simple markdown-like bold rendering: **text** -> <strong>text</strong>
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // Convert newlines to <br>
  html = html.replace(/\n/g, '<br>')
  return html
}

function isThinking(msg) {
  return msg.role === 'assistant' && msg.content && msg.content.startsWith('正在')
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  const hours = d.getHours().toString().padStart(2, '0')
  const minutes = d.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}
</script>

<template>
  <div class="chat-panel">
    <!-- Empty state -->
    <div v-if="messages.length === 0" class="empty-state">
      <el-icon :size="48" color="#c0c4cc"><ChatDotSquare /></el-icon>
      <p class="empty-title">TripManner</p>
      <p class="empty-subtitle">Start a new conversation to plan your trip</p>
    </div>

    <!-- Messages -->
    <div v-else ref="scrollContainer" class="messages-container">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message-row"
        :class="msg.role"
      >
        <div class="message-bubble" :class="msg.role">
          <!-- Thinking indicator -->
          <div v-if="isThinking(msg) && isStreaming && index === messages.length - 1" class="thinking-indicator">
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
          </div>

          <!-- Content -->
          <div class="message-content" v-html="renderContent(msg.content)"></div>

          <!-- Typewriter cursor -->
          <span
            v-if="isStreaming && msg.role === 'assistant' && index === messages.length - 1"
            class="cursor"
          >|</span>

          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #606266;
  margin-top: 8px;
}

.empty-subtitle {
  font-size: 14px;
  color: #909399;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.message-row {
  display: flex;
  margin-bottom: 16px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
  position: relative;
}

.message-bubble.user {
  background-color: #409EFF;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background-color: #f4f4f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.message-content {
  display: inline;
}

.message-content :deep(strong) {
  font-weight: 600;
}

.message-time {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
  text-align: right;
}

.message-bubble.user .message-time {
  color: rgba(255, 255, 255, 0.7);
}

/* Typewriter cursor */
.cursor {
  display: inline;
  animation: blink 0.8s step-end infinite;
  font-weight: 300;
  color: #409EFF;
}

.message-bubble.assistant .cursor {
  color: #409EFF;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Thinking indicator */
.thinking-indicator {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #409EFF;
  animation: thinking-pulse 1.4s ease-in-out infinite;
}

.thinking-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-pulse {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}
</style>
