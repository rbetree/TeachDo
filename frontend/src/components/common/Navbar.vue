<template>
  <nav class="navbar">
    <div class="navbar-left">
      <button class="logo-btn" type="button" @click="goHome">
        <span class="logo-text">ai2ppt</span>
      </button>
    </div>

    <div v-if="!hideLinks" class="navbar-center">
      <RouterLink
        to="/"
        class="nav-link"
        :class="{ active: currentPath === '/' }"
      >
        Home
      </RouterLink>
      <RouterLink
        to="/about"
        class="nav-link"
        :class="{ active: currentPath === '/about' }"
      >
        About
      </RouterLink>
    </div>
    
    <div class="navbar-actions">
      <!-- Theme Toggle Button -->
      <button 
        class="theme-toggle-btn" 
        @click="toggleTheme"
        :title="currentTheme === 'light' ? '切换到深色模式' : '切换到浅色模式'"
        :aria-label="currentTheme === 'light' ? '切换到深色模式' : '切换到浅色模式'"
        type="button"
      >
        <!-- Sun Icon (shown in dark mode) -->
        <svg 
          v-show="currentTheme === 'dark'"
          class="theme-icon" 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="2" 
          stroke-linecap="round" 
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
        <!-- Moon Icon (shown in light mode) -->
        <svg 
          v-show="currentTheme === 'light'"
          class="theme-icon" 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="2" 
          stroke-linecap="round" 
          stroke-linejoin="round"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      </button>
      
      <!-- User Avatar -->
      <div class="navbar-avatar">
        <img 
          :src="avatarUrl" 
          alt="用户头像"
          class="avatar-image"
        />
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useTheme } from '@/hooks/useTheme'

interface Props {
  avatarUrl?: string
  hideLinks?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  avatarUrl: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix',
  hideLinks: false
})

const route = useRoute()
const router = useRouter()
const { currentTheme, toggleTheme } = useTheme()

const currentPath = computed(() => route.path)

const goHome = () => {
  if (route.path !== '/') {
    router.push('/')
  }
}
</script>

<style scoped lang="scss">
.navbar {
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  flex-shrink: 0;
  background-color: var(--bg-body);
}

.navbar-left,
.navbar-center,
.navbar-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.navbar-center {
  gap: 2rem;
}

.logo-btn {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.logo-text {
  font-weight: 700;
  font-size: 1.2rem;
  letter-spacing: -0.03em;
  color: var(--text-primary);
}

.nav-link {
  position: relative;
  font-size: 0.9rem;
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: color var(--transition-base) ease;
  
  &.active,
  &:hover {
    color: var(--text-primary);
  }
  
  &.active::after {
    content: '';
    position: absolute;
    left: 0;
    bottom: -4px;
    width: 100%;
    height: 1px;
    background-color: var(--text-primary);
  }
}

.theme-toggle-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  background-color: transparent;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  transition: background-color var(--transition-base) ease, border-color var(--transition-base) ease;
  
  &:hover {
    background-color: var(--bg-surface);
    border-color: var(--text-primary);
  }
  
  &:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
}

.theme-icon {
  flex-shrink: 0;
}

.navbar-avatar {
  width: 32px;
  height: 32px;
  background: var(--bg-surface);
  border-radius: 50%;
  overflow: hidden;
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: transform var(--transition-base) ease, 
              border-color var(--transition-base) ease;
  
  &:hover {
    transform: scale(1.05);
    border-color: var(--text-primary);
  }
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .navbar {
    padding: 0 var(--spacing-md);
  }
  
  .navbar-center {
    display: none;
  }
}
</style>
