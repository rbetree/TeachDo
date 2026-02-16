import type { CourseGroup, CourseUnit, Presentation, PPTTemplate } from "#root/types";
import { SseParser, stripJsonCodeFence } from "@/utils/sse";
import type { AIPPTSlide } from "@/editor-runtime/types/AIPPT";

/**
 * AI Service Layer - TeachDo Integration
 * 
 * Unified entry point for all LLM interactions.
 * All requests are routed through the backend (TeachDo API).
 * No client-side API keys are used.
 */

// 统一走相对路径 /api（开发：Vite proxy；生产：Nginx 反代）
const BASE_API = "/api";
const apiUrl = (path: string) => `${BASE_API}${path.startsWith("/") ? path : `/${path}`}`;

// Fallback Mock Templates (Updated to Solid Colors)
export const MOCK_TEMPLATES: PPTTemplate[] = [
  { id: 'classic_blue', name: '商务蓝', thumbnailColor: 'bg-blue-600', styleDescription: 'Professional, Clean' },
  { id: 'warm_orange', name: '活力橙', thumbnailColor: 'bg-orange-500', styleDescription: 'Energetic, Warm' },
  { id: 'nature_green', name: '自然绿', thumbnailColor: 'bg-emerald-600', styleDescription: 'Calm, Educational' },
];

// Helper to check backend health with cache cooldown
let backendStatus: { available: boolean; timestamp: number } | null = null;
const CHECK_COOLDOWN = 10000; // Check at most every 10 seconds

const checkBackend = async () => {
  const now = Date.now();
  // Return cached result if within cooldown period
  if (backendStatus && (now - backendStatus.timestamp < CHECK_COOLDOWN)) {
    return backendStatus.available;
  }

  try {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), 2000); // 2s timeout
    const res = await fetch(apiUrl("/healthz"), { signal: controller.signal });
    backendStatus = { available: res.ok, timestamp: now };
  } catch {
    backendStatus = { available: false, timestamp: now };
  }
  return backendStatus.available;
};

