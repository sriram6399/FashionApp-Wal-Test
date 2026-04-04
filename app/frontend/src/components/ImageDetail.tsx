import type { CSSProperties, ReactNode } from "react";
import { fileSrc } from "../api";
import type { ImageItem, StructuredMeta } from "../types";
import { X } from "lucide-react";

type Props = {
  item: ImageItem | null;
  onClose: () => void;
};

function MetaTable({ title, accent, children }: { title: string; accent: string; children: ReactNode }) {
  return (
    <section style={{ marginTop: "1rem" }}>
      <h3
        style={{
          margin: "0 0 1.25rem",
          fontSize: "0.85rem",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          fontWeight: 700,
          color: "var(--primary)",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}
      >
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: accent, display: "inline-block", boxShadow: "0 0 10px " + accent }}></span>
        {title}
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {children}
      </div>
    </section>
  );
}

function formatStructured(s: StructuredMeta): [string, string][] {
  const rows: [string, string][] = [];
  const add = (k: string, v: string | null | undefined) => {
    if (v) rows.push([k, v]);
  };
  add("Garment type", s.garment_type);
  add("Category", s.category);
  add("Style", s.style);
  add("Material", s.material);
  if (s.color_palette?.length) add("Colors", s.color_palette.join(", "));
  add("Pattern", s.pattern);
  add("Season", s.season);
  add("Occasion", s.occasion);
  add("Consumer profile", s.consumer_profile);
  add("Trend notes", s.trend_notes);
  const loc = s.location_context;
  if (loc) {
    add("Continent", loc.continent ?? undefined);
    add("Country", loc.country ?? undefined);
    add("City", loc.city ?? undefined);
  }
  const tm = s.time_context;
  if (tm) {
    if (tm.year != null) add("Year", String(tm.year));
    if (tm.month != null) add("Month", String(tm.month));
    add("Season (time)", tm.season ?? undefined);
  }
  return rows;
}

export function ImageDetail({ item, onClose }: Props) {
  if (!item) return null;

  return (
    <div style={overlay} role="dialog" aria-modal="true" onClick={onClose}>
      <div style={panel} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.75rem", letterSpacing: "-0.03em" }}>Inspiration Detail</h2>
          <button type="button" onClick={onClose} style={closeBtn} aria-label="Close">
            <X size={20} />
          </button>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.4fr 1fr",
            gap: "2.5rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "center", alignItems: "flex-start", background: "var(--surface2)", borderRadius: 16, padding: "0.5rem", boxShadow: "inset 0 2px 10px rgba(0,0,0,0.02)" }}>
             <img
               src={fileSrc(item.file_url)}
               alt=""
               style={{ 
                   width: "100%", 
                   maxHeight: "75vh", 
                   objectFit: "contain", 
                   borderRadius: 12, 
                   boxShadow: "var(--shadow-md)"
               }}
             />
          </div>
          <div style={{ overflowY: "auto", maxHeight: "75vh", paddingRight: "0.5rem" }}>
            <MetaTable title="Visual Analysis & Indexing" accent="var(--accent)">
              <p style={{ 
                margin: 0, 
                lineHeight: 1.6, 
                fontSize: "1.1rem", 
                color: "var(--primary)", 
                fontStyle: "italic", 
                borderLeft: "3px solid var(--accent)", 
                paddingLeft: "1.25rem",
                opacity: 0.9
              }}>
                 "{item.description}"
              </p>
              
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.85rem", marginTop: "0.5rem" }}>
                  {formatStructured(item.structured).map(([k, v]) => (
                    <div key={k} style={{ 
                      background: "var(--bg)", 
                      padding: "0.6rem 1rem", 
                      borderRadius: 14, 
                      border: "1px solid var(--border)",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                      boxShadow: "var(--shadow-sm)"
                    }}>
                      <span style={{ fontSize: "0.65rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)", fontWeight: 700 }}>{k}</span>
                      <span style={{ fontSize: "0.95rem", color: "var(--text)", fontWeight: 500 }}>{v}</span>
                    </div>
                  ))}
              </div>
            </MetaTable>
          </div>
        </div>
      </div>
    </div>
  );
}

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15, 23, 42, 0.45)",
  backdropFilter: "blur(12px)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "2rem",
  zIndex: 1000,
};

const panel: CSSProperties = {
  background: "var(--surface)",
  backdropFilter: "blur(24px)",
  borderRadius: 24,
  border: "1px solid rgba(255, 255, 255, 0.6)",
  boxShadow: "var(--shadow-cover)",
  maxWidth: 1050,
  width: "100%",
  padding: "2rem 2.5rem",
  maxHeight: "92vh",
  overflow: "hidden",
};

const closeBtn: CSSProperties = {
  background: "var(--surface2)",
  border: "none",
  borderRadius: "50%",
  width: 36,
  height: 36,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "var(--text)",
  cursor: "pointer",
  transition: "all 0.2s",
};
