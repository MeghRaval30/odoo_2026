"""
Build the three demo spreadsheets the import studio is shown against.

Each file fails in a *different* way on purpose, because the point of the demo
is not "we can read a CSV" -- it is that the three failure modes a real company
actually arrives with are each handled by a different part of the pipeline:

  messy_startup_roster.csv   structural mess. Junk rows above the header, a
                             trailing total, Hinglish and abbreviated headers,
                             three date formats, three ways of writing rupees.
                             Exercises header detection and the transforms.

  legacy_hrms_export.xlsx    semantic mess. Structurally immaculate -- a machine
                             wrote it -- and wrong anyway: the salary column is
                             annual where the target field is monthly, blanks
                             are the literal string NULL, and the name arrives
                             pre-split. Exercises the profiler, which is the
                             only thing that can catch a number being 12x too
                             large by looking at its distribution.

  acquisition_northwind.csv  taxonomy mess. Clean file, different vocabulary --
                             "Business Unit" holding Technology / Revenue /
                             People Ops against our Engineering / Sales / HR --
                             and four people already on the roster. Exercises
                             value mapping and duplicate detection.

Deterministic: the RNG is seeded, so regenerating produces byte-identical files
and the demo script's figures stay true. ASCII only in both the data and the
output -- the Windows console is cp1252 and a rupee sign kills the command.
"""

import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))

# Four people who are already on the seeded roster, by the email the seed
# builds ("{first}@oxp.com"). The acquisition file reuses them so the duplicate
# detector has something real to find -- see below, they are written out with the
# same names the seed uses.
COLLISIONS = [
    ("John", "Dsouza", "john@oxp.com"),
    ("Priya", "Sharma", "priya@oxp.com"),
    ("Meera", "Iyer", "meera@oxp.com"),
    ("Billy", "Kyle", "billy@oxp.com"),
]


# ==========================================================================
# 1. The hand-made spreadsheet
# ==========================================================================

STARTUP_PEOPLE = [
    # name (as typed, casing deliberately inconsistent), dept, designation,
    # doj (format varies), wage (written three ways), phone, email, ac, ifsc, pan
    ("rajesh kumar",     "Engg", "Developer",         "15-03-2021", "Rs 45,000"),
    ("PRIYA NAIR",       "Engg", "Senior Developer",  "02/07/2019", "72,000"),
    ("  Anil Deshpande", "Sls",  "Sales Executive",   "2020-11-30", "38500/-"),
    ("Sneha Rao",        "Mktg", "Marketing Lead",    "11-01-2022", "Rs 65,000"),
    ("vikram Singh",     "Engg", "QA Engineer",       "23/08/2021", "Rs. 51,000"),
    ("Fatima Sheikh",    "HR",   "HR Executive",      "05-05-2020", "42,000"),
    ("Arjun MENON",      "Ops",  "Operations Analyst", "18/02/2022", "47500"),
    ("Kavya Reddy",      "Engg", "Developer",         "2021-06-14", "Rs 58,000"),
    ("  ROHIT Verma",    "Sls",  "Account Manager",   "09-09-2019", "68,000/-"),
    ("Divya Pillai",     "Mktg", "Content Writer",    "30/03/2023", "35,000"),
    ("Sameer Joshi",     "Engg", "Developer",         "12-12-2020", "Rs 54,500"),
    ("neha Bhatt",       "HR",   "Recruiter",         "07/07/2021", "40,000"),
    ("Imran Qureshi",    "Ops",  "Logistics Officer", "2022-04-19", "44,000"),
    ("Pooja Agarwal",    "Sls",  "Sales Executive",   "25-10-2022", "36,500"),
    ("Karthik Nair",     "Engg", "Senior Developer",  "03/03/2018", "Rs 88,000"),
    ("ANJALI Desai",     "Mktg", "Marketing Lead",    "16-06-2021", "62,000"),
    ("Suresh Babu",      "Ops",  "Operations Analyst", "2019-08-08", "49,000"),
    ("Ritu Malhotra",    "HR",   "HR Executive",      "21/11/2022", "41,500"),
    ("Gaurav Sinha",     "Engg", "Developer",         "14-02-2023", "Rs 52,000"),
    ("meena Krishnan",   "Sls",  "Sales Executive",   "28/05/2020", "39,000"),
    ("Tarun Bhandari",   "Engg", "QA Engineer",       "2021-09-27", "50,500"),
    ("Lakshmi Iyer",     "Mktg", "Content Writer",    "06-06-2022", "Rs 37,000"),
]


