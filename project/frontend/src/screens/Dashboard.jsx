// Payroll Dashboard (T-044).
//
// Every number here is aggregated live from six models by /api/dashboard/.
// The problem statement warns specifically against hardcoded dashboards, so the
// filters matter more than the charts do: changing Period or Department has to
// visibly re-drive every card on the screen. That is the closing move of the
// demo, so the filter bar is the first thing on the page, not the last.

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, compactMoney, money } from "../api";
import { useChartPalette } from "../lib/theme";

// Recharts needs concrete colour strings rather than CSS custom properties for
// its own interpolation, so the palette is read back out of the document by
// `useChartPalette()` — see lib/theme.js. It used to be a hand copy of Ledger's
// tokens here, which was wrong the moment there was more than one theme.

// Keys must match Payrun.STATES in payroll/models.py.
const stateColor = (C) => ({
  PAID: C.green,
  VALIDATED: C.accent,
  COMPUTED: C.amber,
  DRAFT: C.dim,
});

const STATE_BADGE = {
  PAID: "green",
  VALIDATED: "blue",
  COMPUTED: "amber",
  DRAFT: "grey",
};

const tooltipStyleFor = (C) => ({
  background: C.surface,
  border: `1px solid ${C.grid}`,
  borderRadius: C.radius,
  fontSize: 12,
  color: C.text,
  fontFamily: C.sans,
  boxShadow: C.shadow,
});

function Kpi({ label, value, foot, tone }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      <div className={`foot${tone ? ` ${tone}` : ""}`}>{foot}</div>
    </div>
  );
}

