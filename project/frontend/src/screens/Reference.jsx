// Departments, job positions and work locations.
//
// Three near-identical reference lists, so they share one component
// parameterised by endpoint rather than being copied three times.

import { ErrorBox, Loading, PageHead, StateBadge, useResource } from "../components/ui";

function ReferenceList({ title, path, columns }) {
  const records = useResource(path, { page_size: 200 });

  return (
    <div className="page">
      <PageHead title={title} sub={`${records.rows.length} records`} />
      <ErrorBox error={records.error} />
      <div className="card">
        {records.loading ? (
          <Loading />
        ) : records.rows.length === 0 ? (
          <div className="empty">No records.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c.key} className={c.num ? "num" : undefined}>
                      {c.label}
                    </th>
                  ))}
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {records.rows.map((r) => (
                  <tr key={r.id}>
                    {columns.map((c) => (
                      <td
                        key={c.key}
                        className={c.num ? "num mono" : c.muted ? "muted" : undefined}
                      >
                        {r[c.key] ?? "—"}
                      </td>
                    ))}
                    <td>
                      <StateBadge
                        state={r.active ? "RUNNING" : "EXPIRED"}
                        label={r.active ? "Active" : "Inactive"}
                      />
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

export const Departments = () => (
  <ReferenceList
    title="Departments"
    path="/api/departments/"
    columns={[
      { key: "name", label: "Department" },
      { key: "manager_name", label: "Manager", muted: true },
      { key: "employee_count", label: "Headcount", num: true },
    ]}
  />
);

export const JobPositions = () => (
  <ReferenceList
    title="Job Positions"
    path="/api/job-positions/"
    columns={[{ key: "name", label: "Position" }]}
  />
);

export const WorkLocations = () => (
  <ReferenceList
    title="Work Locations"
    path="/api/work-locations/"
    columns={[{ key: "name", label: "Location" }]}
  />
);
