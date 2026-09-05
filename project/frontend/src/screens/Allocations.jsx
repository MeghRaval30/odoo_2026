// Allocations (T-038).
//
// Allocated / Taken / Remaining are server-side properties over approved
// requests, so cancelling a request restores balance without any write here.
// Only an APPROVED allocation creates balance, which is why approve/refuse sit
// on the row.

import { useEffect, useState } from "react";
import { api, auth, formatDate } from "../api";
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

const BLANK = {
  employee: "",
  time_off_type: "",
  name: "",
  allocated: "",
  valid_from: `${new Date().getFullYear()}-01-01`,
  valid_to: `${new Date().getFullYear()}-12-31`,
  state: "TO_APPROVE",
  description: "",
};

function AllocationForm({ onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refs, setRefs] = useState({});

  useEffect(() => {
    Promise.all([
      api.get("/api/employees/", { page_size: 200 }),
      api.get("/api/timeoff-types/"),
    ])
      .then(([e, t]) => setRefs({ employees: rows(e), types: rows(t) }))
      .catch((err) => setError(err.message));
  }, []);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/allocations/", form);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="New Allocation"
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

      <Field label="Employee">
        <select value={form.employee} onChange={set("employee")}>
          <option value="">—</option>
          {refs.employees?.map((e) => (
            <option key={e.id} value={e.id}>
              {e.full_name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Time off type">
        <select value={form.time_off_type} onChange={set("time_off_type")}>
          <option value="">—</option>
          {refs.types?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Name">
        <input value={form.name} onChange={set("name")} placeholder="2026 Annual Balance" />
      </Field>
      <div className="row fill">
        <Field label="Allocated">
          <input type="number" step="0.5" value={form.allocated} onChange={set("allocated")} />
        </Field>
        <Field label="Status">
          <select value={form.state} onChange={set("state")}>
            <option value="TO_APPROVE">To Approve</option>
            <option value="APPROVED">Approved</option>
          </select>
        </Field>
      </div>
      <div className="row fill">
        <Field label="Valid from">
          <input type="date" value={form.valid_from} onChange={set("valid_from")} />
        </Field>
        <Field label="Valid to">
          <input type="date" value={form.valid_to} onChange={set("valid_to")} />
        </Field>
      </div>
    </Modal>
  );
}

export default function Allocations({ route }) {
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);
  const employeeFilter = route?.query?.employee || "";

  const allocations = useResource("/api/allocations/", {
    employee: employeeFilter,
    page_size: 200,
  });

  const canDecide = auth.has("allocation.write");

  const act = async (id, verb) => {
    setBusy(id);
    setError(null);
    try {
      await api.post(`/api/allocations/${id}/${verb}/`, {});
      await allocations.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="page">
      <PageHead title="Allocations" sub={`${allocations.rows.length} records`}>
        {canDecide && (
          <button className="primary" onClick={() => setCreating(true)}>
            New Allocation
          </button>
        )}
      </PageHead>

      <ErrorBox error={error || allocations.error} />

      <div className="card">
        {allocations.loading ? (
          <Loading />
        ) : allocations.rows.length === 0 ? (
          <div className="empty">No allocations.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Type</th>
                  <th>Name</th>
                  <th className="num">Allocated</th>
                  <th className="num">Taken</th>
                  <th className="num">Remaining</th>
                  <th>Validity</th>
                  <th>Status</th>
                  <th className="right">Action</th>
                </tr>
              </thead>
              <tbody>
                {allocations.rows.map((a) => (
                  <tr key={a.id}>
                    <td>{a.employee_name}</td>
                    <td className="muted">{a.type_name}</td>
                    <td className="muted tiny">{a.name}</td>
                    <td className="num mono">{a.allocated}</td>
                    <td className="num mono">{a.taken}</td>
                    <td className="num mono">
                      <strong>{a.remaining}</strong>
                    </td>
                    <td className="muted tiny">
                      {formatDate(a.valid_from)} – {formatDate(a.valid_to)}
                    </td>
                    <td>
                      <StateBadge state={a.state} label={a.state_display} />
                    </td>
                    <td className="right">
                      {a.state !== "APPROVED" && canDecide ? (
                        <div className="row" style={{ justifyContent: "flex-end", gap: 6 }}>
                          <button
                            className="sm"
                            disabled={busy === a.id}
                            onClick={() => act(a.id, "approve")}
                          >
                            Approve
                          </button>
                          <button
                            className="sm danger"
                            disabled={busy === a.id}
                            onClick={() => act(a.id, "refuse")}
                          >
                            Refuse
                          </button>
                        </div>
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {creating && (
        <AllocationForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            allocations.reload();
          }}
        />
      )}
    </div>
  );
}
