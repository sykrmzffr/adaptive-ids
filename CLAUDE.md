# Project context: Adaptive Threshold IDS on Raspberry Pi (UiTM FYP)

This file is read automatically by Claude Code. Keep it updated as decisions are made.

## Who I am and how to work with me

- Student: Syakir Muzaffar, Bachelor of Computer Science (Hons.) Netcentric Computing, UiTM. Supervisor: Dr Siti Rahayu binti Abdul Aziz.
- Final Year Project. The proposal/report (CSP600) is done; I'm now building and evaluating the system. **Deadline: about 5-8 weeks from 17 Oct 2026 for the COMPLETE project** (working system, experiments, final report chapters).
- **I have limited technical background.** Use plain language and short analogies. Avoid jargon, or explain it in one line when you must use it.
- **I'm short on time, so I'm building first and studying deeply later.** For every step, still give me a 2-line "What it does / Why" that I can paste into my decisions log. Keep it brief.
- **No hallucination.** If you don't know or haven't verified something, say so. Label anything that is your own design choice, assumption or estimate (e.g. "my suggestion", "my estimate"). Verify facts (versions, tool behaviour, dataset details) before stating them. Saying "I don't know" is allowed.
- Ask before running anything destructive (deleting files, changing iptables/network settings, force-pushing git). Explain what a command does before running anything on the Raspberry Pi's network config.
- I must be able to explain this work in a viva. Don't silently add features or files: tell me what you added and why.
- AI assistance must be declared to my supervisor (still to confirm UiTM policy). Code written by AI should be marked as such in my notes.

## The project in 30 seconds

The Raspberry Pi 4 sits between devices as a network gateway. It captures traffic, groups packets into flows (conversations), measures each flow (features), and a Random Forest gives each flow a score P(attack) from 0 to 1. A threshold decides when to alert. **Contribution:** an adaptive threshold based on EMA (exponential moving average) of recent scores, `threshold = baseline_mean + k * baseline_std`, recalculated every 5 minutes after a 10-minute learning window. The goal is to show fewer false positives than a fixed threshold under heavy normal traffic, while keeping the detection rate at or above 95% for TCP SYN flood, ICMP flood and port scan (hping3, nmap). Extras: SQLite logging, a Flask dashboard (live alerts, traffic log, system status, blocked IPs), and optional IP auto-block via iptables for 15 minutes.

Report evaluation targets (Table 3.10): detection rate ≥95% per attack; FPR(adaptive) < FPR(fixed) under heavy normal traffic; peak CPU <80%; average latency <100 ms per window.

## Environment (done)

- Windows laptop with WSL2 Ubuntu-22.04. Project at `~/adaptive-ids` (inside WSL, NOT on C:).
- Python 3.13 via `uv`, virtual env at `.venv` (`source .venv/bin/activate`). Chosen because current Raspberry Pi OS (Debian 13 "Trixie") uses Python 3.13; laptop and Pi should match.
- `requirements.txt` (pinned, tested on 3.13, ARM64 wheels confirmed): numpy 2.2.6, pandas 2.2.3, scikit-learn 1.6.1, imbalanced-learn 0.13.0, joblib 1.4.2, scapy 2.6.1, flask 3.1.0, psutil 6.1.1, matplotlib 3.10.0, pytest 8.3.4. **scikit-learn must be the same version on laptop and Pi**, or the saved model may not load.
- Private GitHub repo; `.gitignore` excludes `.venv/ data/ __pycache__/ *.pyc *.joblib *.pcap *.db`.
- **I now have the Raspberry Pi 4 (not yet set up).**

## Pi setup progress (17 Oct 2026)

Decided (my choice, on Claude's suggestion):
- **Raspberry Pi OS Lite (64-bit)**, no desktop: more CPU/RAM left for the IDS. Still counts as "Raspberry Pi OS 64-bit" (Table 3.4).
- Imager OS customisation: hostname `ids-pi`, my own user/password, time zone `Asia/Kuala_Lumpur`, **SSH on (password login for now)**, **Wi-Fi blank**, **Raspberry Pi Connect OFF** (extra service = CPU/RAM noise in measurements + outside traffic in captures; SSH is enough; can install later).
- First boot plan: Ethernet to home router **for setup/updates only, never for attacks**.

Update: **cause found: the laptop's built-in SD slot is faulty.** Use a different reader from now on. No need to format before flashing (Imager overwrites the whole card; if needed, use Imager's "Erase" option = FAT32). If Imager's write + verify passes in the working reader, the card is very likely fine (H2testw only needed if problems return).

