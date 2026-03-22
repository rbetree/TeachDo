import type { ArtifactMeta } from '@/services/ai/artifactService';

export const matchArtifactByTime = (
  artifacts: ArtifactMeta[],
  targetMs: number | null,
  windowMs: number = 10 * 60 * 1000,
): ArtifactMeta | null => {
  if (!Array.isArray(artifacts) || artifacts.length === 0) return null;
  if (!targetMs || !Number.isFinite(targetMs) || targetMs <= 0) return null;

  let best: ArtifactMeta | null = null;
  let bestDelta = Number.POSITIVE_INFINITY;

  for (const artifact of artifacts) {
    const createdAt = typeof artifact?.created_at === 'number' ? artifact.created_at : Number(artifact?.created_at);
    if (!Number.isFinite(createdAt) || createdAt <= 0) continue;
    const delta = Math.abs(createdAt - targetMs);
    if (delta > windowMs) continue;
    if (delta < bestDelta) {
      bestDelta = delta;
      best = artifact;
    }
  }

  return best;
};

