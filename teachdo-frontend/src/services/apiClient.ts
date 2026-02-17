export type ApiErrorKind =
  | 'offline'
  | 'timeout'
  | 'abort'
  | 'http'
  | 'backend'
  | 'parse'
  | 'unknown';

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  url?: string;
  override cause?: unknown;

  constructor(kind: ApiErrorKind, message: string, init?: { status?: number; url?: string; cause?: unknown }) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = init?.status;
    this.url = init?.url;
    this.cause = init?.cause;
  }
}

// 统一走相对路径 /api（开发：Vite proxy；生产：Nginx 反代）
const BASE_API = '/api';
export const apiUrl = (path: string) => `${BASE_API}${path.startsWith('/') ? path : `/${path}`}`;

const isBrowser = typeof window !== 'undefined';

function isAbortError(error: unknown): boolean {
  if (!error) return false;
  const anyErr = error as any;
  return anyErr?.name === 'AbortError' || anyErr?.code === 'ABORT_ERR';
}

function createRequestSignal(opts: { timeoutMs?: number; signal?: AbortSignal }): {
  signal?: AbortSignal;
  cleanup: () => void;
  didTimeout: () => boolean;
  didAbortByUpstream: () => boolean;
} {
  const timeoutMs = opts.timeoutMs;
  const upstream = opts.signal;

  let timedOut = false;
  let abortedByUpstream = false;
  let timer: number | null = null;
  let onAbort: (() => void) | null = null;

  if (!timeoutMs) {
    return {
      signal: upstream,
      cleanup: () => null,
      didTimeout: () => false,
      didAbortByUpstream: () => false,
    };
  }

  const controller = new AbortController();

  timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  if (upstream) {
    if (upstream.aborted) {
      abortedByUpstream = true;
      controller.abort();
    } else {
      onAbort = () => {
        abortedByUpstream = true;
        controller.abort();
      };
      upstream.addEventListener('abort', onAbort);
    }
  }

  const cleanup = () => {
    if (timer) window.clearTimeout(timer);
    timer = null;
    if (upstream && onAbort) upstream.removeEventListener('abort', onAbort);
    onAbort = null;
  };

  return {
    signal: controller.signal,
    cleanup,
    didTimeout: () => timedOut,
    didAbortByUpstream: () => abortedByUpstream,
  };
}

async function safeReadText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
}

async function extractErrorMessage(res: Response): Promise<string> {
  const contentType = (res.headers.get('content-type') || '').toLowerCase();
  if (contentType.includes('application/json')) {
    try {
      const json = await res.json();
      const message = json?.error?.message || json?.message;
      if (typeof message === 'string' && message.trim()) return message.trim();
    } catch {
      // ignore
    }
  }

  const text = (await safeReadText(res)).trim();
  return text || res.statusText || `HTTP ${res.status}`;
}

/**
 * 低层请求封装：
 * - 支持 timeout + 外部 AbortSignal
 * - 统一把 HTTP 非 2xx 转换为 ApiError('http')
 * - 统一把超时/取消/未知网络错误转换为 ApiError(kind)
 */
export async function requestRaw(
  path: string,
  init: RequestInit = {},
  opts: { timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<Response> {
  const url = apiUrl(path);

  // SSR/非浏览器环境不应该发请求（目前 TeachDo 前端不走 SSR，但这里兜底）
  if (!isBrowser) {
    throw new ApiError('unknown', 'Request is only supported in browser environment.', { url });
  }

  const { signal, cleanup, didTimeout, didAbortByUpstream } = createRequestSignal(opts);

  try {
    const res = await fetch(url, { ...init, signal });
    if (!res.ok) {
      const message = await extractErrorMessage(res);
      throw new ApiError('http', message, { status: res.status, url });
    }
    return res;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (didTimeout()) throw new ApiError('timeout', 'Request timed out.', { url, cause: e });
    if (didAbortByUpstream() || isAbortError(e)) throw new ApiError('abort', 'Request aborted.', { url, cause: e });
    throw new ApiError('unknown', 'Network request failed.', { url, cause: e });
  } finally {
    cleanup();
  }
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
  opts: { timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<T> {
  const res = await requestRaw(path, init, opts);
  try {
    return (await res.json()) as T;
  } catch (e) {
    throw new ApiError('parse', 'Failed to parse JSON response.', { url: apiUrl(path), cause: e });
  }
}

type OkWrapper<T> = { ok: boolean; data?: T; error?: { message?: string } };

export async function requestOkWrapper<T>(
  path: string,
  init: RequestInit = {},
  opts: { timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<T> {
  const wrapper = await requestJson<OkWrapper<T>>(path, init, opts);
  if (!wrapper?.ok) {
    const message = wrapper?.error?.message || 'Request failed.';
    throw new ApiError('backend', message, { url: apiUrl(path) });
  }
  return (wrapper.data as T) ?? (null as T);
}

/**
 * 后端健康检查（带冷却缓存）。
 * 注意：这里不会抛错，只返回可用性，方便上层做 fallback。
 */
let backendStatus: { available: boolean; timestamp: number } | null = null;
const DEFAULT_CHECK_COOLDOWN_MS = 10_000;
const DEFAULT_HEALTH_TIMEOUT_MS = 2_000;

export async function checkBackend(opts: { force?: boolean; cooldownMs?: number; timeoutMs?: number } = {}): Promise<boolean> {
  if (!isBrowser) return false;
  const now = Date.now();
  const cooldownMs = typeof opts.cooldownMs === 'number' ? opts.cooldownMs : DEFAULT_CHECK_COOLDOWN_MS;
  const timeoutMs = typeof opts.timeoutMs === 'number' ? opts.timeoutMs : DEFAULT_HEALTH_TIMEOUT_MS;

  if (!opts.force && backendStatus && now - backendStatus.timestamp < cooldownMs) {
    return backendStatus.available;
  }

  try {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(apiUrl('/healthz'), { signal: controller.signal });
    window.clearTimeout(timer);
    backendStatus = { available: res.ok, timestamp: now };
  } catch {
    backendStatus = { available: false, timestamp: now };
  }

  return backendStatus.available;
}

export async function ensureBackendAvailable(): Promise<void> {
  const ok = await checkBackend();
  if (!ok) {
    throw new ApiError('offline', 'Backend service is offline.', { url: apiUrl('/healthz') });
  }
}

