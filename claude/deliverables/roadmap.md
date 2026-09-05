# FUTURE ROADMAP

A required hackathon deliverable: what we would build next given more time.

> **STATUS: OUTLINE.** Refine before submission (T-061). Session 01 produced a
> full survey of world-class HR and payroll platforms; the strongest candidates
> from it are captured here.

**Framing for the judges:** everything below is a deliberate deferral, not an
oversight. We chose depth on the integration rules — period-correct contract
resolution, allocation-gated leave, sequenced rule computation, pre-finalization
validation — over breadth of modules.

---

## Near term — completing the payroll story

- **Off-cycle payruns** for bonuses, corrections and final settlements
- **Retroactive and arrear processing** when a backdated change lands in a closed
  period
- **Pro-ration** for mid-period joiners, leavers and structure changes
- **Salary revision workflow** with approval and effective dating
- **Loans and advances** with automatic EMI recovery inside payroll
- **Bank transfer file export** (NEFT / NACH) and payment-gateway integration
- **Leave encashment** at year end and at exit, flowing into the payslip

## Compliance depth

- Income tax computation with regime selection, plus an employee declaration
  portal for investment proofs
- Statutory filings: PF ECR, ESI returns, Professional Tax, Form 16 / 24Q
- Automatic statutory-rate updates when legislation changes
- Gratuity and end-of-service accrual

## Workforce management

- Shift rostering with swap requests and coverage-gap alerts
- Attendance **regularization** requests with an approval chain
- Biometric and RFID device integration
- Geo-fenced mobile attendance for field staff
- Multi-level and conditional leave approval chains, with delegation when an
  approver is away
- Holiday calendars per location

## Talent lifecycle

- Recruitment / ATS: requisitions, pipeline, interview scheduling, offers
- Structured onboarding and offboarding checklists with asset tracking and full
  and final settlement
- Performance: goals and OKRs, review cycles, 360° feedback, 9-box grid, with the
  review outcome feeding a salary revision
- Learning management with compliance training and certification expiry

## Platform

- **Effective-dated records throughout**, so any record can be viewed as of any
  past date — the single biggest architectural differentiator in enterprise HR
- Full field-level audit trail: who changed what, when, from what value
- Accounting integration posting payroll journal entries to the general ledger
- REST API with webhooks, and a mobile app covering the three actions people
  actually do on a phone: attendance, leave, payslip
- Predictive analytics: attrition risk scoring, headcount forecasting
- A conversational assistant for policy and leave-balance questions
- Multi-company and multi-currency payroll
