// Top-bar check in / check out widget (T-037).
//
// Green when a session is open, neutral when not. The endpoints run under
// IsAuthenticated with ownership forced server-side, so an ordinary employee
// can use this without any HR permission. Accounts with no linked employee
// (the admin login) get no widget rather than a permanent error.

import { useCallback, useEffect, useRef, useState } from "react";
import { api, auth } from "../api";

// Module scope on purpose: the widget remounts on every navigation, and an
// account with no linked employee (the admin login) would otherwise re-probe
// and 400 on every screen change. Keyed by token so signing in as someone else
// re-probes rather than inheriting the previous account's answer.
let noEmployeeForToken = null;

function elapsedLabel(hours) {
  const total = Math.max(0, Number(hours || 0));
  const h = Math.floor(total);
  const m = Math.round((total - h) * 60);
  return `${h}h${String(m).padStart(2, "0")}`;
}

export default function AttendanceWidget() {
  const [status, setStatus] = useState(null);
  const [open, setOpen] = useState(false);
  const token = auth.token;
  const [unavailable, setUnavailable] = useState(noEmployeeForToken === token);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const ref = useRef(null);

  const load = useCallback(async () => {
    try {
      setStatus(await api.get("/api/attendance/status/"));
    } catch {
      noEmployeeForToken = token;
      setUnavailable(true);
    }
  }, [token]);

  useEffect(() => {
    if (noEmployeeForToken !== token) load();
  }, [load, token]);

  // Keep the elapsed counter honest while a session is open.
  useEffect(() => {
    if (!status?.checked_in) return;
    const timer = setInterval(load, 60000);
    return () => clearInterval(timer);
  }, [status?.checked_in, load]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  if (unavailable) return null;

  const act = async (verb) => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/attendance/${verb}/`, {});
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const checkedIn = Boolean(status?.checked_in);

  return (
    <div className="navitem" style={{ position: "relative" }} ref={ref}>
      <div
        className={`attendance-dot ${checkedIn ? "in" : "out"}`}
        onClick={() => setOpen(!open)}
        title={checkedIn ? "Checked in" : "Checked out"}
      >
        {checkedIn ? "●" : "○"}
      </div>

      {open && (
        <div className="popover" onClick={(e) => e.stopPropagation()}>
          {error && <div className="alert error tiny">{error}</div>}

          <div className="row mb" style={{ justifyContent: "space-between" }}>
            <span className="tiny faint">Status</span>
            <span className={`badge ${checkedIn ? "green" : "grey"}`}>
              {checkedIn ? "Checked in" : "Checked out"}
            </span>
          </div>

          {checkedIn && (
            <div className="row mb" style={{ justifyContent: "space-between" }}>
              <span className="tiny faint">Current session</span>
              <span className="mono">{elapsedLabel(status.elapsed_hours)}</span>
            </div>
          )}

          <div className="row mb" style={{ justifyContent: "space-between" }}>
            <span className="tiny faint">Today</span>
            <span className="mono">{elapsedLabel(status?.total_today)}</span>
          </div>

          <button
            className={checkedIn ? "danger" : "primary"}
            style={{ width: "100%" }}
            disabled={busy}
            onClick={() => act(checkedIn ? "check_out" : "check_in")}
          >
            {busy ? <span className="spinner" /> : checkedIn ? "Check Out" : "Check In"}
          </button>
        </div>
      )}
    </div>
  );
}
