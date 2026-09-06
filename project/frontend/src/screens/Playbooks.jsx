// Playbooks — rules that remember things so people do not have to.
//
// Same three-step shape as Segments: describe it in a sentence, read the rule
// that came back, correct it, save. The difference is what happens afterwards
// -- a playbook raises reminders rather than making changes, which is the
// reason it is safe to leave one switched on and forget about it. The worst a
// wrong rule can do is put a line in the inbox below.

import { useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox, Loading, Modal, PageHead, useResource, rows,
} from "../components/ui";
import { Stagger, ThinkingStream, Working } from "../components/ai";

const EXAMPLES = [
  "remind me to review increments for full time staff twelve months after they join",
  "tell me when someone's bond is about to end",
  "flag anyone with no bank account on file",
];

const TRIGGER_LABEL = {
  TENURE_REACHED: "Tenure reached",
  CONTRACT_ENDING: "Contract ending",
  BOND_EXPIRING: "Bond expiring",
  PROBATION_ENDING: "Probation ending",
  NO_BANK_ACCOUNT: "No bank account",
};

const ACTION_LABEL = {
  NOTIFY: "Raise a reminder",
  PROPOSE_INCREMENT: "Propose an increment",
  FLAG_REVIEW: "Flag for review",
};

export default function Playbooks() {
  const [tab, setTab] = useState("rules");
  return (
    <div className="page">
      <PageHead title="Playbooks" sub="Standing rules that watch and remind" />
      <div className="tabs">
        <button className={`tab${tab === "rules" ? " active" : ""}`} onClick={() => setTab("rules")}>
          Rules
        </button>
        <button
          className={`tab${tab === "inbox" ? " active" : ""}`}
          onClick={() => setTab("inbox")}
        >
          Reminders
        </button>
      </div>
      {tab === "rules" ? <Rules /> : <Inbox />}
    </div>
  );
}

// ---------------------------------------------------------------------------

