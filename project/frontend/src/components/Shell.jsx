// Application shell — the mockup's top menu bar, built from the server.
//
// The menu is NOT defined here. `/api/auth/me/` returns a navigation tree
// pruned to the signed-in account's capabilities, and this renders whatever it
// is given. That is deliberate: the mockup's access note says to "show only the
// modules and actions allowed by the user's assigned role", and a menu built
// from the same table the API enforces with cannot drift from it. A hard-coded
// menu here would eventually offer a link that 403s.
//
// Hiding is presentation, never enforcement. Every route these links reach is
// independently gated server-side.

import { useEffect, useRef, useState } from "react";
import { auth, api } from "../api";
import { href, navigate } from "../lib/router";
import { THEMES, applyTheme, currentTheme } from "../lib/theme";
import AttendanceWidget from "./AttendanceWidget";

/**
 * The customer's own marks, read once per session.
 *
 * Kept here rather than in a context because exactly one component draws the
 * logo and exactly one rule draws the wash. A provider would be ceremony
 * around a single consumer.
 *
 * The background mark is applied by setting two custom properties on the root
 * rather than by rendering an element. A fixed element behind the page would
 * have to be kept clear of every stacking context the app already has -- the
 * sticky bar, the modals, the dropdowns -- and the first one that got it wrong
 * would put a company logo across a payslip. A background on the page
 * container cannot do that.
 */
/**
 * The company name as the two lines a logotype is set in.
 *
 * Split on the trailing legal-form words rather than at the halfway point,
 * because that is where these names actually break: "Shree Ganesh" is the
 * name and "Engineering Co" is what kind of company it is, and every printed
 * version of a mark like this stacks them that way. A name with nothing to
 * strip stays on one line rather than being broken somewhere arbitrary.
 */
const TRAILING = ["co", "co.", "company", "ltd", "ltd.", "limited", "llp",
                  "pvt", "pvt.", "private", "inc", "inc.", "corp", "corp.",
                  "industries", "engineering", "enterprises", "works",
                  "technologies", "solutions", "services", "systems", "and",
                  "&"];

function lockup(branding) {
  const name = (branding.company_name || branding.app_name || "").trim();
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length < 3) return [name, ""];

  let cut = words.length;
  while (cut > 1 && TRAILING.includes(words[cut - 1].toLowerCase())) cut -= 1;
  // Nothing recognisable to strip, or it would eat the whole name: one line.
  if (cut === words.length || cut < 1) return [name, ""];
  return [words.slice(0, cut).join(" "), words.slice(cut).join(" ")];
}

function useBranding() {
  const [branding, setBranding] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .get("/api/branding/")
      .then((data) => live && setBranding(data))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (branding && branding.watermark) {
      root.style.setProperty("--watermark", 'url("' + branding.watermark + '")');
      const pct =
        branding.watermark_opacity == null ? 4 : branding.watermark_opacity;
      root.style.setProperty("--watermark-opacity", String(pct / 100));
    } else {
      root.style.removeProperty("--watermark");
      root.style.removeProperty("--watermark-opacity");
    }
  }, [branding]);

  return branding;
}


