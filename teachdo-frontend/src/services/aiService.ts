import type { CourseGroup, CourseUnit, LessonPlan, Presentation, PPTTemplate, ChatMessage } from "#root/types";
import { SseParser, stripJsonCodeFence } from "@/utils/sse";

/**
 * AI Service Layer - TeachDo x ai2ppt Integration
 * 
 * Unified entry point for all LLM interactions.
 * All requests are routed through the backend (ai2ppt/TeachDo API).
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
          // ai2ppt returns { data: [...], message: "Success" }
          const list = wrapper.data || [];
          
          return list.map((t: any) => ({
            id: t.id || t.name, // Use ID from backend
            name: t.name,
            thumbnailColor: 'bg-slate-200',
            styleDescription: t.name,
            // Construct static resource URL for cover
            coverUrl: t.image_path ? apiUrl(`/data/${t.image_path}`) : undefined,
            // Store the full template object for generation
            rawTemplate: t
          }));
        }
      } catch (e) {
        console.warn("Failed to fetch templates from ai2ppt, using mock.", e);
      }
    }
    return MOCK_TEMPLATES;
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
   * POST /teachdo/lesson-plan
   * Generates a structured JSON Lesson Plan via Backend
   */
  async generateLessonPlan(course: CourseGroup, unit: CourseUnit, outline: string): Promise<LessonPlan> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate lesson plan.");

    const response = await fetch(apiUrl("/teachdo/lesson-plan"), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            course: {
                name: course.name,
                subject: course.subject,
                description: course.description
            },
            unit: {
                title: unit.title,
                objectives: unit.objectives
            },
            outline: outline
        })
    });

    if (!response.ok) {
        throw new Error("Failed to generate lesson plan via backend.");
    }

    const data = await response.json();
    return data as LessonPlan;
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

  /**
   * POST /teachdo/assistant/chat (Streaming Text or SSE)
   * Chat with the course assistant via backend
   */
  async chatWithAssistant(
      course: CourseGroup, 
      unit: CourseUnit | undefined | null, 
      history: ChatMessage[], 
      message: string, 
      onChunk: (text: string) => void
  ): Promise<void> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Please check connection.");

    const response = await fetch(apiUrl("/teachdo/assistant/chat"), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            course: {
                name: course.name,
                subject: course.subject,
                description: course.description
            },
            unit: unit ? {
                title: unit.title,
                objectives: unit.objectives
            } : null,
            history: history.map(h => ({ role: h.role, text: h.text })),
            message: message
        })
    });

    if (!response.ok) throw new Error(`Chat request failed: ${response.statusText}`);
    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        
        // Handle SSE if detected (data: prefix), otherwise treat as raw stream
        if (chunk.includes('data:') || buffer.includes('data:')) {
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('data:')) {
                    const dataContent = trimmed.substring(5).trim();
                    if (dataContent === '[DONE]') break;
                    try {
                        // Attempt to parse JSON object from data line (e.g. { content: "..." })
                        if (dataContent.startsWith('{')) {
                            const json = JSON.parse(dataContent);
                            const text = json.text || json.content || json.delta || '';
                            if (text) onChunk(text);
                        } else {
                            // Raw text after data:
                            onChunk(dataContent);
                        }
                    } catch {
                        // Fallback: just use content as is
                        onChunk(dataContent);
                    }
                }
            }
        } else {
            // Raw text stream fallback
            onChunk(chunk);
        }
    }
  }
};

/**
 * Mapper function to convert ai2ppt slide structure to TeachDo simplified preview structure
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
