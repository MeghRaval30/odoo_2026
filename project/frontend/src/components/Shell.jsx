// Application shell: the six-item top bar the spec requires, plus the
// signed-in user chip.
//
// The menu set is fixed by the product spec (T-031):
//   Employees v | Contracts v | Attendance | Time Off v | Payroll | Reports
// Time Off entries appear *only* inside the Time Off dropdown -- they are not
// promoted to the top level.

import { useEffect, useRef, useState } from "react";
import { auth, api } from "../api";
import { href, navigate } from "../lib/router";
import AttendanceWidget from "./AttendanceWidget";

const MENUS = [
  {
    key: "employees",
    label: "Employees",
    match: ["employees", "departments", "job-positions", "work-locations", "schedules"],
    items: [
      { to: "/employees", label: "Employees" },
      { to: "/schedules", label: "Working Schedules" },
      { to: "/departments", label: "Departments" },
      { to: "/job-positions", label: "Job Positions" },
      { to: "/work-locations", label: "Work Locations" },
    ],
  },
  {
    key: "contracts",
    label: "Contracts",
    match: ["contracts", "salary-structures", "salary-rules"],
    items: [
      { to: "/contracts", label: "Contracts" },
      { to: "/salary-structures", label: "Salary Structures", perm: "can_configure_payroll" },
      { to: "/salary-rules", label: "Salary Rules", perm: "can_configure_payroll" },
    ],
  },
  { key: "attendance", label: "Attendance", to: "/attendance", match: ["attendance"] },
  {
    key: "timeoff",
    label: "Time Off",
    match: ["timeoff", "allocations", "timeoff-types"],
    items: [
      { to: "/timeoff", label: "Time Off Requests" },
      { to: "/allocations", label: "Allocations" },
      { to: "/timeoff-types", label: "Time Off Types", perm: "is_admin" },
    ],
  },
  {
    key: "payroll",
    label: "Payroll",
    match: ["payroll", "payslips"],
    items: [
      { to: "/payroll", label: "Payruns", perm: "can_run_payroll" },
      { to: "/payslips", label: "Payslips", perm: "can_run_payroll" },
    ],
  },
  { key: "reports", label: "Reports", to: "/dashboard", match: ["dashboard"] },
];

function initials(user) {
  const source = user?.employee_name || user?.email || "?";
  return source
    .split(/[\s@._]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export default function Shell({ route, children }) {
  const [openMenu, setOpenMenu] = useState(null);
  const [userOpen, setUserOpen] = useState(false);
  const barRef = useRef(null);
  const user = auth.user;
  const active = route.parts[0] || "";

  // Any click that is not inside the top bar closes whatever is open.
  useEffect(() => {
    const onDocClick = (event) => {
      if (barRef.current && !barRef.current.contains(event.target)) {
        setOpenMenu(null);
        setUserOpen(false);
      }
    };
    const onEsc = (event) => {
      if (event.key === "Escape") {
        setOpenMenu(null);
        setUserOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  // Navigating always dismisses the menus.
  useEffect(() => {
    setOpenMenu(null);
    setUserOpen(false);
  }, [route.path]);

  const signOut = async () => {
    try {
      await api.logout();
    } finally {
      navigate("/login");
    }
  };

  const visible = (item) => !item.perm || auth.can(item.perm);

  return (
    <div className="app">
      <div className="topbar" ref={barRef}>
        <div className="brand">
          People<span>Pay</span>360
        </div>

        {MENUS.map((menu) => {
          const isActive = menu.match.includes(active);

          if (menu.to) {
            return (
              <a
                key={menu.key}
                className={`navitem${isActive ? " active" : ""}`}
                href={href(menu.to)}
              >
                {menu.label}
              </a>
            );
          }

          const items = menu.items.filter(visible);
          if (!items.length) return null;

          return (
            <div
              key={menu.key}
              className={`navitem${isActive ? " active" : ""}`}
              onClick={() => setOpenMenu(openMenu === menu.key ? null : menu.key)}
            >
              {menu.label} <span className="tiny faint">&#9662;</span>
              {openMenu === menu.key && (
                <div className="dropdown" onClick={(e) => e.stopPropagation()}>
                  {items.map((item) => (
                    <a key={item.to} href={href(item.to)}>
                      {item.label}
                    </a>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        <div className="spacer" />

        <AttendanceWidget />

        <div
          className="navitem"
          style={{ position: "relative" }}
          onClick={() => setUserOpen(!userOpen)}
        >
          <div className="row" style={{ gap: 8 }}>
            <div className="avatar" style={{ width: 28, height: 28, fontSize: 11 }}>
              {initials(user)}
            </div>
            <span className="tiny">{user?.employee_name || user?.email}</span>
          </div>

          {userOpen && (
            <div className="popover" onClick={(e) => e.stopPropagation()}>
              <div className="tiny faint">Signed in as</div>
              <div style={{ marginBottom: 4 }}>{user?.email}</div>
              <div className="row mb" style={{ gap: 5 }}>
                {(user?.roles || []).map((role) => (
                  <span key={role} className="badge blue">
                    {role}
                  </span>
                ))}
              </div>
              {auth.can("is_admin") && (
                <a className="tiny" href={href("/users")}>
                  User Management
                </a>
              )}
              <button className="mt" style={{ width: "100%" }} onClick={signOut}>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {children}
    </div>
  );
}
