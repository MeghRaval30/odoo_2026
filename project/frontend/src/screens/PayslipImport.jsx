// Importing pay that already happened.
//
// Four steps, one screen: choose a file, check what each column was read as,
// review what would be written, write it. The stages are a state machine
// rather than routes because the run only exists in the middle of it — a
// bookmark to step three would be a bookmark to nothing.
//
// The preview is the point of the screen. Every payroll sheet states a gross
// and a net beside the components that produce them, so the server checks each
// row against its own totals, and the column that matters most here is the one
// showing whether the arithmetic agrees. A migration that quietly drops an
// allowance still produces payslips that look entirely ordinary; the only
// thing that catches it before it is written is that sum.

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { ErrorBox, Loading, PageHead } from "../components/ui";
import { CountUp, Stagger } from "../components/ai";

const MONEY = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const money = (v) => (v === null || v === undefined ? "—" : MONEY.format(Number(v)));

/** Group the field list the way the picker offers it. */
function groupFields(fields) {
  const groups = [];
  fields.forEach((f) => {
    let group = groups.find((g) => g.name === f.group);
    if (!group) groups.push((group = { name: f.group, fields: [] }));
    group.fields.push(f);
  });
  return groups;
}

export default function PayslipImport() {
  const [stage, setStage] = useState("choose");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const [fields, setFields] = useState([]);
  const [health, setHealth] = useState(null);
  const [source, setSource] = useState(null);
  const [runId, setRunId] = useState(null);
  const [plan, setPlan] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [override, setOverride] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef(null);

  useEffect(() => {
    api.get("/api/intel/payslip-fields/").then(setFields).catch(() => {});
    api.get("/api/intel/payslip-health/").then(setHealth).catch(() => {});
  }, []);

  const byKey = useMemo(() => {
    const map = {};
    fields.forEach((f) => (map[f.key] = f));
    return map;
  }, [fields]);

  const grouped = useMemo(() => groupFields(fields), [fields]);

  // -- loading a file -----------------------------------------------------

  function loadFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      setError(null);
      setBusy(true);
      try {
        const b64 = String(reader.result).split(",")[1] || "";
        const src = await api.post("/api/intel/sources/", {
          filename: file.name,
          content_b64: b64,
        });
        setSource(src);
        const run = await api.post("/api/intel/payslip-runs/", { source: src.id });
        setRunId(run.id);
        const read = await api.post(`/api/intel/payslip-runs/${run.id}/analyze/`);
        setAnalysis(read);
        setPlan(read.plan);
        setStage("map");
      } catch (e) {
        setError(e.message);
        setStage("choose");
      } finally {
        setBusy(false);
      }
    };
    reader.readAsDataURL(file);
  }

  // -- editing the mapping ------------------------------------------------

  async function setColumnField(index, field) {
    setError(null);
    try {
      const next = await api.patch(`/api/intel/payslip-runs/${runId}/plan/`, {
        columns: [{ index, field: field || null }],
      });
      setPlan(next);
    } catch (e) {
      setError(e.message);
    }
  }

  async function saveOverride() {
    setError(null);
    try {
      const next = await api.patch(`/api/intel/payslip-runs/${runId}/plan/`, {
        period_override: override,
      });
      setPlan(next);
    } catch (e) {
      setError(e.message);
    }
  }

  // -- preview and commit -------------------------------------------------

  async function runPreview() {
    setError(null);
    setBusy(true);
    try {
      setPreview(await api.post(`/api/intel/payslip-runs/${runId}/preview/`));
      setStage("preview");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runCommit() {
    setError(null);
    setBusy(true);
    try {
      setResult(await api.post(`/api/intel/payslip-runs/${runId}/commit/`));
      setStage("done");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function restart() {
    setStage("choose");
    setSource(null);
    setRunId(null);
    setPlan(null);
    setAnalysis(null);
    setPreview(null);
    setResult(null);
    setOverride("");
    setError(null);
  }

  const gaps = plan?.gaps || [];

  return (
    <div className="page">
      <PageHead
        title="Import Past Payslips"
        sub={
          source
            ? `${source.original_filename} · ${source.row_count} rows`
            : health?.structure
            ? `Filed against ${health.structure}`
            : "—"
        }
      >
        {stage !== "choose" && (
          <button className="ghost" onClick={restart}>
            Start over
          </button>
        )}
      </PageHead>

      <div className="steps">
        {["Choose a file", "Check the columns", "Review", "Import"].map((label, i) => {
          const at = ["choose", "map", "preview", "done"].indexOf(stage);
          return (
            <span
              key={label}
              className={`step${i === at ? " on" : ""}${i < at ? " done" : ""}`}
            >
              {label}
            </span>
          );
        })}
      </div>

      {error && <ErrorBox error={error} />}
      {busy && <Loading />}

      {stage === "choose" && !busy && (
        <ChooseFile
          dragging={dragging}
          setDragging={setDragging}
          fileInput={fileInput}
          onFile={loadFile}
          health={health}
        />
      )}

      {stage === "map" && plan && !busy && (
        <MapColumns
          plan={plan}
          analysis={analysis}
          grouped={grouped}
          byKey={byKey}
          gaps={gaps}
          override={override}
          setOverride={setOverride}
          saveOverride={saveOverride}
          onPick={setColumnField}
          onNext={runPreview}
        />
      )}

      {stage === "preview" && preview && !busy && (
        <Preview
          preview={preview}
          onBack={() => setStage("map")}
          onCommit={runCommit}
        />
      )}

      {stage === "done" && result && !busy && (
        <Done result={result} onAgain={restart} />
      )}
    </div>
  );
}

// ==========================================================================

function ChooseFile({ dragging, setDragging, fileInput, onFile, health }) {
  return (
    <div className="card">
      <div
        className={`dropzone${dragging ? " over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          onFile(e.dataTransfer.files?.[0]);
        }}
        onClick={() => fileInput.current?.click()}
      >
        <div className="card-title">Drop a salary register here</div>
        <div className="muted tiny">.xlsx or .csv</div>
        <input
          ref={fileInput}
          type="file"
          accept=".xlsx,.xls,.csv"
          hidden
          onChange={(e) => onFile(e.target.files?.[0])}
        />
      </div>
      {health && !health.ready && (
        <p className="muted tiny">{health.detail}</p>
      )}
    </div>
  );
}

// ==========================================================================

function MapColumns({
  plan, analysis, grouped, byKey, gaps, override, setOverride, saveOverride,
  onPick, onNext,
}) {
  const mapped = plan.columns.filter((c) => c.field).length;
  const needsPeriod = gaps.some((g) => g.key === "period");

  return (
    <>
      <div className="card">
        <div className="row between">
          <h2>Columns</h2>
          <span className="muted tiny">
            {mapped} of {plan.columns.length} mapped
          </span>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Read as</th>
                <th>Why</th>
                <th>Values</th>
              </tr>
            </thead>
            <tbody>
              {plan.columns.map((column, i) => (
                <Stagger key={column.index} index={i}>
                  <tr className={column.field ? "" : "row-muted"}>
                    <td>{column.header}</td>
                    <td>
                      <select
                       
                        value={column.field || ""}
                        onChange={(e) => onPick(column.index, e.target.value)}
                      >
                        <option value="">— not imported —</option>
                        {grouped.map((group) => (
                          <optgroup key={group.name} label={group.name}>
                            {group.fields.map((f) => (
                              <option key={f.key} value={f.key}>
                                {f.label}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </td>
                    <td className="muted tiny">{column.reason}</td>
                    <td className="muted tiny mono">{column.evidence}</td>
                  </tr>
                </Stagger>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {gaps.length > 0 && (
        <div className="card">
          <div className="row between">
            <h2>Before this can be imported</h2>
          </div>
          <ul className="gap-list">
            {gaps.map((gap) => (
              <li key={gap.key}>
                <span>{gap.label}</span>
                <span className="muted tiny"> {gap.why}</span>
              </li>
            ))}
          </ul>
          {needsPeriod && (
            <div className="inline-form">
              <input
               
                placeholder="December 2025"
                value={override}
                onChange={(e) => setOverride(e.target.value)}
              />
              <button className="ghost" onClick={saveOverride}>
                Use this month for every row
              </button>
            </div>
          )}
        </div>
      )}

      <div className="actions-row">
        <span className="muted tiny">{analysis?.message}</span>
        <button className="primary" disabled={gaps.length > 0} onClick={onNext}>
          Review {analysis?.summary?.rows ?? ""} rows
        </button>
      </div>
    </>
  );
}

// ==========================================================================

function Preview({ preview, onBack, onCommit }) {
  const s = preview.summary;
  return (
    <>
      <div className="smart-row">
        <Stat label="Importable" value={s.importable} />
        <Stat label="Blocked" value={s.blocked} tone={s.blocked ? "red" : null} />
        <Stat label="Months" value={s.period_count} />
        <Stat
          label="Reconciled"
          value={s.reconciled}
          tone={s.unreconciled ? "amber" : "green"}
        />
        <Stat label="Total net" value={money(s.total_net)} text />
      </div>

      {s.periods.length > 0 && (
        <p className="muted tiny">{s.periods.join(" · ")}</p>
      )}

      <div className="card">
        <div className="row between">
          <h2>Rows</h2>
          <span className="muted tiny">
            {s.matched_by_code} by code · {s.matched_by_email} by email ·{" "}
            {s.matched_by_name} by name
          </span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Employee</th>
                <th>Month</th>
                <th className="right">Earnings</th>
                <th className="right">Deductions</th>
                <th className="right">Net</th>
                <th>Checks</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr
                  key={row.row}
                  className={row.importable ? "" : "row-blocked"}
                >
                  <td className="muted tiny mono">{row.row + 1}</td>
                  <td>
                    <span>{row.employee_name}</span>
                    {row.matched_by && (
                      <span className="muted tiny"> · {row.matched_by}</span>
                    )}
                  </td>
                  <td className="tiny">{row.period_label || "—"}</td>
                  <td className="right mono num">{money(row.check.earnings)}</td>
                  <td className="right mono num">{money(row.check.deductions)}</td>
                  <td className="right mono num">
                    {money(row.check.computed_net)}
                  </td>
                  <td className="tiny">
                    {row.problems.map((p, i) => (
                      <div key={i} className="bad">
                        {p}
                      </div>
                    ))}
                    {row.warnings.map((w, i) => (
                      <div key={i} className="warn">
                        {w}
                      </div>
                    ))}
                    {!row.problems.length &&
                      !row.warnings.length &&
                      row.check.ok && <span className="ok">balances</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {preview.truncated > 0 && (
          <p className="muted tiny">{preview.truncated} more rows not shown</p>
        )}
      </div>

      <div className="actions-row">
        <button className="ghost" onClick={onBack}>
          Back to columns
        </button>
        <button
          className="primary"
          disabled={!s.importable}
          onClick={onCommit}
        >
          Import {s.importable} payslips
        </button>
      </div>
    </>
  );
}

// ==========================================================================

function Done({ result, onAgain }) {
  const c = result.created;
  return (
    <div className="card">
      <div className="row between">
        <h2>Imported</h2>
      </div>
      <div className="smart-row">
        <Stat label="Payslips" value={c.payslips} />
        <Stat label="Payruns" value={c.payruns} />
        <Stat label="Lines" value={c.lines} />
      </div>
      <ul className="gap-list">
        {c.payrun_names.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
      <div className="actions-row">
        <button className="ghost" onClick={onAgain}>
          Import another file
        </button>
        <a className="primary" href="#/payroll">
          Open Payruns
        </a>
      </div>
    </div>
  );
}

function Stat({ label, value, tone, text }) {
  return (
    <div className="smart" style={{ cursor: "default" }}>
      <span className={`n${tone ? ` ${tone}` : ""}`}>
        {text ? value : <CountUp to={value} />}
      </span>
      <span className="l">{label}</span>
    </div>
  );
}
