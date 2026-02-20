<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';
import type { TeachingMaterial } from '#root/types';

const props = defineProps<{
  materials: TeachingMaterial[];
  activeMaterialId: string | null;
  collapsed: boolean;
  mobileOpen: boolean;
}>();

const emit = defineEmits<{
  (event: 'select-material', materialId: string): void;
  (event: 'open-create'): void;
  (event: 'toggle-collapse'): void;
  (event: 'close-mobile'): void;
}>();

const { t } = useI18n();

const isActive = (materialId: string) => props.activeMaterialId === materialId;

const handleSelect = (materialId: string) => {
  emit('select-material', materialId);
  if (props.mobileOpen) emit('close-mobile');
};

const handleOpenCreate = () => {
  if (props.collapsed) emit('toggle-collapse');
  emit('open-create');
};

const baseSidebarClasses = computed(() => [
  'workspace-sidebar',
  'fixed md:static top-0 left-0 bottom-0 md:h-full w-72',
  'flex flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl md:shadow-2xl z-50 md:z-20',
  'transition-transform duration-300',
  props.mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
  props.collapsed ? 'md:w-20' : 'md:w-72',
]);

const headerMaterial = computed(() => props.materials.find((m) => m.id === props.activeMaterialId) ?? null);
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
	          class="border-b border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-800/30 transition-[padding] duration-300"
	          :class="collapsed ? 'p-3 flex justify-center' : 'p-5'"
	        >
          <template v-if="!collapsed">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <h1 class="text-lg font-black text-slate-800 dark:text-white leading-tight truncate" :title="headerMaterial?.title || ''">
                  {{ headerMaterial?.title || t('nav.workspace') }}
                </h1>
                <span class="text-[10px] font-bold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 uppercase tracking-widest mt-2 inline-block">
                  {{ headerMaterial?.subject || t('sidebar.materials') }}
                </span>
              </div>
              <button class="md:hidden text-slate-400 hover:text-slate-600" type="button" @click="emit('close-mobile')">
                <LucideIcon name="x" class="w-5 h-5" />
              </button>
            </div>
          </template>
          <template v-else>
            <div class="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-md" :title="headerMaterial?.title || t('sidebar.materials')">
              {{ (headerMaterial?.title || 'T').substring(0, 1).toUpperCase() }}
            </div>
          </template>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar space-y-3" :class="collapsed ? 'p-2' : 'p-4'">
          <div v-if="!collapsed" class="px-1 py-1 flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>{{ t('sidebar.materials') }}</span>
            <button
              type="button"
              class="p-1.5 rounded-md text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-slate-800 transition-colors"
              @click="handleOpenCreate"
            >
              <LucideIcon name="plus" class="w-4 h-4" />
            </button>
          </div>
          <div v-else class="flex justify-center mb-2">
            <button
              type="button"
              class="p-1.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-400 hover:text-indigo-600"
              @click="handleOpenCreate"
            >
              <LucideIcon name="plus" class="w-4 h-4" />
            </button>
          </div>

          <div v-for="material in props.materials" :key="material.id">
	            <button
	              type="button"
	              class="w-full group text-left rounded-xl border transition-colors transition-transform transition-shadow duration-200 relative overflow-hidden"
	              :class="[
	                collapsed ? 'p-2 flex justify-center' : 'p-3.5 transform hover:scale-[1.01]',
	                isActive(material.id)
                  ? 'bg-indigo-600 border-indigo-500 shadow-lg shadow-indigo-500/20 text-white'
                  : 'bg-white dark:bg-slate-800/40 border-slate-100 dark:border-slate-800 hover:border-indigo-200 dark:hover:border-indigo-700/40 hover:bg-indigo-50/30 dark:hover:bg-slate-800/60',
              ]"
              @click="handleSelect(material.id)"
            >
              <template v-if="collapsed">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center font-black text-sm" :class="isActive(material.id) ? 'bg-indigo-700/40 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'">
                  {{ material.title.substring(0, 1).toUpperCase() }}
                </div>
              </template>
              <template v-else>
                <div class="flex items-start gap-3">
                  <div class="w-9 h-9 rounded-xl flex items-center justify-center font-black text-sm flex-shrink-0" :class="isActive(material.id) ? 'bg-indigo-700/40 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'">
                    {{ material.title.substring(0, 1).toUpperCase() }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <p
                      class="font-semibold text-sm leading-tight truncate mb-2"
                      :class="isActive(material.id) ? 'text-white' : 'text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400'"
                    >
                      {{ material.title }}
                    </p>
                    <div class="flex items-center gap-2">
                      <div
                        class="flex items-center gap-1.5 px-1.5 py-0.5 rounded"
                        :class="isActive(material.id) ? 'bg-indigo-700/40' : 'bg-slate-100 dark:bg-slate-800'"
                      >
                        <span class="text-[9px] uppercase font-bold" :class="isActive(material.id) ? 'text-indigo-100' : 'text-slate-400'">
                          {{ t('sidebar.assets') }}
                        </span>
                        <div class="flex gap-1">
                          <span
                            class="w-1.5 h-1.5 rounded-full"
                            :class="material.outlineContent ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                          />
                          <span
                            class="w-1.5 h-1.5 rounded-full"
                            :class="material.lessonPlan ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                          />
                          <span
                            class="w-1.5 h-1.5 rounded-full"
                            :class="material.presentation ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-200 dark:bg-slate-700'"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </button>
          </div>

          <div
            v-if="!props.materials.length && !collapsed"
            class="text-center py-8 px-4 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-400"
          >
            <p class="mb-3">{{ t('sidebar.no_materials') }}</p>
            <button type="button" class="font-bold text-indigo-600 dark:text-indigo-400 hover:underline" @click="handleOpenCreate">
              {{ t('sidebar.create_first_material') }}
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
