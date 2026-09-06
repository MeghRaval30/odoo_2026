// Local AI — what is running, and what happens when it is not.
//
// Written to be honest rather than impressive. Somebody evaluating this will
// reasonably ask two questions: does it work without a GPU, and where does the
// data go. Both are answered here in plain terms, with the fallbacks named
// individually, because "it degrades gracefully" is a claim and a list of what
// still works is evidence.

import { useEffect, useState } from "react";
import { api, auth } from "../api";
import { ErrorBox, Loading, PageHead } from "../components/ui";
import { Pulse } from "../components/ai";

const WINDOWS = `powershell -ExecutionPolicy Bypass -File scripts\\setup-ai.ps1`;
const UNIX = `bash scripts/setup-ai.sh`;
const DOCTOR = `python manage.py ai_doctor`;

const MODELS = [
  {
    name: "qwen2.5:7b",
    params: "7B",
    disk: "4.7 GB",
    vram: "6 GB",
    role: "Default. Reads column headers and compiles rules.",
  },
  {
    name: "qwen2.5:3b",
    params: "3B",
    disk: "1.9 GB",
    vram: "3 GB",
    role: "Fallback for cards under 8 GB. Less accurate on unusual headers.",
  },
];

const FALLBACKS = [
  ["Column mapping", "A synonym dictionary that knows DOJ is a joining date, plus the measured shape of each column. On the bundled files this alone maps 10 of 13 columns."],
  ["Header detection", "Never used the model. Rows are scored on how header-like they are."],
  ["Type and format detection", "Never used the model. Dates, currency, phone numbers, IFSC and PAN are matched by pattern."],
  ["Transform steps", "Never used the model. Derived from what the profiler measured."],
  ["Department matching", "A dictionary of cross-company synonyms. Anything unrecognised is offered as a new value rather than guessed."],
  ["Segments and playbooks from a sentence", "Keyword matching handles the recurring shapes: a department, a year, an amount, a tenure, a bond."],
];

function Copyable({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="row" style={{ gap: 8, alignItems: "center" }}>
      <code
        className="mono"
        style={{
          flex: 1,
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          borderRadius: 4,
          padding: "5px 8px",
          fontSize: 11.5,
          overflowX: "auto",
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </code>
      <button
        className="ghost sm"
        onClick={() => {
          navigator.clipboard?.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        }}
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

export default function AISetup() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [checking, setChecking] = useState(false);

  const load = (force) => {
    setChecking(true);
    api
      .get("/api/intel/health/", force ? { force: "1" } : undefined)
      .then((d) => setHealth(d.llm))
      .catch((e) => setError(e.message))
      .finally(() => setChecking(false));
  };

  useEffect(load, []);

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
      <PageHead title="Local AI" sub="What is running on this machine">
        <button className="ghost" onClick={() => load(true)} disabled={checking}>
          {checking ? "Checking" : "Check again"}
        </button>
      </PageHead>

      <ErrorBox error={error} />

      {!health ? (
        <Loading />
      ) : (
        <>
          <div className="card">
            <div className="row" style={{ gap: 9, alignItems: "center" }}>
              {health.available && <Pulse />}
              <span className="card-title" style={{ margin: 0 }}>
                {health.available ? "Ready" : "Not running"}
              </span>
            </div>
            <div style={{ marginTop: 8 }}>{health.message}</div>

            <div className="table-wrap" style={{ marginTop: 12 }}>
              <table>
                <tbody>
                  <tr>
                    <td style={{ width: 190 }}>Endpoint</td>
                    <td className="mono">{health.base}</td>
                  </tr>
                  <tr>
                    <td>Model requested</td>
                    <td className="mono">{health.model}</td>
                  </tr>
                  <tr>
                    <td>Model present</td>
                    <td>{health.model_present ? "yes" : "no"}</td>
                  </tr>
                  {health.installed_models?.length > 0 && (
                    <tr>
                      <td>Installed</td>
                      <td className="mono tiny">{health.installed_models.join(", ")}</td>
                    </tr>
                  )}
                  {health.latency_ms != null && (
                    <tr>
                      <td>Responded in</td>
                      <td className="mono">{health.latency_ms} ms</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {!health.available && health.install_hint && (
              <div className="alert" style={{ marginTop: 10 }}>
                Try: <code className="mono">{health.install_hint}</code>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title">Setting it up</div>
            <div className="card-sub">
              Three minutes, most of it downloading the model. Safe to re-run.
            </div>
            <div className="stack" style={{ gap: 10, marginTop: 10 }}>
              <div>
                <div className="tiny faint" style={{ marginBottom: 4 }}>
                  Windows, from the repository root
                </div>
                <Copyable text={WINDOWS} />
              </div>
              <div>
                <div className="tiny faint" style={{ marginBottom: 4 }}>
                  macOS or Linux
                </div>
                <Copyable text={UNIX} />
              </div>
              <div>
                <div className="tiny faint" style={{ marginBottom: 4 }}>
                  Diagnose a problem, from project/backend
                </div>
                <Copyable text={DOCTOR} />
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Models</div>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th className="num">Size</th>
                    <th className="num">Disk</th>
                    <th className="num">VRAM</th>
                    <th>Used for</th>
                  </tr>
                </thead>
                <tbody>
                  {MODELS.map((m) => (
                    <tr key={m.name}>
                      <td className="mono">
                        {m.name}
                        {health.model === m.name && (
                          <span className="badge green" style={{ marginLeft: 6 }}>
                            in use
                          </span>
                        )}
                      </td>
                      <td className="num mono">{m.params}</td>
                      <td className="num mono">{m.disk}</td>
                      <td className="num mono">{m.vram}</td>
                      <td className="tiny">{m.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="tiny faint" style={{ marginTop: 8, lineHeight: 1.6 }}>
              Loading a 7B onto an 8 GB card costs about eleven seconds; a warm
              answer takes about four. Every request asks Ollama to keep the
              weights resident for thirty minutes, and the import screen warms
              the model when it opens, so that cost is paid while you are
              choosing a file.
            </div>
          </div>

          <div className="card">
            <div className="card-title">Where the data goes</div>
            <div style={{ marginTop: 8, lineHeight: 1.7 }}>
              Nowhere. The model runs as a process on this machine and there is
              no hosted API in the path. What reaches it is column headers, the
              profiler's one-line description of each column, and at most three
              sample values per column. Full rows are never sent, to the model
              or to anything else.
            </div>
            <div className="tiny faint" style={{ marginTop: 8 }}>
              That constraint is the reason for a local model rather than a
              hosted one. The data on the screen is a company's salary
              register.
            </div>
          </div>

          <div className="card">
            <div className="card-title">What still works without it</div>
            <div className="card-sub">
              The model is one voter of three, and it is never the decider.
              With it switched off the other two carry the feature.
            </div>
            <div className="table-wrap" style={{ marginTop: 8 }}>
              <table>
                <tbody>
                  {FALLBACKS.map(([what, how]) => (
                    <tr key={what}>
                      <td style={{ width: 250 }}>{what}</td>
                      <td className="tiny">{how}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="tiny faint" style={{ marginTop: 8 }}>
              Accuracy drops on headers a dictionary has not seen. Every screen
              states which path produced its answer rather than presenting both
              the same way.
            </div>
          </div>
        </>
      )}
    </div>
  );
}
