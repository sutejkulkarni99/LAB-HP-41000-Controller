# Lab Suite v6 — Modular Multi-Instrument Laboratory Suite

Multi-instrument laboratory control and telemetry platform integrating the ETPS LAB-HP 41000 DC power source (ASCII over TCP port 10001) and Rohde & Schwarz RTB2000 digital storage oscilloscope (SCPI over TCP port 5025) with a PyQt6 GUI and unified session logging producing per-instrument CSVs synchronized to a shared precision session clock.

## Requirements

- Python 3.10+
- PyQt6
- pyqtgraph
- numpy
- matplotlib (fallback rendering and plot export engine)

```bash
pip install PyQt6 pyqtgraph numpy matplotlib
```

## Directory Layout

```
v6/
├── __init__.py                         # Package initialization for v6 laboratory suite
├── main.py                             # v6 Entry point: parses CLI arguments, launches simulators, boots Qt application
├── core/
│   ├── __init__.py                     # Core package exports (SessionClock, InstrumentBase, LoggingSession, WaveformStore)
│   ├── clock.py                        # Precision monotonic and wall clock reference for multi-instrument telemetry
│   ├── session_clock.py                # Session clock alias and backwards-compatible import target
│   ├── instrument_base.py              # Abstract base class defining the unified contract for laboratory instruments
│   ├── session.py                      # Multi-instrument session coordinator managing CSV logging and manifest generation
│   ├── session_manifest.py             # Session manifest data model, serialization, and JSON schema verification
│   └── waveform_store.py               # Waveform trace storage manager saving compressed .npz files and metadata
├── instruments/
│   ├── __init__.py                     # Instrument drivers package
│   ├── labhp_41000/
│   │   ├── __init__.py                 # ETPS LAB-HP 41000 package initialization
│   │   ├── driver.py                   # Raw TCP ASCII socket driver communicating on port 10001
│   │   ├── instrument.py               # InstrumentBase implementation wrapping the LAB-HP 41000 driver
│   │   └── simulator.py                # Standalone multithreaded TCP simulator mimicking LAB-HP 41000 ASCII protocol
│   └── rtb2000/
│       ├── __init__.py                 # Rohde & Schwarz RTB2000 package initialization
│       ├── driver.py                   # Raw TCP SCPI socket driver communicating on port 5025
│       ├── instrument.py               # InstrumentBase implementation wrapping RTB2000 driver with verified setters
│       ├── simulator.py                # Standalone multithreaded TCP simulator mimicking RTB2000 SCPI protocol
│       ├── waveform.py                 # Calibrated WaveformTrace dataclass and container
│       └── math_engine.py              # ScopeMathEngine executing FFT, derivatives, integrals, and filtering on traces
├── workers/
│   ├── __init__.py                     # Background worker threads package
│   ├── telemetry_worker.py             # Generic high-speed background polling thread for InstrumentBase instances
│   ├── logger_worker.py                # Dedicated CSV streaming thread logging instrument metrics under SessionClock
│   ├── scope_capture_worker.py         # Background worker fetching waveform traces and scalar telemetry from scopes
│   ├── scope_worker.py                 # High-speed continuous waveform and measurement acquisition worker
│   └── scanner_worker.py               # Async subnet scanner discovering LAN laboratory instruments via TCP probing
└── ui/
    ├── __init__.py                     # UI components package
    ├── main_window.py                  # Main application window integrating header bar, tabs, and status bar
    ├── styles/
    │   ├── __init__.py                 # Style subsystem initialization and stylesheet loader
    │   ├── tokens.py                   # Design tokens defining palette colors, typography, and layout metrics
    │   ├── dark.py                     # Industrial dark theme stylesheet matching hardware benchtop aesthetic
    │   └── light.py                    # High-contrast light theme stylesheet for brightly lit laboratory benches
    ├── widgets/
    │   ├── __init__.py                 # Custom reusable UI widgets package
    │   ├── connection_chip.py          # Status pill showing connection state dot, endpoint, and real-time RTT latency
    │   ├── metric_card.py              # Visual telemetry readout card with large digital values and status badges
    │   └── estop_button.py             # Industrial latching emergency stop button with twist-to-reset mechanism
    ├── plots/
    │   ├── __init__.py                 # Time-series plotting components package
    │   ├── time_series_plot.py         # Multi-axis rolling telemetry chart with zoom, pan, and cursor readouts
    │   └── export.py                   # Publication-ready figure exporter generating PNG, PDF, and SVG plots
    ├── scope/
    │   ├── __init__.py                 # Scope-specific workspace components package
    │   ├── scope_screen.py             # Graticule CRT-style oscilloscope display canvas for waveform traces
    │   ├── channel_control.py          # Vertical channel analog front-end control panel (scale, offset, coupling)
    │   ├── timebase_control.py         # Horizontal timebase control panel (scale, position, trigger holdoff)
    │   ├── trigger_control.py          # Trigger subsystem control panel (source, mode, slope, level)
    │   ├── math_panel.py               # Math trace configuration panel (FFT, filtering, algebraic operations)
    │   └── softkey_bar.py              # Bottom softkey action bar replicating physical oscilloscope bezel buttons
    └── tabs/
        ├── __init__.py                 # Main tab views package
        ├── psu_tab.py                  # Benchtop control tab for ETPS LAB-HP 41000 DC power supply
        ├── scope_tab.py                # Oscilloscope tab for Rohde & Schwarz RTB2000 digital scope
        ├── session_tab.py              # Unified session logging tab for recording, metadata, and manifest management
        ├── plots_tab.py                # Multi-trace time-series analysis and publication export tab
        ├── soa_tab.py                  # Safe Operating Area (SOA) voltage-current power envelope visualizer tab
        └── terminal_tab.py             # Interactive SCPI and ASCII command terminal for direct bus interrogation
```

