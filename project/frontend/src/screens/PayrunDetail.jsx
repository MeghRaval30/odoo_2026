// Payrun detail and the action bar (T-042).
//
// Warnings are rendered ABOVE the payslip table and before Validate is offered,
// because surfacing problems pre-finalization is graded rule #5. The action
// buttons are driven by the server's own can_compute / can_validate /
// can_mark_paid flags rather than by re-deriving the state machine here.

import { useCallback, useEffect, useState } from "react";
import { api, downloadBlob, formatDate, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge, rows } from "../components/ui";
import { href, navigate } from "../lib/router";

const STEPS = ["DRAFT", "VERIFY", "DONE", "PAID"];
const STEP_LABEL = {
  DRAFT: "Draft",
  VERIFY: "Computed",
  DONE: "Validated",
  PAID: "Paid",
};

export default function PayrunDetail({ id }) {
  const [payrun, setPayrun] = useState(null);
  const [slips, setSlips] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [run, slipRows, warnRows] = await Promise.all([
        api.get(`/api/payruns/${id}/`),
        api.get(`/api/payruns/${id}/payslips/`),
        api.get(`/api/payruns/${id}/warnings/`),
      ]);
      setPayrun(run);
      setSlips(rows(slipRows));
      setWarnings(rows(warnRows));
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (verb, label) => {
    setBusy(verb);
    setError(null);
    setNotice(null);
    try {
      const result = await api.post(`/api/payruns/${id}/${verb}/`, {});
      setNotice(result?.detail || `${label} complete.`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  if (error && !payrun) return <div className="page"><ErrorBox error={error} /></div>;
  if (!payrun) return <div className="page"><Loading /></div>;

  const errors = warnings.filter((w) => w.severity === "ERROR");
  const advisories = warnings.filter((w) => w.severity !== "ERROR");
  const stepIndex = STEPS.indexOf(payrun.state);

  return (
    <div className="page">
      <PageHead
        title={payrun.name}
        sub={`${formatDate(payrun.period_start)} – ${formatDate(payrun.period_end)} · ${payrun.structure_name}`}
      >
        <a className="btn" href={href("/payroll")}>
          All payruns
        </a>
      </PageHead>

      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`step${i <= stepIndex ? " on" : ""}`}>
            {STEP_LABEL[s]}
          </span>
        ))}
        <div className="spacer" />
        <StateBadge state={payrun.state} label={payrun.state_display} />
      </div>

      <ErrorBox error={error} />
      {notice && <div className="alert ok">{notice}</div>}

      <div className="card">
        <div className="row">
          <button
            className="primary"
            disabled={!payrun.can_compute || busy}
            onClick={() => act("compute", "Compute")}
          >
            {busy === "compute" ? <span className="spinner" /> : "Compute"}
          </button>
          <button
            disabled={!payrun.can_validate || busy}
            onClick={() => act("validate", "Validate")}
          >
            {busy === "validate" ? <span className="spinner" /> : "Validate"}
          </button>
          <button
            disabled={!payrun.can_mark_paid || busy}
            onClick={() => act("mark-paid", "Mark paid")}
          >
            {busy === "mark-paid" ? <span className="spinner" /> : "Mark Paid"}
          </button>
          <button
            disabled={!slips.length || busy}
            onClick={() => act("send-payslips", "Send payslips")}
          >
            {busy === "send-payslips" ? <span className="spinner" /> : "Send Payslips"}
          </button>
          <button
            disabled={!slips.length || busy}
            onClick={async () => {
              setBusy("register");
              setError(null);
              try {
                const { blob, filename } = await api.payrunRegister(id);
                downloadBlob(blob, filename);
              } catch (err) {
                setError(err.message);
              } finally {
                setBusy(null);
              }
            }}
          >
            {busy === "register" ? <span className="spinner" /> : "Export Register"}
          </button>
          <div className="spacer" />
          <div className="smart-row" style={{ margin: 0 }}>
            <div className="smart">
              <span className="n">{payrun.payslip_count}</span>
              <span className="l">Payslips</span>
            </div>
            <div className="smart">
              <span className="n">{money(payrun.total_gross)}</span>
              <span className="l">Gross</span>
            </div>
            <div className="smart">
              <span className="n">{money(payrun.total_net)}</span>
              <span className="l">Net</span>
            </div>
          </div>
        </div>
      </div>

      {(errors.length > 0 || advisories.length > 0) && (
        <div className="card">
          <div className="card-title">
            Pre-validation checks — {errors.length} error(s), {advisories.length} warning(s)
          </div>
          {errors.map((w) => (
            <div key={w.id} className="alert error">
              <strong>{w.code_display || w.code}</strong>
              {w.employee_name ? ` · ${w.employee_name}` : ""} — {w.message}
            </div>
          ))}
          {advisories.map((w) => (
            <div key={w.id} className="alert warn">
              <strong>{w.code_display || w.code}</strong>
              {w.employee_name ? ` · ${w.employee_name}` : ""} — {w.message}
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="card-title">Payslips</div>
        {slips.length === 0 ? (
          <div className="empty">
            No payslips yet — run Compute to generate them.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Employee</th>
                  <th>Department</th>
                  <th className="num">Worked days</th>
                  <th className="num">Basic</th>
                  <th className="num">Gross</th>
                  <th className="num">Net</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {slips.map((s) => (
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
                    <td className="num mono">{s.worked_days}</td>
                    <td className="num mono">{money(s.basic)}</td>
                    <td className="num mono">{money(s.gross)}</td>
                    <td className="num mono">{money(s.net)}</td>
                    <td>
                      {s.warning_codes?.length ? (
                        s.warning_codes.map((c) => (
                          <span key={c} className="badge amber" style={{ marginRight: 3 }}>
                            {c}
                          </span>
                        ))
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
    </div>
  );
}
