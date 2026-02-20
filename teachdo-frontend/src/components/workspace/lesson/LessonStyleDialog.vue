<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonStyle } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { trapTabKey } from '@/utils/focusTrap';

interface Props {
  open: boolean;
  loading: boolean;
  style: LessonStyle;
  restoreFocusEl: HTMLElement | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'update:style', value: LessonStyle): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);
const fontSelectRef = ref<HTMLSelectElement | null>(null);

const close = () => emit('update:open', false);

const patchStyle = (patch: Partial<LessonStyle>) => {
  emit('update:style', { ...props.style, ...patch });
};

const fontZhModel = computed({
  get: () => props.style.fontZh,
  set: (v: string) => patchStyle({ fontZh: v }),
});

const titleSizeModel = computed({
  get: () => props.style.titleSizePt,
  set: (v: number) => patchStyle({ titleSizePt: v }),
});

const h1SizeModel = computed({
  get: () => props.style.h1SizePt,
  set: (v: number) => patchStyle({ h1SizePt: v }),
});

const h2SizeModel = computed({
  get: () => props.style.h2SizePt,
  set: (v: number) => patchStyle({ h2SizePt: v }),
});

const bodySizeModel = computed({
  get: () => props.style.bodySizePt,
  set: (v: number) => patchStyle({ bodySizePt: v }),
});

const lineSpacingModel = computed({
  get: () => props.style.lineSpacing,
  set: (v: number) => patchStyle({ lineSpacing: v }),
});

const onKeydown = (e: KeyboardEvent) => {
  if (!props.open) return;
  if (e.key === 'Escape') {
    close();
    return;
  }
  if (e.key === 'Tab' && dialogRef.value) {
    trapTabKey(e, dialogRef.value);
  }
};

watch(
  () => props.open,
  async (open) => {
    if (open) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKeydown);
      await nextTick();
      fontSelectRef.value?.focus?.();
      if (document.activeElement !== fontSelectRef.value) {
        dialogRef.value?.focus();
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

const resetToDefault = () => {
  patchStyle({
    fontZh: '微软雅黑',
    titleSizePt: 20,
    h1SizePt: 16,
    h2SizePt: 14,
    bodySizePt: 12,
    lineSpacing: 1.5,
    marginTopCm: 2.54,
    marginBottomCm: 2.54,
    marginLeftCm: 2.54,
    marginRightCm: 2.54,
  });
};
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
          ref="dialogRef"
          class="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="lesson-style-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2">
              <LucideIcon name="settings-2" :size="18" class="text-slate-500" />
              <h3 id="lesson-style-title" class="text-sm font-black text-slate-900 dark:text-white">
                {{ t('lesson.style.title') }}
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

          <div class="px-5 py-4 space-y-4 max-h-[min(70vh,640px)] overflow-y-auto custom-scrollbar">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.font') }}</div>
                <select
                  ref="fontSelectRef"
                  v-model="fontZhModel"
                  :disabled="props.loading"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                >
                  <option value="微软雅黑">微软雅黑</option>
                  <option value="宋体">宋体</option>
                  <option value="仿宋">仿宋</option>
                  <option value="黑体">黑体</option>
                </select>
              </label>

              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.line_spacing') }}</div>
                <input
                  v-model.number="lineSpacingModel"
                  :disabled="props.loading"
                  type="number"
                  min="1"
                  max="3"
                  step="0.1"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                />
              </label>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.title_size') }}</div>
                <input
                  v-model.number="titleSizeModel"
                  :disabled="props.loading"
                  type="number"
                  min="10"
                  max="60"
                  step="1"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                />
              </label>

              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.h1_size') }}</div>
                <input
                  v-model.number="h1SizeModel"
                  :disabled="props.loading"
                  type="number"
                  min="10"
                  max="48"
                  step="1"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                />
              </label>

              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.h2_size') }}</div>
                <input
                  v-model.number="h2SizeModel"
                  :disabled="props.loading"
                  type="number"
                  min="10"
                  max="40"
                  step="1"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                />
              </label>

              <label class="space-y-1.5">
                <div class="text-xs font-black text-slate-700 dark:text-slate-200">{{ t('lesson.style.body_size') }}</div>
                <input
                  v-model.number="bodySizeModel"
                  :disabled="props.loading"
                  type="number"
                  min="8"
                  max="32"
                  step="1"
                  class="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm font-bold text-slate-700 dark:text-slate-200 disabled:opacity-50"
                />
              </label>
            </div>

            <div class="flex items-center justify-end">
              <button
                type="button"
                class="px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-black text-xs hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                :disabled="props.loading"
                @click="resetToDefault"
              >
                {{ t('lesson.style.reset') }}
              </button>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button
              type="button"
              class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-black text-sm shadow-md transition-colors"
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
</style>
