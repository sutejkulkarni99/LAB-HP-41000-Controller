# LAB-HP 41000 DC Source Controller & Simulator

A professional PyQt6 application for controlling and logging data from the **ETPS LAB-HP 41000** highâ€‘power DC source (4 kW, 1000 V, 7 A) over LAN. The project includes a full GUI for remote control, data logging, plotting, and a builtâ€‘in **device simulator** for testing without hardware.

## Features

### Main Controller GUI (latest version)
- **LAN Connection** with editable IP, network scanner, and port configuration.
- **Setpoints** for voltage, current, power, and OVP with perâ€‘setpoint reset buttons.
- **Output Control** with safety confirmation and verified state readback.
- **Realâ€‘time Measurements** using background threads (voltage, current, power).
- **Data Logging** â€“ CSV logging with pause/resume, stopâ€‘timestamp filenames, and automatic temp file cleanup.
- **Plotting** â€“ live plot with configurable appearance (background, grid, labels, legend, title) and save as PNG, PDF, or SVG (current screen or full data log).
- **Status Indicators** â€“ LEDs for remote/local mode, standby, OVP, current/power limits.
- **Emergency Stop** â€“ industrial circular latching button (red/yellow) with keyboard shortcut `Ctrl+E`.
- **Advanced Tab** â€“ command terminal with history, quick commands dropdown, device info, and status decode.

### Simulator GUI
- Emulates the LAB-HP 41000 on TCP port 10001.
- Adjustable setpoints, load resistance, output state, remote/local mode.
- OVP trip simulation, command log, and realâ€‘time measurement computation.

## File Versions
- `labhp_controller_v0.py` â€“ Initial version.
- `labhp_controller_v2.py` â€“ Enhanced with scanner, background threads, logging.
- `labhp_controller_v3.py` â€“ Added plot saving options, appearance settings.
- `labhp_controller_v4.py` â€“ **Latest** (all features, stable, iconâ€‘based UI, industrial Eâ€‘Stop).
- `labhp_simulator.py` â€“ Simulator for testing.

> Note: `v1` is not included (skipped in version numbering).

## Requirements
- Python 3.10 or later
- PyQt6
- matplotlib
- (Optional) psutil for network scanning

Install dependencies:
`pip install PyQt6 matplotlib psutil`

## Usage

### Running the Simulator (for testing)
1. Start the simulator:
   `python labhp_simulator.py`
2. Note the IP address displayed in the simulator window.

### Running the Main Controller
1. Start the controller:
   `python labhp_controller_v4.py`
2. Enter the simulator's IP (or use **Scan** to find it automatically).
3. Click **Connect**. The controller will set the device to remote mode and begin polling (if enabled).

### Logging
- Set a log base name and interval.
- Click **Start Logging**. Data is written to a temporary file.
- Click **Stop Logging** â€“ the file is renamed with the exact stop timestamp (e.g., `labhp_log_20260814_153000.csv`).

### Plot Saving
- Click the save icon in the Logger tab.
- Choose **Current Screen** (saves what you see) or **Full Data Log** (plots all recorded data from the last CSV log).

### Emergency Stop
- Press the large red/yellow button or `Ctrl+E`. Output is turned off and device set to local mode.
- Click the button again to release the latch (output remains off).

## License
This project is licensed under the MIT License â€“ see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- ETPS for the LAB-HP 41000 manual and protocol documentation.