def _email_for(name, taken):
    """Emails as a small company actually writes them, with two omitted."""
    first = name.strip().split()[0].lower()
    candidate = "%s@brightloom.in" % first
    return candidate


def build_startup_roster(path):
    rng = random.Random(360)
    rows = []

    # Two rows of preamble and a blank one. This is the thing that breaks every
    # naive importer: the header is on line 3, not line 1.
    rows.append(["Brightloom Textiles Pvt Ltd - Employee Master", "", "", "", "",
                 "", "", "", "", "", ""])
    rows.append(["Updated till 31 Aug 2026 (internal use only)", "", "", "", "",
                 "", "", "", "", "", ""])
    rows.append(["", "", "", "", "", "", "", "", "", "", ""])
    rows.append(["Emp Naam", "Dept.", "Designation", "DOJ", "Sal (pm)",
                 "Mob No", "Email ID", "A/C No", "IFSC", "PAN", "Remarks"])

    remarks = ["", "good performer", "", "on notice", "", "", "confirmed", "",
               "", "probation", "", "", "", "", "", "", "", "", "", "", "", ""]

    for i, (name, dept, desig, doj, wage) in enumerate(STARTUP_PEOPLE):
        # Phones written two ways, because two people entered them.
        if i % 3 == 0:
            phone = "+91 %d%d" % (rng.randint(70, 99), rng.randint(10000000, 99999999))
        else:
            phone = "%d%d" % (rng.randint(70, 99), rng.randint(10000000, 99999999))

        email = _email_for(name, None)
        # Two rows have no email at all -- the importer must offer to derive one.
        if i in (6, 17):
            email = ""
        # And one is a straight duplicate of an earlier row, which is a hard
        # error rather than something to auto-fix.
        if i == 20:
            email = _email_for(STARTUP_PEOPLE[0][0], None)

        ac = "" if i in (3, 11) else "%d" % rng.randint(10 ** 11, 10 ** 12 - 1)
        ifsc = "" if i in (3, 11) else rng.choice(
            ["HDFC0000234", "ICIC0001177", "SBIN0007865", "UTIB0000456"])
        pan = "%s%04d%s" % (
            "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5)),
            rng.randint(1000, 9999),
            rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))

        rows.append([name, dept, desig, doj, wage, phone, email, ac, ifsc, pan,
                     remarks[i]])

    # The trailing summary row every hand-kept sheet grows. It is not a person
    # and importing it as one is exactly the kind of silent damage this feature
    # exists to prevent.
    rows.append(["TOTAL", "", "", "", "11 52 500", "", "", "", "", "", ""])

    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    return len(STARTUP_PEOPLE)


# ==========================================================================
# 2. The machine export that is clean and wrong
# ==========================================================================