## How to Run

### With Hardware Simulators

The `--sim` flag is built into `v6/main.py`. It starts background TCP simulators for both the LAB-HP 41000 on `127.0.0.1:10001` and the RTB2000 on `127.0.0.1:5025`:

```bash
python -m v6.main --sim
```

Simulators can also be run as independent background processes:

```bash
python -m v6.instruments.labhp_41000.simulator 10001
python -m v6.instruments.rtb2000.simulator 5025
```

### Without Simulators (Targeting Physical Instruments)

```bash
python -m v6.main --psu-ip 192.168.1.100 --scope-ip 192.168.1.101
```

## Instrument Connection

- **ETPS LAB-HP 41000**: IP address + TCP port `10001` (ASCII command set)
- **Rohde & Schwarz RTB2000**: IP address + TCP port `5025` (SCPI-1999 command set)

### Header Connection Chips

The header bar contains interactive `ConnectionChip` status widgets for each instrument:
- **Status Dot**: Displays a green dot (`●`) when connected and online, or a red dot (`●`) when disconnected.
- **Endpoint & Latency**: Shows the remote endpoint IP along with live round-trip latency (`RTT` in milliseconds).
- **Interactive Click**: Clicking a connection chip emits a signal allowing rapid navigation or status inspection for that device.

## Session Logging Workflow

1. **Configure Metadata & Instruments**: Open the **Unified Session** tab, enter Operator, Project Name, and Purpose notes. Select target instruments and configure independent polling intervals (e.g. 0.1 s for PSU, 0.2 s for Oscilloscope).
2. **Start Session**: Click **START LOGGING**. The unified `SessionClock` starts at zero (`t=0.0000s`), and dedicated `InstrumentLogger` worker threads stream timestamped telemetry to temporary CSV files.
3. **Session Output**:
   - `labhp_41000.csv`: PSU telemetry (`iso_timestamp`, `epoch_s`, `elapsed_s`, `voltage_v`, `current_a`, `power_w`, `resistance_ohm`).
   - `rtb2000.csv`: Scope scalar telemetry (`iso_timestamp`, `epoch_s`, `elapsed_s`, `ch1_vrms`, `ch1_vpp`, `ch1_freq_hz`, `ch2_vrms`, `ch2_vpp`, `ch2_freq_hz`).
   - `waveforms.csv`: Index of captured oscilloscope waveforms recording `elapsed_s`, `instrument`, `channels`, and relative path to the `.npz` archive.
   - `waveforms/`: Directory containing serialized NumPy waveform archives (`.npz`) with full raw sample vectors and timebase calibration.
   - `manifest.json`: Sealed session manifest recording session duration, user metadata, instrument sample rates, recorded row counts, and output file paths.
4. **Pause & Resume**: Click **PAUSE** to temporarily suspend logging without resetting the elapsed timeline; click **RESUME** to continue logging.
5. **Stop Session**: Click **STOP LOGGING**. Workers flush all pending buffers, close files, rename temporary files to canonical `<short_id>.csv` paths, and write the finalized `manifest.json`.

## Tabs

