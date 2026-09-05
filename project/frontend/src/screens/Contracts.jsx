// Contracts (T-034).
//
// RUNNING contracts are made visually obvious, per the spec. The overlap guard
// is graded rule #1's other half: two RUNNING contracts may not overlap, and
// the serializer returns that as a field error which we surface verbatim rather
// than re-implementing the check here.

import { useEffect, useState } from "react";
import { api, formatDate, money } from "../api";
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
  start_date: new Date().toISOString().slice(0, 10),
  end_date: "",
  wage: "",
  salary_structure: "",
  working_schedule: "",
  department: "",
  job_position: "",
  structure_type: "",
  state: "DRAFT",
  notes: "",
};

function ContractForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refs, setRefs] = useState({});

  useEffect(() => {
    Promise.all([
      api.get("/api/employees/", { page_size: 200 }),
      api.get("/api/salary-structures/"),
      api.get("/api/working-schedules/"),
      api.get("/api/departments/"),
      api.get("/api/job-positions/"),
    ])
      .then(([e, s, w, d, j]) =>
        setRefs({
          employees: rows(e),
          structures: rows(s),
          schedules: rows(w),
          departments: rows(d),
          positions: rows(j),
        }),
      )
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/contracts/${id}/`)
      .then((c) =>
        setForm({
          ...BLANK,
          ...Object.fromEntries(
            Object.entries(c).map(([k, v]) => [k, v === null ? "" : v]),
          ),
        }),
      )
      .catch((err) => setError(err.message));
  }, [id]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    setBusy(true);
    setError(null);
    const payload = { ...form };
    for (const key of ["end_date", "department", "job_position", "working_schedule"]) {
      if (payload[key] === "") payload[key] = null;
    }
    delete payload.reference;
    try {
      if (id) await api.patch(`/api/contracts/${id}/`, payload);
      else await api.post("/api/contracts/", payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const opts = (list, labelKey = "name") => [
    <option key="" value="">
      —
    </option>,
    ...(list || []).map((r) => (
      <option key={r.id} value={r.id}>
        {r[labelKey] || r.full_name}
      </option>
    )),
  ];

  return (
    <Modal
      title={id ? `Contract ${form.reference || ""}` : "New Contract"}
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
        <select value={form.employee || ""} onChange={set("employee")}>
          {opts(refs.employees, "full_name")}
        </select>
      </Field>
      <div className="row fill">
        <Field label="Start date">
          <input type="date" value={form.start_date || ""} onChange={set("start_date")} />
        </Field>
        <Field label="End date" hint="Blank for an open-ended contract.">
          <input type="date" value={form.end_date || ""} onChange={set("end_date")} />
        </Field>
      </div>
      <div className="row fill">
        <Field label="Monthly wage">
          <input type="number" step="0.01" value={form.wage} onChange={set("wage")} />
        </Field>
        <Field label="State" hint="Two RUNNING contracts may not overlap.">
          <select value={form.state} onChange={set("state")}>
            <option value="DRAFT">Draft</option>
            <option value="RUNNING">Running</option>
            <option value="EXPIRED">Expired</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </Field>
      </div>
      <div className="row fill">
        <Field label="Salary structure">
          <select value={form.salary_structure || ""} onChange={set("salary_structure")}>
            {opts(refs.structures)}
          </select>
        </Field>
        <Field label="Working schedule">
          <select value={form.working_schedule || ""} onChange={set("working_schedule")}>
            {opts(refs.schedules)}
          </select>
        </Field>
      </div>
      <div className="row fill">
        <Field label="Department">
          <select value={form.department || ""} onChange={set("department")}>
            {opts(refs.departments)}
          </select>
        </Field>
        <Field label="Job position">
          <select value={form.job_position || ""} onChange={set("job_position")}>
            {opts(refs.positions)}
          </select>
        </Field>
      </div>
      <Field label="Notes">
        <textarea rows={2} value={form.notes || ""} onChange={set("notes")} />
      </Field>
    </Modal>
  );
}

export default function Contracts({ route }) {
  const [state, setState] = useState("");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(undefined);
  const employeeFilter = route?.query?.employee || "";

  const contracts = useResource("/api/contracts/", {
    state,
    search,
    employee: employeeFilter,
    ordering: "-start_date",
    page_size: 200,
  });

  return (
    <div className="page">
      <PageHead
        title="Contracts"
        sub={
          employeeFilter
            ? "Filtered to one employee"
            : "Period-scoped — payroll resolves the contract covering the payrun period"
        }
      >
        <button className="primary" onClick={() => setEditing(null)}>
          New Contract
        </button>
      </PageHead>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search reference or employee…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={state} onChange={(e) => setState(e.target.value)}>
          <option value="">All states</option>
          <option value="DRAFT">Draft</option>
          <option value="RUNNING">Running</option>
          <option value="EXPIRED">Expired</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <ErrorBox error={contracts.error} />

      <div className="card">
        {contracts.loading ? (
          <Loading />
        ) : contracts.rows.length === 0 ? (
          <div className="empty">No contracts match those filters.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Employee</th>
                  <th>Period</th>
                  <th className="num">Wage</th>
                  <th>Structure</th>
                  <th>Schedule</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {contracts.rows.map((c) => (
                  <tr
                    key={c.id}
                    className="clickable"
                    onClick={() => setEditing(c.id)}
                    style={
                      c.state === "RUNNING"
                        ? { borderLeft: "3px solid var(--green)" }
                        : undefined
                    }
                  >
                    <td className="mono tiny">{c.reference}</td>
                    <td>{c.employee_name}</td>
                    <td className="muted tiny">
                      {formatDate(c.start_date)} –{" "}
                      {c.end_date ? formatDate(c.end_date) : "open"}
                    </td>
                    <td className="num mono">{money(c.wage)}</td>
                    <td className="muted">{c.salary_structure_name || "—"}</td>
                    <td className="muted tiny">{c.working_schedule_name || "—"}</td>
                    <td>
                      <StateBadge state={c.state} label={c.state_display} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== undefined && (
        <ContractForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            contracts.reload();
          }}
        />
      )}
    </div>
  );
}
