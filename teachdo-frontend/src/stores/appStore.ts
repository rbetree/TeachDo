import { defineStore, type Pinia } from 'pinia';
import type {
  CourseGroup,
  CourseUnit,
  KBFile,
  ChatMessage,
  Language,
} from '#root/types';
import { setLocale } from '@/i18n';
import { loadCourseLarge, loadUnitLargeByCourse, saveCourseLarge, saveUnitLarge } from '@/utils/appStoreIdb';

const STORAGE_KEY = 'teachdo_app_store';
const STORAGE_VERSION = 2 as const;

type ThemeMode = 'light' | 'dark';

export interface AppStoreState {
  courses: CourseGroup[];
  currentCourseId: string | null;
  currentUnitId: string | null;
  theme: ThemeMode;
  language: Language;
}

interface PersistedCourseUnitLiteV2 {
  id: string;
  title: string;
  objectives: string;
  selectedTemplateId?: string;
}

interface PersistedCourseLiteV2 {
  id: string;
  name: string;
  subject: string;
  description: string;
  createdAt: string;
  units: PersistedCourseUnitLiteV2[];
}

interface PersistedAppStoreLiteV2 {
  version: typeof STORAGE_VERSION;
  courses: PersistedCourseLiteV2[];
  currentCourseId: string | null;
  currentUnitId: string | null;
  theme: ThemeMode;
  language: Language;
}

const defaultState: AppStoreState = {
  courses: [],
  currentCourseId: null,
  currentUnitId: null,
  theme: 'light',
  language: 'zh',
};

function createDemoCourses(): CourseGroup[] {
  return [
    {
      id: 'demo-math',
      name: '八年级数学（上）',
      subject: '数学',
      description: '重点讲解代数基础与几何初步，学生基础中等。',
      createdAt: new Date(),
      kbFiles: [
        {
          id: 'kb-1',
          name: '义务教育数学课程标准(2022年版).pdf',
          size: 4500000,
          type: 'pdf',
          status: 'ready',
          uploadedAt: new Date(),
          folderId: 0,
        },
      ],
      units: [
        { id: 'unit-1', title: '第11章 三角形', objectives: '掌握三角形的基本性质', outlineContent: '' },
        { id: 'unit-2', title: '第12章 全等三角形', objectives: '理解全等判定', outlineContent: '' },
      ],
    },
    {
      id: 'demo-history',
      name: '高一历史必修',
      subject: '历史',
      description: '新课标课程，注重史料分析能力的培养。',
      createdAt: new Date(),
      units: [
        { id: 'unit-3', title: '中国古代文明', objectives: '了解夏商周的发展脉络', outlineContent: '' },
      ],
    },
  ];
}

const isBrowser = typeof window !== 'undefined';

function reviveCourses(raw: unknown): CourseGroup[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((course) => ({
    ...course,
    createdAt: course?.createdAt ? new Date(course.createdAt) : new Date(),
    units: Array.isArray(course?.units)
      ? course.units.map((unit: CourseUnit) => ({
          ...unit,
        }))
      : [],
    kbFiles: Array.isArray(course?.kbFiles)
      ? course.kbFiles.map((file: KBFile) => ({
          ...file,
          uploadedAt: file?.uploadedAt ? new Date(file.uploadedAt) : new Date(),
          folderId: typeof file?.folderId === 'number' ? file.folderId : 0,
        }))
      : [],
    chatHistory: Array.isArray(course?.chatHistory)
      ? course.chatHistory.map((msg: ChatMessage) => ({
          ...msg,
          timestamp: msg?.timestamp ? new Date(msg.timestamp) : new Date(),
        }))
      : [],
  })) as CourseGroup[];
}

function reviveCoursesLiteV2(raw: unknown): CourseGroup[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((course) => ({
    id: typeof course?.id === 'string' ? course.id : `course-${Date.now()}`,
    name: typeof course?.name === 'string' ? course.name : '',
    subject: typeof course?.subject === 'string' ? course.subject : '',
    description: typeof course?.description === 'string' ? course.description : '',
    createdAt: course?.createdAt ? new Date(course.createdAt) : new Date(),
    units: Array.isArray(course?.units)
      ? course.units.map((unit: CourseUnit) => ({
          id: typeof unit?.id === 'string' ? unit.id : `unit-${Date.now()}`,
          title: typeof unit?.title === 'string' ? unit.title : '',
          objectives: typeof unit?.objectives === 'string' ? unit.objectives : '',
          selectedTemplateId: typeof (unit as any)?.selectedTemplateId === 'string' ? (unit as any).selectedTemplateId : undefined,
        }))
      : [],
    // 大对象会在 setupAppStore 中异步从 IndexedDB 回填
    kbFiles: [],
    chatHistory: [],
  })) as CourseGroup[];
}

