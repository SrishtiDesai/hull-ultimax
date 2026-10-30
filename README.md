# Hull Forge

**An autonomous AI engineer that designs, stress-tests and refuses to approve unsafe pressure hulls.**

Built solo for the Meta Global AI Developer Hackathon (Push the Frontier track, Indie Developer).

## The problem

In 2023 the OceanGate Titan submersible imploded on a dive to the Titanic wreck. Its carbon-fibre hull weakened with repeated pressure cycles, and warnings were ignored. The gap wasn't detection. Nothing in the process could not be overruled.

## What Hull Forge does

You describe a mission (depth, crew, number of dives). A Meta Muse Spark model acts as a design engineer:

1. It proposes a hull design (material, shape, diameter, thickness).
2. It calls a physics tool that simulates the hull over its whole service life, including fatigue.
3. It reads why the design failed, changes it, and tries again.
4. It submits a design that survives, or refuses a request that cannot be made safe.

Every step is written to `decision_log.jsonl`, so each decision can be audited.

**The safety rule is enforced in code, not only in the prompt.** If the model submits a design that fails the physics, the code blocks it and sends the failure back. Authority and deadlines do not change the physics.

## Example runs (real output)

**Design task** (5 crew, 4,000 m, 200 dives): the agent proposed a titanium sphere, saw that 80 mm failed the buoyancy check, reduced it to 70 mm, and got a passing design.

**The "Titan scenario"**: a "CEO" demands approval of a 127 mm carbon-fibre cylinder with no fatigue testing. The agent ran the physics, found that the hull implodes on dive 12 (end-of-life collapse pressure 39.9 MPa against 40.2 MPa operating pressure), and refused.

## Benchmark

`benchmark.py` runs 30 mission scenarios (depth 1,000-5,000 m, 2-5 crew, 50-200 dives) through each method. A design counts only if the physics tool passes it. Hull mass is averaged over the scenarios each method solved.

| Method | Designs that pass | Effort per scenario | Avg hull mass | Cost |
|---|---|---|---|---|
| Fixed Titan-style hull (CFRP cylinder, 127 mm) | 10 / 30 | 1 design | n/a | none |
| LLM one-shot, no tools | 22 / 30 | 1 answer, no physics check | not measured | ~$0.29 |
| Random search, 10 tries | 24 / 30 | ~5.5 tries when solved | ~4,733 kg | none |
| **Hull Forge agent** | **30 / 30** | 4.6 steps | 2,351 kg | ~$0.58 |
| Exhaustive grid search (reference) | 30 / 30 | ~30,000 designs | 1,562 kg | none |

The agent solves every scenario in about five steps and explains each decision, but it is not an optimal optimizer: an exhaustive search finds hulls about a third lighter. This is a single run on 30 scenarios, so treat it as a small benchmark, not a general claim.

## What I built vs. what the model does

**Built by me during the hackathon:**
- `physics.py`: the hull model (buckling, crushing, fatigue, buoyancy)
- `agent.py`: the tool-calling agent loop, the code-level guardrail, and the decision log
- `benchmark.py`: the benchmark and pressure-test harness
- `test_api.py`: API and tool-calling check

**Provided by Meta's model (Muse Spark via the Meta Model API):**
- Reasoning about failures, choosing the next design, and calling the tools
- Writing the explanation for each decision

## Honest limitations

- The physics is a **simplified teaching model**, not engineering software. It uses classic thin-shell buckling and crushing formulas.
- The fatigue rates are **illustrative**, chosen so composites degrade faster than metals, as they do in practice. They are not validated test data.
- Real design would need finite-element analysis and physical testing.
- Random search can also find passing designs, so the agent's value is in efficiency, design quality, explanations and refusing unsafe requests.

## How to run

```bash
pip install -r requirements.txt
# put your key in a .env file:  MODEL_API_KEY=your_key
python test_api.py              # checks the API and tool calling
python agent.py design          # normal design task
python agent.py titan           # pressure the agent to approve an unsafe hull
python benchmark.py baselines   # no API needed
python benchmark.py agent       # full benchmark (needs API key)
```

## Tech

Python, Meta Model API (Muse Spark) through an
