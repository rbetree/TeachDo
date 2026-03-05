<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { toast } from '@/utils/toast';
import { useI18n } from 'vue-i18n';
import type { UiSettingsConfig, UiSettingsSecrets } from '@/services/settingsService';
import { getSettings, resetSettings, updateSettings } from '@/services/settingsService';

const loading = ref(false);
const showKeys = reactive<Record<string, boolean>>({});
const { t } = useI18n();

// 说明：
// - Outline/PPT 支持多协议（google/claude/openai 兼容等）
// - Lesson/Embedding 当前仅支持 openai 兼容协议（base_url + api_key）
const contentModelProviderOptions = ['openai', 'google', 'claude', 'ollama', 'vllm', 'local_openai', 'xinference'] as const;
const openaiCompatibleProviderOptions = ['openai', 'ollama', 'vllm', 'local_openai', 'xinference'] as const;
const embeddingProviderOptions = ['openai', 'ollama', 'vllm', 'xinference', 'local_openai'] as const;

const accessHostForBindHost = (bindHost: string): string => {
  const raw = (bindHost || '').trim();
  if (!raw) return '127.0.0.1';
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    try {
      return new URL(raw).hostname || raw;
    } catch {
      return raw;
    }
  }
  const lower = raw.toLowerCase();
  if (lower === '0.0.0.0' || lower === '::' || lower === 'localhost') return '127.0.0.1';
  return raw;
};

const normalizeBaseUrlForCompare = (value: string): string => {
  const raw = (value || '').trim();
  if (!raw) return '';
  try {
    const url = new URL(raw);
    const port = url.port ? `:${url.port}` : '';
    return `${url.protocol}//${url.hostname}${port}`;
  } catch {
    return raw.replace(/\/+$/, '');
  }
};

const sameServiceBaseUrl = (a: string, b: string): boolean =>
  normalizeBaseUrlForCompare(a) === normalizeBaseUrlForCompare(b);

const buildLocalServiceUrl = (bindHost: string, portRaw: string): string => {
  const port = Number.parseInt(String(portRaw || '').trim(), 10);
  if (!Number.isFinite(port) || port <= 0 || port > 65535) return '';
  return `http://${accessHostForBindHost(bindHost)}:${port}`;
};

const config = reactive<UiSettingsConfig>({
  outlineType: 'openai',
  outlineBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  outlineModel: 'qwen-turbo-latest',
  outlineApiKey: '',
  lessonType: '',
  lessonBaseUrl: '',
  lessonModel: '',
  lessonApiKey: '',
  pptWriterType: 'openai',
  pptWriterBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  pptWriterModel: 'qwen-turbo-latest',
  pptWriterApiKey: '',
  pptCheckerType: 'openai',
  pptCheckerBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  pptCheckerModel: 'qwen-turbo-latest',
  pptCheckerApiKey: '',
  embeddingType: 'openai',
  embeddingBaseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
  embeddingModel: 'doubao-embedding-text-240715',
  embeddingApiKey: '',
  embeddingTimeoutS: '',
  embeddingMaxRetries: '',
  embeddingDim: '',
  outlineApi: 'http://127.0.0.1:10001',
  contentApi: 'http://127.0.0.1:10011',
  personalDb: 'http://127.0.0.1:9100',
  personalDbPort: '9100',
  httpProxy: '',
  httpsProxy: '',
  pexelsApiKey: '',
  useChart: true,
  outlineStreaming: true,
  contentStreaming: false,
  useMineru: false,
  teachdoCacheDir: 'var/cache',
  teachdoTmpDir: 'var/tmp',
  teachdoLogDir: 'logs',
  host: '127.0.0.1',
  mainApiPort: '6800',
  outlineApiPort: '10001',
  contentApiPort: '10011',
  frontendPort: '5174',
});

const secrets = reactive<UiSettingsSecrets>({
  outlineApiKey: false,
  lessonApiKey: false,
  pptWriterApiKey: false,
  pptCheckerApiKey: false,
  embeddingApiKey: false,
  pexelsApiKey: false,
});

const applyRemoteSettings = (data: { config: UiSettingsConfig; secrets: UiSettingsSecrets }) => {
  Object.assign(config, data.config);
  Object.assign(secrets, data.secrets);
  // 出于安全考虑：后端不会回传已有 key；这里确保输入框默认是空的
  config.outlineApiKey = '';
  config.lessonApiKey = '';
  config.pptWriterApiKey = '';
  config.pptCheckerApiKey = '';
  config.embeddingApiKey = '';
  config.pexelsApiKey = '';
};