LEGACY_PEOPLE = [
    ("EMP0041", "Nikhil",  "Raghavan",  "Technology",   "Software Engineer",  "2020-02-17", 1080000),
    ("EMP0042", "Shreya",  "Kulkarni",  "Technology",   "Senior Engineer",    "2018-07-09", 1560000),
    ("EMP0043", "Manish",  "Tiwari",    "Finance",      "Financial Analyst",  "2021-01-25", 912000),
    ("EMP0044", "Aditi",   "Chauhan",   "People",       "HR Business Partner", "2019-11-04", 1044000),
    ("EMP0045", "Sanjay",  "Pillai",    "Technology",   "Engineering Manager", "2017-05-22", 2160000),
    ("EMP0046", "Ruchi",   "Sethi",     "Revenue",      "Account Executive",  "2022-03-14", 780000),
    ("EMP0047", "Ajay",    "Kulkarni",  "Operations",   "Operations Lead",    "2020-09-30", 996000),
    ("EMP0048", "Bhavna",  "Mistry",    "Finance",      "Accounts Payable",   "2021-08-16", 636000),
    ("EMP0049", "Deepak",  "Choudhury", "Technology",   "Software Engineer",  "2022-06-06", 1020000),
    ("EMP0050", "Nandita", "Ghosh",     "People",       "Recruiter",          "2023-02-13", 660000),
    ("EMP0051", "Pranav",  "Salunkhe",  "Revenue",      "Account Executive",  "2021-04-12", 828000),
    ("EMP0052", "Swati",   "Chandran",  "Technology",   "QA Analyst",         "2020-12-01", 744000),
    ("EMP0053", "Harish",  "Balan",     "Operations",   "Supply Analyst",     "2019-03-18", 888000),
    ("EMP0054", "Tanvi",   "Mahajan",   "Finance",      "Financial Analyst",  "2022-10-24", 864000),
    ("EMP0055", "Rohan",   "Dixit",     "Technology",   "Senior Engineer",    "2018-01-08", 1680000),
    ("EMP0056", "Ipsita",  "Panda",     "People",       "HR Executive",       "2023-05-29", 588000),
    ("EMP0057", "Varun",   "Acharya",   "Revenue",      "Sales Manager",      "2019-09-11", 1320000),
    ("EMP0058", "Kiran",   "Hegde",     "Operations",   "Logistics Analyst",  "2021-11-19", 792000),
]


