<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { TeachingMaterial } from '#root/types';
import { trapTabKey } from '@/utils/focusTrap';

interface Props {
  open: boolean;
  material: TeachingMaterial;
  relatedKbCount: number;
  loading?: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', payload: { deleteKbFiles: boolean }): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);
const cancelButtonRef = ref<HTMLButtonElement | null>(null);
const restoreFocusEl = ref<HTMLElement | null>(null);

const deleteKbFiles = ref(false);
const kbOptionDesc = computed(() =>
  props.relatedKbCount > 0
    ? t('material.delete.kb_option_desc', { count: props.relatedKbCount })
    : t('material.delete.kb_option_desc_unknown'),
);

const close = () => {
  if (props.loading) return;
  emit('update:open', false);
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

const onConfirm = () => {
  if (props.loading) return;
  emit('confirm', { deleteKbFiles: deleteKbFiles.value });
};

watch(
  () => props.open,
  async (open) => {
    if (open) {
      restoreFocusEl.value = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      deleteKbFiles.value = false;
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', onKeydown);
      await nextTick();
      cancelButtonRef.value?.focus?.();
      if (document.activeElement !== cancelButtonRef.value) {
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
          class="relative w-full max-w-xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="material-delete-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2">
              <LucideIcon name="trash-2" :size="18" class="text-red-500" />
              <h3 id="material-delete-title" class="text-sm font-black text-slate-900 dark:text-white">
                {{ t('material.delete.title') }}
              </h3>
            </div>
            <button
              type="button"
              class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
              :aria-label="t('common.close')"
              :disabled="props.loading"
              @click="close"
            >
              <LucideIcon name="x" :size="18" />
            </button>
          </div>

          <div class="px-5 py-4 space-y-4">
            <div class="rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50/60 dark:bg-red-950/20 p-4 text-sm text-red-700 dark:text-red-200">
              {{ t('material.delete.desc', { title: props.material.title }) }}
            </div>

            <label class="flex items-start gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 p-4">
              <input
                v-model="deleteKbFiles"
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                :disabled="props.loading"
              />
              <div class="min-w-0">
                <div class="text-sm font-bold text-slate-800 dark:text-slate-100">
                  {{ t('material.delete.kb_option') }}
                </div>
                <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {{ kbOptionDesc }}
                </div>
              </div>
            </label>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-end gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <button
              ref="cancelButtonRef"
              type="button"
              class="td-btn-secondary disabled:opacity-50"
              :disabled="props.loading"
              @click="close"
            >
              {{ t('sidebar.cancel') }}
            </button>
            <button
              type="button"
              class="td-btn-danger"
              :disabled="props.loading"
              @click="onConfirm"
            >
              <LucideIcon :name="props.loading ? 'loader-2' : 'trash-2'" class="w-4 h-4" :class="{ 'animate-spin': props.loading }" />
              {{ t('material.delete.confirm') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