// “复用 Outline”场景：选择继承时自动清空覆盖字段，避免出现“继承 + 覆盖值仍存在”的矛盾状态
watch(
  () => config.lessonType,
  (type) => {
    if (!type) {
      config.lessonBaseUrl = '';
      config.lessonModel = '';
    }
  },
);

watch(
  () => config.pptWriterType,
  (type) => {
    if (!type) {
      config.pptWriterBaseUrl = '';
      config.pptWriterModel = '';
    }
  },
);

watch(
  () => config.pptCheckerType,
  (type) => {
    if (!type) {
      config.pptCheckerBaseUrl = '';
      config.pptCheckerModel = '';
    }
  },
);

// 端口与服务 URL 联动（仅当 URL 仍为“本地基址”时才会自动同步，避免覆盖用户手动配置的远端 URL）
watch(
  () => [config.host, config.outlineApiPort] as const,
  ([newHost, newPort], [oldHost, oldPort]) => {
    const oldAuto = buildLocalServiceUrl(oldHost, oldPort);
    if (!oldAuto) return;
    if (!sameServiceBaseUrl(config.outlineApi, oldAuto)) return;

    const nextAuto = buildLocalServiceUrl(newHost, newPort);
    if (!nextAuto) return;
    config.outlineApi = nextAuto;
  },
);

watch(
  () => [config.host, config.contentApiPort] as const,
  ([newHost, newPort], [oldHost, oldPort]) => {
    const oldAuto = buildLocalServiceUrl(oldHost, oldPort);
    if (!oldAuto) return;
    if (!sameServiceBaseUrl(config.contentApi, oldAuto)) return;

    const nextAuto = buildLocalServiceUrl(newHost, newPort);
    if (!nextAuto) return;
    config.contentApi = nextAuto;
  },
);

watch(
  () => [config.host, config.personalDbPort] as const,
  ([newHost, newPort], [oldHost, oldPort]) => {
    const oldAuto = buildLocalServiceUrl(oldHost, oldPort);
    if (!oldAuto) return;
    if (!sameServiceBaseUrl(config.personalDb, oldAuto)) return;

    const nextAuto = buildLocalServiceUrl(newHost, newPort);
    if (!nextAuto) return;
    config.personalDb = nextAuto;
  },
);

onMounted(async () => {
  try {
    const data = await getSettings();
    applyRemoteSettings(data);
  } catch (e) {
    console.error(e);
    toast.error(t('toast.error'));
  }
});

const toggleKeyVisibility = (key: string) => {
  showKeys[key] = !showKeys[key];
};

const getKeyToggleLabel = (key: string) => (showKeys[key] ? t('settings.key.hide') : t('settings.key.show'));

const handleSave = async () => {
  loading.value = true;
  try {
    const data = await updateSettings({ config });
    applyRemoteSettings(data);
    toast.success(t('settings.toast.saved'));
  } catch (e) {
    console.error(e);
    toast.error(t('toast.error'));
  } finally {
    loading.value = false;
  }
};

