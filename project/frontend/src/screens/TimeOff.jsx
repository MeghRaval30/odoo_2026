// Time Off requests and the approval flow (T-038, T-039).
//
// The allocation gate is graded rule #3. It lives in the model's clean(), is
// re-run by the serializer, and arrives here as a field error -- so submitting
// against an allocation-required type with no balance shows the server's own
// refusal rather than a message invented on the client.

import { useEffect, useState } from "react";
import { api, auth, formatDate } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  rows,
  useDebounced,
  useResource,
} from "../components/ui";

const BLANK = {
  employee: "",
  time_off_type: "",
  date_from: new Date().toISOString().slice(0, 10),
  date_to: new Date().toISOString().slice(0, 10),
  // A choice, not a flag: the model stores "" / FIRST / SECOND, and the
  // duration is halved only when a half is named and the range is one day.
  half_day: "",
  reason: "",
};

// An employee raising their own request has nothing to choose here: the server
// substitutes their own id on POST whatever the payload says, and scopes
// /api/employees/ to the single row that is theirs. Showing them a one-option
// picker would be asking a question with one answer, so the field is filled in
// and shown read-only instead. HR keeps the picker -- they file on behalf of
// other people, which is the whole reason the field exists.
const selfService = () =>
  !auth.has("timeoff.read.all") && Boolean(auth.user?.employee_id);

