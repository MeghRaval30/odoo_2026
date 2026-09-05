// User management (T-045, brought onto the capability matrix in T-104).
//
// The mockup's User Management screen: columns User · Employee · Work Email ·
// Role · Status, with a search box and a role filter. Accounts are created by
// an administrator, linked to an employee, and assigned **exactly one** role —
// so these are radios, not checkboxes, and the server rejects a second role
// rather than trusting the form to prevent it.
//
// Two things are deliberately not pre-empted client-side. Changing your own
// roles and deactivating yourself are refused by the server, and the refusal
// is shown verbatim: a screen that quietly hides the control teaches nobody
// what the rule is, and the rule is the interesting part.

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  rows,
  useDebounced,
  useResource,
} from "../components/ui";

// `resource.action.scope` — the first segment is the thing being governed, and
// it is the only sane way to read thirty-odd rows at once.
const GROUP_LABELS = {
  profile: "Profile",
  password: "Password",
  attendance: "Attendance",
  timeoff: "Time off",
  allocation: "Allocations",
  payslip: "Payslips",
  employee: "Employees",
  contract: "Contracts",
  schedule: "Working schedules",
  reference: "Reference data",
  payrun: "Payruns",
  salaryconfig: "Salary structures and rules",
  dashboard: "Dashboards",
  user: "User accounts",
  security: "Security",
  audit: "Audit log",
};

function groupOf(capability) {
  const head = capability.split(".")[0];
  return GROUP_LABELS[head] || head;
}

// ---------------------------------------------------------------- the form

function UserForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState({
    email: "",
    employee: "",
    role_ids: [],
    is_active: true,
    password: "",
  });
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [refs, setRefs] = useState({});

  useEffect(() => {
    Promise.all([
      api.get("/api/roles/"),
      api.get("/api/employees/", { page_size: 200 }),
    ])
      .then(([r, e]) => setRefs({ roles: rows(r), employees: rows(e) }))
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/users/${id}/`)
      .then((u) => {
        setRecord(u);
        setForm({
          email: u.email,
          employee: u.employee || "",
          role_ids: (u.roles || []).map((r) => r.id),
          is_active: u.is_active,
          password: "",
        });
      })
      .catch((err) => setError(err.message));
  }, [id]);

  // One role per account: picking a role replaces the selection rather than
  // adding to it. An account with no role at all is still reachable -- leave
  // this untouched when creating one -- but there is no un-pick, because a
  // radio that clears itself on a second click surprises everybody.
  const chooseRole = (roleId) =>
    setForm((f) => ({ ...f, role_ids: [roleId] }));

  const save = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    const payload = { ...form, employee: form.employee || null };
    // On an existing account the password is set through Reset password, which
    // also ends their sessions. Sending a blank here would be a silent no-op.
    delete payload.password;
    if (!id && form.password) payload.password = form.password;
    try {
      if (id) await api.patch(`/api/users/${id}/`, payload);
      else await api.post("/api/users/", payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.post(`/api/users/${id}/reset-password/`, {
        password: newPassword,
      });
      setNotice(result.detail);
      setNewPassword("");
      setResetting(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const isSelf = record && auth.user && record.id === auth.user.id;

  return (
    <Modal
      title={id ? form.email : "New User"}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={save} disabled={busy}>
            {busy ? <span className="spinner" /> : "Save"}
          </button>
        </>
      }
    >
      <ErrorBox error={error} />
      {notice && <div className="alert ok">{notice}</div>}

      <Field label="Sign-in email">
        <input
          type="email"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
        />
      </Field>

      <Field label="Employee">
        <select
          value={form.employee}
          onChange={(e) => setForm((f) => ({ ...f, employee: e.target.value }))}
        >
          <option value="">—</option>
          {refs.employees?.map((e) => (
            <option key={e.id} value={e.id}>
              {e.full_name}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Role">
        <div className="check-list">
          {refs.roles?.map((r) => (
            <label key={r.id} className="check">
              <input
                type="radio"
                name="user-role"
                checked={form.role_ids.includes(r.id)}
                onChange={() => chooseRole(r.id)}
              />
              <span>{r.name}</span>
            </label>
          ))}
        </div>
        {isSelf && (
          <div className="hint">Your own roles cannot be changed from here.</div>
        )}
      </Field>

      <Field label="Status">
        <label className="check">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
          />
          <span>Active — may sign in</span>
        </label>
      </Field>

      {!id && (
        <Field label="Password">
          <input
            type="password"
            value={form.password}
            placeholder="demo1234"
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
        </Field>
      )}

      {id && (
        <Field label="Password">
          {resetting ? (
            <>
              <input
                type="password"
                value={newPassword}
                placeholder="Temporary password"
                onChange={(e) => setNewPassword(e.target.value)}
              />
              <div className="row mt" style={{ gap: 6 }}>
                <button className="sm primary" onClick={resetPassword} disabled={busy}>
                  Reset and end their sessions
                </button>
                <button className="sm" onClick={() => setResetting(false)}>
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <button className="sm" onClick={() => setResetting(true)}>
              Reset password
            </button>
          )}
        </Field>
      )}
    </Modal>
  );
}

// ----------------------------------------------------------- the grid panel

function CapabilityMatrix() {
  const [matrix, setMatrix] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/api/users/capability-matrix/")
      .then(setMatrix)
      .catch((err) => setError(err.message));
  }, []);

  const grouped = useMemo(() => {
    if (!matrix) return [];
    const byGroup = new Map();
    for (const capability of matrix.all) {
      const group = groupOf(capability);
      if (!byGroup.has(group)) byGroup.set(group, []);
      byGroup.get(group).push(capability);
    }
    return [...byGroup.entries()];
  }, [matrix]);

  if (error) return <ErrorBox error={error} />;
  if (!matrix) return <Loading />;

  const baseline = new Set(matrix.baseline);
  const held = (role, capability) =>
    baseline.has(capability) || role.capabilities.includes(capability);

  return (
    <div className="card">
      <div className="card-title">What each role grants</div>
      <div className="card-sub">
        Served from the table the API enforces with, so this grid cannot drift
        from what the server does. An account holding several roles gets the
        union.
      </div>
      <div className="table-wrap">
        <table className="matrix">
          <thead>
            <tr>
              <th>Capability</th>
              {matrix.roles.map((r) => (
                <th key={r.code} className="num">
                  {r.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grouped.map(([group, capabilities]) => (
              <Fragment key={group}>
                <tr className="group-row">
                  <td colSpan={matrix.roles.length + 1}>{group}</td>
                </tr>
                {capabilities.map((capability) => (
                  <tr key={capability}>
                    <td className="mono tiny">{capability}</td>
                    {matrix.roles.map((r) => (
                      <td key={r.code} className="num">
                        {held(r, capability) ? (
                          <span className="tick">✓</span>
                        ) : (
                          <span className="faint">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <div className="tiny faint mt">
        {matrix.baseline.length} of these are baseline — every signed-in account
        holds them, because they only ever reach that person's own record.
      </div>
    </div>
  );
}

// --------------------------------------------------------------- the screen

export default function Users() {
  const [editing, setEditing] = useState(undefined);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [showMatrix, setShowMatrix] = useState(false);
  const users = useResource("/api/users/");
  const roles = useResource("/api/roles/");
  const query = useDebounced(search, 250);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return users.rows.filter((u) => {
      if (role && !(u.roles || []).some((r) => String(r.id) === role)) return false;
      if (!needle) return true;
      return [u.email, u.employee_name, u.employee_work_email, u.employee_code]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(needle));
    });
  }, [users.rows, query, role]);

  if (!auth.has("user.manage")) {
    return (
      <div className="page">
        <div className="card">
          <div className="empty">Administrator access required.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHead
        title="User Management"
        sub={`${visible.length} of ${users.rows.length} accounts`}
      >
        <button onClick={() => setShowMatrix((v) => !v)}>
          {showMatrix ? "Hide capabilities" : "Capabilities"}
        </button>
        <button className="primary" onClick={() => setEditing(null)}>
          New User
        </button>
      </PageHead>

      <ErrorBox error={users.error} />

      <div className="toolbar">
        <input
          placeholder="Search accounts"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 260 }}
        />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">All roles</option>
          {roles.rows.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      {showMatrix && <CapabilityMatrix />}

      <div className="card">
        {users.loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Employee</th>
                  <th>Work Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((u) => (
                  <tr key={u.id} className="clickable" onClick={() => setEditing(u.id)}>
                    <td>{u.email}</td>
                    <td className="muted">
                      {u.employee_name || "—"}
                      {u.employee_code && (
                        <span className="tiny faint"> · {u.employee_code}</span>
                      )}
                    </td>
                    <td className="muted">{u.employee_work_email || "—"}</td>
                    <td>
                      {(u.roles || []).length ? (
                        (u.roles || []).map((r) => (
                          <span
                            key={r.id}
                            className="badge blue"
                            style={{ marginRight: 4 }}
                          >
                            {r.name}
                          </span>
                        ))
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                    <td>
                      <StateBadge
                        state={u.is_active ? "RUNNING" : "EXPIRED"}
                        label={u.is_active ? "Active" : "Inactive"}
                      />
                    </td>
                  </tr>
                ))}
                {!visible.length && (
                  <tr>
                    <td colSpan={5} className="empty">
                      No account matches
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== undefined && (
        <UserForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            users.reload();
          }}
        />
      )}
    </div>
  );
}
