<script setup lang="ts">
import { onBeforeUnmount, ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { TeachingMaterial } from '#root/types';
import { aiService } from '@/services/aiService';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { escapeHtml } from '@/utils/safeHtml';
import { KB_USER_ID, useAppStore } from '@/stores/appStore';
import { ApiError } from '@/services/apiClient';
import { buildGenOutputFileId, formatVersionLabel, sanitizeFilenameSegment } from '@/utils/genOutputFileId';

interface Props {
  currentMaterial: TeachingMaterial;
  headerActionHost?: HTMLElement | null;
}

interface Emits {
  (e: 'updateMaterial', updates: Partial<TeachingMaterial>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const loading = ref(false);
const outlineText = ref('');
const newOutlineText = ref('');
const mode = ref<'PREVIEW' | 'COMPARE'>('PREVIEW');
const pendingController = ref<AbortController | null>(null);
const editorRef = ref<HTMLElement | null>(null);
const editorFocused = ref(false);
const editorFrozenHtml = ref('');
const store = useAppStore();
const outlineLength = ref<'short' | 'standard' | 'long'>('standard');
const useWebSearch = ref(true);

const hasUnsavedChanges = computed(() => (outlineText.value || '') !== (props.currentMaterial.outlineContent || ''));

// Sync state if material changes externally
watch(
  () => props.currentMaterial.id,
  () => {
    outlineText.value = props.currentMaterial.outlineContent || '';
    newOutlineText.value = '';
    mode.value = 'PREVIEW';
    editorFocused.value = false;
    editorFrozenHtml.value = '';
    outlineLength.value = 'standard';
    useWebSearch.value = true;
  },
  { immediate: true },
);

watch(
  () => props.currentMaterial.outlineContent,
  (next, prev) => {
    if (mode.value === 'COMPARE') return;
    if (editorFocused.value) return;
    // 本地内容未被用户修改时，才同步外部变更
    if ((outlineText.value || '') !== (prev || '')) return;
    outlineText.value = next || '';
  },
);

const handleGenerateWrapper = async () => {
  pendingController.value?.abort();
  const controller = new AbortController();
  pendingController.value = controller;

  if (outlineText.value && outlineText.value.trim().length > 0) {
    // --- COMPARE MODE ---
    mode.value = 'COMPARE';
    newOutlineText.value = '';
    loading.value = true;
    try {
      await aiService.generateOutline(
        props.currentMaterial,
        (text) => {
          newOutlineText.value = text;
        },
        { signal: controller.signal, outlineLength: outlineLength.value, useWebSearch: useWebSearch.value },
      );
      toast.success(t('outline.toast.new'));
    } catch (e) {
      if (e instanceof ApiError && e.kind === 'abort') {
        toast.info(t('outline.toast.canceled'));
        newOutlineText.value = '';
        mode.value = 'PREVIEW';
        return;
      }
      console.error(e);
      toast.error(t('outline.toast.error'));
      mode.value = 'PREVIEW'; // Revert
    } finally {
      loading.value = false;
      pendingController.value = null;
    }
  } else {
    // --- DIRECT GENERATE MODE ---
    loading.value = true;
    mode.value = 'PREVIEW';
    try {
      const finalText = await aiService.generateOutline(
        props.currentMaterial,
        (text) => {
          outlineText.value = text;
        },
        { signal: controller.signal, outlineLength: outlineLength.value, useWebSearch: useWebSearch.value },
      );
      emit('updateMaterial', { outlineContent: finalText });
      vectorizeOutlineToKb(finalText);
      toast.success(t('outline.toast.generated'));
    } catch (e) {
      if (e instanceof ApiError && e.kind === 'abort') {
        toast.info(t('outline.toast.canceled'));
        outlineText.value = props.currentMaterial.outlineContent || '';
        return;
      }
      console.error(e);
      toast.error(t('outline.toast.error'));
    } finally {
      loading.value = false;
      pendingController.value = null;
    }
  }
};

const cancelGenerate = () => {
  pendingController.value?.abort();
};

onBeforeUnmount(() => {
  pendingController.value?.abort();
});

const vectorizeOutlineToKb = (content: string) => {
  const trimmed = content?.trim();
  if (!trimmed) return;

  const nowMs = Date.now();
  const materialId = props.currentMaterial.id;
  const titleBase = sanitizeFilenameSegment(props.currentMaterial.title || materialId) || materialId;
  const version = formatVersionLabel(nowMs) || String(nowMs);
  const fileId = buildGenOutputFileId({ userId: KB_USER_ID, materialId, kind: 'outline', nowMs });
  const fileName = `大纲-${titleBase}-${version}.md`;

  void aiService
    .vectorizeTextToKb({
      userId: KB_USER_ID,
      fileId,
      fileName,
      content: trimmed,
      fileType: 'md',
      folderId: 1,
      createdAt: nowMs,
      sourceType: 'material',
      sourceMaterialId: materialId,
      sourceMaterialTitle: props.currentMaterial.title,
    })
    .then(() => {
      const next = (store.kbFiles || []).filter((f) => f.id !== fileId);
      next.unshift({
        id: fileId,
        name: fileName,
        size: trimmed.length,
        type: 'md',
        status: 'ready',
        uploadedAt: new Date(nowMs),
        folderId: 1,
        sourceType: 'material',
        sourceMaterialId: materialId,
        sourceMaterialTitle: props.currentMaterial.title,
      });
      store.setKbFiles(next);
    })
    .catch((e) => console.warn('大纲入库失败（已忽略）', e));
};

const handleConfirmChoice = (choice: 'OLD' | 'NEW') => {
  const finalText = choice === 'NEW' ? newOutlineText.value : outlineText.value;

  outlineText.value = finalText;
  newOutlineText.value = '';
  mode.value = 'PREVIEW';

  // Persist choice
  emit('updateMaterial', { outlineContent: finalText });
  vectorizeOutlineToKb(finalText);
  toast.info(choice === 'NEW' ? t('outline.replace_new') : t('outline.keep_original'));
};

const handleSave = () => {
  emit('updateMaterial', { outlineContent: outlineText.value });
  vectorizeOutlineToKb(outlineText.value);
  mode.value = 'PREVIEW';
  toast.success(t('outline.toast.saved'));
};

// Helper to render bold text within lines
const renderInlineStyles = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return `<strong key="${i}" class="font-bold text-slate-900 dark:text-white bg-indigo-50 dark:bg-indigo-900/30 px-1 rounded mx-0.5">${escapeHtml(part.slice(2, -2))}</strong>`;
    }
    return escapeHtml(part);
  }).join('');
};