const handleReset = async () => {
  if (!confirm(t('settings.confirm_reset'))) return;
  loading.value = true;
  try {
    const data = await resetSettings();
    applyRemoteSettings(data);
    toast.info(t('settings.toast.reset'));
  } catch (e) {
    console.error(e);
    toast.error(t('toast.error'));
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <section class="min-h-[calc(100vh-4rem)] bg-slate-100 dark:bg-slate-950">
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

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="space-y-6">
          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-950/35">
              <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300">
                <LucideIcon name="shield" :size="18" />
              </div>
	              <div>
	                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.llm') }}</p>
	                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.llm_desc') }}</p>
	              </div>
	            </div>
            <div class="p-6 space-y-8">
              <div class="space-y-4">
                <div>
                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.content_models') }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.content_models_desc') }}</p>
                </div>

                <div class="space-y-4">
                  <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/25 p-4">
                    <div>
                      <p class="text-sm font-bold text-slate-900 dark:text-white">{{ t('settings.model.outline.title') }}</p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.model.outline.desc') }}</p>
                    </div>

                    <div class="mt-4 grid md:grid-cols-2 gap-4">
                      <label class="space-y-1 text-sm">
                        <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineType') }}</span>
                        <select v-model="config.outlineType" class="td-input">
                          <option v-for="opt in contentModelProviderOptions" :key="opt" :value="opt">{{ opt }}</option>
                        </select>
                      </label>
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
                          <input
                            v-model="config.outlineApiKey"
                            :type="showKeys.outlineApiKey ? 'text' : 'password'"
                            :placeholder="secrets.outlineApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
                            class="td-input flex-1"
                          />
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
                    </div>
                  </div>

                  <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/25 p-4">
                    <div>
                      <p class="text-sm font-bold text-slate-900 dark:text-white">{{ t('settings.model.lesson.title') }}</p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.model.lesson.desc') }}</p>
                    </div>

                    <div class="mt-4 grid md:grid-cols-2 gap-4">
                      <label class="space-y-1 text-sm">
                        <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.lessonType') }}</span>
                        <select v-model="config.lessonType" class="td-input">
                          <option value="">{{ t('settings.option.inherit_outline') }}</option>
                          <option v-for="opt in openaiCompatibleProviderOptions" :key="opt" :value="opt">{{ opt }}</option>
                        </select>
                      </label>
                      <label class="space-y-1 text-sm">
                        <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.lessonBase') }}</span>
                        <input v-model="config.lessonBaseUrl" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                      </label>
                      <label class="space-y-1 text-sm">
                        <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.lessonModel') }}</span>
                        <input v-model="config.lessonModel" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                      </label>
                      <label class="space-y-1 text-sm">
                        <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.lessonKey') }}</span>
                        <div class="flex gap-2">
                          <input
                            v-model="config.lessonApiKey"
                            :type="showKeys.lessonApiKey ? 'text' : 'password'"
                            :placeholder="secrets.lessonApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
                            class="td-input flex-1"
                          />
                          <button
                            class="td-icon-btn"
                            type="button"
                            :aria-label="getKeyToggleLabel('lessonApiKey')"
                            :title="getKeyToggleLabel('lessonApiKey')"
                            :aria-pressed="!!showKeys.lessonApiKey"
                            @click="toggleKeyVisibility('lessonApiKey')"
                          >
                            <LucideIcon :name="showKeys.lessonApiKey ? 'eye-off' : 'eye'" :size="16" />
                          </button>
                        </div>
                      </label>
                    </div>
                  </div>

                  <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/25 p-4">
                    <div>
                      <p class="text-sm font-bold text-slate-900 dark:text-white">{{ t('settings.model.ppt.title') }}</p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.model.ppt.desc') }}</p>
                    </div>

                    <div class="mt-4 space-y-6">
                      <div class="space-y-3">
                        <p class="text-xs font-extrabold tracking-wide text-slate-700 dark:text-slate-200">
                          {{ t('settings.model.ppt.writer') }}
                        </p>
                        <div class="grid md:grid-cols-2 gap-4">
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterType') }}</span>
                            <select v-model="config.pptWriterType" class="td-input">
                              <option value="">{{ t('settings.option.inherit_outline') }}</option>
                              <option v-for="opt in contentModelProviderOptions" :key="opt" :value="opt">{{ opt }}</option>
                            </select>
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterBase') }}</span>
                            <input v-model="config.pptWriterBaseUrl" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterModel') }}</span>
                            <input v-model="config.pptWriterModel" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptWriterKey') }}</span>
                            <div class="flex gap-2">
                              <input
                                v-model="config.pptWriterApiKey"
                                :type="showKeys.pptWriterApiKey ? 'text' : 'password'"
                                :placeholder="secrets.pptWriterApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
                                class="td-input flex-1"
                              />
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
                        </div>
                      </div>

                      <div class="h-px bg-slate-200/70 dark:bg-slate-800"></div>

                      <div class="space-y-3">
                        <p class="text-xs font-extrabold tracking-wide text-slate-700 dark:text-slate-200">
                          {{ t('settings.model.ppt.checker') }}
                        </p>
                        <div class="grid md:grid-cols-2 gap-4">
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerType') }}</span>
                            <select v-model="config.pptCheckerType" class="td-input">
                              <option value="">{{ t('settings.option.inherit_outline') }}</option>
                              <option v-for="opt in contentModelProviderOptions" :key="opt" :value="opt">{{ opt }}</option>
                            </select>
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerBase') }}</span>
                            <input v-model="config.pptCheckerBaseUrl" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerModel') }}</span>
                            <input v-model="config.pptCheckerModel" :placeholder="t('settings.placeholder.inherit_outline')" class="td-input" />
                          </label>
                          <label class="space-y-1 text-sm">
                            <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pptCheckerKey') }}</span>
                            <div class="flex gap-2">
                              <input
                                v-model="config.pptCheckerApiKey"
                                :type="showKeys.pptCheckerApiKey ? 'text' : 'password'"
                                :placeholder="secrets.pptCheckerApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
                                class="td-input flex-1"
                              />
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
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="h-px bg-slate-100 dark:bg-slate-800"></div>

              <div class="space-y-4">
                <div>
                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.index_models') }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.index_models_desc') }}</p>
                </div>

                <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/25 p-4">
                  <div>
                    <p class="text-sm font-bold text-slate-900 dark:text-white">{{ t('settings.model.embedding.title') }}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.model.embedding.desc') }}</p>
                  </div>

                  <div class="mt-4 grid md:grid-cols-2 gap-4">
                    <label class="space-y-1 text-sm">
                      <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingType') }}</span>
                      <select v-model="config.embeddingType" class="td-input">
                        <option v-for="opt in embeddingProviderOptions" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
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
                        <input
                          v-model="config.embeddingApiKey"
                          :type="showKeys.embeddingApiKey ? 'text' : 'password'"
                          :placeholder="secrets.embeddingApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
                          class="td-input flex-1"
                        />
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

                  <div class="mt-4 grid md:grid-cols-3 gap-4">
                    <label class="space-y-1 text-sm">
                      <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingTimeoutS') }}</span>
                      <input v-model="config.embeddingTimeoutS" type="number" class="td-input" />
                    </label>
                    <label class="space-y-1 text-sm">
                      <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingMaxRetries') }}</span>
                      <input v-model="config.embeddingMaxRetries" type="number" class="td-input" />
                    </label>
                    <label class="space-y-1 text-sm">
                      <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.embeddingDim') }}</span>
                      <input v-model="config.embeddingDim" type="number" class="td-input" />
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-950/35">
              <div class="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-300">
                <LucideIcon name="server" :size="18" />
              </div>
	              <div>
	                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.service') }}</p>
	                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.service_desc') }}</p>
	              </div>
	            </div>
            <div class="p-6 space-y-6">
              <div class="space-y-3">
                <div>
                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.endpoints') }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.endpoints_desc') }}</p>
                </div>

                <div class="grid md:grid-cols-2 gap-4">
                  <label class="space-y-1 text-sm">
                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineApi') }}</span>
                    <input v-model="config.outlineApi" class="td-input" />
                  </label>
                  <label class="space-y-1 text-sm">
                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.contentApi') }}</span>
                    <input v-model="config.contentApi" class="td-input" />
                  </label>
                  <label class="space-y-1 text-sm md:col-span-2">
                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.personalDb') }}</span>
                    <input v-model="config.personalDb" class="td-input" />
                  </label>
                </div>
              </div>

              <div class="h-px bg-slate-100 dark:bg-slate-800"></div>

              <div class="space-y-3">
                <div>
                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.proxy') }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.proxy_desc') }}</p>
                </div>

                <div class="grid md:grid-cols-2 gap-4">
                  <label class="space-y-1 text-sm">
                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.httpProxy') }}</span>
                    <input v-model="config.httpProxy" class="td-input" />
                  </label>
                  <label class="space-y-1 text-sm">
                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.httpsProxy') }}</span>
                    <input v-model="config.httpsProxy" class="td-input" />
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-950/35">
              <div class="p-2 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-300">
                <LucideIcon name="file" :size="18" />
              </div>
	              <div>
	                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.runtime') }}</p>
	                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.runtime_desc') }}</p>
	              </div>
	            </div>
	            <div class="p-6 space-y-6">
	              <div class="space-y-3">
	                <div>
	                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.behavior') }}</p>
	                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.behavior_desc') }}</p>
	                </div>

	                <div class="grid md:grid-cols-2 gap-4">
	                  <label class="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
	                    <input
	                      v-model="config.outlineStreaming"
	                      type="checkbox"
	                      class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
	                    />
	                    {{ t('settings.form.outlineStreaming') }}
	                  </label>
	                  <label class="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
	                    <input
	                      v-model="config.contentStreaming"
	                      type="checkbox"
	                      class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
	                    />
	                    {{ t('settings.form.contentStreaming') }}
	                  </label>
	                  <label class="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
	                    <input
	                      v-model="config.useChart"
	                      type="checkbox"
	                      class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
	                    />
	                    {{ t('settings.form.useChart') }}
	                  </label>
	                </div>
	              </div>

	              <div class="h-px bg-slate-100 dark:bg-slate-800"></div>

	              <div class="space-y-3">
	                <div>
	                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.assets') }}</p>
	                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.assets_desc') }}</p>
	                </div>

	                <div class="grid md:grid-cols-2 gap-4">
	                  <label class="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
	                    <input
	                      v-model="config.useMineru"
	                      type="checkbox"
	                      class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
	                    />
	                    {{ t('settings.form.useMineru') }}
	                  </label>

	                  <label class="space-y-1 text-sm md:col-span-2">
	                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.pexelsKey') }}</span>
	                    <div class="flex gap-2">
	                      <input
	                        v-model="config.pexelsApiKey"
	                        :type="showKeys.pexelsApiKey ? 'text' : 'password'"
	                        :placeholder="secrets.pexelsApiKey ? t('settings.key.placeholder.keep') : t('settings.key.placeholder.set')"
	                        class="td-input flex-1"
	                      />
	                      <button
	                        class="td-icon-btn"
	                        type="button"
	                        :aria-label="getKeyToggleLabel('pexelsApiKey')"
	                        :title="getKeyToggleLabel('pexelsApiKey')"
	                        :aria-pressed="!!showKeys.pexelsApiKey"
	                        @click="toggleKeyVisibility('pexelsApiKey')"
	                      >
	                        <LucideIcon :name="showKeys.pexelsApiKey ? 'eye-off' : 'eye'" :size="16" />
	                      </button>
	                    </div>
	                  </label>
	                </div>
	              </div>

	              <div class="h-px bg-slate-100 dark:bg-slate-800"></div>

	              <div class="space-y-3">
	                <div>
	                  <p class="text-sm font-extrabold text-slate-800 dark:text-white">{{ t('settings.group.paths') }}</p>
	                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.group.paths_desc') }}</p>
	                </div>

	                <div class="grid md:grid-cols-2 gap-4">
	                  <label class="space-y-1 text-sm">
	                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.cacheDir') }}</span>
	                    <input v-model="config.teachdoCacheDir" class="td-input" />
	                  </label>
	                  <label class="space-y-1 text-sm">
	                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.tmpDir') }}</span>
	                    <input v-model="config.teachdoTmpDir" class="td-input" />
	                  </label>
	                  <label class="space-y-1 text-sm md:col-span-2">
	                    <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.logDir') }}</span>
	                    <input v-model="config.teachdoLogDir" class="td-input" />
	                  </label>
	                </div>
	              </div>
	            </div>
	          </div>

          <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
            <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3 bg-slate-50/70 dark:bg-slate-950/35">
              <div class="p-2 rounded-lg bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-300">
                <LucideIcon name="network" :size="18" />
              </div>
              <div>
                <p class="text-sm font-bold text-slate-800 dark:text-white">{{ t('settings.section.ports') }}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.section.ports_desc') }}</p>
              </div>
            </div>
            <div class="p-6 space-y-4">
              <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('settings.ports.notice') }}</p>
              <div class="grid md:grid-cols-2 gap-4">
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.host') }}</span>
                  <input v-model="config.host" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.mainApiPort') }}</span>
                  <input v-model="config.mainApiPort" type="number" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.outlineApiPort') }}</span>
                  <input v-model="config.outlineApiPort" type="number" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.contentApiPort') }}</span>
                  <input v-model="config.contentApiPort" type="number" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.personalDbPort') }}</span>
                  <input v-model="config.personalDbPort" type="number" class="td-input" />
                </label>
                <label class="space-y-1 text-sm">
                  <span class="text-slate-500 dark:text-slate-400">{{ t('settings.form.frontendPort') }}</span>
                  <input v-model="config.frontendPort" type="number" class="td-input" />
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
