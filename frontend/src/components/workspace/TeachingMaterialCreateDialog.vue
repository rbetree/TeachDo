<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { TeachingMaterial } from '#root/types';
import { trapTabKey } from '@/utils/focusTrap';

interface Props {
  open: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'create', material: TeachingMaterial): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);
const titleInputRef = ref<HTMLInputElement | null>(null);
const restoreFocusEl = ref<HTMLElement | null>(null);

const form = reactive({
  title: '',
  subject: '',
  description: '',
  objectives: '',
});

const close = () => emit('update:open', false);

const resetForm = () => {
  form.title = '';
  form.subject = '';
  form.description = '';
  form.objectives = '';
};

const creationDisabled = computed(() => !form.title.trim() || !form.subject.trim() || !form.objectives.trim());

const handleCreate = () => {
  if (creationDisabled.value) return;
  const now = new Date();
  const material: TeachingMaterial = {
    id: `material-${Date.now()}`,
    title: form.title.trim(),
    subject: form.subject.trim(),
    description: form.description.trim(),
    objectives: form.objectives.trim(),
    createdAt: now,
    kbFileIds: [],
    outlineContent: '',
  };
  emit('create', material);
};

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
      restoreFocusEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      resetForm();
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKeydown);
      await nextTick();
      titleInputRef.value?.focus?.();
      if (document.activeElement !== titleInputRef.value) {
        dialogRef.value?.focus();
      }
      return;
    }

    document.body.style.overflow = '';
    document.removeEventListener('keydown', onKeydown);
    await nextTick();
    const el = restoreFocusEl.value;
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
      <div v-if="props.open" class="fixed inset-0 z-[55] flex items-center justify-center p-4">
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
          aria-labelledby="material-create-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2">
              <LucideIcon name="plus" :size="18" class="text-slate-500" />
              <h3 id="material-create-title" class="text-sm font-black text-slate-900 dark:text-white">
                {{ t('material.create.title') }}
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

          <div class="px-5 py-4 space-y-4 max-h-[min(70vh,680px)] overflow-y-auto custom-scrollbar">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="space-y-2 text-left">
                <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                  {{ t('material.form.title') }}
                </span>
                <input
                  ref="titleInputRef"
                  v-model="form.title"
                  type="text"
                  class="td-input"
                  :placeholder="t('material.form.title_placeholder')"
                />
              </label>

              <label class="space-y-2 text-left">
                <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                  {{ t('material.form.subject') }}
                </span>
                <input
                  v-model="form.subject"
                  type="text"
                  class="td-input"
                  :placeholder="t('material.form.subject_placeholder')"
                />
              </label>
            </div>

            <label class="space-y-2 text-left">
              <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                {{ t('material.form.description') }}
              </span>
              <textarea
                v-model="form.description"
                rows="2"
                class="td-input resize-none"
                :placeholder="t('material.form.description_placeholder')"
              ></textarea>
            </label>

            <label class="space-y-2 text-left">
              <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                {{ t('material.form.objectives') }}
              </span>
              <textarea
                v-model="form.objectives"
                rows="4"
                class="td-input resize-none"
                :placeholder="t('material.form.objectives_placeholder')"
              ></textarea>
            </label>

            <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 p-3">
              <div class="flex items-start gap-3">
                <div class="w-9 h-9 rounded-xl bg-indigo-50 dark:bg-indigo-900/25 text-indigo-600 dark:text-indigo-300 flex items-center justify-center border border-indigo-100 dark:border-indigo-800/40 flex-shrink-0">
                  <LucideIcon name="database" :size="18" />
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('material.form.kb_files') }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                    {{ t('material.form.kb_files_sidebar_tip') }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button
              type="button"
              class="td-btn-secondary"
              @click="close"
            >
              {{ t('sidebar.cancel') }}
            </button>
            <button
              type="button"
              class="td-btn-primary"
              :disabled="creationDisabled"
              @click="handleCreate"
            >
              {{ t('material.create.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
