/** Loaded from deploy/.env (VITE_*); see deploy/.env.example */

function trimOrigin(raw: string | undefined): string {
  if (raw === undefined || raw === "") return "";
  return raw.trim().replace(/\/$/, "");
}

/** Empty string = same origin (Vite dev proxy or production nginx /api). */
export const viteApiBaseUrl = trimOrigin(import.meta.env.VITE_API_BASE_URL);

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!viteApiBaseUrl) return p;
  return `${viteApiBaseUrl}${p}`;
}
