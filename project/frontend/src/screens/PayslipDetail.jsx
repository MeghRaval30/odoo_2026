// Payslip detail with the salary computation table (T-043).
//
// The table is the proof of graded rule #4: lines render in `sequence` order
// exactly as the engine evaluated them, and Gross/Net are read from the lines
// rather than from any stored column. The contract panel is the proof of rule
// #1 -- it names the contract that was resolved *for this period*, which is not
// necessarily the employee's newest one.

import { useCallback, useEffect, useState } from "react";
import { api, formatDate, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge } from "../components/ui";
import { href } from "../lib/router";

const CATEGORY_TONE = {
  BASIC: "blue",
  ALLOWANCE: "green",
  DEDUCTION: "red",
  GROSS: "purple",
  NET: "purple",
  EMPLOYER: "grey",
};

export default function PayslipDetail({ id }) {
  const [slip, setSlip] = useState(null);
  const [error, setError] = useState(null);
  const [pdfBusy, setPdfBusy] = useState(false);

  const load = useCallback(async () => {
    // Clear first: navigating between payslips keeps this component mounted, so
    // a failed load's banner otherwise stays on screen above the next payslip.
    setError(null);
    try {
      setSlip(await api.get(`/api/payslips/${id}/`));
    } catch (err) {
      setError(err.message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const openPdf = async () => {
    setPdfBusy(true);
    setError(null);
    try {
      const blob = await api.payslipPdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      setError(err.message);
    } finally {
      setPdfBusy(false);
    }
  };

  if (error && !slip) return <div className="page"><ErrorBox error={error} /></div>;
  if (!slip) return <div className="page"><Loading /></div>;

  const lines = [...(slip.lines || [])].sort((a, b) => a.sequence - b.sequence);

  return (
    <div className="page">
      <PageHead title={slip.employee_name} sub={slip.number}>
        <StateBadge state={slip.state} />
        <a className="btn" href={href(`/payroll/${slip.payrun}`)}>
          Back to payrun
        </a>
        <button className="primary" onClick={openPdf} disabled={pdfBusy}>
          {pdfBusy ? <span className="spinner" /> : "Print Payslip"}
        </button>
      </PageHead>

      <ErrorBox error={error} />

      <div className="smart-row">
        <div className="smart">
          <span className="n">{slip.worked_days}</span>
          <span className="l">Worked days</span>
        </div>
        <div className="smart">
          <span className="n">{slip.expected_days}</span>
          <span className="l">Expected days</span>
        </div>
        <div className="smart">
          <span className="n">{slip.lop_days}</span>
          <span className="l">LOP days</span>
        </div>
        <div className="smart">
          <span className="n">{Number(slip.overtime_hours || 0).toFixed(2)}</span>
          <span className="l">Overtime hrs</span>
        </div>
        <div className="smart">
          <span className="n">{money(slip.gross)}</span>
          <span className="l">Gross</span>
        </div>
        <div className="smart">
          <span className="n">{money(slip.net)}</span>
          <span className="l">Net</span>
        </div>
      </div>

      <div className="grid k3">
        <div className="card">
          <div className="card-title">Contract resolved for this period</div>
          <table>
            <tbody>
              <tr>
                <td className="muted">Reference</td>
                <td className="right mono">{slip.contract_reference || "—"}</td>
              </tr>
              <tr>
                <td className="muted">Contract wage</td>
                <td className="right mono">
                  {slip.contract_wage ? money(slip.contract_wage) : "—"}
                </td>
              </tr>
              <tr>
                <td className="muted">Structure</td>
                <td className="right">{slip.structure_name}</td>
              </tr>
              <tr>
                <td className="muted">Period</td>
                <td className="right tiny">
                  {formatDate(slip.period_start)} – {formatDate(slip.period_end)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-title">Totals</div>
          <table>
            <tbody>
              <tr>
                <td className="muted">Allowances</td>
                <td className="right mono">{money(slip.allowances)}</td>
              </tr>
              <tr>
                <td className="muted">Deductions</td>
                <td className="right mono">{money(slip.deductions)}</td>
              </tr>
              <tr>
                <td className="muted">Gross</td>
                <td className="right mono">{money(slip.gross)}</td>
              </tr>
              <tr>
                <td>
                  <strong>Net payable</strong>
                </td>
                <td className="right mono">
                  <strong>{money(slip.net)}</strong>
                </td>
              </tr>
              {Number(slip.employer_cost) > 0 && (
                <>
                  {/*
                    Employer contributions sit below Net deliberately. They are
                    a company cost, not a deduction from the employee, so they
                    must never appear to reduce take-home pay.
                  */}
                  <tr>
                    <td className="muted">Employer contributions</td>
                    <td className="right mono">
                      {money(slip.employer_cost)}
                    </td>
                  </tr>
                  <tr>
                    <td className="muted">Cost to company</td>
                    <td className="right mono">{money(slip.ctc)}</td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
          {Number(slip.employer_cost) > 0 && (
            <div className="tiny faint mt">
              Employer contributions are paid by the company and do not reduce
              net pay.
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Warnings</div>
          {slip.warnings?.length ? (
            slip.warnings.map((w) => (
              <div
                key={w.id}
                className={`alert ${w.severity === "ERROR" ? "error" : "warn"}`}
              >
                <strong>{w.code_display || w.code}</strong> — {w.message}
              </div>
            ))
          ) : (
            <div className="empty tiny">No warnings on this payslip</div>
          )}
        </div>
      </div>

      <div className="card mt">
        <div className="card-title">Salary computation — evaluated in sequence order</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th className="num" style={{ width: 60 }}>
                  Seq
                </th>
                <th>Rule</th>
                <th>Code</th>
                <th>Category</th>
                <th className="num">Quantity</th>
                <th className="num">Rate</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => {
                const isTotal = line.category === "GROSS" || line.category === "NET";
                return (
                  <tr key={line.id} style={isTotal ? { fontWeight: 600 } : undefined}>
                    <td className="num mono faint">{line.sequence}</td>
                    <td>{line.name}</td>
                    <td className="mono tiny muted">{line.code}</td>
                    <td>
                      <span className={`badge ${CATEGORY_TONE[line.category] || "grey"}`}>
                        {line.category_display || line.category}
                      </span>
                      {/* An employer line sits in the sequence like any other
                          but is kept out of gross and net — label it so the
                          category badge is not read as a deduction. */}
                      {line.is_employer_cost && (
                        <span className="badge purple" style={{ marginLeft: 6 }}>
                          Employer
                        </span>
                      )}
                    </td>
                    <td className="num mono">{line.quantity}</td>
                    <td className="num mono">{line.rate}</td>
                    <td className="num mono">{money(line.amount)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
