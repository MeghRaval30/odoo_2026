// Closing the gaps between what a file has and what the software needs.
//
// This is the second half of the import, and it is the half that decides
// whether the feature is useful. Reading a spreadsheet well is table stakes;
// what a real migration actually runs into is that the spreadsheet is
// *incomplete* -- HR has names and pay, finance has the bank details in a file
// of its own, and nobody has issued employee codes yet.
//
// So the gaps are shown as a checklist rather than as an error. Each line is
// something the operator can resolve without leaving the screen, and it turns
// from amber to green when they do. Nothing here guesses: a second file is
// joined on a key that was measured, and a numbering scheme is previewed
// against real rows before a single code is issued.

import { useRef, useState } from "react";
import { api } from "../api";
import { Field } from "./ui";
import { ConfidenceBar, CountUp, FieldChip, Pulse, Stagger, ThinkingStream } from "./ai";

// ---------------------------------------------------------------------------

/**
 * What the file does not supply, and what can be done about each one.
 *
 * `required` gaps block the import; the rest are worth offering because a
 * payrun warns about a missing bank account every month until somebody fixes
 * it, and fixing it now costs one file.
 */
export function GapsCard({
  plan, fields, hue, onEnrich, onDeriveEmail, deriveOn, codePolicy,
  onOpenCodes, busy,
}) {
  const sourced = new Set();
  for (const column of plan.columns || []) {
    if (column.field) sourced.add(column.field);
  }
  for (const entry of plan.enrichments || []) {
    for (const field of entry.fields || []) sourced.add(field);
  }
  if (sourced.has("full_name")) sourced.add("first_name");

  const missing = new Set(plan.missing_required || []);
  const label = (key) => fields.find((f) => f.key === key)?.label || key;

  // Worth offering, in the order somebody would care about them.
  const WANTED = ["work_email", "bank_account_number", "bank_ifsc",
                  "pan_number", "employee_code"];
  const gaps = WANTED.filter((key) => !sourced.has(key));

  const codesResolved = sourced.has("employee_code") ||
    (codePolicy && codePolicy.mode !== "keep");

  if (gaps.length === 0 && codesResolved) {
    return (
      <div className="card">
        <div className="card-title">Nothing is missing</div>
        <div className="tiny faint" style={{ marginTop: 6 }}>
          Every field this software needs has a source.
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Complete the data</div>
      <div className="card-sub">
        What this file does not carry. Each one can be filled here.
      </div>

      <div className="gaps" style={{ marginTop: 10 }}>
        {gaps.map((key, i) => {
          const blocking = missing.has(key) ||
            (key === "work_email" && missing.has("work_email"));
          const emailFixed = key === "work_email" && deriveOn;
          return (
            <Stagger key={key} index={i}>
              <div className={`gap${emailFixed ? " done" : blocking ? " blocking" : ""}`}>
                <span className="gap-mark">{emailFixed ? "✓" : blocking ? "!" : "•"}</span>
                <span className="gap-what">
                  <b>{label(key)}</b>
                  <span className="tiny faint">
                    {key === "work_email" &&
                      (emailFixed
                        ? "Building addresses from each person's name"
                        : "Required. It identifies the record.")}
                    {key === "bank_account_number" &&
                      "A payrun warns every month until this is set."}
                    {key === "bank_ifsc" && "Needed to pay into the account."}
                    {key === "pan_number" && "Needed for tax reporting."}
                    {key === "employee_code" &&
                      "Not in this file. One can be generated."}
                  </span>
                </span>
                <span className="gap-do">
                  {key === "work_email" && (
                    <button
                      className={emailFixed ? "ghost sm" : "primary sm"}
                      onClick={onDeriveEmail}
                      disabled={busy}
                    >
                      {emailFixed ? "Undo" : "Build from names"}
                    </button>
                  )}
                  {key === "employee_code" && (
                    <button className="ghost sm" onClick={onOpenCodes} disabled={busy}>
                      Choose numbering
                    </button>
                  )}
                  {key !== "work_email" && key !== "employee_code" && (
                    <button className="ghost sm" onClick={onEnrich} disabled={busy}>
                      Fetch from a file
                    </button>
                  )}
                </span>
              </div>
            </Stagger>
          );
        })}
      </div>

      {(plan.enrichments || []).length === 0 && gaps.some((g) =>
        g.startsWith("bank") || g === "pan_number") && (
        <div className="tiny faint" style={{ marginTop: 10, lineHeight: 1.55 }}>
          Bank details usually live in a separate spreadsheet. Add it and the
          rows will be matched up on whichever column the two files share.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

/**
 * A second file, and the join it makes with the first.
 *
 * The join is the interesting part and so it is the part that is shown: which
 * two columns were matched on, how confident that is, and the three numbers
 * that tell an operator whether to trust it -- matched, not found, and unused.
 */
export function EnrichPanel({ onClose, onAdded, runId, fields, hue }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const input = useRef(null);

  const label = (key) => fields.find((f) => f.key === key)?.label || key;

  function send(file) {
    if (!file) return;
    setBusy(true);
    setError(null);
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const body = {
          filename: file.name,
          content_b64: String(reader.result).split(",")[1] || "",
        };
        setResult(await api.post(`/api/intel/runs/${runId}/enrich/`, body));
      } catch (e) {
        setError(e.message);
      } finally {
        setBusy(false);
      }
    };
    reader.readAsDataURL(file);
  }

  if (result) {
    const join = result.join || {};
    return (
      <Stagger>
        <div className="card">
          <div className="row between">
            <span className="card-title" style={{ margin: 0 }}>
              {result.filename}
            </span>
            <span className="badge green">joined</span>
          </div>

          <div className="joinviz" style={{ marginTop: 12 }}>
            <div className="joinside">
              <div className="tiny faint">This file</div>
              <div className="joinkey">{join.primary_header}</div>
            </div>
            <div className="joinlink">
              <span className="joinline" />
              <span className="tiny faint">matched on</span>
              <ConfidenceBar value={join.confidence} />
            </div>
            <div className="joinside right">
              <div className="tiny faint">{result.filename}</div>
              <div className="joinkey">{join.supplement_header}</div>
            </div>
          </div>

          <div style={{ marginTop: 10 }}>
            <ThinkingStream text={join.reason || ""} />
          </div>

          <div className="row" style={{ gap: 26, marginTop: 14, flexWrap: "wrap" }}>
            <JoinStat n={join.matched} label="people matched" tone="green" />
            <JoinStat n={join.unmatched} label="not in the second file" tone={join.unmatched ? "amber" : null} />
            <JoinStat n={join.unused} label="in it and not here" tone={join.unused ? "amber" : null} />
          </div>

          {result.unmatched_examples?.length > 0 && (
            <div className="tiny faint" style={{ marginTop: 10 }}>
              No bank details for{" "}
              {result.unmatched_examples.map((u) => u.label || u.key).join(", ")}.
              They import without one and a payrun will warn.
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <div className="tiny faint" style={{ marginBottom: 5 }}>
              Fields this file fills
            </div>
            <div className="row" style={{ gap: 5, flexWrap: "wrap" }}>
              {(result.fields || []).map((f) => (
                <FieldChip key={f} label={label(f)} hue={hue(f)} />
              ))}
              {(result.fields || []).length === 0 && (
                <span className="tiny faint">
                  Nothing new — the first file already had all of it.
                </span>
              )}
            </div>
          </div>

          <div className="row" style={{ gap: 8, marginTop: 14 }}>
            <button className="primary" onClick={() => onAdded(result)}>
              Use this
            </button>
            <button className="ghost" onClick={onClose}>
              Cancel
            </button>
          </div>
        </div>
      </Stagger>
    );
  }

  return (
    <div className="card">
      <div className="row between">
        <span className="card-title" style={{ margin: 0 }}>
          Add a second file
        </span>
        <button className="ghost sm" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="card-sub">
        It needs one column in common with the first — a staff id, an email or
        a name. Which one is worked out from the values, not from the heading.
      </div>

      {error && <div className="alert error" style={{ marginTop: 10 }}>{error}</div>}

      {busy ? (
        <div className="row" style={{ gap: 9, marginTop: 16, alignItems: "center" }}>
          <Pulse />
          <span className="tiny faint">
            Reading it, and looking for a column the two files share
          </span>
        </div>
      ) : (
        <label
          className={`dropzone${dragging ? " over" : ""}`}
          style={{ display: "block", marginTop: 12 }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            send(e.dataTransfer.files?.[0]);
          }}
        >
          <input
            ref={input}
            type="file"
            accept=".csv,.tsv,.txt,.xlsx,.xlsm"
            style={{ display: "none" }}
            onChange={(e) => send(e.target.files?.[0])}
          />
          <div style={{ fontSize: 13 }}>Drop the second spreadsheet here</div>
          <div className="tiny faint" style={{ marginTop: 4 }}>
            Nothing is written. It is matched against the first and shown to you.
          </div>
        </label>
      )}
    </div>
  );
}

function JoinStat({ n, label, tone }) {
  return (
    <div>
      <div
        className="bignum"
        style={tone ? { color: `var(--${tone})` } : undefined}
      >
        <CountUp to={n || 0} />
      </div>
      <div className="tiny faint">{label}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------

const PRESETS = [
  { label: "EMP/2024/0001", policy: { mode: "generate", prefix: "EMP", separator: "/", include_year: true, year_source: "joining", width: 4 } },
  { label: "EMP-0001", policy: { mode: "generate", prefix: "EMP", separator: "-", include_year: false, width: 4 } },
  { label: "STAFF/2026/001", policy: { mode: "generate", prefix: "STAFF", separator: "/", include_year: true, year_source: "current", width: 3 } },
];

/**
 * How imported people are numbered.
 *
 * Asked rather than assumed, because the file's own ids are almost never the
 * ones you want to keep -- `FF-101` is the old employer's numbering -- and a
 * scheme is very cheap to choose now and very expensive to change once
 * payslips carry it. Previewed against real rows because the year comes from
 * each person's joining date.
 */
export function CodePolicyCard({ runId, policy, onChange, onClose, hasSourceCodes }) {
  const [form, setForm] = useState(policy || {
    mode: "generate", prefix: "EMP", separator: "/", include_year: true,
    year_source: "joining", width: 4, start: 1,
  });
  const [examples, setExamples] = useState([]);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function apply(next) {
    setForm(next);
    setBusy(true);
    try {
      const data = await api.post(`/api/intel/runs/${runId}/code-policy/`, {
        policy: next,
      });
      setExamples(data.examples || []);
      setDescription(data.description || "");
      onChange?.(data.policy);
    } catch {
      setExamples([]);
    } finally {
      setBusy(false);
    }
  }

  const set = (key, value) => apply({ ...form, [key]: value });

  return (
    <Stagger>
      <div className="card">
        <div className="row between">
          <span className="card-title" style={{ margin: 0 }}>
            Employee numbering
          </span>
          {onClose && (
            <button className="ghost sm" onClick={onClose}>
              Close
            </button>
          )}
        </div>
        <div className="card-sub">
          {hasSourceCodes
            ? "This file has its own ids. Keep them, or issue new ones."
            : "This file has no employee codes. They will be generated."}
        </div>

        <div className="row" style={{ gap: 6, marginTop: 10, flexWrap: "wrap" }}>
          {hasSourceCodes && (
            <button
              className={form.mode === "keep" ? "primary sm" : "ghost sm"}
              onClick={() => apply({ ...form, mode: "keep" })}
            >
              Keep the file's ids
            </button>
          )}
          <button
            className={form.mode === "generate" ? "primary sm" : "ghost sm"}
            onClick={() => apply({ ...form, mode: "generate" })}
          >
            Generate to a pattern
          </button>
          <button
            className={form.mode === "auto" ? "primary sm" : "ghost sm"}
            onClick={() => apply({ ...form, mode: "auto" })}
          >
            Use the system default
          </button>
        </div>

        {form.mode === "generate" && (
          <>
            <div className="row" style={{ gap: 5, marginTop: 10, flexWrap: "wrap" }}>
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  className="tchip"
                  onClick={() => apply({ ...form, ...p.policy })}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div
              className="grid"
              style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 9, marginTop: 10 }}
            >
              <Field label="Prefix">
                <input
                  value={form.prefix}
                  maxLength={12}
                  onChange={(e) => setForm({ ...form, prefix: e.target.value })}
                  onBlur={(e) => set("prefix", e.target.value)}
                />
              </Field>
              <Field label="Separator">
                <select
                  value={form.separator}
                  onChange={(e) => set("separator", e.target.value)}
                >
                  <option value="/">slash</option>
                  <option value="-">dash</option>
                  <option value="_">underscore</option>
                  <option value="">none</option>
                </select>
              </Field>
              <Field label="Year">
                <select
                  value={form.include_year ? form.year_source : "none"}
                  onChange={(e) =>
                    apply(
                      e.target.value === "none"
                        ? { ...form, include_year: false }
                        : { ...form, include_year: true, year_source: e.target.value }
                    )
                  }
                >
                  <option value="joining">from joining date</option>
                  <option value="current">this year</option>
                  <option value="none">no year</option>
                </select>
              </Field>
              <Field label="Digits">
                <select
                  value={form.width}
                  onChange={(e) => set("width", Number(e.target.value))}
                >
                  {[3, 4, 5, 6].map((w) => (
                    <option key={w} value={w}>{w}</option>
                  ))}
                </select>
              </Field>
            </div>
          </>
        )}

        <div style={{ marginTop: 10 }}>
          <div className="tiny faint" style={{ marginBottom: 5 }}>
            {busy ? "Working it out" : description || "What the first rows will get"}
          </div>
          <div className="row" style={{ gap: 5, flexWrap: "wrap" }}>
            {examples.map((code, i) => (
              <span key={code} className="codechip" style={{ animationDelay: `${i * 40}ms` }}>
                {code}
              </span>
            ))}
            {!examples.length && !busy && (
              <span className="tiny faint">
                {form.mode === "keep"
                  ? "The file's own ids are kept as they are."
                  : "Numbered EMP/<year>/0001, the way the rest of the system does."}
              </span>
            )}
          </div>
        </div>
      </div>
    </Stagger>
  );
}
