// Employees: kanban + list, sharing one form (T-033).
//
// The spec requires both views to open the same record form, so the view toggle
// only swaps the presentation -- selection and editing are identical.
// Smart-button counts come from server-side annotations, never from counting
// rows on the client.

import { useEffect, useState } from "react";
import { api, formatDate } from "../api";
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
import { navigate } from "../lib/router";

const TYPE_TONE = {
  FULL_TIME: "green",
  PART_TIME: "blue",
  INTERN: "purple",
  CONTRACTOR: "amber",
};

const BLANK = {
  first_name: "",
  last_name: "",
  work_email: "",
  work_phone: "",
  employee_type: "FULL_TIME",
  date_of_joining: new Date().toISOString().slice(0, 10),
  department: "",
  job_position: "",
  manager: "",
  work_location: "",
  working_schedule: "",
  bank_account_number: "",
  bank_ifsc: "",
  pan_number: "",
  active: true,
};

function EmployeeForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refs, setRefs] = useState({});
  const [tab, setTab] = useState("work");

  useEffect(() => {
    Promise.all([
      api.get("/api/departments/"),
      api.get("/api/job-positions/"),
      api.get("/api/work-locations/"),
      api.get("/api/working-schedules/"),
      api.get("/api/employees/", { page_size: 200 }),
      api.get("/api/companies/"),
    ])
      .then(([d, j, w, s, e, c]) =>
        setRefs({
          departments: rows(d),
          positions: rows(j),
          locations: rows(w),
          schedules: rows(s),
          employees: rows(e),
          companies: rows(c),
        }),
      )
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/employees/${id}/`)
      .then((emp) => {
        setDetail(emp);
        setForm({
          ...BLANK,
          ...Object.fromEntries(
            Object.entries(emp).map(([k, v]) => [k, v === null ? "" : v]),
          ),
        });
      })
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
    const payload = { ...form };
    // Blank FK strings must go back as null, not "".
    for (const key of [
      "department", "job_position", "manager", "work_location",
      "working_schedule", "date_of_birth",
    ]) {
      if (payload[key] === "") payload[key] = null;
    }
    payload.company = payload.company || refs.companies?.[0]?.id;
    delete payload.initials;
    delete payload.full_name;
    delete payload.has_bank_details;
    try {
      if (id) await api.patch(`/api/employees/${id}/`, payload);
      else await api.post("/api/employees/", payload);
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
      wide
      title={id ? detail?.full_name || "Employee" : "New Employee"}
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

      {id && detail && (
        <div className="smart-row">
          <button className="smart" onClick={() => navigate(`/contracts?employee=${id}`)}>
            <span className="n">{detail.contract_count ?? 0}</span>
            <span className="l">Contracts</span>
          </button>
          <button className="smart" onClick={() => navigate(`/attendance?employee=${id}`)}>
            <span className="n">{detail.attendance_count ?? 0}</span>
            <span className="l">Attendance</span>
          </button>
          <button className="smart" onClick={() => navigate(`/timeoff?employee=${id}`)}>
            <span className="n">{detail.timeoff_count ?? 0}</span>
            <span className="l">Time Off</span>
          </button>
          <button className="smart" onClick={() => navigate(`/allocations?employee=${id}`)}>
            <span className="n">{detail.allocation_count ?? 0}</span>
            <span className="l">Allocations</span>
          </button>
        </div>
      )}

      <div className="tabs">
        {[
          ["work", "Work Information"],
          ["private", "Private Information"],
          ["hr", "HR Settings"],
        ].map(([key, label]) => (
          <div
            key={key}
            className={`tab${tab === key ? " on" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </div>
        ))}
      </div>

      {tab === "work" && (
        <>
          <div className="row fill">
            <Field label="First name">
              <input value={form.first_name} onChange={set("first_name")} />
            </Field>
            <Field label="Last name">
              <input value={form.last_name} onChange={set("last_name")} />
            </Field>
          </div>
          <div className="row fill">
            <Field label="Work email">
              <input type="email" value={form.work_email} onChange={set("work_email")} />
            </Field>
            <Field label="Work phone">
              <input value={form.work_phone} onChange={set("work_phone")} />
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
          <div className="row fill">
            <Field label="Manager">
              <select value={form.manager || ""} onChange={set("manager")}>
                {opts(refs.employees, "full_name")}
              </select>
            </Field>
            <Field label="Work location">
              <select value={form.work_location || ""} onChange={set("work_location")}>
                {opts(refs.locations)}
              </select>
            </Field>
          </div>
        </>
      )}

      {tab === "private" && (
        <>
          <div className="row fill">
            <Field label="Date of birth">
              <input
                type="date"
                value={form.date_of_birth || ""}
                onChange={set("date_of_birth")}
              />
            </Field>
            <Field label="Gender">
              <select value={form.gender || ""} onChange={set("gender")}>
                <option value="">—</option>
                <option value="M">Male</option>
                <option value="F">Female</option>
                <option value="O">Other</option>
              </select>
            </Field>
          </div>
          <div className="row fill">
            <Field label="Personal email">
              <input
                type="email"
                value={form.personal_email || ""}
                onChange={set("personal_email")}
              />
            </Field>
            <Field label="Personal phone">
              <input
                value={form.personal_phone || ""}
                onChange={set("personal_phone")}
              />
            </Field>
          </div>
          <Field label="Address">
            <textarea rows={2} value={form.address || ""} onChange={set("address")} />
          </Field>
          <div className="row fill">
            <Field label="Bank account">
              <input
                value={form.bank_account_number || ""}
                onChange={set("bank_account_number")}
              />
            </Field>
            <Field label="IFSC">
              <input value={form.bank_ifsc || ""} onChange={set("bank_ifsc")} />
            </Field>
          </div>
          <Field label="PAN">
            <input value={form.pan_number || ""} onChange={set("pan_number")} />
          </Field>
        </>
      )}

      {tab === "hr" && (
        <>
          <div className="row fill">
            <Field label="Working schedule">
              <select value={form.working_schedule || ""} onChange={set("working_schedule")}>
                {opts(refs.schedules)}
              </select>
            </Field>
            <Field label="Employee type">
              <select value={form.employee_type} onChange={set("employee_type")}>
                <option value="FULL_TIME">Full Time</option>
                <option value="PART_TIME">Part Time</option>
                <option value="INTERN">Intern</option>
                <option value="CONTRACTOR">Contractor</option>
              </select>
            </Field>
          </div>
          <div className="row fill">
            <Field label="Date of joining">
              <input
                type="date"
                value={form.date_of_joining || ""}
                onChange={set("date_of_joining")}
              />
            </Field>
            <Field label="Employee code">
              <input value={form.employee_code || ""} readOnly />
            </Field>
          </div>
          <Field label="Active">
            <div className="row">
              <input type="checkbox" checked={!!form.active} onChange={set("active")} />
              <span className="tiny muted">Inactive employees are excluded from payruns</span>
            </div>
          </Field>
        </>
      )}
    </Modal>
  );
}

