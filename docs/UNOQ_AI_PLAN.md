# 🧠 UNO Q — 150 Additional AI Features (local intelligence)

> Living tracker for the UNO Q AI backlog. The UNO Q's QRB2210 Linux side runs
> **lightweight local AI**; the STM32 side stays **deterministic / safety-critical**.
> Every shipped feature carries proof per
> [`FEATURE_PROOF_TEMPLATE.md`](FEATURE_PROOF_TEMPLATE.md).

**Status legend:** `✅` implemented & tested · `🔶` partially / exists in other form ·
`⬜` not yet · `🧭` consolidation target (extend existing module, do not add a file).

**Core principle (enforced by code):**

```
AI can recommend. Safety can veto.
```

The UNO Q/STM32 must never allow an LLM or other probabilistic model to
directly bypass motor safety. This is implemented in
[`tank_os/core/ai_supervisor.py`](tank_os/core/ai_supervisor.py) — see §AI
orchestration below.

---

## 🏆 The two competition features (shipped this pass)

### 🤖 "Diagnose robot" — Robot Doctor ✅
`tank unoq doctor` gathers telemetry from **10 subsystems** (motors, servos,
IMU, battery, CPU/RAM, MCU, Jetson, ESP32 fleet, network, services), scores
each, and produces a ranked diagnosis — health score, likely cause,
recommendation. **Fault-injection acceptance test passed:** 20 known faults,
each identified as the *correct* subsystem (see `tank_os/tests/test_robot_doctor.py`).

```
ROBOT HEALTH: 85/100
  ✓ Motors   ✓ Servos   ✓ IMU   ✓ Battery   ⚠ ESP32 #1/3 offline
  ✓ MCU      ✓ Network
LIKELY CAUSE: esp32 — ESP32 #1/3 offline / intermittent
RECOMMENDATION: → Reconnect/inspect esp32 and rerun diagnostics
```

### 🛡 AI Supervisor — confidence arbitration ✅
`tank unoq supervisor` shows the confidence board and arbitrates any command:

```
  🛡 hardware-safety  1.00 (safety)      ← can veto
  👤 manual           0.99 (manual)
  🤖 jetson           0.94 (ai)
  🤖 battery-pred     0.91 (ai)
  🤖 local-parser     0.87 (ai)

  Command      sudo poweroff
  From         jetson (conf 0.94)
  Safety class dangerous
  Verdict      ⚠️ NEEDS-APPROVAL        ← never auto-executed
```

Rules (deterministic, unit-tested): unknown sources REJECTed · safety
confidence 1.00 vetoes/authorizes · DANGEROUS commands from AI →
NEEDS-APPROVAL · highest-confidence non-safety source wins.

---

## 1. Local AI assistant — 1–20

1. [x] Local natural-language command parser — `AIRouter.natural_to_shell`
2. [x] Intent classification — `AIRouter` intent extraction
3. [x] Robot-command extraction — NL→shell JSON tool call
4. [x] Command confidence scoring — `AISupervisor` source confidence
5. [ ] Ambiguous-command detection 🧭
6. [ ] Command clarification engine 🧭
7. [x] Command history understanding — terminal history recall
8. [ ] Context-aware commands 🧭
9. [x] "Stop" semantic detection — safety gate + supervisor
10. [x] Emergency-language detection — safety classifier
11. [x] Local command fallback when Jetson unavailable — local-llama fallback
12. [x] Natural-language status queries — `tank unoq status`
13. [x] "What are you doing?" response — status command
14. [ ] "Why did you stop?" explanation 🧭
15. [x] "How much battery?" response — `tank unoq power`
16. [x] "Is Jetson connected?" response — `tank unoq mcu` / doctor
17. [x] "Check motors" command — `tank unoq motors`
18. [x] "Check sensors" command — `tank unoq sensors`
19. [x] "Run diagnostics" command — `tank unoq diagnostics`
20. [x] AI-generated diagnostic summary — **`tank unoq doctor`** ✅ NEW

**Test (§1):** intent accuracy measured via `test_ai_supervisor.py` +
`test_terminal_ai_router.py` arbitration / routing cases.

## 2. AI hardware diagnostics — 21–40

