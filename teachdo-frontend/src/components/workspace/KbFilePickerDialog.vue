<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { KBFile } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';

type FolderFilter = 'all' | 'upload' | 'generated';

interface Props {
  open: boolean;
  files: KBFile[];
  selectedIds: string[];
  restoreFocusEl: HTMLElement | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', selectedIds: string[]): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const dialogRef = ref<HTMLElement | null>(null);
const searchQuery = ref('');
const folderFilter = ref<FolderFilter>('all');
const draftSelected = ref<Set<string>>(new Set());

const close = () => emit('update:open', false);

const getFolderLabel = (folderId: number) => {
  if (folderId === 0) return t('kb.folder.upload');
  if (folderId === 1) return t('kb.folder.generated');
  return `${t('kb.folder.unknown')}(${folderId})`;
};

const readyFiles = computed(() => (props.files || []).filter((f) => f.status === 'ready'));

const filteredFiles = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  const filter = folderFilter.value;
  return readyFiles.value.filter((f) => {
    const folderId = typeof f.folderId === 'number' ? f.folderId : 0;
    if (filter === 'upload' && folderId !== 0) return false;
    if (filter === 'generated' && folderId !== 1) return false;
    if (!query) return true;
    return (f.name || '').toLowerCase().includes(query) || (f.id || '').toLowerCase().includes(query);
  });
});

const selectedCount = computed(() => draftSelected.value.size);

const toggleId = (id: string) => {
  const next = new Set(draftSelected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  draftSelected.value = next;
};

const selectAllFiltered = () => {
  const next = new Set(draftSelected.value);
  for (const f of filteredFiles.value) next.add(f.id);
  draftSelected.value = next;
};

const clearAll = () => {
  draftSelected.value = new Set();
};

const confirm = () => {
  emit('confirm', Array.from(draftSelected.value));
  close();
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
      draftSelected.value = new Set((props.selectedIds || []).filter(Boolean));
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
      <div v-if="props.open" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="close" />

        <div
          ref="dialogRef"
          class="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl outline-none td-modal-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="kb-picker-title"
          tabindex="-1"
          @click.stop
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200/60 dark:border-slate-800/60">
            <div class="flex items-center gap-2 min-w-0">
              <LucideIcon name="file" :size="18" class="text-slate-500" />
              <h3 id="kb-picker-title" class="text-sm font-black text-slate-900 dark:text-white truncate">
                {{ t('kb.picker.title') }}
              </h3>
              <span class="text-xs font-bold text-slate-400">
                {{ t('kb.picker.selected', { count: selectedCount }) }}
              </span>
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

          <div class="px-5 py-4 space-y-3 max-h-[min(70vh,720px)] overflow-y-auto custom-scrollbar">
            <div class="flex flex-col md:flex-row md:items-center gap-3">
              <div class="relative flex-1">
                <LucideIcon name="search" :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="t('kb.picker.search')"
                  class="w-full pl-9 pr-3 py-2 bg-white/70 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-indigo-400 dark:focus:border-indigo-700 rounded-xl text-sm outline-none transition-all"
                />
              </div>

              <div class="flex items-center gap-2">
                <select
                  v-model="folderFilter"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm text-slate-700 dark:text-slate-200 outline-none"
                >
                  <option value="all">{{ t('kb.picker.filter.all') }}</option>
                  <option value="upload">{{ t('kb.folder.upload') }}</option>
                  <option value="generated">{{ t('kb.folder.generated') }}</option>
                </select>

                <button
                  type="button"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm font-bold text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  @click="selectAllFiltered"
                >
                  {{ t('kb.picker.select_all') }}
                </button>

                <button
                  type="button"
                  class="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/30 text-sm font-bold text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  @click="clearAll"
                >
                  {{ t('kb.picker.clear') }}
                </button>
              </div>
            </div>

            <div class="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div class="grid grid-cols-12 gap-3 px-4 py-2 text-xs font-bold text-slate-400 uppercase tracking-wider bg-slate-50/60 dark:bg-slate-950/30">
                <div class="col-span-7">{{ t('kb.table.name') }}</div>
                <div class="col-span-3">{{ t('kb.picker.folder') }}</div>
                <div class="col-span-2 text-right">{{ t('kb.picker.action') }}</div>
              </div>

              <div class="max-h-[420px] overflow-y-auto custom-scrollbar divide-y divide-slate-100 dark:divide-slate-800">
                <div v-if="filteredFiles.length === 0" class="px-6 py-10 text-center text-sm text-slate-400">
                  {{ t('kb.picker.empty') }}
                </div>
                <button
                  v-for="file in filteredFiles"
                  :key="file.id"
                  type="button"
                  class="w-full grid grid-cols-12 gap-3 px-4 py-3 items-center text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  @click="toggleId(file.id)"
                >
                  <div class="col-span-7 min-w-0">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-900/25 text-indigo-600 dark:text-indigo-300 flex items-center justify-center border border-indigo-100 dark:border-indigo-800/40 flex-shrink-0">
                        <LucideIcon name="file" :size="16" />
                      </div>
                      <div class="min-w-0">
                        <div class="text-sm font-bold text-slate-800 dark:text-slate-200 truncate" :title="file.name || file.id">
                          {{ file.name || file.id }}
                        </div>
                        <div class="text-[11px] text-slate-400 truncate">{{ file.id }}</div>
                      </div>
                    </div>
                  </div>
                  <div class="col-span-3 text-xs font-bold text-slate-500 dark:text-slate-300">
                    {{ getFolderLabel(typeof file.folderId === 'number' ? file.folderId : 0) }}
                  </div>
                  <div class="col-span-2 flex items-center justify-end">
                    <input
                      type="checkbox"
                      class="h-4 w-4 accent-indigo-600"
                      :checked="draftSelected.has(file.id)"
                      :aria-label="t('kb.picker.toggle')"
                      @click.stop="toggleId(file.id)"
                    />
                  </div>
                </button>
              </div>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between gap-2 bg-slate-50/40 dark:bg-slate-950/20">
            <div class="text-xs text-slate-500 dark:text-slate-400">
              {{ t('kb.picker.ready_only') }}
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                @click="close"
              >
                {{ t('sidebar.cancel') }}
              </button>
              <button
                type="button"
                class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-colors"
                @click="confirm"
              >
                {{ t('kb.picker.confirm') }}
              </button>
            </div>
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
