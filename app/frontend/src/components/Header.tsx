import { Search, SlidersHorizontal, Camera } from "lucide-react";
import { Link } from "react-router-dom";
import type { CSSProperties } from "react";

type Props = {
  search: string;
  onSearch: (val: string) => void;
  /** Run query now (Enter key or search button). */
  onSearchSubmit?: () => void;
  onOpenFilters?: () => void;
  onUploadClick?: () => void;
};

export function Header({ search, onSearch, onSearchSubmit, onOpenFilters, onUploadClick }: Props) {
  return (
    <header style={headerStyle}>
      <div style={containerStyle}>
        {/* Logo / Brand */}
        <Link to="/" style={brandStyle}>
           <div style={logoIconPlaceholder}>FA</div>
           <span style={{ fontWeight: 700, fontSize: "1.25rem" }}>FashionApp</span>
        </Link>

        {/* Centered Search Bar */}
        <div style={searchContainerStyle}>
          <div style={searchInputWrapperStyle}>
            <input
              type="text"
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onSearchSubmit?.();
                }
              }}
              placeholder="Search for clothes, styles, colors..."
              style={searchInputStyle}
            />
            <button
              type="button"
              onClick={() => onSearchSubmit?.()}
              style={searchIconBtnStyle}
              aria-label="Search"
            >
              <Search size={20} color="#FFFFFF" />
            </button>
          </div>
          {/* Filters Button */}
          <button
            type="button"
            onClick={() => onOpenFilters?.()}
            style={filterBtnStyle}
            aria-label={onOpenFilters ? "Toggle filters" : "Filters"}
            disabled={!onOpenFilters}
          >
            <SlidersHorizontal size={20} color="var(--primary)" />
          </button>
        </div>

        {/* Right Actions */}
        <div style={actionsContainerStyle}>
          <button onClick={onUploadClick} style={actionBtnStyle}>
            <Camera size={24} color="#FFFFFF" />
            <span style={actionBtnTextStyle}>Scan / Upload</span>
          </button>
        </div>
      </div>
    </header>
  );
}

const headerStyle: CSSProperties = {
  backgroundColor: "rgba(250, 250, 250, 0.8)",
  backdropFilter: "blur(16px)",
  color: "var(--primary)",
  padding: "1rem 1.5rem",
  position: "sticky",
  top: 0,
  zIndex: 100,
  borderBottom: "1px solid var(--border)",
};

const containerStyle: CSSProperties = {
  maxWidth: 1600,
  margin: "0 auto",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "2rem",
};

const brandStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  color: "var(--primary)",
  textDecoration: "none",
  fontWeight: 600,
  fontSize: "1.1rem",
  letterSpacing: "-0.02em"
};

const logoIconPlaceholder: CSSProperties = {
  width: 38,
  height: 38,
  backgroundColor: "var(--primary)",
  color: "#FFF",
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: "bold",
  fontSize: "1rem",
};

const searchContainerStyle: CSSProperties = {
  flex: 1,
  maxWidth: 700,
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
};

const searchInputWrapperStyle: CSSProperties = {
  display: "flex",
  flex: 1,
  backgroundColor: "var(--surface2)",
  border: "1px solid var(--border)",
  borderRadius: 9999,
  overflow: "hidden",
  padding: "4px 4px 4px 1.25rem",
  transition: "all 0.2s",
};

const searchInputStyle: CSSProperties = {
  flex: 1,
  border: "none",
  outline: "none",
  backgroundColor: "transparent",
  fontSize: "0.95rem",
  color: "var(--text)",
  padding: "0.5rem 0",
};

const searchIconBtnStyle: CSSProperties = {
  backgroundColor: "var(--text)",
  border: "none",
  borderRadius: "50%",
  width: 36,
  height: 36,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  flexShrink: 0,
};

const filterBtnStyle: CSSProperties = {
  backgroundColor: "var(--surface2)",
  border: "1px solid var(--border)",
  borderRadius: "50%",
  width: 44,
  height: 44,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  transition: "all 0.2s",
  color: "var(--text)",
};

const actionsContainerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1rem",
};

const actionBtnStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  backgroundColor: "var(--primary)",
  padding: "0.55rem 1.25rem",
  borderRadius: 9999,
  border: "none",
  color: "#FFF",
  cursor: "pointer",
  transition: "transform 0.2s",
};

const actionBtnTextStyle: CSSProperties = {
  fontSize: "0.85rem",
  fontWeight: 600,
};
