import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchFilters, fetchImages, uploadImage } from "./api";
import { FilterSidebar } from "./components/FilterSidebar";
import { ImageDetail } from "./components/ImageDetail";
import { ImageGrid } from "./components/ImageGrid";
import { UploadZone } from "./components/UploadZone";
import type { FilterOptions, ImageItem } from "./types";

const FILTER_KEYS: (keyof FilterOptions)[] = [
  "garment_type",
  "style",
  "material",
  "color_palette",
  "pattern",
  "season",
  "occasion",
  "consumer_profile",
  "trend_notes",
  "continent",
  "country",
  "city",
  "year",
  "month",
  "time_season",
  "designer_name",
  "designer_tags",
];

export default function App() {
  const [items, setItems] = useState<ImageItem[]>([]);
  const [facets, setFacets] = useState<FilterOptions | null>(null);
  const [search, setSearch] = useState("");
  const [filterVals, setFilterVals] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<ImageItem | null>(null);
  const [health, setHealth] = useState<string>("");

  const queryParams = useMemo(() => {
    const p: Record<string, string | undefined> = {};
    if (search.trim()) p.q = search.trim();
    FILTER_KEYS.forEach((k) => {
      const v = filterVals[k];
      if (v) p[k] = v;
    });
    return p;
  }, [search, filterVals]);

  const reload = useCallback(async () => {
    const [imgs, f] = await Promise.all([fetchImages(queryParams), fetchFilters()]);
    setItems(imgs);
    setFacets(f);
  }, [queryParams]);

  useEffect(() => {
    reload().catch(console.error);
  }, [reload]);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((b) => setHealth(b.classifier === "openai" ? "OpenAI vision" : "Mock classifier (set OPENAI_API_KEY)"))
      .catch(() => setHealth(""));
  }, []);

  const onClear = () => {
    setFilterVals({});
    setSearch("");
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <FilterSidebar
        filters={facets}
        values={filterVals}
        search={search}
        onSearch={setSearch}
        onChange={(k, v) => setFilterVals((prev) => ({ ...prev, [k]: v }))}
        onClear={onClear}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header
          style={{
            padding: "1.25rem 1.5rem",
            borderBottom: "1px solid var(--border)",
            background: "linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%)",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "2rem" }}>Inspiration Library</h1>
          <p style={{ margin: "0.35rem 0 0", color: "var(--muted)", maxWidth: 640 }}>
            Upload field photos, get AI garment metadata, add your own tags and notes. Filter facets are generated from
            your data.
          </p>
          {health ? (
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem", color: "var(--accent-dim)" }}>Classifier: {health}</p>
          ) : null}
        </header>
        <div style={{ padding: "1rem 1.5rem 0" }}>
          <UploadZone
            onUploaded={() => reload()}
            upload={async (file) => {
              await uploadImage(file);
            }}
          />
        </div>
        <ImageGrid items={items} onSelect={setSelected} />
        <ImageDetail item={selected} onClose={() => setSelected(null)} onSaved={() => reload()} />
      </div>
    </div>
  );
}
