/**
 * 主题切换 Composable
 * 支持浅色/深色主题切换和 localStorage 持久化
 */

import { ref, onMounted, watch } from 'vue'

type Theme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'app-theme'

// 全局状态 - 跨组件共享
const currentTheme = ref<Theme>('light')

export function useTheme() {
  /**
   * 从 localStorage 加载主题
   */
  const loadTheme = (): Theme => {
    try {
      const savedTheme = localStorage.getItem(THEME_STORAGE_KEY)
      if (savedTheme === 'dark' || savedTheme === 'light') {
        return savedTheme
      }
    }
    catch (error) {
      console.warn('Failed to load theme from localStorage:', error)
    }
    
    // 检测系统主题偏好
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    
    return 'light'
  }

  /**
   * 应用主题到 DOM
   */
  const applyTheme = (theme: Theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    currentTheme.value = theme
  }

  /**
   * 保存主题到 localStorage
   */
  const saveTheme = (theme: Theme) => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    }
    catch (error) {
      console.warn('Failed to save theme to localStorage:', error)
    }
  }

  /**
   * 切换主题
   */
  const toggleTheme = () => {
    const newTheme: Theme = currentTheme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }

  /**
   * 设置指定主题
   */
  const setTheme = (theme: Theme) => {
    applyTheme(theme)
    saveTheme(theme)
  }

  /**
   * 初始化主题
   */
  const initTheme = () => {
    const theme = loadTheme()
    applyTheme(theme)
  }

  // 监听系统主题变化
  onMounted(() => {
    // 初始化主题
    initTheme()

    // 监听系统主题偏好变化
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      // 只在用户未手动设置主题时响应系统变化
      if (!localStorage.getItem(THEME_STORAGE_KEY)) {
        const newTheme: Theme = e.matches ? 'dark' : 'light'
        applyTheme(newTheme)
      }
    }

    // 兼容不同浏览器
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange)
    }
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange)
    }

    // 清理监听器
    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange)
      }
      else if (mediaQuery.removeListener) {
        mediaQuery.removeListener(handleChange)
      }
    }
  })

  return {
    currentTheme,
    toggleTheme,
    setTheme,
    initTheme,
    isDark: ref(currentTheme.value === 'dark'),
  }
}

// 导出工具函数
export const getTheme = (): Theme => {
  return currentTheme.value
}

export const isDarkTheme = (): boolean => {
  return currentTheme.value === 'dark'
}