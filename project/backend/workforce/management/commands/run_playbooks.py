"""
Fire every active playbook and report what was raised.

Run on a schedule in a real deployment. ASCII output only -- the Windows
console is cp1252 and a management command that prints anything else dies.
"""

from django.core.management.base import BaseCommand

from workforce import playbooks


class Command(BaseCommand):
    help = "Evaluate active playbooks and raise reminder events."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would fire, record nothing.")

    def handle(self, *args, **options):
        commit = not options["dry_run"]
        summary = playbooks.run_all(commit=commit)

        self.stdout.write("%s %d playbook(s)"
                          % ("Ran" if commit else "Checked", summary["playbooks"]))
        for result in summary["results"]:
            self.stdout.write("  %-40s matched %3d  new %3d  already raised %3d"
                              % (result["playbook"][:40], result["matched"],
                                 result["new"], result["already_raised"]))
            for person in result["people"][:5]:
                self.stdout.write("      %-28s %s"
                                  % (person["name"][:28], person["reason"][:60]))
        self.stdout.write("")
        self.stdout.write("%s %d event(s)."
                          % ("Raised" if commit else "Would raise",
                             summary["events_raised"]))
