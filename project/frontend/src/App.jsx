// Application root: hash routing, auth gate, and the screen table.

import { useEffect, useState } from "react";
import Shell from "./components/Shell";
import Allocations from "./screens/Allocations";
import Attendance from "./screens/Attendance";
import Contracts from "./screens/Contracts";
import DashboardRouter from "./screens/DashboardRouter";
import Employees from "./screens/Employees";
import Holidays from "./screens/Holidays";
import Login from "./screens/Login";
import MyPayslips from "./screens/MyPayslips";
import Payruns from "./screens/Payruns";
import Payslips from "./screens/Payslips";
import Profile from "./screens/Profile";
import { Departments, JobPositions, WorkLocations } from "./screens/Reference";
import Reports from "./screens/Reports";
import { SalaryRules, SalaryStructures } from "./screens/SalaryConfig";
import Schedules from "./screens/Schedules";
import Security, { AuditLog } from "./screens/Security";
import TimeOff from "./screens/TimeOff";
import TimeOffTypes from "./screens/TimeOffTypes";
import Users from "./screens/Users";
import { api, auth } from "./api";
import { navigate, useHashRoute } from "./lib/router";

const SCREENS = {
  dashboard: DashboardRouter,
  profile: Profile,
  employees: Employees,
  contracts: Contracts,
  schedules: Schedules,
  attendance: Attendance,
  timeoff: TimeOff,
  allocations: Allocations,
  "timeoff-types": TimeOffTypes,
  payroll: Payruns,
  payslips: Payslips,
  "my-payslips": MyPayslips,
  "salary-structures": SalaryStructures,
  "salary-rules": SalaryRules,
  departments: Departments,
  "job-positions": JobPositions,
  "work-locations": WorkLocations,
  holidays: Holidays,
  reports: Reports,
  users: Users,
  security: Security,
  audit: AuditLog,
};

// Routes reachable from the profile menu rather than the top bar, plus the
// dashboard every account has. Everything else is judged against the
// navigation tree the server built for this account.
const ALWAYS = new Set(["dashboard", "profile", "my-payslips"]);

// Routes whose *detail* view is legitimately reachable by someone who may not
// see the list. `/payslips` is the payroll operator's index and is gated on
// `payslip.read.all`; `/payslips/68` is one record, and the payslip queryset
// narrows to the caller's own employee unless they hold that capability. So an
// employee following Open from My Payslips reaches their own slip, and a
// foreign id 404s at the server rather than being guessed at here.
const OWN_SCOPED_DETAIL = new Set(["payslips"]);

/**
 * Is this account allowed to open this screen?
 *
 * The answer is read off the navigation `/api/auth/me/` already pruned, rather
 * than from a second copy of the capability table kept here — a second copy is
 * how a menu and a screen drift apart. A menu the account cannot use is absent
 * (D-028), so a route that is absent from the tree is a route it may not open,
 * whether it was reached by typing the URL or by a stale bookmark.
 *
 * This is presentation, not enforcement: the server 403s regardless. What it
 * buys is that a refused screen says so in one clause instead of rendering an
 * empty payroll table above a permission error.
 */
function reachable(route) {
  const head = route.parts[0] || "";
  if (ALWAYS.has(head)) return true;
  const nav = auth.user?.navigation || [];
  const paths = new Set();
  for (const group of nav) {
    if (group.to) paths.add(group.to.replace(/^\//, ""));
    for (const item of group.items || []) paths.add(item.to.replace(/^\//, ""));
  }
  if (paths.has(head)) return true;
  return OWN_SCOPED_DETAIL.has(head) && route.parts.length > 1;
}

export default function App() {
  const route = useHashRoute();
  const signedIn = Boolean(auth.token);
  const head = route.parts[0] || "";

  // The navigation tree and capability list are served by /me, so a session
  // that was opened before a role change — or before this build shipped — has
  // to re-read them. Without this a stored user from an older sign-in would
  // render the fallback menu forever.
  const [ready, setReady] = useState(() => Boolean(auth.user?.navigation));

  // refreshMe writes the fresh account into storage, which React cannot see.
  // Without bumping something, a session that already had a cached navigation
  // rendered before the fetch resolved and then never re-rendered, so a role
  // change showed up one reload late -- the menu was right in the response and
  // wrong on the screen.
  const [, setRevision] = useState(0);

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    api
      .refreshMe()
      .then(() => !cancelled && setRevision((n) => n + 1))
      .catch(() => null)
      .finally(() => !cancelled && setReady(true));
    return () => {
      cancelled = true;
    };
  }, [signedIn]);

  // Redirects live in an effect so they happen after render rather than
  // mutating location during it.
  useEffect(() => {
    if (!signedIn && head !== "login") {
      navigate("/login");
    } else if (signedIn && (head === "login" || head === "")) {
      navigate("/dashboard");
    }
  }, [signedIn, head]);

  if (head === "login") return <Login />;

  if (!signedIn || !ready) {
    return (
      <div className="login-wrap">
        <span className="spinner" />
      </div>
    );
  }

  const Screen = SCREENS[head];

  return (
    <Shell route={route}>
      {!Screen ? (
        <div className="page">
          <div className="card">
            <div className="empty">
              Not found. <a href="#/dashboard">Go to dashboard</a>
            </div>
          </div>
        </div>
      ) : reachable(route) ? (
        <Screen route={route} />
      ) : (
        <div className="page">
          <div className="card">
            <div className="empty">Not available for this account.</div>
          </div>
        </div>
      )}
    </Shell>
  );
}