21. [ ] Motor-current anomaly detection 🧭 (`robot_doctor` motor temp rule)
22. [ ] Servo-current anomaly detection 🧭
23. [x] Battery-voltage anomaly detection — `robot_doctor` battery critical rule
24. [x] Temperature anomaly detection — CPU/motor/battery temp rules
25. [x] IMU anomaly detection — dropout / rate rules
26. [ ] Encoder anomaly detection 🧭
27. [ ] I²C anomaly detection 🧭
28. [ ] UART anomaly detection 🧭
29. [x] USB-device anomaly detection — `usb_detector` + `esp32_fleet` timeout
30. [x] Network anomaly detection — `robot_doctor` network rules
31. [ ] MCU timing anomaly detection 🧭 (heartbeat staleness exists)
32. [x] Motor response anomaly detection — stall / temp rules
33. [x] Servo response anomaly detection — fault rule
34. [ ] Battery-drain anomaly detection 🧭
35. [ ] Boot-time anomaly detection 🧭
36. [ ] Service-crash prediction 🧭 (crash detection exists in recovery_manager)
37. [ ] Memory-leak detection 🧭
38. [x] CPU-load anomaly detection — 98%+ rule
39. [ ] Storage-health prediction 🧭
40. [x] Overall robot-health score — **`RobotDoctor.health_score`** ✅ NEW

**Test (§2):** `test_robot_doctor.py` — fault injection suite, precision of
subsystem identification asserted per fault.

## 3. Predictive maintenance — 41–60

41. [ ] Motor failure prediction 🧭
42. [ ] Servo failure prediction 🧭
43. [ ] Battery degradation prediction 🧭 (cycles tracked)
44. [ ] Fan failure prediction 🧭
45. [ ] Sensor failure prediction 🧭
46. [ ] MCU failure prediction 🧭
47. [x] USB-device failure prediction — fleet timeout detection
48. [ ] Network failure prediction 🧭
49. [ ] Storage failure prediction 🧭
50. [ ] Connector/intermittent-fault detection 🧭
51. [ ] Motor-bearing degradation indicator 🧭
52. [ ] Servo mechanical resistance detection 🧭
53. [ ] Increasing-current trend detection 🧭
54. [ ] Increasing-temperature trend detection 🧭
55. [ ] Increasing-vibration detection 🧭
56. [ ] Battery internal-resistance estimation 🧭
57. [ ] Remaining useful life estimation 🧭 (runtime estimate exists)
58. [ ] Maintenance priority ranking 🧭
59. [ ] Maintenance schedule generation 🧭
60. [x] Predictive-maintenance dashboard — **`tank unoq doctor`** findings list

## 4. AI motion intelligence — 61–80

61. [ ] Learn motor response characteristics 🧭
62. [ ] Automatic acceleration optimization 🧭
63. [ ] Automatic braking optimization 🧭
64. [ ] Motor dead-zone learning 🧭 (dead-zone compensation exists)
65. [ ] Left/right motor mismatch learning 🧭
66. [ ] Track-slip detection 🧭
67. [ ] Terrain-dependent speed adjustment 🧭
68. [ ] Surface-dependent acceleration 🧭
69. [ ] Turning optimization 🧭 (PID tuning exists)
70. [ ] Smooth-motion optimizer 🧭
71. [ ] Energy-efficient driving mode 🧭
72. [ ] Low-noise driving mode 🧭
73. [ ] Precision-driving mode 🧭
74. [ ] Aggressive-driving mode 🧭
75. [ ] Battery-saving navigation commands 🧭
76. [x] Motor thermal-aware speed limiting — doctor temp finding → recommendation
77. [ ] Load estimation 🧭
78. [ ] Payload estimation 🧭
79. [ ] Motion-quality score 🧭
80. [ ] Adaptive motor controller 🧭

## 5. Sensor intelligence — 81–100

81. [ ] Automatic sensor calibration recommendation 🧭
82. [ ] Sensor confidence estimation 🧭
83. [ ] Sensor drift detection 🧭
84. [ ] Sensor noise classification 🧭
85. [ ] Sensor dropout prediction 🧭 (dropout detection exists)
86. [ ] Sensor disagreement detection 🧭
87. [ ] Automatic sensor weighting 🧭
88. [ ] Sensor-fusion confidence 🧭
89. [ ] Sensor replacement detection 🧭
90. [ ] Sensor recovery prediction 🧭
91. [ ] IMU drift estimation 🧭
92. [ ] Encoder drift estimation 🧭
93. [ ] Battery-sensor drift detection 🧭
94. [x] Temperature-sensor plausibility checking — doctor temp rules
95. [x] Impossible-value detection — doctor critical thresholds
96. [ ] Sensor-corruption detection 🧭
97. [ ] Sensor temporal-consistency checking 🧭
98. [ ] Cross-sensor consistency checking 🧭
99. [x] Automatic degraded-mode selection — safety degraded mode + doctor warn
100. [x] AI-generated sensor diagnostics — **`tank unoq doctor`** ✅

