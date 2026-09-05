// Payruns: list, the two-step wizard (T-041) and the detail action bar (T-042).
//
// The wizard's defining behaviour, called out explicitly in the spec: step 1
// collects scope and creates NOTHING. Only confirming step 2 posts to
// create-with-employees. Step 2's employee list comes from a POST that is a
// pure query -- it previews contract resolution for the chosen period, so an
// employee with no contract covering it is visible before any record exists.

import { useState } from "react";
import { api, auth, formatDate, money } from "../api";
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
import { href, navigate } from "../lib/router";
import PayrunDetail from "./PayrunDetail";

const today = new Date();
const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
const lastOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);

// Local date parts, not toISOString(): east-of-UTC offsets push the UTC date
// back a day, which defaulted the period to 31 Aug - 29 Sep instead of
// 1 - 30 Sep.
const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;

function Wizard({ onClose, onCreated }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    name: "",
    salary_structure: "",
    period_start: iso(firstOfMonth),
    period_end: iso(lastOfMonth),
    employee_type: "",
    company: "",
  });
  const [eligible, setEligible] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const structures = useResource("/api/salary-structures/");
  const options = useResource("/api/dashboard/filters/");

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  // Step 1 -> 2: a query only. No payrun exists yet.
  const preview = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.post("/api/payruns/eligible-employees/", {
        employee_type: form.employee_type,
        salary_structure: form.salary_structure,
        period_start: form.period_start,
        period_end: form.period_end,
      });
      const list = rows(result);
      setEligible(list);
      setSelected(new Set(list.filter((r) => r.has_contract).map((r) => r.id)));
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  // Step 2 confirm: this is the only call that writes.
  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      const payrun = await api.post("/api/payruns/create-with-employees/", {
        ...form,
        company: form.company || structures.rows[0]?.company || 1,
        employee_ids: [...selected],
      });
      onCreated(payrun);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const needle = employeeSearch.trim().toLowerCase();
  const shown = needle
    ? eligible.filter(
        (r) =>
          r.name.toLowerCase().includes(needle) ||
          (r.department || "").toLowerCase().includes(needle),
      )
    : eligible;

  const toggle = (id) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <Modal
      wide
      title="New Payrun"
      onClose={onClose}
      footer={
        step === 1 ? (
          <>
            <button onClick={onClose}>Cancel</button>
            <button
              className="primary"
              onClick={preview}
              disabled={busy || !form.name || !form.salary_structure}
            >
              {busy ? <span className="spinner" /> : "Next"}
            </button>
          </>
        ) : (
          <>
            <button onClick={() => setStep(1)}>Back</button>
            <button
              className="primary"
              onClick={confirm}
              disabled={busy || !selected.size}
            >
              {busy ? <span className="spinner" /> : `Create payrun (${selected.size})`}
            </button>
          </>
        )
      }
    >
      <div className="steps">
        <span className={`step${step === 1 ? " on" : ""}`}>1 · Scope</span>
        <span className="faint">→</span>
        <span className={`step${step === 2 ? " on" : ""}`}>2 · Employees</span>
      </div>

      <ErrorBox error={error} />

      {step === 1 ? (
        <>
          <Field label="Payrun name">
            <input
              value={form.name}
              onChange={set("name")}
              placeholder="e.g. March 2026"
            />
          </Field>
          <div className="row fill">
            <Field label="Period start">
              <input type="date" value={form.period_start} onChange={set("period_start")} />
            </Field>
            <Field label="Period end">
              <input type="date" value={form.period_end} onChange={set("period_end")} />
            </Field>
          </div>
          <Field label="Salary structure">
            <select value={form.salary_structure} onChange={set("salary_structure")}>
              <option value="">Select a structure…</option>
              {structures.rows.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Employee type">
            <select value={form.employee_type} onChange={set("employee_type")}>
              <option value="">All employee types</option>
              {options.data?.employee_types?.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
        </>
      ) : (
        <>
          <div className="row mb">
            <input
              type="search"
              style={{ maxWidth: 240 }}
              placeholder="Search employee…"
              value={employeeSearch}
              onChange={(e) => setEmployeeSearch(e.target.value)}
            />
            <span className="muted tiny mono">
              1–{shown.length} / {eligible.length}
            </span>
            <span className="badge blue">{selected.size} selected</span>
            <div className="spacer" />
            <button
              className="sm"
              onClick={() =>
                setSelected(
                  new Set([...selected, ...shown.map((r) => r.id)]),
                )
              }
            >
              Select all
            </button>
            <button className="sm" onClick={() => setSelected(new Set())}>
              Clear
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 30 }} />
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Working hours</th>
                  <th>Contract from</th>
                  <th className="num">Wage</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((row) => (
                  <tr key={row.id} className="clickable" onClick={() => toggle(row.id)}>
                    <td>
                      <input
                        type="checkbox"
                        style={{ width: 15 }}
                        checked={selected.has(row.id)}
                        onChange={() => toggle(row.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td>
                      {row.name}
                      {!row.has_contract && (
                        <span className="badge red" style={{ marginLeft: 6 }}>
                          No contract for period
                        </span>
                      )}
                    </td>
                    <td className="muted">{row.department || "—"}</td>
                    <td className="muted tiny">{row.working_hours || "—"}</td>
                    <td className="muted">{formatDate(row.start_date)}</td>
                    <td className="num mono">{row.wage ? money(row.wage) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Modal>
  );
}

export default function Payruns({ route }) {
  const [wizard, setWizard] = useState(false);
  const payruns = useResource("/api/payruns/", { ordering: "-period_start" });
  const detailId = route.parts[1];

  if (detailId) return <PayrunDetail id={detailId} />;

  return (
    <div className="page">
      <PageHead title="Payruns" sub={`${payruns.rows.length} records`}>
        {/* A read-only payroll role opens this screen to check a run, not
            to start one. Offering a button the server refuses is the same
            fault as hiding one it allows, only pointing the other way. */}
        {auth.has("payrun.write") && (
          <button className="primary" onClick={() => setWizard(true)}>
            New Payrun
          </button>
        )}
      </PageHead>

      <ErrorBox error={payruns.error} />

      <div className="card">
        {payruns.loading ? (
          <Loading />
        ) : payruns.rows.length === 0 ? (
          <div className="empty">No payruns yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Period</th>
                  <th>Structure</th>
                  <th className="num">Payslips</th>
                  <th className="num">Gross</th>
                  <th className="num">Net</th>
                  <th>Warnings</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {payruns.rows.map((p) => (
                  <tr
                    key={p.id}
                    className="clickable"
                    onClick={() => navigate(`/payroll/${p.id}`)}
                  >
                    <td>
                      <a href={href(`/payroll/${p.id}`)}>{p.name}</a>
                    </td>
                    <td className="muted tiny">
                      {formatDate(p.period_start)} – {formatDate(p.period_end)}
                    </td>
                    <td className="muted">{p.structure_name}</td>
                    <td className="num mono">{p.payslip_count}</td>
                    <td className="num mono">{money(p.total_gross)}</td>
                    <td className="num mono">{money(p.total_net)}</td>
                    <td>
                      {p.error_count > 0 && (
                        <span className="badge red">{p.error_count} error</span>
                      )}
                      {p.warning_count > 0 && (
                        <span className="badge amber" style={{ marginLeft: 4 }}>
                          {p.warning_count} warn
                        </span>
                      )}
                      {!p.error_count && !p.warning_count && (
                        <span className="faint">—</span>
                      )}
                    </td>
                    <td>
                      <StateBadge state={p.state} label={p.state_display} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {wizard && (
        <Wizard
          onClose={() => setWizard(false)}
          onCreated={(payrun) => {
            setWizard(false);
            navigate(`/payroll/${payrun.id}`);
          }}
        />
      )}
    </div>
  );
}
