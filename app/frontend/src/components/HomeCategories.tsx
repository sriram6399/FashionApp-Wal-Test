import { Link } from "react-router-dom";
import type { CSSProperties } from "react";
import type { ImageItem } from "../types";
import { fileSrc } from "../api";

type Props = {
  categories: string[];
  images: ImageItem[];
};

export function HomeCategories({ categories, images }: Props) {
  if (!categories || categories.length === 0) {
    return (
      <div style={emptyState}>
        <h2 style={{ fontSize: "2.5rem", marginBottom: "1rem", fontWeight: 300 }}>Fashion Departments</h2>
        <p style={{ color: "var(--muted)", fontSize: "1.1rem" }}>No classifications established yet. Seed the library.</p>
      </div>
    );
  }

  return (
    <div style={container}>
      <h2 style={title}>Collections</h2>
      <div style={grid}>
        {categories.map((cat) => {
          const coverImgUrl = images.find((i) => i.structured?.category === cat)?.file_url;
          return (
            <Link key={cat} to={`/category/${encodeURIComponent(cat)}`} className="premium-category-card">
              {coverImgUrl ? (
                <img src={fileSrc(coverImgUrl)} alt={cat} className="category-cover" />
              ) : (
                <div style={placeholderWrapper} />
              )}
              <div className="category-overlay">
                <span className="category-title">{cat}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

const emptyState: CSSProperties = {
  padding: "8rem 2rem",
  textAlign: "center",
  width: "100%",
};

const container: CSSProperties = {
  padding: "4rem 2rem",
  maxWidth: 1600,
  margin: "0 auto",
  width: "100%",
};

const title: CSSProperties = {
  marginBottom: "3rem",
  fontSize: "2.5rem",
  fontWeight: 400,
  letterSpacing: "-0.02em",
};

const grid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
  gap: "2.5rem",
};

const placeholderWrapper: CSSProperties = {
  width: "100%",
  height: "100%",
  background: "var(--surface2)",
};
