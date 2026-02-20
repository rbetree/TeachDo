<template>
  <div class="page-layout">
    <!-- Navbar -->
    <Navbar v-if="!hideNavbar" :avatar-url="avatarUrl" />
    
    <!-- Step Progress -->
    <StepProgress 
      v-if="!hideSteps" 
      :current-step="currentStep"
      :steps="steps"
    />
    
    <!-- Main Content Area -->
    <main class="main-content" :class="{ 'full-height': fullHeight }">
      <div class="page-section" :class="pageClass">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import Navbar from './Navbar.vue'
import StepProgress, { type Step } from './StepProgress.vue'

interface Props {
  currentStep?: number
  steps?: Step[]
  hideNavbar?: boolean
  hideSteps?: boolean
  fullHeight?: boolean
  pageClass?: string
  avatarUrl?: string
}

withDefaults(defineProps<Props>(), {
  currentStep: 0,
  hideNavbar: false,
  hideSteps: true,
  fullHeight: false,
  pageClass: '',
  avatarUrl: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix'
})
</script>

<style scoped lang="scss">
.page-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--bg-body);
  overflow: hidden;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  position: relative;
  padding: var(--spacing-xl) 0 120px;
  
  &.full-height {
    display: flex;
    flex-direction: column;
  }
}

.page-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: fadeIn 0.4s ease;
  min-height: 100%;
  
  &.full-height {
    height: 100%;
  }
}

/* Fade in animation */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-content {
    padding: var(--spacing-md) 0 120px;
  }
}
</style>
