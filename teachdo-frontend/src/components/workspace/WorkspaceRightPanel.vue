<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { CourseGroup, CourseUnit } from '#root/types';
import LucideIcon from '@/components/common/LucideIcon.vue';
import KnowledgeBaseView from '@/components/workspace/KnowledgeBaseView.vue';
import AssistantView from '@/components/workspace/AssistantView.vue';
import { useWorkspaceUiStore } from '@/stores/workspaceUiStore';

interface Props {
  currentCourse: CourseGroup;
  currentUnit: CourseUnit | null;
}

interface Emits {
  (e: 'updateCourse', updates: Partial<CourseGroup>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const ui = useWorkspaceUiStore();

const collapsed = computed(() => ui.rightPanelCollapsed);
const activeTab = computed(() => ui.rightPanelTab);

const panelWidthClass = computed(() => (collapsed.value ? 'w-14' : 'w-[360px]'));
</script>

<template>
  <aside
    class="h-full border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col overflow-hidden"
    :class="panelWidthClass"
  >
    <div class="border-b border-slate-100 dark:border-slate-800">
      <div v-if="collapsed" class="p-2 flex flex-col items-center gap-2">
        <button
          type="button"
          class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
          :aria-label="t('common.expand')"
          @click="ui.toggleRightPanelCollapsed()"
        >
          <LucideIcon name="arrow-left" class="w-5 h-5" />
        </button>

        <button
          type="button"
          class="p-2 rounded-lg border transition-colors flex items-center justify-center w-full"
          :class="activeTab === 'kb'
            ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300'
            : 'bg-transparent border-transparent text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'"
          :aria-label="t('sidebar.kb')"
          :title="t('sidebar.kb')"
          @click="ui.setRightPanelTab('kb')"
        >
          <LucideIcon name="database" class="w-5 h-5" />
        </button>

        <button
          type="button"
          class="p-2 rounded-lg border transition-colors flex items-center justify-center w-full"
          :class="activeTab === 'assistant'
            ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300'
            : 'bg-transparent border-transparent text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'"
          :aria-label="t('sidebar.assistant')"
          :title="t('sidebar.assistant')"
          @click="ui.setRightPanelTab('assistant')"
        >
          <LucideIcon name="message-square" class="w-5 h-5" />
        </button>
      </div>

      <div v-else class="flex items-center justify-between gap-2 p-2">
        <div class="flex items-center gap-2 min-w-0">
          <button
            type="button"
            class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300"
            :aria-label="t('common.collapse')"
            @click="ui.toggleRightPanelCollapsed()"
          >
            <LucideIcon name="arrow-right" class="w-5 h-5" />
          </button>
          <div class="text-xs font-bold text-slate-400 uppercase tracking-wider truncate">
            {{ t('sidebar.modules') }}
          </div>
        </div>

        <div class="flex items-center gap-1">
          <button
            type="button"
            class="px-2.5 py-2 rounded-lg border transition-colors flex items-center gap-2"
            :class="activeTab === 'kb'
              ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300'
              : 'bg-transparent border-transparent text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="ui.setRightPanelTab('kb')"
          >
            <LucideIcon name="database" class="w-4 h-4" />
            <span class="text-sm font-bold">{{ t('sidebar.kb') }}</span>
          </button>

          <button
            type="button"
            class="px-2.5 py-2 rounded-lg border transition-colors flex items-center gap-2"
            :class="activeTab === 'assistant'
              ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300'
              : 'bg-transparent border-transparent text-slate-500 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="ui.setRightPanelTab('assistant')"
          >
            <LucideIcon name="message-square" class="w-4 h-4" />
            <span class="text-sm font-bold">{{ t('sidebar.assistant') }}</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="!collapsed" class="flex-1 min-h-0 overflow-hidden p-3">
      <div class="h-full overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/40">
        <div class="h-full overflow-hidden">
          <KnowledgeBaseView
            v-if="activeTab === 'kb'"
            :current-course="props.currentCourse"
            variant="panel"
            @update-course="(updates) => emit('updateCourse', updates)"
          />
          <AssistantView
            v-else
            :current-course="props.currentCourse"
            :current-unit="props.currentUnit"
            variant="panel"
            @update-course="(updates) => emit('updateCourse', updates)"
          />
        </div>
      </div>
    </div>
  </aside>
</template>
