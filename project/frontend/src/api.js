// API client for the PeoplePay360 backend.

const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const TOKEN_KEY = "pp360_token";
const USER_KEY = "pp360_user";

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  get user() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  set(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  can(permission) {
    return Boolean(this.user?.permissions?.[permission]);
  },
  /**
   * Capability check against the matrix the server enforces with.
   *
   * `can()` reads the four legacy booleans and stays for screens written
   * before the matrix existed; this reads the real thing. Both are UI hints —
   * every route is gated server-side regardless of what is rendered.
   */
  has(...capabilities) {
    const held = this.user?.capabilities || [];
    return capabilities.some((c) => held.includes(c));
  },
  merge(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
};

export class ApiError extends Error {
  constructor(status, payload) {
    super(ApiError.describe(payload) || `Request failed (${status})`);
    this.status = status;
    this.payload = payload;
  }

  // The backend surfaces business-rule violations as field errors; flatten
  // them into something a person can read.
  static describe(payload) {
    if (!payload) return null;
    if (typeof payload === "string") return payload;
    if (payload.detail) {
      return Array.isArray(payload.detail)
        ? payload.detail.join(" ")
        : payload.detail;
    }
    const parts = [];
    for (const [field, value] of Object.entries(payload)) {
      const text = Array.isArray(value) ? value.join(" ") : String(value);
      parts.push(field === "non_field_errors" ? text : `${field}: ${text}`);
    }
    return parts.join(" · ");
  }
}

async function request(path, { method = "GET", body, params } = {}) {
  const url = new URL(path.startsWith("http") ? path : `${BASE}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  const headers = { "Content-Type": "application/json" };
  if (auth.token) headers.Authorization = `Token ${auth.token}`;

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401) {
    auth.clear();
    window.location.hash = "#/login";
    throw new ApiError(401, { detail: "Session expired. Please sign in again." });
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

export const api = {
  get: (path, params) => request(path, { params }),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  delete: (path) => request(path, { method: "DELETE" }),

  async login(email, password) {
    const data = await request("/api/auth/login/", {
      method: "POST",
      body: { email, password },
    });
    auth.set(data.token, data.user);
    return data.user;
  },

  // Re-read the signed-in account. The navigation tree and capability list
  // come from the server, so a role change made by an administrator has to be
  // able to reach a session that is already open.
  async refreshMe() {
    const user = await request("/api/auth/me/");
    auth.merge(user);
    return user;
  },

  async logout() {
    try {
      await request("/api/auth/logout/", { method: "POST" });
    } finally {
      auth.clear();
    }
  },

  // Payslip PDF needs the raw blob rather than JSON
  async payslipPdf(id) {
    const response = await fetch(`${BASE}/api/payslips/${id}/pdf/`, {
      headers: { Authorization: `Token ${auth.token}` },
    });
    if (!response.ok) throw new ApiError(response.status, "Could not render PDF");
    return response.blob();
  },

  // Payroll register CSV — also a blob, and the filename comes from the server
  async payrunRegister(id) {
    const response = await fetch(`${BASE}/api/payruns/${id}/register/`, {
      headers: { Authorization: `Token ${auth.token}` },
    });
    if (!response.ok) {
      throw new ApiError(response.status, "Could not export the register");
    }
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    return { blob: await response.blob(), filename: match?.[1] || "register.csv" };
  },
};

// Hand a blob to the browser as a download.
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

// -- formatting helpers ----------------------------------------------------

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

export const money = (value) => inr.format(Number(value || 0));

export const compactMoney = (value) => {
  const n = Number(value || 0);
  if (n >= 1e7) return `₹ ${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `₹ ${(n / 1e5).toFixed(2)}L`;
  if (n >= 1e3) return `₹ ${(n / 1e3).toFixed(1)}k`;
  return inr.format(n);
};

export const formatDate = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : "—";

export const formatDateTime = (value) =>
  value
    ? new Date(value).toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

export const formatTime = (value) =>
  value
    ? new Date(value).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";


/**
 * Decimal hours as `8h 27m`.
 *
 * The API sends this pre-formatted on attendance rows, and this is the fallback
 * for aggregates computed in the browser. Never render raw decimal hours to a
 * person: `8.45` is eight hours and twenty-seven minutes, not forty-five, and a
 * timesheet that invites that misreading is a timesheet nobody trusts.
 */
export function hoursMinutes(value, blank = "—") {
  const total = Number(value || 0);
  if (!Number.isFinite(total) || total === 0) return blank;
  const sign = total < 0 ? "-" : "";
  const minutes = Math.round(Math.abs(total) * 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return sign + (h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`);
}

/** `6h56` — the compact form the mockup's attendance widget uses. */
export function hoursMinutesCompact(value) {
  const minutes = Math.round(Math.abs(Number(value || 0)) * 60);
  return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`;
}
