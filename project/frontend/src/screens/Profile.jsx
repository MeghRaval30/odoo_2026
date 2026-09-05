// My profile — the one screen every role has, whatever else they can reach.
//
// Three tabs, matching the three things a person actually wants to do with
// their own record: read it, correct it, and secure it.
//
// The editable / needs-approval split is served by the API rather than decided
// here, so the screen cannot disagree with the policy. A phone number applies
// straight away; a bank account raises a request for HR. That is not caution
// for its own sake — repointing a bank account the day before a payrun is the
// most attacked field in any payroll system.

import { useEffect, useState } from "react";
import { api, auth, formatDate, formatDateTime } from "../api";
import { ErrorBox, Field, Loading, PageHead } from "../components/ui";
import { navigate } from "../lib/router";

const TABS = [
  { id: "details", label: "Personal details" },
  { id: "requests", label: "Change requests" },
  { id: "security", label: "Password & sessions" },
];

export default function Profile({ route }) {
  const initial = TABS.some((t) => t.id === route.parts[1]) ? route.parts[1] : "details";
  const [tab, setTab] = useState(initial);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setProfile(await api.get("/api/me/profile/"));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    setTab(TABS.some((t) => t.id === route.parts[1]) ? route.parts[1] : "details");
  }, [route.path]);

  const user = auth.user;

  return (
    <div className="page">
      <PageHead
        title="My profile"
        sub="Your own record, and what you may change about it"
      />

      <div className="card mb">
        <div className="profile-head">
          <div className="avatar lg">
            {(profile?.initials || user?.email || "?").slice(0, 2).toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <h2>{profile?.full_name || user?.email}</h2>
            <div className="muted">
              {[profile?.job_title, profile?.department].filter(Boolean).join(" · ") ||
                "No employee record linked to this account"}
            </div>
            <div className="row mt" style={{ gap: 5 }}>
              {(user?.role_names || user?.roles || []).map((r) => (
                <span key={r} className="badge blue">
                  {r}
                </span>
              ))}
            </div>
          </div>
          <div className="spacer" />
          {profile && (
            <dl className="kv" style={{ gridTemplateColumns: "auto auto" }}>
              <dt>Employee code</dt>
              <dd className="mono">{profile.employee_code || "—"}</dd>
              <dt>Joined</dt>
              <dd>{formatDate(profile.date_of_joining)}</dd>
              <dt>Bank details</dt>
              <dd>
                {profile.has_bank_details ? (
                  <span className="badge green">On file</span>
                ) : (
                  <span className="badge amber">Missing</span>
                )}
              </dd>
            </dl>
          )}
        </div>

        <div className="tabs" style={{ marginBottom: 0 }}>
          {TABS.map((t) => (
            <div
              key={t.id}
              className={`tab${tab === t.id ? " on" : ""}`}
              onClick={() => navigate(`/profile/${t.id}`)}
            >
              {t.label}
            </div>
          ))}
        </div>
      </div>

      <ErrorBox error={error} />
      {loading && <Loading />}

      {!loading && tab === "details" && profile && (
        <DetailsTab profile={profile} onSaved={setProfile} onRequested={load} />
      )}
      {!loading && tab === "requests" && <RequestsTab />}
      {!loading && tab === "security" && <SecurityTab />}
    </div>
  );
}

// ==========================================================================
// Personal details
// ==========================================================================