// Enhanced Markdown Renderer
const renderMarkdown = (content: string) => {
  if (!content) return '';

  const lines = content.split('\n');
  return lines.map((line, idx) => {
    if (line.startsWith('# ')) {
      return `<h1 key="${idx}" class="text-2xl md:text-3xl font-bold text-slate-900 dark:text-white mt-8 mb-4 border-b pb-3 border-slate-200 dark:border-slate-700">${escapeHtml(line.replace('# ', ''))}</h1>`;
    }
    if (line.startsWith('## ')) {
      return `<h2 key="${idx}" class="text-lg md:text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-6 mb-3">${escapeHtml(line.replace('## ', ''))}</h2>`;
    }
    if (line.startsWith('### ')) {
      return `<h3 key="${idx}" class="text-base md:text-lg font-bold text-slate-700 dark:text-slate-300 mt-4 mb-2">${escapeHtml(line.replace('### ', ''))}</h3>`;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      const text = line.replace(/^[-*] /, '');
      return `<li key="${idx}" class="ml-4 list-disc marker:text-indigo-400 pl-2">${renderInlineStyles(text)}</li>`;
    }

    if (line.trim() === '') {
      return `<br key="${idx}" />`;
    }

    return `<p key="${idx}" class="">${renderInlineStyles(line)}</p>`;
  }).join('');
};

const markdownHtml = computed(() => renderMarkdown(outlineText.value));
const newMarkdownHtml = computed(() => renderMarkdown(newOutlineText.value));
const hasExternalToolbar = computed(() => !!props.headerActionHost);
const displayHtml = computed(() => (editorFocused.value ? editorFrozenHtml.value : markdownHtml.value));

const inlineMarkdownFromNode = (node: Node): string => {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent || '';
  if (node.nodeType !== Node.ELEMENT_NODE) return '';

  const el = node as HTMLElement;
  const tag = el.tagName.toLowerCase();

  if (tag === 'br') return '\n';

  const text = Array.from(el.childNodes)
    .map((child) => inlineMarkdownFromNode(child))
    .join('');

  if (tag === 'strong' || tag === 'b') {
    const trimmed = text.trim();
    return trimmed ? `**${trimmed}**` : '';
  }

  return text;
};

