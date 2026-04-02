import { useEffect, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { fileSrc, patchImage } from "../api";
import type { ImageItem, StructuredMeta } from "../types";

type Props = {
  item: ImageItem | null;
  onClose: () => void;
  onSaved: () => void;
};

function MetaTable({ title, accent, children }: { title: string; accent: string; children: ReactNode }) {
  return (
    <section style={{ marginTop: "1.25rem" }}>
      <h3
        style={{
          margin: "0 0 0.5rem",
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: accent,
        }}
      >
        {title}
      </h3>
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "0.75rem",
          background: "var(--surface2)",
          fontSize: "0.9rem",
        }}
      >
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

export function ImageDetail({ item, onClose, onSaved }: Props) {
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [designer, setDesigner] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!item) return;
    setTags(item.designer_tags.join(", "));
    setNotes(item.designer_notes ?? "");
    setDesigner(item.designer_name ?? "");
  }, [item]);

  if (!item) return null;

  const save = async () => {
    setSaving(true);
    try {
      const tagList = tags
        .split(/[,;]+/)
        .map((t) => t.trim())
        .filter(Boolean);
      await patchImage(item.id, {
        designer_tags: tagList,
        designer_notes: notes,
        designer_name: designer,
      });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={overlay} role="dialog" aria-modal="true">
      <div style={panel}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: "1.5rem" }}>Inspiration detail</h2>
          <button type="button" onClick={onClose} style={closeBtn} aria-label="Close">
            ✕
          </button>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(200px, 1fr) minmax(280px, 1.1fr)",
            gap: "1.25rem",
            marginTop: "1rem",
          }}
        >
          <img
            src={fileSrc(item.file_url)}
            alt=""
            style={{ width: "100%", borderRadius: 12, border: "1px solid var(--border)" }}
          />
          <div style={{ overflowY: "auto", maxHeight: "70vh" }}>
            <MetaTable title="AI description & metadata" accent="var(--ai)">
              <p style={{ margin: "0 0 0.75rem", lineHeight: 1.55 }}>{item.description}</p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                <tbody>
                  {formatStructured(item.structured).map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ color: "var(--muted)", padding: "4px 8px 4px 0", verticalAlign: "top" }}>{k}</td>
                      <td style={{ padding: "4px 0" }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </MetaTable>

            <MetaTable title="Designer annotations" accent="var(--designer)">
              <p style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", color: "var(--muted)" }}>
                Tags and notes are yours — searchable and shown separately from AI output.
              </p>
              <label style={lbl}>
                Your name
                <input value={designer} onChange={(e) => setDesigner(e.target.value)} style={inp} />
              </label>
              <label style={lbl}>
                Tags (comma-separated)
                <input value={tags} onChange={(e) => setTags(e.target.value)} style={inp} placeholder="market trip, pleating idea…" />
              </label>
              <label style={lbl}>
                Notes
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} style={{ ...inp, minHeight: 88, resize: "vertical" }} />
              </label>
              <button type="button" onClick={save} disabled={saving} style={primaryBtn}>
                {saving ? "Saving…" : "Save annotations"}
              </button>
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
  background: "rgba(0,0,0,0.72)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "1.5rem",
  zIndex: 50,
};

const panel: CSSProperties = {
  background: "var(--surface)",
  borderRadius: 16,
  border: "1px solid var(--border)",
  maxWidth: 960,
  width: "100%",
  padding: "1.25rem 1.5rem",
  maxHeight: "92vh",
  overflow: "hidden",
};

const closeBtn: CSSProperties = {
  background: "transparent",
  border: "none",
  color: "var(--muted)",
  fontSize: "1.25rem",
  cursor: "pointer",
};

const lbl: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  marginBottom: "0.65rem",
  fontSize: "0.8rem",
  color: "var(--muted)",
};

const inp: CSSProperties = {
  padding: "0.5rem 0.65rem",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg)",
  color: "var(--text)",
};

const primaryBtn: CSSProperties = {
  marginTop: "0.5rem",
  padding: "0.55rem 1rem",
  borderRadius: 8,
  border: "none",
  background: "linear-gradient(135deg, var(--accent-dim), var(--accent))",
  color: "#1a1510",
  fontWeight: 600,
  cursor: "pointer",
};
