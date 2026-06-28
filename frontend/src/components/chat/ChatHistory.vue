<script setup>
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'

const emit = defineEmits(['select', 'create', 'delete'])

const chatStore = useChatStore()

const dialogs = computed(() => chatStore.dialogs)
const currentId = computed(() => chatStore.currentDialogId)

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return d.toLocaleDateString()
}

function handleSelect(id) {
  emit('select', id)
}

function handleCreate() {
  emit('create')
}

function handleDelete(id) {
  emit('delete', id)
}
</script>

<template>
  <div class="chat-history">
    <div class="history-header">
      <el-button
        type="primary"
        class="new-chat-btn"
        @click="handleCreate"
      >
        <el-icon><Plus /></el-icon>
        <span>New Chat</span>
      </el-button>
    </div>

    <div class="dialog-list">
      <div
        v-for="dialog in dialogs"
        :key="dialog.id"
        class="dialog-item"
        :class="{ active: dialog.id === currentId }"
        @click="handleSelect(dialog.id)"
      >
        <div class="dialog-info">
          <div class="dialog-title">{{ dialog.title || 'New Chat' }}</div>
          <div class="dialog-date">{{ formatDate(dialog.updated_at || dialog.created_at) }}</div>
        </div>
        <el-icon
          class="delete-icon"
          @click.stop="handleDelete(dialog.id)"
        >
          <Delete />
        </el-icon>
      </div>

      <div v-if="dialogs.length === 0" class="empty-hint">
        <el-icon :size="32" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>No conversations yet</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #fafafa;
  border-right: 1px solid #e4e7ed;
}

.history-header {
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.new-chat-btn {
  width: 100%;
}

.dialog-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.dialog-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.dialog-item:hover {
  background-color: #ecf5ff;
}

.dialog-item.active {
  background-color: #d9ecff;
}

.dialog-info {
  flex: 1;
  min-width: 0;
}

.dialog-title {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.dialog-date {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.delete-icon {
  flex-shrink: 0;
  color: #c0c4cc;
  font-size: 14px;
  opacity: 0;
  transition: all 0.2s;
  padding: 4px;
  border-radius: 4px;
}

.dialog-item:hover .delete-icon {
  opacity: 1;
}

.delete-icon:hover {
  color: #F56C6C;
  background-color: #fef0f0;
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 8px;
}

.empty-hint p {
  font-size: 13px;
  color: #909399;
}
</style>
