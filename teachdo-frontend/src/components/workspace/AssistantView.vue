<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import type { ChatMessage, CourseGroup, CourseUnit } from '#root/types';
import { aiService } from '@/services/aiService';
import LucideIcon from '@/components/common/LucideIcon.vue';
import { useI18n } from 'vue-i18n';

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

const messages = ref<ChatMessage[]>([]);
const inputValue = ref('');
const isTyping = ref(false);
const messagesEndRef = ref<HTMLDivElement | null>(null);

const greeting = computed(() => t('assistant.greeting', { name: props.currentCourse.name }));

const renderInlineStyles = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts
    .map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return `<strong key="${i}" class="font-semibold text-slate-900 dark:text-white">${part.slice(2, -2)}</strong>`;
      }
      return part;
    })
    .join('');
};

const renderMessage = (content: string) => {
  if (!content) return '';
  const blocks = content.split('\n');
  return blocks
    .map((line, idx) => {
      if (line.startsWith('### ')) return `<h3 key="${idx}" class="text-base font-bold text-slate-800 dark:text-white mt-4 mb-2">${line.replace('### ', '')}</h3>`;
      if (line.startsWith('## ')) return `<h2 key="${idx}" class="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-4 mb-2">${line.replace('## ', '')}</h2>`;
      if (line.startsWith('# ')) return `<h1 key="${idx}" class="text-xl font-bold text-slate-900 dark:text-white mt-4 mb-3 border-b pb-2">${line.replace('# ', '')}</h1>`;

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
    messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' });
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
    await aiService.chatWithAssistant(props.currentCourse, props.currentUnit, history, userMsg.text, (chunk) => {
      fullResponse += chunk;
      const updated = [...messages.value];
      const lastIndex = updated.length - 1;
      if (lastIndex >= 0) {
        const last = updated[lastIndex] || streamingMsg;
        updated[lastIndex] = { ...last, role: last.role ?? 'model', text: fullResponse, timestamp: last.timestamp || new Date() };
      }
      messages.value = updated;
    });
  } catch (e) {
    console.error(e);
    const updated = [...messages.value];
    const lastIndex = updated.length - 1;
    if (lastIndex >= 0) {
      const last = updated[lastIndex] || streamingMsg;
      updated[lastIndex] = {
        ...last,
        role: last.role ?? 'model',
        timestamp: last.timestamp || new Date(),
        text: t('assistant.error'),
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
  <div class="h-full flex flex-col bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
    <div class="p-4 bg-slate-50/80 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
          <LucideIcon name="bot" :size="20" />
        </div>
        <div>
          <h3 class="font-bold text-slate-800 dark:text-white flex items-center gap-2">
            {{ t('assistant.title') }}
            <span class="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wide">
              {{ t('assistant.badge.global') }}
            </span>
          </h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 max-w-[300px] truncate">
            {{ t('assistant.context_full', { name: props.currentCourse.name }) }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="text-xs font-medium text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        @click="clearHistory"
      >
        {{ t('assistant.clear') }}
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-slate-50/50 dark:bg-slate-950/50">
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
            'max-w-[85%] rounded-xl p-5 text-sm shadow-sm',
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
        <div class="bg-white dark:bg-slate-800 p-4 rounded-2xl rounded-bl-none border border-slate-100 dark:border-slate-700 flex items-center gap-1.5 shadow-sm">
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-75"></div>
          <div class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce delay-150"></div>
        </div>
      </div>
      <div ref="messagesEndRef" />
    </div>

    <div class="p-4 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
      <div class="relative group">
        <textarea
          v-model="inputValue"
          class="w-full bg-slate-100 dark:bg-slate-800 border-2 border-transparent focus:border-indigo-500/30 rounded-xl pl-4 pr-14 py-3.5 text-sm outline-none dark:text-white transition-all resize-none h-14 max-h-32 custom-scrollbar shadow-inner"
          :placeholder="t('assistant.placeholder')"
          :disabled="isTyping"
          @keydown.enter.prevent="(event) => { if (!event.shiftKey && !isTyping) handleSend(); }"
        />
        <button
          type="button"
          :disabled="isTyping || !inputValue.trim()"
          class="absolute right-2 top-2 p-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white rounded-lg transition-all shadow-lg shadow-indigo-500/20 hover:scale-105 active:scale-95"
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
