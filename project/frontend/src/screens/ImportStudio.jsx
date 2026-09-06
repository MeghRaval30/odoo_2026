// The import studio.
//
// Five stages: choose a file, watch it get read, review the plan, preview what
// will change, import. The middle three are the product.
//
// The design question this screen answers is "why should anyone trust an
// automatic import". The answer is not accuracy -- it will sometimes be wrong.
// The answer is that every decision is visible before anything is written, and
// every one of them is editable. So the analysis is streamed rather than
// awaited, the reasoning behind each mapping is kept on screen, and the
// import button is the fifth thing you press, not the first.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, auth } from "../api";
import { ErrorBox, Loading, Modal, PageHead } from "../components/ui";
import SheetGrid from "../components/SheetGrid";
import {
  ConfidenceBar, CountUp, DiffCell, FieldChip, LlmPill, Pulse, Stagger,
  ThinkingStream, TransformRow, VoteStack, hueFor, hueVar,
} from "../components/ai";
import { CodePolicyCard, EnrichPanel, GapsCard } from "../components/ImportGaps";
import { navigate } from "../lib/router";

const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Read a Server-Sent Events stream.
 *
 * EventSource cannot send an Authorization header, and this API is token
 * authenticated, so the stream is consumed by hand: fetch, take the reader,
 * decode, split on the blank line that terminates an SSE frame, and keep the
 * remainder in the buffer because a frame can arrive in two chunks.
 */