export default function Dashboard() {
  const C = useChartPalette();
  const tooltipStyle = tooltipStyleFor(C);
  const STATE_COLOR = stateColor(C);
  const [options, setOptions] = useState(null);
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({
    period: "",
    department: "",
    employee_type: "",
    company: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/api/dashboard/filters/")
      .then((opts) => {
        setOptions(opts);
        // Open on the period the server nominates, not on `periods[0]`. They
        // differ the moment an unfinished run exists — an off-cycle correction
        // is the newest period and the worst possible thing to open on, because
        // it holds one payslip and every KPI reads as a collapse.
        const fallback = opts.periods?.length ? opts.periods[0].id : null;
        const chosen = opts.default_period ?? fallback;
        if (chosen != null) {
          setFilters((f) => ({ ...f, period: String(chosen) }));
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  const load = useCallback(async () => {
    if (!options) return;
    setLoading(true);
    setError(null);
    try {
      const period = options.periods?.find(
        (p) => String(p.id) === String(filters.period),
      );
      setData(
        await api.get("/api/dashboard/", {
          period_start: period?.period_start,
          period_end: period?.period_end,
          department: filters.department,
          employee_type: filters.employee_type,
          company: filters.company,
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [options, filters]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (key) => (event) =>
    setFilters((f) => ({ ...f, [key]: event.target.value }));

  const k = data?.kpis;
  const delta = k?.net_delta_pct;

  return (
    <div className="page">
      <div className="page-head">
        <h1>Payroll Dashboard</h1>
        {data && (
          <span className="sub">
            {data.filters.period_start} to {data.filters.period_end}
          </span>
        )}
        <div className="spacer" />
        {loading && <span className="spinner" />}
      </div>

      <div className="toolbar">
        <div>
          <label htmlFor="f-period">Period</label>
          <select id="f-period" value={filters.period} onChange={set("period")}>
            {options?.periods?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="f-dept">Department</label>
          <select id="f-dept" value={filters.department} onChange={set("department")}>
            <option value="">All departments</option>
            {options?.departments?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="f-type">Employee type</label>
          <select
            id="f-type"
            value={filters.employee_type}
            onChange={set("employee_type")}
          >
            <option value="">All types</option>
            {options?.employee_types?.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="f-company">Company</label>
          <select id="f-company" value={filters.company} onChange={set("company")}>
            <option value="">All companies</option>
            {options?.companies?.map((c) => (
              <option key={c.company__id} value={c.company__id}>
                {c.company__name}
              </option>
            ))}
          </select>
        </div>
        <div className="spacer" />
        <button onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {!data && !error && <div className="empty">Loading dashboard…</div>}

      {data && (
        <>
          <div className="grid k5">
            <Kpi
              label="Total Net Paid"
              value={compactMoney(k.total_net_paid)}
              tone={delta == null ? undefined : delta >= 0 ? "up" : "down"}
              foot={
                delta == null
                  ? "—"
                  : `${delta >= 0 ? "+" : "−"}${Math.abs(delta).toFixed(1)}% vs previous period`
              }
            />
            <Kpi
              label="Payslips"
              value={k.payslips_generated}
              foot={`${k.payslips_paid} paid · ${k.payslips_pending} pending`}
            />
            <Kpi
              label="Avg Net / Employee"
              value={compactMoney(k.avg_salary_per_employee)}
              foot={`Gross ${compactMoney(k.total_gross)}`}
            />
            <Kpi
              label="Approved Time Off Days"
              value={k.approved_timeoff_days}
              foot={`${k.headcount} active employees`}
            />
            <Kpi
              label="Attendance Health"
              value={`${k.attendance_health}%`}
              tone={k.attendance_health >= 90 ? "up" : "down"}
              foot={`${data.attendance_overview.missing_checkouts} missing check-outs`}
            />
          </div>

          <div className="grid k2 mt">
            <div className="card">
              <div className="card-title">Net Payroll Trend</div>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={data.salary_trend}>
                  <CartesianGrid stroke={C.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="period" stroke={C.dim} fontSize={11} />
                  <YAxis
                    stroke={C.dim}
                    fontSize={11}
                    tickFormatter={(v) => compactMoney(v)}
                    width={70}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v) => money(v)}
                  />
                  <Line
                    type="monotone"
                    dataKey="net"
                    stroke={C.accent}
                    strokeWidth={2}
                    dot={{ r: 3, fill: C.accent }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-title">Net Pay by Department</div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={data.salary_by_department}>
                  <CartesianGrid stroke={C.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke={C.dim} fontSize={11} />
                  <YAxis
                    stroke={C.dim}
                    fontSize={11}
                    tickFormatter={(v) => compactMoney(v)}
                    width={70}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: "rgba(217,119,87,0.08)" }}
                    formatter={(v) => money(v)}
                  />
                  <Bar dataKey="total" fill={C.accent} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid k3 mt">
            <div className="card">
              <div className="card-title">Payslip Status</div>
              {data.payslip_status.length ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={data.payslip_status}
                      dataKey="count"
                      nameKey="state"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={2}
                    >
                      {data.payslip_status.map((entry) => (
                        <Cell
                          key={entry.state}
                          fill={STATE_COLOR[entry.state] || C.dim}
                        />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty">No payslips in this period</div>
              )}
              <div className="row" style={{ gap: 6 }}>
                {data.payslip_status.map((s) => (
                  <span
                    key={s.state}
                    className={`badge ${STATE_BADGE[s.state] || "grey"}`}
                  >
                    {s.state} {s.count}
                  </span>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-title">Pre-Validation Alerts</div>
              {data.alerts.length ? (
                <>
                  <div className="row mb" style={{ gap: 6 }}>
                    {data.alerts.map((a) => (
                      <span
                        key={a.code}
                        className={`badge ${a.severity === "ERROR" ? "red" : "amber"}`}
                      >
                        {a.code} · {a.count}
                      </span>
                    ))}
                  </div>
                  <ul className="tiny muted" style={{ paddingLeft: 16, margin: 0 }}>
                    {data.alert_messages.map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <div className="empty">No warnings raised</div>
              )}
            </div>

            <div className="card">
              <div className="card-title">Attendance Overview</div>
              {/*
                Overtime is the one figure here that a count cannot carry. Ten
                records of six minutes and one record of nine hours are the same
                count and a different payroll problem, so it reads as a duration
                and the number of people it landed on. Present, half day and
                absent stay as counts: those are days, and a day is the unit.
              */}
              <div className="attendance-headline">
                <div>
                  <div className="tiny faint">Overtime</div>
                  <div className="attendance-headline-value">
                    {data.attendance_overview.total_overtime_hm}
                  </div>
                  <div className="tiny faint">
                    carried by {data.attendance_overview.overtime_employees} employee
                    {data.attendance_overview.overtime_employees === 1 ? "" : "s"}
                  </div>
                </div>
                <div>
                  <div className="tiny faint">Average day worked</div>
                  <div className="attendance-headline-value">
                    {data.attendance_overview.average_worked_hm}
                  </div>
                  <div className="tiny faint">Across every closed session</div>
                </div>
              </div>
              <table>
                <tbody>
                  {[
                    ["Present", data.attendance_overview.present],
                    ["Half day", data.attendance_overview.half_day],
                    ["Absent", data.attendance_overview.absent],
                    ["Days with overtime", data.attendance_overview.overtime],
                    ["Missing check-outs", data.attendance_overview.missing_checkouts],
                    ["Manual edits", data.attendance_overview.manual_edits],
                  ].map(([label, value]) => (
                    <tr key={label}>
                      <td className="muted">{label}</td>
                      <td className="num mono">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid k2 mt">
            <div className="card">
              <div className="card-title">Department Overview</div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Department</th>
                      <th className="num">Headcount</th>
                      <th className="num">Net This Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.department_overview.map((d) => (
                      <tr key={d.id}>
                        <td>{d.name}</td>
                        <td className="num mono">{d.headcount}</td>
                        <td className="num mono">{money(d.monthly_salary)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Time Off Overview</div>
              {data.timeoff_overview.length ? (
                <div className="table-wrap">
                  {/*
                    Approved and Pending are scoped to the selected period;
                    Remaining is the live balance across every open allocation.
                    Spelling that out stops the row reading as arithmetic —
                    440 allocated less 8 approved in February is not 428.
                  */}
                  <table>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th className="num">Approved Days</th>
                        <th className="num">Pending</th>
                        <th className="num">
                          Remaining
                          <div className="tiny faint" style={{ fontWeight: 400 }}>
                            all periods
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.timeoff_overview.map((t) => (
                        <tr key={t.type_name}>
                          <td>{t.type_name}</td>
                          <td className="num mono">{t.approved_days}</td>
                          <td className="num mono">
                            {t.pending ? (
                              <span className="badge amber">{t.pending}</span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="num mono">
                            {t.remaining_balance == null ? "—" : t.remaining_balance}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty">No time off in this period</div>
              )}
            </div>
          </div>

          <div className="tiny faint mt">
            Sources: {data.sources.join(", ")}
          </div>
        </>
      )}
    </div>
  );
}