## 6. Network AI — 101–115

101. [ ] Wi-Fi quality prediction 🧭
102. [ ] Packet-loss prediction 🧭
103. [ ] Jetson-link failure prediction 🧭
104. [x] ESP32-link failure prediction — fleet timeout detection
105. [ ] Tailscale connectivity prediction 🧭
106. [ ] Network congestion detection 🧭
107. [ ] Latency anomaly detection 🧭
108. [ ] Automatic telemetry-rate optimization 🧭
109. [ ] Automatic video-quality reduction 🧭
110. [ ] Intelligent reconnection strategy 🧭
111. [ ] Best-interface selection 🧭
112. [x] Network-health score — doctor network rules
113. [ ] Remote-control latency prediction 🧭
114. [ ] Network failure explanation 🧭
115. [ ] Network optimization advisor 🧭

## 7. AI power management — 116–130

116. [x] Battery-runtime prediction — power_manager runtime estimate
117. [ ] Power-consumption forecasting 🧭
118. [ ] Motor-energy prediction 🧭
119. [ ] Servo-energy prediction 🧭
120. [ ] Display-energy prediction 🧭
121. [ ] Network-energy prediction 🧭
122. [ ] CPU-energy optimization 🧭
123. [x] Idle-mode optimization — power_manager idle modes
124. [ ] Automatic display brightness optimization 🧭
125. [ ] AI workload power scheduling 🧭
126. [x] Low-battery workload reduction — battery-critical rules
127. [x] Battery-drain anomaly detection — doctor battery rules
128. [ ] Runtime-aware mission scheduling 🧭
129. [ ] Power-budget manager 🧭
130. [x] Intelligent power dashboard — `tank unoq power`

## 8. AI security — 131–145

131. [ ] Abnormal command detection 🧭 (safety gate exists)
132. [ ] Repeated-command detection 🧭
133. [ ] Command-flood detection 🧭
134. [ ] Unauthorized-device detection 🧭
135. [x] Unknown USB-device detection — `usb_detector` inventory
136. [ ] Suspicious network behavior detection 🧭
137. [ ] SSH anomaly detection 🧭
138. [ ] API abuse detection 🧭 (rate limiting exists)
139. [ ] Invalid-command classification 🧭
140. [ ] Command replay detection 🧭 (protocol seq numbers exist)
141. [x] Impossible-motion command detection — supervisor + safety
142. [x] Safety-policy violation detection — `CommandSafety` classifier
143. [ ] AI-assisted permission checking 🧭
144. [ ] Security-risk score 🧭
145. [ ] Security-event explanation 🧭

## 9. AI orchestration — 146–150 ✅ (new `ai_supervisor.py`)

146. [x] Local AI workload scheduler — supervisor arbitration loop
147. [x] AI model resource manager — `local_llm_provider` + `ai_manager`
148. [x] Automatic model selection — GGUF discovery (smallest-first)
149. [x] **AI confidence arbitration** — `AISupervisor.arbitrate()` ✅ NEW
150. [x] **UNO Q autonomous AI supervisor** — `AISupervisor` + `RobotDoctor` ✅ NEW

```
UNO Q AI SUPERVISOR
        │
   ┌────┼────┐
   ↓    ↓    ↓
Hardware AI  Command AI  Network AI
   │    │    │
   └────┼────┘
        ↓
   SAFETY CHECK   ← AISupervisor.arbitrate() + CommandSafety
        ↓
   STM32 CONTROL
```

Example confidence board (implemented in `tank unoq supervisor`):

| Source | Confidence | Role |
|--------|-----------:|------|
| Jetson command | 0.94 | AI |
| Manual controller | 0.99 | MANUAL |
| Local command parser | 0.87 | AI |
| Hardware safety | 1.00 | SAFETY (veto) |
| Battery prediction | 0.91 | AI |

---

## How to prove every completed feature

Fill [`FEATURE_PROOF_TEMPLATE.md`](FEATURE_PROOF_TEMPLATE.md) — including the
**fault-injection acceptance test**: deliberately inject 20–30 known faults,
then measure whether the diagnostic AI identifies the *correct* subsystem
rather than merely producing plausible text.
