// Time Off Types (T-038).
//
// requires_allocation is the switch behind graded rule #3 -- a type with it set
// refuses requests that no approved allocation covers.

import { useEffect, useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  useResource,
} from "../components/ui";

const BLANK = {
  name: "",
  code: "",
  unit: "DAYS",
  requires_allocation: false,
  approval: "MANAGER",
  is_paid: true,
  active: true,
  description: "",
};

function TypeForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/timeoff-types/${id}/`)
      .then((t) => setForm({ ...BLANK, ...t }))
      .catch((err) => setError(err.message));
  }, [id]);

  const set = (key) => (e) =>
    setForm((f) => ({
      ...f,
      [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value,
    }));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      if (id) await api.patch(`/api/timeoff-types/${id}/`, form);
      else await api.post("/api/timeoff-types/", form);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={id ? form.name : "New Time Off Type"}
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
      <div className="row fill">
        <Field label="Name">
          <input value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Code">
          <input value={form.code} onChange={set("code")} />
        </Field>
      </div>
      <div className="row fill">
        <Field label="Unit">
          <select value={form.unit} onChange={set("unit")}>
            <option value="DAYS">Days</option>
            <option value="HOURS">Hours</option>
          </select>
        </Field>
        <Field label="Approval">
          <select value={form.approval} onChange={set("approval")}>
            <option value="MANAGER">Manager</option>
            <option value="OFFICER">Officer</option>
            <option value="NONE">None</option>
          </select>
        </Field>
      </div>
      <Field label="Requires allocation">
        <div className="row">
          <input
            type="checkbox"
            checked={form.requires_allocation}
            onChange={set("requires_allocation")}
          />
          <span className="tiny muted">
            Refuse requests without an approved allocation
          </span>
        </div>
      </Field>
      <Field label="Paid">
        <div className="row">
          <input type="checkbox" checked={form.is_paid} onChange={set("is_paid")} />
          <span className="tiny muted">Unpaid types produce Loss of Pay on payroll</span>
        </div>
      </Field>
      <Field label="Description">
        <textarea rows={2} value={form.description || ""} onChange={set("description")} />
      </Field>
    </Modal>
  );
}

export default function TimeOffTypes() {
  const [editing, setEditing] = useState(undefined);
  const types = useResource("/api/timeoff-types/");

  return (
    <div className="page">
      <PageHead title="Time Off Types" sub={`${types.rows.length} records`}>
        {auth.has("timeoff.type.write") && (
          <button className="primary" onClick={() => setEditing(null)}>
            New Type
          </button>
        )}
      </PageHead>

      <ErrorBox error={types.error} />

      <div className="card">
        {types.loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Unit</th>
                  <th>Requires allocation</th>
                  <th>Approval</th>
                  <th>Paid</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {types.rows.map((t) => (
                  <tr key={t.id} className="clickable" onClick={() => setEditing(t.id)}>
                    <td>{t.name}</td>
                    <td className="mono tiny muted">{t.code}</td>
                    <td className="muted">{t.unit_display}</td>
                    <td>
                      <span className={`badge ${t.requires_allocation ? "amber" : "grey"}`}>
                        {t.requires_allocation ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="muted">{t.approval_display}</td>
                    <td className="muted">{t.is_paid ? "Yes" : "No"}</td>
                    <td>
                      <StateBadge
                        state={t.active ? "RUNNING" : "EXPIRED"}
                        label={t.active ? "Active" : "Inactive"}
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
        <TypeForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            types.reload();
          }}
        />
      )}
    </div>
  );
}