Earlier status (kept for the record): **BLOCKED on the microSD card.**
- During Imager write, Windows asked to format the card; I quick-formatted it (this wiped the write; not harmful). Lesson: **after flashing, always click Cancel on Windows' "format disk" prompt.**
- On rewrite, Imager warned the storage is "fake" (exact wording not recorded), then the card stopped being detected. The laptop's built-in slot was already unreliable (needed reinserting).
- Unknown cause: loose laptop slot vs counterfeit/failing card.
- Next: (A) try the card in a different reader (USB reader / other laptop / phone). (B) if detected, run **H2testw** to check real capacity. If it fails, or was bought cheaply from an unknown seller, buy a genuine card (SanDisk/Samsung/Kingston, official store) + a USB card reader.
- 17 Oct: **flashed successfully** (verify passed). **No USB-to-Ethernet adapter yet** (needed by testbed step 7; buy soon). **No heatsink/fan, plain case only**: Pi 4 throttles when hot, which would distort CPU/latency results. Buy cooling before experiments; log temperature/throttling meanwhile.

Step 1 plan: ~~flash~~ → ~~first boot + SSH~~ (done 18 Oct) → ~~OS update~~ (done 18 Oct: 14 packages, Debian 13.7, kernel 6.18.50+rpt-rpi-v8; **OS frozen: no more updates until experiments finish**) → **uv (NEXT)**, venv, requirements (my suggestion: uv Python 3.13.15 to match laptop), copy model, prove it loads → **CICFlowMeter test on ARM64** (Java not installed yet).

Pi access (18 Oct): user `syakir`, IP **192.168.100.11** on home router (DHCP, may change; re-check with `ping ids-pi.local` in Windows PowerShell). WSL can't resolve `.local` but reaches the IP. Laptop must be on Ethernet (Wi-Fi couldn't reach the Pi). Password-free SSH from WSL with `~/.ssh/id_ed25519` (no passphrase); host key verified against Windows known_hosts. **sudo needs my password**, so admin commands are run by me in the Ubuntu terminal (`ssh -t ...`), not via `!`.
Pi state: Debian 13 Trixie aarch64, Python 3.13.5, 3.7 GiB RAM, 24 GB free, 43.3°C, throttled=0x0.

Why the OS update doesn't break report versions (decided 18 Oct): Table 3.4 names no OS version; we stay on Debian 13; the IDS runs in its own uv Python + pinned requirements, which apt doesn't touch. Report the ACTUAL versions in Chapter 4.
Lesson: copy-paste long commands instead of typing them (a missing closing `'` makes bash show `>` and wait; press Ctrl+C).

Next session, start here (step 5, no network changes):
1. Pi on home router by Ethernet, laptop on Ethernet; check IP with `ping ids-pi.local` in PowerShell (was 192.168.100.11).
2. Claude installs uv on the Pi (official astral.sh installer, user folder, no sudo; shows the commands first).
3. `.venv` with Python 3.13.15, install pinned `requirements.txt`, copy `models/rf_model.joblib` + `model_meta.json`, prove the model loads and time a batch prediction.
4. Then the CICFlowMeter on ARM64 test (install Java first; needs sudo, so I run it in the Ubuntu terminal).

Shopping list: USB 3.0 Gigabit USB-to-Ethernet adapter (Realtek RTL8153 chip suggested by Claude, not yet tested on this Pi); heatsink kit or fan case.

## Folder layout

```
adaptive-ids/
├─ data/MachineLearningCVE/   CIC-IDS2017 MachineLearningCSV (8 CSVs, from UNB) + processed.npz + preprocess_report.json
├─ models/                    rf_model.joblib (not in git, 22.6 MB) + model_meta.json
├─ training/preprocess.py     (AI-written) clean + 80/20 stratified split, no SMOTE here
├─ training/train.py          (AI-written) CV with SMOTE inside imblearn Pipeline, final fit, metrics, plots, save
├─ ids/ema.py                 (AI-written) AdaptiveThreshold class, fixed + adaptive modes
├─ ids/schema.sql             (AI-written) SQLite schema: traffic_log, alerts, blocked_ips (WAL mode)
├─ ids/ (other files)         placeholders: main, capture, features, detector, blocker, db - NOT written yet
├─ dashboard/                 placeholder - NOT written yet
├─ docs/                      CSP600 report PDF + progress-log.md (STEP | ACTION | DATE TIME)
├─ tests/test_ema.py          (AI-written) 12 pytest tests, all pass
└─ eval/offline/              metrics.json + confusion_matrix / feature_importance / roc / pr / score_histogram PNGs
```

