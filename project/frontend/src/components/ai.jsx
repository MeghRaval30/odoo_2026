// Presentational pieces for the import studio.
//
// Everything here shows one fact and nothing here fetches anything. They are
// separated from the studio screen because the studio is already a state
// machine over a stream, and mixing "how a confidence bar animates" into that
// makes both harder to read.
//
// The house rule for all of it: motion carries information or it does not
// happen. A confidence bar fills so you can see how far it got. A reason types
// out because it is being produced as you watch. Nothing bounces, nothing
// spins for decoration, and under prefers-reduced-motion every one of these
// renders its finished state immediately.

import { useEffect, useRef, useState } from "react";

//: Ten hues, assigned to fields in the order the schema declares them, so a
//: field keeps its colour between files and between sessions.
export const HUES = 10;

export function hueFor(fieldKey, fields) {
  if (!fieldKey) return null;
  const i = (fields || []).findIndex((f) => f.key === fieldKey);
  return (i < 0 ? 0 : i % HUES) + 1;
}

export const hueVar = (hue) => (hue ? `var(--fld-${hue})` : "var(--text-faint)");
export const hueWash = (hue) => (hue ? `var(--fld-${hue}-wash)` : "var(--surface-2)");

const reduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// ---------------------------------------------------------------------------

export function ScanBeam({ active }) {
  if (!active) return null;
  return <div className="scanbeam" aria-hidden="true" />;
}

export function Pulse({ active = true }) {
  if (!active) return null;
  return <span className="pulse-ring" aria-hidden="true" />;
}

/**
 * Types `text` out one character at a time.
 *
 * Used only for text the model produced. That is a deliberate limit: if
 * everything types, typing stops meaning anything, and the one thing worth
 * signalling on this screen is which words came from the model rather than
 * from the deterministic half.
 */
export function ThinkingStream({ text, speed = 14, onDone }) {
  const [shown, setShown] = useState(reduced() ? text || "" : "");
  const done = useRef(false);

  useEffect(() => {
    if (reduced()) {
      setShown(text || "");
      onDone?.();
      return;
    }
    const full = text || "";
    setShown("");
    done.current = false;
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setShown(full.slice(0, i));
      if (i >= full.length) {
        clearInterval(timer);
        if (!done.current) {
          done.current = true;
          onDone?.();
        }
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);

  const finished = shown.length >= (text || "").length;
  return (
    <div className="thinking">
      {shown}
      {!finished && <span className="caret" />}
    </div>
  );
}

export function ConfidenceBar({ value = 0, label }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const tone = value >= 0.75 ? "high" : value >= 0.55 ? "mid" : "low";
  return (
    <span className="row" style={{ gap: 6, alignItems: "center" }}>
      <span className={`confbar ${tone}`}>
        <i style={{ width: `${pct}%` }} />
      </span>
      {label !== false && <span className="tiny faint mono">{pct}%</span>}
    </span>
  );
}

//: Three letters rather than three icons. The voters are a dictionary, some
//: arithmetic and a language model, and no icon says that -- a label the
//: legend can explain once does.
const VOTER_LABEL = { lexical: "LEX", shape: "SHP", model: "AI" };

export function VoteStack({ votes, fields }) {
  if (!votes?.length) return null;
  const labelFor = (key) =>
    (fields || []).find((f) => f.key === key)?.label || key || "nothing";

  return (
    <div className="votes">
      {votes.map((v, i) => (
        <div key={i} className={`vote ${v.status || ""}`}>
          <span className="who">{VOTER_LABEL[v.voter] || v.voter}</span>
          <span className="what">
            <b>{labelFor(v.field)}</b>
            {v.reason ? ` — ${v.reason}` : ""}
          </span>
          <ConfidenceBar value={v.confidence} label={false} />
        </div>
      ))}
    </div>
  );
}

export function FieldChip({ label, hue, muted }) {
  if (!label) return null;
  return (
    <span
      className="fieldchip"
      style={{
        color: muted ? "var(--text-faint)" : hueVar(hue),
        background: muted ? "var(--surface-2)" : hueWash(hue),
      }}
    >
      <span className="dot" />
      {label}
    </span>
  );
}

export function TransformChip({ t, active, onClick }) {
  return (
    <button
      type="button"
      className={`tchip${active ? " on" : ""}`}
      title={t.detail}
      onClick={onClick}
    >
      {t.label}
    </button>
  );
}

export function TransformRow({ transforms, activeId, onPick }) {
  if (!transforms?.length) return <span className="tiny faint">No changes</span>;
  return (
    <span className="tchip-row">
      {transforms.map((t, i) => (
        <span key={`${t.id}-${i}`} className="row" style={{ gap: 4 }}>
          {i > 0 && <span className="tchip-sep">+</span>}
          <TransformChip
            t={t}
            active={activeId === i}
            onClick={() => onPick?.(activeId === i ? null : i)}
          />
        </span>
      ))}
    </span>
  );
}

export function DiffCell({ before, after }) {
  const changed = String(before ?? "") !== String(after ?? "");
  if (!changed) return <span>{String(after ?? "")}</span>;
  return (
    <span>
      <span className="diff-before">{String(before ?? "")}</span>
      <span className="diff-arrow">&rarr;</span>
      <span className="diff-after">{String(after ?? "") || "(empty)"}</span>
    </span>
  );
}

/** Counts up to `to`. Used once, on the result card, where it earns itself. */
export function CountUp({ to = 0, duration = 700 }) {
  const [n, setN] = useState(reduced() ? to : 0);

  useEffect(() => {
    if (reduced()) {
      setN(to);
      return;
    }
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      // Ease out, so it decelerates into the final figure instead of stopping.
      setN(Math.round(to * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to, duration]);

  return <>{n.toLocaleString("en-IN")}</>;
}

export function Stagger({ index = 0, children, step = 45 }) {
  return (
    <div className="stagger" style={{ animationDelay: `${index * step}ms` }}>
      {children}
    </div>
  );
}

export function LlmPill({ health, onClick }) {
  if (!health) return null;
  const on = health.available;
  return (
    <button
      type="button"
      className={`llmpill ${on ? "on" : "off"}`}
      onClick={onClick}
      title={health.message}
    >
      <span className="dot" />
      {on ? `Local model ready — ${health.model}` : "Running on rules only"}
    </button>
  );
}
