<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonDocxTemplate } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { trapTabKey } from '@/utils/focusTrap';

interface Props {
  open: boolean;
  loading: boolean;
  templates: LessonDocxTemplate[];
  selectedTemplateId: string;
  restoreFocusEl: HTMLElement | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'update:selectedTemplateId', value: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);

const close = () => emit('update:open', false);
const selectTemplate = (id: string) => emit('update:selectedTemplateId', id);

const selected = computed(() => props.templates.find((x) => x.id === props.selectedTemplateId) ?? null);

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
      dialogRef.value?.focus();
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
          ref="dialogRef"
          class="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="lesson-template-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2 min-w-0">
              <LucideIcon name="layout-grid" :size="18" class="text-slate-500" />
              <div class="min-w-0">
                <h3 id="lesson-template-title" class="text-sm font-black text-slate-900 dark:text-white">
                  {{ t('lesson.template.title') }}
                </h3>
                <p class="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {{ selected?.name ? `${t('lesson.template.current')}：${selected.name}` : t('lesson.template.hint') }}
                </p>
              </div>
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
            <div v-if="props.loading" class="flex items-center justify-center py-10 text-slate-500 dark:text-slate-300">
              <LucideIcon name="loader-2" :size="18" class="animate-spin mr-2" />
              <span class="text-sm font-bold">{{ t('common.loading') }}</span>
            </div>

            <div v-else-if="!props.templates.length" class="py-10 text-center text-slate-500 dark:text-slate-400">
              <p class="text-sm font-bold">{{ t('lesson.template.empty') }}</p>
            </div>

            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <button
                v-for="template in props.templates"
                :key="template.id"
                type="button"
                :aria-pressed="props.selectedTemplateId === template.id"
                :class="[
                  'group relative rounded-xl overflow-hidden border-2 transition-colors transition-transform duration-200 text-left disabled:opacity-60 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 focus-visible:outline-offset-2',
                  props.selectedTemplateId === template.id
                    ? 'border-indigo-500 ring-4 ring-indigo-500/20 scale-[1.02]'
                    : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300',
                ]"
                @click="selectTemplate(template.id)"
              >
                <div v-if="template.coverUrl" class="h-28 w-full bg-slate-100 overflow-hidden">
                  <img
                    :src="template.coverUrl"
                    width="640"
                    height="224"
                    loading="lazy"
                    decoding="async"
                    class="h-full w-full object-cover group-hover:scale-110 transition-transform duration-500"
                    :alt="template.name"
                  />
                </div>
                <div v-else :class="['h-28 w-full flex items-center justify-center', template.thumbnailColor]">
                  <span class="text-white font-bold opacity-80 text-lg">Aa</span>
                </div>
                <div class="p-4 bg-white dark:bg-slate-900">
                  <h4 class="font-bold text-slate-800 dark:text-white">{{ template.name }}</h4>
                  <p class="text-xs text-slate-500 mt-1">{{ template.styleDescription }}</p>
                </div>
                <div v-if="props.selectedTemplateId === template.id" class="absolute top-2 right-2 bg-indigo-500 text-white rounded-full p-1 shadow-lg">
                  <LucideIcon name="check" :size="16" />
                </div>
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