function Rules() {
  const { data, loading, error, reload } = useResource("/api/workforce/playbooks/");
  const list = rows(data);

  const [text, setText] = useState("");
  const [proposal, setProposal] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [failure, setFailure] = useState(null);
  const [dry, setDry] = useState(null);
  const [busy, setBusy] = useState(false);

  const canWrite = auth.has("workforce.write");

  async function interpret(sentence) {
    const value = (sentence ?? text).trim();
    if (!value) return;
    setText(value);
    setThinking(true);
    setFailure(null);
    setProposal(null);
    try {
      setProposal(await api.post("/api/workforce/playbooks/compile/", { text: value }));
    } catch (e) {
      setFailure(e.message);
    } finally {
      setThinking(false);
    }
  }

  async function save() {
    setBusy(true);
    try {
      await api.post("/api/workforce/playbooks/", {
        name: proposal.name,
        trigger: proposal.trigger,
        trigger_params: proposal.trigger_params,
        criteria: proposal.criteria,
        action: proposal.action,
        action_params: proposal.action_params,
        nl_prompt: text,
        active: true,
      });
      setProposal(null);
      setText("");
      reload();
    } catch (e) {
      setFailure(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggle(playbook) {
    try {
      await api.patch(`/api/workforce/playbooks/${playbook.id}/`, {
        active: !playbook.active,
      });
      reload();
    } catch (e) {
      setFailure(e.message);
    }
  }

  async function runAll() {
    setBusy(true);
    try {
      const r = await api.post("/api/workforce/playbooks/run-due/");
      setFailure(null);
      setDry({
        title: "Ran every active rule",
        summary: `${r.events_raised} reminder${r.events_raised === 1 ? "" : "s"} raised across ${r.playbooks} rule${r.playbooks === 1 ? "" : "s"}.`,
        people: r.results.flatMap((x) => x.people),
      });
      reload();
    } catch (e) {
      setFailure(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function dryRun(playbook) {
    try {
      const r = await api.post(`/api/workforce/playbooks/${playbook.id}/dry-run/`);
      setDry({
        title: `${playbook.name} — who it matches today`,
        summary: `${r.matched} matched, ${r.new} of them not yet raised.`,
        people: r.people,
      });
    } catch (e) {
      setFailure(e.message);
    }
  }

  if (loading) return <Loading />;

  return (
    <>
      <ErrorBox error={error || failure} />

      {canWrite && (
        <div className="card">
          <div className="card-title">Describe the reminder</div>
          <div className="card-sub">
            A playbook only ever raises a reminder. It never changes a record, so
            leaving one switched on is safe.
          </div>

          <div className="row" style={{ gap: 8, marginTop: 10 }}>
            <input
              style={{ flex: 1 }}
              placeholder="remind me to review increments six months after someone joins"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && interpret()}
            />
            <button className="primary" onClick={() => interpret()} disabled={thinking || !text.trim()}>
              {thinking ? "Reading" : "Interpret"}
            </button>
          </div>

          <div className="row" style={{ gap: 6, marginTop: 8, flexWrap: "wrap" }}>
            {EXAMPLES.map((e) => (
              <button key={e} className="tchip" onClick={() => interpret(e)}>
                {e.length > 52 ? `${e.slice(0, 49)}...` : e}
              </button>
            ))}
          </div>

          {thinking && (
            <Working
              label="Working out the trigger and who it applies to"
              sub="matching it against the triggers this system has"
            />
          )}

          {proposal && (
            <Stagger>
              <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
                <div className="row between">
                  <span className="card-title" style={{ margin: 0 }}>
                    How that was read
                  </span>
                  <span className={`badge ${proposal.source === "model" ? "purple" : "grey"}`}>
                    {proposal.source === "model" ? "local model" : "keyword match"}
                  </span>
                </div>

                {proposal.reading && (
                  <div style={{ marginTop: 7 }}>
                    <ThinkingStream text={proposal.reading} />
                  </div>
                )}

                <div className="alert" style={{ marginTop: 10 }}>
                  <b>When</b> {TRIGGER_LABEL[proposal.trigger]}
                  {proposal.trigger_params?.months
                    ? ` — ${proposal.trigger_params.months} months`
                    : proposal.trigger_params?.days
                    ? ` — within ${proposal.trigger_params.days} days`
                    : ""}
                  <br />
                  <b>For</b> {proposal.description}
                  <br />
                  <b>Then</b> {ACTION_LABEL[proposal.action]}
                  {proposal.action_params?.percent ? ` of ${proposal.action_params.percent}%` : ""}
                </div>

                {proposal.dropped?.length > 0 && (
                  <div className="tiny faint" style={{ marginTop: 6 }}>
                    Left out of the rule: {proposal.dropped.join("; ")}.
                  </div>
                )}

                <div className="tiny" style={{ marginTop: 8 }}>
                  Matches <b className="mono">{proposal.preview?.count ?? 0}</b> people today.
                </div>

                <div className="row" style={{ gap: 8, marginTop: 12 }}>
                  <input
                    style={{ flex: 1 }}
                    value={proposal.name}
                    onChange={(e) => setProposal({ ...proposal, name: e.target.value })}
                  />
                  <button className="primary" onClick={save} disabled={busy}>
                    Save rule
                  </button>
                  <button className="ghost" onClick={() => setProposal(null)}>
                    Discard
                  </button>
                </div>
              </div>
            </Stagger>
          )}
        </div>
      )}

      <div className="card">
        <div className="row between">
          <span className="card-title" style={{ margin: 0 }}>
            Rules
          </span>
          {canWrite && (
            <button className="ghost sm" onClick={runAll} disabled={busy}>
              {busy ? "Running" : "Run all now"}
            </button>
          )}
        </div>

        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Rule</th>
                <th>When</th>
                <th>Then</th>
                <th className="num">Open</th>
                <th>Last run</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <div className="empty">No rules yet. Describe one above.</div>
                  </td>
                </tr>
              )}
              {list.map((p) => (
                <tr key={p.id} style={p.active ? undefined : { opacity: 0.55 }}>
                  <td>
                    <b>{p.name}</b>
                    <div className="tiny faint">{p.criteria_description}</div>
                  </td>
                  <td className="tiny">
                    {TRIGGER_LABEL[p.trigger]}
                    {p.trigger_params?.months
                      ? ` — ${p.trigger_params.months} mo`
                      : p.trigger_params?.days
                      ? ` — ${p.trigger_params.days} d`
                      : ""}
                  </td>
                  <td className="tiny">{ACTION_LABEL[p.action]}</td>
                  <td className="num mono">{p.open_events || ""}</td>
                  <td className="tiny mono faint">
                    {p.last_run ? new Date(p.last_run).toLocaleDateString("en-IN") : "never"}
                  </td>
                  <td className="right nowrap">
                    <button className="ghost sm" onClick={() => dryRun(p)}>
                      Who
                    </button>
                    {canWrite && (
                      <button className="ghost sm" onClick={() => toggle(p)}>
                        {p.active ? "Pause" : "Resume"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {dry && (
        <Modal title={dry.title} onClose={() => setDry(null)} wide>
          <div style={{ marginBottom: 8 }}>{dry.summary}</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {dry.people.length === 0 && (
                  <tr>
                    <td colSpan={2}>
                      <div className="empty">Nobody matches this rule today.</div>
                    </td>
                  </tr>
                )}
                {dry.people.map((p, i) => (
                  <tr key={`${p.id}-${i}`}>
                    <td>{p.name}</td>
                    <td className="tiny">{p.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------

function Inbox() {
  const { data, loading, error, reload } = useResource("/api/workforce/playbook-events/");
  const list = rows(data);
  const open = list.filter((e) => !e.acknowledged);

  async function ack(event) {
    await api.post(`/api/workforce/playbook-events/${event.id}/acknowledge/`);
    reload();
  }

  if (loading) return <Loading />;

  return (
    <>
      <ErrorBox error={error} />
      <div className="card">
        <div className="card-title">
          {open.length} open reminder{open.length === 1 ? "" : "s"}
        </div>
        <div className="card-sub">
          Each of these was raised by a rule. Nothing was changed.
        </div>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Reminder</th>
                <th>Why</th>
                <th>Rule</th>
                <th>Raised</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">
                      Nothing raised yet. Run the rules from the Rules tab.
                    </div>
                  </td>
                </tr>
              )}
              {list.map((e) => (
                <tr key={e.id} style={e.acknowledged ? { opacity: 0.5 } : undefined}>
                  <td>{e.title}</td>
                  <td className="tiny">{e.detail}</td>
                  <td className="tiny faint">{e.playbook_name}</td>
                  <td className="tiny mono faint">
                    {new Date(e.fired_at).toLocaleDateString("en-IN")}
                  </td>
                  <td className="right">
                    {!e.acknowledged && (
                      <button className="ghost sm" onClick={() => ack(e)}>
                        Done
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