async function readStream(path, onEvent, signal) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Token ${auth.token}` },
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`The analysis could not be started (${response.status}).`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {
        // A frame we cannot parse is not worth killing the run over; the
        // stream always ends with either a done or an error event.
      }
    }
  }
}

export default function ImportStudio() {
  const [health, setHealth] = useState(null);
  const [fields, setFields] = useState([]);
  const [stage, setStage] = useState("choose");
  const [error, setError] = useState(null);

  const [source, setSource] = useState(null);
  const [grid, setGrid] = useState(null);
  const [runId, setRunId] = useState(null);

  const [events, setEvents] = useState([]);
  const [progress, setProgress] = useState(0);
  const [columnState, setColumnState] = useState({});
  const [structure, setStructure] = useState(null);
  const [modelCard, setModelCard] = useState(null);
  const [focus, setFocus] = useState(null);
  const [plan, setPlan] = useState(null);
  const [elapsed, setElapsed] = useState(null);

  const [preview, setPreview] = useState(null);
  const [applyFixes, setApplyFixes] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);
  const [dragging, setDragging] = useState(false);

  const abort = useRef(null);

  // The model costs about eleven seconds to load onto the card. Asking for it
  // when the screen opens means that cost is paid while somebody is choosing a
  // file, rather than while they are watching a progress bar.
  useEffect(() => {
    api
      .get("/api/intel/health/", { warm: "1" })
      .then((d) => {
        setHealth(d.llm);
        setFields(d.fields || []);
      })
      .catch((e) => setError(e.message));
    return () => abort.current?.abort();
  }, []);

  // Filling the gaps: a second file, and how people are numbered. Both live
  // on the plan, so both survive a reload and are applied by the same preview
  // the operator approves.
  const [enriching, setEnriching] = useState(false);
  const [showCodes, setShowCodes] = useState(false);
  const [codePolicy, setCodePolicy] = useState(null);

  const hue = useCallback((key) => hueFor(key, fields), [fields]);
  const labelFor = useCallback(
    (key) => fields.find((f) => f.key === key)?.label || key,
    [fields]
  );

  // -- loading a file ---------------------------------------------------

  async function ingest(promise) {
    setError(null);
    setBusy(true);
    try {
      const src = await promise;
      setSource(src);
      setGrid(src.grid);
      const run = await api.post("/api/intel/runs/", { source: src.id });
      setRunId(run.id);
      startAnalysis(run.id);
    } catch (e) {
      setError(e.message);
      setStage("choose");
    } finally {
      setBusy(false);
    }
  }

  function loadFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = String(reader.result).split(",")[1] || "";
      ingest(
        api.post("/api/intel/sources/", {
          filename: file.name,
          content_b64: b64,
        })
      );
    };
    reader.readAsDataURL(file);
  }

  // -- the analysis -----------------------------------------------------

  function startAnalysis(id) {
    setStage("analyzing");
    setEvents([]);
    setColumnState({});
    setStructure(null);
    setModelCard(null);
    setFocus(null);
    setProgress(0);

    const controller = new AbortController();
    abort.current = controller;

    readStream(
      `/api/intel/runs/${id}/analyze/`,
      (event) => {
        setProgress(event.progress ?? 0);
        setEvents((prev) => [...prev, event].slice(-140));

        if (event.stage === "structure") {
          setStructure(event.payload);
        } else if (event.stage === "profiling") {
          const i = event.payload?.index;
          setColumnState((prev) => ({
            ...prev,
            [i]: { ...(prev[i] || {}), pulsing: true },
          }));
        } else if (event.stage === "model_start") {
          setModelCard(event.payload);
        } else if (event.stage === "column") {
          const col = event.payload;
          setColumnState((prev) => ({
            ...prev,
            [col.index]: {
              field: col.field,
              hue: hueFor(col.field, fields),
              decision: col.decision,
              confidence: col.confidence,
              decided: true,
              pulsing: false,
            },
          }));
          setFocus(col);
        } else if (event.stage === "done") {
          setPlan(event.payload?.plan || null);
          setElapsed(event.payload?.elapsed_ms ?? null);
          // A short beat so the last column's reason finishes typing rather
          // than being replaced mid-word by the next screen.
          setTimeout(() => setStage("plan"), 700);
        } else if (event.stage === "error") {
          setError(event.message);
          setStage("choose");
        }
      },
      controller.signal
    ).catch((e) => {
      if (e.name === "AbortError") return;
      setError(e.message);
      setStage("choose");
    });
  }

  // Once the plan exists the grid is coloured from it rather than from the
  // stream, so an operator's edits are reflected immediately.
  useEffect(() => {
    if (!plan) return;
    const next = {};
    for (const col of plan.columns || []) {
      next[col.index] = {
        field: col.field,
        hue: hueFor(col.field, fields),
        decision: col.decision,
        confidence: col.confidence,
        decided: true,
      };
    }
    setColumnState(next);
  }, [plan, fields]);

  // -- editing ----------------------------------------------------------

  async function remap(index, field) {
    setEditing(null);
    try {
      setPlan(await api.patch(`/api/intel/runs/${runId}/plan/`, { column: index, field }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function remapValue(column, from, to) {
    try {
      setPlan(
        await api.patch(`/api/intel/runs/${runId}/plan/`, {
          value_map: { column, pairs: { [from]: to } },
        })
      );
    } catch (e) {
      setError(e.message);
    }
  }

  async function runPreview(fixes = applyFixes) {
    setBusy(true);
    setError(null);
    try {
      const data = await api.post(`/api/intel/runs/${runId}/preview/`, {
        apply_fixes: fixes,
      });
      setPreview(data);
      setStage("preview");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.post(`/api/intel/runs/${runId}/commit/`, {
        apply_fixes: applyFixes,
      });
      setResult(data);
      setStage("done");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function restart() {
    abort.current?.abort();
    setStage("choose");
    setSource(null);
    setGrid(null);
    setPlan(null);
    setPreview(null);
    setResult(null);
    setRunId(null);
    setApplyFixes([]);
    setError(null);
  }

  if (!auth.has("data.import")) {
    return (
      <div className="page">
        <div className="card">
          <div className="empty">Not available for this account.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHead
        title="Data import"
        sub={
          {
            choose: "Bring a roster in from whatever it lives in today",
            analyzing: "Reading the file",
            plan: "Check what each column became",
            preview: "Nothing has been written yet",
            done: "Import complete",
          }[stage]
        }
      >
        <LlmPill health={health} onClick={() => navigate("/ai-setup")} />
        {stage !== "choose" && (
          <button className="ghost" onClick={restart}>
            Start over
          </button>
        )}
      </PageHead>

      <ErrorBox error={error} />

      {stage === "choose" && (
        <ChooseStage
          busy={busy}
          dragging={dragging}
          setDragging={setDragging}
          onFile={loadFile}
          health={health}
        />
      )}

      {(stage === "analyzing" || stage === "plan") && grid && (
        <div className="studio-split">
          <div className="stack">
            {stage === "analyzing" && (
              <div className="card">
                <div className="progress">
                  <i style={{ width: `${Math.round(progress * 100)}%` }} />
                </div>
                <div className="row between" style={{ marginTop: 8 }}>
                  <span className="row" style={{ gap: 7, alignItems: "center" }}>
                    <Pulse />
                    <span>{events[events.length - 1]?.message || "Starting"}</span>
                  </span>
                  <span className="tiny faint mono">
                    {Math.round(progress * 100)}%
                  </span>
                </div>
                {structure && (
                  <div className="tiny faint" style={{ marginTop: 6 }}>
                    {(structure.notes || []).join(" ")}
                  </div>
                )}
              </div>
            )}

            <SheetGrid
              headers={grid.headers}
              rows={grid.rows}
              rawRows={grid.raw_rows}
              headerRowIndex={grid.header_row_index}
              junkIdentified={Boolean(structure) || stage === "plan"}
              columnState={columnState}
              scanning={stage === "analyzing" && progress < 0.45}
              fields={fields}
              onHeaderClick={stage === "plan" ? (i) => setEditing(i) : undefined}
            />

            {stage === "plan" && plan && (
              <>
                <GapsCard
                  plan={plan}
                  fields={fields}
                  hue={hue}
                  busy={busy}
                  deriveOn={applyFixes.includes("derive_email")}
                  codePolicy={codePolicy || plan.code_policy}
                  onEnrich={() => setEnriching(true)}
                  onOpenCodes={() => setShowCodes(true)}
                  onDeriveEmail={() =>
                    setApplyFixes((prev) =>
                      prev.includes("derive_email")
                        ? prev.filter((f) => f !== "derive_email")
                        : [...prev, "derive_email"]
                    )
                  }
                />

                {enriching && (
                  <EnrichPanel
                    runId={runId}
                    fields={fields}
                    hue={hue}
                    onClose={() => setEnriching(false)}
                    onAdded={async () => {
                      setEnriching(false);
                      // The plan gained a source, so re-read it rather than
                      // patching a copy -- the server recomputed which
                      // required fields are still missing.
                      try {
                        setPlan(await api.get(`/api/intel/runs/${runId}/plan/`));
                      } catch (e) {
                        setError(e.message);
                      }
                    }}
                  />
                )}

                {(plan.enrichments || []).map((entry, i) => (
                  <SecondFileCard
                    key={`${entry.source_id}-${i}`}
                    entry={entry}
                    labelFor={labelFor}
                    hue={hue}
                    onRemove={async () => {
                      try {
                        await api.delete(`/api/intel/runs/${runId}/enrich/${i}/`);
                        setPlan(await api.get(`/api/intel/runs/${runId}/plan/`));
                      } catch (e) {
                        setError(e.message);
                      }
                    }}
                  />
                ))}

                {showCodes && (
                  <CodePolicyCard
                    runId={runId}
                    policy={codePolicy || plan.code_policy}
                    hasSourceCodes={(plan.columns || []).some(
                      (c) => c.field === "employee_code"
                    )}
                    onChange={setCodePolicy}
                    onClose={() => setShowCodes(false)}
                  />
                )}

                <PlanDetail
                  plan={plan}
                  fields={fields}
                  labelFor={labelFor}
                  hue={hue}
                  onRemap={remap}
                  onRemapValue={remapValue}
                />
              </>
            )}
          </div>

          <div className="studio-rail">
            {stage === "analyzing" && (
              <AnalysisRail
                modelCard={modelCard}
                focus={focus}
                fields={fields}
                labelFor={labelFor}
                hue={hue}
              />
            )}
            {stage === "plan" && plan && (
              <PlanRail
                plan={plan}
                fields={fields}
                hue={hue}
                elapsed={elapsed}
                busy={busy}
                onPreview={() => runPreview()}
              />
            )}
          </div>
        </div>
      )}

      {stage === "preview" && preview && (
        <PreviewStage
          preview={preview}
          labelFor={labelFor}
          busy={busy}
          applyFixes={applyFixes}
          onToggleFix={(fix) => {
            const next = applyFixes.includes(fix)
              ? applyFixes.filter((f) => f !== fix)
              : [...applyFixes, fix];
            setApplyFixes(next);
            runPreview(next);
          }}
          onBack={() => setStage("plan")}
          onCommit={commit}
        />
      )}

      {stage === "done" && result && (
        <DoneStage result={result} source={source} onAgain={restart} />
      )}

      {editing !== null && plan && (
        <Modal title={`Column: ${grid.headers[editing]}`} onClose={() => setEditing(null)}>
          <RemapForm
            column={(plan.columns || []).find((c) => c.index === editing)}
            fields={fields}
            onPick={(field) => remap(editing, field)}
          />
        </Modal>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

const HANDLES = [
  "A header that is not on the first row",
  "Column names in any wording — DOJ, Emp Naam, A/C No",
  "Dates in more than one format in the same column",
  "Rupees written as Rs 45,000, 72,000 or 38500/-",
  "A salary column that is annual where we store monthly",
  "Departments under another company's names",
  "Missing bank details, filled from a second file",
  "No employee codes, generated to a pattern you pick",
];

function ChooseStage({ busy, dragging, setDragging, onFile, health }) {
  if (busy) return <Loading />;
  return (
    <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 320px", gap: 14 }}>
      <div className="card">
        <div className="card-title">Bring a roster in</div>
        <div className="card-sub">
          Excel or CSV, in whatever shape it is already in. Nothing is written
          until you have seen what it will do and approved it.
        </div>
        <label
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
          style={{ display: "block", marginTop: 12, padding: "38px 18px" }}
        >
          <input
            type="file"
            accept=".csv,.tsv,.txt,.xlsx,.xlsm"
            style={{ display: "none" }}
            onChange={(e) => onFile(e.target.files?.[0])}
          />
          <div style={{ fontSize: 14 }}>
            Drop a spreadsheet here, or click to choose one
          </div>
          <div className="tiny faint" style={{ marginTop: 5 }}>
            .xlsx, .xlsm, .csv or .tsv
          </div>
        </label>

        {health && !health.available && (
          <div className="alert" style={{ marginTop: 12 }}>
            {health.message} Imports still run: columns are matched by a synonym
            dictionary and by the shape of the values, which handles most files.
            Unusual header names are where the local model earns its place.
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">What it copes with</div>
        <div className="stack" style={{ gap: 0, marginTop: 8 }}>
          {HANDLES.map((line, i) => (
            <Stagger key={line} index={i} step={35}>
              <div
                className="tiny"
                style={{
                  padding: "5px 0",
                  borderBottom: "1px solid var(--border)",
                  color: "var(--text-dim)",
                }}
              >
                {line}
              </div>
            </Stagger>
          ))}
        </div>
        <div className="tiny faint" style={{ marginTop: 10, lineHeight: 1.55 }}>
          Sample rosters to try this on are in <b>test-data/import/</b> in the
          repository. Open one in Excel first — they look like what a company
          actually hands you.
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function AnalysisRail({ modelCard, focus, fields, labelFor, hue }) {
  return (
    <>
      {modelCard && (
        <div className="card stagger">
          <div className="row" style={{ gap: 7, alignItems: "center" }}>
            <Pulse active={modelCard.available} />
            <span className="card-title" style={{ margin: 0 }}>
              {modelCard.available ? modelCard.model : "Rules only"}
            </span>
          </div>
          <div className="tiny faint" style={{ marginTop: 5 }}>
            {modelCard.available
              ? "Running on this machine. Column headers and three sample values " +
                "are sent to it; row data is not."
              : "No local model. Matching on the synonym dictionary and the " +
                "measured shape of each column."}
          </div>
        </div>
      )}

      {focus && (
        <div className="card stagger" key={focus.index}>
          <div className="row between">
            <span className="card-title" style={{ margin: 0 }}>
              {focus.header}
            </span>
            {focus.field ? (
              <FieldChip label={labelFor(focus.field)} hue={hue(focus.field)} />
            ) : (
              <span className="badge grey">not imported</span>
            )}
          </div>

          <div style={{ margin: "9px 0" }}>
            <ConfidenceBar value={focus.confidence} />
          </div>

          <VoteStack votes={focus.votes} fields={fields} />

          {focus.votes?.some((v) => v.voter === "model" && v.reason) && (
            <div style={{ marginTop: 9 }}>
              <ThinkingStream
                text={focus.votes.find((v) => v.voter === "model")?.reason || ""}
              />
            </div>
          )}

          {focus.note && (
            <div className="tiny faint" style={{ marginTop: 7 }}>
              {focus.note}
            </div>
          )}
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------

function PlanRail({ plan, fields, hue, elapsed, busy, onPreview }) {
  const claimed = useMemo(() => {
    const map = {};
    for (const c of plan.columns || []) if (c.field) map[c.field] = c;
    return map;
  }, [plan]);

  const s = plan.summary || {};
  const llm = plan.llm || {};

  // Which required fields are genuinely still missing is the server's answer,
  // not one recomputed here. It has to be: a mapped "Full name" satisfies both
  // halves of the name because splitting it is a transform, and a second copy
  // of that rule in the browser is a second copy that will drift. It did --
  // this legend reported First name as missing while the same plan's
  // missing_required was empty and the button beneath it was enabled.
  const missing = new Set(plan.missing_required || []);

  return (
    <>
      <div className="card">
        <div className="card-title">What happened</div>
        <div className="tiny" style={{ lineHeight: 1.7, marginTop: 6 }}>
          Read {s.columns} headers. Mapped {s.auto} automatically
          {s.review ? `, ${s.review} need a look` : ""}
          {s.unmapped ? `, ${s.unmapped} left out` : ""}.
        </div>
        <div className="tiny faint" style={{ marginTop: 6 }}>
          {llm.used
            ? `${llm.model} answered in ${(llm.latency_ms / 1000).toFixed(1)}s.`
            : `Rules only — ${llm.fallback_reason || "no local model"}.`}
          {elapsed ? ` Whole analysis ${(elapsed / 1000).toFixed(1)}s.` : ""}
        </div>
      </div>

      <div className="card">
        <div className="card-title">Where each field comes from</div>
        <div style={{ marginTop: 6 }}>
          {fields.map((f) => {
            const col = claimed[f.key];
            const absent = missing.has(f.key);
            // Show a field if a column claims it, or if it is required and
            // still unsatisfied. Everything else is noise on a screen whose
            // job is "what did my columns become".
            if (!col && !absent) return null;
            return (
              <div key={f.key} className={`legend-row${absent ? " missing" : ""}`}>
                <span
                  className="swatch"
                  style={{ background: col ? hueVar(hue(f.key)) : "var(--surface-3)" }}
                />
                <span>{f.label}</span>
                <span className="src">{col ? col.header : "still needed"}</span>
              </div>
            );
          })}
        </div>
        {(plan.missing_required || []).length > 0 && (
          <div className="alert error" style={{ marginTop: 9 }}>
            Still needed:{" "}
            {plan.missing_required
              .map((k) => fields.find((f) => f.key === k)?.label || k)
              .join(", ")}
            . Click a column header to map one.
          </div>
        )}
      </div>

      <button
        className="primary"
        disabled={busy || (plan.missing_required || []).length > 0}
        onClick={onPreview}
      >
        {busy ? "Working" : "Preview import"}
      </button>
    </>
  );
}

// ---------------------------------------------------------------------------

function PlanDetail({ plan, fields, labelFor, hue, onRemap, onRemapValue }) {
  const [openChip, setOpenChip] = useState({});
  const mapped = (plan.columns || []).filter((c) => c.field);

  return (
    <>
      <div className="card">
        <div className="card-title">What is done to each column</div>
        <div className="card-sub">
          These run in order, top to bottom. Click one to see it applied to real
          cells.
        </div>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Column</th>
                <th>Becomes</th>
                <th>Steps</th>
                <th>Example</th>
              </tr>
            </thead>
            <tbody>
              {mapped.map((c) => (
                <tr key={c.index}>
                  <td>{c.header}</td>
                  <td>
                    <FieldChip label={labelFor(c.field)} hue={hue(c.field)} />
                  </td>
                  <td>
                    <TransformRow
                      transforms={c.transforms}
                      activeId={openChip[c.index]}
                      onPick={(i) =>
                        setOpenChip((p) => ({ ...p, [c.index]: i }))
                      }
                    />
                    {openChip[c.index] != null && c.transforms?.[openChip[c.index]] && (
                      <div className="tiny faint" style={{ marginTop: 4 }}>
                        {c.transforms[openChip[c.index]].detail}
                      </div>
                    )}
                  </td>
                  <td className="mono tiny">
                    <DiffCell
                      before={(c.sample_before || [])[0]}
                      after={(c.sample_after || [])[0]}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {(plan.value_maps || []).map((vm) => (
        <div className="card" key={vm.column}>
          <div className="card-title">
            {labelFor(vm.field)} — matching their words to ours
          </div>
          <div className="card-sub">
            Values already here are reused. Anything new is created on import.
            Edit any of them.
          </div>
          <table className="vmap" style={{ marginTop: 8 }}>
            <tbody>
              {vm.pairs.map((p) => (
                <tr key={p.from}>
                  <td style={{ width: "38%" }}>{p.from}</td>
                  <td style={{ width: 18, color: "var(--text-faint)" }}>&rarr;</td>
                  <td>
                    <input
                      defaultValue={p.to}
                      onBlur={(e) =>
                        e.target.value !== p.to &&
                        onRemapValue(vm.column, p.from, e.target.value)
                      }
                    />
                  </td>
                  <td style={{ width: 88, textAlign: "right" }}>
                    <span className={`badge ${p.status === "matched" ? "green" : "amber"}`}>
                      {p.status === "matched" ? "exists" : "new"}
                    </span>
                  </td>
                  <td className="tiny faint" style={{ width: 66, textAlign: "right" }}>
                    {p.source}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------

/** A second file already attached: what it joins on and what it fills. */
function SecondFileCard({ entry, labelFor, hue, onRemove }) {
  const join = entry.join || {};
  return (
    <Stagger>
      <div className="card">
        <div className="row between">
          <span className="card-title" style={{ margin: 0 }}>
            Second file — {entry.filename}
          </span>
          <button className="ghost sm" onClick={onRemove}>
            Remove
          </button>
        </div>
        <div className="card-sub">
          Matched on <b>{join.primary_header}</b> to{" "}
          <b>{join.supplement_header}</b>. {join.matched} of{" "}
          {(join.matched || 0) + (join.unmatched || 0)} people found.
        </div>
        <div className="row" style={{ gap: 5, marginTop: 8, flexWrap: "wrap" }}>
          {(entry.fields || []).map((f) => (
            <FieldChip key={f} label={labelFor(f)} hue={hue(f)} />
          ))}
        </div>
        {join.unmatched > 0 && (
          <div className="tiny faint" style={{ marginTop: 8 }}>
            {join.unmatched} {join.unmatched === 1 ? "person is" : "people are"}{" "}
            not in it
            {entry.unmatched_examples?.length
              ? `: ${entry.unmatched_examples.map((u) => u.label || u.key).join(", ")}`
              : ""}
            . They import without those fields.
          </div>
        )}
      </div>
    </Stagger>
  );
}

function RemapForm({ column, fields, onPick }) {
  if (!column) return null;
  const grouped = fields.reduce((acc, f) => {
    (acc[f.group] = acc[f.group] || []).push(f);
    return acc;
  }, {});

  return (
    <div className="stack">
      <div className="tiny faint">{column.profile?.evidence}</div>
      <VoteStack votes={column.votes} fields={fields} />
      <div className="field" style={{ marginTop: 8 }}>
        <label>Import this column as</label>
        <select
          defaultValue={column.field || ""}
          onChange={(e) => onPick(e.target.value || null)}
        >
          <option value="">Do not import it</option>
          {Object.entries(grouped).map(([group, list]) => (
            <optgroup key={group} label={group}>
              {list.map((f) => (
                <option key={f.key} value={f.key}>
                  {f.label}
                  {f.required ? " (required)" : ""}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function PreviewStage({ preview, labelFor, busy, applyFixes, onToggleFix, onBack, onCommit }) {
  const c = preview.counts || {};
  const will = preview.will_create || {};
  const errors = (preview.issues || []).filter((i) => i.severity === "error");
  const warnings = (preview.issues || []).filter((i) => i.severity === "warning");
  const canDerive = errors.some((i) => i.auto_fix === "derive_email");

  const columns = useMemo(() => {
    const keys = new Set();
    for (const r of preview.records || []) {
      Object.keys(r.cells || {}).forEach((k) => keys.add(k));
    }
    return [...keys].slice(0, 7);
  }, [preview]);

  return (
    <div className="studio-split">
      <div className="stack">
        <div className="card">
          <div className="card-title">Before and after</div>
          <div className="card-sub">
            The first {(preview.records || []).length} rows, as they will be
            written. Nothing has been created yet.
          </div>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 34 }}>Row</th>
                  {columns.map((k) => (
                    <th key={k}>{labelFor(k)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(preview.records || []).map((r) => (
                  <tr key={r.row} style={r.blocked ? { opacity: 0.45 } : undefined}>
                    <td className="mono">{r.row + 1}</td>
                    {columns.map((k) => {
                      const cell = r.cells[k];
                      if (!cell) {
                        return (
                          <td key={k} className="tiny">
                            <span className="faint">&mdash;</span>
                          </td>
                        );
                      }
                      // A value that came from somewhere other than the file
                      // on screen is marked, because an operator checking a
                      // bank account needs to know where it came from.
                      const outside = cell.from || cell.generated;
                      return (
                        <td key={k} className={`tiny${outside ? " from-second" : ""}`}>
                          <DiffCell before={cell.before} after={cell.after} />
                          {cell.from && (
                            <div className="tiny faint">from {cell.from}</div>
                          )}
                          {cell.generated && (
                            <div className="tiny faint">generated</div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {(errors.length > 0 || warnings.length > 0) && (
          <div className="card">
            <div className="card-title">
              {errors.length} to fix, {warnings.length} to know about
            </div>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table>
                <tbody>
                  {[...errors, ...warnings].slice(0, 40).map((i, n) => (
                    <tr key={n}>
                      <td style={{ width: 76 }}>
                        <span className={`badge ${i.severity === "error" ? "red" : "amber"}`}>
                          {i.severity}
                        </span>
                      </td>
                      <td className="mono tiny" style={{ width: 46 }}>
                        {i.row >= 0 ? i.row + 1 : ""}
                      </td>
                      <td>
                        {i.message}
                        {i.suggestion && (
                          <div className="tiny faint">{i.suggestion}</div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div className="studio-rail">
        <div className="card">
          <div className="card-title">What this will create</div>
          <div className="stack" style={{ gap: 4, marginTop: 7 }}>
            <div className="row between">
              <span>Employees</span>
              <b className="mono">{will.employees}</b>
            </div>
            <div className="row between">
              <span>Contracts</span>
              <b className="mono">{will.contracts}</b>
            </div>
            {(will.departments || []).length > 0 && (
              <div className="row between">
                <span>New departments</span>
                <b className="mono">{will.departments.length}</b>
              </div>
            )}
            {(will.job_positions || []).length > 0 && (
              <div className="row between">
                <span>New job positions</span>
                <b className="mono">{will.job_positions.length}</b>
              </div>
            )}
            {c.blocked > 0 && (
              <div className="row between">
                <span className="faint">Rows skipped</span>
                <b className="mono">{c.blocked}</b>
              </div>
            )}
          </div>
          {(will.departments || []).length > 0 && (
            <div className="tiny faint" style={{ marginTop: 7 }}>
              Creating: {will.departments.join(", ")}
            </div>
          )}
        </div>

        {(preview.enrichment || []).map((e, i) => (
          <div className="card" key={i}>
            <div className="card-title">From {e.name}</div>
            <div className="tiny" style={{ marginTop: 6, lineHeight: 1.6 }}>
              <b className="mono">{e.values_filled}</b> values filled across{" "}
              <b className="mono">{e.matched}</b> people, matched on{" "}
              <b>{e.joined_on}</b>.
            </div>
            {e.unmatched > 0 && (
              <div className="tiny faint" style={{ marginTop: 5 }}>
                {e.unmatched} not found in it.
              </div>
            )}
          </div>
        ))}

        {preview.code_policy && preview.code_policy.mode === "generate" && (
          <div className="card">
            <div className="card-title">Employee codes</div>
            <div className="tiny faint" style={{ marginTop: 5 }}>
              {preview.code_policy.description}
            </div>
            <div className="row" style={{ gap: 5, marginTop: 8, flexWrap: "wrap" }}>
              {(preview.code_policy.examples || []).slice(0, 4).map((c) => (
                <span key={c} className="codechip">{c}</span>
              ))}
            </div>
          </div>
        )}

        {canDerive && (
          <div className="card">
            <div className="card-title">Rows without an email</div>
            <div className="tiny faint" style={{ marginTop: 5, lineHeight: 1.55 }}>
              An email identifies the record, so a row without one cannot be
              imported. One can be built from the name using the domain the rest
              of the file uses.
            </div>
            <label className="check" style={{ marginTop: 8 }}>
              <input
                type="checkbox"
                checked={applyFixes.includes("derive_email")}
                onChange={() => onToggleFix("derive_email")}
              />
              Build the missing addresses
            </label>
          </div>
        )}

        <div className="row" style={{ gap: 8 }}>
          <button className="ghost" onClick={onBack}>
            Back
          </button>
          <button
            className="primary"
            disabled={busy || will.employees === 0}
            onClick={onCommit}
          >
            {busy ? "Importing" : `Import ${will.employees} employees`}
          </button>
        </div>
        {c.blocked > 0 && (
          <div className="tiny faint">
            {c.blocked} row{c.blocked === 1 ? "" : "s"} will be skipped. The rest
            import.
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function DoneStage({ result, source, onAgain }) {
  const made = result.created || {};
  return (
    <div className="card stagger" style={{ maxWidth: 620 }}>
      <div className="card-title">Imported</div>
      <div className="card-sub">
        From {source?.name} in {((result.duration_ms || 0) / 1000).toFixed(2)}s.
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 14 }}>
        <div>
          <div className="bignum">
            <CountUp to={made.employees || 0} />
          </div>
          <div className="tiny faint">employees</div>
        </div>
        <div>
          <div className="bignum">
            <CountUp to={made.contracts || 0} />
          </div>
          <div className="tiny faint">contracts</div>
        </div>
        <div>
          <div className="bignum">
            <CountUp to={made.departments || 0} />
          </div>
          <div className="tiny faint">new departments</div>
        </div>
      </div>

      {result.skipped > 0 && (
        <div className="tiny faint" style={{ marginTop: 12 }}>
          {result.skipped} row{result.skipped === 1 ? " was" : "s were"} skipped
          and nothing was written for {result.skipped === 1 ? "it" : "them"}.
        </div>
      )}

      <div className="row" style={{ gap: 8, marginTop: 16 }}>
        <button className="primary" onClick={() => navigate("/employees")}>
          Open Employees
        </button>
        <button className="ghost" onClick={() => navigate("/contracts")}>
          Contracts
        </button>
        <button className="ghost" onClick={onAgain}>
          Import another
        </button>
      </div>
    </div>
  );
}
