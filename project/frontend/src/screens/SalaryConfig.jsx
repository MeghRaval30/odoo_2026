// Salary Structures and Salary Rules (T-040).
//
// Rules are listed in sequence order because that is the order the engine
// evaluates them in, and later rules read earlier results. Showing them in any
// other order would misrepresent the computation.

import { useState } from "react";
import { ErrorBox, Loading, PageHead, StateBadge, useResource } from "../components/ui";

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

export function SalaryRules() {
  const [category, setCategory] = useState("");
  const rules = useResource("/api/salary-rules/", {
    category,
    ordering: "sequence",
    page_size: 200,
  });

  return (
    <div className="page">
      <PageHead title="Salary Rules" sub={`${rules.rows.length} records`} />

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
                  <tr key={r.id}>
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
                          : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
