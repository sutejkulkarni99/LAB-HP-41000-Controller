"""Comprehensive functional test script verifying all v6 core, drivers, workers, and file pipelines."""
import os
import sys
import time
import json
import shutil
from pathlib import Path

from v6.core.session_clock import SessionClock
from v6.core.waveform_store import WaveformStore
from v6.instruments.labhp_41000.simulator import LABHPSimulator
from v6.instruments.labhp_41000.instrument import LABHPInstrument
from v6.instruments.rtb2000.simulator import RTB2000Simulator
from v6.instruments.rtb2000.instrument import RTB2000Instrument
from v6.instruments.rtb2000.math_engine import ScopeMathEngine
from v6.core.session import LoggingSession
from v6.workers.scanner_worker import ScannerWorker

try:
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)
except Exception:
    app = None


def run_tests():
    print("=" * 70)
    print("STARTING V6 LABORATORY SUITE COMPREHENSIVE SYSTEM TEST")
    print("=" * 70)

    # 1. Boot Hardware Simulators
    print("\n[TEST 1] Booting TCP Hardware Simulators...")
    psu_sim = LABHPSimulator(host="127.0.0.1", port=10001)
    psu_sim.start()
    print("  -> LAB-HP 41000 Simulator listening on 127.0.0.1:10001")

    scope_sim = RTB2000Simulator(host="127.0.0.1", port=5025)
    scope_sim.start()
    print("  -> RTB2000 Simulator listening on 127.0.0.1:5025")
    time.sleep(0.3)

    try:
        # 2. Test Network Scanner Discovery
        print("\n[TEST 2] Testing ScannerWorker device discovery...")
        scanner = ScannerWorker(["127.0.0.1"], ports=[10001, 5025], timeout=0.5)
        found_devices = []
        scanner.device_discovered.connect(lambda ip, port, idn: found_devices.append((ip, port, idn)))
        scanner.run()
        if app:
            app.processEvents()
        print(f"  -> Discovered {len(found_devices)} devices: {found_devices}")
        assert len(found_devices) >= 2, f"Expected at least 2 discovered devices, got {len(found_devices)}"

        # 3. Connect Instrument Drivers
        print("\n[TEST 3] Connecting Instrument Drivers...")
        psu = LABHPInstrument()
        psu.connect("127.0.0.1", 10001)
        assert psu.connected, "PSU should be connected"
        print(f"  -> PSU Connected: ID={psu.idn()}")

        scope = RTB2000Instrument()
        scope.connect("127.0.0.1", 5025)
        assert scope.connected, "Scope should be connected"
        print(f"  -> Scope Connected: ID={scope.idn()}")

        # 4. Test PSU Operations & Telemetry
        print("\n[TEST 4] Testing PSU Controls and Readbacks...")
        psu.driver.set_voltage(48.0)
        psu.driver.set_current(7.5)
        psu.driver.set_output(True)
        time.sleep(0.2)
        meas = psu.poll_measurements()
        print(f"  -> PSU Telemetry: {meas}")
        assert abs(meas["voltage"] - 48.0) < 5.0, "Voltage should track setpoint"
        assert meas["current"] > 0.0, "Current should be flowing into load"
        assert meas["power"] > 0.0, "Power should be > 0"
        st = psu.status()
        print(f"  -> PSU Status: {st}")
        assert st["output_on"] is True, "Output state should be ON"

        # 5. Test RTB2000 State Changing & Re-Query Verification
        print("\n[TEST 5] Testing RTB2000 State-Changing Commands & Re-query logic...")
        # CH1 Scale
        scope.driver.set_channel_scale(1, 0.5)
        sc = scope.driver.get_channel_scale(1)
        print(f"  -> CH1 Scale verified: {sc} V/div (requested 0.5)")
        assert abs(sc - 0.5) < 1e-4

        # Timebase Scale
        scope.driver.set_timebase_scale(0.002)
        tb = scope.driver.get_timebase_scale()
        print(f"  -> Timebase scale verified: {tb} s/div (requested 0.002)")
        assert abs(tb - 0.002) < 1e-5

        # Trigger Level & Source
        scope.driver.set_trigger_source("CH1")
        assert scope.driver.get_trigger_source() == "CH1"
        scope.driver.set_trigger_level(1.25)
        tl = scope.driver.get_trigger_level()
        print(f"  -> Trigger level verified: {tl} V (requested 1.25)")
        assert abs(tl - 1.25) < 1e-4

        # Channel State
        scope.driver.set_channel_state(2, True)
        assert scope.driver.get_channel_state(2) is True
        print("  -> CH2 State verified: ENABLED")

        # 6. Test Waveform Acquisition & WaveformStore
        print("\n[TEST 6] Testing Scope Waveform Acquisition & Compression...")
        wf1 = scope.get_waveform(1)
        assert wf1 is not None, "Waveform trace should not be None"
        print(f"  -> Acquired CH1 Waveform: {len(wf1.x_time)} points, Range: [{min(wf1.y_volts):.2f}, {max(wf1.y_volts):.2f}] V")

        wf2 = scope.get_waveform(2)
        print(f"  -> Acquired CH2 Waveform: {len(wf2.x_time)} points, Range: [{min(wf2.y_volts):.2f}, {max(wf2.y_volts):.2f}] V")

        tmp_wf_file = "/tmp/test_v6_waveform.npz"
        WaveformStore.save(tmp_wf_file, {
            "time": wf1.x_time,
            "ch1": wf1.y_volts,
            "ch2": wf2.y_volts
        }, metadata={"sample_rate": 1e6, "trigger": "CH1"})
        assert os.path.exists(tmp_wf_file)
        loaded_wf = WaveformStore.load(tmp_wf_file)
        print(f"  -> WaveformStore saved & reloaded: channels={list(loaded_wf.keys())}")
        assert "ch1" in loaded_wf and "ch2" in loaded_wf and "time" in loaded_wf

        # 7. Test Scope Math Engine (FFT & Calculations)
        print("\n[TEST 7] Testing Scope Math Engine (FFT & Analysis)...")
        math_eng = ScopeMathEngine()
        fft_freq, fft_mag = math_eng.compute_fft(wf1.x_time, wf1.y_volts)
        print(f"  -> FFT computed: {len(fft_freq)} frequency bins, peak mag={max(fft_mag):.1f} dBV")
        assert len(fft_freq) > 0 and len(fft_mag) > 0

        # 8. Test Unified Session Clock & Multi-Instrument Logger
        print("\n[TEST 8] Testing Unified Session Logger with Shared Clock...")
        clock = SessionClock()
        clock.start()
        test_session_dir = Path("/tmp/test_v6_session")
        if test_session_dir.exists():
            shutil.rmtree(test_session_dir)

        session = LoggingSession(clock=clock)
        session.set_metadata({"operator": "Dr. Smith", "project": "High-Power Switching Test", "purpose": "Validation"})
        # start with (instrument, interval_seconds)
        session.start(
            str(test_session_dir),
            [(psu, 0.05), (scope, 0.05)]
        )

        # Queue a waveform reference
        scope_logger = session.loggers.get("rtb2000")
        if scope_logger:
            scope_logger.queue_waveform(clock.now(), "rtb2000", "CH1", "/tmp/test_v6_session/trace.npz")

        time.sleep(0.35)
        final_csv_paths = session.stop()

        # Check recorded files
        psu_csv = test_session_dir / "labhp_41000.csv"
        scope_csv = test_session_dir / "rtb2000.csv"
        wf_csv = test_session_dir / "waveforms.csv"
        manifest_json = test_session_dir / "manifest.json"

        assert psu_csv.exists(), f"PSU CSV file should exist at {psu_csv}"
        assert scope_csv.exists(), f"Scope CSV file should exist at {scope_csv}"
        assert wf_csv.exists(), f"Waveforms CSV index should exist at {wf_csv}"
        assert manifest_json.exists(), f"Manifest JSON file should exist at {manifest_json}"

        with open(manifest_json, "r") as mf:
            m_data = json.load(mf)
            print(f"  -> Sealed Manifest: {m_data}")
            assert m_data["status"] == "COMPLETED"
            assert m_data["rows_recorded"]["labhp_41000"] >= 3
            assert m_data["rows_recorded"]["rtb2000"] >= 3

        with open(wf_csv, "r") as wf:
            wf_content = wf.read()
            assert "elapsed_s,instrument,channels,npz_path" in wf_content
            assert "trace.npz" in wf_content

        # 9. Clean up
        print("\n[TEST 9] Disconnecting instruments and stopping simulators...")
        psu.disconnect()
        scope.disconnect()
        psu_sim.stop()
        scope_sim.stop()

        # 10. Test UI ModernMetricCard and PSUTab
        print("\n[TEST 10] Testing ModernMetricCard signatures and PSUTab telemetry...")
        from v6.ui.widgets.metric_card import ModernMetricCard
        from v6.ui.tabs.psu_tab import PSUTab

        card1 = ModernMetricCard("OUTPUT VOLTAGE", "0.00", "V", "#38BDF8")
        card2 = ModernMetricCard("OUTPUT CURRENT", "0.0000", "A", "#34D399", parent=None)
        card3 = ModernMetricCard("DELIVERED POWER", "W", "#F472B6")
        card4 = ModernMetricCard("CALCULATED LOAD", "---", "Ω", "#FBBF24")

        card1.set_value("48.00")
        card1.update_setpoint(50.0)
        card1.set_value(48.0)
        card1.set_theme(False)
        assert card1.actual_val == 48.0
        assert card1.setpoint_val == 50.0
        print("  -> ModernMetricCard constructed and verified across all argument signatures")

        tab_psu = PSUTab()
        tab_psu.update_telemetry(1.0, 48.0, 2.5, 120.0, 19.2)
        tab_psu.update_output_state(True)
        tab_psu.update_output_state(False)
        print("  -> PSUTab instantiated and telemetry update executed successfully")

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 70)

    except Exception as e:
        print(f"\nTEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        psu_sim.stop()
        scope_sim.stop()
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
