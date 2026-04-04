import { fileSrc } from "../api";
import type { ImageItem } from "../types";

type Props = {
  items: ImageItem[];
  onSelect: (item: ImageItem) => void;
};

export function ImageGrid({ items, onSelect }: Props) {
  if (!items.length) {
    return (
      <div style={{ padding: "4rem 2rem", color: "var(--muted)", textAlign: "center", fontSize: "1.1rem", fontWeight: 300 }}>
        No items discovered. Let's curate something new.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: "1.5rem",
        alignContent: "start",
      }}
    >
      {items.map((item) => {
        // Filter out 'eval' from tags
        const validTags = item.designer_tags?.filter(t => t.toLowerCase() !== 'eval') || [];
        
        return (
          <div
            key={item.id}
            className="premium-card"
            onClick={() => onSelect(item)}
            role="button"
            tabIndex={0}
          >
            <div className="card-image-wrapper">
              <img
                src={fileSrc(item.file_url)}
                alt={item.description || "Apparel Image"}
                className="card-image"
              />
              <div className="card-overlay">
                <div className="card-title">
                  {item.structured?.garment_type ?? "Apparel"}
                </div>
                {item.description && (
                  <div className="card-caption">
                    {item.description}
                  </div>
                )}
                {validTags.length > 0 && (
                  <div style={{ fontSize: "0.75rem", color: "var(--designer)", marginTop: 6, fontWeight: 500 }}>
                    {validTags.join(" · ")}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
