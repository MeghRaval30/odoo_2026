// Segments — describing a group of people in a sentence.
//
// The primary input is prose, and the three steps after it are the whole
// design: the machine proposes a rule, the person reads and corrects it, and
// only the corrected rule is ever executed. The live match count sits under
// the rule for the same reason a preview sits before an import -- being told
// "this matches 7 people, here they are" is how somebody knows the sentence
// was understood, without having to trust that it was.

import { useCallback, useEffect, useState } from "react";
import { api, auth } from "../api";
import { ErrorBox, Field, Loading, Modal, PageHead, useResource, rows } from "../components/ui";
import { Pulse, Stagger, ThinkingStream } from "../components/ai";

const EXAMPLES = [
  "engineers who joined before 2026 earning under 90000",
  "interns who have been here more than 6 months",
  "everyone with no bank account on file",
  "full time staff in sales earning over 80000",
];

export default function Segments() {
  const { data, loading, error, reload } = useResource("/api/workforce/segments/");
  const list = rows(data);

  const [text, setText] = useState("");
  const [proposal, setProposal] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [failure, setFailure] = useState(null);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [inspect, setInspect] = useState(null);

  const canWrite = auth.has("workforce.write");

  async function interpret(sentence) {
    const value = (sentence ?? text).trim();
    if (!value) return;
    setText(value);
    setThinking(true);
    setFailure(null);
    setProposal(null);
    try {
      const p = await api.post("/api/workforce/segments/compile/", { text: value });
      setProposal(p);
      setName(value.length > 60 ? `${value.slice(0, 57)}...` : value);
    } catch (e) {
      setFailure(e.message);
    } finally {
      setThinking(false);
    }
  }

  // Re-count as the operator edits the rule, so the number under it is always
  // the number for what is currently on screen rather than for what was
  // proposed a minute ago.
  const recount = useCallback(async (criteria) => {
    try {
      const preview = await api.post("/api/workforce/segments/preview/", { criteria });
      setProposal((p) => (p ? { ...p, criteria, preview, description: preview.description } : p));
    } catch (e) {
      setFailure(e.message);
    }
  }, []);

  async function save() {
    setSaving(true);
    try {
      await api.post("/api/workforce/segments/", {
        name: name || text.slice(0, 60),
        description: proposal.description,
        criteria: proposal.criteria,
        source: proposal.source === "model" ? "ai" : "manual",
        nl_prompt: text,
      });
      setProposal(null);
      setText("");
      reload();
    } catch (e) {
      setFailure(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <PageHead
        title="Segments"
        sub="Describe a group of people once, use it everywhere"
      />

      <ErrorBox error={error || failure} />

      {canWrite && (
        <div className="card">
          <div className="card-title">Describe the group</div>
          <div className="card-sub">
            Type it the way you would say it. The rule that comes back is
            editable, and nothing runs until you save it.
          </div>

          <div className="row" style={{ gap: 8, marginTop: 10 }}>
            <input
              style={{ flex: 1 }}
              placeholder="engineers who joined before 2026 earning under 90000"
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
                {e}
              </button>
            ))}
          </div>

          {thinking && (
            <div className="row" style={{ gap: 8, marginTop: 12, alignItems: "center" }}>
              <Pulse />
              <span className="tiny faint">Working out which filters this means</span>
            </div>
          )}

          {proposal && (
            <Proposal
              proposal={proposal}
              name={name}
              setName={setName}
              onChange={recount}
              onSave={save}
              onDiscard={() => setProposal(null)}
              saving={saving}
            />
          )}
        </div>
      )}

      {loading ? (
        <Loading />
      ) : (
        <div className="card">
          <div className="card-title">Saved segments</div>
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Rule</th>
                  <th className="num">People</th>
                  <th>From</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {list.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty">
                        No segments yet. Describe one above.
                      </div>
                    </td>
                  </tr>
                )}
                {list.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <b>{s.name}</b>
                      {s.description && <div className="tiny faint">{s.description}</div>}
                    </td>
                    <td className="tiny">{s.description_text}</td>
                    <td className="num mono">{s.match_count}</td>
                    <td>
                      <span className={`badge ${s.source === "ai" ? "purple" : "grey"}`}>
                        {s.source === "ai" ? "sentence" : "by hand"}
                      </span>
                    </td>
                    <td className="right">
                      <button className="ghost sm" onClick={() => setInspect(s)}>
                        Who
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {inspect && (
        <SegmentPeople segment={inspect} onClose={() => setInspect(null)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function Proposal({ proposal, name, setName, onChange, onSave, onDiscard, saving }) {
  const c = proposal.criteria || {};
  const count = proposal.preview?.count ?? 0;

  const setKey = (key, value) => {
    const next = { ...c };
    if (value === "" || value === null || value === undefined) delete next[key];
    else next[key] = value;
    onChange(next);
  };

  return (
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
          {proposal.description}
        </div>

        {proposal.dropped?.length > 0 && (
          <div className="tiny faint" style={{ marginTop: 6 }}>
            Parts of the answer were not usable and were left out:{" "}
            {proposal.dropped.join("; ")}.
          </div>
        )}

        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 12 }}>
          <Field label="Earning at least">
            <input
              type="number"
              defaultValue={c.wage_min ?? ""}
              onBlur={(e) => setKey("wage_min", e.target.value ? Number(e.target.value) : "")}
            />
          </Field>
          <Field label="Earning under">
            <input
              type="number"
              defaultValue={c.wage_max ?? ""}
              onBlur={(e) => setKey("wage_max", e.target.value ? Number(e.target.value) : "")}
            />
          </Field>
          <Field label="Months of service, at least">
            <input
              type="number"
              defaultValue={c.tenure_months_min ?? ""}
              onBlur={(e) =>
                setKey("tenure_months_min", e.target.value ? Number(e.target.value) : "")
              }
            />
          </Field>
          <Field label="Joined before">
            <input
              type="date"
              defaultValue={c.joined_before ?? ""}
              onBlur={(e) => setKey("joined_before", e.target.value)}
            />
          </Field>
          <Field label="Departments" hint="Comma separated">
            <input
              defaultValue={(c.departments || []).join(", ")}
              onBlur={(e) =>
                setKey(
                  "departments",
                  e.target.value ? e.target.value.split(",").map((x) => x.trim()) : ""
                )
              }
            />
          </Field>
          <Field label="Job positions" hint="Comma separated">
            <input
              defaultValue={(c.job_positions || []).join(", ")}
              onBlur={(e) =>
                setKey(
                  "job_positions",
                  e.target.value ? e.target.value.split(",").map((x) => x.trim()) : ""
                )
              }
            />
          </Field>
        </div>

        <div className="row between" style={{ marginTop: 12 }}>
          <span>
            Matches <b className="mono">{count}</b>{" "}
            {count === 1 ? "person" : "people"}
            {proposal.preview?.employees?.length > 0 && (
              <span className="tiny faint">
                {" "}
                — {proposal.preview.employees.slice(0, 4).map((e) => e.name).join(", ")}
                {count > 4 ? ` and ${count - 4} more` : ""}
              </span>
            )}
          </span>
        </div>

        <div className="row" style={{ gap: 8, marginTop: 12 }}>
          <input
            style={{ flex: 1 }}
            placeholder="Name this segment"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="primary" onClick={onSave} disabled={saving || !name.trim()}>
            {saving ? "Saving" : "Save segment"}
          </button>
          <button className="ghost" onClick={onDiscard}>
            Discard
          </button>
        </div>
      </div>
    </Stagger>
  );
}

// ---------------------------------------------------------------------------

function SegmentPeople({ segment, onClose }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    api
      .post("/api/workforce/segments/preview/", { criteria: segment.criteria })
      .then(setData)
      .catch(() => setData({ count: 0, employees: [] }));
  }, [segment]);

  return (
    <Modal title={segment.name} onClose={onClose} wide>
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="tiny faint">{data.description}</div>
          <div style={{ margin: "8px 0" }}>
            <b className="mono">{data.count}</b> matched
            {data.employees.length < data.count &&
              `, showing the first ${data.employees.length}`}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Position</th>
                  <th>Joined</th>
                  <th className="num">Wage</th>
                </tr>
              </thead>
              <tbody>
                {data.employees.map((e) => (
                  <tr key={e.id}>
                    <td>{e.name}</td>
                    <td>{e.department || <span className="faint">&mdash;</span>}</td>
                    <td>{e.job_position || <span className="faint">&mdash;</span>}</td>
                    <td className="mono">{e.date_of_joining}</td>
                    <td className="num mono">{e.wage || <span className="faint">&mdash;</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Modal>
  );
}
