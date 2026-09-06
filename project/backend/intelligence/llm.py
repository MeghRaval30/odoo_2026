"""
The local model, and the discipline of not depending on it.

PeoplePay360 talks to a language model running on the operator's own machine
through Ollama. Not to a hosted API -- the data on the screen when this runs is
a company's salary register, and "we send it to somebody else's computer" is a
sentence that ends the conversation with any HR department worth selling to.
Column headers and at most three sample values reach a process on localhost.
Row data never leaves the host at all.

The cost of that choice is that the model is small. A 7B on an 8GB laptop card
is not GPT-4; it forgets instructions, invents fields, and returns confident
nulls. So it is used narrowly and never trusted:

  * it is asked one question per file, not one per column, because latency is
    real -- about four seconds warm, eleven cold while the weights load;
  * it is given the profiler's evidence rather than raw data, which is what
    took it from three of six columns correct to six of six;
  * its answer is a vote, reconciled against two deterministic voters in
    `mapper`, and it loses to hard evidence;
  * and every path that uses it works without it.

`available()` is therefore not a gate on the feature. It decides whether the
answer says "read by qwen2.5:7b" or "matched by rules", and both are real
answers.
"""

import json
import re
import time
import urllib.error
import urllib.request

from django.conf import settings

DEFAULT_MODEL = "qwen2.5:7b"

#: For machines under 8GB of video memory. Meaningfully worse at the semantic
#: judgement, still better than nothing, and the setup script selects it.
FALLBACK_MODEL = "qwen2.5:3b"

#: How long a health probe is trusted. Long enough that a screen polling it
#: does not hammer the socket; short enough that starting Ollama mid-demo is
#: noticed without a restart.
HEALTH_TTL_SECONDS = 20


class LLMUnavailable(Exception):
    """Raised when the model cannot answer. Callers fall back; they never fail."""


def _setting(name, default):
    return getattr(settings, name, default)