function DetailsTab({ profile, onSaved, onRequested }) {
  const [draft, setDraft] = useState(() =>
    Object.fromEntries(profile.editable.map((f) => [f.field, f.value]))
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [asking, setAsking] = useState(null);

  const dirty = profile.editable.some((f) => draft[f.field] !== f.value);

  const save = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.patch("/api/me/profile/update/", draft);
      onSaved(updated);
      setDraft(Object.fromEntries(updated.editable.map((f) => [f.field, f.value])));
      setMessage("Saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid k2">
      <div className="card">
        <div className="card-title">Yours to change</div>
        <div className="card-sub">
          These apply immediately. They affect how you are contacted, and
          nothing else.
        </div>

        {message && <div className="alert ok">{message}</div>}
        <ErrorBox error={error} />

        {profile.editable.map((f) => (
          <Field key={f.field} label={f.label}>
            {f.field === "address" ? (
              <textarea
                rows={3}
                value={draft[f.field] || ""}
                onChange={(e) => setDraft({ ...draft, [f.field]: e.target.value })}
              />
            ) : (
              <input
                value={draft[f.field] || ""}
                onChange={(e) => setDraft({ ...draft, [f.field]: e.target.value })}
              />
            )}
          </Field>
        ))}

        <button className="primary" onClick={save} disabled={!dirty || saving}>
          {saving ? <span className="spinner" /> : null}
          Save changes
        </button>
      </div>

      <div className="stack">
        <div className="card">
          <div className="card-title">Needs HR approval</div>
          <div className="card-sub">
            These change your identity or where you are paid, so somebody in HR
            has to confirm them. Nobody — including HR — can approve a change to
            their own record.
          </div>

          <div className="table-wrap">
            <table>
              <tbody>
                {profile.needs_approval.map((f) => {
                  const pending = profile.pending?.[f.field];
                  return (
                    <tr key={f.field}>
                      <td style={{ width: "40%" }}>
                        <div className="tiny faint">{f.label}</div>
                        <div className="mono">{f.value || "—"}</div>
                      </td>
                      <td>
                        {pending ? (
                          <>
                            <span className="badge amber">Awaiting approval</span>
                            <div className="tiny mono mt" style={{ marginTop: 4 }}>
                              &rarr; {pending}
                            </div>
                          </>
                        ) : (
                          <span className="tiny faint">No pending change</span>
                        )}
                      </td>
                      <td className="right" style={{ width: 90 }}>
                        <button className="sm" onClick={() => setAsking(f)}>
                          Request
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Set by HR</div>
          <div className="card-sub">
            Your position in the organisation. Changing any of it is an HR
            action on your record, not a request from you.
          </div>
          <dl className="kv">
            {profile.read_only.map((f) => (
              <FragmentRow key={f.field} label={f.label} value={f.value} />
            ))}
          </dl>
        </div>
      </div>

      {asking && (
        <RequestModal
          field={asking}
          current={asking.value}
          onClose={() => setAsking(null)}
          onDone={() => {
            setAsking(null);
            onRequested();
          }}
        />
      )}
    </div>
  );
}

function FragmentRow({ label, value }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </>
  );
}

function RequestModal({ field, current, onClose, onDone }) {
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/me/profile/request/", {
        field: field.field,
        new_value: value,
        reason,
      });
      onDone();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div
      className="backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal" style={{ maxWidth: 520 }}>
        <div className="modal-head">
          <h2>Request a change to {field.label.toLowerCase()}</h2>
          <button className="ghost sm" onClick={onClose}>
            &#10005;
          </button>
        </div>
        <div className="modal-body">
          <ErrorBox error={error} />
          <Field label="Current value">
            <input value={current || "—"} disabled />
          </Field>
          <Field label={`New ${field.label.toLowerCase()}`}>
            <input
              autoFocus
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </Field>
          <Field
            label="Why"
            hint="HR sees this when deciding. A bank change without a reason will usually be queried."
          >
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </Field>
        </div>
        <div className="modal-foot">
          <button onClick={onClose}>Cancel</button>
          <button className="primary" disabled={!value.trim() || busy} onClick={submit}>
            Send to HR
          </button>
        </div>
      </div>
    </div>
  );
}

// ==========================================================================
// Change requests
// ==========================================================================

function RequestsTab() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const canApprove = auth.has("profile.approve");

  const load = async () => {
    try {
      setData(await api.get("/api/profile-change-requests/", { ordering: "-created_at" }));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const decide = async (row, action) => {
    try {
      await api.post(`/api/profile-change-requests/${row.id}/${action}/`, {});
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const list = data?.results || [];

  return (
    <div className="card">
      <div className="card-title">
        {canApprove ? "Change requests" : "My change requests"}
      </div>
      <div className="card-sub">
        {canApprove
          ? "Everything waiting on HR, and everything already decided. A request marked sensitive changes where money goes — check the person, not just the form."
          : "What you have asked HR to change, and what they decided."}
      </div>
      <ErrorBox error={error} />

      {!list.length ? (
        <div className="empty">Nothing here yet.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Raised</th>
                {canApprove && <th>Employee</th>}
                <th>Field</th>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
                <th>Status</th>
                {canApprove && <th />}
              </tr>
            </thead>
            <tbody>
              {list.map((row) => (
                <tr key={row.id} className={row.is_sensitive ? "flagged" : ""}>
                  <td className="tiny nowrap">{formatDate(row.created_at)}</td>
                  {canApprove && <td>{row.employee_name}</td>}
                  <td>
                    {row.field_label}
                    {row.is_sensitive && (
                      <span className="badge red" style={{ marginLeft: 6 }}>
                        Sensitive
                      </span>
                    )}
                  </td>
                  <td className="mono tiny">{row.old_value || "—"}</td>
                  <td className="mono tiny">{row.new_value}</td>
                  <td className="tiny muted">{row.reason || "—"}</td>
                  <td>
                    <span
                      className={`badge ${
                        { PENDING: "amber", APPROVED: "green", REFUSED: "red" }[
                          row.state
                        ] || "grey"
                      }`}
                    >
                      {row.state}
                    </span>
                    {row.reviewed_by_name && (
                      <div className="tiny faint">
                        by {row.reviewed_by_name}
                      </div>
                    )}
                  </td>
                  {canApprove && (
                    <td className="right nowrap">
                      {row.state === "PENDING" && (
                        <>
                          <button className="sm" onClick={() => decide(row, "approve")}>
                            Approve
                          </button>{" "}
                          <button
                            className="sm danger"
                            onClick={() => decide(row, "refuse")}
                          >
                            Refuse
                          </button>
                        </>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Password and sessions
// ==========================================================================

function SecurityTab() {
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sessions, setSessions] = useState([]);

  const loadSessions = () =>
    api
      .get("/api/me/sessions/")
      .then(setSessions)
      .catch(() => setSessions([]));

  useEffect(() => {
    loadSessions();
  }, []);

  const submit = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.post("/api/me/password/", form);
      // The server rotates the token deliberately — changing a password ends
      // every other session, and this one would otherwise be among them.
      if (result.token) auth.set(result.token, auth.user);
      setForm({ current_password: "", new_password: "", confirm_password: "" });
      setMessage(result.detail);
      loadSessions();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const ready =
    form.current_password && form.new_password && form.confirm_password;

  return (
    <div className="grid k2">
      <div className="card">
        <div className="card-title">Change your password</div>
        <div className="card-sub">
          Your current password is required even though you are signed in — an
          unlocked laptop should not become a permanent account takeover.
          Changing it signs out every other session.
        </div>

        {message && <div className="alert ok">{message}</div>}
        <ErrorBox error={error} />

        <Field label="Current password">
          <input
            type="password"
            autoComplete="current-password"
            value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })}
          />
        </Field>
        <Field label="New password" hint="At least eight characters, and not a common one.">
          <input
            type="password"
            autoComplete="new-password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          />
        </Field>
        <Field label="Confirm new password">
          <input
            type="password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
          />
        </Field>

        <button className="primary" disabled={!ready || busy} onClick={submit}>
          {busy && <span className="spinner" />} Change password
        </button>
      </div>

      <div className="card">
        <div className="card-title">Where you are signed in</div>
        <div className="card-sub">
          Sessions expire on their own — after inactivity, and again at their
          absolute lifetime. If you see an address you do not recognise, change
          your password: that ends all of them.
        </div>

        {!sessions.length ? (
          <div className="empty">No other sessions.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Address</th>
                  <th>Started</th>
                  <th>Last used</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <tr key={i}>
                    <td className="mono tiny">
                      {s.ip_address || "unknown"}
                      {s.current && (
                        <span className="badge green" style={{ marginLeft: 6 }}>
                          This one
                        </span>
                      )}
                    </td>
                    <td className="tiny">{formatDateTime(s.started_at)}</td>
                    <td className="tiny">{formatDateTime(s.last_used)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
