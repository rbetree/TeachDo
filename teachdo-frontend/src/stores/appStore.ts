import { defineStore, type Pinia } from 'pinia';
import type {
  CourseGroup,
  CourseUnit,
  KBFile,
  ChatMessage,
  Language,
} from '#root/types';
import { setLocale } from '@/i18n';

const STORAGE_KEY = 'teachdo_app_store';

type ThemeMode = 'light' | 'dark';

export interface AppStoreState {
  courses: CourseGroup[];
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
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
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
    },
    upsertCourse(course: CourseGroup) {
      const index = this.courses.findIndex((item) => item.id === course.id);
      if (index >= 0) {
        this.courses[index] = course;
      } else {
        this.courses.push(course);
      }
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
      const updated = updater([...target.units]);
      this.courses[index] = {
        ...target,
        units: updated,
      };
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
  store.$subscribe((_mutation, state) => {
    persistState(state);
    applyTheme(state.theme);
    applyLanguage(state.language);
  }, { detached: true });
  if (!store.courses.length) {
    store.setCourses(createDemoCourses());
  }
  return store;
};
