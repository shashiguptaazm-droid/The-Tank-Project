# 🧾 Feature Proof Template (mandatory)

> Every feature shipped to this repo must be accompanied by proof — fill this
> template in for each completed item of the
> [UNO Q Master Plan](UNOQ_MASTER_PLAN.md). The goal is **measurable hardware
> validation**, not more Python files.
>
> **Rule:** a feature is *done* only when every box below that applies to it is
> ticked. Copy this template, fill it, and link it from the master-plan row.

---

## FEATURE

```
Name:                     <one-line feature name>
Repository files changed: <paths, one per line>
Existing implementation:  <what already existed before this change>
What was upgraded:        <what this change added / replaced / fixed>
Dependencies:             <new or changed dependencies, or "none">
```

## TEST

```
Unit test:        <pytest file::test_name — pass/fail>
Simulation test:  <how it was exercised without hardware, or "n/a">
Hardware test:    <what real hardware it ran on, what was observed>
Failure test:     <what was injected (kill service / disconnect / stall),
                   and the SAFE STATE → EVENT → LOG → RECOVERY trace>
```

## MEASUREMENTS

```
Latency:       <ms — command → response>
CPU:           <% during operation>
RAM:           <MB used>
Power:         <W / V / mA>
Temperature:   <°C>
```

## STATUS

- [ ] Code complete
- [ ] Unit tested
- [ ] Simulated
- [ ] Hardware tested
- [ ] Competition tested

---

## Example — filled-in (ESP32 fleet manager, #281–300)

```
Name:                     ESP32 fleet manager
Repository files changed: tank_os/core/esp32_fleet.py
                          tank_os/cli/unoq_cli.py (tank unoq esp32)
                          tank_os/tests/test_esp32_fleet.py
                          tank_os/tests/test_unoq_cli.py
Existing implementation:  usb_detector.py listed raw USB devices; no identity,
                          heartbeat or health tracking for the 3 ESP32 boards.
What was upgraded:        KNOWN_BOARDS identity registry (3 boards by MAC),
                          discovery via usb_detector serials, heartbeat +
                          timeout detection, telemetry aggregation, fleet
                          self-test, `tank unoq esp32` dashboard.
Dependencies:             none (stdlib + existing tank_os.core.usb_detector)

Unit test:        test_esp32_fleet.py (8 tests) + test_unoq_cli.py (6 tests)
                  — 14/14 pass in the full suite (262 total)
Simulation test:  discovery against a mocked /dev scan; board marked ONLINE
                  when serial matches, OFFLINE after timeout window
Hardware test:    UNO Q — ESP32-S3 CAM (14:C1:9F:C1:2C:24) detected ONLINE
                  1/3 at ttyACM0; heartbeat recorded
Failure test:     unplugged board → status flips OFFLINE → fleet_self_test
                  reports missing board (non-zero exit)

Latency:       <50 ms discover + match
CPU:           <1% (idle poll)
RAM:           ~6 MB
Power:         n/a (software module)
Temperature:   n/a

- [x] Code complete
- [x] Unit tested
- [x] Simulated
- [x] Hardware tested
- [ ] Competition tested
```
