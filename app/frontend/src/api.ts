import type { FilterOptions, ImageItem, ImageListResponse } from "./types";
import { apiUrl, viteApiBaseUrl } from "./env";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchImages(params: Record<string, string | undefined>): Promise<ImageListResponse> {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === "") return;
    q.append(k, v);
  });
  const res = await fetch(apiUrl(`/api/images?${q.toString()}`));
  return parseJson<ImageListResponse>(res);
}

export async function fetchFilters(): Promise<FilterOptions> {
  const res = await fetch(apiUrl("/api/filters"));
  return parseJson<FilterOptions>(res);
}

export async function uploadImage(
  file: File,
  opts?: { caption?: string; tags?: string; uploadMetadataJson?: string }
): Promise<ImageItem> {
  const body = new FormData();
  body.append("file", file);
  const c = opts?.caption?.trim();
  if (c) body.append("caption", c);
  const tg = opts?.tags?.trim();
  if (tg) body.append("tags", tg);
  const mj = opts?.uploadMetadataJson?.trim();
  if (mj) body.append("upload_metadata", mj);
  const res = await fetch(apiUrl("/api/images"), { method: "POST", body });
  return parseJson<ImageItem>(res);
}

export async function patchImage(
  id: number,
  body: { designer_tags: string[]; designer_notes: string; designer_name: string }
): Promise<ImageItem> {
  const res = await fetch(apiUrl(`/api/images/${id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<ImageItem>(res);
}

export function fileSrc(url: string): string {
  if (url.startsWith("http")) return url;
  return viteApiBaseUrl ? `${viteApiBaseUrl}${url}` : url;
}
