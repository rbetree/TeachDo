export type SseMessage = {
  event?: string;
  data: string;
};

function findEventDelimiter(buffer: string): { index: number; length: number } | null {
  const lfIndex = buffer.indexOf("\n\n");
  const crlfIndex = buffer.indexOf("\r\n\r\n");

  if (lfIndex === -1 && crlfIndex === -1) return null;

  if (crlfIndex !== -1 && (lfIndex === -1 || crlfIndex < lfIndex)) {
    return { index: crlfIndex, length: 4 };
  }

  return { index: lfIndex, length: 2 };
}

function parseEventBlock(block: string): SseMessage | null {
  const lines = block.split(/\r\n|\n|\r/);
  let event: string | undefined;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line) continue;
    if (line.startsWith(":")) continue;

    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      let value = line.slice("data:".length);
      // SSE 规范：冒号后若有一个空格，应当去掉该空格
      if (value.startsWith(" ")) value = value.slice(1);
      dataLines.push(value);
    }
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

/**
 * 简单 SSE 解析器：
 * - 以空行（\n\n 或 \r\n\r\n）作为事件边界
 * - 支持单事件内多行 data:，拼接为完整 payload
 */
export class SseParser {
  private buffer = "";

  feed(chunk: string): SseMessage[] {
    this.buffer += chunk;
    const messages: SseMessage[] = [];

    while (true) {
      const delimiter = findEventDelimiter(this.buffer);
      if (!delimiter) break;

      const raw = this.buffer.slice(0, delimiter.index);
      this.buffer = this.buffer.slice(delimiter.index + delimiter.length);

      const msg = parseEventBlock(raw);
      if (msg) messages.push(msg);
    }

    return messages;
  }

  reset() {
    this.buffer = "";
  }

  getRemaining() {
    return this.buffer;
  }
}

/**
 * 兼容后端把 JSON 包在 ```json ... ``` 围栏内的情况。
 */
export function stripJsonCodeFence(input: string): string {
  const trimmed = input.trim();
  if (!trimmed.startsWith("```")) return input;

  const lines = trimmed.split(/\r\n|\n|\r/);
  if (lines.length < 2) return input;
  if (!lines[0].trim().startsWith("```")) return input;

  let endFenceIndex = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].trim() === "```") {
      endFenceIndex = i;
      break;
    }
  }
  if (endFenceIndex <= 0) return input;

  return lines.slice(1, endFenceIndex).join("\n").trim();
}

