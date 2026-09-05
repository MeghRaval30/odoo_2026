// Minimal hash router.
//
// Hash routing rather than history routing on purpose: api.js already forces
// `window.location.hash = "#/login"` on a 401, so the whole app has to agree
// that the hash is the source of truth. It also means the built frontend can be
// opened from a file path or served from any subdirectory without rewrites.

import { useEffect, useState } from "react";

export function parseHash(hash) {
  const raw = (hash || "").replace(/^#/, "") || "/";
  const [pathPart, queryPart] = raw.split("?");
  const parts = pathPart.split("/").filter(Boolean);
  return {
    path: "/" + parts.join("/"),
    parts,
    query: Object.fromEntries(new URLSearchParams(queryPart || "")),
  };
}

export function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return route;
}

export function navigate(to) {
  const next = to.startsWith("#") ? to : `#${to}`;
  if (window.location.hash === next) return;
  window.location.hash = next;
}

// For <a href> targets, so middle-click and "open in new tab" still behave.
export const href = (to) => `#${to}`;
