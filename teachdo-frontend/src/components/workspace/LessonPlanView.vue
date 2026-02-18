<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LessonPlan, TeachingMaterial } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';

interface Props {
  currentMaterial: TeachingMaterial;
  headerActionHost?: HTMLElement | null;
}

interface Emits {
  (e: 'updateMaterial', updates: Partial<TeachingMaterial>): void;
  (e: 'navigate', tab: 'outline'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const loading = ref(false);
const plan = ref<LessonPlan | null>(null);
const copied = ref(false);
const hasExternalToolbar = computed(() => !!props.headerActionHost);

const hasOutline = computed(() => !!props.currentMaterial?.outlineContent);

// Sync state if material changes
watch(
  () => props.currentMaterial,
  (material) => {
    plan.value = material?.lessonPlan || null;
  },
  { immediate: true }
);

const handleGenerate = async () => {
  toast.info(t('lesson.toast.in_progress'));
};

const copyToClipboard = () => {
  if (!plan.value) return;
  const text = `
Title: ${plan.value.title}
Audience: ${plan.value.targetAudience}
Duration: ${plan.value.duration}

Objectives:
${plan.value.objectives.map((o, i) => `${i + 1}. ${o}`).join('\n')}

Procedures:
    ${plan.value.procedure.map(p => `[${p.step} - ${p.duration}]\n${p.activity}`).join('\n\n')}

Homework:
${plan.value.homework}
  `.trim();
  navigator.clipboard.writeText(text);
  copied.value = true;
  toast.info(t('lesson.toast.copied'));
  setTimeout(() => (copied.value = false), 2000);
};

const downloadDocx = () => {
  if (!plan.value) return;

  const htmlContent = `
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head>
      <meta charset='utf-8'>
      <title>${plan.value.title}</title>
      <style>
         body { font-family: 'Times New Roman', serif; padding: 20px; }
         h1 { font-size: 24pt; color: #333333; text-align: center; }
         h2 { font-size: 16pt; color: #546DD4; border-bottom: 1px solid #E5E7EB; padding-bottom: 5px; margin-top: 20px; }
         p { font-size: 12pt; line-height: 1.5; margin-bottom: 10px; }
         .meta { color: #666666; font-size: 11pt; margin-bottom: 20px; text-align: center; }
         .procedure-step { margin-bottom: 15px; }
         .step-title { font-weight: bold; }
      </style>
    </head>
    <body>
      <h1>${plan.value.title}</h1>
      <div class="meta">
         <p><b>Target Audience:</b> ${plan.value.targetAudience} | <b>Duration:</b> ${plan.value.duration}</p>
      </div>

      <h2>Objectives</h2>
      <ul>${plan.value.objectives.map(o => `<li>${o}</li>`).join('')}</ul>

      <h2>Materials</h2>
      <p>${plan.value.materials.join(', ')}</p>

      <h2>Procedure</h2>
      ${plan.value.procedure.map(p => `
        <div class="procedure-step">
           <p><span class="step-title">${p.step} (${p.duration})</span><br/>${p.activity}</p>
        </div>
      `).join('')}

      <h2>Homework</h2>
      <p>${plan.value.homework}</p>
    </body></html>
  `;

  const blob = new Blob(['\ufeff', htmlContent], {
    type: 'application/msword'
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${plan.value.title.replace(/\s+/g, '_')}_LessonPlan.doc`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  toast.success(t('lesson.toast.downloaded'));
};

const goToOutline = () => {
  emit('navigate', 'outline');
};
</script>
	
<template>
  <div v-if="!hasOutline" class="h-full flex flex-col min-h-0">
    <div class="workspace-card flex-1 min-h-0 p-4 md:p-6">
      <div class="h-full w-full flex flex-col items-center justify-center text-slate-400 p-8 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-50/50 dark:bg-slate-900/30">
        <div class="w-16 h-16 bg-white dark:bg-slate-800 rounded-2xl shadow-sm flex items-center justify-center mb-4">
          <span class="text-3xl grayscale opacity-50">📑</span>
        </div>
        <h3 class="text-lg font-bold text-slate-700 dark:text-slate-300">{{ t('lesson.need_outline.title') }}</h3>
        <p class="text-sm mt-2 mb-6 max-w-md text-center text-slate-500">
          {{ t('lesson.need_outline.desc') }}
        </p>
        <button
          class="px-6 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-bold text-sm transition-colors shadow-lg shadow-slate-200/50 dark:shadow-none"
          @click="goToOutline"
        >
          {{ t('lesson.go_outline') }}
        </button>
      </div>
    </div>
  </div>

  <div v-else class="h-full flex flex-col min-h-0" :class="hasExternalToolbar ? 'gap-0' : 'gap-6'">
    <Teleport :to="props.headerActionHost || 'body'" :disabled="!hasExternalToolbar">
      <div
        class="flex items-center justify-end gap-2"
        :class="hasExternalToolbar
          ? 'w-full h-full'
          : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[44px]'"
      >
        <button
          v-if="plan"
          type="button"
          class="toolbar-item text-slate-500 hover:text-slate-800 dark:text-slate-300 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700"
          @click="copyToClipboard"
        >
          {{ copied ? t('lesson.copied') : t('lesson.copy') }}
        </button>
        <button
          v-if="plan"
          type="button"
          class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600"
          @click="downloadDocx"
        >
          <LucideIcon name="download" class="w-4 h-4" /> {{ t('lesson.download') }}
        </button>
        <button
          type="button"
          :disabled="loading"
          class="toolbar-item bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm disabled:bg-slate-300 disabled:text-slate-500"
          @click="handleGenerate"
        >
          {{ t('lesson.in_progress.cta') }}
        </button>
      </div>
    </Teleport>

    <div :class="['workspace-card flex-1 min-h-0 flex flex-col', hasExternalToolbar ? 'mt-4' : '']">
      <div class="p-4 md:p-5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
        <div class="max-w-4xl mx-auto w-full">
          <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-2xl p-4 flex gap-3">
            <div class="w-10 h-10 rounded-xl bg-white/80 dark:bg-slate-900/40 border border-amber-200 dark:border-amber-800/50 flex items-center justify-center text-amber-600 dark:text-amber-300 flex-shrink-0">
              <LucideIcon name="alert-triangle" :size="18" />
            </div>
            <div class="min-w-0">
              <div class="text-sm font-bold text-amber-900 dark:text-amber-100">{{ t('lesson.in_progress.title') }}</div>
              <div class="text-xs text-amber-700 dark:text-amber-200 mt-0.5 leading-relaxed">{{ t('lesson.in_progress.desc') }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 md:p-6">
        <div class="max-w-4xl mx-auto w-full">
          <div v-if="!plan" class="w-full min-h-[420px] border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50/60 dark:bg-slate-950/20 flex items-center justify-center text-slate-300">
            <div class="text-center">
              <div class="text-6xl mb-4 opacity-20">📄</div>
              <p class="font-bold text-slate-500 dark:text-slate-400">{{ t('lesson.ready') }}</p>
            </div>
          </div>

          <div v-else class="text-slate-800 dark:text-slate-200 min-h-[1000px] p-10 md:p-12 relative mx-auto animate-fade-in-up">
            <!-- Decorative Header Line -->
            <div class="w-20 h-1 bg-indigo-600 mb-8"></div>

            <h1 class="text-4xl font-serif font-bold text-slate-900 dark:text-white mb-6 leading-tight">{{ plan.title }}</h1>

            <div class="flex gap-6 text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-12 border-b border-slate-100 dark:border-slate-800 pb-6">
              <div><span class="text-indigo-600">{{ t('lesson.labels.audience') }}:</span> {{ plan.targetAudience }}</div>
              <div><span class="text-indigo-600">{{ t('lesson.labels.duration') }}:</span> {{ plan.duration }}</div>
            </div>

            <div class="space-y-10 font-serif leading-relaxed">
              <section>
                <h3 class="text-lg font-sans font-bold text-slate-900 dark:text-white mb-3 uppercase tracking-wide">{{ t('lesson.section.objectives') }}</h3>
                <ul class="list-disc pl-5 space-y-2 text-slate-700 dark:text-slate-300">
                  <li v-for="(o, i) in plan.objectives" :key="i">{{ o }}</li>
                </ul>
              </section>

              <section>
                <h3 class="text-lg font-sans font-bold text-slate-900 dark:text-white mb-3 uppercase tracking-wide">{{ t('lesson.section.materials') }}</h3>
                <p class="text-slate-700 dark:text-slate-300">{{ plan.materials.join(', ') }}</p>
              </section>

              <section>
                <h3 class="text-lg font-sans font-bold text-slate-900 dark:text-white mb-5 uppercase tracking-wide">{{ t('lesson.section.procedure') }}</h3>
                <div class="space-y-6">
                  <div v-for="(p, i) in plan.procedure" :key="i" class="flex gap-4">
                    <div class="w-16 flex-shrink-0 text-xs font-sans font-bold text-slate-400 dark:text-slate-500 pt-1">{{ p.duration }}</div>
                    <div>
                      <div class="font-bold text-slate-900 dark:text-slate-100 mb-1">{{ p.step }}</div>
                      <p class="text-slate-600 dark:text-slate-300">{{ p.activity }}</p>
                    </div>
                  </div>
                </div>
              </section>

              <section class="bg-slate-50 dark:bg-slate-800/50 p-6 rounded-lg border border-slate-100 dark:border-slate-700 mt-8">
                <h3 class="text-sm font-sans font-bold text-slate-900 dark:text-slate-100 mb-2 uppercase tracking-wide">{{ t('lesson.section.homework') }}</h3>
                <p class="text-slate-700 dark:text-slate-300 italic">{{ plan.homework }}</p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
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

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fade-in-up 0.5s ease-out;
}
</style>
