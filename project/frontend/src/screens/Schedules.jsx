// Working Schedules (T-035).
//
// Graded rule #2: hours_per_week and days_per_week are read-only on the
// serializer and recomputed from the day lines. The form therefore has no
// weekly-hours input -- editing a line and saving is what moves the total.

import { useEffect, useState } from "react";
import { api } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  useResource,
} from "../components/ui";

const DAYS = [
  [0, "Monday"],
  [1, "Tuesday"],
  [2, "Wednesday"],
  [3, "Thursday"],
  [4, "Friday"],
  [5, "Saturday"],
  [6, "Sunday"],
];

const BLANK_LINE = {
  day_of_week: 0,
  start_time: "09:00",
  end_time: "18:00",
  break_minutes: 60,
};

function ScheduleForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: "",
    calendar_type: "FIXED",
    timezone: "Asia/Kolkata",
    active: true,
    lines: [BLANK_LINE],
  });
  const [derived, setDerived] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/working-schedules/${id}/`)
      .then((s) => {
        setForm({
          name: s.name,
          calendar_type: s.calendar_type,
          timezone: s.timezone,
          active: s.active,
          company: s.company,
          lines: (s.lines || []).map((l) => ({
            day_of_week: l.day_of_week,
            start_time: (l.start_time || "").slice(0, 5),
            end_time: (l.end_time || "").slice(0, 5),
            break_minutes: l.break_minutes,
          })),
        });
        setDerived({ hours: s.hours_per_week, days: s.days_per_week });
      })
      .catch((err) => setError(err.message));
  }, [id]);

  const setLine = (index, key, value) =>
    setForm((f) => ({
      ...f,
      lines: f.lines.map((l, i) => (i === index ? { ...l, [key]: value } : l)),
    }));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload = { ...form };
      if (id) await api.patch(`/api/working-schedules/${id}/`, payload);
      else await api.post("/api/working-schedules/", payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      wide
      title={id ? form.name || "Working Schedule" : "New Working Schedule"}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={save} disabled={busy}>
            {busy ? <span className="spinner" /> : "Save"}
          </button>
        </>
      }
    >
      <ErrorBox error={error} />

      {derived && (
        <div className="smart-row">
          <div className="smart">
            <span className="n">{derived.hours}</span>
            <span className="l">Hours / week</span>
          </div>
          <div className="smart">
            <span className="n">{derived.days}</span>
            <span className="l">Days / week</span>
          </div>
        </div>
      )}

      <div className="row fill">
        <Field label="Name">
          <input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
        </Field>
        <Field label="Calendar type">
          <select
            value={form.calendar_type}
            onChange={(e) => setForm((f) => ({ ...f, calendar_type: e.target.value }))}
          >
            <option value="FIXED">Fixed</option>
            <option value="VARIABLE">Variable</option>
          </select>
        </Field>
        <Field label="Timezone">
          <input
            value={form.timezone}
            onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
          />
        </Field>
      </div>

      <div className="card-title">Weekly hours</div>
      <div className="table-wrap mb">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Start</th>
              <th>End</th>
              <th className="num">Break (min)</th>
              <th className="right" />
            </tr>
          </thead>
          <tbody>
            {form.lines.map((line, i) => (
              <tr key={i}>
                <td>
                  <select
                    value={line.day_of_week}
                    onChange={(e) => setLine(i, "day_of_week", Number(e.target.value))}
                  >
                    {DAYS.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="time"
                    value={line.start_time}
                    onChange={(e) => setLine(i, "start_time", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="time"
                    value={line.end_time}
                    onChange={(e) => setLine(i, "end_time", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    value={line.break_minutes}
                    onChange={(e) => setLine(i, "break_minutes", Number(e.target.value))}
                  />
                </td>
                <td className="right">
                  <button
                    className="sm danger"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        lines: f.lines.filter((_, j) => j !== i),
                      }))
                    }
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        className="sm"
        onClick={() => setForm((f) => ({ ...f, lines: [...f.lines, BLANK_LINE] }))}
      >
        Add day
      </button>
    </Modal>
  );
}

export default function Schedules() {
  const [editing, setEditing] = useState(undefined);
  const schedules = useResource("/api/working-schedules/");

  return (
    <div className="page">
      <PageHead title="Working Schedules" sub={`${schedules.rows.length} records`}>
        <button className="primary" onClick={() => setEditing(null)}>
          New Schedule
        </button>
      </PageHead>

      <ErrorBox error={schedules.error} />

      <div className="card">
        {schedules.loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Calendar type</th>
                  <th className="num">Days / week</th>
                  <th className="num">Hours / week</th>
                  <th>Company</th>
                  <th>Timezone</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {schedules.rows.map((s) => (
                  <tr key={s.id} className="clickable" onClick={() => setEditing(s.id)}>
                    <td>{s.name}</td>
                    <td className="muted">{s.calendar_type}</td>
                    <td className="num mono">{s.days_per_week}</td>
                    <td className="num mono">{s.hours_per_week}</td>
                    <td className="muted">{s.company_name}</td>
                    <td className="muted tiny">{s.timezone}</td>
                    <td>
                      <StateBadge
                        state={s.active ? "RUNNING" : "EXPIRED"}
                        label={s.active ? "Active" : "Inactive"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== undefined && (
        <ScheduleForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            schedules.reload();
          }}
        />
      )}
    </div>
  );
}
