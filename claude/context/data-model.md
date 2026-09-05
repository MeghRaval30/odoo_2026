# DATA MODEL

**Version** 1.0 · **Author** Michael (session 01) · **Status** Ready to implement
**Stack** Django 5 + DRF + PostgreSQL *(D-001)* · **Locale** India, ₹ *(D-003)*

> Field lists derive from the mockup wireframes recorded in
> `claude/context/product-spec.md` §4. Constraints derive from the graded
> business rules in `claude/context/prd.md` §4.

---

## 1. Entity relationship map

```
Company
  ├── Department ──────── Employee.department
  ├── JobPosition ─────── Employee.job_position
  ├── WorkLocation ────── Employee.work_location
  └── WorkingSchedule
          └── ScheduleLine        (day, start, end, break)

User (auth) ──1:1── Employee
                      ├── manager ──> Employee            (self-referential)
                      ├── Contract              (many, period-scoped)
                      │      ├── working_schedule ──> WorkingSchedule
                      │      └── salary_structure ──> SalaryStructure
                      ├── Attendance            (many)
                      ├── Allocation            (many)
                      │      └── time_off_type ──> TimeOffType
                      ├── TimeOffRequest        (many)
                      │      ├── time_off_type   ──> TimeOffType
                      │      └── allocation_used ──> Allocation
                      └── Payslip               (many)

SalaryStructure
      └── SalaryRule            (many, ordered by sequence)

Payrun
  ├── salary_structure ──> SalaryStructure
  └── Payslip                   (many)
          ├── employee ──> Employee
          ├── contract ──> Contract     (resolved at compute time)
          ├── PayslipLine             (many, one per executed rule)
          └── PayslipWarning          (many)
```

## 2. Conventions

| Concern | Rule |
|---|---|
| Money | `DECIMAL(12,2)` — **never** float *(PRD-7.6)* |
| Hours | `DECIMAL(6,2)` |
| Percentages | `DECIMAL(6,3)` |
| Timestamps | timezone-aware, stored UTC |
| Soft delete | `active` boolean where the mockup shows an Active flag |
| Audit | `created_at`, `updated_at` on every table |
| Primary keys | `BigAutoField` |
| Naming | Django default `app_model` tables; snake_case columns |

---

## 3. Organisation

### `Company`
| Field | Type | Notes |
|---|---|---|
| `name` | varchar(200) | e.g. "OXP Pvt Ltd" |
| `currency` | varchar(3) | default `INR` |
| `timezone` | varchar(64) | default `Asia/Kolkata` |
| `active` | bool | default true |

### `Department`
| Field | Type | Notes |
|---|---|---|
| `name` | varchar(120) | Finance, HR, Engineering, Sales, IT |
| `company` | FK → Company | |
| `manager` | FK → Employee, null | `on_delete=SET_NULL` |
| `active` | bool | |

**Constraint:** `unique(company, name)`

### `JobPosition`
`name` varchar(120) · `department` FK → Department, null · `company` FK · `active` bool

### `WorkLocation`
`name` varchar(120) · `company` FK · `active` bool

---

## 4. Working schedules

### `WorkingSchedule`
| Field | Type | Notes |
|---|---|---|
| `name` | varchar(120) | "40 Hours / Week", "Night Shift" |
| `company` | FK → Company | |
| `calendar_type` | choice | `FIXED` / `VARIABLE` |
| `timezone` | varchar(64) | |
| `active` | bool | |

**Derived properties — never stored as editable input** *(PRD-4.2.2)*:
```python
@property
def hours_per_week(self):
    return sum(line.hours for line in self.lines.all())

@property
def days_per_week(self):
    return self.lines.values('day_of_week').distinct().count()
```

### `ScheduleLine`
| Field | Type | Notes |
|---|---|---|
| `schedule` | FK → WorkingSchedule, `related_name='lines'` | cascade |
| `day_of_week` | smallint | 0 = Monday … 6 = Sunday |
| `start_time` | time | |
| `end_time` | time | |
| `break_minutes` | smallint | default 0 |

