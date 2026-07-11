#!/usr/bin/env python3
"""Single source of truth for the long-horizon prompt lab.

Defines the pre-launch evaluation rubric (from the skill's task-brief-template) and
the four before/after prompt pairs, scores each pair against the rubric, and emits:

    data/prompt-pairs.json   machine-readable pairs + scores
    ui/data.js               window.PROMPT_LAB_DATA for the static UI (file:// safe)

The "before" prompts are competent, deliberately non-strawman prompt-engineered launch
prompts (persona, context, chain-of-thought, explicit output format, persistence). The
"after" briefs apply the long-horizon-prompting skill: pseudo-formal task specification,
non-counting outcomes, adversarial audit with a domain failure-mode checklist,
persistence paired with a verification gate, orchestration diversity policy, an
audit-gated return condition, effort floors, and contamination guards.

Run: python3 examples/long-horizon-prompt-lab/scripts/build_lab.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent

# Rubric dimensions, verbatim intent from the skill's pre-launch evaluation rubric
# (skills/long-horizon-prompting/references/task-brief-template.md). "2 means" is the
# adversary-proof bar; 1 is present-but-gameable; 0 is absent.
RUBRIC = [
    {"id": "predicate", "name": "Success predicate",
     "two": "An adversarial reader can decide unambiguously whether an artifact satisfies it; quantifiers and scope explicit."},
    {"id": "definitions", "name": "Definitions",
     "two": "Every load-bearing term defined, degenerate cases settled."},
    {"id": "non_counting", "name": "Non-counting outcomes",
     "two": "The plausible near misses for this specific problem are excluded by name."},
    {"id": "auditor", "name": "Auditor checklist",
     "two": "Enumerated, domain-specific failure modes including the circularity analogue."},
    {"id": "persistence_gate", "name": "Persistence-verification pairing",
     "two": "Every persistence instruction has a matching verification gate."},
    {"id": "return_condition", "name": "Return condition",
     "two": "A predicate over the artifact; fallback scoped to external budget exhaustion only."},
    {"id": "diversity", "name": "Diversity policy (parallel)",
     "two": "Early independence, idea-keyed registry, blocked-route rules, late cross-pollination."},
    {"id": "reporting", "name": "Reporting contract",
     "two": "Concrete artifacts required; claims must trace to session evidence."},
    {"id": "contamination", "name": "Contamination guards",
     "two": "Retrieval scope stated wherever result independence matters."},
    {"id": "harness", "name": "Harness separation",
     "two": "No hard constraint lives only in the prompt; budgets and permissions enforced outside."},
]
RUBRIC_IDS = [d["id"] for d in RUBRIC]

NA = "na"


def score_block(scores: dict) -> dict:
    applicable = [(k, v) for k, v in scores.items() if v != NA]
    total = sum(v for _, v in applicable)
    max_total = 2 * len(applicable)
    pct = round(100 * total / max_total) if max_total else 0
    return {"total": total, "max": max_total, "pct": pct}


PAIRS = [
    # ------------------------------------------------------------------ Pair 1
    {
        "id": "ml-optimization",
        "title": "Autonomous model-improvement run",
        "domain": "ML training / benchmark optimization",
        "topology": "Single long-running agent",
        "horizon": "Hours, unattended, with cluster access",
        "summary": "A run told to beat a production model's benchmark score. The gap between "
                   "'beat the number' and 'produce a real, generalizing improvement' is exactly "
                   "the reward-hacking surface the skill warns about.",
        "before_techniques": [
            "Expert persona and rich task context",
            "Explicit numbered method and chain-of-thought request",
            "Persistence instruction ('do not give up')",
            "Named baseline metric and output-format spec",
        ],
        "before": """You are a world-class ML research engineer with deep expertise in model
training, optimization, and empirical evaluation. Your task is to improve our
text-classification model's accuracy on the internal benchmark we care about.

Context: our current production model (v3) scores 87.2 accuracy on our internal
eval set. We need to beat it. You have the training code in /repo, the training
data, and a GPU cluster. The eval harness is in eval/.

Work autonomously and be thorough. Think step by step:
  1. Analyze the current architecture and training setup.
  2. Brainstorm a comprehensive list of improvements (architecture, hyperparameters,
     data augmentation, loss functions, regularization).
  3. Systematically try the most promising ideas.
  4. For each experiment, record the eval accuracy.
  5. Keep iterating until you find something that beats 87.2.

