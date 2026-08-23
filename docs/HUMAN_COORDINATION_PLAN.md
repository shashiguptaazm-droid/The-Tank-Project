# 👤 THE TANK — Human Coordination AI (100 features)

> Living tracker. The robot understands **who is commanding it, what humans are
> doing around it, where they are, what they want, and when it should ask for
> permission instead of acting autonomously** — a dedicated human-coordination
> subsystem, not a pile of buttons.

**Status legend:** `✅` implemented & tested · `🔶` partially / exists in other form ·
`⬜` not yet · `🧭` consolidation target (extend existing module/screen).

**Core modules:** `tank_os/core/human_coordination.py` (people, interaction
modes, control authority, human-in-the-loop requests, ask-the-human) ·
`tank_os/windows/human_control_center.py` (the dedicated GUI).

---

## 1. Human presence & awareness — 1–20

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Human detection | ✅ | `Person` registry + RobotDoctor camera subsystem |
| 2 | Multiple-human detection | ✅ | `people()` dict of tracked persons |
| 3 | Human tracking IDs | ✅ | sequential `Person.id` |
| 4 | Human distance estimation | ✅ | `distance_m` (proximity zones) |
| 5 | Human direction estimation | ✅ | `direction_deg` |
| 6 | Human velocity estimation | ✅ | `velocity_ms` (signed toward robot) |
| 7 | Human approach detection | ✅ | `PresenceState.APPROACHING` |
| 8 | Human departure detection | ✅ | `PresenceState.DEPARTING` |
| 9 | Human stationary-state detection | ✅ | `PresenceState.STATIONARY` |
| 10 | Human proximity zones | ✅ | danger 0.5 / warning 1.5 / comfort 3.0 m |
| 11 | Safe-distance monitoring | ✅ | zone + `PROXIMITY_ZONES` |
| 12 | Human density estimation | 🧭 | count of active persons |
| 13 | Crowd detection | 🧭 | density threshold on people list |
| 14 | Group detection | 🔶 | group coordination (§group, below) |
| 15 | Person-isolated-from-group detection | 🧭 | group analysis |
| 16 | Human movement prediction | 🧭 | extrapolate velocity |
| 17 | Human trajectory visualization | 🧭 | map overlay from `history` |
| 18 | Human confidence score | ✅ | `confidence` per person |
| 19 | Human visibility confidence | 🔶 | confidence doubles as visibility |
| 20 | Human presence history | ✅ | per-person `history` + interaction log |

## 🧍 2. Human–robot interaction — 21–40

| # | Feature | Status | Where |
|---|---|---|---|
| 21 | Follow-me mode | ✅ | `InteractionMode.FOLLOW` + GUI FOLLOW button |
| 22 | Stop-follow mode | ✅ | `InteractionMode.STOP` + GUI STOP button |
| 23 | Person-relative navigation | 🔶 | follow uses person distance/heading |
| 24 | Maintain-distance mode | ✅ | `MAINTAIN_DISTANCE` mode |
| 25 | Maintain-angle mode | ✅ | `MAINTAIN_ANGLE` mode |
| 26 | Escort mode | ✅ | `ESCORT` + GUI ESCORT button |
| 27 | Lead-me mode | ✅ | `LEAD` mode |
| 28 | Stay-with-me mode | 🔶 | follow-family mode |
| 29 | Meet-me-at-location | ✅ | `MEET` mode |
| 30 | Return-to-owner location | ✅ | `RETURN_TO_OWNER` + GUI RETURN button |
| 31 | Human proximity warning | ✅ | danger/warning zones |
| 32 | Human collision prevention | ✅ | constitution Article 1 veto |
| 33 | Human crossing detection | ✅ | `PresenceState.CROSSING` |
| 34 | Human approaching warning | ✅ | APPROACHING presence |
| 35 | Human blocking-path detection | 🧭 | nav + presence fusion |
| 36 | Human-guided navigation | ✅ | `HUMAN_GUIDED` mode |
| 37 | Human waypoint confirmation | 🧭 | ask-the-human on waypoints |
| 38 | Human-assisted exploration | 🧭 | mission + human input |
| 39 | Human-assisted recovery | 🔶 | approve/reject recovery plan |
| 40 | Human interaction state machine | ✅ | mode enum + history transitions |

## 👋 3. Gesture interaction — 41–50

| # | Feature | Status | Where |
|---|---|---|---|
| 41 | Hand-wave detection | 🧭 | vision pipeline |
| 42 | Stop gesture | 🧭 | vision + safety validation |
| 43 | Start gesture | 🧭 | vision |
| 44 | Come-here gesture | 🧭 | vision |
| 45 | Follow gesture | 🧭 | vision |
| 46 | Pointing detection | 🧭 | vision |
| 47 | Direction-of-pointing estimation | 🧭 | vision + attention model |
| 48 | Thumbs-up recognition | 🧭 | vision |
| 49 | Thumbs-down recognition | 🧭 | vision |
| 50 | Hand-raised request | 🧭 | vision |

> Rule (enforced): gestures become commands only after **confidence + safety
> validation** — same `AISupervisor`/constitution path as every other input.