**Derived:** `hours = (end_time − start_time) − break_minutes`
**Constraint:** `CHECK (end_time > start_time)`
**Ordering:** `day_of_week, start_time`

> A day may have multiple lines (split shifts). `days_per_week` therefore counts
> *distinct* days, not line count.

---

## 5. People

### `User` — `AbstractBaseUser`
| Field | Type | Notes |
|---|---|---|
| `email` | varchar(254), unique | the login identifier |
| `employee` | OneToOne → Employee, null | *(PRD-3.3)* |
| `is_active`, `is_staff`, `is_superuser` | bool | |
| `roles` | M2M → Role | |

> Accounts are **separate from** Employee records but linked. An Employee may
> exist with no account; an account requires an employee link *(PRD-3.3)*.
> Users cannot modify their own `roles` *(PRD-3.2)*.

### `Role`
`code` choice, unique: `EMPLOYEE` / `HR_MANAGER` / `PAYROLL_USER` / `PAYROLL_MANAGER` / `ADMIN` · `name` varchar(60)
Permission matrix: `claude/context/prd.md` §3.2.

### `Employee`
| Field | Type | Notes |
|---|---|---|
| `employee_code` | varchar(20), unique | auto `EMP/2026/0001` |
| `first_name`, `last_name` | varchar(80) | |
| `work_email` | varchar(254), unique | |
| `work_phone` | varchar(20), null | |
| `company` | FK → Company | |
| `department` | FK → Department, null | `SET_NULL` |
| `job_position` | FK → JobPosition, null | `SET_NULL` |
| `manager` | FK → **self**, null | `SET_NULL`, `related_name='reports'` |
| `work_location` | FK → WorkLocation, null | |
| `working_schedule` | FK → WorkingSchedule, null | default; contract may override |
| `employee_type` | choice | `FULL_TIME` / `PART_TIME` / `INTERN` / `CONTRACTOR` |
| `date_of_joining` | date | |
| `bank_account_number` | varchar(34), **null** | null ⇒ `A/C missing` warning *(PRD-4.5.2)* |
| `bank_ifsc` | varchar(11), null | |
| `pan_number` | varchar(10), null | |
| `date_of_birth`, `gender`, `personal_email`, `personal_phone`, `address` | | Private Information tab |
| `active` | bool | |

**Indexes:** `department`, `active`, `employee_type`
**Guard:** prevent a manager cycle (`manager` chain must not reach self).

**Smart-button counts** *(PRD-5.2.4)* — annotate in the queryset, never store:
```python
Employee.objects.annotate(
    contract_count=Count('contracts', distinct=True),
    attendance_count=Count('attendances', distinct=True),
    timeoff_count=Count('timeoff_requests', distinct=True),
    allocation_count=Count('allocations', distinct=True),
)
```

---

## 6. Contracts — graded rule #1

### `Contract`
| Field | Type | Notes |
|---|---|---|
| `reference` | varchar(24), unique | auto `CON/2026/0042` |
| `employee` | FK → Employee, `related_name='contracts'` | |
| `department` | FK → Department, null | snapshot at signing |
| `job_position` | FK → JobPosition, null | |
| `start_date` | date | |
| `end_date` | date, **null** | null ⇒ open-ended |
| `wage` | DECIMAL(12,2) | monthly gross wage |
| `working_schedule` | FK → WorkingSchedule | |
| `salary_structure` | FK → SalaryStructure, null | null ⇒ `No structure` warning |
| `structure_type` | varchar(60) | "Employee Salary" |
| `state` | choice | `DRAFT` / `RUNNING` / `EXPIRED` / `CANCELLED` |
| `notes` | text, null | |

