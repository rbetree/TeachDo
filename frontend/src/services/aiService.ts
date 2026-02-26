import { getTemplateFileData, getTemplates, streamAipptSlides, MOCK_TEMPLATES } from '@/services/ai/pptService';
import { generateOutline } from '@/services/ai/outlineService';
import { kbDeleteFile, kbExportFile, kbListFiles, kbUpload, vectorizeTextToKb } from '@/services/ai/kbService';
import { streamAssistantReply } from '@/services/ai/assistantService';
import { exportLessonDocx, getLessonTemplates, streamLessonPlan } from '@/services/ai/lessonService';

/**
 * AI Service Layer - TeachDo Integration
 *
 * 说明：
 * - aiService 作为对外的统一入口，内部按领域拆分（ppt/outline/kb）
 * - 调用方保持 `aiService.xxx()` 不变，便于渐进式重构
 */
export const aiService = {
  // PPT
  getTemplates,
  getTemplateFileData,
  streamAipptSlides,

  // Outline
  generateOutline,

  // Lesson
  streamLessonPlan,
  exportLessonDocx,
  getLessonTemplates,

  // KB
  kbUpload,
  kbListFiles,
  kbDeleteFile,
  kbExportFile,
  vectorizeTextToKb,

  // Assistant
  streamAssistantReply,
};

// 外部仍可按需引用 mock 模板（调试/兜底用）
export { MOCK_TEMPLATES };
