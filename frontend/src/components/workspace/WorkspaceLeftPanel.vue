<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import KnowledgeBaseView from '@/components/workspace/KnowledgeBaseView.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';

interface Props {
  currentMaterial: TeachingMaterial | null;
}

const props = defineProps<Props>();
const { t } = useI18n();

const ui = useWorkspaceUiStore();

const collapsed = computed(() => ui.rightPanelCollapsed);

const panelWidthClass = computed(() => (collapsed.value ? 'w-14' : 'w-[360px]'));
const panelPositionClass = computed(() => (collapsed.value ? '' : 'fixed top-16 left-0 bottom-0 z-50 shadow-2xl md:static md:shadow-none'));

onMounted(() => {
  if (typeof window === 'undefined') return;
  if (window.matchMedia('(max-width: 767px)').matches) {
    ui.collapseRightPanel();
  }
});
</script>

<template>
  <div
    v-if="!collapsed"
    class="fixed inset-0 top-16 bg-slate-900/60 backdrop-blur-sm z-40 md:hidden"
    @click="ui.collapseRightPanel()"
  ></div>
  <aside
    class="h-full shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col overflow-hidden"
    :class="[panelWidthClass, panelPositionClass]"
  >
    <div class="border-b border-slate-100 dark:border-slate-800">
      <div v-if="collapsed" class="p-2 flex flex-col items-center gap-2">
        <button
          type="button"
          class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
          :aria-label="t('common.expand')"
          @click="ui.toggleRightPanelCollapsed()"
        >
          <LucideIcon name="arrow-right" class="w-5 h-5" />
        </button>

        <div
          class="p-2 rounded-lg border border-transparent text-slate-500 dark:text-slate-300 flex items-center justify-center w-full"
          :title="t('workspace.references.title')"
        >
          <LucideIcon name="database" class="w-5 h-5" />
        </div>
      </div>

      <div v-else class="flex items-center justify-between gap-2 p-2">
        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
            :aria-label="t('common.collapse')"
            @click="ui.toggleRightPanelCollapsed()"
          >
            <LucideIcon name="arrow-left" class="w-5 h-5" />
          </button>
          <div class="text-xs font-bold text-slate-400 uppercase tracking-wider truncate">
            {{ t('workspace.references.title') }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="!collapsed" class="flex-1 min-h-0 overflow-hidden">
      <KnowledgeBaseView variant="panel" :current-material="props.currentMaterial" source-filter="uploaded" />
    </div>
  </aside>
</template>
