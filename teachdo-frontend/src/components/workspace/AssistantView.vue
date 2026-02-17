<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { ChatMessage, CourseGroup, CourseUnit } from '#root/types';
import { toast } from '@/utils/toast';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';
import { escapeHtml } from '@/utils/safeHtml';

type AssistantViewVariant = 'page' | 'panel';

interface Props {
  currentCourse: CourseGroup;
  currentUnit: CourseUnit | null;
  variant?: AssistantViewVariant;
}

interface Emits {
  (e: 'updateCourse', updates: Partial<CourseGroup>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const { t } = useI18n();

const isPanel = computed(() => props.variant === 'panel');

const assistantEnabled = false;

const messages = ref<ChatMessage[]>([]);
const inputValue = ref('');
const isTyping = ref(false);
const messagesListRef = ref<HTMLDivElement | null>(null);

const greeting = computed(() =>
  assistantEnabled ? t('assistant.greeting', { name: props.currentCourse.name }) : t('assistant.in_progress.greeting', { name: props.currentCourse.name }),
);

const renderInlineStyles = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts
    .map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return `<strong key="${i}" class="font-semibold text-slate-900 dark:text-white">${escapeHtml(part.slice(2, -2))}</strong>`;
      }
      return escapeHtml(part);
    })
    .join('');
};

const renderMessage = (content: string) => {
  if (!content) return '';
  const blocks = content.split('\n');
  return blocks
    .map((line, idx) => {
      if (line.startsWith('### ')) return `<h3 key="${idx}" class="text-base font-bold text-slate-800 dark:text-white mt-4 mb-2">${escapeHtml(line.replace('### ', ''))}</h3>`;
      if (line.startsWith('## ')) return `<h2 key="${idx}" class="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-4 mb-2">${escapeHtml(line.replace('## ', ''))}</h2>`;
      if (line.startsWith('# ')) return `<h1 key="${idx}" class="text-xl font-bold text-slate-900 dark:text-white mt-4 mb-3 border-b pb-2">${escapeHtml(line.replace('# ', ''))}</h1>`;

      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const text = line.replace(/^(\s*)([-*])\s+/, '');
        return `<div key="${idx}" class="flex gap-2 ml-2"><span class="text-indigo-500 font-bold">•</span><span>${renderInlineStyles(text)}</span></div>`;
      }

      if (/^\d+\.\s/.test(line.trim())) {
        return `<div key="${idx}" class="flex gap-2 ml-2"><span class="text-indigo-500 font-bold font-mono text-xs mt-1">${line.trim().split('.')[0]}.</span><span>${renderInlineStyles(
          line.replace(/^\d+\.\s/, ''),
        )}</span></div>`;
      }

      if (!line.trim()) return `<div key="${idx}" class="h-2"></div>`;

      return `<p key="${idx}" class="break-words">${renderInlineStyles(line)}</p>`;
    })
    .join('');
};

const scrollToBottom = () => {
  nextTick(() => {
    const el = messagesListRef.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  });
};

const syncHistory = () => {
  if (props.currentCourse.chatHistory && props.currentCourse.chatHistory.length > 0) {
    messages.value = props.currentCourse.chatHistory.map((msg) => ({
      role: msg.role === 'user' ? 'user' : 'model',
      text: msg.text,
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
    }));
  } else {
    messages.value = [{ role: 'model', text: greeting.value, timestamp: new Date() }];
  }
};

watch(
  () => props.currentCourse.id,
  () => {
    syncHistory();
    scrollToBottom();
  },
  { immediate: true },
);

watch(
  messages,
  (list) => {
    emit('updateCourse', { chatHistory: list });
    scrollToBottom();
  },
  { deep: true },
);

const handleSend = async () => {
  if (!assistantEnabled) {
    toast.info(t('assistant.toast.in_progress'));
    return;
  }
  if (!inputValue.value.trim()) return;
  const userMsg: ChatMessage = { role: 'user', text: inputValue.value.trim(), timestamp: new Date() };
  const history = [...messages.value, userMsg];
  messages.value = history;
  inputValue.value = '';
  isTyping.value = true;

  const streamingMsg: ChatMessage = { role: 'model', text: '', timestamp: new Date() };
  messages.value = [...messages.value, streamingMsg];

  let fullResponse = '';

  try {
    // 当前阶段仅保留页面与路由结构，助教能力后续接入。
    fullResponse = t('assistant.toast.in_progress');
    const updated = [...messages.value];
    const lastIndex = updated.length - 1;
    if (lastIndex >= 0) {
      const last = updated[lastIndex] || streamingMsg;
      updated[lastIndex] = {
        ...last,
        role: last.role ?? 'model',
        timestamp: last.timestamp || new Date(),
        text: fullResponse,
      };
    }
    messages.value = updated;
  } finally {
    isTyping.value = false;
  }
};

const clearHistory = () => {
  messages.value = [{ role: 'model', text: greeting.value, timestamp: new Date() }];
};
</script>