**Constraints**
- `CHECK (end_date IS NULL OR end_date >= start_date)`
- **No overlapping `RUNNING` contracts per employee** *(PRD-4.1.1)*. Postgres
  exclusion constraint on a daterange, which enforces it at the database level
  rather than trusting application code:

```sql
ALTER TABLE hr_contract ADD CONSTRAINT no_overlapping_running_contracts
EXCLUDE USING gist (
  employee_id WITH =,
  daterange(start_date, COALESCE(end_date, 'infinity'::date), '[]') WITH &&
) WHERE (state = 'RUNNING');
```
Requires `CREATE EXTENSION btree_gist;`

**Resolution — the single most important query in the system** *(PRD-4.1.2)*:
```python
def resolve_for_period(employee, period_start, period_end):
    """The contract valid for the payrun period — by period, never by recency."""
    return (Contract.objects
            .filter(employee=employee,
                    state='RUNNING',
                    start_date__lte=period_end)
            .filter(Q(end_date__gte=period_start) | Q(end_date__isnull=True))
            .order_by('-start_date')
            .first())
```
Returning `None` excludes the employee from the payrun and raises a
`No contract` warning *(PRD-4.1.3)*.

**Index:** `(employee, state, start_date, end_date)`

---

## 7. Attendance

### `Attendance`
| Field | Type | Notes |
|---|---|---|
| `employee` | FK → Employee, `related_name='attendances'` | |
| `check_in` | datetime | |
| `check_out` | datetime, **null** | null ⇒ session open |
| `status` | choice | `PRESENT` / `ABSENT` / `OVERTIME` / `HALF_DAY` |
| `overtime_hours` | DECIMAL(6,2) | default 0 |
| `is_manually_edited` | bool | set on HR correction *(PRD-5.5.4)* |
| `edited_by` | FK → User, null | |
| `notes` | text, null | |

**Derived:**
```python
@property
def worked_hours(self):
    if not self.check_out:
        return Decimal('0.00')
    return round(Decimal((self.check_out - self.check_in).total_seconds()) / 3600, 2)
```

**Constraints**
- `CHECK (check_out IS NULL OR check_out > check_in)`
- At most one open session per employee — partial unique index:
  `UNIQUE (employee) WHERE check_out IS NULL`

**Index:** `(employee, check_in)`

> The widget *(PRD-5.5.5)* reads the open session: present ⇒ show **Check Out**
> with live elapsed time; absent ⇒ show **Check In**.

---

## 8. Time off — graded rule #3

### `TimeOffType`
| Field | Type | Notes |
|---|---|---|
| `name` | varchar(120) | Paid Time Off, Sick Leave, Comp Off |
| `code` | varchar(20), unique | |
| `unit` | choice | `DAYS` / `HOURS` |
| `requires_allocation` | bool | **the gate** *(PRD-4.3.2)* |
| `approval` | choice | `NONE` / `MANAGER` / `OFFICER` |
| `is_paid` | bool | false ⇒ contributes LOP *(PRD-4.6.2)* |
| `work_entry_code` | varchar(40), null | "Leave Work Entry" |
| `color` | varchar(20) | display colour |
| `active` | bool | |
| `description` | text, null | |

### `Allocation`
| Field | Type | Notes |
|---|---|---|
| `employee` | FK → Employee, `related_name='allocations'` | |
| `time_off_type` | FK → TimeOffType | |
| `name` | varchar(120) | "Paid Time Off 2026" |
| `allocated` | DECIMAL(6,2) | in the type's unit |
| `valid_from`, `valid_to` | date / date null | |
| `state` | choice | `DRAFT` / `TO_APPROVE` / `APPROVED` / `REFUSED` |
| `description` | text, null | |

**Derived — never stored** *(PRD-4.3.3)*:
```python
@property
def taken(self):
    return (self.consuming_requests
            .filter(state='APPROVED')
            .aggregate(t=Coalesce(Sum('duration'), Decimal('0')))['t'])

@property
def remaining(self):
    return self.allocated - self.taken
```

