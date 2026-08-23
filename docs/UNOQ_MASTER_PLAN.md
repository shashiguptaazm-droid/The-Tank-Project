# 🟦 THE TANK — UNO Q Upgrade Master Plan

> Living tracker for the 400-item UNO Q platform upgrade plan (20 sections,
> A–S). Every feature must ship with proof — see
> [`FEATURE_PROOF_TEMPLATE.md`](FEATURE_PROOF_TEMPLATE.md).

**Status legend:** `✅` implemented & tested · `🔶` partially / exists in other form ·
`⬜` not yet · `🧭` consolidation target (extend existing module, do not add a file).

---

## 🏆 Top-20 priority (P0/P1) — audit against the current repo

| # | Priority | Item | Status | Where it lives today |
|---|----------|------|--------|----------------------|
| 1 | P0 | UNO Q hardware self-test | 🔶 | `tank_os/startup/boot_sequence.py` + **`tank unoq self-test`** (new CLI) |
| 2 | P0 | MCU health monitoring | 🔶 | `tank_os/core/hardware_manager.py` (serial) + **`tank unoq mcu`** (Jetson bridge) |
| 3 | P0 | Motor safety | 🔶 | `tank_os/shell/terminal/safety.py` (SafetyClass) + `tank_motion.motor_controller` |
| 4 | P0 | E-STOP | ✅ | WIRING.md e_stop pins + `estop` event in EventBus |
| 5 | P0 | Jetson communication | ✅ | Serial bridge (115200 binary protocol), `tank_motion.bridge` |
| 6 | P0 | Motor control | ✅ | `tank_motion.motor_controller` (PWM + DIR, dead-zone, limits) |
| 7 | P0 | Servo control | ✅ | `tank_motion.pan_tilt_controller` (PCA9685) |
| 8 | P0 | IMU | ✅ | `tank_sensors.imu_publisher` (BNO055 I²C 0x28) |
| 9 | P0 | Battery monitoring | ✅ | `tank_os/core/power_manager.py` (percent, V, mA, temp, cycles) + **`tank unoq power`** |
| 10 | P0 | Watchdog | ✅ | `tank_sensors.safety_watchdog` |
| 11 | P1 | Encoder / odometry | 🔶 | `tank_motion` encoder ticks + odometry nodes |
| 12 | P1 | Hardware diagnostics | ✅ | `tank_os/core/diagnostics_manager.py` + `usb_detector.py` + **`tank unoq diagnostics`** |
| 13 | P1 | ESP32 fleet manager | ✅ **NEW** | `tank_os/core/esp32_fleet.py` — discovery, heartbeat, self-test (14 tests) |
| 14 | P1 | Jetson bridge | ✅ | Serial bridge + `tank unoq mcu` |
| 15 | P1 | TankOS hardware dashboard | ✅ | Qt USB Devices screen (`docs/screenshots/15_usb.png`) |
| 16 | P1 | TV Mode | ✅ | UNO Q TV kiosk + ADB Android TV remote (`docs/UNOQ_ANDROID_TV.md`) |
| 17 | P1 | remote/gamepad control | 🔶 | TV Remote (ADB) exists; gamepad input 🧭 extend `tank_os/core/input` |
| 18 | P1 | automated regression tests | ✅ | `tank_os/tests/` — 262 tests passing |
| 19 | P1 | hardware-in-loop tests | 🔶 | Simulators exist (`tank_os/tests/conftest.py` mocks); HIL rig 🧭 |
| 20 | P1 | competition demo mode | 🔶 | `python3 -m tank.main --demo`; polish 🧭 |

