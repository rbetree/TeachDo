<script setup lang="ts">
/* eslint-env browser */
 
import { onMounted, onUnmounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ToastType } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
}

const toasts = reactive<ToastMessage[]>([]);
const { t } = useI18n();

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
  <div class="fixed top-20 right-4 z-[999] pointer-events-none">
    <transition-group name="toast-slide" tag="div" class="flex flex-col gap-3">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="min-w-[260px] pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg bg-white/95 dark:bg-slate-900/90 flex items-center justify-between gap-3"
        :role="toast.type === 'error' ? 'alert' : 'status'"
        :aria-live="toast.type === 'error' ? 'assertive' : 'polite'"
        aria-atomic="true"
        :class="{
          'border-emerald-200 text-emerald-600 dark:border-emerald-800 dark:text-emerald-300': toast.type === 'success',
          'border-red-200 text-red-600 dark:border-red-800 dark:text-red-300': toast.type === 'error',
          'border-indigo-200 text-indigo-600 dark:border-indigo-800 dark:text-indigo-300': toast.type === 'info',
        }"
      >
        <span class="text-sm font-medium">{{ toast.message }}</span>
        <button
          type="button"
          class="w-11 h-11 -my-2 -mr-2 inline-flex items-center justify-center rounded-xl text-slate-500 dark:text-slate-300 opacity-70 hover:opacity-100 hover:bg-black/5 dark:hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-slate-900"
          :aria-label="t('common.close')"
          :title="t('common.close')"
          @click="remove(toast.id)"
        >
          <LucideIcon name="x" :size="18" />
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