function initials(user) {
  const source = user?.employee_name || user?.email || "?";
  return source
    .split(/[\s@._]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

/** Fallback for the moment before `/me` has answered, or if it ever fails. */
const MINIMAL_NAV = [{ key: "dashboard", label: "Dashboard", to: "/dashboard" }];

export default function Shell({ route, children }) {
  const [openMenu, setOpenMenu] = useState(null);
  const [userOpen, setUserOpen] = useState(false);
  const [theme, setTheme] = useState(currentTheme);
  const barRef = useRef(null);
  const branding = useBranding();
  const user = auth.user;
  const active = route.parts[0] || "";
  const nav = user?.navigation?.length ? user.navigation : MINIMAL_NAV;

  // Any click outside the bar closes whatever is open; so does Escape.
  useEffect(() => {
    const onDocClick = (event) => {
      if (barRef.current && !barRef.current.contains(event.target)) {
        setOpenMenu(null);
        setUserOpen(false);
      }
    };
    const onEsc = (event) => {
      if (event.key === "Escape") {
        setOpenMenu(null);
        setUserOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  useEffect(() => {
    setOpenMenu(null);
    setUserOpen(false);
  }, [route.path]);

  const signOut = async () => {
    try {
      await api.logout();
    } finally {
      auth.clear();
      navigate("/login");
    }
  };

  const chooseTheme = (id) => setTheme(applyTheme(id));

  /** A group is active when the current route is one of its children. */
  const groupIsActive = (group) =>
    group.to
      ? group.to.slice(1) === active
      : (group.items || []).some((item) => item.to.slice(1) === active);

  return (
    <div className="app">
      <div className="topbar" ref={barRef}>
        <a className="brand brand-plate" href={href("/dashboard")}>
          {branding && branding.logo ? (
            <>
              <img
                className="brand-logo"
                src={branding.logo}
                alt={branding.company_name || branding.app_name}
              />
              <span className="brand-words">
                <span className="brand-l1">{lockup(branding)[0]}</span>
                {lockup(branding)[1] && (
                  <span className="brand-l2">{lockup(branding)[1]}</span>
                )}
              </span>
            </>
          ) : (
            <span className="brand-name">
              People<span>Pay</span>360
            </span>
          )}
        </a>

        {branding && branding.logo && (
          <span className="app-mark">
            People<span>Pay</span>360
          </span>
        )}

        {nav.map((group) => {
          const isActive = groupIsActive(group);

          if (group.to) {
            return (
              <a
                key={group.key}
                className={`navitem${isActive ? " active" : ""}`}
                href={href(group.to)}
              >
                {group.label}
              </a>
            );
          }

          return (
            <div
              key={group.key}
              className={`navitem${isActive ? " active" : ""}`}
              onClick={() => setOpenMenu(openMenu === group.key ? null : group.key)}
            >
              {group.label} <span className="tiny faint">&#9662;</span>
              {openMenu === group.key && (
                <div className="dropdown" onClick={(e) => e.stopPropagation()}>
                  {group.items.map((item) => (
                    <a key={item.to} href={href(item.to)}>
                      {item.label}
                    </a>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        <div className="spacer" />

        <AttendanceWidget />

        <div
          className="navitem"
          style={{ position: "relative" }}
          onClick={() => setUserOpen(!userOpen)}
        >
          <div className="row" style={{ gap: 8, flexWrap: "nowrap" }}>
            <div className="avatar" style={{ width: 26, height: 26, fontSize: 10 }}>
              {initials(user)}
            </div>
            <span className="tiny nowrap">{user?.employee_name || user?.email}</span>
            <span className="tiny faint">&#9662;</span>
          </div>

          {userOpen && (
            <div className="popover" onClick={(e) => e.stopPropagation()}>
              <div className="row" style={{ gap: 11, flexWrap: "nowrap" }}>
                <div className="avatar">{initials(user)}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600 }}>
                    {user?.employee_name || "No employee linked"}
                  </div>
                  <div className="tiny faint">{user?.email}</div>
                  {user?.job_title && (
                    <div className="tiny faint">
                      {user.job_title}
                      {user.department ? ` · ${user.department}` : ""}
                    </div>
                  )}
                </div>
              </div>

              <div className="row mt" style={{ gap: 5 }}>
                {(user?.role_names || user?.roles || []).map((role) => (
                  <span key={role} className="badge blue">
                    {role}
                  </span>
                ))}
              </div>

              <div className="mt" style={{ display: "grid", gap: 3 }}>
                <a className="tiny" href={href("/profile")}>
                  My profile &amp; personal details
                </a>
                <a className="tiny" href={href("/profile/security")}>
                  Password &amp; sessions
                </a>
                {user?.employee_id && (
                  <a className="tiny" href={href("/my-payslips")}>
                    My payslips
                  </a>
                )}
              </div>

              <div className="mt">
                <div className="head" style={{ padding: "0 0 5px" }}>
                  Appearance
                </div>
                <div className="theme-grid">
                  {THEMES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`theme-swatch${theme === t.id ? " on" : ""}`}
                      onClick={() => chooseTheme(t.id)}
                      title={t.blurb}
                    >
                      <span className="nm">{t.name}</span>
                      <span className="dsc">{t.blurb}</span>
                      <span className="chips">
                        {t.swatch.map((c) => (
                          <i key={c} style={{ background: c }} />
                        ))}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <button className="mt" style={{ width: "100%" }} onClick={signOut}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {children}
    </div>
  );
}
