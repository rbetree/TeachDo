<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';

interface Props {
  currentMaterial: TeachingMaterial | null;
}

const props = defineProps<Props>();
const { t } = useI18n();

const ui = useWorkspaceUiStore();

const collapsed = computed(() => ui.outputPanelCollapsed);

const panelWidthClass = computed(() => (collapsed.value ? 'w-14' : 'w-[360px]'));
const panelPositionClass = computed(() => (collapsed.value ? '' : 'fixed top-16 right-0 bottom-0 z-50 shadow-2xl md:static md:shadow-none'));

onMounted(() => {
  if (typeof window === 'undefined') return;
  if (window.matchMedia('(max-width: 767px)').matches) {
    ui.collapseOutputPanel();
  }
});
</script>

<template>
  <div
    v-if="!collapsed"
    class="fixed inset-0 top-16 bg-slate-900/60 backdrop-blur-sm z-40 md:hidden"
    @click="ui.collapseOutputPanel()"
  ></div>
  <aside
    class="h-full shrink-0 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col overflow-hidden"
    :class="[panelWidthClass, panelPositionClass]"
  >
    <div class="border-b border-slate-100 dark:border-slate-800">
      <div v-if="collapsed" class="p-2 flex flex-col items-center gap-2">
        <button
          type="button"
          class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
          :aria-label="t('common.expand')"
          @click="ui.toggleOutputPanelCollapsed()"
        >
          <LucideIcon name="arrow-left" class="w-5 h-5" />
        </button>

        <div
          class="p-2 rounded-lg border border-transparent text-slate-500 dark:text-slate-300 flex items-center justify-center w-full"
          :title="t('workspace.outputs.title')"
        >
          <LucideIcon name="file" class="w-5 h-5" />
        </div>
      </div>

      <div v-else class="flex items-center justify-between gap-2 p-2">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 flex items-center justify-center border border-emerald-100 dark:border-emerald-800/40 shrink-0">
            <LucideIcon name="file" class="w-5 h-5" />
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

        <button
          type="button"
          class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
          :aria-label="t('common.collapse')"
          @click="ui.toggleOutputPanelCollapsed()"
        >
          <LucideIcon name="arrow-right" class="w-5 h-5" />
        </button>
      </div>
    </div>

    <div v-if="!collapsed" class="flex-1 min-h-0 overflow-auto p-4">
      <div v-if="!props.currentMaterial" class="text-xs text-slate-500 dark:text-slate-400">
        {{ t('workspace.no_course') }}
      </div>
      <div v-else class="h-full flex flex-col items-center justify-center text-center gap-2 text-slate-500 dark:text-slate-400">
        <div class="text-sm font-bold text-slate-600 dark:text-slate-200">{{ t('workspace.outputs.empty_title') }}</div>
        <div class="text-xs leading-relaxed max-w-[22rem]">{{ t('workspace.outputs.empty_desc') }}</div>
      </div>
    </div>
  </aside>
</template>
