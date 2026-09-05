// Departments, job positions and work locations.
//
// Three near-identical reference lists, so they share one component
// parameterised by endpoint and field list rather than being copied three
// times.

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
  useDefaultCompany,
  useResource,
} from "../components/ui";

function ReferenceForm({ title, path, fields, id, onClose, onSaved }) {
  const [form, setForm] = useState(() =>
    Object.fromEntries(fields.map((f) => [f.key, f.type === "check" ? true : ""])),
  );
  const [refs, setRefs] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const defaultCompany = useDefaultCompany();

  useEffect(() => {
    const needed = fields.filter((f) => f.type === "fk");
    if (!needed.length) return;
    Promise.all(needed.map((f) => api.get(f.source, { page_size: 200 })))
      .then((results) =>
        setRefs(
          Object.fromEntries(needed.map((f, i) => [f.key, rows(results[i])])),
        ),
      )
      .catch(() => setRefs({}));
  }, [fields]);

  useEffect(() => {
    if (!id) return;
    api
      .get(`${path}${id}/`)
      .then((r) =>
        setForm(
          Object.fromEntries(
            fields.map((f) => [f.key, r[f.key] === null ? "" : r[f.key]]),
          ),
        ),
      )
      .catch((err) => setError(err.message));
  }, [id, path, fields]);

  const save = async () => {
    setBusy(true);
    setError(null);
    const payload = { ...form, company: form.company || defaultCompany };
    for (const f of fields) {
      if (f.type === "fk" && payload[f.key] === "") payload[f.key] = null;
    }
    try {
      if (id) await api.patch(`${path}${id}/`, payload);
      else await api.post(path, payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={id ? title : `New ${title}`}
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
      {fields.map((f) => (
        <Field key={f.key} label={f.label}>
          {f.type === "fk" ? (
            <select
              value={form[f.key] || ""}
              onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))}
            >
              <option value="">&#8212;</option>
              {(refs[f.key] || []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name || r.full_name}
                </option>
              ))}
            </select>
          ) : f.type === "check" ? (
            <input
              type="checkbox"
              checked={!!form[f.key]}
              onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.checked }))}
            />
          ) : (
            <input
              value={form[f.key] || ""}
              onChange={(e) => setForm((s) => ({ ...s, [f.key]: e.target.value }))}
            />
          )}
        </Field>
      ))}
    </Modal>
  );
}

function ReferenceList({ title, singular, path, columns, fields }) {
  const [editing, setEditing] = useState(undefined);
  const records = useResource(path, { page_size: 200 });

  return (
    <div className="page">
      <PageHead title={title} sub={`${records.rows.length} records`}>
        {auth.has("reference.write") && (
          <button className="primary" onClick={() => setEditing(null)}>
            New {singular}
          </button>
        )}
      </PageHead>
      <ErrorBox error={records.error} />
      <div className="card">
        {records.loading ? (
          <Loading />
        ) : records.rows.length === 0 ? (
          <div className="empty">No records.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c.key} className={c.num ? "num" : undefined}>
                      {c.label}
                    </th>
                  ))}
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {records.rows.map((r) => (
                  <tr
                    key={r.id}
                    className="clickable"
                    onClick={() => setEditing(r.id)}
                  >
                    {columns.map((c) => (
                      <td
                        key={c.key}
                        className={c.num ? "num mono" : c.muted ? "muted" : undefined}
                      >
                        {r[c.key] ?? "—"}
                      </td>
                    ))}
                    <td>
                      <StateBadge
                        state={r.active ? "RUNNING" : "EXPIRED"}
                        label={r.active ? "Active" : "Inactive"}
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
        <ReferenceForm
          title={singular}
          path={path}
          fields={fields}
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            records.reload();
          }}
        />
      )}
    </div>
  );
}

const DEPARTMENT_FIELDS = [
  { key: "name", label: "Name" },
  { key: "manager", label: "Manager", type: "fk", source: "/api/employees/" },
  { key: "active", label: "Active", type: "check" },
];

const POSITION_FIELDS = [
  { key: "name", label: "Name" },
  { key: "department", label: "Department", type: "fk", source: "/api/departments/" },
  { key: "active", label: "Active", type: "check" },
];

const LOCATION_FIELDS = [
  { key: "name", label: "Name" },
  { key: "active", label: "Active", type: "check" },
];

export const Departments = () => (
  <ReferenceList
    title="Departments"
    singular="Department"
    path="/api/departments/"
    fields={DEPARTMENT_FIELDS}
    columns={[
      { key: "name", label: "Department" },
      { key: "manager_name", label: "Manager", muted: true },
      { key: "employee_count", label: "Headcount", num: true },
    ]}
  />
);

export const JobPositions = () => (
  <ReferenceList
    title="Job Positions"
    singular="Job Position"
    path="/api/job-positions/"
    fields={POSITION_FIELDS}
    columns={[{ key: "name", label: "Position" }]}
  />
);

export const WorkLocations = () => (
  <ReferenceList
    title="Work Locations"
    singular="Work Location"
    path="/api/work-locations/"
    fields={LOCATION_FIELDS}
    columns={[{ key: "name", label: "Location" }]}
  />
);
