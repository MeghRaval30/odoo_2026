// Application root: hash routing, auth gate, and the screen table.
//
// Screens not yet built render a Placeholder rather than 404ing, so the top bar
// is fully explorable during the demo and the next session can see at a glance
// what is still outstanding.

import { useEffect } from "react";
import Shell from "./components/Shell";
import Dashboard from "./screens/Dashboard";
import Login from "./screens/Login";
import { auth } from "./api";
import { navigate, useHashRoute } from "./lib/router";

function Placeholder({ title, task }) {
  return (
    <div className="page">
      <div className="page-head">
        <h1>{title}</h1>
        <span className="sub">{task}</span>
      </div>
      <div className="card">
        <div className="empty">
          This screen is not built yet.
          <div className="tiny mt">
            The API behind it already works — see the task board for {task}.
          </div>
        </div>
      </div>
    </div>
  );
}

const SCREENS = {
  dashboard: { title: "Payroll Dashboard", component: Dashboard },
  employees: { title: "Employees", task: "T-033" },
  contracts: { title: "Contracts", task: "T-034" },
  schedules: { title: "Working Schedules", task: "T-035" },
  attendance: { title: "Attendance", task: "T-036" },
  timeoff: { title: "Time Off Requests", task: "T-038" },
  allocations: { title: "Allocations", task: "T-038" },
  "timeoff-types": { title: "Time Off Types", task: "T-038" },
  payroll: { title: "Payruns", task: "T-041 / T-042" },
  payslips: { title: "Payslips", task: "T-043" },
  "salary-structures": { title: "Salary Structures", task: "T-040" },
  "salary-rules": { title: "Salary Rules", task: "T-040" },
  departments: { title: "Departments", task: "T-033" },
  "job-positions": { title: "Job Positions", task: "T-033" },
  "work-locations": { title: "Work Locations", task: "T-033" },
  users: { title: "User Management", task: "T-045" },
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

  const screen = SCREENS[head];

  return (
    <Shell route={route}>
      {screen ? (
        screen.component ? (
          <screen.component route={route} />
        ) : (
          <Placeholder title={screen.title} task={screen.task} />
        )
      ) : (
        <div className="page">
          <div className="card">
            <div className="empty">
              Nothing here.
              <div className="tiny mt">
                <a href="#/dashboard">Go to the dashboard</a>
              </div>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
