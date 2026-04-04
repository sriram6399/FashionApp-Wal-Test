import { useCallback, useRef, useState } from "react";
import Webcam from "react-webcam";
import { Camera, UploadCloud, X, Aperture } from "lucide-react";
import type { CSSProperties } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: () => void;
  upload: (file: File, opts: { caption: string; tags: string; uploadMetadataJson: string }) => Promise<void>;
};

export function CameraUpload({ isOpen, onClose, onUploaded, upload }: Props) {
  const [mode, setMode] = useState<"camera" | "upload">("camera");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  
  const [caption, setCaption] = useState("");
  const [tags, setTags] = useState("");
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const webcamRef = useRef<Webcam>(null);

  const handleCapture = useCallback(() => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) setCapturedImage(imageSrc);
    }
  }, [webcamRef]);

  const base64ToFile = async (base64String: string) => {
    const res = await fetch(base64String);
    const blob = await res.blob();
    return new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
  };

  const submitAction = async () => {
    setErr(null);
    let targetFile = selectedFile;
    
    if (mode === "camera") {
        if (!capturedImage) return;
        targetFile = await base64ToFile(capturedImage);
    }

    if (!targetFile) return;

    setBusy(true);
    try {
      await upload(targetFile, { caption, tags, uploadMetadataJson: "" });
      setCaption(""); setTags(""); setCapturedImage(null); setSelectedFile(null);
      onUploaded();
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const onFilesDrop = (files: FileList | null) => {
    if (!files?.length) return;
    setSelectedFile(files[0]);
    // Create an object URL just for local previewing of the dropped file
    setCapturedImage(URL.createObjectURL(files[0]));
  };

  if (!isOpen) return null;

  return (
    <div className="upload-overlay">
      <div className="upload-modal-container">
        
        <div className="upload-modal-header">
          <h2 style={{ fontSize: "1.4rem", margin: 0 }}>Publish Item</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)" }}>
            <X size={26} />
          </button>
        </div>

        <div className="upload-modal-body">
            {/* LEFT COLUMN: VISUALS */}
            <div className="upload-modal-left">
                {capturedImage ? (
                    <img src={capturedImage} style={{ width: "100%", height: "100%", objectFit: "cover" }} alt="Captured Preview" />
                ) : (
                    mode === "camera" ? (
                        <>
                            <Webcam
                                audio={false}
                                ref={webcamRef}
                                screenshotFormat="image/jpeg"
                                videoConstraints={{ facingMode: "environment" }}
                                style={{ width: "100%", height: "100%", objectFit: "cover", position: "absolute", inset: 0 }}
                            />
                            <button onClick={handleCapture} style={floatingCaptureButton}>
                                <Aperture size={36} color="#000" />
                            </button>
                        </>
                    ) : (
                        <div style={uploadZone}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => { e.preventDefault(); onFilesDrop(e.dataTransfer.files); }}
                        >
                            <UploadCloud size={64} color="var(--muted)" style={{ marginBottom: 16 }} />
                            <h3 style={{ color: "var(--primary)", marginTop: 0 }}>Drop an image file</h3>
                            <p style={{ color: "var(--muted)" }}>Or click to browse</p>
                            <input type="file" accept="image/*" onChange={(e) => onFilesDrop(e.target.files)} style={{ marginTop: 16 }} />
                        </div>
                    )
                )}

                {/* Overlaid Mode Tabs if we haven't captured yet */}
                {!capturedImage && (
                    <div style={tabSwitcher}>
                        <button style={mode === "camera" ? tabActive : tabInactive} onClick={() => setMode("camera")}>
                            <Camera size={18} /> Camera
                        </button>
                        <button style={mode === "upload" ? tabActive : tabInactive} onClick={() => setMode("upload")}>
                            <UploadCloud size={18} /> Browse
                        </button>
                    </div>
                )}
            </div>

            {/* RIGHT COLUMN: METADATA */}
            <div className="upload-modal-right">
               <label>Notes & Description</label>
               <textarea 
                  className="form-input" 
                  value={caption} 
                  onChange={(e) => setCaption(e.target.value)} 
                  rows={4} 
                  placeholder="What is this item? Note any specific details, flaws, or measurements..."
                  disabled={busy} 
               />

               <label>Designer / Tags</label>
               <input 
                  className="form-input" 
                  value={tags} 
                  onChange={(e) => setTags(e.target.value)} 
                  placeholder="e.g. Vintage, SSENSE, Zara, Summer Collection" 
                  disabled={busy} 
               />

               {err && <div style={{ color: "var(--danger)", padding: "1rem", background: "rgba(239, 68, 68, 0.1)", borderRadius: 8 }}>{err}</div>}

               <div style={{ flex: 1 }} />

               <div style={{ display: "flex", gap: "1rem" }}>
                   {capturedImage && (
                       <button className="btn-secondary" disabled={busy} onClick={() => { setCapturedImage(null); setSelectedFile(null); }}>
                           Retake
                       </button>
                   )}
                   <button 
                       className="btn-primary" 
                       disabled={busy || !capturedImage} 
                       onClick={submitAction}
                   >
                       {busy ? "Uploading & Classifying..." : "Publish to Library"}
                   </button>
               </div>
            </div>
        </div>
      </div>
    </div>
  );
}

const floatingCaptureButton: CSSProperties = {
  position: "absolute",
  bottom: "2.5rem",
  width: 80,
  height: 80,
  borderRadius: "50%",
  backgroundColor: "#FFF",
  boxShadow: "0 10px 25px rgba(0,0,0,0.4)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  border: "none",
  cursor: "pointer",
  zIndex: 10,
};

const tabSwitcher: CSSProperties = {
    position: "absolute",
    top: "1.5rem",
    background: "rgba(0,0,0,0.6)",
    backdropFilter: "blur(8px)",
    borderRadius: 999,
    display: "flex",
    padding: 6,
    gap: 4,
    zIndex: 10,
};

const tabActive: CSSProperties = {
    display: "flex", gap: 8, alignItems: "center",
    background: "#FFF", color: "#000", border: "none", padding: "0.5rem 1rem", borderRadius: 999, fontWeight: 600, fontSize: "0.9rem", cursor: "pointer"
};

const tabInactive: CSSProperties = {
    display: "flex", gap: 8, alignItems: "center",
    background: "transparent", color: "#FFF", border: "none", padding: "0.5rem 1rem", borderRadius: 999, fontWeight: 600, fontSize: "0.9rem", cursor: "pointer"
};

const uploadZone: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    height: "100%",
    background: "rgba(255,255,255,0.05)",
};
