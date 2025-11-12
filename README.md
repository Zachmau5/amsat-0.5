## Brief Screenshot of what we are playing with
<img width="800" height="470" alt="Tracking GUI" src="https://raw.githubusercontent.com/Zachmau5/amsat-1.0/refs/heads/main/assets/capture.png" />



### Installation Steps
> **Note:** Run all setup commands from the repository root.


1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd <repository_directory>

2. **Create and Activate Virtual Environment:**
   ```bash
   conda env create -f assets/amsat.yml
   conda activate amsat

3. **Run Tracking Software:**
   ```bash
   python3 main_gs232b.py
---
## Antenna Boresight Wizard

A standalone Tkinter-based tool for aligning the Yaesu G-5500DC/GS-232B antenna rotator system before satellite tracking.
#### Note: Checks if hardware is present as well
   ```bash
   python3 src/calibration_wizard.py
   ```
---
### Overview
```mermaid
flowchart LR

  %% States (pages)
  S0["Splash: Calibration Wizard"]
  N0["Step 1: TRUE NORTH (W000 000)"]
  S1["Step 2: DUE SOUTH (W180 000)"]
  STAGE["Stage: Choose park azimuth (Wxxx 000, EL=0)"]
  COMPLETE["Complete: Calibration Complete"]

  EXIT_OK["Exit wizard (ok = True)"]
  EXIT_CANCEL["Exit wizard (ok = False)"]

  %% Splash
  S0 -->|Start| N0
  S0 -->|Cancel| EXIT_CANCEL

  %% North
  N0 -->|"Move (W000 000)"| N0
  N0 -->|"Next ▶"| S1
  N0 -->|"Stop + Restart"| S0

  %% South
  S1 -->|"Move (W180 000)"| S1
  S1 -->|"Next ▶"| STAGE
  S1 -->|"Stop + Restart"| S0

  %% Stage
  STAGE -->|"Move (Wxxx 000)"| STAGE
  STAGE -->|"Back"| S1
  STAGE -->|"Stop + Restart"| S0
  STAGE -->|"Finish ▶"| COMPLETE

  %% Complete
  COMPLETE -->|"Continue"| EXIT_OK
  COMPLETE -->|"Restart Wizard"| S0
  COMPLETE -->|"Cancel"| EXIT_CANCEL
```
---
This tool performs a structured **boresight sequence** independent of the main tracking GUI:
1. **Point to True North:**
   Sends `W000 000` and allows the user to verify azimuth alignment.
2. **Point to Due South:**
   Sends `W180 000` and allows confirmation of travel range.
3. **Full 360° Sweep (Speed-Based):**
   Uses rotation speed commands (`X1`–`X4`) and a continuous clockwise rotation (`R`) to confirm smooth motion and limits.
4. **Stage / Park:**
   Lets the user select a fixed azimuth (0–345° in 15° steps) to park the array before exit.



---
### Usage

Run independently from the repository root:
```bash
python3 calibration_wizard.py
```

---

##  Repository Structure

```
amsat/
├── main_gs232b.py           # Main tracking GUI and
├── calibration_wizard.py    # Standalone GS-232B
├── FILL ME IN WHEN I'VE DECIDED TO CLEAN UP MY MESS...
```


---
```mermaid
---
config:
  layout: dagre
  theme: neutral
  look: classic
---
flowchart TD
    A["Program start"] --> B["Set ground station location"]
    B --> C["Prefetch TLE groups into cache"]
    C --> D["Compute visibility cache"]
    D --> E["Create GUI window and build selector"]
    E --> F["GUI event loop"]
    F --> I["User clicks Run Prediction"] & L["User clicks Quit"]
    I --> N{"Any satellites selected?"}
    N -- No --> N
    N -- Yes --> J["Start prediction, serial, Skyfield and open tracking window"]
    J --> K["Animation frame compute pointing and update"]
    K --> P{"Satellite above horizon?"} & V["User closes tracking window"]
    P -- No --> R["Hold rotator do not move"]
    P -- Yes --> Q{"Change exceeds deadband and interval?"}
    R --> S["Update gauges maps and console"]
    Q -- No --> T["Skip move only update status"]
    Q -- Yes --> U["Send move command and get echo"]
    T --> S
    U --> S
    S --> K
    V --> F
    L --> M["Program exit"]
```



