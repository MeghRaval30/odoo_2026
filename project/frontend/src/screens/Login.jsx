// Login screen (T-032, brought to the mockup's copy in T-101).
//
// The mockup's LOGIN / USER ACCESS NOTE is the spec for this screen: accounts
// are created by an administrator, linked to an employee and assigned one or
// more roles. Nothing here creates an account, and there is no self-service
// password reset for a signed-out person — the honest answer is the
// administrator.
//
// The five demo chips are a demo device, not a product feature, so they are
// compiled out of a production build. `import.meta.env.DEV` is true under
// `npm run dev` (which is how the demo runs) and false in `npm run build`.

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
const SHOW_DEMO_ACCOUNTS =
  import.meta.env.DEV && import.meta.env.VITE_DEMO_ACCOUNTS !== "0";

export default function Login() {
  const [email, setEmail] = useState(SHOW_DEMO_ACCOUNTS ? "admin@oxp.com" : "");
  const [password, setPassword] = useState(SHOW_DEMO_ACCOUNTS ? DEMO_PASSWORD : "");
  const [error, setError] = useState(null);
  const [forgot, setForgot] = useState(false);
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
        <div className="login-brand">
          People<span style={{ color: "var(--primary)" }}>Pay</span>360
        </div>

        <form className="card" onSubmit={submit}>
          <h1 className="login-head">Welcome back</h1>
          <div className="tiny faint login-sub">Sign in to continue to your workspace</div>

          {error && <div className="alert error">{error}</div>}
          {forgot && (
            <div className="alert info">
              Ask your administrator to reset it.
            </div>
          )}

          <div className="field">
            <label htmlFor="email">Work Email</label>
            <input
              id="email"
              type="email"
              value={email}
              placeholder="name@company.com"
              autoComplete="username"
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="field">
            <div className="login-label-row">
              <label htmlFor="password">Password</label>
              <button
                type="button"
                className="linky tiny"
                onClick={() => setForgot(true)}
              >
                Forgot password?
              </button>
            </div>
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
            {busy ? <span className="spinner" /> : "Sign In"}
          </button>

          <div className="tiny faint login-note">
            Accounts are created by an administrator.
          </div>
        </form>

        {SHOW_DEMO_ACCOUNTS && (
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
          </div>
        )}
      </div>
    </div>
  );
}
