// The employee's home screen.
//
// The user's brief was specific: an employee login lands on the employee
// dashboard, and attendance and the rest live behind their own tabs. So this
// answers the four questions somebody has about their own working month —
// am I clocked in, how much have I worked, what leave do I have left, and what
// was I paid — and links out for the detail rather than duplicating it.
//
// Every figure is this person's own. The endpoint scopes by employee in the
// query itself, so there is no request shape that returns somebody else's.

import { api, formatDate, formatTime, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge } from "../components/ui";
import { href } from "../lib/router";
import { useResource } from "../components/ui";

export default function MyDashboard() {
  const { data, loading, error } = useResource("/api/dashboard/me/");

  if (loading) return <Loading />;
  if (error)
    return (
      <div className="page">
        <ErrorBox error={error} />
      </div>
    );
  if (!data) return null;

  const { employee, attendance, leave, contract, payslips } = data;
  const latest = payslips?.[0];

  return (
    <div className="page">
      <PageHead
        title={`Good to see you, ${employee.name.split(" ")[0]}`}
        sub={[employee.job_title, employee.department].filter(Boolean).join(" · ")}
      />

      {!employee.has_bank_details && (
        <div className="alert warn">
          <strong>No bank account on file.</strong> Payroll will flag this before
          your next payslip is finalised. Raise the change from{" "}
          <a href={href("/profile")}>your profile</a> — bank details need HR
          approval, so do it well before the run.
        </div>
      )}

      {data.pending_profile_changes > 0 && (
        <div className="alert info">
          {data.pending_profile_changes} change{data.pending_profile_changes === 1 ? "" : "s"} to your
          details {data.pending_profile_changes === 1 ? "is" : "are"} waiting on
          HR. <a href={href("/profile/requests")}>See what</a>.
        </div>
      )}

      <div className="grid k4 mb">
        <div className="card kpi">
          <div className="label">Right now</div>
          <div className="value" style={{ fontSize: 20 }}>
            {attendance.checked_in ? "Checked in" : "Checked out"}
          </div>
          <div className="foot">
            {attendance.checked_in
              ? `Since ${formatTime(attendance.open_since)}`
              : "Use the clock in the top bar"}
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Worked this month</div>
          <div className="value">{attendance.worked_this_month_hm}</div>
          <div className="foot">
            {attendance.days_recorded} day{attendance.days_recorded === 1 ? "" : "s"} recorded
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Overtime this month</div>
          <div className="value">{attendance.overtime_this_month_hm}</div>
          <div className="foot">
            {attendance.missing_checkouts
              ? `${attendance.missing_checkouts} missing check-out`
              : "Every session closed"}
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Last net pay</div>
          <div className="value">{latest ? money(latest.net) : "—"}</div>
          <div className="foot">
            {latest ? latest.payrun || formatDate(latest.period_end) : "No payslip yet"}
          </div>
        </div>
      </div>

      <div className="grid wide-left">
        <div className="stack">
          <div className="card">
            <div className="between">
              <div className="card-title" style={{ marginBottom: 0 }}>
                Recent attendance
              </div>
              <a className="tiny" href={href("/attendance")}>
                All my records &rarr;
              </a>
            </div>
            {!attendance.recent.length ? (
              <div className="empty">Nothing recorded this month yet.</div>
            ) : (
              <div className="table-wrap mt">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>In</th>
                      <th>Out</th>
                      <th className="num">Worked</th>
                      <th className="num">Overtime</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendance.recent.map((row) => (
                      <tr key={row.id}>
                        <td className="nowrap">{formatDate(row.date)}</td>
                        <td className="mono">{formatTime(row.check_in)}</td>
                        <td className="mono">
                          {row.check_out ? (
                            formatTime(row.check_out)
                          ) : (
                            <span className="badge amber">Open</span>
                          )}
                        </td>
                        <td className="num">{row.worked_hm}</td>
                        <td className="num">{row.overtime_hm}</td>
                        <td>{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <div className="between">
              <div className="card-title" style={{ marginBottom: 0 }}>
                My payslips
              </div>
              <a className="tiny" href={href("/my-payslips")}>
                All payslips &rarr;
              </a>
            </div>
            {!payslips.length ? (
              <div className="empty">No payslips yet.</div>
            ) : (
              <div className="table-wrap mt">
                <table>
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Number</th>
                      <th className="num">Gross</th>
                      <th className="num">Net</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payslips.map((p) => (
                      <tr
                        key={p.id}
                        className="clickable"
                        onClick={() => (window.location.hash = `#/payslips/${p.id}`)}
                      >
                        <td className="nowrap">
                          {formatDate(p.period_start)} – {formatDate(p.period_end)}
                        </td>
                        <td className="mono tiny">{p.number}</td>
                        <td className="num">{money(p.gross)}</td>
                        <td className="num">{money(p.net)}</td>
                        <td>
                          <StateBadge state={p.state} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="between">
              <div className="card-title" style={{ marginBottom: 0 }}>
                Leave balance
              </div>
              <a className="tiny" href={href("/timeoff")}>
                Request &rarr;
              </a>
            </div>
            {!leave.balances.length ? (
              <div className="empty tiny">
                No approved allocation. Leave types that require one cannot be
                requested until HR allocates a balance.
              </div>
            ) : (
              <div className="barlist mt">
                {leave.balances.map((b) => {
                  const used = Number(b.allocated)
                    ? (Number(b.taken) / Number(b.allocated)) * 100
                    : 0;
                  return (
                    <div className="barrow" key={b.type}>
                      <span className="nm">{b.type}</span>
                      <span className="vl">
                        {b.remaining} left of {b.allocated}
                      </span>
                      <div className="meter">
                        <i
                          className={used > 85 ? "red" : used > 60 ? "amber" : "green"}
                          style={{ width: `${Math.min(100, used)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {leave.pending > 0 && (
              <div className="alert warn mt" style={{ marginBottom: 0 }}>
                {leave.pending} request{leave.pending === 1 ? "" : "s"} awaiting approval.
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">My contract</div>
            {!contract.reference ? (
              <div className="empty tiny">
                No contract covers today. Payroll cannot pay a period without
                one — speak to HR.
              </div>
            ) : (
              <dl className="kv">
                <dt>Reference</dt>
                <dd className="mono">{contract.reference}</dd>
                <dt>Position</dt>
                <dd>{contract.job_position || "—"}</dd>
                <dt>Period</dt>
                <dd>
                  {formatDate(contract.start_date)} –{" "}
                  {contract.end_date ? formatDate(contract.end_date) : "open"}
                </dd>
                <dt>Wage</dt>
                <dd className="mono">{money(contract.wage)} / month</dd>
              </dl>
            )}
          </div>

          <div className="card">
            <div className="card-title">Working pattern</div>
            <dl className="kv">
              <dt>Schedule</dt>
              <dd>{employee.schedule || "—"}</dd>
              <dt>Expected weekly</dt>
              <dd className="mono">{employee.expected_weekly_hm}</dd>
              <dt>Manager</dt>
              <dd>{employee.manager || "—"}</dd>
              <dt>Employee code</dt>
              <dd className="mono">{employee.code}</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
