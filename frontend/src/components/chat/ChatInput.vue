<script setup>
import { ref, computed } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'

const emit = defineEmits(['send'])

const props = defineProps({
  isStreaming: {
    type: Boolean,
    default: false,
  },
})

const appStore = useAppStore()
const inputText = ref('')

const algorithmLabel = computed(() => {
  return appStore.currentAlgorithm || ''
})

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.isStreaming) return
  emit('send', text)
  inputText.value = ''
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input">
    <div class="input-row">
      <el-input
        v-model="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 4 }"
        placeholder="Tell me where you want to travel..."
        :disabled="isStreaming"
        @keydown="handleKeydown"
        resize="none"
      />
      <el-button
        type="primary"
        :icon="Promotion"
        circle
        :disabled="!inputText.trim() || isStreaming"
        @click="handleSend"
        class="send-btn"
      />
    </div>
    <div v-if="algorithmLabel" class="input-status">
      <div class="status-right">
        <el-tag size="small" type="info" effect="plain">{{ algorithmLabel }}</el-tag>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-input {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  background-color: #fff;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-row :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 8px 14px;
  font-size: 14px;
  line-height: 1.5;
  box-shadow: none;
}

.send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
}

.input-status {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 6px;
  padding: 0 4px;
}

.status-right {
  display: flex;
  align-items: center;
}
</style>
