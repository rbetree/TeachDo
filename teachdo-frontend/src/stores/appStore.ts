import { defineStore, type Pinia } from 'pinia';
import type { ChatMessage, KBFile, Language, TeachingMaterial } from '#root/types';
import { setLocale } from '@/i18n';
import { deleteLegacyIndexedDb, deleteMaterialLarge, loadAppLarge, loadMaterialLarge, saveAppLarge, saveMaterialLarge } from '@/utils/appStoreIdb';

export const KB_USER_ID = 'default_user' as const;

const STORAGE_KEY = 'teachdo_app_store_material';
const STORAGE_VERSION = 1 as const;

type ThemeMode = 'light' | 'dark';

export interface AppStoreState {
  materials: TeachingMaterial[];
  currentMaterialId: string | null;
  kbFiles: KBFile[];
  /**
   * 助教：全局单会话（仅内存，不做持久化）。
   * - 由前端维护 messages，后端不保存会话
   * - 刷新页面即清空
   */
  assistantMessages: ChatMessage[];
  theme: ThemeMode;
  language: Language;
}

interface PersistedMaterialLiteV1 {
  id: string;
  title: string;
  subject: string;
  description: string;
  objectives: string;
  createdAt: string;
  kbFileIds: string[];
  selectedTemplateId?: string;
}

interface PersistedAppStoreLiteV1 {
  version: typeof STORAGE_VERSION;
  materials: PersistedMaterialLiteV1[];
  currentMaterialId: string | null;
  theme: ThemeMode;
  language: Language;
}

const defaultState: AppStoreState = {
  materials: [],
  currentMaterialId: null,
  kbFiles: [],
  assistantMessages: [],
  theme: 'light',
  language: 'zh',
};

function createDemoMaterials(): TeachingMaterial[] {
  return [
    {
      id: 'demo-material-1',
      title: '三角形的基本性质',
      subject: '数学',
      description: '八年级上册 · 重点讲解三角形三边关系与内角和。',
      objectives: '理解三角形三边关系；掌握内角和定理；能解决基础应用题。',
      createdAt: new Date(),
      kbFileIds: [],
      outlineContent: '',
    },
    {
      id: 'demo-material-2',
      title: '中国古代文明概览',
      subject: '历史',
      description: '高一必修 · 以时间线梳理早期文明发展脉络。',
      objectives: '掌握核心时间线；能结合史料进行简单分析；形成宏观框架。',
      createdAt: new Date(),
      kbFileIds: [],
      outlineContent: '',
    },
  ];
}

const isBrowser = typeof window !== 'undefined';

function normalizeStringArray(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((x) => typeof x === 'string').map((x) => x.trim()).filter(Boolean);
}

function reviveMaterialsLiteV1(raw: unknown): TeachingMaterial[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((material) => ({
    id: typeof material?.id === 'string' ? material.id : `material-${Date.now()}`,
    title: typeof material?.title === 'string' ? material.title : '',
    subject: typeof material?.subject === 'string' ? material.subject : '',
    description: typeof material?.description === 'string' ? material.description : '',
    objectives: typeof material?.objectives === 'string' ? material.objectives : '',
    createdAt: material?.createdAt ? new Date(material.createdAt) : new Date(),
    kbFileIds: normalizeStringArray(material?.kbFileIds),
    selectedTemplateId: typeof (material as any)?.selectedTemplateId === 'string' ? (material as any).selectedTemplateId : undefined,
    // 大对象会在 setupAppStore 中异步从 IndexedDB 回填
    outlineContent: '',
    lessonPlan: undefined,
    presentation: undefined,
    editorDocument: undefined,
  })) as TeachingMaterial[];
}

function toLiteStateV1(state: AppStoreState): PersistedAppStoreLiteV1 {
  return {
    version: STORAGE_VERSION,
    theme: state.theme,
    language: state.language,
    currentMaterialId: state.currentMaterialId,
    materials: state.materials.map((material) => ({
      id: material.id,
      title: material.title,
      subject: material.subject,
      description: material.description,
      objectives: material.objectives,
      createdAt: (material.createdAt instanceof Date ? material.createdAt : new Date(material.createdAt)).toISOString(),
      kbFileIds: Array.isArray(material.kbFileIds) ? material.kbFileIds : [],
      selectedTemplateId: typeof material.selectedTemplateId === 'string' ? material.selectedTemplateId : undefined,
    })),
  };
}

function loadState(): AppStoreState {
  if (!isBrowser) return { ...defaultState };

  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (!saved) return { ...defaultState };

  try {
    const parsed = JSON.parse(saved) as Record<string, unknown>;
    if (parsed.version !== STORAGE_VERSION) return { ...defaultState };

    const theme = parsed.theme === 'dark' ? 'dark' : 'light';
    const language: Language = parsed.language === 'en' ? 'en' : 'zh';
    const currentMaterialId = typeof parsed.currentMaterialId === 'string' ? parsed.currentMaterialId : null;

    return {
      ...defaultState,
      theme,
      language,
      currentMaterialId,
      materials: reviveMaterialsLiteV1(parsed.materials),
    };
  } catch (error) {
    console.warn('恢复 Pinia 状态失败，使用默认值', error);
    return { ...defaultState };
  }
}

function persistState(state: AppStoreState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(toLiteStateV1(state)));
  } catch (e) {
    console.warn('写入 localStorage 失败（已忽略）', e);
  }
}

