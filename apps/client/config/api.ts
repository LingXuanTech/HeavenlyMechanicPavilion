const DEFAULT_API_BASE = 'http://localhost:8000/api';

function normalizeApiBase(url?: string): string {
  if (!url) {
    return DEFAULT_API_BASE;
  }

  const trimmed = url.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE;
  }

  return trimmed.replace(/\/+$/, '');
}

export const API_BASE = normalizeApiBase(import.meta.env.VITE_API_URL as string | undefined);

