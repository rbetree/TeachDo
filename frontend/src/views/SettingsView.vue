<script setup lang="ts">
import { reactive, ref } from 'vue';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { toast } from '@/utils/toast';
import { useAppStore } from '@/stores/appStore';
import { useI18n } from 'vue-i18n';

const store = useAppStore();
const loading = ref(false);
const showKeys = reactive<Record<string, boolean>>({});
const { t } = useI18n();

const config = reactive({
  outlineType: 'openai',
  outlineBaseUrl: 'https://api.siliconflow.cn/v1',
  outlineModel: 'deepseek-ai/DeepSeek-V3',
  outlineApiKey: 'sk-xxxxxxxx',
  pptWriterType: 'openai',
  pptWriterBaseUrl: 'https://api.siliconflow.cn/v1',
  pptWriterModel: 'deepseek-ai/DeepSeek-V3',
  pptWriterApiKey: 'sk-xxxxxxxx',
  pptCheckerType: 'openai',
  pptCheckerBaseUrl: 'https://api.siliconflow.cn/v1',
  pptCheckerModel: 'deepseek-ai/DeepSeek-V3',
  pptCheckerApiKey: 'sk-xxxxxxxx',
  embeddingType: 'openai',
  embeddingBaseUrl: 'https://api.siliconflow.cn/v1',
  embeddingModel: 'BAAI/bge-m3',
  embeddingApiKey: 'sk-xxxxxxxx',
  outlineApi: 'http://127.0.0.1:10001',
  contentApi: 'http://127.0.0.1:10011',
  personalDb: 'http://127.0.0.1:9100',
  httpProxy: '',
  httpsProxy: '',
  useChart: true,
});

const toggleKeyVisibility = (key: string) => {
  showKeys[key] = !showKeys[key];
};

const getKeyToggleLabel = (key: string) => (showKeys[key] ? t('settings.key.hide') : t('settings.key.show'));

const handleSave = () => {
  loading.value = true;
  setTimeout(() => {
    loading.value = false;
    toast.success(t('settings.toast.saved_demo'));
  }, 800);
};

const handleReset = () => {
  if (!confirm(t('settings.confirm_reset_demo'))) return;
  toast.info(t('settings.toast.reset_demo'));
};
</script>

