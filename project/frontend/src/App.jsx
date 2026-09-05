// Application root: hash routing, auth gate, and the screen table.

import { useEffect } from "react";
import Shell from "./components/Shell";
import Allocations from "./screens/Allocations";
import Attendance from "./screens/Attendance";
import Contracts from "./screens/Contracts";
import Dashboard from "./screens/Dashboard";
import Employees from "./screens/Employees";
import Holidays from "./screens/Holidays";
import Login from "./screens/Login";
import Payruns from "./screens/Payruns";
import Payslips from "./screens/Payslips";
import { Departments, JobPositions, WorkLocations } from "./screens/Reference";
import { SalaryRules, SalaryStructures } from "./screens/SalaryConfig";
import Schedules from "./screens/Schedules";
import TimeOff from "./screens/TimeOff";
import TimeOffTypes from "./screens/TimeOffTypes";
import Users from "./screens/Users";
import { auth } from "./api";
import { navigate, useHashRoute } from "./lib/router";

const SCREENS = {
  dashboard: Dashboard,
  employees: Employees,
  contracts: Contracts,
  schedules: Schedules,
  attendance: Attendance,
  timeoff: TimeOff,
  allocations: Allocations,
  "timeoff-types": TimeOffTypes,
  payroll: Payruns,
  payslips: Payslips,
  "salary-structures": SalaryStructures,
  "salary-rules": SalaryRules,
  departments: Departments,
  "job-positions": JobPositions,
  "work-locations": WorkLocations,
  holidays: Holidays,
  users: Users,
};

export default function App() {
  const route = useHashRoute();
  const signedIn = Boolean(auth.token);
  const head = route.parts[0] || "";

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

  if (!signedIn) {
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