- **`⚡ Benchtop PSU (LAB-HP)`**: Direct control of voltage setpoints, current limits, power limits, OVP thresholds, operating modes (UI/UIR), output enabling, and live telemetry cards.
- **`🌊 Oscilloscope (RTB2000)`**: Oscilloscope workspace displaying live waveform traces on a graticule canvas with timebase, channel vertical scale, trigger controls, and cursor readouts.
- **`🗂 Unified Session`**: Multi-instrument experiment recorder configuring run metadata, sample intervals, session clock controls, live row counters, and session sealing.
- **`📈 Multi-Trace Plots`**: Time-series visualization plotting synchronized telemetry from all active instruments on rolling time axes with channel visibility toggles and export tools.
- **`🛡 Safe Operating Area (SOA)`**: Live voltage versus current power boundary visualizer displaying the active operating point relative to LAB-HP 41000 hardware limits.
- **`💻 SCPI / ASCII Terminal`**: Interactive command console for transmitting raw SCPI and ASCII commands directly to connected instruments and inspecting bus responses.

## Verified SCPI Commands for RTB2000

The driver (`v6/instruments/rtb2000/driver.py`) implements the following verified SCPI commands:

### Identity & System
- `*IDN?` — Instrument identification query
- `*RST` — Reset instrument to factory defaults
- `*CLS` — Clear status registers and error queue
- `*OPC?` — Operation complete query synchronization

### Run & Acquisition Control
- `:RUN` — Start continuous acquisition
- `:STOP` — Stop acquisition
- `:SINGle` — Arm single acquisition sequence
- `:FORMat:DATA ASCii` — Set waveform data format to ASCII

### Horizontal Timebase
- `:TIMebase:SCALe <val>` / `:TIMebase:SCALe?` — Set/query horizontal timebase scale (s/div)
- `:TIMebase:POSition <val>` / `:TIMebase:POSition?` — Set/query horizontal trigger delay offset (s)

### Vertical Channels (1..4)
- `:CHANnel<n>:STATe <0|1>` / `:CHANnel<n>:STATe?` — Enable or disable channel display
- `:CHANnel<n>:SCALe <val>` / `:CHANnel<n>:SCALe?` — Set/query vertical deflection scale (V/div)
- `:CHANnel<n>:POSition <val>` / `:CHANnel<n>:POSition?` — Set/query vertical ground position (divisions)
- `:CHANnel<n>:COUPling <DC|AC|GND>` / `:CHANnel<n>:COUPling?` — Set/query input coupling
- `:CHANnel<n>:PROBe <ratio>` / `:CHANnel<n>:PROBe?` — Set/query probe attenuation factor

### Trigger Subsystem
- `:TRIGger:A:SOURce <source>` / `:TRIGger:A:SOURce?` — Set/query trigger source channel (e.g. `CH1`, `CH2`)
- `:TRIGger:A:LEVel <val>` / `:TRIGger:A:LEVel?` — Set/query trigger voltage threshold level (V)
- `:TRIGger:A:EDGE:SLOPe <POS|NEG>` / `:TRIGger:A:EDGE:SLOPe?` — Set/query edge trigger slope
- `:TRIGger:A:MODE <AUTO|NORM>` / `:TRIGger:A:MODE?` — Set/query trigger mode

### Automated Measurements (Slots 1..4)
- `:MEASurement<n>:SOURce CH<ch>` — Assign channel source to measurement slot
- `:MEASurement<n>:MAIN <param>` — Configure measurement parameter (`UPEakvalue`, `RMS`, `MEAN`, `FREQuency`, `PERiod`, `RTIMe`, `FTIMe`, `PDCYcle`, `PEAK`)
- `:MEASurement<n>:ENABle ON` — Enable measurement slot
- `:MEASurement<n>:RESult?` — Query scalar measurement value

### Waveform Transfer
- `:CHANnel<n>:DATA:HEADer?` — Query waveform header parameters (xstart, xstop, count, xincrement, xorigin, yincrement, yorigin)
- `:CHANnel<n>:DATA:YINCrement?` — Query vertical scaling step size
- `:CHANnel<n>:DATA:YORigin?` — Query vertical ground level origin reference
- `:CHANnel<n>:DATA?` — Query raw waveform sample data string

## Known Limitations

- **ASCII Waveform Transfer**: Waveform acquisition currently requests ASCII transfer (`:FORMat:DATA ASCii`); high-speed IEEE 488.2 binary block transfer is not yet implemented.
- **Fixed Measurement Slots**: Hardware measurement slots are limited to 4 concurrent measurement parameters allocated dynamically.
- **Synthetic Simulator Signals**: Included simulators generate synthetic test waveforms (50 Hz sine and square waves) and simulated load curves; hardware timing nuances may vary on physical instruments.
- **Independent Tree**: `v6/` operates as an independent multi-instrument suite and does not modify the legacy `v5/` single-PSU codebase.

## License & Acknowledgements

- **License**: MIT License
- **ETPS Ltd**: LAB-HP 41000 DC Power Supply communication protocol documentation and programming manual.
- **Rohde & Schwarz**: RTB2000 Series Digital Oscilloscope SCPI Programming Manual.