function toLiteStateV2(state: AppStoreState): PersistedAppStoreLiteV2 {
  return {
    version: STORAGE_VERSION,
    theme: state.theme,
    language: state.language,
    currentCourseId: state.currentCourseId,
    currentUnitId: state.currentUnitId,
    courses: state.courses.map((course) => ({
      id: course.id,
      name: course.name,
      subject: course.subject,
      description: course.description,
      createdAt: (course.createdAt instanceof Date ? course.createdAt : new Date(course.createdAt)).toISOString(),
      units: (course.units || []).map((unit) => ({
        id: unit.id,
        title: unit.title,
        objectives: unit.objectives,
        selectedTemplateId: typeof unit.selectedTemplateId === 'string' ? unit.selectedTemplateId : undefined,
      })),
    })),
  };
}

function loadState(): AppStoreState {
  if (!isBrowser) {
    return { ...defaultState };
  }
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (!saved) {
    return { ...defaultState };
  }
  try {
    const parsed = JSON.parse(saved) as Record<string, unknown>;
    const theme = parsed.theme === 'dark' ? 'dark' : 'light';
    const language: Language = parsed.language === 'en' ? 'en' : 'zh';
    const currentCourseId = typeof parsed.currentCourseId === 'string' ? parsed.currentCourseId : null;
    const currentUnitId = typeof parsed.currentUnitId === 'string' ? parsed.currentUnitId : null;
    // v2：localStorage 仅存轻量元数据（大对象走 IndexedDB）
    if (parsed.version === STORAGE_VERSION) {
      return {
        ...defaultState,
        theme,
        language,
        currentCourseId,
        currentUnitId,
        courses: reviveCoursesLiteV2(parsed.courses),
      };
    }
    return {
      ...defaultState,
      theme,
      language,
      currentCourseId,
      currentUnitId,
      courses: reviveCourses(parsed.courses),
    };
  } catch (error) {
    console.warn('恢复 Pinia 状态失败，使用默认值', error);
    return { ...defaultState };
  }
}

function persistState(state: AppStoreState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(toLiteStateV2(state)));
  } catch (e) {
    console.warn('写入 localStorage 失败（已忽略）', e);
  }
}

