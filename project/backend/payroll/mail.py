"""Bulk payslip email from a payrun (PRD-5.9.5)."""

from django.conf import settings
from django.core.mail import EmailMessage

from .pdf import build_payslip_pdf


def send_payslip_email(payslip) -> bool:
    employee = payslip.employee
    if not employee.work_email:
        return False

    subject = (f"Payslip for {payslip.period_start:%B %Y} — "
               f"{employee.company.name}")
    body = (
        f"Dear {employee.first_name},\n\n"
        f"Please find attached your payslip for "
        f"{payslip.period_start:%d %b %Y} to {payslip.period_end:%d %b %Y}.\n\n"
        f"  Payslip number : {payslip.number}\n"
        f"  Worked days    : {payslip.worked_days} of {payslip.expected_days}\n"
        f"  Gross salary   : INR {payslip.gross:,.2f}\n"
        f"  Deductions     : INR {payslip.deductions:,.2f}\n"
        f"  Net salary     : INR {payslip.net:,.2f}\n\n"
        f"This is an automated message from {employee.company.name} Payroll.\n"
    )

    message = EmailMessage(
        subject=subject, body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[employee.work_email],
    )
    filename = f"payslip-{payslip.number.replace('/', '-')}.pdf"
    message.attach(filename, build_payslip_pdf(payslip), "application/pdf")
    message.send(fail_silently=False)
    return True


def send_payrun_payslips(payrun):
    """Send every payslip in the run. Returns (sent, skipped)."""
    sent = skipped = 0
    for payslip in payrun.payslips.select_related("employee", "employee__company"):
        try:
            if send_payslip_email(payslip):
                sent += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1
    return sent, skipped
