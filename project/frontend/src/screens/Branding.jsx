// Whose system this is.
//
// Two images, two names and one slider. The preview beside each upload is the
// point of the screen: a logo is judged at the size it will actually be drawn
// at, and 26px in a dark bar is unforgiving in a way a file browser thumbnail
// does not warn you about. So the logo previews on the bar's own colour, and
// the background mark previews at the wash strength it will be shown at.

import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { ErrorBox, Loading, PageHead } from "../components/ui";

const ACCEPT = ".png,.jpg,.jpeg,.svg,.webp,.gif";

function readAsDataUri(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("That file could not be read."));
    reader.readAsDataURL(file);
  });
}

export default function Branding() {
  const [branding, setBranding] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [appName, setAppName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [opacity, setOpacity] = useState(4);

  useEffect(() => {
    api
      .get("/api/branding/")
      .then((data) => {
        setBranding(data);
        setAppName(data.app_name || "");
        setCompanyName(data.company_name || "");
        setOpacity(data.watermark_opacity ?? 4);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function save(body) {
    setError(null);
    setBusy(true);
    setSaved(false);
    try {
      const next = await api.patch("/api/branding/update/", body);
      setBranding(next);
      setSaved(true);
      // The shell reads branding once at mount, so a change here is not on
      // screen until it does that again. Saying so is better than a top bar
      // that silently disagrees with this page.
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function upload(which, file) {
    if (!file) return;
    try {
      const uri = await readAsDataUri(file);
      await save({ [`${which}_b64`]: uri, [`${which}_filename`]: file.name });
    } catch (e) {
      setError(e.message);
    }
  }

  if (!branding) return <Loading />;

  return (
    <div className="page">
      <PageHead
        title="Branding"
        sub={branding.company_name || branding.app_name}
      />

      {error && <ErrorBox error={error} />}

      <div className="grid">
        <ImageCard
          title="Top bar logo"
          hint="Drawn 26px high"
          image={branding.logo}
          filename={branding.logo_filename}
          onPick={(file) => upload("logo", file)}
          onClear={() => save({ logo_b64: "" })}
          busy={busy}
          dark
        />

        <ImageCard
          title="Background mark"
          hint="Falls back to the top bar logo"
          image={branding.watermark}
          filename={branding.watermark_filename}
          onPick={(file) => upload("watermark", file)}
          onClear={() => save({ watermark_b64: "" })}
          busy={busy}
          wash={opacity}
        />
      </div>

      <div className="card">
        <div className="row between">
          <h2 className="card-title">Names</h2>
        </div>

        <div className="field">
          <label>Application name</label>
          <input
            value={appName}
            maxLength={60}
            onChange={(e) => setAppName(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Company name</label>
          <input
            value={companyName}
            maxLength={120}
            onChange={(e) => setCompanyName(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Background wash {opacity}%</label>
          <input
            type="range"
            min="0"
            max="40"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
          />
        </div>

        <div className="row">
          <div className="spacer" />
          {saved && <span className="muted tiny">Saved — reload to see the bar</span>}
          <button
            className="primary"
            disabled={busy}
            onClick={() =>
              save({
                app_name: appName,
                company_name: companyName,
                watermark_opacity: opacity,
              })
            }
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

function ImageCard({
  title, hint, image, filename, onPick, onClear, busy, dark, wash,
}) {
  const input = useRef(null);
  return (
    <div className="card">
      <div className="row between">
        <h2 className="card-title">{title}</h2>
        <span className="muted tiny">{hint}</span>
      </div>

      <div
        className={`brand-preview${dark ? " on-bar" : ""}`}
        style={
          wash !== undefined && image
            ? { opacity: Math.max(wash, 3) / 100 + 0.25 }
            : undefined
        }
      >
        {image ? (
          <img src={image} alt={title} />
        ) : (
          <span className="muted tiny">Not set</span>
        )}
      </div>

      <div className="row">
        <span className="muted tiny mono">{filename || "—"}</span>
        <div className="spacer" />
        {image && (
          <button className="ghost sm" disabled={busy} onClick={onClear}>
            Remove
          </button>
        )}
        <button
          className="ghost sm"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          Choose file
        </button>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => onPick(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}