function applyTheme(theme: ThemeMode) {
  if (!isBrowser) return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

function applyLanguage(language: Language) {
  setLocale(language);
}

export const useAppStore = defineStore('app', {
  state: (): AppStoreState => loadState(),
  getters: {
    currentMaterial: (state): TeachingMaterial | null =>
      state.materials.find((m) => m.id === state.currentMaterialId) ?? null,
    isDarkMode: (state): boolean => state.theme === 'dark',
  },
  actions: {
    setMaterials(materials: TeachingMaterial[]) {
      this.materials = materials;
      this.currentMaterialId = materials[0]?.id ?? null;

      // 大对象异步写入 IndexedDB（不阻断 UI）
      void (async () => {
        for (const material of materials) {
          await saveMaterialLarge(material.id, {
            outlineContent: material.outlineContent ?? '',
            lessonPlan: material.lessonPlan ?? null,
            presentation: material.presentation ?? null,
            editorDocument: material.editorDocument ?? null,
          });
        }
      })();
    },
    upsertMaterial(material: TeachingMaterial) {
      const index = this.materials.findIndex((item) => item.id === material.id);
      const prev = index >= 0 ? this.materials[index] : null;
      if (index >= 0) {
        this.materials[index] = material;
      } else {
        this.materials.push(material);
      }

      if (!this.currentMaterialId) {
        this.currentMaterialId = material.id;
      }

      void (async () => {
        const largeChanged =
          !prev ||
          prev.outlineContent !== material.outlineContent ||
          prev.lessonPlan !== material.lessonPlan ||
          prev.presentation !== material.presentation ||
          prev.editorDocument !== material.editorDocument;
        if (!largeChanged) return;
        await saveMaterialLarge(material.id, {
          outlineContent: material.outlineContent ?? '',
          lessonPlan: material.lessonPlan ?? null,
          presentation: material.presentation ?? null,
          editorDocument: material.editorDocument ?? null,
        });
      })();
    },
    selectMaterial(materialId: string | null) {
      this.currentMaterialId = materialId;
    },
    patchMaterial(materialId: string, updates: Partial<TeachingMaterial>) {
      const index = this.materials.findIndex((m) => m.id === materialId);
      if (index === -1) return;
      const prev = this.materials[index];
      if (!prev) return;
      this.upsertMaterial({ ...prev, ...updates });
    },
    removeMaterial(materialId: string): boolean {
      const index = this.materials.findIndex((m) => m.id === materialId);
      if (index === -1) return false;

      this.materials = this.materials.filter((m) => m.id !== materialId);
      if (this.currentMaterialId === materialId) {
        this.currentMaterialId = null;
      }

      void deleteMaterialLarge(materialId);
      return true;
    },
    setKbFiles(files: KBFile[]) {
      this.kbFiles = files;
      void saveAppLarge({ kbFiles: files });
    },
    setAssistantMessages(messages: ChatMessage[]) {
      this.assistantMessages = messages;
    },
    appendAssistantMessage(message: ChatMessage) {
      this.assistantMessages.push(message);
    },
    updateLastAssistantMessageText(text: string) {
      const last = this.assistantMessages[this.assistantMessages.length - 1];
      if (!last) return;
      last.text = text;
    },
    setTheme(theme: ThemeMode) {
      this.theme = theme;
      applyTheme(theme);
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
    },
    setLanguage(language: Language) {
      this.language = language;
      applyLanguage(language);
    },
  },
});

export const setupAppStore = (pinia: Pinia) => {
  const store = useAppStore(pinia);
  if (!isBrowser) return store;

  applyTheme(store.theme);
  applyLanguage(store.language);

  // 开发阶段：不做旧数据迁移。检测到旧结构则直接重置（localStorage + IndexedDB）。
  void (async () => {
    try {
      window.localStorage.removeItem('teachdo_app_store');
    } catch {
      // ignore
    }
    await deleteLegacyIndexedDb();
  })();

  store.$subscribe(
    (mutation, state) => {
      // 助教对话为高频更新（流式），且不做持久化；跳过持久化可避免频繁写 localStorage 卡顿。
      const events = (mutation as any)?.events as Array<{ key?: unknown }> | undefined;
      if (Array.isArray(events) && events.length > 0) {
        const onlyAssistant = events.every((e) => typeof e?.key === 'string' && (e.key as string).startsWith('assistantMessages'));
        if (onlyAssistant) return;
      }
      persistState(state);
      applyTheme(state.theme);
      applyLanguage(state.language);
    },
    { detached: true },
  );

  // 从 IndexedDB 异步回填大对象字段（outline/lesson/presentation/editorDocument/kbFiles）。
  void (async () => {
    const appLarge = await loadAppLarge();
    if (appLarge && (!Array.isArray(store.kbFiles) || store.kbFiles.length === 0)) {
      store.kbFiles = appLarge.kbFiles;
    }

    const patched = store.materials.map((m) => ({ ...m }));
    for (const material of patched) {
      const record = await loadMaterialLarge(material.id);
      if (!record) continue;
      if (!material.outlineContent) material.outlineContent = record.outlineContent || '';
      if (material.lessonPlan == null) material.lessonPlan = record.lessonPlan ?? undefined;
      if (material.presentation == null) material.presentation = record.presentation ?? undefined;
      if (material.editorDocument == null) material.editorDocument = record.editorDocument ?? undefined;
    }
    store.materials = patched;
  })();

  if (!store.materials.length) {
    store.setMaterials(createDemoMaterials());
  }

  return store;
};
