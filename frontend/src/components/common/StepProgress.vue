<template>
  <div v-if="!hidden" class="steps-wrapper">
    <div class="steps">
      <template v-for="(step, index) in steps" :key="step.id">
        <!-- Step Item -->
        <div 
          class="step-item" 
          :class="{
            active: currentStep === step.id,
            completed: currentStep > step.id
          }"
        >
          <div class="step-circle">
            <span v-if="currentStep <= step.id">{{ step.id }}</span>
            <!-- Checkmark icon for completed steps -->
            <svg 
              v-else
              class="step-check-icon"
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              stroke-width="3" 
              stroke-linecap="round" 
              stroke-linejoin="round"
            >
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <span class="step-label">{{ step.label }}</span>
        </div>
        
        <!-- Divider (not after last step) -->
        <div 
          v-if="index < steps.length - 1" 
          class="step-divider"
          :class="{ completed: currentStep > step.id }"
        ></div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface Step {
  id: number
  label: string
}

interface Props {
  currentStep: number
  steps?: Step[]
  hidden?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  steps: () => [
    { id: 1, label: '输入主题' },
    { id: 2, label: '编辑大纲' },
    { id: 3, label: '选择模板' },
    { id: 4, label: '生成预览' }
  ],
  hidden: false
})
</script>

<style scoped lang="scss">
.steps-wrapper {
  background-color: var(--bg-body);
  padding: var(--spacing-xl) 0 var(--spacing-lg) 0;
  flex-shrink: 0;
  width: 100%;
}

.steps {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-lg);
  flex-wrap: wrap;
  padding: 0 var(--spacing-md);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 1.05rem;
  font-weight: 600;
  opacity: 0.5;
  position: relative;
  user-select: none;
  
  /* Active state */
  &.active {
    color: var(--primary-color);
    opacity: 1;
    transform: scale(1.05);
    
    .step-circle {
      background-color: var(--primary-color);
      color: white;
      border-color: var(--primary-color);
      box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.08), 
                  0 4px 12px rgba(0, 0, 0, 0.16);
      animation: pulse 2s ease-in-out infinite;
    }
  }
  
  /* Completed state */
  &.completed {
    color: var(--text-primary);
    opacity: 0.85;
    
    .step-circle {
      background-color: var(--primary-color);
      color: white;
      border-color: var(--primary-color);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    }
  }
  
  &:hover .step-circle {
    transform: scale(1.1);
  }
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid currentColor;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 700;
  background-color: var(--bg-body);
  flex-shrink: 0;
}

.step-check-icon {
  flex-shrink: 0;
}

.step-label {
  white-space: nowrap;
}

.step-divider {
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, var(--border-color) 0%, var(--border-color) 100%);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
  
  &.completed {
    background: linear-gradient(90deg, var(--primary-color) 0%, var(--border-color) 100%);
  }
}

/* Pulse animation for active step */
@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 4px rgba(0, 0, 0, 0.08), 
                0 4px 12px rgba(0, 0, 0, 0.16);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(0, 0, 0, 0.06), 
                0 4px 16px rgba(0, 0, 0, 0.2);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .steps {
    gap: var(--spacing-sm);
  }
  
  .step-item {
    font-size: 0.9rem;
    gap: 8px;
  }
  
  .step-circle {
    width: 32px;
    height: 32px;
    font-size: 0.85rem;
  }
  
  .step-divider {
    width: 40px;
  }
  
  .step-label {
    display: none;
  }
}

@media (max-width: 480px) {
  .step-divider {
    width: 20px;
  }
}
</style>