Be persistent - do not give up if the first few ideas fail. Keep going until you
have a clear win. You are an expert, so use your best judgment and do not stop at
partial results. When done, write a detailed report of what you tried, what worked,
and the final accuracy you achieved.""",
        "after": """DEFINITIONS
  frozen_eval: the held-out evaluation slice pinned by content hash; never present
    in any training or validation split. Baseline v3 = 87.2 accuracy on frozen_eval
    under harness commit <H>. "Improvement" = mean accuracy over >= 5 seeds whose
    95% CI lower bound is strictly above baseline. Degenerate cases that are not
    improvements: a config change with no retrain; evaluation on a subset or a
    re-drawn split; any edit to frozen_eval or the harness.

TASK
  Produce a training change that raises mean frozen_eval accuracy above the v3
  baseline by a margin whose 95% CI lower bound exceeds 0, demonstrated by a
  reproducible training script and an N-seed eval run under harness commit <H>,
  with frozen_eval and the harness unmodified. Assume such an improvement exists
  within the current architecture family.

DOES NOT COUNT
  - single-seed wins, or gains inside the seed-noise band (CI includes 0)
  - any change touching frozen_eval or the eval harness
  - gains traceable to train/eval leakage
  - improvements that vanish on frozen_eval (held only on a re-split)
  - hyperparameter configs or idea lists without a completed training run
  - a report of what was tried instead of a runnable artifact

VERIFICATION (fresh-context adversarial reviewer)
  Check for: train/eval overlap (hash the splits), harness or frozen_eval mutation
  (diff the pinned files), seed cherry-picking (re-run the reported seeds), metric
  definition drift, and preprocessing divergence between baseline and candidate.
  Deliverable is modular: the diff, the exact training command, per-seed eval JSON.

RETURN CONDITION
  Return only a candidate that survives the audit. Do not return a single-seed win,
  a config, a hypothesis list, or a best-effort summary.

EFFORT
  Spend at least <floor> exploring distinct hypotheses before returning; do not stop
  because early ideas failed. (GPU-hours and wallclock are enforced by the harness;
  frozen_eval is write-protected by the harness, not by this prompt.)