def build_legacy_export(path):
    from openpyxl import Workbook

    rng = random.Random(361)
    wb = Workbook()
    ws = wb.active
    ws.title = "EMP_MASTER"

    ws.append(["EMPLOYEE_CODE", "FIRST_NAME", "LAST_NAME", "EMAIL_ADDRESS",
               "DEPARTMENT_NAME", "DESIGNATION", "DATE_OF_JOINING",
               "ANNUAL_CTC", "MOBILE_NUMBER", "BANK_AC", "IFSC_CODE",
               "PAN_NUMBER", "STATUS"])

    for i, (code, first, last, dept, desig, doj, ctc) in enumerate(LEGACY_PEOPLE):
        email = "%s.%s@northgate-systems.com" % (first.lower(), last.lower())
        # A machine export writes NULL rather than leaving a cell empty, and
        # pads with trailing spaces. Both are silent poison to a naive import.
        bank = "NULL" if i in (2, 9) else "%d" % rng.randint(10 ** 11, 10 ** 12 - 1)
        ifsc = "NULL" if i in (2, 9) else rng.choice(
            ["KKBK0000958", "YESB0000123", "IDFB0040101", "AXIS0000077"])
        pan = "%s%04d%s" % (
            "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5)),
            rng.randint(1000, 9999),
            rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        mobile = "%d%d" % (rng.randint(70, 99), rng.randint(10000000, 99999999))

        ws.append([code, first + "  ", last, email + " ", dept, desig, doj,
                   ctc, mobile, bank, ifsc, pan, "Y" if i != 12 else "N"])

    wb.save(path)
    return len(LEGACY_PEOPLE)


# ==========================================================================
# 3. The acquisition
# ==========================================================================

NORTHWIND_NEW = [
    ("Meghna",  "Bharadwaj", "Technology", "Platform Engineer",  "2021-07-05", 96000),
    ("Yash",    "Trivedi",   "Technology", "Data Engineer",      "2022-02-21", 88000),
    ("Snehal",  "Kadam",     "Revenue",    "Enterprise AE",      "2020-10-12", 104000),
    ("Farhan",  "Ali",       "People Ops", "People Partner",     "2021-12-06", 71000),
    ("Ritika",  "Chopra",    "Revenue",    "Sales Development",  "2023-01-30", 54000),
    ("Alok",    "Nanda",     "Technology", "Platform Engineer",  "2019-06-17", 112000),
    ("Sunita",  "Ravi",      "People Ops", "Learning Lead",      "2020-04-27", 79000),
    ("Devansh", "Kohli",     "Technology", "Security Engineer",  "2022-08-08", 99000),
]


def build_acquisition(path):
    rng = random.Random(362)
    rows = [["Employee Name", "Business Unit", "Role", "Start Date",
             "Monthly Pay (INR)", "Contact Number", "Work Email"]]

    # The four who are already on our roster. They carry the same email the
    # seed gave them, which is what makes them findable -- and the same person
    # arriving twice with two employers is exactly what an acquisition is.
    for first, last, email in COLLISIONS:
        rows.append(["%s %s" % (first, last),
                     rng.choice(["Technology", "Revenue", "People Ops"]),
                     rng.choice(["Engineer", "Account Manager", "People Partner"]),
                     "2024-%02d-%02d" % (rng.randint(1, 12), rng.randint(1, 28)),
                     "%d" % (rng.randint(60, 120) * 1000),
                     "%d%d" % (rng.randint(70, 99), rng.randint(10000000, 99999999)),
                     email])

    for first, last, unit, role, start, pay in NORTHWIND_NEW:
        rows.append(["%s %s" % (first, last), unit, role, start, "%d" % pay,
                     "%d%d" % (rng.randint(70, 99), rng.randint(10000000, 99999999)),
                     "%s.%s@northwind.co.in" % (first.lower(), last.lower())])

    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    return len(rows) - 1


# ==========================================================================

MANIFEST = [
    {
        "file": "messy_startup_roster.csv",
        "label": "Messy startup roster",
        "description": "A spreadsheet somebody kept by hand. Two title rows above "
                       "the header, Hinglish column names, three date formats, "
                       "rupees written three ways, and a total row at the bottom.",
        "teaches": "Header detection, transforms, duplicate and missing email handling.",
        "difficulty": "hard",
    },
    {
        "file": "legacy_hrms_export.xlsx",
        "label": "Legacy HRMS export",
        "description": "A clean machine export that is semantically wrong: salary "
                       "is annual where we store monthly, blanks are the string "
                       "NULL, and names arrive already split.",
        "teaches": "Value profiling. Only the distribution reveals an annual figure.",
        "difficulty": "medium",
    },
    {
        "file": "acquisition_northwind.csv",
        "label": "Acquisition - Northwind",
        "description": "Another company's roster. Different department vocabulary, "
                       "and four people who already work here.",
        "teaches": "Value mapping across taxonomies and duplicate detection.",
        "difficulty": "medium",
    },
]


def main():
    a = build_startup_roster(os.path.join(HERE, "messy_startup_roster.csv"))
    b = build_legacy_export(os.path.join(HERE, "legacy_hrms_export.xlsx"))
    c = build_acquisition(os.path.join(HERE, "acquisition_northwind.csv"))

    counts = {"messy_startup_roster.csv": a,
              "legacy_hrms_export.xlsx": b,
              "acquisition_northwind.csv": c}
    for entry in MANIFEST:
        entry["rows"] = counts[entry["file"]]

    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(MANIFEST, fh, indent=2)
        fh.write("\n")

    print("wrote messy_startup_roster.csv     %d people (+3 junk rows, +1 total row)" % a)
    print("wrote legacy_hrms_export.xlsx      %d people (annual CTC)" % b)
    print("wrote acquisition_northwind.csv    %d people (4 already on the roster)" % c)
    print("wrote manifest.json")


if __name__ == "__main__":
    main()