export const aiService = {
  
  /**
   * GET /templates
   */
  async getTemplates(): Promise<PPTTemplate[]> {
    const available = await checkBackend();
    if (available) {
      try {
        const res = await fetch(apiUrl("/templates"));
        if (res.ok) {
          const wrapper = await res.json();
          // main_api returns { data: [...] }
          const list = wrapper.data || [];
          
          return list.map((t: any) => ({
            id: t.id || t.name,
            name: t.name || t.id,
            thumbnailColor: 'bg-slate-200',
            styleDescription: t.name || t.id,
            // main_api already returns /api/data/*.jpg
            coverUrl: typeof t.cover === 'string' ? t.cover : undefined,
            rawTemplate: t,
          }));
        }
      } catch (e) {
        console.warn("Failed to fetch templates from backend, using mock.", e);
      }
    }
    return MOCK_TEMPLATES;
  },

  /**
   * GET /data/{templateId}.json
   * 获取模板详情（slides/theme/width/height 等）
   */
  async getTemplateFileData(templateId: string): Promise<any> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot fetch template data.");

    const id = (templateId || "").trim();
    if (!id) throw new Error("templateId is required.");

    const res = await fetch(apiUrl(`/data/${id}.json`));
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `Failed to fetch template data: ${res.statusText}`);
    }
    return await res.json();
  },

  /**
   * POST /tools/aippt (SSE, JSON per slide)
   * 返回 AIPPTSlide[]；并可通过 onSlide 增量回调。
   */
  async streamAipptSlides(input: {
    content: string;
    sessionId: string;
    language?: string;
    generateFromWebSearch?: boolean;
    generateFromUploadedFile?: boolean;
    kbFolderIds?: number[] | null;
    onSlide?: (slide: AIPPTSlide) => void;
  }): Promise<AIPPTSlide[]> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate PPT.");

    const payload = {
      content: input.content,
      language: input.language ?? "zh",
      sessionId: input.sessionId,
      generateFromWebSearch: input.generateFromWebSearch ?? true,
      generateFromUploadedFile: input.generateFromUploadedFile ?? false,
      kb_folder_ids: input.kbFolderIds ?? null,
    };

    const response = await fetch(apiUrl("/tools/aippt"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(text || `Backend PPT generation failed: ${response.statusText}`);
    }
    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SseParser();

    const slides: AIPPTSlide[] = [];
    let finished = false;

    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const messages = parser.feed(chunk);

      for (const msg of messages) {
        const raw = msg.data.trim();
        if (!raw) continue;
        if (raw === "[DONE]") {
          finished = true;
          break;
        }

        const candidate = stripJsonCodeFence(raw).trim();
        let obj: any;
        try {
          obj = JSON.parse(candidate);
        } catch {
          // 非 JSON（例如零散文本片段）直接忽略
          continue;
        }

        const type = obj?.type;
        if (type === "error") {
          throw new Error(obj?.text || "PPT generation error.");
        }

        if (type === "cover" || type === "contents" || type === "transition" || type === "content" || type === "reference" || type === "end") {
          const slide = obj as AIPPTSlide;
          slides.push(slide);
          input.onSlide?.(slide);
        }
      }
    }

    return slides;
  },

  /**
   * POST /kb/upload
   * 上传知识库文件并向量化（folder_id: 0=上传素材，1=生成产物）。
   */
  async kbUpload(input: { userId: string; file: File; folderId?: number }): Promise<{
    user_id: string;
    file_id: string;
    file_name: string;
    file_type: string;
    folder_id: number;
    status: string;
  }> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot upload KB file.");

    const formData = new FormData();
    formData.append("user_id", input.userId);
    formData.append("folder_id", String(input.folderId ?? 0));
    formData.append("file_type", input.file.name.split(".").pop() || "unknown");
    formData.append("file", input.file);

    const res = await fetch(apiUrl("/kb/upload"), {
      method: "POST",
      body: formData,
    });

    let wrapper: any;
    try {
      wrapper = await res.json();
    } catch {
      wrapper = null;
    }

    if (!res.ok || !wrapper?.ok) {
      const message = wrapper?.error?.message || res.statusText || "KB upload failed.";
      throw new Error(message);
    }

    return wrapper.data;
  },

  /**
   * GET /kb/files/{user_id}
   */
  async kbListFiles(input: { userId: string; folderId?: number }): Promise<
    Array<{
      user_id: string;
      file_id: string;
      file_name: string;
      file_type: string;
      folder_id: number;
    }>
  > {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot list KB files.");

    const userId = encodeURIComponent(input.userId);
    const qs = typeof input.folderId === "number" ? `?folder_id=${encodeURIComponent(String(input.folderId))}` : "";
    const res = await fetch(apiUrl(`/kb/files/${userId}${qs}`));

    let wrapper: any;
    try {
      wrapper = await res.json();
    } catch {
      wrapper = null;
    }

    if (!res.ok || !wrapper?.ok) {
      const message = wrapper?.error?.message || res.statusText || "KB list failed.";
      throw new Error(message);
    }

    return wrapper.data || [];
  },

  /**
   * DELETE /kb/files/{user_id}/{file_id}
   */
  async kbDeleteFile(input: { userId: string; fileId: string }): Promise<void> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot delete KB file.");

    const userId = encodeURIComponent(input.userId);
    const fileId = encodeURIComponent(input.fileId);
    const res = await fetch(apiUrl(`/kb/files/${userId}/${fileId}`), { method: "DELETE" });

    let wrapper: any;
    try {
      wrapper = await res.json();
    } catch {
      wrapper = null;
    }

    if (!res.ok || !wrapper?.ok) {
      const message = wrapper?.error?.message || res.statusText || "KB delete failed.";
      throw new Error(message);
    }
  },

  /**
   * POST /tools/aippt_outline_unified (SSE Text)
   * Strictly uses backend. No client-side fallback.
   */
  async generateOutline(course: CourseGroup, unit: CourseUnit, onStream?: (text: string) => void): Promise<string> {
    // We check availability but fail fast if offline
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate outline.");

    const topic = unit.title?.trim();
    if (!topic) throw new Error("Unit title is required to generate outline.");

    const content = [
      `主题：${topic}`,
      `课程：${course.name}`,
      course.description ? `课程背景：${course.description}` : "",
      unit.objectives ? `教学目标：${unit.objectives}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const formData = new FormData();
    formData.append("content", content);
    formData.append("language", "chinese");
    formData.append("user_id", course.id);

    const response = await fetch(apiUrl("/tools/aippt_outline_unified"), {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(text || `Backend error: ${response.statusText}`);
    }

    if (!response.body) throw new Error("No response body");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    const parser = new SseParser();
    let finished = false;

    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const messages = parser.feed(chunk);

      for (const msg of messages) {
        const raw = msg.data;
        if (!raw) continue;
        if (raw.trim() === "[DONE]") {
          finished = true;
          break;
        }
        fullText += raw;
        onStream?.(fullText);
      }
    }
    return fullText;
  },

  /**
   * POST /kb/vectorize/text
   * 将生成/编辑后的文本写入知识库索引（产物入库）。
   */
  async vectorizeTextToKb(input: {
    userId: string;
    fileId: string;
    fileName: string;
    content: string;
    fileType?: string;
    folderId?: number;
  }): Promise<void> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot write KB index.");

    const response = await fetch(apiUrl("/kb/vectorize/text"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: input.userId,
        file_id: input.fileId,
        file_name: input.fileName,
        content: input.content,
        file_type: input.fileType ?? "md",
        folder_id: input.folderId ?? 1,
      }),
    });

    let wrapper: any;
    try {
      wrapper = await response.json();
    } catch {
      wrapper = null;
    }

    if (!response.ok) {
      const message = wrapper?.error?.message || response.statusText || "KB vectorize failed.";
      throw new Error(message);
    }
    if (!wrapper?.ok) {
      const message = wrapper?.error?.message || "KB vectorize failed.";
      throw new Error(message);
    }
  },

  /**
   * POST /tools/aippt (Server Sent Events)
   * Strictly uses backend. No client-side fallback.
   */
  async generatePPT(
    course: CourseGroup, 
    unit: CourseUnit, 
    outline: string, 
    template: PPTTemplate,
    onSlideGenerated?: (slide: any) => void
  ): Promise<Presentation> {
    // 兼容旧调用：阶段 D 已改为 streamAipptSlides + 模板映射，这里保留但不再使用
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate PPT.");

    if (!template.rawTemplate) {
        throw new Error("Invalid template selected (missing backend definition).");
    }
    
    const response = await fetch(apiUrl("/tools/aippt"), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        content: outline,
        language: 'chinese',
        template: template.rawTemplate,
        model: 'GLM-4.5-Air',
        stream: true
      }),
    });

    if (!response.ok) throw new Error("Backend PPT generation failed.");
    if (!response.body) throw new Error("No response body");
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    const slides: any[] = [];
    const parser = new SseParser();
    let finished = false;

    // SSE Parser Logic
    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const messages = parser.feed(chunk);

      for (const msg of messages) {
        const raw = msg.data.trim();
        if (!raw) continue;
        if (raw === "[DONE]") {
          finished = true;
          break;
        }

        const payload = stripJsonCodeFence(raw);
        try {
          const slideData = JSON.parse(payload);
          // Map backend slide format to TeachDo simplified format
          const eventType = msg.event || slideData?.type || "";
          const mappedSlide = mapBackendSlideToFrontend(slideData, eventType);

          if (mappedSlide) {
            slides.push(mappedSlide);
            onSlideGenerated?.(mappedSlide);
          }
        } catch (e) {
          console.warn("Failed to parse SSE JSON event", e, { raw });
        }
      }
    }
    
    return {
      theme: template.id,
      slides: slides
    };
  },

};

/**
 * Mapper function to convert AIPPT slide structure to TeachDo simplified preview structure
 */
function mapBackendSlideToFrontend(backendSlide: any, eventType: string): any | null {
  // Logic to extract title and text content from 'elements' array
  let title = "Untitled Slide";
  const content: string[] = [];
  
  if (backendSlide.elements && Array.isArray(backendSlide.elements)) {
      backendSlide.elements.forEach((el: any) => {
          // Heuristics to find title vs content
          if (el.type === 'text') {
              // Basic HTML strip
              const cleanText = el.text ? el.text.replace(/<[^>]*>?/gm, '') : '';
              
              if (!cleanText) return;

              if (title === "Untitled Slide") {
                  title = cleanText;
              } else {
                  content.push(cleanText);
              }
          }
      });
  }

  // Handle specific event types nicely
  if (eventType === 'cover') {
     // Content usually empty for cover in preview, or subtitle
  } else if (eventType === 'contents') {
     title = "目录 / Table of Contents";
  }

  // Fallback if extraction failed but raw text exists (rare)
  if (content.length === 0 && backendSlide.content) {
      // content.push(backendSlide.content);
  }

  return {
    title: title,
    content: content,
    notes: backendSlide.note || ""
  };
}
