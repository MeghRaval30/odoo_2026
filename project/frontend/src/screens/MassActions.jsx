// Mass actions — a change to many people, with the consequences shown first.
//
// Nothing here happens without a preview. That is not a courtesy; it is the
// only reason a screen that can end fifty contracts is safe to put in front of
// somebody. The preview is a real table of every person and every figure, from
// the same code that performs the change, and the execute button is behind a
// typed confirmation because a mis-click here is not undoable.

import { useState } from "react";
import { api, auth } from "../api";
import { ErrorBox, Field, Loading, PageHead, useResource, rows } from "../components/ui";
import { CountUp, Stagger } from "../components/ai";

const KINDS = [
  { key: "INCREMENT", label: "Increment", blurb: "Raise pay from a date, on a new contract" },
  { key: "EXIT", label: "Offboarding", blurb: "End employment, settle bonds" },
  { key: "TRANSFER", label: "Transfer", blurb: "Move people between departments or sites" },
  { key: "BOND_ISSUE", label: "Issue bonds", blurb: "Raise a bond for everyone in a segment" },
];

const money = (v) =>
  v === null || v === undefined || v === ""
    ? "—"
    : Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });

export default function MassActions() {
  const segments = rows(useResource("/api/workforce/segments/").data);
  const templates = rows(useResource("/api/workforce/bond-templates/").data);
  const history = useResource("/api/workforce/bulk-operations/");

  const [kind, setKind] = useState("INCREMENT");
  const [segmentId, setSegmentId] = useState("");
  const [params, setParams] = useState({ mode: "percent", value: 8 });
  const [operation, setOperation] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [confirm, setConfirm] = useState("");
  const [result, setResult] = useState(null);

  const canWrite = auth.has("workforce.write");
  const segment = segments.find((s) => String(s.id) === String(segmentId));

  if (!canWrite) {
    return (
      <div className="page">
        <div className="card">
          <div className="empty">Not available for this account.</div>
        </div>
      </div>
    );
  }

  async function runPreview() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const op = await api.post("/api/workforce/bulk-operations/", {
        name: `${KINDS.find((k) => k.key === kind).label} — ${segment?.name || "everyone"}`,
        kind,
        segment: segmentId || null,
        params,
      });
      const p = await api.post(`/api/workforce/bulk-operations/${op.id}/preview/`, {
        params,
      });
      setOperation(op);
      setPreview(p);
      setConfirm("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function execute() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post(`/api/workforce/bulk-operations/${operation.id}/execute/`);
      setResult(r);
      setPreview(null);
      setOperation(null);
      history.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const people = preview?.totals?.people ?? 0;
  const phrase = `${kind.toLowerCase()} ${people}`;

  return (
    <div className="page">
      <PageHead
        title="Mass actions"
        sub="One decision, applied to a group, previewed before it lands"
      />
      <ErrorBox error={error} />

      {result && (
        <Stagger>
          <div className="card" style={{ borderColor: "var(--green)" }}>
            <div className="card-title">Done</div>
            <div className="row" style={{ gap: 22, marginTop: 8 }}>
              {Object.entries(result)
                .filter(([k, v]) => typeof v === "number" && k !== "matched")
                .map(([k, v]) => (
                  <div key={k}>
                    <div className="bignum">
                      <CountUp to={v} />
                    </div>
                    <div className="tiny faint">{k.replace(/_/g, " ")}</div>
                  </div>
                ))}
            </div>
          </div>
        </Stagger>
      )}

      <div className="card">
        <div className="card-title">What to do</div>
        <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap" }}>
          {KINDS.map((k) => (
            <button
              key={k.key}
              className={kind === k.key ? "primary" : "ghost"}
              onClick={() => {
                setKind(k.key);
                setPreview(null);
                setResult(null);
                setParams(
                  k.key === "INCREMENT"
                    ? { mode: "percent", value: 8 }
                    : k.key === "EXIT"
                    ? { exit_date: new Date().toISOString().slice(0, 10), reason: "" }
                    : k.key === "BOND_ISSUE"
                    ? { template: templates[0]?.id }
                    : {}
                );
              }}
              title={k.blurb}
            >
              {k.label}
            </button>
          ))}
        </div>
        <div className="tiny faint" style={{ marginTop: 6 }}>
          {KINDS.find((k) => k.key === kind)?.blurb}
        </div>

        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 12 }}>
          <Field label="Who" hint={segment ? segment.description_text : "Everyone employed"}>
            <select value={segmentId} onChange={(e) => { setSegmentId(e.target.value); setPreview(null); }}>
              <option value="">Everyone</option>
              {segments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.match_count})
                </option>
              ))}
            </select>
          </Field>

          {kind === "INCREMENT" && (
            <>
              <Field label="Raise by">
                <div className="row" style={{ gap: 6 }}>
                  <select
                    value={params.mode}
                    onChange={(e) => setParams({ ...params, mode: e.target.value })}
                  >
                    <option value="percent">Percent</option>
                    <option value="flat">Fixed amount</option>
                  </select>
                  <input
                    type="number"
                    value={params.value}
                    onChange={(e) => setParams({ ...params, value: Number(e.target.value) })}
                  />
                </div>
              </Field>
              <Field label="Effective from" hint="A new contract starts on this date">
                <input
                  type="date"
                  value={params.effective_from || ""}
                  onChange={(e) => setParams({ ...params, effective_from: e.target.value })}
                />
              </Field>
            </>
          )}

          {kind === "EXIT" && (
            <>
              <Field label="Last working day">
                <input
                  type="date"
                  value={params.exit_date || ""}
                  onChange={(e) => setParams({ ...params, exit_date: e.target.value })}
                />
              </Field>
              <Field label="Reason" hint="Recorded against any bond breach">
                <input
                  value={params.reason || ""}
                  onChange={(e) => setParams({ ...params, reason: e.target.value })}
                />
              </Field>
            </>
          )}

          {kind === "TRANSFER" && (
            <Field label="Move to department">
              <input
                value={params.department || ""}
                onChange={(e) => setParams({ ...params, department: e.target.value })}
              />
            </Field>
          )}

          {kind === "BOND_ISSUE" && (
            <>
              <Field label="Bond template">
                <select
                  value={params.template || ""}
                  onChange={(e) => setParams({ ...params, template: Number(e.target.value) })}
                >
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Starting">
                <input
                  type="date"
                  value={params.start_date || ""}
                  onChange={(e) => setParams({ ...params, start_date: e.target.value })}
                />
              </Field>
            </>
          )}
        </div>

        <button className="primary" style={{ marginTop: 12 }} onClick={runPreview} disabled={busy}>
          {busy ? "Working" : "Preview"}
        </button>
      </div>

      {preview && (
        <Stagger>
          <PreviewCard
            preview={preview}
            kind={kind}
            confirm={confirm}
            setConfirm={setConfirm}
            phrase={phrase}
            busy={busy}
            onExecute={execute}
            onCancel={() => setPreview(null)}
          />
        </Stagger>
      )}

      <HistoryCard history={history} />
    </div>
  );
}

