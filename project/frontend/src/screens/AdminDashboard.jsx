// The administrator's home screen.
//
// An Admin also holds every payroll capability and can open the payroll
// dashboard from Reports. What they cannot get anywhere else is this: who holds
// which role, who is signed in right now, whether the security posture is
// actually what they think it is, and what happened recently that somebody may
// be asked about.
//
// The posture panel states each setting as a sentence rather than a checkbox,
// because "enforce_network_policy: false" is easy to read past and "sign-in is
// not restricted by network" is not.

import { formatDateTime } from "../api";
import { ErrorBox, Loading, PageHead, useResource } from "../components/ui";
import { href } from "../lib/router";

export default function AdminDashboard() {
  const { data, loading, error } = useResource("/api/dashboard/admin/");

  if (loading) return <Loading />;
  if (error)
    return (
      <div className="page">
        <ErrorBox error={error} />
      </div>
    );
  if (!data) return null;

  const { accounts, sessions, posture, sign_ins: signIns } = data;

  return (
    <div className="page">
      <PageHead
        title="Administration"
        sub="Accounts, access and what the system has been doing"
      >
        <a className="btn" href={href("/dashboard/payroll")}>
          Payroll dashboard
        </a>
        <a className="btn" href={href("/users")}>
          Users &amp; roles
        </a>
      </PageHead>

      <div className="grid k5 mb">
        <div className="card kpi">
          <div className="label">Accounts</div>
          <div className="value">{accounts.active}</div>
          <div className="foot">
            {accounts.disabled} disabled · {accounts.unlinked} with no employee
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Holding several roles</div>
          <div className="value">{accounts.multi_role}</div>
          <div className="foot">Permission is the union of them</div>
        </div>
        <div className="card kpi">
          <div className="label">Live sessions</div>
          <div className="value">{sessions.live}</div>
          <div className="foot">
            Expire after {posture.session_idle_minutes}m idle
          </div>
        </div>
        <div className="card kpi">
          <div className="label">Sign-ins · 24h</div>
          <div className="value">{signIns.succeeded_24h}</div>
          <div className="foot">succeeded</div>
        </div>
        <div className="card kpi">
          <div className="label">Refused · 24h</div>
          <div className="value">{signIns.failed_24h}</div>
          <div className={`foot${signIns.failed_24h > 10 ? " down" : ""}`}>
            {signIns.failed_24h > 10 ? "worth a look" : "nothing unusual"}
          </div>
        </div>
      </div>

      <div className="grid wide-left">
        <div className="stack">
          <div className="card">
            <div className="between">
              <div className="card-title" style={{ marginBottom: 0 }}>
                Recent activity
              </div>
              <a className="tiny" href={href("/audit")}>
                Full audit log &rarr;
              </a>
            </div>
            <div className="card-sub mt" style={{ marginTop: 8 }}>
              Append-only. Every action that touches money, access or identity.
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Action</th>
                    <th>What happened</th>
                    <th>From</th>
                  </tr>
                </thead>
                <tbody>
                  {!data.audit_tail.length && (
                    <tr>
                      <td colSpan={4}>
                        <div className="empty">Nothing recorded yet.</div>
                      </td>
                    </tr>
                  )}
                  {data.audit_tail.map((row) => (
                    <tr key={row.id}>
                      <td className="tiny nowrap">{formatDateTime(row.created_at)}</td>
                      <td className="tiny nowrap">{row.action_display}</td>
                      <td className="tiny">{row.summary}</td>
                      <td className="mono tiny">{row.ip_address || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Who is signed in</div>
            {!sessions.rows.length ? (
              <div className="empty tiny">No live sessions.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Address</th>
                      <th>Started</th>
                      <th>Last used</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.rows.map((s, i) => (
                      <tr key={i}>
                        <td>{s.email}</td>
                        <td className="mono tiny">{s.ip_address || "unknown"}</td>
                        <td className="tiny">{formatDateTime(s.started_at)}</td>
                        <td className="tiny">{formatDateTime(s.last_used)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="between">
              <div className="card-title" style={{ marginBottom: 0 }}>
                Security posture
              </div>
              <a className="tiny" href={href("/security")}>
                Change &rarr;
              </a>
            </div>
            <div className="card-sub mt" style={{ marginTop: 8 }}>
              Stated as sentences, because a false boolean is easy to read past.
            </div>
            <div className="stack" style={{ gap: 7 }}>
              <Posture
                on={posture.network_enforced}
                yes={`Sign-in is restricted to ${posture.active_policies} permitted network${posture.active_policies === 1 ? "" : "s"}.`}
                no="Sign-in is allowed from any network."
              />
              <Posture
                on={posture.punch_network_enforced}
                yes="Attendance check-in must come from a permitted network."
                no="Attendance can be punched from anywhere."
              />
              <Posture
                on={posture.session_bound_to_ip}
                yes="Sessions are bound to the address they were opened from."
                no="A session works from any address until it expires."
              />
              <Posture
                on
                yes={`Accounts lock for ${posture.session_idle_minutes >= 0 ? "" : ""}${posture.max_failed_logins} failed attempts.`}
              />
              <Posture
                on
                yes={`Sessions end after ${posture.session_idle_minutes} minutes idle, and at ${posture.session_max_hours} hours regardless.`}
              />
              <Posture
                on
                yes={`Passwords must be at least ${posture.password_min_length} characters.`}
              />
            </div>
            <div className="tiny faint mt">
              You are connected from{" "}
              <span className="mono">{posture.your_ip_address || "an unknown address"}</span>.
            </div>
          </div>

          <div className="card">
            <div className="card-title">Accounts by role</div>
            <div className="card-sub">
              An account can hold more than one, so these do not sum to the
              headcount.
            </div>
            <div className="barlist">
              {accounts.by_role.map((r) => (
                <div className="barrow" key={r.code}>
                  <span className="nm">{r.name}</span>
                  <span className="vl">{r.count}</span>
                  <div className="meter">
                    <i
                      style={{
                        width: `${(r.count / Math.max(1, accounts.active)) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {signIns.failed_addresses.length > 0 && (
            <div className="card">
              <div className="card-title">Where refusals came from</div>
              <div className="card-sub">Last 24 hours.</div>
              {signIns.failed_addresses.map((row) => (
                <div className="between tiny" key={row.ip_address || "unknown"}>
                  <span className="mono">{row.ip_address || "unknown"}</span>
                  <span className={`badge ${row.count > 5 ? "red" : "grey"}`}>
                    {row.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Posture({ on, yes, no }) {
  return (
    <div className="row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
      <span className={`badge ${on ? "green" : "grey"}`} style={{ marginTop: 1 }}>
        {on ? "on" : "off"}
      </span>
      <span className="tiny">{on ? yes : no}</span>
    </div>
  );
}
