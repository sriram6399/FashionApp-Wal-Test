import type { FilterOptions, ImageItem } from "./types";

const prefix = "";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchImages(params: Record<string, string | undefined>): Promise<ImageItem[]> {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === "") return;
    q.append(k, v);
  });
  const res = await fetch(`${prefix}/api/images?${q.toString()}`);
  return parseJson<ImageItem[]>(res);
}

export async function fetchFilters(): Promise<FilterOptions> {
  const res = await fetch(`${prefix}/api/filters`);
  return parseJson<FilterOptions>(res);
}

export async function uploadImage(file: File): Promise<ImageItem> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${prefix}/api/images`, { method: "POST", body });
  return parseJson<ImageItem>(res);
}

export async function patchImage(
  id: number,
  body: { designer_tags: string[]; designer_notes: string; designer_name: string }
): Promise<ImageItem> {
  const res = await fetch(`${prefix}/api/images/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<ImageItem>(res);
}

export function fileSrc(url: string): string {
  if (url.startsWith("http")) return url;
  return `${prefix}${url}`;
}
