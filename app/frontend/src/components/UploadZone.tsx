import { useCallback, useState } from "react";
import type { CSSProperties } from "react";

type Props = {
  onUploaded: () => void;
  upload: (file: File) => Promise<void>;
};

export function UploadZone({ onUploaded, upload }: Props) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setErr(null);
      setBusy(true);
      try {
        for (const f of Array.from(files)) {
          await upload(f);
        }
        onUploaded();
      } catch (e) {
        setErr(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setBusy(false);
      }
    },
    [onUploaded, upload]
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