**Constraint:** `CHECK (allocated > 0)`
**Index:** `(employee, time_off_type, state)`

> Only `APPROVED` allocations create balance. Draft and refused ones grant
> nothing.

### `TimeOffRequest`
| Field | Type | Notes |
|---|---|---|
| `employee` | FK → Employee, `related_name='timeoff_requests'` | |
| `time_off_type` | FK → TimeOffType | |
| `allocation_used` | FK → Allocation, null, `related_name='consuming_requests'` | *(PRD-4.3.4)* |
| `date_from`, `date_to` | date | |
| `duration` | DECIMAL(6,2) | computed, excluding weekends and holidays |
| `half_day` | choice, null | `FIRST` / `SECOND` |
| `state` | choice | `DRAFT` / `TO_APPROVE` / `APPROVED` / `REFUSED` / `CANCELLED` |
| `reason` | text, null | |
| `approver` | FK → User, null | |
| `approved_at` | datetime, null | |

**Validation on submit** *(PRD-4.3.2)*:
```python
def clean(self):
    if self.time_off_type.requires_allocation:
        alloc = self.find_valid_allocation()
        if alloc is None:
            raise ValidationError(
                f"No approved {self.time_off_type.name} allocation covering "
                f"{self.date_from}–{self.date_to}.")
        if alloc.remaining < self.duration:
            raise ValidationError(
                f"Insufficient balance: {alloc.remaining} remaining, "
                f"{self.duration} requested.")
        self.allocation_used = alloc
```

**Constraints**
- `CHECK (date_to >= date_from)`
- `CHECK (duration > 0)`

Cancelling or refusing an approved request restores balance automatically,
because `taken` is derived from approved requests only *(PRD-4.3.5)*.

### `Holiday`
`name` varchar(120) · `date` date · `company` FK · `unique(company, date)`
Excluded from `TimeOffRequest.duration` and from expected working days.

---

## 9. Payroll configuration — graded rule #4

### `SalaryStructure`
`name` varchar(120) · `code` varchar(20) unique · `company` FK · `active` bool
Derived: `rule_count`, `employee_count` (annotated, not stored).

### `SalaryRule`
| Field | Type | Notes |
|---|---|---|
| `structure` | FK → SalaryStructure, `related_name='rules'` | |
| `name` | varchar(120) | "Basic Salary" |
| `code` | varchar(20) | `BASIC`, `HRA`, `GROSS`, `PF`, `NET` |
| `category` | choice | `BASIC` / `ALLOWANCE` / `GROSS` / `DEDUCTION` / `NET` |
| `sequence` | integer | 1, 10, 20 … 110 — **execution order** |
| `computation` | choice | `FIXED` / `PERCENTAGE` / `FORMULA` |
| `amount` | DECIMAL(12,2), null | for `FIXED` |
| `percentage` | DECIMAL(6,3), null | for `PERCENTAGE`, % of contract wage |
| `formula` | text, null | for `FORMULA` |
| `condition` | text, null | optional gate; blank ⇒ always applies |
| `quantity` | DECIMAL(6,2) | default 1 |
| `appears_on_payslip` | bool | default true |
| `is_employer_cost` | bool | employer contribution, excluded from net |
| `active` | bool | |

**Constraints**
- `unique(structure, code)`
- `CHECK` that the value field matching `computation` is non-null

**Ordering:** `sequence, id`

**Seed rule set** — matches the mockup exactly:

