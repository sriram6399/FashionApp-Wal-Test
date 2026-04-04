import { useCallback, useEffect, useMemo, useState } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { fetchFilters, fetchImages, uploadImage } from "./api";
import { Header } from "./components/Header";
import { FilterSidebar } from "./components/FilterSidebar";
import { ImageDetail } from "./components/ImageDetail";
import { ImageGrid } from "./components/ImageGrid";
import { HomeCategories } from "./components/HomeCategories";
import { CameraUpload } from "./components/CameraUpload";
import type { FilterOptions, ImageItem, ImageListSearchMeta } from "./types";

/** Every facet the sidebar can set must be forwarded to `/api/images`. */
const FILTER_KEYS: (keyof FilterOptions)[] = [
  "garment_type",
  "category",
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
  const location = useLocation();
  const categoryMatch = location.pathname.match(/^\/category\/(.+)$/);
  const currentCategoryRoute = categoryMatch ? decodeURIComponent(categoryMatch[1]) : undefined;

  const [items, setItems] = useState<ImageItem[]>([]);
  const [searchMeta, setSearchMeta] = useState<ImageListSearchMeta | null>(null);
  const [facets, setFacets] = useState<FilterOptions | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filterVals, setFilterVals] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<ImageItem | null>(null);
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isListLoading, setIsListLoading] = useState(false);

  // Debounce typing (500ms idle) before committing `q`; Enter / search icon commits immediately via commitSearchQuery
  useEffect(() => {
    if (!search.trim()) {
      setDebouncedSearch("");
      return;
    }
    const timer = setTimeout(() => setDebouncedSearch(search), 500);
    return () => clearTimeout(timer);
  }, [search]);

  const queryParams = useMemo(() => {
    const p: Record<string, string | undefined> = {};
    if (debouncedSearch.trim()) p.q = debouncedSearch.trim();
    
    // Auto-apply category route if present
    if (currentCategoryRoute) {
      p.category = currentCategoryRoute;
    }

    FILTER_KEYS.forEach((k) => {
      const v = filterVals[k];
      if (v) p[k] = v;
    });
    return p;
  }, [debouncedSearch, filterVals, currentCategoryRoute]);

  const reload = useCallback(async () => {
    setIsListLoading(true);
    try {
      const [list, f] = await Promise.all([fetchImages(queryParams), fetchFilters()]);
      setItems(list.items);
      setSearchMeta(list.search);
      setFacets(f);
    } catch (err) {
      console.error("Network or query failure:", err);
    } finally {
      setIsListLoading(false);
    }
  }, [queryParams]);

  useEffect(() => {
    // Re-fetch automatically when filters/search changes or route changes
    reload().catch(console.error);
  }, [reload]);

  /** Run search immediately (Enter / search icon); typing still uses debounce above. */
  const commitSearchQuery = useCallback(() => {
    setDebouncedSearch(search.trim());
  }, [search]);

  const onClearFilters = () => {
    setFilterVals({});
  };

  const isSearchActive = search.trim().length > 0 || Object.keys(filterVals).length > 0;

  /** Box has text but `q` not committed yet (waiting for 500ms pause or submit). */
  const searchDebouncePending =
    search.trim().length > 0 && search.trim() !== debouncedSearch.trim();

  /** Don’t show the results grid until the search query is settled and the request finished. */
  const showSearchLoading =
    search.trim().length > 0 && (searchDebouncePending || isListLoading);

  const filterSidebarColumn =
    isSidebarOpen ? (
      <div style={{ width: 280, flexShrink: 0 }}>
        <FilterSidebar
          filters={facets}
          values={filterVals}
          onChange={(k, v) => setFilterVals((prev) => ({ ...prev, [k]: v }))}
          onClear={onClearFilters}
        />
      </div>
    ) : null;

  const mainRowStyle = {
    flex: 1,
    display: "flex" as const,
    width: "100%",
    maxWidth: 1440,
    margin: "0 auto",
    padding: "1.5rem 0",
  };

  const searchLoadingBlock = (
    <div
      style={{
        padding: "4rem 2rem",
        color: "var(--muted)",
        textAlign: "center",
        fontSize: "1.05rem",
        fontWeight: 400,
      }}
      role="status"
      aria-live="polite"
    >
      Loading search results...
    </div>
  );

  const renderGridWithSidebar = (title: string, opts?: { showSearchHint?: boolean }) => (
    <div style={mainRowStyle}>
      {filterSidebarColumn}
      <div style={{ flex: 1, padding: "0 1.5rem", minWidth: 0 }}>
        <div style={{ marginBottom: "1.5rem" }}>
          <h1 style={{ margin: 0, fontSize: "2rem", color: "var(--text)" }}>{title}</h1>
          {opts?.showSearchHint && searchMeta && !showSearchLoading ? (
            <p
              style={{
                margin: "0.35rem 0 0",
                fontSize: "0.95rem",
                color: "var(--muted)",
                lineHeight: 1.45,
              }}
            >
              {searchMeta.message}
            </p>
          ) : null}
          {!showSearchLoading ? (
            <p style={{ margin: "0.35rem 0 0", color: "var(--muted)" }}>
              Showing {items.length} {items.length === 1 ? "item" : "items"}
            </p>
          ) : null}
        </div>
        {showSearchLoading ? searchLoadingBlock : <ImageGrid items={items} onSelect={setSelected} />}
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Header 
        search={search} 
        onSearch={setSearch} 
        onSearchSubmit={commitSearchQuery}
        onOpenFilters={() => setIsSidebarOpen(!isSidebarOpen)}
        onUploadClick={() => setIsUploadOpen(true)}
      />

      <Routes>
        <Route 
          path="/" 
          element={
            isSearchActive ? (
              renderGridWithSidebar("Search results", { showSearchHint: !!debouncedSearch.trim() })
            ) : (
              <div style={mainRowStyle}>
                {filterSidebarColumn}
                <div style={{ flex: 1, padding: "0 1.5rem", minWidth: 0 }}>
                  <HomeCategories categories={facets?.category ?? []} images={items} />
                </div>
              </div>
            )
          } 
        />
        <Route 
          path="/category/:categoryId" 
          element={renderGridWithSidebar(currentCategoryRoute || "Category", {
            showSearchHint: !!debouncedSearch.trim(),
          })} 
        />
      </Routes>

      <CameraUpload
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={() => reload()}
        upload={async (file, opts) => {
          await uploadImage(file, opts);
        }}
      />

      <ImageDetail item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
