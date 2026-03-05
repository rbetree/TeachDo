import { ApiError, ensureBackendAvailable, requestOkWrapper } from '@/services/apiClient';

export type UiSettingsConfig = {
  outlineType: string;
  outlineBaseUrl: string;
  outlineModel: string;
  outlineApiKey: string;
  pptWriterType: string;
  pptWriterBaseUrl: string;
  pptWriterModel: string;
  pptWriterApiKey: string;
  pptCheckerType: string;
  pptCheckerBaseUrl: string;
  pptCheckerModel: string;
  pptCheckerApiKey: string;
  embeddingType: string;
  embeddingBaseUrl: string;
  embeddingModel: string;
  embeddingApiKey: string;
  embeddingTimeoutS: string;
  embeddingMaxRetries: string;
  embeddingDim: string;
  outlineApi: string;
  contentApi: string;
  personalDb: string;
  personalDbPort: string;
  httpProxy: string;
  httpsProxy: string;
  pexelsApiKey: string;
  useChart: boolean;
  outlineStreaming: boolean;
  contentStreaming: boolean;
  useMineru: boolean;
  teachdoCacheDir: string;
  teachdoTmpDir: string;
  teachdoLogDir: string;
  host: string;
  mainApiPort: string;
  outlineApiPort: string;
  contentApiPort: string;
  frontendPort: string;
};

export type UiSettingsSecrets = {
  outlineApiKey: boolean;
  pptWriterApiKey: boolean;
  pptCheckerApiKey: boolean;
  embeddingApiKey: boolean;
  pexelsApiKey: boolean;
};

export type UiSettingsResponse = {
  config: UiSettingsConfig;
  secrets: UiSettingsSecrets;
  persistPath?: string;
  note?: string;
  updatedKeys?: string[];
};

export async function getSettings(input: { signal?: AbortSignal } = {}): Promise<UiSettingsResponse> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();
  return await requestOkWrapper('/settings', { method: 'GET' }, { timeoutMs: 12_000, signal: input.signal });
}

export async function updateSettings(input: { config: UiSettingsConfig; signal?: AbortSignal }): Promise<UiSettingsResponse> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  return await requestOkWrapper(
    '/settings',
    {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input.config),
    },
    { timeoutMs: 12_000, signal: input.signal },
  );
}

export async function resetSettings(input: { signal?: AbortSignal } = {}): Promise<UiSettingsResponse> {
  if (input.signal?.aborted) {
    throw new ApiError('abort', 'Request aborted.');
  }
  await ensureBackendAvailable();

  return await requestOkWrapper('/settings/reset', { method: 'POST' }, { timeoutMs: 12_000, signal: input.signal });
}