## 🗣️ 4. Voice coordination — 51–60 — `voice_ops.py` / `voice_audio.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 51 | Voice wake word | 🔶 | voice ops |
| 52 | Speech-to-command | ✅ | voice → intent pipeline |
| 53 | "Follow me" | 🔶 | voice intent → FOLLOW mode |
| 54 | "Stop" | ✅ | stop intent |
| 55 | "Come here" | 🔶 | meet intent |
| 56 | "Stay here" | 🔶 | stop/stay intent |
| 57 | "Go there" | 🔶 | nav intent |
| 58 | "Return home" | 🔶 | return intent |
| 59 | "Start mission" | ✅ | mission intent |
| 60 | "Cancel mission" | ✅ | cancel intent |

> Chain enforced: USER → VOICE → INTENT → CONFIDENCE → AUTHORIZATION →
> SAFETY CHECK → ACTION (voice never touches motor PWM directly).

## 🧠 5. Human intent AI — 61–70

| # | Feature | Status | Where |
|---|---|---|---|
| 61 | Intent classification | 🔶 | voice intent classifier |
| 62 | Command confidence | ✅ | `AISupervisor` confidences |
| 63 | Ambiguous-command detection | ✅ | `ask_human()` low-confidence path |
| 64 | Context-aware command interpretation | 🔶 | mode-aware intents |
| 65 | Command confirmation | ✅ | approve/reject requests |
| 66 | Contradictory-command detection | 🧭 | arbitration of conflicting sources |
| 67 | Repeated-command detection | 🧭 | history scan |
| 68 | User-command priority | ✅ | `human_priority_check` |
| 69 | Human-vs-autonomy arbitration | ✅ | authority chain + priority check |
| 70 | **"Ask human" decision** | ✅ | `resolve_route_ambiguity` demo — LEFT/RIGHT |

## 🎮 6. Human control arbitration — 71–80

| # | Feature | Status | Where |
|---|---|---|---|
| 71 | Manual override | ✅ | `human_takes_control()` |
| 72 | Autonomous override | ✅ | `autonomy_resumes()` |
| 73 | Remote-control priority | 🔶 | remote source → human role |
| 74 | Local-control priority | 🔶 | local manual source |
| 75 | Emergency-stop priority | ✅ | `emergency_stop()` → SAFETY |
| 76 | Human-command priority | ✅ | authority chain |
| 77 | Mission priority | ✅ | `mission_priority()` |
| 78 | Safety priority | ✅ | SAFETY first in chain |
| 79 | Command queue visualization | 🔶 | pending request list |
| 80 | Current-controller indicator | ✅ | GUI authority dots (HUMAN ● ACTIVE) |

## 🤝 7. Human + AI collaboration — 81–90 — human-in-the-loop autonomy ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 81 | AI proposes action | ✅ | `ai_propose()` |
| 82 | Human approves action | ✅ | `approve()` + GUI APPROVE |
| 83 | Human rejects action | ✅ | `reject()` + GUI REJECT |
| 84 | AI requests clarification | ✅ | `ask_human()` |
| 85 | AI requests permission | ✅ | pending requests |
| 86 | Human modifies AI plan | ✅ | `modify()` + GUI MODIFY |
| 87 | Human pauses AI | 🧭 | pause state |
| 88 | Human resumes AI | 🧭 | resume state |
| 89 | Human takes control | ✅ | `human_takes_control()` |
| 90 | AI hands control back | ✅ | `autonomy_resumes()` |

```
AI → PROPOSE → HUMAN (APPROVE / MODIFY / REJECT) → SAFETY → ROBOT
```

## 🖥️ GUI — Human Control Center ✅

`tank_os/windows/human_control_center.py` — the plan's exact screen:

```
👤 PERSON #01 · Distance: 2.4 m · Direction: 37° · Status: FOLLOWING · Conf: 94%
   [ FOLLOW ] [ STOP ] [ ESCORT ] [ RETURN ]
CONTROL AUTHORITY  SAFETY ○ HUMAN ● MISSION ○ AUTONOMY ○
🤝 AI REQUEST  "Obstacle detected. Change route?"  [ APPROVE ] [ REJECT ] [ MODIFY ]
🤔 ASK THE HUMAN  "I found two possible routes. Which should I take?"  [ LEFT ] [ RIGHT ]
INTERACTION HISTORY  (live event log)
```

## 🧑🤝🧑 Human group coordination — 91–100

| # | Feature | Status | Where |
|---|---|---|---|
| 91 | Human-group formation detection | 🧭 | people list clustering |
| 92 | Group centroid tracking | 🧭 | multi-person centroids |
| 93 | Group movement prediction | 🧭 | velocity fusion |
| 94 | Group splitting detection | 🧭 | cluster analysis |
| 95 | Group merging detection | 🧭 | cluster analysis |
| 96 | Follow designated person | ✅ | `_designated_id` follow |
| 97 | Ignore non-commanding people | 🔶 | designated-person focus |
| 98 | Human priority selection | 🔶 | nearest/designated |
| 99 | Human interaction history | ✅ | `interaction_history()` |
| 100 | Multi-human coordination manager | 🔶 | `HumanCoordination` singleton |

---

## Proof

- **345 tests passing** (328 + 17 new: person tracking/presence/zones, follow/stop
  modes, authority chain + E-stop, approve/reject/modify, ask-the-human,
  constitution vetoes ×5, AI debate, command chain + 3 new GUI smoke tests).
- Screenshots `62_human_control_center`, `63_constitution_debate`,
  `64_robot_knowledge_map` + updated contact sheet (26 screens).
- Verified on the UNO Q and the VPS.

## Prioritized next

1. #41–50 gesture interaction via the vision pipeline (confidence + safety validated).
2. #16–17 human movement prediction + trajectory overlay on the map.
3. #12–15 density / crowd / group analysis.
