# Progress log

| STEP | ACTION | DATE TIME |
|---|---|---|
| 1 | Installed WSL 2.9.12.0 and Ubuntu 22.04 on main laptop | 260916/2300 |
| 2 | Decided on all dependency versions (Python 3.13, requirements.txt) | 260930/1100 |
| 3 | Set up the project with the chosen versions; installed successfully | 260930/1122 |
| 4 | Created all directories, started Git and connected to GitHub | 260930/1149 |
| 5 | Downloaded CIC-IDS2017 MachineLearningCSV.zip from UNB. NOTE: changed source from Kaggle to UNB | 260930 |
| 6 | Moved MachineLearningCSV.zip into WSL and unzipped | 260930/2322 |
| 7 | Cleaned and split the dataset: python training/preprocess.py (2,830,743 → 1,825,243 rows; PortScan 158,930 → 1,371) | 261014/0000 |
| 8 | Trained baseline model: python training/train.py (accuracy 99.60%, detection rate 99.13%, FPR ~0.30%) | 261014/0000 |
| 9 | Raspberry Pi 4 first setup. Flashed Raspberry Pi OS Lite 64-bit with Raspberry Pi Imager (17 Oct): hostname ids-pi, SSH on, Wi-Fi blank, Raspberry Pi Connect off. PROBLEM: laptop's built-in SD slot is faulty (caused a "fake storage" warning and card disconnects); fixed by using another reader. Booted the Pi on the home router by Ethernet (setup only, never for attacks); SSH works with ids-pi.local only when the laptop is also on Ethernet (Wi-Fi didn't work). Pi IP 192.168.100.11. Made an SSH key in WSL (ssh-keygen + ssh-copy-id) for password-free login. Read-only check: Debian 13 Trixie 64-bit, Python 3.13.5 (laptop 3.13.15), 3.7 GiB RAM, 24 GB disk free, 43.3°C, never throttled, Java not installed. No USB-to-Ethernet adapter or cooling yet | 261018/0113 |
| 10 | Updated the Pi OS once before installing tools: sudo apt update && sudo apt full-upgrade -y && sudo reboot. 14 packages updated (security/bug fixes: curl, xz-utils, libexpat1, ntfs-3g, camera libraries), no errors, 0 failed services. Still Debian 13.7 Trixie, kernel 6.18.50+rpt-rpi-v8, system Python 3.13.5 (unchanged). DECISION: no more OS updates until experiments finish, so all runs use the same system; the IDS uses its own uv Python + pinned requirements, so OS updates don't change its versions. PROBLEM: first attempt didn't run (missing closing quote in the command) | 261018/0130 |
| 11 | Stopped for the day. Pi is set up, updated and reachable by SSH. Next: step 5, install uv on the Pi, Python 3.13.15 venv, pinned requirements, copy the model and prove it loads; then test CICFlowMeter on the Pi | 261018/0134 |
