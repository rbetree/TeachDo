<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, type Component } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import LucideIcon from '@/components/common/LucideIcon.vue';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const normalizeParam = (value: unknown): string | null => {
  if (Array.isArray(value)) return value.length ? value[0] ?? null : null;
  return typeof value === 'string' ? value : null;
};

const materialId = computed(() => normalizeParam(route.params.materialId));

const runtimeComponent = shallowRef<Component | null>(null);
const runtimeError = ref<string | null>(null);
const editorReady = ref(false);

const loadRuntime = async () => {
  runtimeError.value = null;
  editorReady.value = false;
  try {
    const mod = await import('@/views/pptEditor/PPTEditorRuntime.vue');
    runtimeComponent.value = mod.default as unknown as Component;
  } catch (e) {
    runtimeComponent.value = null;
    runtimeError.value = e instanceof Error && e.message ? e.message : String(e || '');
  }
};

onMounted(() => {
  void loadRuntime();
});

const handleBack = async () => {
  const id = materialId.value;
  if (!id) {
    await router.replace({ name: 'workspace' });
    return;
  }
  await router.replace({ name: 'material-tab', params: { materialId: id, tab: 'ppt' } });
};

const handleRetry = () => {
  void loadRuntime();
};

const overlayVisible = computed(() => !editorReady.value);
</script>

<template>
  <div class="relative w-full h-screen bg-slate-100 dark:bg-slate-950">
    <component :is="runtimeComponent" v-if="runtimeComponent" @ready="editorReady = true" />

    <div v-if="overlayVisible" class="absolute inset-0 flex items-center justify-center px-4">
      <div
        class="w-full max-w-md rounded-2xl bg-white/90 dark:bg-slate-900/70 backdrop-blur border border-slate-200 dark:border-slate-800 shadow-xl p-6 text-center"
        role="status"
        aria-live="polite"
      >
        <template v-if="runtimeError">
          <LucideIcon name="alert-circle" :size="44" class="mx-auto mb-4 text-amber-600 dark:text-amber-300" />
          <p class="font-black text-slate-800 dark:text-slate-100">{{ t('editor.load_failed') }}</p>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 break-words">
            {{ t('editor.load_failed_desc') }}
          </p>
          <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-2 break-words">
            {{ runtimeError }}
          </p>
          <div class="mt-5 flex items-center justify-center gap-2">
            <button
              type="button"
              class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs transition-colors"
              @click="handleRetry"
            >
              {{ t('common.retry') }}
            </button>
            <button
              type="button"
              class="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-700 dark:text-slate-200 font-bold text-xs hover:bg-white dark:hover:bg-slate-900 transition-colors"
              @click="handleBack"
            >
              {{ t('editor.back') }}
            </button>
          </div>
        </template>

        <template v-else>
          <LucideIcon name="loader-2" :size="44" class="animate-spin mx-auto mb-4 text-indigo-600 dark:text-indigo-300" />
          <p class="font-black text-slate-800 dark:text-slate-100">{{ t('editor.loading') }}</p>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ t('editor.loading_desc') }}</p>
          <button
            type="button"
            class="mt-5 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-700 dark:text-slate-200 font-bold text-xs hover:bg-white dark:hover:bg-slate-900 transition-colors"
            @click="handleBack"
          >
            {{ t('editor.back') }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
