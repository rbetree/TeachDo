<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { KBFile, TeachingMaterial } from '#root/types';
import KbFilePickerDialog from '@/components/workspace/KbFilePickerDialog.vue';

interface Props {
  open: boolean;
  kbFiles: KBFile[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'create', material: TeachingMaterial): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);
const restoreFocusEl = ref<HTMLElement | null>(null);

const form = reactive({
  title: '',
  subject: '',
  description: '',
  objectives: '',
});

const pickerOpen = ref(false);
const pickerRestoreFocusEl = ref<HTMLElement | null>(null);
const selectedKbFileIds = ref<string[]>([]);

const close = () => emit('update:open', false);

const resetForm = () => {
  form.title = '';
  form.subject = '';
  form.description = '';
  form.objectives = '';
  selectedKbFileIds.value = [];
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
    kbFileIds: [...selectedKbFileIds.value],
    outlineContent: '',
  };
  emit('create', material);
};

const openPicker = () => {
  pickerRestoreFocusEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  pickerOpen.value = true;
};

const onPickerConfirm = (ids: string[]) => {
  selectedKbFileIds.value = ids;
};

const onKeydown = (e: KeyboardEvent) => {
  if (e.key !== 'Escape') return;
  if (!props.open) return;
  close();
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
      dialogRef.value?.focus();
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
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="close" />

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
            <div class="rounded-xl border border-amber-200/70 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/20 p-3 text-xs text-amber-800 dark:text-amber-100 leading-relaxed">
              <div class="flex items-start gap-2">
                <LucideIcon name="info" :size="16" class="mt-0.5 text-amber-600 dark:text-amber-300" />
                <div>
                  <div class="font-bold">{{ t('material.create.tip_title') }}</div>
                  <div class="mt-0.5">
                    {{ t('material.create.tip_desc') }}
                  </div>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="space-y-2 text-left">
                <span class="block text-xs font-bold uppercase tracking-widest text-slate-500">
                  {{ t('material.form.title') }}
                </span>
                <input
                  v-model="form.title"
                  type="text"
                  class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                  class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
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
                class="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                :placeholder="t('material.form.objectives_placeholder')"
              ></textarea>
            </label>

            <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 p-3">
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="text-sm font-bold text-slate-700 dark:text-slate-200">{{ t('material.form.kb_files') }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {{ t('material.form.kb_files_desc', { count: selectedKbFileIds.length }) }}
                  </div>
                </div>
                <button
                  type="button"
                  class="px-3 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-200 font-bold text-xs hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors"
                  @click="openPicker"
                >
                  {{ t('kb.picker.open') }}
                </button>
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button
              type="button"
              class="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              @click="close"
            >
              {{ t('sidebar.cancel') }}
            </button>
            <button
              type="button"
              class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-colors disabled:bg-slate-300 disabled:text-slate-500"
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

  <KbFilePickerDialog
    :open="pickerOpen"
    :files="props.kbFiles"
    :selected-ids="selectedKbFileIds"
    :restore-focus-el="pickerRestoreFocusEl"
    @update:open="(v) => (pickerOpen = v)"
    @confirm="onPickerConfirm"
  />
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