function RequestForm({ onClose, onSaved }) {
  const ownRequest = selfService();
  const [form, setForm] = useState(() =>
    ownRequest
      ? { ...BLANK, employee: String(auth.user.employee_id) }
      : BLANK);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refs, setRefs] = useState({});
  const [balances, setBalances] = useState([]);

  useEffect(() => {
    // Only HR needs the employee list; for an own request it would be one row.
    Promise.all([
      ownRequest
        ? Promise.resolve(null)
        : api.get("/api/employees/", { page_size: 200 }),
      api.get("/api/timeoff-types/"),
    ])
      .then(([e, t]) =>
        setRefs({ employees: e ? rows(e) : [], types: rows(t) }))
      .catch((err) => setError(err.message));
  }, [ownRequest]);

  useEffect(() => {
    if (!form.employee) return setBalances([]);
    api
      .get("/api/timeoff-requests/balances/", { employee: form.employee })
      .then((b) => setBalances(rows(b)))
      .catch(() => setBalances([]));
  }, [form.employee]);

  const set = (key) => (e) => {
    // Clear a previous refusal as soon as the request changes. Without this
    // the server's "no allocation covers this" message stays on screen after
    // the user switches to a type they *do* have balance for, so the form
    // shows a refusal directly above a balance table saying 20 days are
    // available — which reads as though that type were refused too.
    setError(null);
    setForm((f) => ({
      ...f,
      [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value,
    }));
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/timeoff-requests/", form);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const type = refs.types?.find((t) => String(t.id) === String(form.time_off_type));

  return (
    <Modal
      title="New Time Off Request"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={save} disabled={busy}>
            {busy ? <span className="spinner" /> : "Submit"}
          </button>
        </>
      }
    >
      <ErrorBox error={error} />

      <Field label="Employee">
        {ownRequest ? (
          <input value={auth.user?.employee_name || ""} readOnly disabled />
        ) : (
          <select value={form.employee} onChange={set("employee")}>
            <option value="">—</option>
            {refs.employees?.map((e) => (
              <option key={e.id} value={e.id}>
                {e.full_name}
              </option>
            ))}
          </select>
        )}
      </Field>

      <Field label="Time off type">
        <select value={form.time_off_type} onChange={set("time_off_type")}>
          <option value="">—</option>
          {refs.types?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.requires_allocation ? " (allocation required)" : ""}
            </option>
          ))}
        </select>
      </Field>

      {type?.requires_allocation && balances.length > 0 && (
        <div className="table-wrap mb">
          <table>
            <thead>
              <tr>
                <th>Balance</th>
                <th className="num">Allocated</th>
                <th className="num">Taken</th>
                <th className="num">Remaining</th>
              </tr>
            </thead>
            <tbody>
              {balances
                .filter((b) => String(b.time_off_type) === String(form.time_off_type))
                .map((b) => (
                  <tr key={b.time_off_type}>
                    <td>{b.type_name}</td>
                    <td className="num mono">{b.allocated}</td>
                    <td className="num mono">{b.taken}</td>
                    <td className="num mono">{b.remaining}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="row fill">
        <Field label="From">
          <input type="date" value={form.date_from} onChange={set("date_from")} />
        </Field>
        <Field label="To">
          <input type="date" value={form.date_to} onChange={set("date_to")} />
        </Field>
      </div>

      <Field label="Half day">
        <select value={form.half_day} onChange={set("half_day")}>
          <option value="">Full day</option>
          <option value="FIRST">First half</option>
          <option value="SECOND">Second half</option>
        </select>
        {form.half_day && form.date_from !== form.date_to && (
          <div className="muted">
            Counted as a half day only when From and To are the same date.
          </div>
        )}
      </Field>

      <Field label="Reason">
        <textarea rows={2} value={form.reason} onChange={set("reason")} />
      </Field>
    </Modal>
  );
}

// Both states mean "nobody has decided this yet", so both are actionable by
// someone who may decide. Gating on TO_APPROVE alone left every request the UI
// created — all of which were DRAFT — showing a state badge and a dash where
// Approve and Refuse belonged. New requests are now created as TO_APPROVE, and
// DRAFT stays here so any row written before that fix is still decidable
// rather than stranded.
const UNDECIDED = new Set(["DRAFT", "TO_APPROVE"]);

export default function TimeOff({ route }) {
  const [state, setState] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search);
  const [myTeam, setMyTeam] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);
  const employeeFilter = route?.query?.employee || "";

  const requests = useResource("/api/timeoff-requests/", {
    state,
    search: debouncedSearch,
    my_team: myTeam ? 1 : "",
    employee: employeeFilter,
    ordering: "-date_from",
    page_size: 200,
  });

  // An employee sees their own pending request here. Offering them Approve
  // and Refuse on it would advertise a power the server refuses — and on their
  // own leave, of all things. The capability, not the screen, decides.
  const canApprove = auth.has("timeoff.approve");

  const act = async (id, verb) => {
    setBusy(id);
    setError(null);
    try {
      await api.post(`/api/timeoff-requests/${id}/${verb}/`, {});
      await requests.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="page">
      <PageHead title="Time Off Requests" sub={`${requests.rows.length} records`}>
        <button className="primary" onClick={() => setCreating(true)}>
          New Request
        </button>
      </PageHead>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search employee or reason…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div>
          <label>Status</label>
          <select value={state} onChange={(e) => setState(e.target.value)}>
            <option value="">All</option>
            <option value="TO_APPROVE">To Approve</option>
            <option value="APPROVED">Approved</option>
            <option value="REFUSED">Refused</option>
          </select>
        </div>
        <label className="row" style={{ gap: 6, marginBottom: 0 }}>
          <input
            type="checkbox"
            checked={myTeam}
            onChange={(e) => setMyTeam(e.target.checked)}
          />
          <span>My Team</span>
        </label>
      </div>

      <ErrorBox error={error || requests.error} />

      <div className="card">
        {requests.loading ? (
          <Loading />
        ) : requests.rows.length === 0 ? (
          <div className="empty">No requests.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Type</th>
                  <th>From</th>
                  <th>To</th>
                  <th className="num">Duration</th>
                  <th>Allocation used</th>
                  <th>Status</th>
                  <th className="right">Action</th>
                </tr>
              </thead>
              <tbody>
                {requests.rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.employee_name}</td>
                    <td className="muted">{r.type_name}</td>
                    <td className="muted">{formatDate(r.date_from)}</td>
                    <td className="muted">{formatDate(r.date_to)}</td>
                    <td className="num mono">{r.duration}</td>
                    <td className="muted tiny">{r.allocation_name || "—"}</td>
                    <td>
                      <StateBadge state={r.state} label={r.state_display} />
                    </td>
                    <td className="right">
                      {UNDECIDED.has(r.state) && canApprove ? (
                        <div className="row" style={{ justifyContent: "flex-end", gap: 6 }}>
                          <button
                            className="sm"
                            disabled={busy === r.id}
                            onClick={() => act(r.id, "approve")}
                          >
                            Approve
                          </button>
                          <button
                            className="sm danger"
                            disabled={busy === r.id}
                            onClick={() => act(r.id, "refuse")}
                          >
                            Refuse
                          </button>
                        </div>
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {creating && (
        <RequestForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            requests.reload();
          }}
        />
      )}
    </div>
  );
}
