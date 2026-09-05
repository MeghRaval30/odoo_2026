// Attendance list and correction form (T-036).
//
// worked_hours and overtime_hours are derived from check-in/check-out on the
// server, so they are shown but never edited. The screen reads the `_hm` pair
// the serializer sends alongside them — decimal for payroll, hours and minutes
// for people (D-032). Saving a correction makes the
// viewset stamp is_manually_edited and record who did it, which is why the
// Source column exists.

import { useEffect, useState } from "react";
import { api, formatDateTime } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  rows,
  useDebounced,
  useResource,
} from "../components/ui";

const STATUS_TONE = {
  PRESENT: "green",
  OVERTIME: "blue",
  HALF_DAY: "amber",
  ABSENT: "red",
};

// <input type="datetime-local"> wants local wall time with no zone suffix.
const toLocalInput = (value) => {
  if (!value) return "";
  const d = new Date(value);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
};

function AttendanceForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get("/api/employees/", { page_size: 200 })
      .then((e) => setEmployees(rows(e)))
      .catch(() => setEmployees([]));
  }, []);

  useEffect(() => {
    if (!id) {
      setForm({
        employee: "",
        check_in: toLocalInput(new Date()),
        check_out: "",
        status: "PRESENT",
        notes: "",
      });
      return;
    }
    api
      .get(`/api/attendance/${id}/`)
      .then((a) =>
        setForm({
          employee: a.employee,
          check_in: toLocalInput(a.check_in),
          check_out: toLocalInput(a.check_out),
          status: a.status,
          notes: a.notes || "",
          worked_hm: a.worked_hm,
          overtime_hm: a.overtime_hm,
          is_manually_edited: a.is_manually_edited,
        }),
      )
      .catch((err) => setError(err.message));
  }, [id]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    setBusy(true);
    setError(null);
    const payload = {
      employee: form.employee,
      check_in: form.check_in,
      check_out: form.check_out || null,
      status: form.status,
      notes: form.notes,
    };
    try {
      if (id) await api.patch(`/api/attendance/${id}/`, payload);
      else await api.post("/api/attendance/", payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!form) return null;

  return (
    <Modal
      title={id ? "Attendance Record" : "New Attendance Record"}
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

      {id && (
        <div className="smart-row">
          <div className="smart">
            <span className="n">{form.worked_hm || "—"}</span>
            <span className="l">Worked</span>
          </div>
          <div className="smart">
            <span className="n">{form.overtime_hm || "—"}</span>
            <span className="l">Overtime</span>
          </div>
          <div className="smart">
            <span className="n">{form.is_manually_edited ? "Manual" : "System"}</span>
            <span className="l">Source</span>
          </div>
        </div>
      )}

      <Field label="Employee">
        <select value={form.employee || ""} onChange={set("employee")}>
          <option value="">—</option>
          {employees.map((e) => (
            <option key={e.id} value={e.id}>
              {e.full_name}
            </option>
          ))}
        </select>
      </Field>

      <div className="row fill">
        <Field label="Check in">
          <input
            type="datetime-local"
            value={form.check_in}
            onChange={set("check_in")}
          />
        </Field>
        <Field label="Check out">
          <input
            type="datetime-local"
            value={form.check_out}
            onChange={set("check_out")}
          />
        </Field>
      </div>

      <Field label="Status">
        <select value={form.status} onChange={set("status")}>
          <option value="PRESENT">Present</option>
          <option value="OVERTIME">Overtime</option>
          <option value="HALF_DAY">Half Day</option>
          <option value="ABSENT">Absent</option>
        </select>
      </Field>

      <Field label="Notes">
        <textarea rows={2} value={form.notes} onChange={set("notes")} />
      </Field>
    </Modal>
  );
}

export default function Attendance({ route }) {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search);
  const [editing, setEditing] = useState(undefined);
  const employeeFilter = route?.query?.employee || "";

  const records = useResource("/api/attendance/", {
    status,
    search: debouncedSearch,
    employee: employeeFilter,
    ordering: "-check_in",
    page_size: 100,
  });

  return (
    <div className="page">
      <PageHead title="Attendance" sub={`${records.rows.length} records`}>
        <button className="primary" onClick={() => setEditing(null)}>
          New Record
        </button>
      </PageHead>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search employee…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="PRESENT">Present</option>
            <option value="OVERTIME">Overtime</option>
            <option value="HALF_DAY">Half Day</option>
            <option value="ABSENT">Absent</option>
          </select>
        </div>
      </div>

      <ErrorBox error={records.error} />

      <div className="card">
        {records.loading ? (
          <Loading />
        ) : records.rows.length === 0 ? (
          <div className="empty">No attendance records.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Check in</th>
                  <th>Check out</th>
                  <th className="num">Worked</th>
                  <th className="num">Overtime</th>
                  <th>Status</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {records.rows.map((a) => (
                  <tr
                    key={a.id}
                    className="clickable"
                    onClick={() => setEditing(a.id)}
                  >
                    <td>{a.employee_name}</td>
                    <td className="muted">{a.department_name || "—"}</td>
                    <td className="muted tiny">{formatDateTime(a.check_in)}</td>
                    <td className="muted tiny">
                      {a.check_out ? (
                        formatDateTime(a.check_out)
                      ) : (
                        <span className="badge amber">Open</span>
                      )}
                    </td>
                    <td className="num mono">{a.worked_hm || "—"}</td>
                    <td className="num mono">{a.overtime_hm || "—"}</td>
                    <td>
                      <span className={`badge ${STATUS_TONE[a.status] || "grey"}`}>
                        {a.status_display}
                      </span>
                    </td>
                    <td className="tiny muted">
                      {a.is_manually_edited ? "Manual" : "System"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== undefined && (
        <AttendanceForm
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