## Results so far (real data)

**Preprocessing** (11 features, binary BENIGN=0 / ATTACK=1):
- Loaded 2,830,743 rows. Dropped: inf/NaN 2,867; negative 115; exact duplicates 998,852; same-features-different-label 3,666. Final 1,825,243 (BENIGN 1,500,825). Train 1,460,194 / test 365,049.
- **PortScan collapsed from 158,930 to 1,371 rows** after dedup: scan flows are identical on these 11 features because Destination Port isn't a feature.

**11 features** (exact CIC-IDS2017 column names): Flow Duration (microseconds), Total Fwd Packets, Total Backward Packets, Total Length of Fwd Packets, Total Length of Bwd Packets, Fwd Packet Length Mean, Bwd Packet Length Mean, Flow Packets/s, Flow Bytes/s, SYN Flag Count, RST Flag Count. The report's 12th feature, "Destination Port Entropy", does NOT exist in CICFlowMeter or CIC-IDS2017.

**Baseline Random Forest** (100 trees, gini, max_depth None, seed 42):
- 5-fold CV on a 300k subsample: test accuracy 99.54% ± 0.02%, train 99.998%.
- SMOTE 1,460,194 → 2,401,320 rows; fit 162 s on laptop.
- Held-out test: accuracy 99.60%, ATTACK precision 98.61%, detection rate (recall) 99.13%, BENIGN recall 99.70% (FPR ≈ 0.30%).
- Model 22.6 MB; 4.01 ms per single flow on laptop. Reproducible: identical numbers on a second run.
- Measured earlier on test hardware: with `n_jobs=-1`, single-flow prediction is about 5x slower than `n_jobs=1`, and batching 200 flows in one call costs about the same as one flow. **On the Pi: score each window's flows in one batched call with n_jobs=1** (train.py already saves with n_jobs=1).
- Not yet checked: per-attack-type detection (especially PortScan, only ~274 test rows), score histogram, feature importance.

## ema.py design (deviations from the report are deliberate; tell my supervisor)

- Report equations implemented exactly: `mean_new = β*score + (1-β)*mean_old`; `std_new = sqrt(β*(score-mean_new)² + (1-β)*std_old²)`; threshold recalculated every 300 s; 600 s learning window with no alerts; each score is compared against the ACTIVE threshold.
- (A) `update_on_alert=False`: the baseline does not learn from windows that alerted, otherwise a sustained flood raises its own threshold (a test demonstrates this).
- (B) `floor`/`ceiling` clamp (defaults 0.5 / 0.95, unvalidated; choose from the score histogram).
- (C) `min_std`: the report's std update collapses on smooth traffic (std about 0.005 → 0.0005 within 5 min in tests), so the threshold hugs the mean and slow legitimate rises cause false alerts. `min_std` (e.g. 0.02, arbitrary) prevents this.
- **Risk for the main experiment:** if benign scores stay near 0, the adaptive threshold sits on the floor and behaves the same as fixed. Must check early whether heavy normal traffic raises benign scores at all.
- Plan: run fixed and adaptive at the same time on the same window scores (paired comparison), and log all raw scores so k/β/floor can be replayed offline.

## Decisions

Decided by me:
- **Option A** (pending supervisor approval): tcpdump captures → CICFlowMeter extracts features → Python scores. Reason: same extraction tool as the dataset (training/deployment consistency, report §3.3.2). The report's §3.5.5 mentions scapy computing features; that is to be fixed.
- Known concern with Option A: CICFlowMeter writes a flow only when it ends (FIN/RST or timeout; default flow timeout 120 s, activity timeout 5 s, per Engelen et al. 2021 instructions). hping3 floods create many 1-packet flows that never close, so alerts may be delayed. Plan: measure the delay. Shortening the timeout reduces consistency with the training data.
- CICFlowMeter (Java, jnetpcap native library) has NOT been tested on the Pi's ARM64 OS. Unknown whether it runs. **Check this first, now that the Pi is here.**

