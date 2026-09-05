// The HR Manager's home screen.
//
// Deliberately contains no money. The problem statement gives the HR Manager
// role "no access to payroll features", and total net paid or salary by
// department are payroll features however they are framed — so the endpoint
// behind this screen never computes them, rather than this screen hiding them.
//
// What it leads with instead is the queue: what is waiting on this person's
// decision right now, and what will break if nobody acts. That is the actual
// job, and it is the thing a generic "here are some charts" dashboard buries.

import { api, formatDate } from "../api";
import { ErrorBox, Loading, PageHead, useResource } from "../components/ui";
import { href } from "../lib/router";

export default function HRDashboard() {
  const { data, loading, error, reload } = useResource("/api/dashboard/hr/");

  if (loading) return <Loading />;
  if (error)
    return (
      <div className="page">
        <ErrorBox error={error} />
      </div>
    );
  if (!data) return null;

  const { kpis, awaiting_you: queue, attendance_overview: att } = data;
  const waiting =
    kpis.pending_leave + kpis.pending_allocations + kpis.pending_profile_changes;

  const decide = async (path, id, action) => {
    try {
      await api.post(`${path}${id}/${action}/`, {});
      reload();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="page">
      <PageHead
        title="Workforce"
        sub={`${formatDate(data.filters.period_start)} – ${formatDate(data.filters.period_end)}`}
      />

      <div className="grid k5 mb">
        <div className="card kpi">
          <div className="label">Headcount</div>
          <div className="value">{kpis.headcount}</div>
          <div className="foot">
            {kpis.joined_this_period} joined this period
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Waiting on you</div>
          <div className="value">{waiting}</div>
          <div className="foot">
            {kpis.pending_leave} leave · {kpis.pending_allocations} allocations ·{" "}
            {kpis.pending_profile_changes} details
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Attendance coverage</div>
          <div className="value">{kpis.attendance_coverage}%</div>
          <div className="foot">
            {att.missing_checkouts} missing check-out
            {att.missing_checkouts === 1 ? "" : "s"}
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Average day worked</div>
          <div className="value">{kpis.average_worked_hm}</div>
          <div className="foot">Across every closed session</div>
        </div>
        <div className="card kpi">
          <div className="label">Overtime</div>
          <div className="value">{kpis.total_overtime_hm}</div>
          <div className="foot">
            carried by {kpis.overtime_employees} employee
            {kpis.overtime_employees === 1 ? "" : "s"}
          </div>
        </div>
      </div>

      <div className="grid wide-left">
        <div className="stack">
          <div className="card">
            <div className="card-title">Awaiting your decision</div>
            <div className="card-sub">
              Approve from here, or open the record for the full context.
            </div>

            {!waiting ? (
              <div className="empty">Nothing waiting. Genuinely.</div>
            ) : (
              <div className="stack">
                {queue.leave.length > 0 && (
                  <QueueTable
                    title="Time off requests"
                    link="/timeoff"
                    rows={queue.leave}
                    columns={["Employee", "Type", "Dates", "Duration"]}
                    render={(r) => [
                      r.employee,
                      r.type,
                      `${formatDate(r.date_from)} – ${formatDate(r.date_to)}`,
                      r.duration,
                    ]}
                    onApprove={(r) =>
                      decide("/api/timeoff-requests/", r.id, "approve")
                    }
                    onRefuse={(r) =>
                      decide("/api/timeoff-requests/", r.id, "refuse")
                    }
                  />
                )}

                {queue.allocations.length > 0 && (
                  <QueueTable
                    title="Allocations to approve"
                    link="/allocations"
                    rows={queue.allocations}
                    columns={["Employee", "Type", "Allocated"]}
                    render={(r) => [r.employee, r.type, r.allocated]}
                    onApprove={(r) =>
                      decide("/api/allocations/", r.id, "approve")
                    }
                    onRefuse={(r) => decide("/api/allocations/", r.id, "refuse")}
                  />
                )}

                {queue.profile_changes.length > 0 && (
                  <QueueTable
                    title="Personal detail changes"
                    link="/profile/requests"
                    rows={queue.profile_changes}
                    columns={["Employee", "Field", "New value"]}
                    render={(r) => [
                      r.employee,
                      <>
                        {r.field}
                        {r.sensitive && (
                          <span className="badge red" style={{ marginLeft: 6 }}>
                            Sensitive
                          </span>
                        )}
                      </>,
                      <span className="mono">{r.new_value}</span>,
                    ]}
                    flagged={(r) => r.sensitive}
                    onApprove={(r) =>
                      decide("/api/profile-change-requests/", r.id, "approve")
                    }
                    onRefuse={(r) =>
                      decide("/api/profile-change-requests/", r.id, "refuse")
                    }
                  />
                )}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">Attendance quality</div>
            <div className="card-sub">
              Source: Attendance. Exceptions are what this panel is for — a
              perfect month is a boring one.
            </div>
            <div className="grid k4">
              <Tile label="Present" value={att.present} />
              <Tile label="Absent" value={att.absent} tone={att.absent ? "amber" : ""} />
              <Tile
                label="Missing check-outs"
                value={att.missing_checkouts}
                tone={att.missing_checkouts ? "amber" : ""}
              />
              <Tile
                label="Corrected by hand"
                value={att.manual_edits}
                tone={att.manual_edits ? "amber" : ""}
              />
            </div>
            <div className="mt">
              <div className="between tiny">
                <span className="faint">Coverage — sessions with a check-out</span>
                <span className="mono">{att.coverage_pct}%</span>
              </div>
              <div className="meter mt" style={{ marginTop: 5 }}>
                <i
                  className={
                    att.coverage_pct > 95
                      ? "green"
                      : att.coverage_pct > 85
                      ? "amber"
                      : "red"
                  }
                  style={{ width: `${att.coverage_pct}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-title">Contracts needing attention</div>
            <div className="card-sub">
              A contract that lapses mid-period means somebody is not paid.
            </div>
            {!data.contracts_expiring.length &&
            !data.employees_without_contract.length ? (
              <div className="empty tiny">Nothing expiring in the next 45 days.</div>
            ) : (
              <>
                {data.contracts_expiring.map((c) => (
                  <div className="between tiny" key={c.id} style={{ padding: "5px 0" }}>
                    <span>
                      {c.employee}
                      <span className="faint mono"> · {c.reference}</span>
                    </span>
                    <span
                      className={`badge ${c.days_left < 14 ? "red" : "amber"}`}
                    >
                      {c.days_left}d left
                    </span>
                  </div>
                ))}
                {data.employees_without_contract.map((e) => (
                  <div className="between tiny" key={e.id} style={{ padding: "5px 0" }}>
                    <span>
                      {e.name}
                      <span className="faint"> · {e.department || "—"}</span>
                    </span>
                    <span className="badge red">No contract</span>
                  </div>
                ))}
              </>
            )}
            <a className="tiny" href={href("/contracts")}>
              All contracts &rarr;
            </a>
          </div>

          <div className="card">
            <div className="card-title">Headcount by department</div>
            <BarList rows={data.headcount_by_department} />
          </div>

          <div className="card">
            <div className="card-title">Headcount by employment type</div>
            <BarList rows={data.headcount_by_type} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value, tone }) {
  return (
    <div className="card kpi" style={{ padding: "11px 13px" }}>
      <div className="label">{label}</div>
      <div className="value" style={{ fontSize: 20 }}>
        {value}
      </div>
      {tone && <div className={`foot ${tone === "amber" ? "down" : ""}`}>needs review</div>}
    </div>
  );
}

function BarList({ rows }) {
  const max = Math.max(1, ...rows.map((r) => r.headcount));
  if (!rows.length) return <div className="empty tiny">No data.</div>;
  return (
    <div className="barlist">
      {rows.map((r) => (
        <div className="barrow" key={r.name || "unassigned"}>
          <span className="nm">{r.name || "Unassigned"}</span>
          <span className="vl">{r.headcount}</span>
          <div className="meter">
            <i style={{ width: `${(r.headcount / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function QueueTable({ title, link, rows, columns, render, onApprove, onRefuse, flagged }) {
  return (
    <div>
      <div className="between mb" style={{ marginBottom: 6 }}>
        <strong className="tiny">{title}</strong>
        <a className="tiny" href={href(link)}>
          Open list &rarr;
        </a>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className={flagged?.(r) ? "flagged" : ""}>
                {render(r).map((cell, i) => (
                  <td key={i}>{cell}</td>
                ))}
                <td className="right nowrap">
                  <button className="sm" onClick={() => onApprove(r)}>
                    Approve
                  </button>{" "}
                  <button className="sm danger" onClick={() => onRefuse(r)}>
                    Refuse
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
