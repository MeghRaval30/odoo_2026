// User management (T-045). Admin only.
//
// User accounts are separate from employee records but linked to one. The
// server refuses an attempt to change your own roles, so that error surfaces
// here rather than being pre-empted client-side.

import { useEffect, useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  rows,
  useResource,
} from "../components/ui";

function UserForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState({
    email: "",
    employee: "",
    role_ids: [],
    is_active: true,
    password: "",
  });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
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
      .then((u) =>
        setForm({
          email: u.email,
          employee: u.employee || "",
          role_ids: (u.roles || []).map((r) => r.id),
          is_active: u.is_active,
          password: "",
        }),
      )
      .catch((err) => setError(err.message));
  }, [id]);

  const toggleRole = (roleId) =>
    setForm((f) => ({
      ...f,
      role_ids: f.role_ids.includes(roleId)
        ? f.role_ids.filter((r) => r !== roleId)
        : [...f.role_ids, roleId],
    }));

  const save = async () => {
    setBusy(true);
    setError(null);
    const payload = { ...form, employee: form.employee || null };
    if (!payload.password) delete payload.password;
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
      <Field label="Work email">
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
      <Field label="Roles">
        <div className="row">
          {refs.roles?.map((r) => (
            <label key={r.id} className="row" style={{ gap: 5, marginBottom: 0 }}>
              <input
                type="checkbox"
                checked={form.role_ids.includes(r.id)}
                onChange={() => toggleRole(r.id)}
              />
              <span>{r.name}</span>
            </label>
          ))}
        </div>
      </Field>
      <Field label={id ? "Reset password" : "Password"}>
        <input
          type="password"
          value={form.password}
          placeholder={id ? "Leave blank to keep" : "demo1234"}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
        />
      </Field>
    </Modal>
  );
}

export default function Users() {
  const [editing, setEditing] = useState(undefined);
  const users = useResource("/api/users/");

  if (!auth.can("is_admin")) {
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
      <PageHead title="User Management" sub={`${users.rows.length} accounts`}>
        <button className="primary" onClick={() => setEditing(null)}>
          New User
        </button>
      </PageHead>

      <ErrorBox error={users.error} />

      <div className="card">
        {users.loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Employee</th>
                  <th>Roles</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.rows.map((u) => (
                  <tr key={u.id} className="clickable" onClick={() => setEditing(u.id)}>
                    <td>{u.email}</td>
                    <td className="muted">{u.employee_name || "—"}</td>
                    <td>
                      {(u.roles || []).map((r) => (
                        <span key={r.id} className="badge blue" style={{ marginRight: 4 }}>
                          {r.name}
                        </span>
                      ))}
                    </td>
                    <td>
                      <StateBadge
                        state={u.is_active ? "RUNNING" : "EXPIRED"}
                        label={u.is_active ? "Active" : "Inactive"}
                      />
                    </td>
                  </tr>
                ))}
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
