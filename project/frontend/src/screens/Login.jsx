// Login screen (T-032) against POST /api/auth/login/.
//
// The role chips are deliberate: the five graded permission levels are enforced
// server-side, and being able to switch personas in one click during the live
// demo is the fastest way to show that.

import { useState } from "react";
import { api, ApiError } from "../api";
import { navigate } from "../lib/router";

const DEMO_ACCOUNTS = [
  { email: "admin@oxp.com", label: "Admin" },
  { email: "aarav@oxp.com", label: "Payroll Manager" },
  { email: "sara@oxp.com", label: "HR Manager" },
  { email: "rahul@oxp.com", label: "Payroll User" },
  { email: "john@oxp.com", label: "Employee" },
];

const DEMO_PASSWORD = "demo1234";

export default function Login() {
  const [email, setEmail] = useState("admin@oxp.com");
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="center mb">
          <div style={{ fontSize: 21, fontWeight: 700 }}>
            People<span style={{ color: "var(--accent)" }}>Pay</span>360
          </div>
          <div className="tiny faint">Integrated HR &amp; Payroll Operations</div>
        </div>

        <form className="card" onSubmit={submit}>
          {error && <div className="alert error">{error}</div>}

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              autoComplete="username"
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button className="primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? <span className="spinner" /> : "Sign in"}
          </button>
        </form>

        <div className="card">
          <div className="card-title">Demo accounts</div>
          <div className="row" style={{ gap: 6 }}>
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className="sm"
                onClick={() => {
                  setEmail(account.email);
                  setPassword(DEMO_PASSWORD);
                }}
              >
                {account.label}
              </button>
            ))}
          </div>
          <div className="tiny faint mt">
            All demo accounts use the password <span className="mono">demo1234</span>.
          </div>
        </div>
      </div>
    </div>
  );
}
