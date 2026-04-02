import type { CSSProperties } from "react";
import type { FilterOptions } from "../types";

const LABELS: Record<string, string> = {
  garment_type: "Garment type",
  style: "Style",
  material: "Material",
  color_palette: "Color",
  pattern: "Pattern",
  season: "Season (garment)",
  occasion: "Occasion",
  consumer_profile: "Consumer profile",
  trend_notes: "Trend notes",
  continent: "Continent",
  country: "Country",
  city: "City",
  year: "Year",
  month: "Month",
  time_season: "Season (time)",
  designer_name: "Designer",
  designer_tags: "Designer tag",
};

type Props = {
  filters: FilterOptions | null;
  values: Record<string, string>;
  search: string;
  onSearch: (v: string) => void;
  onChange: (key: string, value: string) => void;
  onClear: () => void;
};

export function FilterSidebar({ filters, values, search, onSearch, onChange, onClear }: Props) {
  if (!filters) {
    return (
      <aside style={asideStyle}>
        <p style={{ color: "var(--muted)", margin: 0 }}>Loading filters…</p>
      </aside>
    );
  }

  const keys = Object.keys(filters) as (keyof FilterOptions)[];

  return (
    <aside style={asideStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <h2 style={{ margin: 0, fontSize: "1.25rem" }}>Refine</h2>
        <button type="button" onClick={onClear} style={ghostBtn}>
          Clear
        </button>
      </div>
      <p style={{ color: "var(--muted)", fontSize: "0.8rem", marginTop: 4 }}>
        Options are built from your library. Combine with search.
      </p>

      <label style={labelStyle}>
        Search
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder='e.g. "embroidered neckline", "artisan market"'
          style={inputStyle}
        />
      </label>

      {keys.map((key) => {
        const opts = filters[key];
        if (!opts.length) return null;
        return (
          <label key={key} style={labelStyle}>
            {LABELS[key] ?? key}
            <select
              value={values[key] ?? ""}
              onChange={(e) => onChange(key, e.target.value)}
              style={inputStyle}
            >
              <option value="">Any</option>
              {opts.map((o) => (
                <option key={String(o)} value={String(o)}>
                  {String(o)}
                </option>
              ))}
            </select>
          </label>
        );
      })}
    </aside>
  );
}

const asideStyle: CSSProperties = {
  width: 280,
  flexShrink: 0,
  borderRight: "1px solid var(--border)",
  padding: "1.25rem 1rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.85rem",
  maxHeight: "100vh",
  overflowY: "auto",
  background: "var(--surface)",
};

const labelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  fontSize: "0.75rem",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "var(--muted)",
};

const inputStyle: CSSProperties = {
  padding: "0.5rem 0.65rem",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--surface2)",
  color: "var(--text)",
};

const ghostBtn: CSSProperties = {
  background: "transparent",
  border: "none",
  color: "var(--accent)",
  cursor: "pointer",
  fontSize: "0.85rem",
};
