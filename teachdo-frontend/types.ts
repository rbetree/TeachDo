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
  folderId?: number;
  /**
   * 来源类型（用于知识库列表展示溯源信息）
   * - upload: 用户上传
   * - material: 由某个教学资料生成
   */
  sourceType?: 'upload' | 'material';
  sourceMaterialId?: string;
  sourceMaterialTitle?: string;
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

export interface EditorViewport {
  size: number;
  ratio: number;
}

export interface EditorDocument {
  title: string;
  templateId: string;
  width: number;
  height: number;
  theme: any;
  slides: any[];
  viewport: EditorViewport;
  updatedAt: number;
}

export interface TeachingMaterial {
  id: string;
  title: string;
  subject: string;
  description: string;
  objectives: string;
  createdAt: Date;
  /**
   * 引用的知识库文件 IDs（全局 KB 的 file_id）
   *
   * 说明：
   * - 创建教学资料时可选
   * - 生成 PPT/大纲时可临时覆盖
   */
  kbFileIds: string[];
  outlineContent?: string;
  lessonPlan?: LessonPlan;
  presentation?: Presentation;
  selectedTemplateId?: string;
  editorDocument?: EditorDocument;
}