<template>
  <div
    :class="[
      'h-full flex flex-col overflow-hidden',
      isPanel ? '' : 'bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800',
    ]"
  >
    <div
      :class="[
        'bg-slate-50/80 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between backdrop-blur-sm',
        isPanel ? 'px-3 py-3' : 'p-4',
      ]"
    >
      <div class="flex items-center gap-3 min-w-0">
        <div
          :class="[
            'rounded-xl flex items-center justify-center text-white flex-shrink-0',
            isPanel ? 'w-9 h-9 bg-indigo-600 shadow-sm' : 'w-10 h-10 bg-gradient-to-br from-indigo-500 to-indigo-700 shadow-lg shadow-indigo-500/20',
          ]"
        >
          <LucideIcon name="bot" :size="isPanel ? 18 : 20" />
        </div>
        <div class="min-w-0">
          <h3 class="font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <span class="truncate">{{ t('assistant.title') }}</span>
            <span
              v-if="!isPanel"
              class="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wide"
            >
              {{ t('assistant.badge.global') }}
            </span>
          </h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 truncate">
            {{ t('assistant.context_full', { name: props.currentCourse.name }) }}
          </p>
        </div>
      </div>

      <!-- 侧栏：用 IconButton 提升触达与触摸尺寸；页面：保持原文案按钮 -->
      <button
        v-if="isPanel"
        type="button"
        class="w-10 h-10 inline-flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-900/30 text-slate-600 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-900 transition-colors"
        :aria-label="t('assistant.clear')"
        :title="t('assistant.clear')"
        @click="clearHistory"
      >
        <LucideIcon name="trash-2" :size="18" />
      </button>
      <button
        v-else
        type="button"
        class="text-xs font-medium text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        @click="clearHistory"
      >
        {{ t('assistant.clear') }}
      </button>
    </div>

    <div
      :class="[
        'bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200/70 dark:border-amber-800/40',
        isPanel ? 'px-3 py-2.5' : 'px-4 py-3',
      ]"
    >
      <div class="flex items-start gap-3">
        <div
          :class="[
            'rounded-xl bg-white/80 dark:bg-slate-900/40 border border-amber-200 dark:border-amber-800/50 flex items-center justify-center text-amber-600 dark:text-amber-300 flex-shrink-0',
            isPanel ? 'w-8 h-8' : 'w-9 h-9',
          ]"
        >
          <LucideIcon name="alert-triangle" :size="isPanel ? 16 : 18" />
        </div>
        <div class="min-w-0">
          <div class="text-sm font-bold text-amber-900 dark:text-amber-100">{{ t('assistant.in_progress.title') }}</div>
          <div class="text-xs text-amber-700 dark:text-amber-200 mt-0.5 leading-relaxed">{{ t('assistant.in_progress.desc') }}</div>
        </div>
      </div>
    </div>

    <div
      ref="messagesListRef"
      :class="[
        'flex-1 overflow-y-auto custom-scrollbar bg-slate-50/50 dark:bg-slate-950/50',
        isPanel ? 'p-3 space-y-3' : 'p-6 space-y-6',
      ]"
    >
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="['flex gap-4 animate-fade-in', msg.role === 'user' ? 'justify-end' : 'justify-start']"
      >
        <div v-if="msg.role === 'model'" class="w-8 h-8 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
          <LucideIcon name="sparkles" :size="16" class="text-indigo-500" />
        </div>

        <div
          :class="[
            isPanel ? 'max-w-[92%] rounded-xl p-3 text-sm shadow-sm' : 'max-w-[85%] rounded-xl p-5 text-sm shadow-sm',
            msg.role === 'user'
              ? 'bg-indigo-600 text-white shadow-indigo-500/20'
              : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-slate-700 shadow-slate-200/50 dark:shadow-none',
          ]"
        >
          <div v-if="msg.role === 'model'" class="prose dark:prose-invert prose-sm max-w-none text-sm leading-relaxed space-y-2" v-html="renderMessage(msg.text)" />
          <div v-else class="whitespace-pre-wrap leading-relaxed">{{ msg.text }}</div>
        </div>

        <div v-if="msg.role === 'user'" class="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1 overflow-hidden">
          <LucideIcon name="user" :size="20" class="text-slate-500 dark:text-slate-400" />
        </div>
      </div>

      <div v-if="isTyping && messages[messages.length - 1]?.role === 'user'" class="flex gap-4 justify-start animate-fade-in">
        <div class="w-8 h-8 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center flex-shrink-0 shadow-sm">
          <LucideIcon name="sparkles" :size="16" class="text-indigo-500" />
        </div>
        <div
          :class="[
            'bg-white dark:bg-slate-800 rounded-2xl rounded-bl-none border border-slate-100 dark:border-slate-700 flex items-center gap-1.5 shadow-sm',
            isPanel ? 'p-3' : 'p-4',
          ]"
        >
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-75"></div>
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-150"></div>
        </div>
      </div>
    </div>

    <div :class="['bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800', isPanel ? 'p-3' : 'p-4']">
      <div class="relative group">
        <textarea
          v-model="inputValue"
          :class="[
            'w-full bg-slate-100 dark:bg-slate-800 border-2 border-transparent focus:border-indigo-500/30 rounded-xl pl-4 pr-14 text-sm outline-none dark:text-white transition-all resize-none custom-scrollbar shadow-inner',
            isPanel ? 'py-3 h-12 max-h-28' : 'py-3.5 h-14 max-h-32',
          ]"
          :placeholder="assistantEnabled ? t('assistant.placeholder') : t('assistant.in_progress.placeholder')"
          :disabled="isTyping || !assistantEnabled"
          @keydown.enter.prevent="(event) => { if (!event.shiftKey && !isTyping) handleSend(); }"
        />
        <button
          type="button"
          :disabled="isTyping || !assistantEnabled || !inputValue.trim()"
          :class="[
            'absolute right-2 top-2 p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-all shadow-lg shadow-indigo-500/20',
            isPanel ? '' : 'hover:scale-105 active:scale-95',
          ]"
          @click="handleSend"
        >
          <LucideIcon name="send" :size="16" />
        </button>
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
</style>
