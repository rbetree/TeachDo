export enum ViewState {
  DASHBOARD = 'DASHBOARD',
  LESSON_PLAN = 'LESSON_PLAN',
  PPT_GENERATOR = 'PPT_GENERATOR',
  OUTLINE = 'OUTLINE',
  ASSISTANT = 'ASSISTANT',
  KNOWLEDGE_BASE = 'KNOWLEDGE_BASE',
}

export type Language = 'zh' | 'en';

export interface KBFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'processing' | 'ready' | 'error';
  uploadedAt: Date;
  progress?: number;
}

interface LessonPlanSection {
  step: string;
  duration: string;
  activity: string;
}

export interface LessonPlan {
  title: string;
  targetAudience: string;
  duration: string;
  objectives: string[];
  materials: string[];
  procedure: LessonPlanSection[];
  homework: string;
}

interface Slide {
  title: string;
  content: string[];
  notes: string;
}

export interface Presentation {
  theme: string;
  slides: Slide[];
}

export interface PPTTemplate {
  id: string;
  name: string;
  thumbnailColor: string;
  styleDescription: string;
  file?: string;
  coverUrl?: string;
  rawTemplate?: any;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
}

export interface CourseUnit {
  id: string;
  title: string;
  objectives: string;
  outlineContent?: string;
  lessonPlan?: LessonPlan;
  presentation?: Presentation;
  selectedTemplateId?: string;
}

export interface CourseGroup {
  id: string;
  name: string;
  subject: string;
  description: string;
  createdAt: Date;
  units: CourseUnit[];
  kbFiles?: KBFile[];
  chatHistory?: ChatMessage[];
}