<template>
  <section class="min-h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900">
    <div class="mx-auto max-w-6xl px-6 md:px-10 py-8 md:py-10 space-y-6">
      <header class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
            <LucideIcon name="settings-2" :size="26" class="text-indigo-600" />
            {{ t('settings.title') }}
          </h1>
          <p class="text-slate-600 dark:text-slate-400">{{ t('settings.subtitle') }}</p>
        </div>
        <div class="flex gap-3">
          <button
            class="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-slate-800"
            @click="handleReset"
          >
            <LucideIcon name="rotate-ccw" :size="16" /> {{ t('settings.reset') }}
          </button>
          <button
            class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 shadow-sm"
            :disabled="loading"
            @click="handleSave"
          >
            <LucideIcon :name="loading ? 'loader-2' : 'save'" :size="16" :class="{ 'animate-spin': loading }" />
            {{ loading ? t('settings.saving') : t('settings.save') }}
          </button>
        </div>
      </header>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-6">
          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-900/50">
              <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300">
                <LucideIcon name="shield" :size="18" />
              </div>
	              <div>
	                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.llm') }}</p>
	                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.llm_desc') }}</p>
	              </div>
	            </div>
            <div class="p-6 space-y-4">
              <div class="grid md:grid-cols-2 gap-4">
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineBase') }}</span>
                  <input v-model="config.outlineBaseUrl" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineModel') }}</span>
                  <input v-model="config.outlineModel" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineKey') }}</span>
                  <div class="flex gap-2">
	                    <input v-model="config.outlineApiKey" :type="showKeys.outlineApiKey ? 'text' : 'password'" class="td-input flex-1" />
	                    <button
	                      class="td-icon-btn"
	                      type="button"
	                      :aria-label="getKeyToggleLabel('outlineApiKey')"
	                      :title="getKeyToggleLabel('outlineApiKey')"
	                      :aria-pressed="!!showKeys.outlineApiKey"
	                      @click="toggleKeyVisibility('outlineApiKey')"
	                    >
	                      <LucideIcon :name="showKeys.outlineApiKey ? 'eye-off' : 'eye'" :size="16" />
	                    </button>
	                  </div>
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterBase') }}</span>
                  <input v-model="config.pptWriterBaseUrl" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterModel') }}</span>
                  <input v-model="config.pptWriterModel" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterKey') }}</span>
                  <div class="flex gap-2">
	                    <input v-model="config.pptWriterApiKey" :type="showKeys.pptWriterApiKey ? 'text' : 'password'" class="td-input flex-1" />
	                    <button
	                      class="td-icon-btn"
	                      type="button"
	                      :aria-label="getKeyToggleLabel('pptWriterApiKey')"
	                      :title="getKeyToggleLabel('pptWriterApiKey')"
	                      :aria-pressed="!!showKeys.pptWriterApiKey"
	                      @click="toggleKeyVisibility('pptWriterApiKey')"
	                    >
	                      <LucideIcon :name="showKeys.pptWriterApiKey ? 'eye-off' : 'eye'" :size="16" />
	                    </button>
	                  </div>
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerBase') }}</span>
                  <input v-model="config.pptCheckerBaseUrl" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerModel') }}</span>
                  <input v-model="config.pptCheckerModel" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerKey') }}</span>
                  <div class="flex gap-2">
	                    <input v-model="config.pptCheckerApiKey" :type="showKeys.pptCheckerApiKey ? 'text' : 'password'" class="td-input flex-1" />
	                    <button
	                      class="td-icon-btn"
	                      type="button"
	                      :aria-label="getKeyToggleLabel('pptCheckerApiKey')"
	                      :title="getKeyToggleLabel('pptCheckerApiKey')"
	                      :aria-pressed="!!showKeys.pptCheckerApiKey"
	                      @click="toggleKeyVisibility('pptCheckerApiKey')"
	                    >
	                      <LucideIcon :name="showKeys.pptCheckerApiKey ? 'eye-off' : 'eye'" :size="16" />
	                    </button>
	                  </div>
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingBase') }}</span>
                  <input v-model="config.embeddingBaseUrl" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingModel') }}</span>
                  <input v-model="config.embeddingModel" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingKey') }}</span>
                  <div class="flex gap-2">
	                    <input v-model="config.embeddingApiKey" :type="showKeys.embeddingApiKey ? 'text' : 'password'" class="td-input flex-1" />
	                    <button
	                      class="td-icon-btn"
	                      type="button"
	                      :aria-label="getKeyToggleLabel('embeddingApiKey')"
	                      :title="getKeyToggleLabel('embeddingApiKey')"
	                      :aria-pressed="!!showKeys.embeddingApiKey"
	                      @click="toggleKeyVisibility('embeddingApiKey')"
	                    >
	                      <LucideIcon :name="showKeys.embeddingApiKey ? 'eye-off' : 'eye'" :size="16" />
	                    </button>
	                  </div>
	                </label>
              </div>
            </div>
          </div>

          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-900/50">
              <div class="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-300">
                <LucideIcon name="server" :size="18" />
              </div>
	              <div>
	                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.service') }}</p>
	                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.service_desc') }}</p>
	              </div>
	            </div>
            <div class="p-6 space-y-4">
              <div class="grid md:grid-cols-2 gap-4">
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineApi') }}</span>
                  <input v-model="config.outlineApi" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.contentApi') }}</span>
                  <input v-model="config.contentApi" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.personalDb') }}</span>
                  <input v-model="config.personalDb" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.httpProxy') }}</span>
                  <input v-model="config.httpProxy" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.httpsProxy') }}</span>
                  <input v-model="config.httpsProxy" class="td-input" />
                </label>
                <label class="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 pt-4">
                  <input v-model="config.useChart" type="checkbox" class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  {{ t('settings.form.useChart') }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm p-5 flex items-start gap-3">
            <div class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <LucideIcon name="shield" :size="18" />
            </div>
	            <div class="space-y-2">
	              <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.security') }}</p>
	              <p class="text-sm text-slate-600 dark:text-slate-400">{{ t('settings.security_notice_demo') }}</p>
	            </div>
	          </div>

          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm p-5 flex items-start gap-3">
            <div class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              <LucideIcon name="activity" :size="18" />
            </div>
	            <div class="space-y-2">
	              <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.theme') }}</p>
	              <p class="text-sm text-slate-600 dark:text-slate-400">
	                {{ t('settings.theme') }}：{{ store.isDarkMode ? t('settings.theme.dark') : t('settings.theme.light') }}
	              </p>
	              <button
	                class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900"
	                @click="store.toggleTheme()"
	              >
	                {{ t('settings.toggle') }}
	              </button>
	            </div>
	          </div>
        </div>
      </div>
    </div>
  </section>
</template>