| Seq | Name | Code | Category | Computation |
|---|---|---|---|---|
| 1 | Basic Salary | `BASIC` | BASIC | 50% of wage |
| 10 | House Rent Allowance | `HRA` | ALLOWANCE | 40% of BASIC |
| 20 | Standard Allowance | `STD` | ALLOWANCE | fixed ₹10,000 |
| 30 | Performance Bonus | `BONUS` | ALLOWANCE | fixed |
| 40 | Leave Travel Allowance | `LTA` | ALLOWANCE | fixed |
| 50 | Fixed Allowance | `FIX` | ALLOWANCE | fixed |
| 60 | **Gross Salary** | `GROSS` | GROSS | `categories['BASIC'] + categories['ALLOWANCE']` |
| 70 | Labour Welfare Fund | `LWF` | DEDUCTION | fixed ₹20 |
| 80 | Provident Fund | `PF` | DEDUCTION | 12% of BASIC |
| 90 | ESIC | `ESIC` | DEDUCTION | 0.75% of GROSS, if GROSS ≤ 21000 |
| 100 | Professional Tax | `PT` | DEDUCTION | fixed ₹200 |
| 110 | **Net Salary** | `NET` | NET | `categories['GROSS'] - categories['DEDUCTION']` |

---

## 10. Payroll processing

### `Payrun`
| Field | Type | Notes |
|---|---|---|
| `name` | varchar(120) | "February 2026" |
| `company` | FK → Company | |
| `salary_structure` | FK → SalaryStructure | |
| `period_start`, `period_end` | date | |
| `employee_type` | choice, null | scope filter from wizard step 1 |
| `state` | choice | `DRAFT` / `COMPUTED` / `VALIDATED` / `PAID` |
| `computed_at`, `validated_at`, `paid_at` | datetime, null | |
| `created_by` | FK → User | |

**Constraints:** `CHECK (period_end >= period_start)`; `PAID` is terminal and
read-only *(PRD-6)*.

### `Payslip`
| Field | Type | Notes |
|---|---|---|
| `payrun` | FK → Payrun, `related_name='payslips'` | cascade |
| `employee` | FK → Employee, `related_name='payslips'` | |
| `contract` | FK → Contract, null | **resolved at compute time** |
| `salary_structure` | FK → SalaryStructure | snapshot |
| `period_start`, `period_end` | date | |
| `worked_days` | DECIMAL(6,2) | from Attendance *(PRD-4.6.1)* |
| `expected_days` | DECIMAL(6,2) | from the working schedule |
| `lop_days` | DECIMAL(6,2) | unpaid leave *(PRD-4.6.2)* |
| `overtime_hours` | DECIMAL(6,2) | from Attendance *(PRD-4.6.3)* |
| `state` | choice | mirrors the payrun |
| `number` | varchar(30), unique | `PAY/2026/02/0042` |

**Constraint — the duplicate-payslip guard** *(PRD-4.5.2)*:
`unique(employee, period_start, period_end)`

**Derived from lines — never stored independently** *(PRD-4.4.8)*:
```python
@property
def gross(self):
    return self._category_total('GROSS')

@property
def net(self):
    return self._category_total('NET')
```

### `PayslipLine`
| Field | Type | Notes |
|---|---|---|
| `payslip` | FK → Payslip, `related_name='lines'` | cascade |
| `rule` | FK → SalaryRule, `SET_NULL` | |
| `name`, `code`, `category` | varchar | **snapshotted** — the payslip must stay readable if the rule is later edited |
| `sequence` | integer | |
| `quantity`, `rate`, `amount` | DECIMAL | |

**Constraint:** `unique(payslip, code)` — this is what makes recompute
idempotent *(PRD-6.1)*. Recompute deletes and rewrites lines; it never appends.

### `PayslipWarning`
| Field | Type | Notes |
|---|---|---|
| `payslip` | FK → Payslip, null, `related_name='warnings'` | |
| `payrun` | FK → Payrun, `related_name='warnings'` | |
| `employee` | FK → Employee, null | for employees excluded from the run |
| `code` | choice | `AC_MISSING` / `DUPLICATE` / `NO_CONTRACT` / `NEGATIVE_NET` / `NO_STRUCTURE` |
| `message` | varchar(255) | |
| `severity` | choice | `WARNING` / `ERROR` — only `ERROR` blocks Validate |

Warnings are **regenerated on every compute**, never accumulated.

---

## 11. The rule engine

