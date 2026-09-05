// Holidays.
//
// These are not decorative: the payroll engine excludes them from expected
// working days, so a holiday added here changes the LOP arithmetic on the next
// compute.

import { useEffect, useState } from "react";
import { api, auth, formatDate } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  rows,
  useResource,
} from "../components/ui";

const WEEKDAY = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-IN", { weekday: "long" })
    : "—";

function HolidayForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState({ name: "", date: "", company: "" });
  const [companies, setCompanies] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get("/api/companies/")
      .then((c) => {
        const list = rows(c);
        setCompanies(list);
        setForm((f) => ({ ...f, company: f.company || list[0]?.id || "" }));
      })
      .catch(() => setCompanies([]));
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/holidays/${id}/`)
      .then((h) => setForm({ name: h.name, date: h.date, company: h.company }))
      .catch((err) => setError(err.message));
  }, [id]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      if (id) await api.patch(`/api/holidays/${id}/`, form);
      else await api.post("/api/holidays/", form);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.delete(`/api/holidays/${id}/`);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  // Rows are clickable, so a role with read access but no write access
  // reaches this modal legitimately -- to look, not to change. Offering
  // a Save the server would refuse is the mirror image of hiding a
  // control it allows; both mislead about what the account can do.
  const canWrite = auth.has("reference.write");

  return (
    <Modal
      title={id ? form.name || "Holiday" : "New Holiday"}
      onClose={onClose}
      footer={
        canWrite ? (
          <>
            {id && (
              <button className="danger" onClick={remove} disabled={busy}>
                Delete
              </button>
            )}
            <div className="spacer" />
            <button onClick={onClose}>Cancel</button>
            <button className="primary" onClick={save} disabled={busy}>
              {busy ? <span className="spinner" /> : "Save"}
            </button>
          </>
        ) : (
          <button onClick={onClose}>Close</button>
        )
      }
    >
      <fieldset
        disabled={!canWrite}
        style={{ border: 0, padding: 0, margin: 0, minInlineSize: 0 }}
      >
      <ErrorBox error={error} />
      <Field label="Name">
        <input value={form.name} onChange={set("name")} />
      </Field>
      <Field label="Date">
        <input type="date" value={form.date} onChange={set("date")} />
      </Field>
      <Field label="Company">
        <select value={form.company || ""} onChange={set("company")}>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      </fieldset>
    </Modal>
  );
}

export default function Holidays() {
  const [editing, setEditing] = useState(undefined);
  const holidays = useResource("/api/holidays/", {
    ordering: "date",
    page_size: 200,
  });

  const byYear = holidays.rows.reduce((acc, h) => {
    const year = (h.date || "").slice(0, 4) || "—";
    (acc[year] = acc[year] || []).push(h);
    return acc;
  }, {});

  return (
    <div className="page">
      <PageHead title="Holidays" sub={`${holidays.rows.length} records`}>
        {auth.has("reference.write") && (
          <button className="primary" onClick={() => setEditing(null)}>
            New Holiday
          </button>
        )}
      </PageHead>

      <ErrorBox error={holidays.error} />

      {holidays.loading ? (
        <Loading />
      ) : holidays.rows.length === 0 ? (
        <div className="card">
          <div className="empty">No holidays.</div>
        </div>
      ) : (
        Object.entries(byYear)
          .sort(([a], [b]) => b.localeCompare(a))
          .map(([year, list]) => (
            <div className="card" key={year}>
              <div className="card-title">
                {year} — {list.length} days
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Day</th>
                      <th>Holiday</th>
                      <th>Company</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((h) => (
                      <tr
                        key={h.id}
                        className="clickable"
                        onClick={() => setEditing(h.id)}
                      >
                        <td className="mono">{formatDate(h.date)}</td>
                        <td className="muted">{WEEKDAY(h.date)}</td>
                        <td>{h.name}</td>
                        <td className="muted">{h.company_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))
      )}

      {editing !== undefined && (
        <HolidayForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            holidays.reload();
          }}
        />
      )}
    </div>
  );
}
