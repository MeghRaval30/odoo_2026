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
