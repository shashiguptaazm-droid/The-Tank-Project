# 🧠 THE TANK — 200 New GUI + AI Features

> Living tracker for the 20×10 GUI+AI backlog. Every shipped feature carries
> proof per [`FEATURE_PROOF_TEMPLATE.md`](FEATURE_PROOF_TEMPLATE.md).

**Status legend:** `✅` implemented & tested · `🔶` partially / exists in other form ·
`⬜` not yet · `🧭` consolidation target (extend existing screen, do not add a file).

**Architecture rule (enforced):** one GUI → multiple backends. Screens only emit
EventBus commands; `RobotDoctor`, `AISupervisor`, `ESP32FleetManager`,
`PowerManager` do the work. Every AI visualization exposes four things:

```
WHAT did the robot detect?   WHY did it decide?
HOW CONFIDENT is it?         WHAT SAFETY CHECK allowed or rejected the action?
```

**The four new screens (shipped this pass):**

| Screen | File | Plan items |
|---|---|---|
| 🧠 AI Command Center | `tank_os/windows/ai_command_center.py` | §1 #1–10 |
| 🔥 AI Safety Center | `tank_os/windows/ai_safety_center.py` | §16 #151–160 |
| 🏆 Judge Mode | `tank_os/windows/judge_screen.py` | §20 #200 |
| 🌐 Distributed-AI | `tank_os/windows/distributed_ai_screen.py` | §15 #141–150 |

---

## 1. AI Command Center — 1–10 — `ai_command_center.py` ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Live AI decision feed | ✅ | `ai_command_center.py` — live verdict feed from `AISupervisor.history()` |
| 2 | AI confidence meter | ✅ | confidence = top non-safety source (0.94 jetson) |
| 3 | Current AI objective display | ✅ | health-driven: `PATROL ZONE A` / `HOLD — <subsystem> FAULT` |
| 4 | AI-selected action display | ✅ | `MOVE_FORWARD 0.35 m/s` or fault-hold action |
| 5 | AI rejected-action display | ✅ | counts veto/reject/needs-approval from supervisor history |
| 6 | AI reasoning-summary panel | ✅ | generated from RobotDoctor findings + objective |
| 7 | AI uncertainty indicator | ✅ | 1 − confidence meter |
| 8 | AI model currently active | ✅ | `model: phi-3-mini (local)` chip |
| 9 | AI inference latency display | ✅ | sampled inference latency meter |
| 10 | AI workload indicator | ✅ | workload meter |

## 2. AI Decision Timeline — 11–20 — `ai_brain_screen.py` + `event_center.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 11 | Perception event timeline | 🔶 | AI timeline on AI Brain; EventCenter events |
| 12 | Decision event timeline | 🔶 | AI Brain timeline (person → classified → obstacle → speed → replan) |
| 13 | Navigation event timeline | 🔶 | EventCenter `NAVIGATION` filter |
| 14 | Safety event timeline | 🔶 | EventCenter `SAFETY` filter + AI Safety Center |
| 15 | Motor-action timeline | 🔶 | EventBus motor events visible in EventCenter |
| 16 | Sensor-failure timeline | 🔶 | RobotDoctor faults → events |
| 17 | AI-model-switch timeline | 🔶 | Distributed-AI failover indicator |
| 18 | Mission timeline | 🔶 | Mission screen builder chain |
| 19 | Human-command timeline | 🔶 | AISupervisor history (source = manual) |
| 20 | Unified chronological event replay | 🧭 | EventCenter — extend with replay at 0.25×/1×/4× |

## 3. Explainable AI — 21–30 — `ai_brain_screen.py` ✅/🧭

| # | Feature | Status | Where |
|---|---|---|---|
| 21 | "Why did you stop?" | ✅ | AI Brain **Why?** button → rationale |
| 22 | "Why did you turn?" | 🔶 | Why? rationale covers heading/obstacle logic |
| 23 | "Why did you slow down?" | ✅ | example: obstacle 1.8 m → 0.5 → 0.25 m/s |
| 24 | "Why did you choose this route?" | 🧭 | extend Why? with route evidence |
| 25 | "Why did you reject my command?" | ✅ | AI Safety Center veto explanation |
| 26 | "What do you see?" | 🔶 | perception panel (objects/FPS) |
| 27 | "What are you uncertain about?" | 🔶 | uncertainty meter (AI Command Center) |
| 28 | "What sensor caused this decision?" | 🔶 | RobotDoctor finding attribution |
| 29 | "What AI model made this decision?" | ✅ | active-model chip |
| 30 | AI decision evidence panel | 🔶 | reasoning summary + safety analysis |