const htmlToMarkdown = (html: string): string => {
  const doc = new DOMParser().parseFromString(html || '', 'text/html');
  const root = doc.body;
  const lines: string[] = [];

  const pushTextLines = (text: string) => {
    const normalized = String(text || '').replace(/\u00a0/g, ' ');
    const parts = normalized.split('\n').map((p) => p.trim());
    for (const part of parts) lines.push(part);
  };

  const walk = (node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = (node.textContent || '').replace(/\u00a0/g, ' ').trim();
      if (text) lines.push(text);
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;

    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();

    if (tag === 'br') {
      lines.push('');
      return;
    }

    if (tag === 'h1' || tag === 'h2' || tag === 'h3') {
      const prefix = tag === 'h1' ? '# ' : tag === 'h2' ? '## ' : '### ';
      const text = inlineMarkdownFromNode(el).replace(/\n+/g, ' ').trim();
      lines.push(`${prefix}${text}`.trimEnd());
      return;
    }

    if (tag === 'li') {
      const text = inlineMarkdownFromNode(el).replace(/\n+/g, ' ').trim();
      lines.push(`- ${text}`.trimEnd());
      return;
    }

    if (tag === 'ul' || tag === 'ol') {
      for (const child of Array.from(el.childNodes)) walk(child);
      return;
    }

    if (tag === 'p' || tag === 'div') {
      const text = inlineMarkdownFromNode(el);
      if (!text.trim()) {
        lines.push('');
        return;
      }
      pushTextLines(text);
      return;
    }

    for (const child of Array.from(el.childNodes)) walk(child);
  };

  for (const node of Array.from(root.childNodes)) walk(node);

  while (lines.length > 0 && lines[lines.length - 1] === '') lines.pop();
  return lines.join('\n');
};

const syncMarkdownFromEditor = () => {
  const el = editorRef.value;
  if (!el) return;
  outlineText.value = htmlToMarkdown(el.innerHTML);
};

const handleEditorFocus = () => {
  editorFocused.value = true;
  editorFrozenHtml.value = editorRef.value?.innerHTML ?? markdownHtml.value;
};

const handleEditorBlur = () => {
  syncMarkdownFromEditor();
  editorFocused.value = false;
  editorFrozenHtml.value = '';
};

const handleEditorInput = () => {
  syncMarkdownFromEditor();
};
</script>

