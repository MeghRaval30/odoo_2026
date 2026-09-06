"""
Diagnose the local model setup, and say what to do about each failure.

Always exits 0. This is a diagnostic, not a gate -- a non-zero exit would make
it unusable in the one place it matters, which is a CI step or a setup script
that wants to print the report and carry on. The product works without the
model, so "the model is missing" is information, not an error.

ASCII output only: the Windows console is cp1252 and a management command that
prints anything else dies mid-report.
"""

import json
import os
import subprocess
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from intelligence.llm import LocalModel
from intelligence.mapper import build_prompt
from intelligence.profiler import profile_column

MANIFEST = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "models_manifest.json")


class Command(BaseCommand):
    help = "Check that the local language model is reachable and usable."

    def add_arguments(self, parser):
        parser.add_argument("--skip-generate", action="store_true",
                            help="Do not spend a real generation on the check.")

    # -- reporting --------------------------------------------------------

    def row(self, check, ok, detail):
        mark = "PASS" if ok else "FAIL" if ok is False else "----"
        self.stdout.write("  %-4s  %-26s %s" % (mark, check[:26], detail[:78]))

    def remedy(self, text):
        self.stdout.write("        -> %s" % text)

    # -- checks -----------------------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("PeoplePay360 local model check")
        self.stdout.write("=" * 72)

        model = LocalModel()
        failures = 0

        # 1. Configuration
        self.row("Configuration", None,
                 "%s, model %s" % (model.base, model.model))
        if not model.enabled:
            self.row("Enabled", False, "PP360_LLM_ENABLED switches it off")
            self.remedy("Set PP360_LLM_ENABLED=1 to use the model. Imports "
                        "still work without it.")
            failures += 1

        # 2. GPU, where we can see one
        vram = self._vram_mb()
        if vram is None:
            self.row("GPU", None, "no nvidia-smi; CPU inference will be slow "
                                  "but correct")
        else:
            enough = vram >= 6000
            self.row("GPU", enough, "%d MB of video memory" % vram)
            if not enough:
                self.remedy("Under 6 GB. Use the 3B model: "
                            "set PP360_LLM_MODEL=qwen2.5:3b")

        # 3. Is Ollama answering
        installed = model.installed_models()
        if installed is None:
            self.row("Ollama reachable", False, "nothing answering on %s"
                     % model.base)
            self.remedy("Start it with 'ollama serve', or run "
                        "scripts/setup-ai.ps1 (Windows) / scripts/setup-ai.sh")
            self.remedy("Not installed? https://ollama.com/download")
            failures += 1
            return self._finish(failures)

        self.row("Ollama reachable", True, "%d model(s) installed"
                 % len(installed))

        # 4. Is the configured model one of them
        present = any(m == model.model or
                      m.split(":")[0] == model.model.split(":")[0]
                      for m in installed)
        self.row("Model present", present,
                 model.model if present else "%s is not pulled" % model.model)
        if not present:
            self.remedy("Run: ollama pull %s" % model.model)
            self.remedy("Installed instead: %s" % ", ".join(installed[:5]))
            failures += 1
            return self._finish(failures)

        if options["skip_generate"]:
            return self._finish(failures)

        # 5. A real round trip, on a real prompt. Anything less proves nothing
        #    -- the failure this catches is a model that loads and then returns
        #    prose where JSON was asked for.
        profile = profile_column(0, "Sal (pm)",
                                 ["Rs 45,000", "72,000", "38500/-", "Rs 65,000"])
        started = time.time()
        try:
            data, elapsed = model.generate_json(build_prompt([profile]),
                                                num_predict=200)
        except Exception as exc:                # noqa: BLE001
            self.row("Round trip", False, str(exc)[:70])
            self.remedy("The model is installed but did not answer usably. "
                        "Try 'ollama run %s' by hand." % model.model)
            return self._finish(failures + 1)

        mappings = data.get("mappings") or []
        answered = mappings[0].get("field") if mappings else None
        first = time.time() - started
        self.row("Round trip", True, "%d ms (%d ms of that the first load)"
                 % (int(first * 1000), max(0, int(first * 1000) - elapsed)))

        # 6. Did it get the answer right
        correct = answered == "wage"
        self.row("Answer quality", correct,
                 "mapped 'Sal (pm)' to %s" % (answered or "nothing"))
        if not correct:
            self.remedy("The model is running but reading columns poorly. "
                        "Imports still work: the lexical and shape voters "
                        "carry the result and the plan will say so.")

        # 7. Warm latency, which is the number that matters in a demo
        started = time.time()
        try:
            model.generate_json(build_prompt([profile]), num_predict=200)
            warm = int((time.time() - started) * 1000)
            self.row("Warm latency", warm < 15000, "%d ms" % warm)
            if warm >= 15000:
                self.remedy("Slow. Another model may be resident; "
                            "'ollama ps' shows what is loaded.")
        except Exception:                       # noqa: BLE001
            self.row("Warm latency", None, "not measured")

        return self._finish(failures)

    # -- helpers ----------------------------------------------------------

    def _vram_mb(self):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=6)
            if out.returncode != 0:
                return None
            return int(out.stdout.strip().split("\n")[0])
        except Exception:                       # noqa: BLE001
            return None

    def _finish(self, failures):
        self.stdout.write("=" * 72)
        if failures:
            self.stdout.write(
                "%d check(s) failed. The import studio still works: column "
                "matching" % failures)
            self.stdout.write(
                "falls back to a synonym dictionary and value profiling, and "
                "every screen")
            self.stdout.write("says which path produced its answer.")
        else:
            self.stdout.write("All checks passed.")
        self.stdout.write("")
        try:
            with open(MANIFEST, encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.stdout.write("Manifest: %s" % MANIFEST)
            for entry in manifest.get("models", []):
                self.stdout.write(
                    "  %-14s %-4s %5.1f GB disk  %d GB VRAM  %s"
                    % (entry["name"], entry["parameters"], entry["disk_gb"],
                       entry["min_vram_gb"],
                       "default" if entry.get("default") else "fallback"))
        except (OSError, ValueError):
            pass
        self.stdout.write("")
