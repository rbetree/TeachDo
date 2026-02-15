<script setup lang="ts">
/* eslint-env browser */
 
import { onMounted, onUnmounted, reactive } from 'vue';
import type { ToastType } from '@/utils/toast';

interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
}

const toasts = reactive<ToastMessage[]>([]);

const remove = (id: string) => {
  const index = toasts.findIndex((t) => t.id === id);
  if (index >= 0) {
    toasts.splice(index, 1);
  }
};

const handleEvent = (event: Event) => {
  const detail = (event as CustomEvent<{ type: ToastType; message: string }>).detail;
  if (!detail) return;
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  toasts.push({ id, type: detail.type, message: detail.message });
  setTimeout(() => remove(id), 4000);
};

onMounted(() => {
  window.addEventListener('toast', handleEvent);
});

onUnmounted(() => {
  window.removeEventListener('toast', handleEvent);
});
</script>

<template>
  <div class="fixed top-20 right-4 z-[999] flex flex-col gap-3 pointer-events-none">
    <transition-group name="toast-slide" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="min-w-[260px] pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg bg-white/95 dark:bg-slate-900/90 flex items-center justify-between gap-3"
        :class="{
          'border-emerald-200 text-emerald-600 dark:border-emerald-800 dark:text-emerald-300': toast.type === 'success',
          'border-red-200 text-red-600 dark:border-red-800 dark:text-red-300': toast.type === 'error',
          'border-indigo-200 text-indigo-600 dark:border-indigo-800 dark:text-indigo-300': toast.type === 'info',
        }"
      >
        <span class="text-sm font-medium">{{ toast.message }}</span>
        <button class="text-xs opacity-60 hover:opacity-100" @click="remove(toast.id)">✕</button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.25s ease;
}
.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
