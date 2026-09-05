// Security administration — Admin only.
//
// Two things live here: the network allowlist ("you may only sign in from the
// office Wi-Fi") and the knobs around sessions and lockout. Both are the sort
// of setting that is easy to get catastrophically wrong, so the screen leads
// with the administrator's own address and the server refuses to switch
// enforcement on from an address no policy covers.

import { useEffect, useState } from "react";
import { api, formatDateTime } from "../api";
import { ErrorBox, Field, Loading, Modal, PageHead, rows } from "../components/ui";

export default function Security() {
  const [settings, setSettings] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [s, p, r] = await Promise.all([
        api.get("/api/security/settings/"),
        api.get("/api/security/networks/"),
        api.get("/api/roles/"),
      ]);
      setSettings(s);
      setPolicies(rows(p));
      setRoles(rows(r));
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

  const patch = async (body) => {
    setError(null);
    setMessage(null);
    try {
      setSettings(await api.patch("/api/security/settings/", body));
      setMessage("Saved.");
    } catch (err) {
      setError(err.message);
      // Re-read, so a refused toggle does not leave the switch looking flipped.
      load();
    }
  };

  const removePolicy = async (row) => {
    if (!confirm(`Remove the network policy "${row.name}" (${row.cidr})?`)) return;
    try {
      await api.delete(`/api/security/networks/${row.id}/`);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="page">
      <PageHead
        title="Security"
        sub="Who may sign in, from where, and for how long"
      >
        <button className="primary" onClick={() => setEditing({})}>
          + Network policy
        </button>
      </PageHead>

      <ErrorBox error={error} />
      {message && <div className="alert ok">{message}</div>}

      <div className="alert info">
        You are connected from <strong className="mono">{settings?.your_ip_address || "an unknown address"}</strong>.
        Turning on network enforcement while no active policy covers this address
        would lock you out, so the server will refuse to do it.
      </div>

      <div className="grid wide-left">
        <div className="card">
          <div className="card-title">Permitted networks</div>
          <div className="card-sub">
            Each row is a CIDR range. A policy scoped to a role only constrains
            holders of that role — the usual shape is to pin payroll staff to the
            office, because they can move money, and leave everyone else alone.
            With no active policy at all, sign-in is unrestricted.
          </div>

          {!policies.length ? (
            <div className="empty">
              No policies. Sign-in is currently unrestricted.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Range</th>
                    <th>Applies to</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {policies.map((row) => (
                    <tr key={row.id}>
                      <td>
                        {row.name}
                        {row.description && (
                          <div className="tiny faint">{row.description}</div>
                        )}
                      </td>
                      <td className="mono">{row.cidr}</td>
                      <td>{row.role_name || "All accounts"}</td>
                      <td>
                        <span className={`badge ${row.is_active ? "green" : "grey"}`}>
                          {row.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="right nowrap">
                        <button className="sm" onClick={() => setEditing(row)}>
                          Edit
                        </button>{" "}
                        <button className="sm danger" onClick={() => removePolicy(row)}>
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-title">Enforcement</div>
            <Toggle
              label="Restrict sign-in to permitted networks"
              hint="Checked on every request, not only at sign-in — otherwise you could authenticate at the office and use the session from anywhere."
              value={settings?.enforce_network_policy}
              onChange={(v) => patch({ enforce_network_policy: v })}
            />
            <Toggle
              label="Restrict attendance check-in to permitted networks"
              hint="Separate switch, because a clock you can punch from your sofa is not attendance."
              value={settings?.enforce_network_on_punch}
              onChange={(v) => patch({ enforce_network_on_punch: v })}
            />
            <Toggle
              label="Bind each session to the address it was opened from"
              hint="Turns a stolen session token into a dead one unless the thief is on the same network. Inconvenient on flaky mobile connections."
              value={settings?.bind_session_to_ip}
              onChange={(v) => patch({ bind_session_to_ip: v })}
            />
          </div>

          <div className="card">
            <div className="card-title">Sessions and lockout</div>
            <NumberSetting
              label="Failed attempts before lockout"
              value={settings?.max_failed_logins}
              onSave={(v) => patch({ max_failed_logins: v })}
            />
            <NumberSetting
              label="Lockout duration (minutes)"
              value={settings?.lockout_minutes}
              onSave={(v) => patch({ lockout_minutes: v })}
            />
            <NumberSetting
              label="Sign out after inactivity (minutes)"
              value={settings?.session_idle_minutes}
              onSave={(v) => patch({ session_idle_minutes: v })}
            />
            <NumberSetting
              label="Absolute session lifetime (hours)"
              value={settings?.session_max_hours}
              onSave={(v) => patch({ session_max_hours: v })}
            />
            <NumberSetting
              label="Minimum password length"
              value={settings?.password_min_length}
              onSave={(v) => patch({ password_min_length: v })}
            />
          </div>
        </div>
      </div>

      {editing && (
        <PolicyModal
          row={editing}
          roles={roles}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function Toggle({ label, hint, value, onChange }) {
  return (
    <div className="field">
      <label
        style={{
          display: "flex",
          gap: 9,
          alignItems: "flex-start",
          textTransform: "none",
          letterSpacing: 0,
          fontSize: 13,
          color: "var(--text)",
          cursor: "pointer",
        }}
      >
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          style={{ marginTop: 3 }}
        />
        <span>
          {label}
          <span className="tiny faint" style={{ display: "block", fontWeight: 400 }}>
            {hint}
          </span>
        </span>
      </label>
    </div>
  );
}

function NumberSetting({ label, value, onSave }) {
  const [draft, setDraft] = useState(value ?? "");
  useEffect(() => setDraft(value ?? ""), [value]);
  const changed = String(draft) !== String(value ?? "");

  return (
    <Field label={label}>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <input
          type="number"
          min="0"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          className="sm"
          disabled={!changed}
          onClick={() => onSave(Number(draft))}
        >
          Save
        </button>
      </div>
    </Field>
  );
}

function PolicyModal({ row, roles, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: row.name || "",
    cidr: row.cidr || "",
    role: row.role || "",
    description: row.description || "",
    is_active: row.is_active ?? true,
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    setError(null);
    const body = { ...form, role: form.role || null };
    try {
      if (row.id) await api.patch(`/api/security/networks/${row.id}/`, body);
      else await api.post("/api/security/networks/", body);
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal
      title={row.id ? "Edit network policy" : "New network policy"}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>Cancel</button>
          <button
            className="primary"
            disabled={!form.name.trim() || !form.cidr.trim() || busy}
            onClick={save}
          >
            Save policy
          </button>
        </>
      }
    >
      <ErrorBox error={error} />
      <Field label="Name" hint="What people call this network. Shown in the refusal message.">
        <input
          autoFocus
          placeholder="Head office Wi-Fi"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
      </Field>
      <Field
        label="Address range (CIDR)"
        hint="A whole network like 192.168.1.0/24, or one address as 203.0.113.7/32."
      >
        <input
          placeholder="192.168.1.0/24"
          value={form.cidr}
          onChange={(e) => setForm({ ...form, cidr: e.target.value })}
        />
      </Field>
      <Field
        label="Applies to"
        hint="Leave as every account unless you mean to restrict one role only."
      >
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
        >
          <option value="">Every account</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Note">
        <input
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </Field>
      <Toggle
        label="Active"
        hint="Inactive policies are ignored entirely, including when deciding whether any policy applies."
        value={form.is_active}
        onChange={(v) => setForm({ ...form, is_active: v })}
      />
    </Modal>
  );
}

// ==========================================================================
// Audit log
// ==========================================================================

const ACTION_TONE = {
  SIGN_IN: "green",
  SIGN_IN_FAILED: "red",
  SIGN_OUT: "grey",
  PASSWORD_CHANGED: "amber",
  ROLES_CHANGED: "purple",
  USER_CREATED: "blue",
  USER_DEACTIVATED: "red",
  PROFILE_EDITED: "grey",
  PROFILE_CHANGE_REQUESTED: "amber",
  PROFILE_CHANGE_DECIDED: "blue",
  ATTENDANCE_PUNCH: "grey",
  ATTENDANCE_CORRECTED: "amber",
  TIMEOFF_DECIDED: "blue",
  PAYRUN_STATE: "purple",
  SECURITY_CHANGED: "red",
};

export function AuditLog() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .get("/api/audit/", { search, action, ordering: "-created_at" })
        .then(setData)
        .catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [search, action]);

  const list = rows(data);

  return (
    <div className="page">
      <PageHead
        title="Audit log"
        sub="Append-only. Every action that touches money, access or identity."
      />

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search summary, email or address…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={action} onChange={(e) => setAction(e.target.value)}>
          <option value="">All actions</option>
          {Object.keys(ACTION_TONE).map((a) => (
            <option key={a} value={a}>
              {a.replace(/_/g, " ").toLowerCase()}
            </option>
          ))}
        </select>
        <span className="tiny faint">{data?.count ?? list.length} entries</span>
      </div>

      <ErrorBox error={error} />

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>Who</th>
                <th>What happened</th>
                <th>From</th>
              </tr>
            </thead>
            <tbody>
              {!list.length && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">Nothing recorded yet.</div>
                  </td>
                </tr>
              )}
              {list.map((row) => (
                <tr key={row.id}>
                  <td className="tiny nowrap">{formatDateTime(row.created_at)}</td>
                  <td>
                    <span className={`badge ${ACTION_TONE[row.action] || "grey"}`}>
                      {row.action_display}
                    </span>
                  </td>
                  <td className="tiny">{row.actor_email || "—"}</td>
                  <td>{row.summary}</td>
                  <td className="mono tiny">{row.ip_address || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
