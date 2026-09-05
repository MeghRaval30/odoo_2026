// Payslip list, delegating to the detail view when the route carries an id.

import { useState } from "react";
import { formatDate, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge, useResource } from "../components/ui";
import { href, navigate } from "../lib/router";
import PayslipDetail from "./PayslipDetail";

export default function Payslips({ route }) {
  const id = route.parts[1];
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [state, setState] = useState("");
  const departments = useResource("/api/departments/");
  const payslips = useResource("/api/payslips/", {
    search,
    state,
    employee__department: department,
    page_size: 200,
  });

  if (id) return <PayslipDetail id={id} />;

  return (
    <div className="page">
      <PageHead title="Payslips" sub={`${payslips.rows.length} records`} />

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search number or employee…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div>
          <select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All departments</option>
            {departments.rows.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <select value={state} onChange={(e) => setState(e.target.value)}>
            <option value="">All states</option>
            <option value="DRAFT">Draft</option>
            <option value="VERIFY">Computed</option>
            <option value="DONE">Validated</option>
            <option value="PAID">Paid</option>
          </select>
        </div>
      </div>

      <ErrorBox error={payslips.error} />

      <div className="card">
        {payslips.loading ? (
          <Loading />
        ) : payslips.rows.length === 0 ? (
          <div className="empty">No payslips.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Period</th>
                  <th className="num">Worked days</th>
                  <th className="num">Gross</th>
                  <th className="num">Net</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {payslips.rows.map((s) => (
                  <tr
                    key={s.id}
                    className="clickable"
                    onClick={() => navigate(`/payslips/${s.id}`)}
                  >
                    <td className="mono tiny">
                      <a href={href(`/payslips/${s.id}`)}>{s.number}</a>
                    </td>
                    <td>{s.employee_name}</td>
                    <td className="muted">{s.department_name || "—"}</td>
                    <td className="muted tiny">
                      {formatDate(s.period_start)} – {formatDate(s.period_end)}
                    </td>
                    <td className="num mono">{s.worked_days}</td>
                    <td className="num mono">{money(s.gross)}</td>
                    <td className="num mono">{money(s.net)}</td>
                    <td>
                      <StateBadge state={s.state} />
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