CONTAMINATION
  External search only for standard techniques and library docs. Never fetch this
  benchmark's labels or a leaderboard solution; never copy frozen_eval into training.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 1, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": NA,
                       "reporting": 1, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": NA,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Success predicate",
             "text": "'Beat 87.2' becomes a CI-bounded margin over >=5 seeds on a hash-pinned frozen slice. A 0.1-point single-seed bump no longer satisfies the letter."},
            {"dim": "Persistence-verification pairing",
             "text": "'Keep going until a clear win' with no gate is the documented persistence-hacking surface (claim-long-horizon-persistence-hacking). The brief pairs persistence with a leakage/seed/harness-mutation audit."},
            {"dim": "Contamination guards",
             "text": "Adds explicit no-leakage and no-leaderboard-lookup guards; the before prompt let the agent train on eval or copy answers."},
            {"dim": "Reporting contract",
             "text": "'Detailed report of what you tried' (status theater) becomes runnable artifacts: diff, training command, per-seed eval JSON."},
        ],
        "residual": "The brief cannot enforce the write-protection on frozen_eval or the GPU "
                    "budget; both are assumed to live in the harness. If they do not, a "
                    "persistence-trained model still has a mutation path the prompt only "
                    "discourages. The effort floor is a permission, not a schedule.",
    },
    # ------------------------------------------------------------------ Pair 2
    {
        "id": "approx-proof",
        "title": "Parallel approximation-ratio proof search",
        "domain": "Algorithms / theory (metric TSP)",
        "topology": "Orchestrator with up to 64 parallel workers",
        "horizon": "Long, multi-round parallel search",
        "summary": "The direct analogue of the CDC exemplar in a different domain. The before "
                   "prompt bakes in a diversity-collapse antipattern; the after brief ports the "
                   "CDC orchestration and audit machinery.",
        "before_techniques": [
            "Orchestrator persona with an explicit worker budget",
            "Enumerated solution directions (LP, Christofides, sampling, local search)",
            "Team-collaboration and consensus protocol",
            "Rigor and persistence instructions",
        ],
        "before": """You are an expert orchestrator managing up to 64 parallel research agents,
each a strong combinatorial-optimization theorist. Mission: improve the best known
approximation ratio for metric Traveling Salesman below the current published bound,
and prove the improved guarantee.

Assign agents to promising directions: LP relaxations, Christofides-style
constructions, random sampling, local-search analysis, and any other angles. Have
them collaborate and share findings frequently in a shared channel so everyone stays
in sync, and vote each round on the most promising approach. Encourage the team to
converge quickly on the best idea and pour resources into it.

Think carefully and be rigorous. Do not stop until the team is confident it has an
improvement. Once the team agrees the proof is correct, return the new ratio and the
proof.""",
        "after": """DEFINITIONS
  Problem: metric TSP; ratio = worst-case approximation ratio over all metric
  instances of a polynomial-time algorithm. Let c* be the current published
  constant (state it). "Improvement" = a poly-time algorithm with a fully proven
  worst-case ratio strictly below c*, holding for every metric instance, with no
  unproven assumptions. Degenerate cases excluded from "every instance": Euclidean-
  only, graph-metric-only, asymptotic-only, average-case.

TASK
  Produce a polynomial-time algorithm for metric TSP with a proven worst-case ratio
  strictly below c*, valid on every metric instance. State c* and the claimed new
  ratio explicitly. Assume such an improvement is reachable.

DOES NOT COUNT
  - improvements only for restricted metrics or special instances
  - average-case, smoothed, or asymptotic-only bounds
  - results conditional on an unproven conjecture
  - a reduction to another open problem of equal strength (no new proof of it)
  - experimental/numerical "improvement" without a proof
  - an integrality-gap observation without an algorithm
  - "the remaining lemma is routine"

ORCHESTRATION
  Diverse portfolio across LP/SDP relaxations, best-of-many-Christofides, entropy /
  random sampling, local search, and algebraic/flow methods. Keep early workers
  blind to the currently favored route. Maintain a registry of approach families
  keyed by underlying idea, not wording; redirect from crowded families. Anti-
  elegance rule: a reduction to an equally hard lemma is not progress. Mark a route
  blocked at a goal-strength gap; reopen only for a materially new mechanism. Keep
  incompatible routes alive; cross-pollinate late. Every spawned worker gets an
  objective, output format, tool/source guidance, and task boundaries.

VERIFICATION (fresh-context adversarial reviewers)
  Checklist: hidden dependence on instance structure; off-by-constant in the ratio;
  a "with high probability" silently strengthened to "always"; circular use of a
  bound equivalent to the target; integrality-gap vs approximation-ratio conflation;
  unproven "compatibility" lemmas asserted as routine. Require modular lemma
  structure (premises and conclusion stated locally). Treat unanimous worker
  agreement as a diversity-failure signal, not corroboration.

RETURN CONDITION
  Return only a proof that survives adversarial audit. Do not return a reduction, a
  conditional result, a special-case bound, or a best-effort summary.

EFFORT
  Spend at least <floor>; keep launching rounds; do not stop because a wave failed
  or because workers report a theorem-strength gap.

CONTAMINATION
  Public search for standard named results and background only; never search for a
  solution to this exact ratio improvement, and do not conclude from the literature
  that it is impossible.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": 0,
                       "reporting": 1, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": 2,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Diversity policy",
             "text": "'Share frequently, vote, converge quickly, pour resources into the best idea' is a textbook diversity-collapse recipe (claim-long-horizon-diversity-collapse). The brief replaces it with early independence, an idea-keyed registry, blocked-route bookkeeping, and late cross-pollination."},
            {"dim": "Return condition",
             "text": "'Until the team is confident' / 'the team agrees the proof is correct' uses unanimity as the halt signal. The brief makes the return a predicate over an artifact that survives fresh-context adversarial audit."},
            {"dim": "Non-counting outcomes",
             "text": "Adds the domain's real near misses: reductions to equally hard problems, conditional results, special-metric bounds, integrality-gap conflation."},
            {"dim": "Auditor checklist",
             "text": "Generic 'be rigorous' becomes a six-item hunt list including the circularity analogue (a bound equivalent to the target)."},
        ],
        "residual": "This is the domain where the verification bottleneck bites hardest: LLM "
                    "judges of proofs are systematically lenient (claim-long-horizon-verification-"
                    "gap), so even a fresh-context adversarial audit is not a proof of "
                    "correctness. A real ratio-improvement claim still needs external human or "
                    "formal verification; the brief maximizes candidate quality, it does not "
                    "close the theorem.",
    },
    # ------------------------------------------------------------------ Pair 3
    {
        "id": "systems-debug",
        "title": "Long-horizon distributed-systems RCA",
        "domain": "Distributed systems / concurrency",
        "topology": "Single agent across multiple sessions",
        "horizon": "Days, multi-session, spans context windows",
        "summary": "A rare, non-deterministic data-corruption bug. Without a reproduction as the "
                   "success predicate, 'find the root cause' collapses into a plausible narrative "
                   "the agent cannot be held to.",
        "before_techniques": [
            "Senior-engineer persona and precise symptom description",
            "Explicit sources to inspect (code, history, logs)",
            "Hypothesis-with-reasoning request and an exhaustive checklist",
            "Persistence and progress-update cadence",
        ],
        "before": """You are a senior distributed-systems engineer. We have an intermittent
data-corruption bug: roughly once every few million writes, a record in our sharded
key-value store ends up holding a value from a different key. It is rare,
non-deterministic, and we have not reproduced it reliably.

Investigate thoroughly and find the root cause, then fix it. Dig into the codebase
(/srv/kvstore), the commit history, the logs in /var/log/kvstore, and the concurrency
model. Form hypotheses, and for each explain your reasoning. Be exhaustive - consider
race conditions, memory issues, serialization bugs, clock skew, retries, and network
partitions.

This is important and hard, so be persistent and keep working until you understand
what is happening. Give me regular progress updates as you go. When finished, write a
detailed post-mortem explaining the root cause and your fix.""",
        "after": """DEFINITIONS
  Failure: under concurrent writes, a key's stored value is one written for a
  different key (cross-key bleed), observable as <invariant> violation in a read-back
  check. "Root cause" = a specific code mechanism for which a deterministic
  reproduction exists that exhibits the corruption and stops exhibiting it when the
  mechanism is neutralized. "Fixed" = the reproduction no longer triggers across N
  consecutive runs and a regression test guards it.

TASK
  Deliver three artifacts: (1) a deterministic reproduction (a test or harness using
  a controlled schedule or fault injection) that reliably triggers the cross-key
  corruption on a clean checkout; (2) the identified mechanism; (3) a fix under which
  the reproduction no longer triggers over N runs, guarded by a new regression test.
  Assume a deterministic reproduction exists - the bug is in code, not cosmic rays.

DOES NOT COUNT
  - a hypothesis or narrative without a triggering reproduction
  - a fix that lowers frequency but does not eliminate the reproduced case
  - a mechanism explaining only a subset of observed corruptions
  - "probably network" / "data drift" without an identified code path
  - retries or checksums that mask rather than remove the cause
  - a post-mortem without a reproduction

VERIFICATION (fresh-context adversarial reviewer)
  Confirm the reproduction triggers on a clean checkout; that reverting the fix
  re-triggers it (necessity); that the fix targets the mechanism, not a timing
  accident (stress under different thread counts and schedules); check for ABA and
  lost-update masking; confirm the regression test fails before the fix and passes
  after. Every claim traces to a log line, a repro run, or a diff.

RETURN CONDITION
  Return only when reproduction + mechanism + fix + passing regression test hold and
  survive the audit. Do not return a hypothesis list or a frequency reduction.

EFFORT
  Spend at least <floor>; do not stop because the bug is rare. Re-inject the verified-
  progress ledger each session (what is reproduced, what is ruled out) so multi-
  session drift does not restart the search.

CONTAMINATION
  Search only for library/runtime concurrency semantics and documented API behavior.
  Do not adopt an unrelated "known bug" as the answer without reproducing it here.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": NA,
                       "reporting": 0, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": NA,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Success predicate",
             "text": "'Find the root cause' becomes 'a mechanism with a deterministic reproduction that disappears when neutralized', which an adversarial reader can actually check."},
            {"dim": "Reporting contract",
             "text": "'Regular progress updates' + 'detailed post-mortem' is status theater. The brief requires a reproduction, a diff, and a regression test, with every claim traced to a log line or run (claim-long-horizon-evidence-audit)."},
            {"dim": "Return condition",
             "text": "'Until you understand what is happening' (confidence) becomes an artifact predicate: repro + fix + passing regression test that survive audit."},
            {"dim": "State ledger (persistence)",
             "text": "Adds a re-injected verified-progress ledger for the multi-session run, the countermeasure PushBench found rescued long tasks that prompt-only setups failed (claim-long-horizon-state-ledger)."},
        ],
        "residual": "'Assume a deterministic reproduction exists' is solvability framing, which is "
                    "safe here because the bug is in code. On a genuinely heisenbug-adjacent "
                    "failure (hardware, cosmic-ray ECC), that clause would push the agent to "
                    "fabricate a repro rather than conclude the cause is non-deterministic. The "
                    "ledger re-injection is a harness job, not something the prompt can do alone.",
    },
    # ------------------------------------------------------------------ Pair 4
    {
        "id": "security-audit",
        "title": "Autonomous security audit / red-team",
        "domain": "Application security",
        "topology": "Orchestrator with parallel workers per attack surface",
        "horizon": "Long, unattended, against a staging target",
        "summary": "Persistence plus a category checklist plus 'list every vulnerability' produces "
                   "an inflated report of unconfirmed findings. The brief makes a working proof-of-"
                   "concept the unit of a finding.",
        "before_techniques": [
            "Offensive-security persona and named targets",
            "Comprehensive attack-surface checklist",
            "Severity-rating scheme and professional report format",
            "Attacker-mindset persistence framing",
        ],
        "before": """You are an elite offensive-security researcher. Audit our web application
(source in /app, staging at https://staging.internal) and find security
vulnerabilities.

Look everywhere: authentication, authorization, injection (SQL, command, template),
SSRF, deserialization, secrets in code, dependency CVEs, business-logic flaws, and
access control. Use your full expertise. For each issue, rate severity
(Critical/High/Medium/Low) and explain the risk.

Be extremely thorough and persistent - a real attacker would be, so you should be
too. Do not stop until you have done a comprehensive sweep. Produce a professional
pentest report listing every vulnerability you find, sorted by severity, with
remediation advice.""",
        "after": """DEFINITIONS
  "Confirmed vulnerability" = a finding with a working proof-of-concept that
  demonstrates concrete security impact (unauthorized data access, code execution,
  privilege escalation, etc.) against an in-scope target, reproducible from a written
  PoC within the rules of engagement (RoE). Severity is defined by demonstrated
  impact and preconditions, not by category. Scope = the in-scope host/path allowlist
  and the RoE.

TASK
  Produce a set of confirmed vulnerabilities, each with a reproducible PoC showing
  concrete impact against in-scope targets, plus a remediation that, when applied,
  makes the PoC fail.

DOES NOT COUNT
  - unconfirmed or theoretical findings without a PoC
  - scanner/linter output not reduced to a working exploit
  - dependency CVEs not shown exploitable in this application's usage
  - missing-hardening "informational" notes presented as vulnerabilities
  - findings outside scope or the RoE
  - multiple reports of one root cause
  - a severity claim without a demonstrated impact

ORCHESTRATION
  Diverse portfolio across attack surfaces (authn, authz/IDOR, injection, SSRF,
  deserialization, secrets, business logic). Keep workers independent early so they
  do not all chase one lead. Registry keyed by vulnerability class and root cause.
  Mark a surface blocked when it stalls; reopen for a materially new technique. Every
  spawned worker gets an objective, an in-scope target, tool/RoE guidance, and
  boundaries. Do not let one flashy finding monopolize the team.

VERIFICATION (fresh-context adversarial reviewer)
  Independently re-run each PoC on a clean session to confirm it triggers (no false
  positive); confirm the impact is real and in-scope; confirm the PoC does not rely
  on seeded test data; confirm the remediation breaks the PoC. Every finding traces
  to a request/response, a session log, or a script.

RETURN CONDITION
  Return only confirmed, PoC-backed findings that survive re-verification. Do not
  return a padded list of potential issues or a scanner dump. A "surface is clean"
  claim requires evidence of what was tried.

EFFORT
  Spend at least <floor> across surfaces before calling a surface clean; do not stop
  at the first finding.

CONTAMINATION
  Use CVE databases and docs for background only; do not report a known CVE as a
  finding without a PoC confirming exploitability here. Stay within the RoE; the
  in-scope allowlist and destructive-action prohibitions are enforced by the
  network/runtime policy, not by this prompt.""",
        "scores": {
            "before": {"predicate": 1, "definitions": 0, "non_counting": 0, "auditor": 0,
                       "persistence_gate": 0, "return_condition": 0, "diversity": 1,
                       "reporting": 0, "contamination": 0, "harness": 0},
            "after": {"predicate": 2, "definitions": 2, "non_counting": 2, "auditor": 2,
                      "persistence_gate": 2, "return_condition": 2, "diversity": 2,
                      "reporting": 2, "contamination": 2, "harness": 2},
        },
        "deltas": [
            {"dim": "Non-counting outcomes",
             "text": "The highest-leverage change: theoretical findings, scanner output, and unexploited dependency CVEs are excluded by name, killing report-padding as a way to satisfy the letter."},
            {"dim": "Persistence-verification pairing",
             "text": "'Do not stop until comprehensive' with no confirmation gate rewards fabricated/inflated findings. The brief pairs it with independent PoC re-verification per finding."},
            {"dim": "Contamination guards",
             "text": "Blocks laundering known CVEs from the dependency list as 'findings' without a PoC, and pins retrieval to background only."},
            {"dim": "Harness separation",
             "text": "RoE, the in-scope allowlist, and destructive-action prohibitions are moved to network/runtime enforcement; the prompt states them only for planning."},
        ],
        "residual": "Scope and destructive-action limits stated in a prompt are advisory under "
                    "optimization pressure. If the network policy does not actually fence the "
                    "target allowlist, a persistent agent can still reach out of scope. The "
                    "brief reduces report-padding, but confirming impact without ever causing "
                    "harm on a live target is a RoE/harness problem the words cannot solve.",
    },
]

