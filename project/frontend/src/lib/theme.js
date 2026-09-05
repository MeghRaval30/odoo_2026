import { useEffect, useState } from "react";

// Theme selection: apply, persist, list.
//
// The choice is per browser rather than per account, deliberately. Someone
// demoing on a projector wants Blueprint for its contrast; the same person on
// a laptop at night wants Console. That is a property of where you are sitting,
// not of who you are, so it lives in localStorage and never touches the server.

export const THEMES = [
  {
    id: "ledger",
    name: "Ledger",
    blurb: "Warm paper, serif figures, hairline rules",
    swatch: ["#f4efe9", "#d97757", "#3b2e28"],
  },
  {
    id: "console",
    name: "Console",
    blurb: "Dark slate, monospaced numbers, caps labels",
    swatch: ["#0d1117", "#3fd0c9", "#e4ecf4"],
  },
  {
    id: "atrium",
    name: "Atrium",
    blurb: "Light and roomy, soft shadows, indigo",
    swatch: ["#f6f7fb", "#4f46e5", "#14161f"],
  },
  {
    id: "blueprint",
    name: "Blueprint",
    blurb: "Square corners, 2px rules, projector contrast",
    swatch: ["#ffffff", "#0040ff", "#0a0a0a"],
  },
  {
    id: "marigold",
    name: "Marigold",
    blurb: "Cream and cocoa, rounded, humanist serif",
    swatch: ["#fbf5ea", "#d98324", "#2e2317"],
  },
  {
    id: "graphite",
    name: "Graphite",
    blurb: "Neutral dark, amber accent, grotesk display",
    swatch: ["#131316", "#f5a524", "#ececf0"],
  },
];

const KEY = "pp360_theme";
export const DEFAULT_THEME = "ledger";

export function currentTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && THEMES.some((t) => t.id === saved)) return saved;
  } catch {
    /* private browsing, blocked storage — fall through to the default */
  }
  return DEFAULT_THEME;
}

export function applyTheme(id) {
  const theme = THEMES.some((t) => t.id === id) ? id : DEFAULT_THEME;
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* the theme still applies for this page; it just will not be remembered */
  }
  return theme;
}

/** Call once at start-up, before first paint, so there is no flash of Ledger. */
export function initTheme() {
  return applyTheme(currentTheme());
}

// --------------------------------------------------------------- charts

/**
 * Recharts cannot read CSS custom properties — it needs concrete colour
 * strings for its own interpolation — so the chart palette used to be a hand
 * copy of Ledger's tokens at the top of `Dashboard.jsx`. With one theme that
 * was merely fragile. With six it was wrong: a terracotta line on Blueprint's
 * electric blue, and on the two dark themes an axis drawn in a light-theme
 * grey that vanished into the card.
 *
 * So read the tokens back out of the document instead. Same source of truth as
 * every other colour in the product, resolved at render time for whichever
 * theme is on.
 */
export function chartPalette() {
  const cs = getComputedStyle(document.documentElement);
  const token = (name, fallback) =>
    cs.getPropertyValue(name).trim() || fallback;
  return {
    accent: token("--primary", "#d97757"),
    green: token("--green", "#5b7d58"),
    amber: token("--amber", "#a97a24"),
    red: token("--red", "#b5504a"),
    purple: token("--purple", "#856b9c"),
    rose: token("--rose", "#c0757b"),
    grid: token("--border", "#e7d9d1"),
    dim: token("--text-faint", "#9c8f84"),
    surface: token("--surface", "#fffcf9"),
    text: token("--text", "#241e1a"),
    sans: token("--font-sans", "Inter, sans-serif"),
    radius: parseInt(token("--radius", "8px"), 10) || 0,
    shadow: token("--shadow-pop", "0 6px 22px rgba(59,46,40,0.16)"),
  };
}

/**
 * The palette for the theme currently on, recomputed when it changes.
 *
 * The switcher sets `data-theme` on <html> without remounting anything, so a
 * palette captured once at module load would go stale the moment somebody
 * changed theme with a dashboard open — which is exactly what a demo does.
 */
export function useChartPalette() {
  const [palette, setPalette] = useState(chartPalette);

  useEffect(() => {
    const observer = new MutationObserver(() => setPalette(chartPalette()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  return palette;
}