class LocalModel:
    def __init__(self, base=None, model=None, timeout=None):
        self.base = (base or _setting("PP360_LLM_BASE", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or _setting("PP360_LLM_MODEL", DEFAULT_MODEL)
        self.timeout = timeout or _setting("PP360_LLM_TIMEOUT", 120)
        self.keep_alive = _setting("PP360_LLM_KEEP_ALIVE", "30m")
        self.enabled = _setting("PP360_LLM_ENABLED", True)

    # -- plumbing ---------------------------------------------------------

    def _post(self, path, payload, timeout=None):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path, timeout=4):
        req = urllib.request.Request(self.base + path, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # -- health -----------------------------------------------------------

    _cache = {"at": 0.0, "value": None}

    def installed_models(self):
        try:
            tags = self._get("/api/tags")
        except Exception:
            return None
        return [m.get("name") for m in tags.get("models", []) if m.get("name")]

    def resolve(self, models=None):
        """
        The exact tag to generate against, given what is actually pulled.

        Ollama's tags are exact strings: asking it for "qwen2.5:7b" when what
        is installed is "qwen2.5:7b-instruct" is a 404, not a near miss. The
        health check has always matched loosely, on the model family, so
        without this the two disagree -- the setup screen reports the model
        ready and every import then fails on a model that is not there.

        Preference order is the exact tag, then a tag in the same family that
        the configured one is a prefix of, then the shortest tag in the family.
        Shortest because tags grow by qualification: between "qwen2.5:7b" and
        "qwen2.5:7b-instruct-q4_K_M" the shorter is the more general build, and
        the more general one is the better guess when configuration did not say.
        """
        if models is None:
            models = self.installed_models()
        if not models:
            return self.model
        if self.model in models:
            return self.model
        family = self.model.split(":")[0]
        kin = [m for m in models if m.split(":")[0] == family]
        if not kin:
            return self.model
        prefixed = [m for m in kin if m.startswith(self.model)]
        return min(prefixed or kin, key=len)

    def available(self):
        return bool(self.health().get("available"))

    def health(self, force=False):
        now = time.time()
        cached = LocalModel._cache
        if not force and cached["value"] and now - cached["at"] < HEALTH_TTL_SECONDS:
            return cached["value"]

        out = {
            "available": False, "base": self.base, "model": self.model,
            "model_present": False, "installed_models": [],
            "latency_ms": None, "message": "", "install_hint": None,
            "enabled": bool(self.enabled),
        }

        if not self.enabled:
            out["message"] = ("The local model is switched off by configuration "
                              "(PP360_LLM_ENABLED). Imports run on rules alone.")
        else:
            started = time.time()
            models = self.installed_models()
            if models is None:
                out["message"] = ("Ollama is not answering on %s. Start it, or run "
                                  "the setup script." % self.base)
                out["install_hint"] = "scripts/setup-ai.ps1"
            else:
                out["installed_models"] = models
                # Ollama reports "qwen2.5:7b"; a caller may have configured
                # "qwen2.5" and meant the same thing.
                resolved = self.resolve(models)
                out["model_present"] = resolved in models
                # What the screen names has to be what generation will use.
                out["configured_model"] = self.model
                out["model"] = resolved
                out["latency_ms"] = int((time.time() - started) * 1000)
                if out["model_present"]:
                    out["available"] = True
                    out["message"] = "Local model ready."
                else:
                    out["message"] = ("Ollama is running but %s is not pulled. "
                                      "Run: ollama pull %s" % (self.model, self.model))
                    out["install_hint"] = "ollama pull %s" % self.model

        LocalModel._cache = {"at": now, "value": out}
        return out

    def warm(self):
        """
        Pay the cold-load cost early, on a screen that expects to wait.

        Loading a 7B onto this card costs about eleven seconds. Paying it when
        the operator opens the import screen rather than when they press
        Analyze is the difference between a feature that feels instant and one
        that looks hung, and it costs nothing but a one-token generation.
        """
        if not self.enabled:
            return False
        try:
            self._post("/api/generate", {
                "model": self.resolve(), "prompt": "ok", "stream": False,
                "keep_alive": self.keep_alive,
                "options": {"num_predict": 1, "temperature": 0},
            }, timeout=self.timeout)
            return True
        except Exception:
            return False

    # -- generation -------------------------------------------------------

    @staticmethod
    def extract_json(text):
        """
        Pull an object out of whatever the model actually said.

        `format: json` usually makes this unnecessary, but a small model under
        a long prompt still occasionally opens with a sentence or wraps the
        object in a fence. Scanning for the outermost balanced braces recovers
        every case seen in testing, and costs nothing when the response is
        already clean.
        """
        if not text:
            raise ValueError("empty response")
        text = text.strip()
        try:
            return json.loads(text)
        except ValueError:
            pass

        fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
        if fenced:
            try:
                return json.loads(fenced.group(1).strip())
            except ValueError:
                pass

        start = text.find("{")
        if start < 0:
            raise ValueError("no JSON object in response")
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
        raise ValueError("unbalanced JSON in response")

    def generate_json(self, prompt, num_predict=700, num_ctx=4096, temperature=0.0):
        """Ask for a JSON object. Raises LLMUnavailable rather than returning junk."""
        if not self.enabled:
            raise LLMUnavailable("The local model is switched off by configuration.")

        payload = {
            "model": self.resolve(),
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        }

        started = time.time()
        try:
            raw = self._post("/api/generate", payload)
        except urllib.error.URLError as exc:
            raise LLMUnavailable("Cannot reach Ollama at %s (%s)." % (self.base, exc))
        except Exception as exc:
            raise LLMUnavailable("The local model failed: %s" % exc)

        elapsed = int((time.time() - started) * 1000)
        text = raw.get("response", "")

        try:
            return self.extract_json(text), elapsed
        except ValueError:
            # One retry, with the instruction restated. A small model that
            # drifted into prose usually complies the second time, and a second
            # failure means the answer is not worth waiting for again.
            try:
                payload["prompt"] = prompt + "\n\nReturn ONLY a JSON object. No prose."
                raw = self._post("/api/generate", payload)
                elapsed = int((time.time() - started) * 1000)
                return self.extract_json(raw.get("response", "")), elapsed
            except Exception as exc:
                raise LLMUnavailable("The local model did not return usable JSON (%s)." % exc)


def get_model():
    return LocalModel()
