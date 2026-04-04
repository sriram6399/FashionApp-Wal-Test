import { useCallback, useState } from "react";
import type { CSSProperties } from "react";

type Props = {
  onUploaded: () => void;
  upload: (file: File, opts: { caption: string; tags: string; uploadMetadataJson: string }) => Promise<void>;
  caption: string;
  onCaptionChange: (v: string) => void;
  tags: string;
  onTagsChange: (v: string) => void;
  uploadMetadataJson: string;
  onUploadMetadataChange: (v: string) => void;
};

export function UploadZone({
  onUploaded,
  upload,
  caption,
  onCaptionChange,
  tags,
  onTagsChange,
  uploadMetadataJson,
  onUploadMetadataChange,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setErr(null);
      const metaTrim = uploadMetadataJson.trim();
      if (metaTrim) {
        try {
          const p = JSON.parse(metaTrim) as unknown;
          if (p === null || typeof p !== "object" || Array.isArray(p)) {
            setErr("Metadata must be a JSON object, e.g. {\"city\":\"Lisbon\",\"event\":\"market\"}");
            return;
          }
        } catch {
          setErr("Metadata must be valid JSON object syntax");
          return;
        }
      }
      setBusy(true);
      try {
        for (const f of Array.from(files)) {
          await upload(f, { caption, tags, uploadMetadataJson });
        }
        onUploaded();
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setBusy(false);
      }
    },
    [onUploaded, upload, caption, tags, uploadMetadataJson]
  );

  return (
    <div
      style={zone}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onFiles(e.dataTransfer.files);
      }}
    >
      <p style={{ margin: 0, fontSize: "0.95rem" }}>
        {busy ? "Uploading…" : "Drop garment photos here, or choose files"}
      </p>
      <label style={lbl}>
        Caption (sent to the vision model + search index)
        <input
          value={caption}
          onChange={(e) => onCaptionChange(e.target.value)}
          placeholder="e.g. Pleated skirt at Mercado da Ribeira"
          style={inp}
          disabled={busy}
        />
      </label>
      <label style={lbl}>
        Tags (comma-separated — same as mobile capture chips)
        <input
          value={tags}
          onChange={(e) => onTagsChange(e.target.value)}
          placeholder="market, linen, summer-trip"
          style={inp}
          disabled={busy}
        />
      </label>
      <label style={lbl}>
        Metadata JSON (optional object — location, date, designer notes)
        <textarea
          value={uploadMetadataJson}
          onChange={(e) => onUploadMetadataChange(e.target.value)}
          placeholder='{"city":"Lisbon","country":"Portugal","month":6,"year":2024}'
          style={{ ...inp, minHeight: 72, fontFamily: "ui-monospace, monospace", fontSize: "0.8rem" }}
          disabled={busy}
        />
      </label>
      <input
        type="file"
        accept="image/*"
        multiple
        disabled={busy}
        style={{ marginTop: 10 }}
        onChange={(e) => onFiles(e.target.files)}
      />
      {err && <p style={{ color: "var(--danger)", margin: "8px 0 0", fontSize: "0.85rem" }}>{err}</p>}
    </div>
  );
}

const zone: CSSProperties = {
  border: "1px dashed var(--border)",
  borderRadius: 12,
  padding: "1.25rem",
  background: "var(--surface2)",
  textAlign: "center",
};

const lbl: CSSProperties = {
  display: "block",
  textAlign: "left",
  marginTop: "0.75rem",
  fontSize: "0.75rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  color: "var(--muted)",
};

const inp: CSSProperties = {
  display: "block",
  width: "100%",
  marginTop: 6,
  padding: "0.5rem 0.65rem",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg)",
  color: "var(--text)",
  boxSizing: "border-box",
};