// ---------------------------------------------------------------------------

function PreviewCard({ preview, kind, confirm, setConfirm, phrase, busy, onExecute, onCancel }) {
  const t = preview.totals || {};
  const rowsList = preview.rows || [];

  return (
    <div className="card">
      <div className="card-title">Nothing has happened yet</div>
      <div className="card-sub">{preview.criteria_description}</div>

      <div className="row" style={{ gap: 24, marginTop: 12, flexWrap: "wrap" }}>
        <Stat label="People" value={t.people} />
        {kind === "INCREMENT" && (
          <>
            <Stat label="Payroll now" value={money(t.old_monthly)} />
            <Stat label="Payroll after" value={money(t.new_monthly)} />
            <Stat label="Extra per month" value={money(t.monthly_delta)} accent />
            <Stat label="Extra per year" value={money(t.annual_delta)} />
          </>
        )}
        {kind === "EXIT" && (
          <>
            <Stat label="Monthly payroll released" value={money(t.monthly_payroll_released)} />
            <Stat label="Bonds affected" value={t.bonds_affected} />
            <Stat label="Bonds breached" value={t.bonds_breached} />
            <Stat label="Recovery due" value={money(t.recovery_due)} accent />
          </>
        )}
        {kind === "BOND_ISSUE" && (
          <>
            <Stat label="Already bonded" value={t.already_bonded} />
            <Stat label="Term, months" value={t.term_months} />
            <Stat label="Total recovery cover" value={money(t.total_recovery)} accent />
          </>
        )}
      </div>

      {preview.note && (
        <div className="alert" style={{ marginTop: 12 }}>
          {preview.note}
        </div>
      )}

      <div className="table-wrap" style={{ marginTop: 10 }}>
        <table>
          <thead>
            <tr>
              <th>Employee</th>
              {kind === "INCREMENT" && (
                <>
                  <th className="num">Now</th>
                  <th className="num">After</th>
                  <th className="num">Change</th>
                </>
              )}
              {kind === "EXIT" && (
                <>
                  <th className="num">Wage</th>
                  <th className="num">Notice</th>
                  <th>Bond</th>
                  <th className="num">Recovery</th>
                </>
              )}
              {kind === "TRANSFER" && (
                <>
                  <th>From</th>
                  <th>To</th>
                </>
              )}
              {kind === "BOND_ISSUE" && (
                <>
                  <th>Term</th>
                  <th className="num">Recovery</th>
                  <th />
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {rowsList.slice(0, 40).map((r, i) => (
              // Rows arrive in sequence for the first dozen. Past that the
              // stagger stops reading as "these are arriving" and starts
              // reading as "this table is slow".
              <tr
                key={r.employee_id}
                className={i < 12 ? "stagger-row" : undefined}
                style={{
                  ...(r.skip ? { opacity: 0.45 } : null),
                  ...(i < 12 ? { animationDelay: `${i * 28}ms` } : null),
                }}
              >
                <td>
                  {r.name}
                  <div className="tiny faint">{r.department || r.email}</div>
                </td>
                {kind === "INCREMENT" && (
                  <>
                    <td className="num mono">{money(r.old_wage)}</td>
                    <td className="num mono">{money(r.new_wage)}</td>
                    <td className="num mono" style={{ color: "var(--green)" }}>
                      +{money(r.delta)}
                    </td>
                  </>
                )}
                {kind === "EXIT" && (
                  <>
                    <td className="num mono">{money(r.wage)}</td>
                    <td className="num mono">{r.notice_days}d</td>
                    <td className="tiny">
                      {r.bond ? (
                        <>
                          ends {r.bond.ends}
                          <div className="faint">{r.bond.months_remaining} months left</div>
                        </>
                      ) : (
                        <span className="faint">none</span>
                      )}
                    </td>
                    <td className="num mono">
                      {r.bond ? (
                        <span style={{ color: r.bond.breached ? "var(--red)" : undefined }}>
                          {money(r.bond.recovery)}
                        </span>
                      ) : (
                        <span className="faint">&mdash;</span>
                      )}
                    </td>
                  </>
                )}
                {kind === "TRANSFER" && (
                  <>
                    <td>{r.department || <span className="faint">&mdash;</span>}</td>
                    <td>{r.new_department}</td>
                  </>
                )}
                {kind === "BOND_ISSUE" && (
                  <>
                    <td className="mono tiny">
                      {r.start} to {r.end}
                    </td>
                    <td className="num mono">{money(r.recovery)}</td>
                    <td className="tiny faint">{r.skip ? "already bonded" : ""}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(preview.skipped || []).length > 0 && (
        <div className="tiny faint" style={{ marginTop: 8 }}>
          Skipped: {preview.skipped.map((s) => `${s.employee} (${s.reason})`).join(", ")}
        </div>
      )}

      <div className="row" style={{ gap: 8, marginTop: 14, alignItems: "flex-end" }}>
        <Field
          label={`Type "${phrase}" to confirm`}
          hint="This cannot be undone from the interface."
        >
          <input value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        <button
          className="primary"
          disabled={busy || confirm.trim().toLowerCase() !== phrase || !t.people}
          onClick={onExecute}
        >
          {busy ? "Running" : "Run it"}
        </button>
        <button className="ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  // Counts up when it is a bare number. A formatted rupee figure is left
  // alone -- animating the digits of a total somebody is about to approve
  // makes it harder to read, which is the opposite of the point.
  const numeric = typeof value === "number";
  return (
    <div>
      <div className="bignum" style={accent ? { color: "var(--primary)" } : undefined}>
        {value === null || value === undefined
          ? "—"
          : numeric
          ? <CountUp to={value} />
          : value}
      </div>
      <div className="tiny faint">{label}</div>
    </div>
  );
}

function HistoryCard({ history }) {
  const list = rows(history.data);
  if (history.loading) return <Loading />;
  return (
    <div className="card">
      <div className="card-title">What has been run</div>
      <div className="table-wrap" style={{ marginTop: 8 }}>
        <table>
          <thead>
            <tr>
              <th>Operation</th>
              <th>Who it hit</th>
              <th>State</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && (
              <tr>
                <td colSpan={4}>
                  <div className="empty">Nothing has been run yet.</div>
                </td>
              </tr>
            )}
            {list.map((op) => (
              <tr key={op.id}>
                <td>
                  {op.name || op.kind}
                  <div className="tiny faint">{op.criteria_description}</div>
                </td>
                <td className="tiny">{op.segment_name || "Everyone"}</td>
                <td>
                  <span
                    className={`badge ${
                      op.state === "EXECUTED" ? "green" : op.state === "FAILED" ? "red" : "amber"
                    }`}
                  >
                    {op.state}
                  </span>
                </td>
                <td className="tiny mono">
                  {op.result && Object.keys(op.result).length
                    ? Object.entries(op.result)
                        .filter(([, v]) => typeof v === "number")
                        .map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`)
                        .join(", ")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