export default function Employees() {
  const [view, setView] = useState("kanban");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [editing, setEditing] = useState(undefined);

  const departments = useResource("/api/departments/");
  const employees = useResource("/api/employees/", {
    search,
    department,
    page_size: 200,
  });

  return (
    <div className="page">
      <PageHead title="Employees" sub={`${employees.rows.length} shown`}>
        <button className="primary" onClick={() => setEditing(null)}>
          New Employee
        </button>
      </PageHead>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={department} onChange={(e) => setDepartment(e.target.value)}>
          <option value="">All departments</option>
          {departments.rows.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <div className="spacer" />
        <button
          className={view === "kanban" ? "primary sm" : "sm"}
          onClick={() => setView("kanban")}
        >
          Kanban
        </button>
        <button
          className={view === "list" ? "primary sm" : "sm"}
          onClick={() => setView("list")}
        >
          List
        </button>
      </div>

      <ErrorBox error={employees.error} />

      {employees.loading ? (
        <Loading />
      ) : employees.rows.length === 0 ? (
        <div className="card">
          <div className="empty">No employees match those filters.</div>
        </div>
      ) : view === "kanban" ? (
        <div className="kanban">
          {employees.rows.map((e) => (
            <div key={e.id} className="kcard" onClick={() => setEditing(e.id)}>
              <div className="avatar">{e.initials}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600 }}>{e.full_name}</div>
                <div className="tiny muted">{e.job_position_name || "—"}</div>
                <div className="tiny faint">{e.department_name || "—"}</div>
                <div className="mt">
                  <span className={`badge ${TYPE_TONE[e.employee_type] || "grey"}`}>
                    {e.employee_type.replace("_", " ")}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Department</th>
                  <th>Position</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {employees.rows.map((e) => (
                  <tr key={e.id} className="clickable" onClick={() => setEditing(e.id)}>
                    <td className="mono tiny">{e.employee_code}</td>
                    <td>{e.full_name}</td>
                    <td className="muted tiny">{e.work_email}</td>
                    <td className="muted">{e.department_name || "—"}</td>
                    <td className="muted">{e.job_position_name || "—"}</td>
                    <td>
                      <span className={`badge ${TYPE_TONE[e.employee_type] || "grey"}`}>
                        {e.employee_type.replace("_", " ")}
                      </span>
                    </td>
                    <td>
                      <StateBadge
                        state={e.active ? "RUNNING" : "EXPIRED"}
                        label={e.active ? "Active" : "Inactive"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {editing !== undefined && (
        <EmployeeForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            employees.reload();
          }}
        />
      )}
    </div>
  );
}