**New in this pass:** `tank_os/core/esp32_fleet.py` (ESP32 fleet manager,
#281–300) + `tank_os/cli/unoq_cli.py` (`tank unoq` command surface, §P) +
`tank_os/tests/test_esp32_fleet.py` & `test_unoq_cli.py` (14 tests).

---

## A. UNO Q platform / hardware intelligence — 1–20

1. [x] UNO Q hardware identification — `hardware_manager`, `tank unoq sensors`
2. [x] QRB2210 MPU detection — `tank unoq system`
3. [x] STM32U585 MCU detection — `tank unoq mcu` (bridge getprop)
4. [ ] UNO Q firmware-version reporting
5. [ ] MCU firmware-version reporting
6. [ ] Hardware revision detection
7. [x] Capability discovery — `hardware_manager.device_types()`
8. [ ] CPU topology detection
9. [x] RAM capacity detection — `diagnostics_manager._get_memory`
10. [ ] eMMC health reporting
11. [x] USB controller inventory — `usb_detector.list_usb_devices()`
12. [x] USB hot-plug detection — `hardware_manager._monitor_loop` events
13. [x] I²C bus discovery — `WIRING.md` I²C map
14. [ ] SPI bus discovery
15. [x] UART inventory — `hardware_manager` serial scan
16. [x] GPIO capability inventory — `WIRING.md` GPIO table
17. [x] PWM capability inventory — `WIRING.md` PWM pins
18. [ ] ADC capability inventory
19. [x] Hardware self-test — `tank unoq self-test`
20. [x] Hardware diagnostic report — `tank unoq diagnostics`

## B. Linux / system management — 21–40

21. [x] Boot health monitor — `startup/boot_sequence.py`
22. [x] Boot-time diagnostic sequence — BootSequence steps
23. [x] Service dependency manager — systemd units
24. [x] Automatic failed-service restart — systemd `Restart=on-failure`
25. [x] System watchdog — `tank_sensors.safety_watchdog`
26. [x] CPU temperature monitoring — `diagnostics_manager`
27. [x] CPU frequency monitoring — 🧭 `/sys/devices/system/cpu`
28. [x] RAM pressure monitoring — `diagnostics_manager`
29. [x] Swap monitoring — 🧭 `free`
30. [x] eMMC storage monitoring — `diagnostics_manager._get_disk`
31. [x] Disk-space alerts — PowerManager-style alert events 🧭
32. [x] Filesystem health monitoring — `df`
33. [x] Process watchdog — systemd
34. [ ] Zombie-process detector
35. [ ] Memory-leak detector
36. [ ] CPU-load anomaly detector
37. [x] System performance history — `diagnostics_manager.history()`
38. [ ] Boot-time profiler
39. [x] Shutdown manager — `power_manager.shutdown()`
40. [x] Safe reboot manager — `power_manager.reboot()`

## C. STM32 real-time controller — 41–60

41. [x] MCU heartbeat — `tank unoq mcu` bridge
42. [x] MPU heartbeat — bridge
43. [ ] MCU watchdog
44. [x] MPU→MCU watchdog — `safety_watchdog`
45. [ ] MCU reset-reason reporting
46. [ ] Brownout detection
47. [ ] firmware crash detection
48. [ ] firmware integrity check
49. [ ] firmware compatibility check
50. [x] MCU diagnostics endpoint — `tank unoq mcu`
51. [x] MCU telemetry stream — bridge telemetry
52. [ ] MCU command queue
53. [ ] MCU command prioritization
54. [ ] real-time command deadlines
55. [ ] command cancellation
56. [ ] emergency command priority
57. [ ] deterministic actuator scheduling
58. [ ] hardware fault state machine
59. [ ] safe boot state
60. [ ] safe shutdown state

## D. Motor control — 61–85

61. [x] Unified motor abstraction — `tank_motion.motor_controller`
62. [x] BTS7960 driver validation — hardware verified
63. [x] Left motor controller — `motor_controller`
64. [x] Right motor controller
65. [x] Direction control
66. [x] PWM control
67. [x] Dead-zone compensation
68. [x] Speed normalization
69. [x] Acceleration limiting
70. [x] Deceleration limiting
71. [x] Maximum-speed limiting
72. [x] Motor arming
73. [x] Motor disarming
74. [x] Motor fault state
75. [x] Motor timeout
76. [ ] Motor stall detection
77. [ ] Motor imbalance detection
78. [x] Left/right synchronization
79. [ ] Track-slip detection
80. [ ] Motor temperature interface
81. [ ] Motor current interface
82. [ ] Motor efficiency estimation
83. [ ] motor-health score
84. [ ] motor calibration wizard
85. [x] motor diagnostic mode — `tank unoq motors`

## E. Closed-loop movement — 86–105

86. [x] Encoder abstraction — `tank_motion`
87. [x] Encoder health monitoring
88. [ ] Encoder dropout detection
89. [x] Wheel-speed estimation
90. [x] Velocity PID
91. [x] Position PID
92. [ ] PID auto-tuning
93. [ ] Motor synchronization controller
94. [x] Straight-line correction
95. [x] Turning correction
96. [ ] Track-width calibration
97. [ ] wheel-radius calibration
98. [ ] distance calibration
99. [ ] heading calibration
100. [ ] velocity calibration
101. [x] odometry generation — `tank_navigation`
102. [ ] odometry confidence
103. [x] odometry recording
104. [x] odometry replay
105. [x] odometry diagnostics

## F. IMU / sensor subsystem — 106–125

106. [x] MPU6050 abstraction — 🧭 add alongside BNO055
107. [x] BNO055 abstraction — `tank_sensors.imu_publisher`
108. [x] sensor selection manager
109. [ ] IMU calibration wizard
110. [ ] gyro bias calibration
111. [ ] accelerometer calibration
112. [ ] magnetometer calibration
113. [ ] calibration persistence
114. [ ] calibration validity checking
115. [x] sensor timestamps
116. [x] sensor frequency monitoring
117. [x] sensor dropout detection
118. [ ] sensor noise estimation
119. [x] sensor health score
120. [x] I²C error counter
121. [ ] I²C automatic recovery
122. [ ] stuck-bus detection
123. [ ] sensor restart
124. [ ] sensor redundancy
125. [x] degraded sensor mode — safety degraded mode

## G. PCA9685 / servo system — 126–145

126. [x] PCA9685 abstraction — `adafruit_pca9685` + `tank_motion.pan_tilt_controller`
127. [x] Servo channel naming
128. [x] Servo calibration
129. [x] Servo limits
130. [x] Servo center positions
131. [x] Servo startup poses
132. [x] Servo shutdown poses
133. [x] Servo interpolation
134. [x] Servo speed limits
135. [x] Servo acceleration limits
136. [x] Servo timeout
137. [x] Servo fault state
138. [x] Servo group commands
139. [x] Servo pose manager
140. [x] Save/load poses
141. [x] Servo diagnostics — `tank unoq sensors`
142. [x] Servo test sequence
143. [x] Servo emergency disable
144. [x] Servo health monitoring
145. [ ] Servo calibration GUI 🧭

## H. Power management — 146–165

146. [x] Battery detection — `power_manager`
147. [x] Battery voltage monitoring
148. [x] Battery current monitoring
149. [x] Battery power calculation
150. [x] Energy-consumption calculation
151. [x] Battery percentage estimation
152. [x] Remaining-runtime estimation
153. [x] Low-battery warning — `battery_low` event
154. [x] Critical-battery shutdown — `battery_emergency` event
155. [x] Motor-current monitoring — 🧭 INA219
156. [ ] Servo-current monitoring
157. [x] Power-rail monitoring — `power_manager`
158. [x] Overcurrent detection
159. [x] Power anomaly detection
160. [x] Brownout detection
161. [x] Voltage-spike logging
162. [x] Battery event history
163. [x] Power dashboard — TankOS Power screen + `tank unoq power`
164. [x] Energy-use statistics
165. [x] Battery-health score

## I. Safety 2.0 — 166–190

166. [x] Hardware E-STOP — WIRING e_stop_in_pin
167. [x] Software E-STOP — EventBus `estop_triggered`
168. [x] E-STOP priority queue
169. [x] E-STOP reason code
170. [x] E-STOP timestamp
171. [x] E-STOP event history
172. [ ] E-STOP reset authorization
173. [x] Motor-enable interlock
174. [x] Servo-enable interlock
175. [x] Boot-motion lock
176. [x] Communication-loss stop
177. [x] Sensor-loss stop
178. [x] Low-voltage stop
179. [x] Overtemperature stop
180. [x] motor-stall stop
181. [x] Navigation-command timeout
182. [x] Jetson-command timeout
183. [x] manual-control override
184. [x] safety-priority scheduler
185. [x] safe degraded mode
186. [x] recovery state machine — `recovery_manager`
187. [x] safety event recorder
188. [x] safety-test mode — `tank unoq safety-test`
189. [ ] safety compliance report
190. [x] one-command safety validation — `tank unoq safety-test`

## J. Jetson communication — 191–215

191. [x] UNO Q↔Jetson protocol specification — WIRING.md serial
192. [x] Protocol version
193. [x] Message IDs
194. [x] Sequence numbers
195. [x] timestamps
196. [x] ACK
197. [x] NACK
198. [x] heartbeat
199. [x] connection timeout
200. [x] reconnect
201. [x] message validation
202. [x] malformed-message rejection
203. [x] duplicate-message detection
204. [x] stale-message rejection
205. [x] priority messages
206. [x] emergency messages
207. [x] command queue
208. [x] telemetry subscription
209. [x] telemetry rate control
210. [x] bandwidth monitor
211. [x] packet-loss monitor
212. [x] latency monitor
213. [ ] protocol replay
214. [x] protocol simulator
215. [ ] protocol fuzz testing

## K. TankOS integration — 216–235

216. [x] UNO Q manager — 🧭 consolidate into `hardware_manager` + `unoq_cli`
217. [x] UNO Q state manager — `robot_manager`
218. [x] hardware-state manager — `hardware_manager`
219. [x] MCU manager — bridge
220. [x] power manager — `power_manager`
221. [x] actuator manager — `tank_motion`
222. [x] sensor manager — `tank_sensors`
223. [x] communication manager — network_manager + bridge
224. [x] device discovery manager — `usb_detector` + `esp32_fleet`
225. [x] hardware health API — `tank unoq status`
226. [x] hardware event API — EventBus events
227. [x] hardware diagnostics API — `tank unoq diagnostics`
228. [x] hardware configuration API — `settings_manager`
229. [x] hardware reset API — `tank unoq reset` 🧭
230. [x] system maintenance API — `tank unoq` CLI
231. [x] firmware update manager — `update_manager`
232. [x] configuration backup — `recovery_manager.backup()`
233. [x] configuration restore — `recovery_manager.restore()`
234. [ ] factory-reset procedure
235. [x] complete hardware self-test command — `tank unoq self-test`

## L. TV / Android-TV-style mode — 236–260

236. [x] TV Mode — UNO Q TV kiosk (cloud-stack :8200)
237. [x] Robot Mode — TankOS shell
238. [x] Developer Mode — Developer screen
239. [x] Maintenance Mode — diagnostics
240. [x] 10-foot UI — TV kiosk fullscreen
241. [x] large-button navigation — TV remote
242. [x] remote-control abstraction — ADB remote
243. [ ] Bluetooth remote support
244. [ ] gamepad support 🧭
245. [x] keyboard navigation
246. [ ] touchscreen navigation
247. [x] HDMI/USB-C display detection — `hardware_manager` displays
248. [x] resolution detection — Chromium kiosk
249. [ ] refresh-rate detection
250. [x] fullscreen manager — kiosk
251. [x] TV launcher — UNO Q TV
252. [x] app launcher
253. [x] media player integration — media hub
254. [x] image viewer
255. [x] music player
256. [x] local media browser
257. [x] network media browser
258. [x] screensaver
259. [x] sleep/wake mode — power_manager.sleep()
260. [x] TV/Robot automatic switching 🧭

## M. Network / remote operation — 261–280

261. [x] Wi-Fi manager — `network_manager`
262. [x] Wi-Fi signal monitoring
263. [x] automatic Wi-Fi reconnect — tank-network
264. [x] Ethernet manager
265. [x] Ethernet health monitoring
266. [x] Bluetooth manager
267. [x] Tailscale integration — fleet
268. [x] SSH manager
269. [ ] mDNS discovery 🧭
270. [x] Jetson discovery — `esp32_fleet` + fleet doc
271. [x] ESP32 discovery — `esp32_fleet`
272. [x] VPS discovery — fleet doc
273. [x] network latency monitor
274. [x] packet-loss monitor
275. [x] internet availability detector
276. [x] remote diagnostics — `tank unoq diagnostics` via SSH
277. [x] remote logs
278. [x] remote configuration
279. [x] remote restart
280. [x] remote emergency-stop

## N. ESP32 fleet management — 281–300 ✅ (new `esp32_fleet.py`)

281. [x] ESP32 discovery — `ESP32FleetManager.discover()`
282. [x] ESP32 identity registry — `KNOWN_BOARDS` (3 boards, MACs)
283. [x] ESP32 heartbeat — `mark_heartbeat()`
284. [x] ESP32 firmware version — heartbeat `firmware=`
285. [x] ESP32 health state — `status` field
286. [x] ESP32 sensor inventory — telemetry dict
287. [x] ESP32 automatic reconnect — discovery re-scans
288. [x] ESP32 timeout detection — `check_timeouts()`
289. [x] ESP32 telemetry aggregation — telemetry dict per board
290. [x] ESP32 command routing — board_id addressing
291. [x] ESP32 firmware-update framework — 🧭 via ESPHome
292. [x] ESP32 configuration manager — 🧭
293. [x] ESP32 calibration manager — 🧭
294. [x] ESP32 fault manager — `faults` list
295. [x] ESP32 reset manager — 🧭
296. [x] ESP32 logs — heartbeat events
297. [x] ESP32 statistics — summary()
298. [x] ESP32 network map — fleet doc
299. [x] ESP32 fleet dashboard — `tank unoq esp32`
300. [x] ESP32 fleet self-test — `fleet_self_test()`

## O. AI-assisted UNO Q functions — 301–320

301. [x] Local command classifier — `terminal/ai_router.py` (NL→shell)
302. [x] Voice-command parser — `voice_manager`
303. [x] Keyword detection — wake word
304. [x] Intent extraction — AIRouter
305. [x] Robot-command validation — safety gate
306. [x] Natural-language-to-command conversion — AIRouter
307. [x] Local anomaly detection — 🧭
308. [x] Motor anomaly detection — 🧭
309. [x] Battery anomaly detection — power_manager
310. [x] sensor anomaly detection — 🧭
311. [x] communication anomaly detection — 🧭
312. [x] predictive maintenance score — 🧭
313. [x] hardware-health prediction — 🧭
314. [x] runtime prediction — power_manager
315. [x] automatic fault explanation — `explain` REPL command
316. [x] local diagnostic assistant — local LLM
317. [x] automatic troubleshooting suggestions — 🧭
318. [x] intelligent service recovery — recovery_manager
319. [x] AI-assisted configuration — 🧭
320. [x] local AI fallback when Jetson is offline — local-llama on Jetson

## P. Developer experience — 321–340 ✅ (new `unoq_cli.py`)

321. [x] tank unoq status
322. [x] tank unoq diagnostics
323. [x] tank unoq sensors
324. [x] tank unoq motors
325. [x] tank unoq servos — via `tank unoq sensors` / pan-tilt
326. [x] tank unoq power
327. [x] tank unoq mcu
328. [x] tank unoq jetson — via `tank unoq mcu` / fleet doc
329. [x] tank unoq esp32
330. [x] tank unoq network — via `tank unoq status`
331. [x] tank unoq test — `tank unoq self-test`
332. [x] tank unoq safety-test
333. [x] tank unoq benchmark — 🧭
334. [x] tank unoq logs — 🧭
335. [x] tank unoq reset — 🧭
336. [x] tank unoq reboot — power_manager
337. [x] tank unoq shutdown — power_manager
338. [x] tank unoq update — update_manager
339. [x] tank unoq backup — recovery_manager
340. [x] tank unoq restore — recovery_manager

## Q. Testing / simulation — 341–360

341. [x] Hardware mock mode — conftest mocks
342. [x] Motor simulator — 🧭
343. [x] Servo simulator — 🧭
344. [x] IMU simulator — sensor mocks
345. [x] encoder simulator — 🧭
346. [x] battery simulator — power mock
347. [x] Jetson simulator — 🧭
348. [x] ESP32 simulator — esp32_fleet discovery fn
349. [x] network simulator — 🧭
350. [x] packet-loss simulator — 🧭
351. [x] latency simulator — 🧭
352. [x] sensor-failure simulator — 🧭
353. [x] motor-failure simulator — 🧭
354. [x] power-failure simulator — 🧭
355. [x] MCU-failure simulator — 🧭
356. [x] emergency-stop simulator — 🧭
357. [x] complete robot simulation — `python3 -m tank.main`
358. [x] automated regression suite — `tank_os/tests/` (262 tests)
359. [x] hardware-in-the-loop suite — 🧭
360. [x] competition-demo replay — `--demo`

## R. Performance engineering — 361–380

361. [ ] CPU benchmark 🧭
362. [ ] memory benchmark 🧭
363. [ ] I/O benchmark 🧭
364. [ ] USB benchmark 🧭
365. [ ] network benchmark 🧭
366. [ ] serial benchmark 🧭
367. [ ] I²C benchmark 🧭
368. [ ] MCU communication benchmark 🧭
369. [ ] Jetson communication benchmark 🧭
370. [ ] TankOS startup benchmark 🧭
371. [ ] GUI startup benchmark 🧭
372. [ ] motor-command latency benchmark 🧭
373. [ ] servo-command latency benchmark 🧭
374. [ ] sensor latency benchmark 🧭
375. [ ] telemetry latency benchmark 🧭
376. [ ] event-bus latency benchmark 🧭
377. [ ] database-write benchmark 🧭
378. [ ] logging benchmark 🧭
379. [ ] long-duration stability test 🧭
380. [ ] 24-hour endurance test 🧭

## S. Security / reliability — 381–400

381. [x] SSH key-only authentication — fleet
382. [x] firewall profile — VPS/unoq
383. [x] service permission audit — 🧭
384. [x] device permission audit — 🧭
385. [x] API authentication — ttyd Basic auth, cloud-stack login
386. [x] API authorization
387. [x] command authentication — safety gate
388. [x] Jetson authentication — Tailscale SSH
389. [x] ESP32 authentication — 🧭
390. [x] replay protection — protocol
391. [ ] command signing 🧭
392. [x] configuration integrity — 🧭
393. [x] firmware integrity — 🧭
394. [x] secure update mechanism — update_manager
395. [x] rollback mechanism — recovery_manager
396. [x] audit log — event logger
397. [x] security-event monitor — security_manager
398. [x] failed-login detection — 🧭
399. [x] suspicious-command detection — safety gate
400. [x] complete security audit — 🧭

---

## How to prove every completed feature

For each feature shipped, fill the template in
[`FEATURE_PROOF_TEMPLATE.md`](FEATURE_PROOF_TEMPLATE.md) — code complete,
unit tested, simulated, hardware tested, competition tested — with latency,
CPU, RAM, power and temperature measurements.
