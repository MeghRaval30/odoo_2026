// Bonds — service agreements, their lock-in, and what is owed if it breaks.
//
// The figure this screen exists to make visible is the remaining liability. A
// bond is not interesting while it runs; it becomes interesting the day
// somebody resigns, and at that moment the only question is how much of the
// recovery is still enforceable. Computing it pro rata and showing it on every
// row means the mass-exit preview and this list agree, because both read the
// same property.

import { useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox, Field, Loading, Modal, PageHead, StateBadge, useResource, rows,
} from "../components/ui";

const money = (v) =>
  v === null || v === undefined || v === ""
    ? "—"
    : Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });

export default function Bonds() {
  const [tab, setTab] = useState("bonds");
  return (
    <div className="page">
      <PageHead title="Bonds" sub="Service agreements and what they recover" />
      <div className="tabs">
        <button className={`tab${tab === "bonds" ? " active" : ""}`} onClick={() => setTab("bonds")}>
          Bonds
        </button>
        <button
          className={`tab${tab === "templates" ? " active" : ""}`}
          onClick={() => setTab("templates")}
        >
          Templates
        </button>
      </div>
      {tab === "bonds" ? <BondList /> : <TemplateList />}
    </div>
  );
}

// ---------------------------------------------------------------------------

function BondList() {
  const { data, loading, error, reload } = useResource("/api/workforce/bonds/");
  const list = rows(data);
  const [signing, setSigning] = useState(null);
  const [reading, setReading] = useState(null);
  const [failure, setFailure] = useState(null);

  const canWrite = auth.has("workforce.write");
  const active = list.filter((b) => b.state === "ACTIVE" || b.state === "SIGNED");
  const exposure = active.reduce((n, b) => n + Number(b.remaining_liability || 0), 0);
  const expiring = active.filter((b) => b.expiring_soon);

  if (loading) return <Loading />;

  return (
    <>
      <ErrorBox error={error || failure} />

      <div className="card">
        <div className="row" style={{ gap: 26, flexWrap: "wrap" }}>
          <Stat label="Active bonds" value={active.length} />
          <Stat label="Recoverable today" value={money(exposure.toFixed(2))} />
          <Stat label="Ending within 60 days" value={expiring.length} accent={expiring.length > 0} />
        </div>
        {expiring.length > 0 && (
          <div className="alert" style={{ marginTop: 10 }}>
            {expiring.length === 1
              ? `${expiring[0].employee_name}'s bond ends in ${expiring[0].days_to_expiry} days.`
              : `${expiring.length} bonds end within the next 60 days.`}{" "}
            A playbook can raise these automatically.
          </div>
        )}
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Term</th>
                <th className="num">Served</th>
                <th className="num">Left</th>
                <th className="num">Recoverable now</th>
                <th>State</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <div className="empty">
                      No bonds yet. Issue them to a segment from Mass actions.
                    </div>
                  </td>
                </tr>
              )}
              {list.map((b) => (
                <tr key={b.id}>
                  <td>
                    {b.employee_name}
                    <div className="tiny faint">{b.template_name || "No template"}</div>
                  </td>
                  <td className="tiny mono">
                    {b.start_date} to {b.end_date}
                    {b.expiring_soon && (
                      <div style={{ color: "var(--amber)" }}>
                        ends in {b.days_to_expiry} days
                      </div>
                    )}
                  </td>
                  <td className="num mono">{b.months_served}</td>
                  <td className="num mono">{b.months_remaining}</td>
                  <td className="num mono">{money(b.remaining_liability)}</td>
                  <td>
                    <StateBadge state={b.state} />
                  </td>
                  <td className="right nowrap">
                    <button className="ghost sm" onClick={() => setReading(b)}>
                      Read
                    </button>
                    {canWrite && b.state !== "ACTIVE" && b.state !== "SIGNED" && (
                      <button className="ghost sm" onClick={() => setSigning(b)}>
                        Sign
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {reading && (
        <Modal title={`Bond — ${reading.employee_name}`} onClose={() => setReading(null)} wide>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              fontFamily: "var(--font-sans)",
              fontSize: 12.5,
              lineHeight: 1.7,
              margin: 0,
            }}
          >
            {reading.rendered_body || "This bond has no template text."}
          </pre>
          {reading.signed_name && (
            <div className="tiny faint" style={{ marginTop: 12 }}>
              Signed by {reading.signed_name} on{" "}
              {new Date(reading.signed_at).toLocaleDateString("en-IN")}.
            </div>
          )}
        </Modal>
      )}

      {signing && (
        <SignModal
          bond={signing}
          onClose={() => setSigning(null)}
          onDone={() => {
            setSigning(null);
            reload();
          }}
          onError={setFailure}
        />
      )}
    </>
  );
}

function SignModal({ bond, onClose, onDone, onError }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function sign() {
    setBusy(true);
    try {
      await api.post(`/api/workforce/bonds/${bond.id}/sign/`, { signed_name: name });
      onDone();
    } catch (e) {
      onError(e.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Sign — ${bond.employee_name}`}
      onClose={onClose}
      wide
      footer={
        <>
          <button className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={busy || name.trim().toLowerCase() !== bond.employee_name.toLowerCase()}
            onClick={sign}
          >
            {busy ? "Signing" : "Sign"}
          </button>
        </>
      }
    >
      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 6,
          padding: 14,
          maxHeight: 260,
          overflowY: "auto",
          background: "var(--surface-2)",
        }}
      >
        <pre
          style={{
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-sans)",
            fontSize: 12.5,
            lineHeight: 1.7,
            margin: 0,
          }}
        >
          {bond.rendered_body || "This bond has no template text."}
        </pre>
      </div>
      <Field
        label="Type the employee's full name to sign"
        hint={`Exactly: ${bond.employee_name}`}
      >
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
    </Modal>
  );
}

// ---------------------------------------------------------------------------

function TemplateList() {
  const { data, loading, error, reload } = useResource("/api/workforce/bond-templates/");
  const list = rows(data);
  const [editing, setEditing] = useState(null);
  const [failure, setFailure] = useState(null);
  const canWrite = auth.has("workforce.write");

  if (loading) return <Loading />;

  return (
    <>
      <ErrorBox error={error || failure} />
      <div className="card">
        <div className="row between">
          <span className="card-title" style={{ margin: 0 }}>
            Templates
          </span>
          {canWrite && (
            <button
              className="primary sm"
              onClick={() =>
                setEditing({
                  name: "",
                  description: "",
                  duration_months: 24,
                  recovery_amount: "100000.00",
                  notice_days: 30,
                  body: "",
                  active: true,
                })
              }
            >
              New template
            </button>
          )}
        </div>
        <div className="table-wrap" style={{ marginTop: 8 }}>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th className="num">Term</th>
                <th className="num">Recovery</th>
                <th className="num">Notice</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.map((t) => (
                <tr key={t.id}>
                  <td>
                    {t.name}
                    <div className="tiny faint">{t.description}</div>
                  </td>
                  <td className="num mono">{t.duration_months} mo</td>
                  <td className="num mono">{money(t.recovery_amount)}</td>
                  <td className="num mono">{t.notice_days} d</td>
                  <td className="right">
                    {canWrite && (
                      <button className="ghost sm" onClick={() => setEditing(t)}>
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {editing && (
        <TemplateModal
          template={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
          onError={setFailure}
        />
      )}
    </>
  );
}

function TemplateModal({ template, onClose, onSaved, onError }) {
  const [form, setForm] = useState(template);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm({ ...form, [k]: v });

  async function save() {
    setBusy(true);
    try {
      if (form.id) await api.patch(`/api/workforce/bond-templates/${form.id}/`, form);
      else await api.post("/api/workforce/bond-templates/", form);
      onSaved();
    } catch (e) {
      onError(e.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      title={form.id ? "Edit template" : "New template"}
      onClose={onClose}
      wide
      footer={
        <>
          <button className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy || !form.name.trim()} onClick={save}>
            {busy ? "Saving" : "Save"}
          </button>
        </>
      }
    >
      <Field label="Name">
        <input value={form.name} onChange={(e) => set("name", e.target.value)} />
      </Field>
      <Field label="Description">
        <input value={form.description} onChange={(e) => set("description", e.target.value)} />
      </Field>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <Field label="Term, months">
          <input
            type="number"
            value={form.duration_months}
            onChange={(e) => set("duration_months", Number(e.target.value))}
          />
        </Field>
        <Field label="Recovery amount">
          <input
            type="number"
            value={form.recovery_amount}
            onChange={(e) => set("recovery_amount", e.target.value)}
          />
        </Field>
        <Field label="Notice days">
          <input
            type="number"
            value={form.notice_days}
            onChange={(e) => set("notice_days", Number(e.target.value))}
          />
        </Field>
      </div>
      <Field
        label="Agreement text"
        hint="Placeholders: {{employee_name}} {{company}} {{duration_months}} {{recovery_amount}} {{start_date}} {{end_date}} {{notice_days}}"
      >
        <textarea rows={9} value={form.body} onChange={(e) => set("body", e.target.value)} />
      </Field>
    </Modal>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div>
      <div className="bignum" style={accent ? { color: "var(--amber)" } : undefined}>
        {value}
      </div>
      <div className="tiny faint">{label}</div>
    </div>
  );
}