function persistLegacyState(state: AppStoreState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('写入 localStorage(legacy) 失败（已忽略）', e);
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
    currentCourse: (state): CourseGroup | null =>
      state.courses.find((course) => course.id === state.currentCourseId) ?? null,
    currentUnit: (state): CourseUnit | null => {
      if (!state.currentCourseId) return null;
      const course = state.courses.find((item) => item.id === state.currentCourseId);
      if (!course) return null;
      return course.units.find((unit) => unit.id === state.currentUnitId) ?? null;
    },
    isDarkMode: (state): boolean => state.theme === 'dark',
  },
  actions: {
    setCourses(courses: CourseGroup[]) {
      this.courses = courses;
      const [firstCourse] = courses;
      if (firstCourse) {
        this.currentCourseId = firstCourse.id;
        this.currentUnitId = firstCourse.units[0]?.id ?? null;
      } else {
        this.currentCourseId = null;
        this.currentUnitId = null;
      }

      // 大对象异步写入 IndexedDB（不阻断 UI）
      void (async () => {
        for (const course of courses) {
          await saveCourseLarge(course);
          for (const unit of course.units || []) {
            await saveUnitLarge(course.id, unit);
          }
        }
      })();
    },
    upsertCourse(course: CourseGroup) {
      const index = this.courses.findIndex((item) => item.id === course.id);
      const prev = index >= 0 ? this.courses[index] : null;
      if (index >= 0) {
        this.courses[index] = course;
      } else {
        this.courses.push(course);
      }

      // 大对象异步写入 IndexedDB（只写入发生变化的部分）
      void (async () => {
        if (!prev || prev.kbFiles !== course.kbFiles || prev.chatHistory !== course.chatHistory) {
          await saveCourseLarge(course);
        }

        const prevById = new Map<string, CourseUnit>();
        for (const u of prev?.units || []) prevById.set(u.id, u);
        for (const u of course.units || []) {
          const old = prevById.get(u.id);
          if (!old || old !== u) {
            await saveUnitLarge(course.id, u);
          }
        }
      })();
    },
    selectCourse(courseId: string | null) {
      this.currentCourseId = courseId;
      if (courseId === null) {
        this.currentUnitId = null;
        return;
      }
      const target = this.courses.find((item) => item.id === courseId);
      this.currentUnitId = target?.units[0]?.id ?? null;
    },
    selectUnit(unitId: string | null) {
      this.currentUnitId = unitId;
    },
    updateCourseUnits(courseId: string, updater: (units: CourseUnit[]) => CourseUnit[]) {
      const index = this.courses.findIndex((item) => item.id === courseId);
      if (index === -1) return;
      const target = this.courses[index];
      if (!target) return;
      const prevUnits = target.units || [];
      const updated = updater([...prevUnits]);
      this.courses[index] = {
        ...target,
        units: updated,
      };

      // 只对变更的 unit 写入 IndexedDB，避免不必要的大写入
      void (async () => {
        const prevById = new Map<string, CourseUnit>();
        for (const u of prevUnits) prevById.set(u.id, u);
        for (const u of updated) {
          const old = prevById.get(u.id);
          if (!old || old !== u) {
            await saveUnitLarge(courseId, u);
          }
        }
      })();
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
  if (!isBrowser) {
    return store;
  }
  applyTheme(store.theme);
  applyLanguage(store.language);

  // 保护 legacy 数据：如果本地还是旧格式（无 version），在完成迁移之前不要覆盖 localStorage，避免在 IndexedDB 不可用时造成数据丢失。
  let allowLitePersistence = true;
  let needsMigration = false;
  const savedAtBoot = window.localStorage.getItem(STORAGE_KEY);
  if (savedAtBoot) {
    try {
      const parsed = JSON.parse(savedAtBoot) as Record<string, unknown>;
      if (parsed.version !== STORAGE_VERSION) {
        allowLitePersistence = false;
        needsMigration = true;
      }
    } catch {
      // 本地数据损坏时允许直接覆盖为 v2
      allowLitePersistence = true;
      needsMigration = false;
    }
  }

  store.$subscribe((_mutation, state) => {
    if (allowLitePersistence) persistState(state);
    else persistLegacyState(state);
    applyTheme(state.theme);
    applyLanguage(state.language);
  }, { detached: true });

  // localStorage 旧格式（无 version）的一次性迁移：将大对象写入 IndexedDB，然后把 localStorage 压缩为 v2 轻量结构。
  void (async () => {
    if (!needsMigration) return;

    // 迁移的源数据已经在 store 中（loadState 已复活 Date）
    let ok = true;
    for (const course of store.courses) {
      ok = (await saveCourseLarge(course)) && ok;
      for (const unit of course.units || []) {
        ok = (await saveUnitLarge(course.id, unit)) && ok;
      }
    }
    if (!ok) {
      console.warn('IndexedDB 迁移失败：为避免数据丢失，已保留 legacy localStorage（不会压缩为 v2）。');
      return;
    }

    // 迁移成功后才允许覆盖 localStorage
    allowLitePersistence = true;
    persistState(store.$state);
  })();

  // 若 localStorage 为 v2 轻量结构，则从 IndexedDB 异步回填大对象字段（outline/lesson/presentation/editorDocument/kb/chat）。
  void (async () => {
    if (needsMigration) return;
    if (!allowLitePersistence) return;

    const patchedCourses = store.courses.map((course) => ({ ...course }));
    for (const course of patchedCourses) {
      const courseLarge = await loadCourseLarge(course.id);
      if (courseLarge) {
        // 仅在当前内存里为空时回填，避免覆盖用户正在进行的修改
        if (!Array.isArray(course.kbFiles) || course.kbFiles.length === 0) {
          course.kbFiles = courseLarge.kbFiles;
        }
        if (!Array.isArray(course.chatHistory) || course.chatHistory.length === 0) {
          course.chatHistory = courseLarge.chatHistory;
        }
      }

      const unitLargeMap = await loadUnitLargeByCourse(course.id);
      if (unitLargeMap.size === 0) continue;
      course.units = (course.units || []).map((unit) => {
        const record = unitLargeMap.get(unit.id);
        if (!record) return unit;
        return {
          ...unit,
          outlineContent: unit.outlineContent || record.outlineContent || unit.outlineContent,
          lessonPlan: unit.lessonPlan ?? record.lessonPlan ?? unit.lessonPlan,
          presentation: unit.presentation ?? record.presentation ?? unit.presentation,
          editorDocument: unit.editorDocument ?? record.editorDocument ?? unit.editorDocument,
        };
      });
    }

    store.courses = patchedCourses;
  })();

  if (!store.courses.length) {
    store.setCourses(createDemoCourses());
  }
  return store;
};
