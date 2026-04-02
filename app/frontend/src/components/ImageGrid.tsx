import type { CSSProperties } from "react";
import { fileSrc } from "../api";
import type { ImageItem } from "../types";

type Props = {
  items: ImageItem[];
  onSelect: (item: ImageItem) => void;
};

export function ImageGrid({ items, onSelect }: Props) {
  if (!items.length) {
    return (
      <div style={{ padding: "2rem", color: "var(--muted)", textAlign: "center" }}>
        No images match. Upload inspiration or relax filters.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
        gap: "1rem",
        padding: "1rem",
        alignContent: "start",
      }}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onSelect(item)}
          style={card}
        >
          <img
            src={fileSrc(item.file_url)}
            alt=""
            style={{
              width: "100%",
              aspectRatio: "3 / 4",
              objectFit: "cover",
              borderRadius: 8,
              display: "block",
            }}
          />
          <div style={{ padding: "0.5rem 0 0", textAlign: "left" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
              {item.structured.garment_type ?? "Look"}
            </div>
            {item.designer_tags?.length ? (
              <div style={{ fontSize: "0.75rem", color: "var(--designer)", marginTop: 4 }}>
                {item.designer_tags.join(" · ")}
              </div>
            ) : null}
          </div>
        </button>
      ))}
    </div>
  );
}

const card: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "0.5rem",
  background: "var(--surface)",
  cursor: "pointer",
  textAlign: "left",
  color: "inherit",
};