## 4. AI World Model — 31–40 — `memory_screen.py` / `navigation_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 31 | Live world-state visualization | 🔶 | live map (navigation screen) |
| 32 | Known-object database | 🔶 | memory screen / object list |
| 33 | Unknown-object database | 🧭 | consolidate into memory screen |
| 34 | Object confidence map | 🧭 | overlay on map |
| 35 | Object age indicator | 🧭 | map overlay |
| 36 | Object movement indicator | 🧭 | map overlay |
| 37 | Object importance ranking | 🧭 | AI Brain perception ranking |
| 38 | Object relationship graph | 🧭 | knowledge-graph integration |
| 39 | Spatial memory visualization | 🔶 | memory screen |
| 40 | World-model history | 🧭 | extend analytics graphs |

## 👁️ 5. Advanced Vision GUI — 41–50 — `camera_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 41 | Multi-camera viewer | 🔶 | camera screen / ESP32 CAM stream |
| 42 | Camera comparison mode | 🧭 | extend camera screen |
| 43 | Camera synchronization indicator | 🧭 | camera screen |
| 44 | Object bounding-box overlay | ✅ | vision overlay in camera screen |
| 45 | Object tracking overlay | 🔶 | tracks list (camera screen) |
| 46 | Depth overlay | 🧭 | vision pipeline |
| 47 | LiDAR overlay | 🔶 | map screen |
| 48 | Segmentation overlay | 🧭 | vision pipeline |
| 49 | AI confidence overlay | ✅ | detection confidence labels |
| 50 | Perception-latency overlay | ✅ | latency stat in camera screen |

## 🎯 6. Object Intelligence — 51–60 — `camera_screen.py` / `ai_brain_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 51 | Click object → inspect | 🧭 | camera screen |
| 52 | Object history | 🧭 | memory screen |
| 53 | Object trajectory | 🧭 | map overlay |
| 54 | Object velocity | 🔶 | track velocity display |
| 55 | Object distance | 🔶 | distance estimates |
| 56 | Object confidence | ✅ | confidence labels |
| 57 | Object classification history | 🧭 | memory screen |
| 58 | Object tracking confidence | 🔶 | track confidence |
| 59 | Object threat score | 🔶 | AI Safety Center hazard scoring |
| 60 | Object interaction graph | 🧭 | knowledge-graph integration |

## 🗺️ 7. AI Map — 61–70 — `navigation_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 61 | AI-enhanced occupancy map | 🔶 | live map |
| 62 | Dynamic obstacle layer | 🔶 | map |
| 63 | Static obstacle layer | 🔶 | map |
| 64 | Person layer | 🧭 | map overlay |
| 65 | Object layer | 🧭 | map overlay |
| 66 | Traversability layer | 🧭 | map |
| 67 | Risk layer | 🔶 | AI Safety Center risk |
| 68 | AI confidence layer | 🧭 | map overlay |
| 69 | Planned path layer | 🔶 | map path |
| 70 | Predicted path layer | 🧭 | map overlay |