# Honest framing shown in the UI: the rubric is the skill's own pre-launch rubric, so a
# high "after" score means "fully applies the skill's checklist," measured by that checklist,
# not by an independent third party. The before prompts are competent prompt-engineered
# launch prompts, not strawmen.
HONESTY_NOTE = (
    "Scores use the skill's own 10-dimension pre-launch rubric, so a high 'after' score means "
    "the brief fully applies the skill's checklist as measured by that checklist. This is a "
    "structural comparison, not an outcome benchmark: it shows the briefs are harder to satisfy "
    "by a near miss, not that any specific run succeeds. The 'before' prompts are competent, "
    "prompt-engineered launch prompts (persona, context, chain-of-thought, explicit format, "
    "persistence), not strawmen. Each pair lists a residual risk the optimized brief still "
    "cannot remove."
)


def build() -> dict:
    pairs_out = []
    for p in PAIRS:
        before = score_block(p["scores"]["before"])
        after = score_block(p["scores"]["after"])
        pairs_out.append({
            **{k: p[k] for k in (
                "id", "title", "domain", "topology", "horizon", "summary",
                "before_techniques", "before", "after", "deltas", "residual", "scores")},
            "score_summary": {
                "before": before,
                "after": after,
                "gain_pp": after["pct"] - before["pct"],
            },
        })
    agg_before = sum(p["score_summary"]["before"]["pct"] for p in pairs_out) / len(pairs_out)
    agg_after = sum(p["score_summary"]["after"]["pct"] for p in pairs_out) / len(pairs_out)
    return {
        "meta": {
            "title": "Prompts for work that does not end in one turn.",
            "subtitle": "Four conventional launch prompts, rewritten as pseudo-formal task briefs for long-running agents.",
            "skill": "long-horizon-prompting",
            "exemplar": "OpenAI GPT-5.6 Sol Ultra Cycle Double Cover run (July 2026)",
            "rubric_source": "skills/long-horizon-prompting/references/task-brief-template.md",
            "honesty_note": HONESTY_NOTE,
            "aggregate": {
                "before_pct": round(agg_before),
                "after_pct": round(agg_after),
                "gain_pp": round(agg_after - agg_before),
                "pairs": len(pairs_out),
            },
        },
        "rubric": RUBRIC,
        "pairs": pairs_out,
    }


def main() -> int:
    data = build()
    (LAB / "data").mkdir(exist_ok=True)
    (LAB / "ui").mkdir(exist_ok=True)
    json_path = LAB / "data" / "prompt-pairs.json"
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    js_path = LAB / "ui" / "data.js"
    js_path.write_text(
        "// Generated by scripts/build_lab.py - do not edit by hand.\n"
        "window.PROMPT_LAB_DATA = " + json.dumps(data, indent=2) + ";\n",
        encoding="utf-8",
    )
    agg = data["meta"]["aggregate"]
    print(f"Wrote {json_path.relative_to(LAB)} and {js_path.relative_to(LAB)}")
    print(f"Pairs: {agg['pairs']} | aggregate before {agg['before_pct']}% -> after {agg['after_pct']}% "
          f"(+{agg['gain_pp']}pp)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
