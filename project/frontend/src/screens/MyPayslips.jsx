// An employee's own payslips.
//
// Separate from the Payslips list, which is a payroll operator's tool: that one
// spans everybody, filters by period and structure, and exists to find an
// anomaly. This one spans one person and exists to answer "what was I paid, and
// can I have the PDF".
//
// The scoping is the server's — the payslip queryset narrows to the caller's
// own employee unless they hold `payslip.read.all`. This screen would show
// nothing extra even if it asked for it.

import { useState } from "react";
import { api, downloadBlob, formatDate, money } from "../api";
import { ErrorBox, Loading, PageHead, StateBadge, useResource } from "../components/ui";

export default function MyPayslips() {
  const { rows, loading, error } = useResource("/api/payslips/", {
    ordering: "-period_start",
  });
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
        {!rows.length ? (
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
                    <td className="num">
                      {slip.worked_days} / {slip.expected_days}
                    </td>
                    <td className="num">{money(slip.gross)}</td>
                    <td className="num">
                      {money(Number(slip.gross || 0) - Number(slip.net || 0))}
                    </td>
                    <td className="num">
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
