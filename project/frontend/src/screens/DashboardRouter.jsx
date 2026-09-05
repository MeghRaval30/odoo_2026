// `#/dashboard` means a different screen depending on who is signed in.
//
// The server decides which, and says so in `/api/auth/me/` as `home_dashboard`.
// Doing it here from a list of role codes would be a second copy of the rules,
// and second copies drift.
//
// `#/dashboard/payroll` forces the payroll view for anyone entitled to it —
// that is the route the Admin screen and the Reports menu link to, so an
// administrator can reach the money view without it being their home.

import { auth } from "../api";
import AdminDashboard from "./AdminDashboard";
import HRDashboard from "./HRDashboard";
import MyDashboard from "./MyDashboard";
import PayrollDashboard from "./Dashboard";

export default function DashboardRouter({ route }) {
  const requested = route.parts[1];
  const home = auth.user?.home_dashboard || "employee";

  if (requested === "payroll") {
    return auth.has("dashboard.payroll") ? <PayrollDashboard /> : <MyDashboard />;
  }
  if (requested === "hr") {
    return auth.has("dashboard.hr") ? <HRDashboard /> : <MyDashboard />;
  }
  if (requested === "me") return <MyDashboard />;

  if (home === "admin") return <AdminDashboard />;
  if (home === "payroll") return <PayrollDashboard />;
  if (home === "hr") return <HRDashboard />;
  return <MyDashboard />;
}
