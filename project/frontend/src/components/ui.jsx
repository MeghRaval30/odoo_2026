// Shared UI primitives.
//
// DRF paginates list endpoints (PAGE_SIZE 50) but the custom @action endpoints
// return bare arrays, so every consumer goes through rows().

import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

export const rows = (payload) =>
  Array.isArray(payload) ? payload : payload?.results || [];

// Department, JobPosition, WorkLocation and WorkingSchedule all carry a
// required company FK that no create form asks for, because the product is
// single-company (D-003). Without this, every one of those "New" buttons failed
// with "company: This field is required."
export function useDefaultCompany() {
  const [company, setCompany] = useState(null);

  useEffect(() => {
    api
      .get("/api/companies/")
      .then((payload) => setCompany(rows(payload)[0]?.id ?? null))
      .catch(() => setCompany(null));
  }, []);

  return company;
}

// Search boxes feed straight into useResource, so without this every keystroke
// fired a request and the responses could land out of order.
export function useDebounced(value, delay = 300) {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return settled;
}

/**
 * Fetch a list resource.
 *
 * `path` may be null, meaning "there is nothing to ask for" -- the request is
 * skipped and the hook settles empty rather than loading forever. That is the
 * honest shape for a screen whose subject does not exist for this account: an
 * account with no employee record has no payslips of its own, and the
 * alternative is either an unfiltered request that returns everybody's or a
 * sentinel filter value the server rejects as an invalid choice. Hooks cannot
 * be called conditionally, so the condition belongs here.
 */
export function useResource(path, params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState(null);
  const key = JSON.stringify(params || {});

  const reload = useCallback(async () => {
    if (!path) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await api.get(path, JSON.parse(key)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [path, key]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, rows: rows(data), loading, error, reload, setData };
}

export function Modal({ title, children, footer, onClose, wide }) {
  useEffect(() => {
    const onEsc = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [onClose]);

  return (
    <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className={`modal${wide ? " wide" : ""}`}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="ghost sm" onClick={onClose}>
            &#10005;
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <div className="tiny faint">{hint}</div>}
    </div>
  );
}

const STATE_TONE = {
  DRAFT: "grey",
  TO_APPROVE: "amber",
  COMPUTED: "amber",
  CONFIRM: "amber",
  RUNNING: "green",
  APPROVED: "green",
  VALIDATED: "green",
  PAID: "green",
  EXPIRED: "grey",
  REFUSED: "red",
  CANCELLED: "red",
  NEW: "grey",
};

export function StateBadge({ state, label }) {
  if (!state) return <span className="faint">—</span>;
  return (
    <span className={`badge ${STATE_TONE[state] || "grey"}`}>{label || state}</span>
  );
}

export const Loading = () => <div className="empty"><span className="spinner" /></div>;

export const ErrorBox = ({ error }) =>
  error ? <div className="alert error">{error}</div> : null;

export function PageHead({ title, sub, children }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      {sub && <span className="sub">{sub}</span>}
      <div className="spacer" />
      {children}
    </div>
  );
}
