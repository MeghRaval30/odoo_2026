// Attendance list (T-036).
//
// worked_hours and overtime_hours are derived from check-in/check-out on the
// server. A row edited by hand is flagged is_manually_edited by the viewset,
// which is surfaced here rather than hidden.

import { useState } from "react";
import { formatDateTime } from "../api";
import { ErrorBox, Loading, PageHead, useResource } from "../components/ui";

const STATUS_TONE = {
  PRESENT: "green",
  OVERTIME: "blue",
  HALF_DAY: "amber",
  ABSENT: "red",
};

export default function Attendance({ route }) {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const employeeFilter = route?.query?.employee || "";

  const records = useResource("/api/attendance/", {
    status,
    search,
    employee: employeeFilter,
    ordering: "-check_in",
    page_size: 100,
  });

  return (
    <div className="page">
      <PageHead title="Attendance" sub={`${records.rows.length} records`} />

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
                  <tr key={a.id}>
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
                    <td className="num mono">{a.worked_hours}</td>
                    <td className="num mono">{a.overtime_hours}</td>
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
    </div>
  );
}
