<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatHistory from '@/components/chat/ChatHistory.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import MapView from '@/components/map/MapView.vue'
import IntentPanel from '@/components/intent/IntentPanel.vue'

const chatStore = useChatStore()
const mapViewRef = ref(null)
const intentCollapsed = ref(false)

function handleIntentToggle() {
  intentCollapsed.value = !intentCollapsed.value
}

// Event handlers
function handleCreateDialog() {
  if (typeof chatStore.createDialog === 'function') {
    chatStore.createDialog()
  } else {
    // Fallback: create a new dialog manually
    const newId = Date.now().toString()
    chatStore.dialogs.push({
      id: newId,
      title: '新对话',
      createdAt: new Date().toISOString(),
    })
    chatStore.currentDialogId = newId
    chatStore.messages = []
  }
}

function handleSelectDialog(id) {
  if (typeof chatStore.switchDialog === 'function') {
    chatStore.switchDialog(id)
  } else {
    chatStore.setCurrentDialogId(id)
    chatStore.setMessages([])
  }
}

function handleDeleteDialog(id) {
  if (typeof chatStore.deleteDialog === 'function') {
    chatStore.deleteDialog(id)
  } else {
    const idx = chatStore.dialogs.findIndex((d) => d.id === id)
    if (idx !== -1) {
      chatStore.dialogs.splice(idx, 1)
    }
    if (chatStore.currentDialogId === id) {
      chatStore.currentDialogId = chatStore.dialogs.length > 0 ? chatStore.dialogs[0].id : null
      chatStore.messages = []
    }
  }
}

function handleSendMessage(text) {
  if (typeof chatStore.sendMessage === 'function') {
    chatStore.sendMessage(text)
  } else {
    chatStore.addMessage({
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    })
  }
}

// Watch for pois reset (new dialog) to clear map
watch(
  () => chatStore.currentDialogId,
  () => {
    nextTick(() => {
      if (mapViewRef.value && typeof mapViewRef.value.clearMap === 'function') {
        mapViewRef.value.clearMap()
      }
    })
  }
)

// Watch currentPois if it exists
watch(
  () => chatStore.currentPois,
  (newPois) => {
    if (!newPois || (Array.isArray(newPois) && newPois.length === 0)) {
      if (mapViewRef.value && typeof mapViewRef.value.clearMap === 'function') {
        mapViewRef.value.clearMap()
      }
    }
  },
  { deep: true }
)

// Auto-create a dialog on mount if none exists
onMounted(() => {
  if (chatStore.dialogs.length === 0) {
    handleCreateDialog()
  }
})
</script>

<template>
  <div class="home-view">
    <!-- Left Sidebar: Chat History -->
    <aside class="sidebar">
      <ChatHistory
        @create="handleCreateDialog"
        @select="handleSelectDialog"
        @delete="handleDeleteDialog"
      />
    </aside>

    <!-- Main Content Area -->
    <div class="main-area">
      <!-- Top Section: Chat + Map -->
      <div class="top-section">
        <div class="chat-panel-wrapper">
          <ChatPanel
            :messages="chatStore.messages"
            :is-streaming="chatStore.isStreaming"
          />
        </div>
        <div class="map-wrapper">
          <MapView
            ref="mapViewRef"
            :pois="chatStore.currentPois || []"
          />
        </div>
      </div>

      <!-- Middle Section: Intent Panel (conditional) -->
      <transition name="fade">
        <div
          v-if="chatStore.currentIntentData"
          class="intent-section"
          :class="{ 'intent-collapsed': intentCollapsed }"
        >
          <IntentPanel
            :algorithm-type="chatStore.currentAlgorithm || ''"
            :intent-data="chatStore.currentIntentData"
            :source-city="chatStore.parsedFields?.departure_city || ''"
            :target-city="chatStore.parsedFields?.destination_city || ''"
            :collapsed="intentCollapsed"
            @toggle="handleIntentToggle"
          />
        </div>
      </transition>

      <!-- Bottom Section: Chat Input -->
      <div class="input-section">
        <ChatInput
          :is-streaming="chatStore.isStreaming"
          @send="handleSendMessage"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  height: 100%;
  display: flex;
  overflow: hidden;
}

/* Left Sidebar */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Main Content Area */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* Top Section: Chat + Map side by side */
.top-section {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.chat-panel-wrapper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.map-wrapper {
  flex: 1;
  overflow: hidden;
  border-left: 1px solid #e4e7ed;
  min-width: 0;
}

/* Intent Section */
.intent-section {
  height: var(--intent-panel-height, 220px);
  flex-shrink: 0;
  border-top: 1px solid #e4e7ed;
  overflow: hidden;
  transition: height 0.3s ease;
}

.intent-section.intent-collapsed {
  height: 42px;
}

/* Input Section */
.input-section {
  flex-shrink: 0;
  border-top: 1px solid #e4e7ed;
  background: #fff;
}

/* Fade transition for IntentPanel */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, max-height 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
