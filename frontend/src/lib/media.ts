const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function resolveMediaUrl(url?: string | null): string | null {
  if (!url) return null;

  const trimmed = url.trim();
  if (!trimmed) return null;

  // Absolute URLs can be used as-is
  if (/^https?:\/\//i.test(trimmed)) return trimmed;

  // Root-relative paths are assumed to belong to the backend (API_URL)
  if (trimmed.startsWith('/')) return `${API_URL}${trimmed}`;

  return trimmed;
}