Waiting on supervisor (meeting not yet held):
1. Option A approval (CICFlowMeter on Pi)
2. Feature 12: drop it (11 features) or compute entropy separately
3. PortScan collapse: add `Destination Port` as a feature / another feature / accept as a limitation
4. No ICMP flood class in CIC-IDS2017 (verified on UNB page): treat as a generalisation test, or add own captured ICMP flood data
5. Binary vs multi-class (dashboard/schema show attack_class; binary can't fill it)
6. Python 3.10 → 3.13 in Tables 3.5/3.8
7. EMA std-collapse finding
8. AI-use declaration / UiTM policy

## Report errors to fix later

- §3.3.3: Tekin et al. 624.43 s is TRAINING time, not inference.
- §3.5.5 vs Table 3.5: scapy vs CICFlowMeter for feature extraction.
- Table 3.7: feature 12 doesn't exist; add exact dataset column names.
- Tables 3.5 / 3.8: Python and library versions.
- §3.5.1.3: says two DB tables; §3.4.7 has three.
- Table 3.4: second NIC should be a USB-to-Ethernet adapter, not USB Wi-Fi.
- §3.5.7: iptables blocking must include the FORWARD chain (gateway traffic), not only INPUT.
- §3.5.1.1: says 64-bit is needed to "address more than 4 GB of memory", but the Pi has only 4 GB. Better reason: 64-bit gives each process its full address space and matches the ARM64 Python wheels we confirmed.

## Testbed plan (matches report Figure 3.3)

- Attacker / test laptop → Pi second NIC (e.g. eth1, 192.168.50.0/24, Pi 192.168.50.1, attacker .20, my suggested addresses) → Pi eth0 → SEPARATE router or phone hotspot (not home/hostel network) → target machine.
- Capture on the attacker-facing interface (pre-NAT source IPs).
- Never put attacker and target on the same switch, or traffic bypasses the Pi.
- Recent Raspberry Pi OS uses NetworkManager (`nmcli`); old `dhcpcd.conf` guides don't apply. Verify on the device.
- Cooling matters: log `vcgencmd measure_temp` and `vcgencmd get_throttled` with CPU stats.
- Attack only on the isolated testbed; tell the supervisor.

## Remaining work (rough order; time estimates are my guess)

1. Pi setup (Raspberry Pi OS 64-bit, SSH, Python 3.13 venv, requirements, copy model, prove it loads) + **CICFlowMeter feasibility on the Pi**.
2. Supervisor meeting → apply decisions (may mean re-running preprocess + train).
3. Feature pipeline (tcpdump + CICFlowMeter → feature vectors in model_meta.json order) + validate against the dataset definitions.
4. detector.py (version check, batch predict) + main.py 5-second loop (per-source-IP window score = max flow score; both thresholds in parallel; latency_ms).
5. db.py (WAL, `foreign_keys=ON` per connection, single writer) + Flask dashboard (4 pages, JSON endpoints, 5 s polling).
6. blocker.py (iptables FORWARD + INPUT, never-block list, 15-min expiry, subprocess with list args).
7. Gateway testbed + systemd service.
8. Early check: does heavy normal traffic raise benign scores? (decides whether the main comparison can show a difference)
9. Experiments: steady / heavy / mixed scenarios × 3 repeats, ground-truth logging, tcpdump drop counts, CPU/RAM/temperature, latency → fill Table 3.10.
10. Chapters 4 and 5, viva prep.

## Saved for later (don't start unless I ask)

Build a full syllabus + teaching website covering all theory, comparisons and related projects for this FYP. Strictly sourced, no hallucination, plain language, self-check questions.

## Progress log rule (always)
- Progress log: after every completed step (and before I quit), append a row to docs/progress-log.md. Use the same format as my Word log: a table with columns STEP | ACTION | DATE TIME, where DATE TIME is YYMMDD/HHMM in Malaysia time (get it with TZ=Asia/Kuala_Lumpur date +%y%m%d/%H%M, never guess). ACTION should say what was done, the key command or result, and any important decision or problem in plain language. Never write passwords or secrets in the log.

## Git rule (always)
- Never add yourself (Claude/AI) as an author, co-author or contributor. No "Co-Authored-By: Claude" trailer and no "Generated with Claude Code" line in any commit, pull request or push. Commits go under my own name and my GitHub noreply email only.
