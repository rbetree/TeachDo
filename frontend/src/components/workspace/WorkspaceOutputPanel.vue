<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';
import OutputFilesView from '@/components/workspace/OutputFilesView.vue';
import { isFullTextKbFileId } from '@/utils/kbFileId';

interface Props {
  currentMaterial: TeachingMaterial | null;
}

const props = defineProps<Props>();
const { t } = useI18n();

const ui = useWorkspaceUiStore();

const collapsed = computed(() => ui.outputPanelCollapsed);

const outputFilesRef = ref<InstanceType<typeof OutputFilesView> | null>(null);

const normalizeStringArray = (raw: unknown): string[] => {
  if (!Array.isArray(raw)) return [];
  const result: string[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    const id = typeof item === 'string' ? item.trim() : '';
    if (!id) continue;
    if (seen.has(id)) continue;
    seen.add(id);
    result.push(id);
  }
  return result;
};

const selectedFullCount = computed(() => normalizeStringArray(props.currentMaterial?.kbFileIds).filter(isFullTextKbFileId).length);
const artifactsLoading = computed(() => outputFilesRef.value?.loadingArtifacts ?? false);

const handleClearSelectedFull = () => {
  outputFilesRef.value?.clearSelectedFull?.();
};

const handleRefreshArtifacts = () => {
  void outputFilesRef.value?.refreshArtifacts?.();
};

const panelWidthClass = computed(() => (collapsed.value ? 'w-[360px] md:w-14' : 'w-[360px]'));
const panelPositionClass = 'fixed top-16 right-0 bottom-0 z-50 shadow-2xl md:static md:shadow-none';
const panelTransformClass = computed(() => (collapsed.value ? 'translate-x-full md:translate-x-0' : 'translate-x-0'));

onMounted(() => {
  if (typeof window === 'undefined') return;
  if (window.matchMedia('(max-width: 767px)').matches) {
    ui.closeOutputPanel();
  }
});
</script>

<template>
  <div
    v-if="!collapsed"
    class="fixed inset-0 top-16 bg-slate-900/60 backdrop-blur-sm z-40 md:hidden"
    @click="ui.closeOutputPanel()"
  ></div>
  <aside
    class="h-full shrink-0 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col overflow-hidden transition-transform duration-300"
    :class="[panelWidthClass, panelPositionClass, panelTransformClass]"
  >
    <div class="border-b border-slate-100 dark:border-slate-800">
      <div v-if="collapsed" class="p-2 flex flex-col items-center gap-2">
        <button
          type="button"
          class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
          :aria-label="t('common.expand')"
          @click="ui.toggleOutputPanel()"
        >
          <LucideIcon name="arrow-left" class="w-5 h-5" />
        </button>

        <div
          class="p-2 rounded-lg border border-transparent text-slate-500 dark:text-slate-300 flex items-center justify-center w-full"
          :title="t('workspace.outputs.title')"
        >
          <LucideIcon name="book-open" class="w-5 h-5" />
        </div>
      </div>

      <div v-else class="p-3">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <div class="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 flex items-center justify-center border border-emerald-100 dark:border-emerald-800/40 shrink-0">
              <LucideIcon name="book-open" class="w-5 h-5" />
            </div>
            <div class="min-w-0">
              <div class="text-sm font-extrabold text-slate-800 dark:text-slate-100 truncate">
                {{ t('workspace.outputs.title') }}
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                {{ t('workspace.outputs.subtitle') }}
              </div>
            </div>
          </div>

          <div class="flex items-center gap-1 shrink-0">
            <button
              type="button"
              class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors disabled:opacity-40"
              :aria-label="t('kb.action.refresh')"
              :title="t('kb.action.refresh')"
              :disabled="artifactsLoading"
              @click="handleRefreshArtifacts"
            >
              <LucideIcon name="refresh-cw" class="w-4 h-4" :class="artifactsLoading ? 'animate-spin' : ''" />
            </button>

            <button
              type="button"
              class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
              :aria-label="t('common.collapse')"
              @click="ui.toggleOutputPanel()"
            >
              <LucideIcon name="arrow-right" class="w-5 h-5" />
            </button>
          </div>
        </div>

        <div v-if="props.currentMaterial" class="mt-3 flex items-center justify-between gap-2">
          <div class="text-[11px] font-bold text-slate-500 dark:text-slate-400">
            {{ t('kb.picker.selected', { count: selectedFullCount }) }}
          </div>
          <button
            type="button"
            class="px-2 py-1 rounded-lg text-[11px] font-bold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
            :disabled="selectedFullCount === 0"
            @click="handleClearSelectedFull"
          >
            {{ t('kb.picker.clear') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="!collapsed" class="flex-1 min-h-0 overflow-hidden">
      <OutputFilesView v-if="props.currentMaterial" ref="outputFilesRef" :current-material="props.currentMaterial" />
      <div v-else class="px-4 pt-4 text-xs text-slate-500 dark:text-slate-400">
        {{ t('workspace.no_course') }}
      </div>
    </div>
  </aside>
</template>
