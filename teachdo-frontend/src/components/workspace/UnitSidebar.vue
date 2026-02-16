<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { CourseGroup } from '#root/types';

const props = defineProps<{
  course: CourseGroup;
  activeUnitId: string | null;
  collapsed: boolean;
  mobileOpen: boolean;
}>();

const emit = defineEmits<{
  (event: 'select-unit', unitId: string): void;
  (event: 'add-unit', payload: { title: string; objectives: string }): void;
  (event: 'toggle-collapse'): void;
  (event: 'close-mobile'): void;
}>();

const { t } = useI18n();

const isCreatingUnit = ref(false);
const newUnitTitle = ref('');
const newUnitObjectives = ref('');

const isUnitActive = (unitId: string) => props.activeUnitId === unitId;

const handleSelectUnit = (unitId: string) => {
  emit('select-unit', unitId);
  if (props.mobileOpen) emit('close-mobile');
};

const handleCreateUnit = () => {
  const title = newUnitTitle.value.trim();
  const objectives = newUnitObjectives.value.trim();
  if (!title || !objectives) return;

  emit('add-unit', { title, objectives });
  newUnitTitle.value = '';
  newUnitObjectives.value = '';
  isCreatingUnit.value = false;
};

const handleOpenCreation = () => {
  if (props.collapsed) {
    emit('toggle-collapse');
  }
  isCreatingUnit.value = true;
};

const baseSidebarClasses = computed(() => [
  'workspace-sidebar',
  'fixed md:static top-0 left-0 bottom-0 md:h-full w-72',
  'flex flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl md:shadow-2xl z-50 md:z-20',
  'transition-transform duration-300',
  props.mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
  props.collapsed ? 'md:w-20' : 'md:w-72',
]);
</script>

