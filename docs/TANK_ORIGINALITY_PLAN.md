# 🚀 THE TANK — 25 Originality Ideas

> System-level ideas that give the project a distinctive identity: combining
> AI, human interaction, distributed computing, and the unusual
> UNO Q + Jetson architecture. Positioning: **THE TANK — a
> Human-Collaborative, Self-Diagnosing, Distributed Edge-AI Robot.**

**Status legend:** `✅` implemented & tested · `🔶` partially · `⬜` not yet ·
`🧭` consolidation target.

---

| # | Idea | Status | Where |
|---|---|---|---|
| 1 | 🧠 **Robot "Self-Awareness" Map** — environment map + knowledge-confidence map + health map | ✅ | `tank_os/windows/knowledge_map_screen.py` — per-region confidence (North corridor 96% · Room A 88% · Behind obstacle 41% · Stair area 22%), custom-painted, live RobotDoctor health panel |
| 2 | 🤔 **"I Don't Know" AI** — explicit uncertainty, unknown objects request human confirmation | 🔶 | ask-the-human (route ambiguity) + uncertainty meters; object-labeling loop `🧭` |
| 3 | 👨🏫 **Human Teaches Robot** — demonstrate → learn → repeat | 🧭 | record demonstration route (mission memory) |
| 4 | 🧬 **Robot Digital Twin** — virtual copy, test-before-execute | 🧭 | simulator layer |
| 5 | 🪞 **Counterfactual AI** — "what if I chose the other action?" | 🔶 | AI debate shows alternatives; full chosen-vs-alternative `🧭` |
| 6 | 🧠 **Robot Memory Palace** — episodic memory ("at 14:31 I saw a chair here") | 🔶 | memory screen + mission history |
| 7 | 🗺️ **Uncertainty Map** — FREE/OCCUPIED/UNKNOWN/UNCERTAIN/DYNAMIC | 🔶 | knowledge-map regions (uncertain = yellow/red) |
| 8 | 🧠 **Distributed Brain** — Jetson / UNO Q / STM32 / ESP32 / VPS task map | ✅ | `tank_os/windows/distributed_ai_screen.py` |
| 9 | 🧩 **AI Task Migration** — Jetson overload/offline → UNO Q fallback | ✅ | distributed-AI failover indicator |
| 10 | 🩺 **Robot Doctor** — diagnose itself | ✅ | `RobotDoctor` + `tank unoq doctor` + health screens |
| 11 | 🧪 **Robot Laboratory** — experiments (motor/battery/sensor/nav/AI) | 🔶 | testing center + benchmark suite |
| 12 | 🎓 **Robot Learns From Humans** — "this is a charging station" semantic labels | 🧭 | knowledge graph + object memory |
| 13 | 👁️ **Human Attention Model** — where is the person paying attention? | 🧭 | vision pipeline |
| 14 | 🤝 **Shared Control** — human + autonomous simultaneously, AI assists | 🧭 | drive screen + human control |
| 15 | 🗣️ **Robot Negotiation** — "corridor blocked, alternate +18 s, proceed?" | 🔶 | ask-the-human + approve/reject requests |
| 16 | 🧠 **Mission Negotiation** — "search all building? needs 71%, have 64% → zones A+B?" | 🧭 | mission AI predictions |
| 17 | 🪫 **Energy-Aware Intelligence** — plan around energy, reject impossible missions | 🔶 | power dashboard predictions + recommendations |
| 18 | 🧠 **"What Changed?" AI** — environment diff vs previous missions | 🧭 | memory + map diff |
| 19 | 👻 **Ghost Map** — historical objects on the map | 🧭 | map layers |
| 20 | 🔮 **Predictive Environment** — predict where objects will be | 🧭 | trajectory prediction |
| 21 | 🧠 **AI Debate** — vision/nav/safety/resource modules vote, safety wins, explainable | ✅ | `RobotConstitution.debate()` + `tank_os/windows/constitution_screen.py` — VISION GO · NAVIGATION GO · SAFETY STOP · BATTERY GO → **FINAL: STOP (SAFETY)** |
| 22 | 🧑✈️ **Robot Command Chain** — authority explicit, every action has a visible source | ✅ | `command_chain_for()` — EMERGENCY STOP → SAFETY → HUMAN → MISSION → AI → AUTOMATION |
| 23 | 🧠 **Robot Dream Mode** — offline mission review / improvement generation | 🧭 | learning scheduler |
| 24 | 🧬 **Robot Evolution Dashboard** — measurable learning story (v1→current) | 🧭 | analytics + auto-evolution docs |
| 25 | 🌟 **Robot Constitution** — machine-readable priorities, every AI action passes through the policy engine | ✅ | `tank_os/core/robot_constitution.py` (8 articles, priority-ordered) + constitution screen — AI: MOVE FORWARD → Article 1 triggered → **VETO: Safety priority > mission priority** |

---

## 🌟 The Robot Constitution (idea #25) — the project's central philosophy

```
THE TANK CONSTITUTION
  1. Protect humans.                5. Complete mission.
  2. Never bypass safety.           6. Minimize energy consumption.
  3. Obey authorized humans.        7. Ask for help when uncertain.
  4. Preserve hardware.             8. Report failures honestly.
```

Every AI action passes through `RobotConstitution.check()`; verdicts carry the
triggered article, so vetoes are always explainable:

```
AI: MOVE FORWARD  →  Constitution: human detected + obstacle →  DECISION: VETO
REASON: Article 1 (Protect humans) > Article 5 (Complete mission)
```

## 🧠 AI Debate (idea #21) — the explainable multi-module vote

```
VISION:      GO      (conf 0.90)
NAVIGATION:  GO      (conf 0.85)
SAFETY:      STOP    (conf 1.00)  ← wins
BATTERY:     GO      (conf 0.91)
FINAL: STOP — SAFETY vetoes — safety wins over action.
```

## Proof

- **345 tests passing** — 17 new tests cover person tracking, interaction modes,
  authority + E-stop, approve/reject/modify, ask-the-human, all 5 constitution
  veto classes, the debate, and the command chain; 3 new GUI smoke tests.
- Screenshots `62_human_control_center` (the Human Control Center GUI),
  `63_constitution_debate` (constitution + debate + command chain),
  `64_robot_knowledge_map` (knowledge-confidence map) — in `docs/screenshots/gui/`.
- Verified on the UNO Q and the VPS.

## Prioritized next

1. #2 "I Don't Know" AI — unknown-object → human label → learn (closes the
   human-in-the-loop learning loop).
2. #3 Human Teaches Robot — demonstrated-route learning.
3. #24 Robot Evolution Dashboard — measurable learning story.
