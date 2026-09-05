// Salary Structures and Salary Rules (T-040).
//
// Rules are listed in sequence order because that is the order the engine
// evaluates them in, and later rules read earlier results. Showing them in any
// other order would misrepresent the computation.

import { useEffect, useState } from "react";
import { api, auth } from "../api";
import {
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  StateBadge,
  rows,
  useResource,
} from "../components/ui";

const CATEGORY_TONE = {
  BASIC: "blue",
  ALLOWANCE: "green",
  DEDUCTION: "red",
  GROSS: "purple",
  NET: "purple",
  EMPLOYER: "grey",
};

export function SalaryStructures() {
  const [expanded, setExpanded] = useState(null);
  const structures = useResource("/api/salary-structures/");

  return (
    <div className="page">
      <PageHead title="Salary Structures" sub={`${structures.rows.length} records`} />

      <ErrorBox error={structures.error} />

      {structures.loading ? (
        <Loading />
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Structure</th>
                  <th>Code</th>
                  <th className="num">Rules</th>
                  <th className="num">Employees</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {structures.rows.map((s) => (
                  <tr
                    key={s.id}
                    className="clickable"
                    onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                  >
                    <td>{s.name}</td>
                    <td className="mono tiny muted">{s.code}</td>
                    <td className="num mono">{s.rules?.length ?? s.rule_count ?? 0}</td>
                    <td className="num mono">{s.employee_count ?? "—"}</td>
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
        </div>
      )}

      {expanded && (
        <div className="card">
          <div className="card-title">
            {structures.rows.find((s) => s.id === expanded)?.name} — rules in sequence
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="num">Seq</th>
                  <th>Rule</th>
                  <th>Code</th>
                  <th>Category</th>
                  <th>Computation</th>
                  <th className="num">Value</th>
                </tr>
              </thead>
              <tbody>
                {[...(structures.rows.find((s) => s.id === expanded)?.rules || [])]
                  .sort((a, b) => a.sequence - b.sequence)
                  .map((r) => (
                    <tr key={r.id}>
                      <td className="num mono faint">{r.sequence}</td>
                      <td>{r.name}</td>
                      <td className="mono tiny muted">{r.code}</td>
                      <td>
                        <span className={`badge ${CATEGORY_TONE[r.category] || "grey"}`}>
                          {r.category_display || r.category}
                        </span>
                      </td>
                      <td className="muted tiny">{r.computation_display}</td>
                      <td className="num mono">
                        {r.computation === "PERCENTAGE"
                          ? `${r.percentage}%`
                          : r.computation === "FIXED"
                            ? r.amount
                            : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

const RULE_BLANK = {
  structure: "",
  name: "",
  code: "",
  category: "ALLOWANCE",
  sequence: 10,
  computation: "FIXED",
  amount: "0",
  percentage: "0",
  percentage_base: "",
  formula: "",
  condition: "",
  quantity: "1",
  appears_on_payslip: true,
  is_employer_cost: false,
  active: true,
};

function RuleForm({ id, onClose, onSaved }) {
  const [form, setForm] = useState(RULE_BLANK);
  const [structures, setStructures] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get("/api/salary-structures/")
      .then((r) => setStructures(rows(r)))
      .catch(() => setStructures([]));
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/api/salary-rules/${id}/`)
      .then((r) =>
        setForm({
          ...RULE_BLANK,
          ...Object.fromEntries(
            Object.entries(r).map(([k, v]) => [k, v === null ? "" : v]),
          ),
        }),
      )
      .catch((err) => setError(err.message));
  }, [id]);

  const set = (key) => (e) =>
    setForm((f) => ({
      ...f,
      [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value,
    }));

  const save = async () => {
    setBusy(true);
    setError(null);
    const payload = { ...form };
    delete payload.category_display;
    delete payload.computation_display;
    delete payload.structure_name;
    // percentage_base is blank=True but not null=True: blank means "contract
    // wage", null is a 400.
    if (payload.percentage_base == null) payload.percentage_base = "";
    try {
      if (id) await api.patch(`/api/salary-rules/${id}/`, payload);
      else await api.post("/api/salary-rules/", payload);
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  // Save is already withheld below; this keeps the fields from
  // looking editable and silently discarding what is typed into them.
  const canWrite = auth.has("salaryconfig.write");

  return (
    <Modal
      title={id ? form.name || "Salary Rule" : "New Salary Rule"}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose}>Close</button>
          {/*
            The PDF gives the HR Payroll User read-only access to salary
            structures and rules, and full CRUD only to the Payroll Manager.
            Read-only means the rule opens and reads — it does not mean a Save
            button that returns 403.
          */}
          {auth.has("salaryconfig.write") && (
            <button className="primary" onClick={save} disabled={busy}>
              {busy ? <span className="spinner" /> : "Save"}
            </button>
          )}
        </>
      }
    >
      <fieldset
        disabled={!canWrite}
        style={{ border: 0, padding: 0, margin: 0, minInlineSize: 0 }}
      >
      <ErrorBox error={error} />

      <Field label="Salary structure">
        <select value={form.structure || ""} onChange={set("structure")}>
          <option value="">&#8212;</option>
          {structures.map((st) => (
            <option key={st.id} value={st.id}>
              {st.name}
            </option>
          ))}
        </select>
      </Field>

      <div className="row fill">
        <Field label="Name">
          <input value={form.name} onChange={set("name")} />
        </Field>
        <Field label="Code">
          <input value={form.code} onChange={set("code")} />
        </Field>
      </div>

      <div className="row fill">
        <Field label="Category">
          <select value={form.category} onChange={set("category")}>
            <option value="BASIC">Basic</option>
            <option value="ALLOWANCE">Allowance</option>
            <option value="GROSS">Gross</option>
            <option value="DEDUCTION">Deduction</option>
            <option value="NET">Net</option>
          </select>
        </Field>
        <Field label="Sequence">
          <input type="number" value={form.sequence} onChange={set("sequence")} />
        </Field>
      </div>

      <Field label="Computation">
        <select value={form.computation} onChange={set("computation")}>
          <option value="FIXED">Fixed Amount</option>
          <option value="PERCENTAGE">Percentage of Wage</option>
          <option value="FORMULA">Python Code</option>
        </select>
      </Field>

      {form.computation === "FIXED" && (
        <Field label="Amount">
          <input type="number" step="0.01" value={form.amount} onChange={set("amount")} />
        </Field>
      )}

      {form.computation === "PERCENTAGE" && (
        <div className="row fill">
          <Field label="Percentage">
            <input
              type="number"
              step="0.01"
              value={form.percentage}
              onChange={set("percentage")}
            />
          </Field>
          <Field label="Base code">
            <input
              value={form.percentage_base || ""}
              onChange={set("percentage_base")}
              placeholder="WAGE"
            />
          </Field>
        </div>
      )}

      {form.computation === "FORMULA" && (
        <Field label="Formula">
          <textarea
            rows={3}
            className="mono"
            value={form.formula}
            onChange={set("formula")}
            placeholder="result = categories['BASIC'] * 0.4"
          />
        </Field>
      )}

      <Field label="Condition">
        <input value={form.condition || ""} onChange={set("condition")} />
      </Field>

      <div className="row">
        <label className="row" style={{ gap: 6, marginBottom: 0 }}>
          <input
            type="checkbox"
            checked={!!form.appears_on_payslip}
            onChange={set("appears_on_payslip")}
          />
          <span>Appears on payslip</span>
        </label>
        <label className="row" style={{ gap: 6, marginBottom: 0 }}>
          <input
            type="checkbox"
            checked={!!form.is_employer_cost}
            onChange={set("is_employer_cost")}
          />
          <span>Employer cost</span>
        </label>
        <label className="row" style={{ gap: 6, marginBottom: 0 }}>
          <input type="checkbox" checked={!!form.active} onChange={set("active")} />
          <span>Active</span>
        </label>
      </div>
      </fieldset>
    </Modal>
  );
}

export function SalaryRules() {
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState(undefined);
  const rules = useResource("/api/salary-rules/", {
    category,
    ordering: "sequence",
    page_size: 200,
  });

  return (
    <div className="page">
      <PageHead title="Salary Rules" sub={`${rules.rows.length} records`}>
        {auth.has("salaryconfig.write") && (
          <button className="primary" onClick={() => setEditing(null)}>
            New Rule
          </button>
        )}
      </PageHead>

      <div className="toolbar">
        <div>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            <option value="BASIC">Basic</option>
            <option value="ALLOWANCE">Allowance</option>
            <option value="GROSS">Gross</option>
            <option value="DEDUCTION">Deduction</option>
            <option value="NET">Net</option>
          </select>
        </div>
      </div>

      <ErrorBox error={rules.error} />

      <div className="card">
        {rules.loading ? (
          <Loading />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="num">Seq</th>
                  <th>Rule</th>
                  <th>Code</th>
                  <th>Structure</th>
                  <th>Category</th>
                  <th>Computation</th>
                  <th className="num">Value</th>
                </tr>
              </thead>
              <tbody>
                {rules.rows.map((r) => (
                  <tr key={r.id} className="clickable" onClick={() => setEditing(r.id)}>
                    <td className="num mono faint">{r.sequence}</td>
                    <td>{r.name}</td>
                    <td className="mono tiny muted">{r.code}</td>
                    <td className="muted">{r.structure_name}</td>
                    <td>
                      <span className={`badge ${CATEGORY_TONE[r.category] || "grey"}`}>
                        {r.category_display || r.category}
                      </span>
                    </td>
                    <td className="muted tiny">{r.computation_display}</td>
                    <td className="num mono">
                      {r.computation === "PERCENTAGE"
                        ? `${r.percentage}%`
                        : r.computation === "FIXED"
                          ? r.amount
                          : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing !== undefined && (
        <RuleForm
          id={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            rules.reload();
          }}
        />
      )}
    </div>
  );
}
