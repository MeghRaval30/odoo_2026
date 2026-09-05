// Payroll register report.
//
// The dashboard answers "how are we doing"; this answers "show me the numbers".
// One row per payslip, one column per rule code, with a totals row — the view a
// payroll officer reconciles against before releasing a run.
//
// Columns come from the lines the payrun actually produced, not from the salary
// structure, so a run whose rules changed mid-period still reconciles.

import { useCallback, useEffect, useState } from "react";
import { api, downloadBlob, hoursMinutes, money } from "../api";
import { ErrorBox, Loading, PageHead, useResource } from "../components/ui";

const CATEGORY_HINT = {
  BASIC: "blue",
  GROSS: "purple",
  NET: "purple",
};

export default function Reports() {
  const [payrunId, setPayrunId] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  const payruns = useResource("/api/payruns/", { ordering: "-period_start" });

  // Which run to open on is decided by the server, not by "the first row"
  // (D-034). The newest payrun is the off-cycle correction holding a single
  // payslip, so a register defaulting to it opens on a one-line report; the
  // newest *paid* run is the one an officer actually reconciles. The dashboard
  // already reads this same value, which is the point of naming it once.
  useEffect(() => {
    if (payrunId || !payruns.rows.length) return;
    let cancelled = false;
    (async () => {
      let preferred = null;
      try {
        const opts = await api.get("/api/dashboard/filters/");
        preferred = opts.default_period;
      } catch {
        preferred = null;      // fall through to the newest run
      }
      if (cancelled) return;
      const known = payruns.rows.some((p) => String(p.id) === String(preferred));
      setPayrunId(String(known ? preferred : payruns.rows[0].id));
    })();
    return () => { cancelled = true; };
  }, [payruns.rows, payrunId]);

  const load = useCallback(async () => {
    if (!payrunId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.get(`/api/payruns/${payrunId}/register-data/`));
    } catch (err) {
      setError(err.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [payrunId]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = async () => {
    setExporting(true);
    setError(null);
    try {
      const { blob, filename } = await api.payrunRegister(payrunId);
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  };

  const payrun = payruns.rows.find((p) => String(p.id) === String(payrunId));

  return (
    <div className="page">
      <PageHead
        title="Payroll Register"
        sub={payrun ? `${payrun.name} · ${payrun.structure_name}` : undefined}
      >
        {loading && <span className="spinner" />}
        <button onClick={exportCsv} disabled={!data || exporting}>
          {exporting ? <span className="spinner" /> : "Export CSV"}
        </button>
      </PageHead>

      <div className="toolbar">
        <div>
          <label htmlFor="r-payrun">Payrun</label>
          <select
            id="r-payrun"
            value={payrunId}
            onChange={(e) => setPayrunId(e.target.value)}
          >
            {payruns.rows.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="spacer" />
        <button onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>

      <ErrorBox error={error || payruns.error} />

      {!data ? (
        loading ? (
          <Loading />
        ) : (
          <div className="card">
            <div className="empty">No register to show.</div>
          </div>
        )
      ) : data.rows.length === 0 ? (
        <div className="card">
          <div className="empty">
            This payrun has no payslips yet. Run Compute first.
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-title">
            {data.rows.length} payslips · {data.codes.length} rule columns
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th className="num">Worked</th>
                  <th className="num">LOP</th>
                  <th className="num">Overtime</th>
                  {data.codes.map((code) => (
                    <th key={code} className="num">
                      {code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.payslip_id}>
                    <td>{row.employee}</td>
                    <td className="muted">{row.department || "—"}</td>
                    <td className="num mono">{row.worked_days}</td>
                    <td className="num mono">{row.lop_days}</td>
                    <td className="num mono">{hoursMinutes(row.overtime_hours)}</td>
                    {data.codes.map((code) => (
                      <td
                        key={code}
                        className="num mono"
                        style={
                          CATEGORY_HINT[code]
                            ? { fontWeight: 600 }
                            : undefined
                        }
                      >
                        {row.amounts[code] == null
                          ? "—"
                          : money(row.amounts[code])}
                      </td>
                    ))}
                  </tr>
                ))}
                <tr style={{ fontWeight: 600 }}>
                  <td>Total</td>
                  <td />
                  <td />
                  <td />
                  <td />
                  {data.codes.map((code) => (
                    <td key={code} className="num mono">
                      {money(data.totals[code])}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