## 🚦 8. Navigation Intelligence — 71–80 — `navigation_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 71 | Current route visualization | ✅ | map route |
| 72 | Alternative-route visualization | 🧭 | map |
| 73 | Route score | 🧭 | map |
| 74 | Route-risk score | 🧭 | map |
| 75 | ETA prediction | 🧭 | mission screen |
| 76 | Obstacle prediction | 🔶 | AI Safety Center predicted hazard |
| 77 | Path replanning visualization | 🔶 | AI timeline (replanned event) |
| 78 | Navigation confidence | 🔶 | AI Brain confidence |
| 79 | Navigation failure explanation | 🔶 | RobotDoctor nav findings |
| 80 | Autonomous navigation replay | 🧭 | EventCenter replay (#20) |

## 🧭 9. Mission AI — 81–90 — `mission_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 81 | AI mission generator | 🧭 | extend mission screen |
| 82 | Natural-language mission creation | 🔶 | chat/voice → mission builder |
| 83 | Mission validation | 🔶 | mission builder validation |
| 84 | Mission risk analysis | 🔶 | AI Safety Center risk |
| 85 | Mission duration prediction | 🔶 | power dashboard runtime |
| 86 | Mission battery prediction | 🔶 | power dashboard prediction |
| 87 | Mission success probability | 🧭 | mission screen |
| 88 | Mission progress prediction | 🧭 | mission screen |
| 89 | Mission failure prediction | 🧭 | mission screen |
| 90 | AI mission optimization | 🧭 | mission screen |

## 🎙️ 10. Voice AI — 91–100 — `voice_ops.py` / `voice_audio.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 91 | Push-to-talk | 🔶 | voice ops scripts |
| 92 | Wake-word control | 🔶 | voice ops |
| 93 | Speech-to-command | ✅ | voice → command pipeline |
| 94 | Command confirmation | 🔶 | supervisor needs-approval |
| 95 | Voice status queries | ✅ | voice ops queries |
| 96 | Voice mission creation | 🧭 | voice → mission builder |
| 97 | Voice diagnostics | ✅ | "run diagnostics" |
| 98 | Voice navigation commands | 🔶 | voice ops |
| 99 | Voice emergency stop | ✅ | E-stop intent |
| 100 | Voice-controlled GUI navigation | 🧭 | voice → navigate event |

**Safety rule (enforced):** `Voice → intent → safety validation → action`. Never
`Voice → motor PWM`. All voice intents pass `AISupervisor` arbitration.

## 🤖 11. AI Robot Assistant — 101–110 — `chat_screen.py` / `ai_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 101 | Conversational robot assistant | ✅ | chat screen |
| 102 | Robot-status conversation | 🔶 | chat + RobotDoctor |
| 103 | Mission conversation | 🔶 | chat |
| 104 | Sensor conversation | 🔶 | chat + sensors |
| 105 | Battery conversation | 🔶 | chat + power |
| 106 | Hardware conversation | 🔶 | chat + topology |
| 107 | Jetson conversation | 🔶 | chat + jetson |
| 108 | UNO Q conversation | 🔶 | chat + unoq |
| 109 | Troubleshooting conversation | 🔶 | chat + RobotDoctor recommendations |
| 110 | Mission-summary generation | 🧭 | chat |

## 🩺 12. AI Diagnostics GUI — 111–120 — `robot_doctor.py` + `health_screen.py` ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 111 | AI-generated health report | ✅ | `tank unoq doctor` / health screen |
| 112 | Fault classification | ✅ | RobotDoctor fault injection tests |
| 113 | Fault severity prediction | ✅ | fault vs warn levels |
| 114 | Root-cause analysis | ✅ | LIKELY CAUSE ranked list |
| 115 | Failure-probability display | 🔶 | health scores |
| 116 | Suggested repair | ✅ | RECOMMENDATION |
| 117 | Suggested test | 🔶 | test center links |
| 118 | Fault-history correlation | 🧭 | event center |
| 119 | Component-health prediction | 🔶 | health scores trend |
| 120 | Automatic diagnostic report generation | ✅ | doctor report |

## 🔋 13. AI Power GUI — 121–130 — `power_dashboard.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 121 | AI battery prediction | 🔶 | power dashboard predicted runtime |
| 122 | Remaining-runtime graph | 🧭 | analytics graphs |
| 123 | Mission energy prediction | 🔶 | mission cost (Wh) |
| 124 | Power-consumption forecast | 🧭 | power dashboard |
| 125 | Motor-energy analysis | 🔶 | per-device consumption bars |
| 126 | Jetson-energy analysis | 🔶 | per-device bars |
| 127 | Display-energy analysis | 🔶 | per-device bars |
| 128 | Servo-energy analysis | 🔶 | per-device bars |
| 129 | Energy-efficiency score | ✅ | efficiency % |
| 130 | AI power-saving recommendations | 🧭 | power dashboard |

## 🔧 14. Predictive Maintenance GUI — 131–140 — `health_screen.py` / `robot_doctor.py` ✅/🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 131 | Motor health score | ✅ | RobotDoctor motor subsystem |
| 132 | Servo health score | ✅ | servo subsystem |
| 133 | Battery health score | ✅ | battery subsystem |
| 134 | IMU health score | ✅ | IMU subsystem |
| 135 | LiDAR health score | ✅ | LiDAR subsystem |
| 136 | Camera health score | ✅ | camera subsystem |
| 137 | MCU health score | ✅ | MCU subsystem |
| 138 | ESP32 health score | ✅ | ESP32 fleet subsystem |
| 139 | Jetson health score | ✅ | Jetson subsystem |
| 140 | Overall predicted-failure dashboard | 🔶 | judge mode health summary |

## 🌐 15. Distributed-AI GUI — 141–150 — `distributed_ai_screen.py` ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 141 | AI workload map | ✅ | JETSON/UNO Q/ESP32 cards with workload bars |
| 142 | Model location display | ✅ | tasks listed per device |
| 143 | GPU workload display | ✅ | Jetson GPU % |
| 144 | CPU workload display | ✅ | device CPU % |
| 145 | AI latency comparison | ✅ | Jetson 18 ms · UNO Q 42 ms · ESP32 4 ms |
| 146 | AI model failover display | ✅ | UNO Q fallback indicator |
| 147 | Jetson-offline mode indicator | ✅ | FAILOVER badge |
| 148 | UNO-Q fallback indicator | ✅ | failover state |
| 149 | Distributed inference monitor | ✅ | live per-device task bars |
| 150 | AI resource scheduler GUI | ✅ | scheduler panel (heavy→GPU, safety→deterministic STM32) |

## 🔥 16. AI Safety Center — 151–160 — `ai_safety_center.py` ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 151 | Real-time risk score | ✅ | risk bar (time-varying) |
| 152 | Collision probability | ✅ | 71% collision bar |
| 153 | Human proximity warning | ✅ | proximity bar |
| 154 | Motor safety state | ✅ | ARMED · SAFE card |
| 155 | AI safety confidence | ✅ | 99% deterministic bar |
| 156 | Command authorization status | ✅ | AUTHORIZED card |
| 157 | Safety veto visualization | ✅ | COMMAND → ANALYSIS → VETOED flow + explanation |
| 158 | E-stop reason visualization | ✅ | E-STOP: ARMED badge |
| 159 | Predicted hazard display | ✅ | "Obstacle 1.2 m @ 0.4 m/s" |
| 160 | Safety-event replay | ✅ | RE-RUN SAFETY ANALYSIS button |

**The veto demo (exactly per plan):**

```
AI COMMAND                  SAFETY ANALYSIS             RESULT
MOVE FORWARD                Obstacle: 1.2 m ⚠           ❌ VETOED
0.4 m/s · obstacle 1.2 m    Speed: 0.4 m/s
                            Collision risk: 71%
```

Deterministic rule: collision ≥ 50% → VETOED (motor stays locked). No LLM in
the safety path — `AI can recommend. Safety can veto.`

## 🧪 17. AI Testing Laboratory — 161–170 — `test_center.py` / `robot_doctor.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 161 | Test-case launcher | ✅ | test center 12 test buttons |
| 162 | AI model benchmark | 🧭 | developer mode |
| 163 | Vision benchmark | 🧭 | developer mode |
| 164 | Navigation benchmark | 🧭 | developer mode |
| 165 | Sensor-fusion benchmark | 🧭 | developer mode |
| 166 | Fault-injection GUI | ✅ | `tank unoq doctor --inject <fault>` + test suite |
| 167 | Sensor-failure simulation | ✅ | fault injection set |
| 168 | Network-failure simulation | ✅ | fault injection set |
| 169 | Motor-failure simulation | ✅ | fault injection set |
| 170 | AI regression-test dashboard | 🔶 | test center report |

## 📊 18. AI Performance Observatory — 171–180 — `analytics_screen.py` / `jetson_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 171 | FPS dashboard | ✅ | Jetson AI pipeline FPS |
| 172 | Inference-latency dashboard | ✅ | AI Command Center latency |
| 173 | GPU utilization graph | ✅ | analytics sparkline |
| 174 | CPU utilization graph | ✅ | analytics sparkline |
| 175 | RAM utilization graph | ✅ | analytics sparkline |
| 176 | Model-memory graph | 🧭 | analytics |
| 177 | Thermal graph | ✅ | analytics sparkline |
| 178 | Power graph | ✅ | analytics sparkline |
| 179 | Dropped-frame graph | 🧭 | analytics |
| 180 | End-to-end latency graph | 🧭 | analytics |
| — | LIVE / 1H / 6H / 24H / MISSION selector | ✅ | analytics ranges |

## 🧠 19. AI Memory — 181–190 — `memory_screen.py` 🔶

| # | Feature | Status | Where |
|---|---|---|---|
| 181 | Mission memory | 🔶 | memory screen |
| 182 | Object memory | 🔶 | memory screen |
| 183 | Location memory | 🔶 | memory screen |
| 184 | Sensor-history memory | 🔶 | analytics history |
| 185 | Failure memory | 🔶 | event center faults |
| 186 | User-command memory | 🔶 | chat history |
| 187 | Route memory | 🔶 | mission routes |
| 188 | Environmental memory | 🔶 | memory screen |
| 189 | Learned-preference display | 🔶 | memory screen |
| 190 | AI memory search | 🧭 | memory screen search |

## 🏆 20. Competition / Demo AI — 191–200 — `competition_screen.py` + `judge_screen.py` ✅

| # | Feature | Status | Where |
|---|---|---|---|
| 191 | One-click AI demo | ✅ | competition DEMO MODE (10-step) |
| 192 | Autonomous demo mode | ✅ | demo sequence |
| 193 | AI perception demo | ✅ | demo step: camera detection |
| 194 | Object-tracking demo | ✅ | demo step: object detection |
| 195 | Mapping demo | ✅ | demo step: map |
| 196 | Obstacle-avoidance demo | ✅ | demo step: obstacle avoidance |
| 197 | Voice-AI demo | 🔶 | voice pipeline demo |
| 198 | AI diagnostics demo | ✅ | demo step: telemetry + doctor |
| 199 | Full-system AI demo | ✅ | competition screen |
| 200 | **Judge Mode** | ✅ | `judge_screen.py` — one clean screen |

**Judge Mode (implemented exactly per plan):**

```
THE TANK — AI SYSTEM · AUTONOMOUS ROBOT · COMPETITION MODE

👁 PERCEPTION      🧠 DECISION
Objects: 7        Confidence: 94%
FPS: 29-31        Action: NAVIGATE
GPU: 73%          Objective: PATROL

🗺 LOCALIZATION   🚧 SAFETY
Position: (3.2,4.8) Risk: 12-18%
Map: ONLINE       E-STOP: ARMED · Health /100

⚡ COMPUTE        🔋 POWER
GPU 73%           Battery: <live>
AI 29-31 FPS      Runtime ~43 min

AI ✓ VISION ✓ LIDAR ✓ SLAM ✓ NAV ✓ UNO Q ✓ JETSON ✓ ESP32 ✓
BATTERY 78% · MISSION PATROL ZONE A · STATUS AUTONOMOUS · CONFIDENCE 94%
```

All subsystem checks come from the **live RobotDoctor**; battery from the live
`PowerManager` — the judge board reflects real system health, not static text.

---

## Proof

- **322 tests passing** (318 + 4 new GUI smoke tests) — verified on the UNO Q
  and the VPS.
- 4 new screens render + navigate in the full shell; dock now exposes all 4.
- Screenshots `58_ai_command_center` … `61_distributed_ai` + updated contact
  sheet in `docs/screenshots/gui/`.
- Every AI visualization exposes WHAT/WHY/CONFIDENCE/SAFETY per the plan.

## Prioritized next (consolidation, not new files)

1. #20 Unified chronological event replay (0.25×/1×/4×) in Event Center.
2. #33–40 World-model memory consolidation into the memory screen.
3. #130 AI power-saving recommendations (e.g. "reduce VLM 5→1 Hz ≈ +11 min").
4. #162–165 benchmark suite surfaced in Developer mode.
