<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { trapTabKey } from '@/utils/focusTrap';

interface Props {
  open: boolean;
  loading: boolean;
  hasReadyKbFiles: boolean;
  readyKbFileCount: number;
  selectedKbFileCount: number;
  generateFromWebSearch: boolean;
  generateFromUploadedFile: boolean;
  restoreFocusEl: HTMLElement | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'update:generateFromWebSearch', value: boolean): void;
  (e: 'update:generateFromUploadedFile', value: boolean): void;
  (e: 'goToKnowledgeBase'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const advancedDialogRef = ref<HTMLElement | null>(null);
const webSearchInputRef = ref<HTMLInputElement | null>(null);

const close = () => emit('update:open', false);

const webSearchModel = computed({
  get: () => props.generateFromWebSearch,
  set: (v: boolean) => emit('update:generateFromWebSearch', v),
});

const uploadedFileModel = computed({
  get: () => props.generateFromUploadedFile,
  set: (v: boolean) => emit('update:generateFromUploadedFile', v),
});

const onKeydown = (e: KeyboardEvent) => {
  if (!props.open) return;
  if (e.key === 'Escape') {
    close();
    return;
  }
  if (e.key === 'Tab' && advancedDialogRef.value) {
    trapTabKey(e, advancedDialogRef.value);
  }
};

watch(
  () => props.open,
  async (open) => {
    if (open) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKeydown);
      await nextTick();
      webSearchInputRef.value?.focus?.();
      if (document.activeElement !== webSearchInputRef.value) {
        advancedDialogRef.value?.focus();
      }
      return;
    }

    document.body.style.overflow = '';
    document.removeEventListener('keydown', onKeydown);
    await nextTick();
    const el = props.restoreFocusEl;
    if (el && document.contains(el)) el.focus();
  },
  { flush: 'post' },
);

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown);
  document.body.style.overflow = '';
});
</script>

<template>
  <Teleport to="body">
    <Transition name="td-modal">
      <div v-if="props.open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <button
          type="button"
          class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          :aria-label="t('common.close')"
          @click="close"
        />

        <div
          ref="advancedDialogRef"
          class="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ppt-advanced-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2">
              <LucideIcon name="settings-2" :size="18" class="text-slate-500" />
              <h3 id="ppt-advanced-title" class="text-sm font-black text-slate-900 dark:text-white">
                {{ t('ppt.advanced.title') }}
              </h3>
            </div>
            <button
              type="button"
              class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              :aria-label="t('common.close')"
              @click="close"
            >
              <LucideIcon name="x" :size="18" />
            </button>
          </div>

          <div class="px-5 py-4 space-y-3 max-h-[min(70vh,640px)] overflow-y-auto custom-scrollbar">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30">
                <input
                  ref="webSearchInputRef"
                  v-model="webSearchModel"
                  :disabled="props.loading"
                  type="checkbox"
                  class="mt-1 h-4 w-4 accent-indigo-600 disabled:opacity-50"
                />
                <div class="min-w-0">
                  <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.web_search') }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ t('ppt.advanced.web_search_desc') }}</div>
                </div>
              </label>

              <label
                class="flex items-start gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30"
                :class="!props.hasReadyKbFiles ? 'opacity-60' : ''"
              >
                <input
                  v-model="uploadedFileModel"
                  :disabled="props.loading || !props.hasReadyKbFiles"
                  type="checkbox"
                  class="mt-1 h-4 w-4 accent-indigo-600 disabled:opacity-50"
                />
                <div class="min-w-0">
                  <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.kb') }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ t('ppt.advanced.kb_desc') }}</div>
                </div>
              </label>
            </div>

            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30">
              <div class="min-w-0">
                <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('ppt.advanced.kb_files') }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {{ t('ppt.advanced.kb_files_desc', { count: props.selectedKbFileCount }) }}
                </div>
              </div>
              <button
                type="button"
                class="px-3 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-200 font-bold text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors disabled:opacity-50"
                :disabled="props.loading"
                @click="emit('goToKnowledgeBase')"
              >
                {{ props.hasReadyKbFiles ? t('ppt.advanced.manage_kb_files') : t('ppt.advanced.goto_kb') }}
              </button>
            </div>

            <div class="flex items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
              <div>{{ t('ppt.advanced.kb_ready', { count: props.readyKbFileCount }) }}</div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button
              type="button"
              class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-colors"
              @click="close"
            >
              {{ t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 4px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.5);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(71, 85, 105, 0.7);
}

.td-modal-enter-active,
.td-modal-leave-active {
  transition: opacity 150ms ease;
}

.td-modal-enter-from,
.td-modal-leave-to {
  opacity: 0;
}

.td-modal-enter-active .td-modal-panel,
.td-modal-leave-active .td-modal-panel {
  transition: transform 150ms ease, opacity 150ms ease;
}

.td-modal-enter-from .td-modal-panel,
.td-modal-leave-to .td-modal-panel {
  opacity: 0;
  transform: translateY(6px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .td-modal-enter-active,
  .td-modal-leave-active,
  .td-modal-enter-active .td-modal-panel,
  .td-modal-leave-active .td-modal-panel {
    transition: none;
  }
}
</style>
