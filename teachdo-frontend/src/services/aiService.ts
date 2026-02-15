import type { CourseGroup, CourseUnit, LessonPlan, Presentation, PPTTemplate, ChatMessage } from "#root/types";

/**
 * AI Service Layer - TeachDo x ai2ppt Integration
 * 
 * Unified entry point for all LLM interactions.
 * All requests are routed through the backend (ai2ppt/TeachDo API).
 * No client-side API keys are used.
 */

// Safe access to environment variable to prevent runtime errors if import.meta.env is undefined
const getBackendUrl = () => {
  try {
    if (typeof import.meta !== 'undefined' && import.meta?.env?.VITE_API_BASE) {
      return import.meta.env.VITE_API_BASE;
    }
  } catch {
    // 忽略环境变量读取错误，保持兜底地址
  }
  return "http://localhost:6800";
};

const BACKEND_URL = getBackendUrl();

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
    const res = await fetch(`${BACKEND_URL}/healthz`, { signal: controller.signal });
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
        const res = await fetch(`${BACKEND_URL}/templates`);
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
            coverUrl: t.image_path ? `${BACKEND_URL}/data/${t.image_path}` : undefined,
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
   * POST /tools/aippt_outline (Streaming Text)
   * Strictly uses backend. No client-side fallback.
   */
  async generateOutline(course: CourseGroup, unit: CourseUnit, onStream?: (text: string) => void): Promise<string> {
    // We check availability but fail fast if offline
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate outline.");

    const response = await fetch(`${BACKEND_URL}/tools/aippt_outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        content: `课程：${course.name}\n背景：${course.description}\n单元：${unit.title}`,
        language: 'chinese',
        model: 'GLM-4.5-Air', // Configurable via backend ideally, but passed here for now
        stream: true
      }),
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
    }

    if (!response.body) throw new Error("No response body");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;
      onStream?.(fullText);
    }
    return fullText;
  },

  /**
   * POST /teachdo/lesson-plan
   * Generates a structured JSON Lesson Plan via Backend
   */
  async generateLessonPlan(course: CourseGroup, unit: CourseUnit, outline: string): Promise<LessonPlan> {
    const available = await checkBackend();
    if (!available) throw new Error("Backend service is offline. Cannot generate lesson plan.");

    const response = await fetch(`${BACKEND_URL}/teachdo/lesson-plan`, {
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
    
    const response = await fetch(`${BACKEND_URL}/tools/aippt`, {
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
    let buffer = '';

    // SSE Parser Logic
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line

      let currentEvent = '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(':')) continue; // skip empty or comments

        if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.substring(6).trim();
        } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.substring(5).trim();
            if (dataStr === '[DONE]') break;
            
            try {
              const slideData = JSON.parse(dataStr);
              // Map backend slide format to TeachDo simplified format
              const mappedSlide = mapBackendSlideToFrontend(slideData, currentEvent);
              
              if (mappedSlide) {
                slides.push(mappedSlide);
                onSlideGenerated?.(mappedSlide);
              }
            } catch (e) {
              console.warn("Failed to parse SSE JSON chunk", e);
            }
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

    const response = await fetch(`${BACKEND_URL}/teachdo/assistant/chat`, {
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
