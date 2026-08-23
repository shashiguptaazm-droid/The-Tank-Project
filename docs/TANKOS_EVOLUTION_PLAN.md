# 🧬 TankOS Evolution Engine — TEE (25 parts)

> **The Tank observes itself → identifies weaknesses → proposes an improvement →
> tests it safely → measures the result → promotes it only if objectively better →
> keeps rollback available.**

```
OBSERVE → ANALYZE → IDENTIFY WEAKNESS → GENERATE IMPROVEMENT → SIMULATE
→ TEST → BENCHMARK → COMPARE → HUMAN APPROVAL* → DEPLOY → MONITOR → ROLLBACK
```

* Human approval is mandatory for hardware, safety, firmware, security, or
  behavior changes.

**Status legend:** `✅` implemented & tested · `🔶` partially · `⬜` not yet ·
`🧭` consolidation target.

**Core module:** `tank_os/core/evolution_engine.py` · GUI:
`tank_os/windows/evolution_lab.py`.

---

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | **Evolution Manager** (`tank.evolution`) — weaknesses, proposals, experiments, versions, deploy, rollback, history | ✅ | `EvolutionEngine` singleton |
| 2 | **What can evolve** — AI/software/missions/UI params, bounded | ✅ | genome sections: navigation / vision / power / mission |
| 3 | **Performance baseline** — current version metrics | ✅ | `Baseline` (navigation 91%, detection 94%, latency 83 ms, completion 87%, battery 78%, recovery 72%) |
| 4 | **Weakness discovery** — pattern search over mission history | ✅ | `weaknesses()` — cause + location correlation with confidence |
| 5 | **Evolution proposal** — problem / change / expected / cost | ✅ | `propose()` → `EvolutionProposal` (#042-style card in the GUI) |
| 6 | **Digital twin test** — current vs candidate in simulation | 🔶 | replay benchmark over recorded missions; twin wiring `🧭` |
| 7 | **Replay-based evolution** — candidates tested against historical data | ✅ | `replay_benchmark()` — 91.2% → 95.1% style comparison |
| 8 | **A/B robot intelligence** — identical scenarios, measure accuracy/latency/energy/failures | 🔶 | experiment variants; full A/B harness `🧭` |
| 9 | **Multi-objective evolution** — safety 40% etc., **safety a hard constraint** | ✅ | `multi_objective_score()` — unsafe ⇒ score 0 |
| 10 | **Evolution generations** — GEN 0 → GEN n with scores | ✅ | `generations[]` + GUI timeline chips |
| 11 | **Evolution genome** — versioned config, bounded parameters | ✅ | `DEFAULT_GENOME` + `GENOME_BOUNDS` (clamped proposals) |
| 12 | **Evolution sandbox** — DEV → SIMULATION → SHADOW → PRODUCTION | 🔶 | `EvolutionStage` enum present; stage gating `🧭` |
| 13 | **Shadow mode** — candidate predicts silently beside current | ✅ | `shadow_compare()` + `shadow_summary()` (candidate better %) |
| 14 | **Automatic rollback** — return to previous known-good | ✅ | `rollback()` — reverts genome + generation |
| 15 | **Evolution checkpoints** — reproduce state before deploy | ✅ | `_checkpoint()` — code/config/model/params/env/deps |
| 16 | **"Why did I evolve?"** — explanation per evolution | ✅ | `prop.explanation` (replay evidence, not "AI improved itself") |
| 17 | **Human evolution approval** — GUI approve/reject with safety/sim/shadow status | ✅ | Evolution Lab — APPROVE / REJECT / DETAILS + ROLLBACK |
| 18 | **Evolution Lab GUI** — current/proposals/experiments/candidates/benchmarks/generations/deployments/rollbacks | ✅ | `evolution_lab.py` |
| 19 | **Auto-generated experiments** — battery high → A/B/C variants benchmarked | ✅ | `run_experiment()` — "Vision FPS vs battery" A:20/B:10/C:adaptive |
| 20 | **Resource-aware evolution** — reject candidates exceeding budgets | ✅ | `resource_check()` — predicted GPU/thermal risk gate |
| 21 | **Cross-device evolution** — optimize the whole robot (Jetson↔UNO Q↔ESP32) | 🧭 | ownership map exists; load migration experiments `🧭` |
| 22 | **Evolution memory** — learn from past failures | ✅ | `history[]` — proposed/approved/deployed/rollback events |
| 23 | **Evolution simulator** — "show how the robot evolved" judge demo | ✅ | `test_evolution_story_progression` — DAY 1 71% → DAY 14 94% monotonic story |
| 24 | **No uncontrolled self-modification** — explicit evolution policy | ✅ | `policy()` — AI may analyze/propose/simulate/benchmark/bound; may NOT disable safety / modify E-stop / raise motor limits / deploy arbitrary code |
| 25 | **The ultimate TankOS loop** — PERCEIVE→REASON→ACT→MEASURE→ANALYZE→EVOLVE→…→HUMAN APPROVAL→DEPLOY→MONITOR→KEEP/ROLLBACK | ✅ | engine implements the full loop end-to-end |

---

## 🧪 The proposal card (§5, §17)

```
EVOLUTION PROPOSAL #042
Problem:            Repeated navigation failures (12/50, corridor B, conf 88%)
Change:             navigation.prediction_horizon: 1.5 → 2.0
Expected:           ↓ collision risk · ↓ replanning frequency
Potential cost:     ↑ compute usage
Baseline → Candidate 91.2% → 95.1%  ·  Safety PASS ✓  ·  Simulation PASS ✓
[ APPROVE ] [ REJECT ] [ DETAILS ]
```

## 🧬 Generations (§10)

```
GEN 0 ──► GEN 1 ──► GEN 2 ──► GEN 3        (GUI timeline, score per version)
 82%      92%       94%       96%
```

## 📜 Evolution policy (§24) — enforced

```
AI MAY:      analyze · propose · simulate · benchmark · shadow-test ·
             optimize bounded parameters · replay historical data
AI may NOT:  disable safety · modify E-stop · increase motor limits ·
             modify electrical protection · change authentication ·
             replace safety firmware · deploy arbitrary executable code
```

## 🛡 Safety is a hard constraint (§9) — enforced

`multi_objective_score(..., safety_ok=False) → 0.0` — an unsafe candidate can
never win, regardless of how much accuracy it would add.

## Proof

- **398 tests passing** (380 + 18 new: baseline, weakness discovery, proposal
  bounds, replay benchmark, safety hard-gate, multi-objective weights,
  approve→deploy→rollback, reject, experiments, resource-aware rejection,
  shadow summary, policy, evolution story progression) — verified on VPS.
- Screenshot `67_evolution_lab` + 29-screen contact sheet.
- Verified on the UNO Q and the VPS.

## Prioritized next

1. §6/§8 — wire the digital twin + full A/B harness into replay benchmarking.
2. §21 — cross-device experiments (move preprocessing Jetson→UNO Q, measure).
3. §12 — enforce the sandbox stage gate (DEV→SIMULATION→SHADOW→PRODUCTION) in
   the approve pipeline.