<template>
  <div class="h-full flex flex-col min-h-0" :class="hasExternalToolbar ? 'gap-0' : 'gap-6'">
    <!-- Toolbar -->
    <Teleport :to="props.headerActionHost || 'body'" :disabled="!hasExternalToolbar">
      <div
        class="flex items-center justify-between gap-2"
        :class="hasExternalToolbar
          ? 'w-full h-full'
          : 'bg-white dark:bg-slate-900 p-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm sticky top-0 z-10 min-h-[44px]'"
      >
        <div class="flex items-center gap-2 min-w-0 overflow-x-auto no-scrollbar">
          <div class="toolbar-cluster shrink-0">
            <span class="toolbar-item text-slate-600 dark:text-slate-300">
              <LucideIcon name="layout-list" class="w-4 h-4" />
              <span>{{ t('workspace.tab.outline') }}</span>
            </span>
          </div>

          <div v-if="mode === 'COMPARE'" class="toolbar-item text-indigo-600 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-700 shadow-sm shrink-0">
            <LucideIcon name="arrow-left-right" class="w-4 h-4" /> {{ t('outline.compare_banner') }}
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            v-if="loading"
            type="button"
            class="toolbar-item bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-800/40 hover:bg-red-100 dark:hover:bg-red-900/30"
            @click="cancelGenerate"
          >
            <LucideIcon name="x" class="w-4 h-4" />
            <span>{{ t('common.cancel') }}</span>
          </button>
          <template v-if="mode !== 'COMPARE'">
            <label
              class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 select-none"
              :class="loading ? 'opacity-60 cursor-not-allowed' : ''"
            >
              <span class="text-xs font-black text-slate-500 dark:text-slate-300">{{ t('outline.length') }}</span>
              <select
                v-model="outlineLength"
                :disabled="loading"
                class="bg-transparent outline-none text-slate-700 dark:text-slate-100 font-black text-sm"
              >
                <option value="short">{{ t('outline.length.short') }}</option>
                <option value="standard">{{ t('outline.length.standard') }}</option>
                <option value="long">{{ t('outline.length.long') }}</option>
              </select>
            </label>

            <label
              class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 cursor-pointer select-none disabled:opacity-60"
              :class="loading ? 'opacity-60 cursor-not-allowed' : ''"
              :title="t('outline.web_search.desc')"
            >
              <input
                v-model="useWebSearch"
                type="checkbox"
                class="h-4 w-4 accent-indigo-600 disabled:opacity-50"
                :disabled="loading"
              />
              <span>{{ t('outline.web_search') }}</span>
            </label>

            <button
              :disabled="loading"
              class="toolbar-item border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-slate-600 disabled:opacity-60"
              @click="handleGenerateWrapper"
            >
              <LucideIcon
                :name="loading ? 'loader-2' : (outlineText ? 'refresh-cw' : 'sparkles')"
                class="w-4 h-4"
                :class="{ 'animate-spin': loading }"
              />
              <span>{{ outlineText ? t('outline.regenerate') : t('outline.generate_cta') }}</span>
            </button>
            <button
              v-if="hasUnsavedChanges"
              :disabled="loading"
              class="toolbar-item bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm"
              @click="handleSave"
            >
              <LucideIcon name="save" class="w-4 h-4" /> {{ t('outline.save') }}
            </button>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- Main Content Area -->
    <div
      :class="[
        'workspace-card flex-1 min-h-0 relative flex flex-col',
        hasExternalToolbar ? 'mt-4' : '',
        mode === 'COMPARE' ? 'bg-slate-100 dark:bg-slate-950' : '',
      ]"
    >
      <!-- --- COMPARE MODE --- -->
      <div
        v-if="mode === 'COMPARE'"
        class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 dark:divide-slate-800"
      >
        <!-- Left: Original -->
        <div class="flex flex-col h-full min-h-0 bg-white dark:bg-slate-900">
          <div class="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex justify-between items-center sticky top-0 z-10">
            <span class="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <LucideIcon name="history" :size="16" /> {{ t('outline.current_version') }}
            </span>
          </div>
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6">
            <article class="prose dark:prose-invert prose-sm max-w-none opacity-80">
              <div class="space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base" v-html="markdownHtml"></div>
            </article>
          </div>
          <div class="p-4 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 sticky bottom-0 z-20">
            <button
              class="w-full py-3 rounded-xl border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-bold text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
              @click="handleConfirmChoice('OLD')"
            >
              <LucideIcon name="x" :size="16" /> {{ t('outline.keep_original') }}
            </button>
          </div>
        </div>

        <!-- Right: New -->
        <div class="flex flex-col h-full min-h-0 bg-indigo-50/30 dark:bg-indigo-900/10 relative">
          <div class="p-4 border-b border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-900/20 flex justify-between items-center sticky top-0 z-10">
            <span class="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider flex items-center gap-2">
              <LucideIcon :name="loading ? 'loader-2' : 'refresh-cw'" :size="16" :class="{ 'animate-spin': loading }" />
              {{ t('outline.new_version') }}
            </span>
          </div>
          <div class="flex-1 overflow-y-auto custom-scrollbar p-6">
            <article class="prose dark:prose-invert prose-indigo prose-sm max-w-none">
              <div v-if="newOutlineText" class="space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base" v-html="newMarkdownHtml"></div>
              <div v-else class="h-40 flex items-center justify-center text-indigo-400/50 italic">{{ t('outline.generating_new') }}</div>
            </article>
          </div>
          <div class="p-4 border-t border-indigo-100 dark:border-indigo-900/50 bg-indigo-50/30 dark:bg-indigo-900/20 sticky bottom-0 z-20">
            <button
              :disabled="loading"
              :class="[
                'w-full py-3 rounded-xl font-bold text-sm shadow-lg transition-colors transition-transform flex items-center justify-center gap-2',
                loading
                  ? 'bg-indigo-300 cursor-not-allowed text-white'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white hover:-translate-y-1'
              ]"
              @click="handleConfirmChoice('NEW')"
            >
              <LucideIcon :name="loading ? 'loader-2' : 'check'" :size="16" :class="{ 'animate-spin': loading }" />
              {{ t('outline.replace_new') }}
            </button>
          </div>
        </div>
      </div>

      <!-- --- LOADING SPINNER (For direct generate) --- -->
      <div v-if="mode !== 'COMPARE' && loading && !outlineText" class="absolute inset-0 z-20 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm flex items-center justify-center">
        <div class="flex flex-col items-center gap-3">
          <LucideIcon name="loader-2" :size="40" class="text-indigo-600 animate-spin" />
          <span class="text-sm font-bold text-indigo-600 dark:text-indigo-400">{{ t('outline.crafting') }}</span>
        </div>
      </div>

      <!-- --- PREVIEW MODE --- -->
      <div v-if="mode === 'PREVIEW'" class="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 md:p-6">
        <div class="max-w-4xl mx-auto w-full">
          <article class="prose dark:prose-invert prose-indigo max-w-none">
            <div
              ref="editorRef"
              class="outline-editor space-y-4 font-serif text-slate-800 dark:text-slate-200 leading-relaxed text-sm md:text-base outline-none focus:outline-none min-h-[18rem]"
              :contenteditable="!loading"
              role="textbox"
              aria-multiline="true"
              :aria-label="t('outline.placeholder')"
              :data-placeholder="t('outline.placeholder')"
              spellcheck="false"
              @focus="handleEditorFocus"
              @blur="handleEditorBlur"
              @input="handleEditorInput"
              v-html="displayHtml"
            ></div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.outline-editor:empty::before {
  content: attr(data-placeholder);
  color: rgba(100, 116, 139, 0.85);
}

.dark .outline-editor:empty::before {
  color: rgba(148, 163, 184, 0.6);
}
</style>
