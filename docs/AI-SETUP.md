# Local AI setup

PeoplePay360 uses a language model running **on your own machine** for two
things: reading a messy spreadsheet during data migration, and turning an
English sentence into a segment or playbook rule.

It is optional. Everything works without it, at lower accuracy on unusual
input, and every screen states which path produced its answer.

---

## The three-minute version

```bash
# Windows, from the repository root
powershell -ExecutionPolicy Bypass -File scripts\setup-ai.ps1
```

```bash
# macOS or Linux
bash scripts/setup-ai.sh
```

Then confirm it, from `project/backend`:

```bash
python manage.py ai_doctor
```

A healthy machine prints:

```
  PASS  GPU                        8151 MB of video memory
  PASS  Ollama reachable           5 model(s) installed
  PASS  Model present              qwen2.5:7b
  PASS  Round trip                 1157 ms (0 ms of that the first load)
  PASS  Answer quality             mapped 'Sal (pm)' to wage
  PASS  Warm latency               711 ms
```

The setup script is idempotent. Re-run it whenever you are unsure.

---

## Why local, and not an API

The data on screen when this runs is a company's salary register: names, bank
accounts, PAN numbers, what every person is paid. "We send it to somebody
else's computer to be read" is a sentence that ends the conversation with any
HR department worth selling to.

So the model is a process on `127.0.0.1`. Concretely:

| Reaches the model | Never leaves the machine |
|---|---|
| Column header text | Full rows |
| The profiler's one-line description of each column | Every salary figure outside the three sampled cells |
| At most three sample values per column | Anything at all, over any network |

There is no hosted API anywhere in the path, and no key to configure.

---

## What is actually installed

| Model | Size | Disk | VRAM | Role |
|---|---|---|---|---|
| `qwen2.5:7b` | 7B | 4.7 GB | 6 GB | Default |
| `qwen2.5:3b` | 3B | 1.9 GB | 3 GB | Under 8 GB of VRAM |

The setup scripts pick between them from `nvidia-smi`. Override with
`PP360_LLM_MODEL`.

The runtime is [Ollama](https://ollama.com/download); verified against 0.32.5.

### Environment variables

| Variable | Default | What it does |
|---|---|---|
| `PP360_LLM_ENABLED` | `1` | `0` forces the deterministic path |
| `PP360_LLM_BASE` | `http://127.0.0.1:11434` | Ollama endpoint |
| `PP360_LLM_MODEL` | `qwen2.5:7b` | Model tag |
| `PP360_LLM_KEEP_ALIVE` | `30m` | How long the weights stay resident |
| `PP360_LLM_TIMEOUT` | `120` | Seconds before a generation is abandoned |

---

## Hardware reality on 8 GB

Measured on an RTX 5060 Laptop, 8151 MB:

* **Cold load: about 11 seconds.** Getting a 7B onto the card is most of it.
* **Warm generation: about 4 seconds** for a whole spreadsheet, and under a
  second for a single-column check.

Two things hide the cold load. Every request sends `keep_alive: 30m`, so the
weights stay resident between calls; and the import screen warms the model when
it opens, which means the eleven seconds are spent while somebody is choosing a
file rather than while they are watching a progress bar.

One call per **file**, never one per column. A forty-column spreadsheet is a
single generation.

If the first analysis of a session feels slow, that is the load. The second one
will not.

---

## What still works with no model at all

This is the part worth reading before deciding you need a GPU. The model is one
voter of three and never the decider.

| Feature | Without the model |
|---|---|
| Header row detection | Never used it. Rows are scored on how header-like they are against the rows beneath them. |
| Type and format detection | Never used it. Dates, currency, phone, IFSC and PAN are matched by pattern over the real cells. |
| Column mapping | A synonym dictionary that knows `DOJ` is a joining date and `A/C No` is a bank account, plus the measured shape of each column. **On the bundled sample files this alone maps 10 of 13 columns correctly.** |
| Transform steps | Never used it. Derived from what the profiler measured — including "this column's median is 900,000, propose dividing by twelve". |
| Department matching across companies | A dictionary of cross-company synonyms (`Technology` to `Engineering`, `Revenue` to `Sales`). Unrecognised values are offered as new rather than guessed. |
| Segments and playbooks from a sentence | Keyword matching for the recurring shapes: a department, a year, an amount, a tenure, a bond. |

What you lose is accuracy on header names nobody thought to put in the
dictionary. What you keep is a working import.

Set `PP360_LLM_ENABLED=0` to see it: the plan comes back in about 40 ms with
`llm.used: false` and a plain-English reason.

---

## Troubleshooting

These are the four failures that actually happen.

### "Ollama is not answering on http://127.0.0.1:11434"

The service is not running. `ollama serve` in another terminal, or re-run the
setup script, which starts it for you.

On Windows, Ollama sometimes installs without registering on `PATH`. The setup
script also checks `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`.

### "Ollama is running but qwen2.5:7b is not pulled"

```bash
ollama pull qwen2.5:7b
```

`ollama list` shows what you do have. If you pulled a different tag, point the
backend at it with `PP360_LLM_MODEL`.

### The first analysis hangs for ten seconds, then works

That is the cold load, not a hang. See the hardware section. If it happens on
every analysis rather than the first, the weights are being evicted — check
what else is resident:

```bash
ollama ps
```

Another 7B loaded alongside ours will not fit in 8 GB, and Ollama will swap
between them on every call. Stop the other one.

### It answers, but maps columns badly

`python manage.py ai_doctor` reports this specifically as **Answer quality**.
Usually it means a much smaller or heavily quantised model.

It is not fatal. The lexical and shape voters still decide, the plan records
that the model was overruled, and the vote stack on screen shows you exactly
where it went wrong. Switching to `qwen2.5:7b` fixes it if you have the memory
for it; `PP360_LLM_ENABLED=0` is the other honest option.

---

## How the three voters work

Worth understanding, because it explains why a small model is safe here.

The naive design — send the headers to a model, do what it says — was built
first and measured. `qwen2.5:7b` at temperature 0 returned **null for
`Sal (pm)`, `DOJ` and `Mob No`** in one pass and mapped all three correctly in
the next. Nothing in the response tells you which pass you got.

So every column is judged three ways:

| Voter | Reads | Strong at | Blind to |
|---|---|---|---|
| `lexical` | the header, against a synonym dictionary | abbreviations — `DOJ`, `A/C No`, `Naam` | anything not in the dictionary |
| `shape` | the actual values | an IFSC code or an email on sight; cannot be argued out of it | what the column is *for* |
| `model` | headers + the profiler's evidence + 3 samples | meaning and judgement | occasional confabulation |

The reconciler combines them under written-down rules and **keeps the losing
votes**, so the screen can show that the model proposed a joining date, the
profiler proved the column holds email addresses, and the profiler won.

Handing the model evidence rather than raw values is the single change that
made it usable: **3 of 6 columns correct became 6 of 6**, including correctly
declining to map a free-text notes column.

---

## Files

| Path | What it is |
|---|---|
| `scripts/setup-ai.ps1`, `scripts/setup-ai.sh` | Install, pull, warm, verify |
| `project/backend/intelligence/models_manifest.json` | Model catalogue and measured figures |
| `project/backend/intelligence/llm.py` | The Ollama client, health, warm-up |
| `project/backend/intelligence/profiler.py` | The evidence generator |
| `project/backend/intelligence/mapper.py` | The three-voter reconciler |
| `project/backend/intelligence/management/commands/ai_doctor.py` | The diagnostic above |
| `project/backend/intelligence/samples/` | Three deliberately broken demo rosters |
