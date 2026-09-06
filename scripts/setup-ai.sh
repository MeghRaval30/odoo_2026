#!/usr/bin/env bash
#
# Set up the local language model PeoplePay360 uses for data migration.
#
# Idempotent and safe to re-run. It verifies rather than assumes: after pulling
# the model it fires one real mapping prompt at it and reports PASS or FAIL
# with the latency, because "the pull succeeded" and "the model can do the job"
# are different claims.
#
#   bash scripts/setup-ai.sh
#   bash scripts/setup-ai.sh qwen2.5:3b

set -u

MODEL="${1:-}"
ENDPOINT="${PP360_LLM_BASE:-http://127.0.0.1:11434}"

say()  { printf '%s\n' "$1"; }
step() { printf '\n-> %s\n' "$1"; }
ok()   { printf '   PASS  %s\n' "$1"; }
bad()  { printf '   FAIL  %s\n' "$1"; }
note() { printf '         %s\n' "$1"; }

say "PeoplePay360 - local model setup"
say "============================================================"

# --------------------------------------------------------------------------
step "Looking for Ollama"

if ! command -v ollama >/dev/null 2>&1; then
  bad "Ollama is not installed."
  note "Install it:  curl -fsSL https://ollama.com/install.sh | sh"
  note "or see https://ollama.com/download"
  note "Everything in the product still works without it - column matching"
  note "falls back to a synonym dictionary and value profiling."
  exit 0
fi
ok "found at $(command -v ollama)"

# --------------------------------------------------------------------------
step "Checking the service"

endpoint_up() {
  curl -fsS -m 4 "$ENDPOINT/api/tags" >/dev/null 2>&1
}

if endpoint_up; then
  ok "already answering on $ENDPOINT"
else
  note "not answering; starting it in the background"
  nohup ollama serve >/dev/null 2>&1 &
  up=0
  for _ in $(seq 1 15); do
    sleep 1
    if endpoint_up; then up=1; break; fi
  done
  if [ "$up" = "1" ]; then
    ok "started, answering on $ENDPOINT"
  else
    bad "could not reach $ENDPOINT after 15 seconds."
    note "Run 'ollama serve' in another terminal and try again."
    exit 0
  fi
fi

# --------------------------------------------------------------------------
step "Choosing a model"

if [ -z "$MODEL" ]; then
  VRAM=""
  if command -v nvidia-smi >/dev/null 2>&1; then
    VRAM="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')"
  fi
  if [ -z "$VRAM" ]; then
    note "no NVIDIA GPU detected; CPU or Metal inference is correct but slower"
    # Apple silicon runs the 7B comfortably on unified memory.
    if [ "$(uname -s)" = "Darwin" ]; then MODEL="qwen2.5:7b"; else MODEL="qwen2.5:3b"; fi
  elif [ "$VRAM" -lt 6000 ]; then
    note "$VRAM MB of video memory - using the smaller model"
    MODEL="qwen2.5:3b"
  else
    note "$VRAM MB of video memory"
    MODEL="qwen2.5:7b"
  fi
fi
ok "using $MODEL"

# --------------------------------------------------------------------------
step "Pulling the model"

if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
  ok "$MODEL is already pulled"
else
  note "downloading $MODEL - this is the slow part, a few GB"
  if ! ollama pull "$MODEL"; then
    bad "the pull failed."
    note "Check the network, then run: ollama pull $MODEL"
    exit 0
  fi
  ok "$MODEL pulled"
fi

# --------------------------------------------------------------------------
step "Testing it on a real prompt"
note "first call includes loading the weights, so it is the slow one"

PROMPT='You map the columns of a messy HR spreadsheet onto a fixed schema.

TARGET FIELDS - choose exactly one per column, or null:
- full_name: the person'"'"'s whole name in one column
- work_email: official email address
- wage: monthly gross pay in rupees
- date_of_joining: the day employment started

COLUMNS. A deterministic profiler has already inspected the values;
EVIDENCE states what it measured.

COLUMN 1  header=Sal (pm)
  EVIDENCE: currency-like, values 35000 to 88000, 22 of 22 filled
  SAMPLES: Rs 45,000 | 72,000 | 38500/-

The EVIDENCE is authoritative about what TYPE a column holds. Your job is the
MEANING: which schema field this column is for.

Return JSON only:
{"mappings":[{"column":1,"field":"wage","confidence":0.9,"reason":"short"}]}'

BODY="$(MODEL="$MODEL" PROMPT="$PROMPT" python3 -c '
import json, os
print(json.dumps({
    "model": os.environ["MODEL"],
    "prompt": os.environ["PROMPT"],
    "stream": False,
    "format": "json",
    "keep_alive": "30m",
    "options": {"temperature": 0, "num_predict": 200},
}))')"

run_once() {
  curl -fsS -m 180 -X POST "$ENDPOINT/api/generate" \
       -H "Content-Type: application/json" -d "$BODY"
}

START=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')
RESP="$(run_once)" || {
  bad "the model did not answer."
  note "Try 'ollama run $MODEL' by hand to see what it says."
  exit 0
}
END=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')

FIELD="$(RESP="$RESP" python3 -c '
import json, os
try:
    inner = json.loads(os.environ["RESP"]).get("response", "")
    print((json.loads(inner).get("mappings") or [{}])[0].get("field") or "none")
except Exception:
    print("unparseable")')"

if [ "$FIELD" = "wage" ]; then
  ok "answered correctly in $((END - START)) ms - mapped 'Sal (pm)' to wage"
else
  bad "answered in $((END - START)) ms but mapped 'Sal (pm)' to '$FIELD'"
  note "The model runs but reads columns poorly. Imports still work;"
  note "the dictionary and profiler carry the result and say so."
fi

# --------------------------------------------------------------------------
step "Measuring warm latency"

START=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')
if run_once >/dev/null; then
  END=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')
  ok "$((END - START)) ms with the weights already resident"
else
  note "not measured"
fi

say ""
say "============================================================"
say "Ready."
say ""
say "If the model is not the default, tell the backend:"
say "  export PP360_LLM_MODEL=$MODEL"
say ""
say "Check it any time from project/backend:"
say "  python manage.py ai_doctor"
say ""