<template>
  <div>
    <div
      v-if="mobileOpen"
      class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 md:hidden"
      @click="emit('close-mobile')"
    ></div>

    <aside :class="baseSidebarClasses">
      <div class="flex-1 flex flex-col">
        <div
          class="border-b border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 transition-all duration-300"
          :class="collapsed ? 'p-3 flex justify-center' : 'p-5'"
        >
          <template v-if="!collapsed">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <h1 class="text-lg font-black text-slate-800 dark:text-white leading-tight truncate" :title="course.name">
                  {{ course.name }}
                </h1>
                <span class="text-[10px] font-bold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 uppercase tracking-widest mt-2 inline-block">
                  {{ course.subject }}
                </span>
              </div>
              <button class="md:hidden text-slate-400 hover:text-slate-600" type="button" @click="emit('close-mobile')">
                <LucideIcon name="x" class="w-5 h-5" />
              </button>
            </div>
          </template>
          <template v-else>
            <div class="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-md" :title="course.name">
              {{ course.name.substring(0, 1).toUpperCase() }}
            </div>
          </template>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar space-y-3" :class="collapsed ? 'p-2' : 'p-4'">
          <div v-if="!collapsed" class="px-1 py-1 flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>{{ t('sidebar.units') }}</span>
            <button
              type="button"
              class="p-1.5 rounded-md text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-slate-800 transition-colors"
              @click="handleOpenCreation"
            >
              <LucideIcon name="plus" class="w-4 h-4" />
            </button>
          </div>
          <div v-else class="flex justify-center mb-2">
            <button
              type="button"
              class="p-1.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-400 hover:text-indigo-600"
              @click="handleOpenCreation"
            >
              <LucideIcon name="plus" class="w-4 h-4" />
            </button>
          </div>

          <div v-for="(unit, index) in course.units" :key="unit.id">
            <button
              type="button"
              class="w-full group text-left rounded-xl border transition-all duration-200 relative overflow-hidden"
              :class="[
                collapsed ? 'p-2 flex justify-center' : 'p-3.5 transform hover:scale-[1.01]',
                isUnitActive(unit.id)
                  ? 'bg-indigo-600 border-indigo-500 shadow-lg shadow-indigo-500/20 text-white'
                  : 'bg-white dark:bg-slate-800/40 border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800 hover:border-indigo-200 dark:hover:border-slate-700 text-slate-600 dark:text-slate-300',
              ]"
              :title="collapsed ? unit.title : ''"
              @click="handleSelectUnit(unit.id)"
            >
              <template v-if="collapsed">
                <div class="flex flex-col items-center gap-1">
                  <span
                    class="text-xs font-mono font-bold"
                    :class="isUnitActive(unit.id) ? 'text-indigo-200' : 'text-slate-400'"
                  >
                    {{ (index + 1).toString().padStart(2, '0') }}
                  </span>
                  <div class="flex gap-0.5">
                    <span
                      class="w-1 h-1 rounded-full"
                      :class="unit.outlineContent ? 'bg-emerald-400' : 'bg-slate-300'"
                    />
                    <span
                      class="w-1 h-1 rounded-full"
                      :class="unit.lessonPlan ? 'bg-emerald-400' : 'bg-slate-300'"
                    />
                    <span
                      class="w-1 h-1 rounded-full"
                      :class="unit.presentation ? 'bg-emerald-400' : 'bg-slate-300'"
                    />
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="flex items-start justify-between gap-3">
                  <div class="flex items-start gap-3 w-full min-w-0">
                    <span
                      class="text-xs font-mono font-bold mt-0.5"
                      :class="isUnitActive(unit.id) ? 'text-indigo-200' : 'text-slate-400'"
                    >
                      {{ (index + 1).toString().padStart(2, '0') }}
                    </span>
                    <div class="min-w-0 flex-1">
                      <p
                        class="font-semibold text-sm leading-tight truncate mb-2"
                        :class="isUnitActive(unit.id) ? 'text-white' : 'text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400'"
                      >
                        {{ unit.title }}
                      </p>
                      <div class="flex items-center gap-2">
                        <div
                          class="flex items-center gap-1.5 px-1.5 py-0.5 rounded"
                          :class="isUnitActive(unit.id) ? 'bg-indigo-700/40' : 'bg-slate-100 dark:bg-slate-800'"
                        >
                          <span
                            class="text-[9px] uppercase font-bold"
                            :class="isUnitActive(unit.id) ? 'text-indigo-100' : 'text-slate-400'"
                          >
                            {{ t('sidebar.assets') }}
                          </span>
                          <div class="flex gap-1">
                            <span
                              class="w-1.5 h-1.5 rounded-full"
                              :class="unit.outlineContent ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                            />
                            <span
                              class="w-1.5 h-1.5 rounded-full"
                              :class="unit.lessonPlan ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                            />
                            <span
                              class="w-1.5 h-1.5 rounded-full"
                              :class="unit.presentation ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </button>
          </div>

          <div
            v-if="isCreatingUnit && !collapsed"
            class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border-2 border-dashed border-indigo-300 dark:border-indigo-700/40"
          >
            <input
              v-model="newUnitTitle"
              type="text"
              class="w-full bg-transparent text-sm font-medium outline-none mb-2 text-slate-900 dark:text-white placeholder-slate-400"
              :placeholder="t('sidebar.unit_placeholder')"
              @keyup.enter="handleCreateUnit"
            />
            <textarea
              v-model="newUnitObjectives"
              rows="3"
              class="w-full bg-transparent text-sm font-medium outline-none mb-3 text-slate-900 dark:text-white placeholder-slate-400 resize-none"
              :placeholder="t('sidebar.unit_objectives_placeholder')"
            />
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:text-slate-500 text-white text-xs py-1.5 rounded-md font-medium transition-colors"
                :disabled="!newUnitTitle.trim() || !newUnitObjectives.trim()"
                @click="handleCreateUnit"
              >
                {{ t('sidebar.add_unit') }}
              </button>
              <button
                type="button"
                class="flex-1 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 text-xs py-1.5 rounded-md font-medium transition-colors"
                @click="isCreatingUnit = false"
              >
                {{ t('sidebar.cancel') }}
              </button>
            </div>
          </div>

          <div
            v-if="!course.units.length && !isCreatingUnit && !collapsed"
            class="text-center py-8 px-4 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-400"
          >
            <p class="mb-3">{{ t('sidebar.no_units') }}</p>
            <button type="button" class="font-bold text-indigo-600 dark:text-indigo-400 hover:underline" @click="handleOpenCreation">
              {{ t('sidebar.create_first_unit') }}
            </button>
          </div>
        </div>
      </div>

      <button
        class="hidden md:flex mt-auto w-full p-3 items-center justify-center border-t border-slate-200 dark:border-slate-800 text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-indigo-600 transition-colors"
        type="button"
        @click="emit('toggle-collapse')"
      >
        <LucideIcon :name="collapsed ? 'panel-left-open' : 'panel-left-close'" class="w-5 h-5" />
      </button>
    </aside>
  </div>
</template>