Ordered evaluation, each result visible to later rules *(PRD-4.4.4)*:

```python
def compute_payslip(payslip):
    payslip.lines.all().delete()          # idempotent — PRD-6.1
    contract = payslip.contract
    categories = defaultdict(Decimal)     # running totals by category
    rules_by_code = {}

    ctx = {
        'contract': contract,
        'employee': payslip.employee,
        'payslip': payslip,               # worked_days, lop_days, overtime_hours
        'wage': contract.wage,
        'categories': categories,
        'rules': rules_by_code,
    }

    for rule in payslip.salary_structure.rules.filter(active=True).order_by('sequence'):
        if rule.condition and not safe_eval(rule.condition, ctx):
            continue
        try:
            amount = evaluate(rule, ctx)          # FIXED | PERCENTAGE | FORMULA
        except Exception as exc:
            record_error(payslip, rule, exc)      # PRD-4.4.7 — never abort the run
            continue

        PayslipLine.objects.create(
            payslip=payslip, rule=rule,
            name=rule.name, code=rule.code, category=rule.category,
            sequence=rule.sequence, quantity=rule.quantity, amount=amount)

        categories[rule.category] += amount
        rules_by_code[rule.code] = amount
```

**Sandboxing** *(PRD-4.4.6)* — restricted `eval` with `__builtins__` emptied, an
allowlist of names, and a hard reject of any source containing `__`, `import`,
`open`, `exec`, `eval`. Timebox this: 45 minutes, then fall back to `FIXED` +
`PERCENTAGE` only *(PRD §10 risks)*.

---

## 12. Derived, never stored

Deriving these is explicitly graded. Storing any of them as an editable input is
a correctness bug.

| Field | Source |
|---|---|
| `WorkingSchedule.hours_per_week` / `days_per_week` | ScheduleLine aggregate |
| `ScheduleLine.hours` | end − start − break |
| `Attendance.worked_hours` | check_out − check_in |
| `Allocation.taken` / `remaining` | approved consuming requests |
| `Payslip.gross` / `net` | PayslipLine by category |
| `Payslip.worked_days` / `lop_days` / `overtime_hours` | Attendance + approved leave |
| Employee smart-button counts | queryset annotations |

---

## 13. Django app layout

```
project/backend/
├── config/          settings, urls, wsgi
├── core/            Company, Department, JobPosition, WorkLocation, Holiday
├── accounts/        User, Role, permissions
├── employees/       Employee, Contract, WorkingSchedule, ScheduleLine
├── attendance/      Attendance
├── timeoff/         TimeOffType, Allocation, TimeOffRequest
├── payroll/         SalaryStructure, SalaryRule, Payrun, Payslip,
│                    PayslipLine, PayslipWarning, engine.py, pdf.py
└── dashboard/       aggregation endpoints (no models of its own)
```

## 14. Migration order

`core` → `accounts` → `employees` → `attendance` → `timeoff` → `payroll`

`btree_gist` must be enabled before the Contract exclusion constraint:

```python
from django.contrib.postgres.operations import BtreeGistExtension

class Migration(migrations.Migration):
    operations = [BtreeGistExtension(), ...]
```

## 15. Seed data targets *(PRD-7.1)*

| Item | Target |
|---|---|
| Companies | 1 (OXP Pvt Ltd) |
| Departments | 5 — Finance, HR, Engineering, Sales, IT |
| Employees | 22 |
| Employees with 2+ contracts | ≥ 2 — proves period-based resolution |
| Employees with no bank account | ≥ 2 — triggers `A/C missing` on cue |
| Working schedules | 5 — matching the mockup names |
| Salary structures | 3 — Regular, Intern, Contractor |
| Salary rules | 12 on Regular, per §9 |
| Payroll history | 3 months — needed for the trend chart |
| Attendance | full coverage of the demo period, with gaps and overtime |
| Time off | mixed approved / pending, both allocation-required and not |
