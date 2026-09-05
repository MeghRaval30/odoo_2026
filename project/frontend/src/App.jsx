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

export default function App() {
  const route = useHashRoute();
  const signedIn = Boolean(auth.token);
  const head = route.parts[0] || "";

  // The navigation tree and capability list are served by /me, so a session
  // that was opened before a role change — or before this build shipped — has
  // to re-read them. Without this a stored user from an older sign-in would
  // render the fallback menu forever.
  const [ready, setReady] = useState(() => Boolean(auth.user?.navigation));

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    api
      .refreshMe()
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
      {Screen ? (
        <Screen route={route} />
      ) : (
        <div className="page">
          <div className="card">
            <div className="empty">
              Not found. <a href="#/dashboard">Go to dashboard</a>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
