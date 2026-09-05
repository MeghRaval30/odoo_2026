// An employee's own payslips.
//
// Separate from the Payslips list, which is a payroll operator's tool: that one
// spans everybody, filters by period and structure, and exists to find an
// anomaly. This one spans one person and exists to answer "what was I paid, and
// can I have the PDF".
//
// This screen asks for one person's payslips **explicitly**.
//
// It used to lean on the server: the payslip queryset narrows to the caller's
// own employee unless they hold `payslip.read.all`, and the note here claimed
// the screen would show nothing extra even if it asked for everything. That
// reasoning only held from an Employee's seat. The three roles that do hold
// `payslip.read.all` are never narrowed, so a payroll operator opening this
// page saw all 61 payslips in the company under the heading "My payslips —
// every period you have been paid for". Not a leak, since those roles may read
// them anyway, but the page was telling them something untrue about whose
// money they were looking at.
//
// Own-scope is this screen's whole subject, so it states it rather than
// inheriting it. An account with no employee record has no payslips by
// definition, and says so instead of falling back to everybody's.

import { useState } from "react";
import { api, auth, downloadBlob, formatDate, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge, useResource } from "../components/ui";

export default function MyPayslips() {
  const employeeId = auth.user?.employee_id ?? null;
  const { rows, loading, error } = useResource(
    employeeId ? "/api/payslips/" : null,
    { ordering: "-period_start", employee: employeeId },
  );
  const [busy, setBusy] = useState(null);
  const [problem, setProblem] = useState(null);

  const getPdf = async (slip) => {
    setBusy(slip.id);
    setProblem(null);
    try {
      const blob = await api.payslipPdf(slip.id);
      downloadBlob(blob, `${(slip.number || "payslip").replace(/\//g, "-")}.pdf`);
    } catch (err) {
      setProblem(err.message);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="page">
      <PageHead
        title="My payslips"
        sub="Every period you have been paid for, newest first"
      />

      <ErrorBox error={error || problem} />



      <div className="card">
        {employeeId === null ? (
          <div className="empty">
            This account is not linked to an employee record, so it has no
            payslips of its own. The full payroll register is under Payroll.
          </div>
        ) : !rows.length ? (
          <div className="empty">
            No payslips yet. One appears here once a payrun covering your period
            has been computed.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Period</th>
                  <th className="num">Worked days</th>
                  <th className="num">Gross</th>
                  <th className="num">Deductions</th>
                  <th className="num">Net</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((slip) => (
                  <tr key={slip.id}>
                    <td className="mono tiny">{slip.number}</td>
                    <td className="nowrap">
                      {formatDate(slip.period_start)} – {formatDate(slip.period_end)}
                    </td>
                    <td className="num mono">
                      {slip.worked_days} / {slip.expected_days}
                    </td>
                    <td className="num mono">{money(slip.gross)}</td>
                    <td className="num mono">
                      {money(Number(slip.gross || 0) - Number(slip.net || 0))}
                    </td>
                    <td className="num mono">
                      <strong>{money(slip.net)}</strong>
                    </td>
                    <td>
                      <StateBadge state={slip.state} />
                    </td>
                    <td className="right nowrap">
                      <a
                        className="btn sm"
                        href={`#/payslips/${slip.id}`}
                        style={{ marginRight: 6 }}
                      >
                        Open
                      </a>
                      <button
                        className="sm"
                        disabled={busy === slip.id}
                        onClick={() => getPdf(slip)}
                      >
                        {busy === slip.id ? <span className="spinner" /> : null} PDF
                      </button>
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
