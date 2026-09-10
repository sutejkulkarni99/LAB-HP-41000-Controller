"""LABHPInstrument — InstrumentBase wrapper for the ETPS LAB-HP 41000 DC Power Supply."""
import time
from typing import Dict, List, Any
from ...core.instrument_base import InstrumentBase
from .driver import LABHPController


class LABHPInstrument(InstrumentBase):
    """
    Plugin wrapper integrating ETPS LAB-HP 41000 into the unified laboratory suite.
    All state-changing operations are verified by automatic read-back queries.
    """

    name: str = "ETPS LAB-HP 41000"
    short_id: str = "labhp"
    default_port: int = 10001
    supports_waveform: bool = False

    def __init__(self):
        self.controller = LABHPController()
        self.driver = self.controller
        self._cached_idn: str = ""

    def connect(self, ip: str, port: int = 10001) -> None:
        self.controller.connect(ip, port)
        try:
            self._cached_idn = self.controller.get_idn()
            self.controller.set_remote()
        except Exception:
            pass

    def disconnect(self) -> None:
        if self.controller.connected:
            try:
                self.controller.set_local()
            except Exception:
                pass
        self.controller.disconnect()
        self._cached_idn = ""

    def idn(self) -> str:
        if not self.controller.connected:
            return ""
        if not self._cached_idn:
            self._cached_idn = self.controller.get_idn()
        return self._cached_idn

    def measurement_columns(self) -> List[str]:
        return ["voltage_v", "current_a", "power_w", "resistance_ohm"]

    def poll_measurements(self) -> Dict[str, Any]:
        if not self.controller.connected:
            return {c: 0.0 for c in self.measurement_columns()}
        data = self.controller.measure_fast_telemetry()
        v = round(data.get("voltage", 0.0), 3)
        i = round(data.get("current", 0.0), 4)
        p = round(data.get("power", 0.0), 2)
        r = round(data.get("resistance", 0.0), 3) if data.get("resistance") != float('inf') else 999999.0
        return {
            "voltage_v": v,
            "current_a": i,
            "power_w": p,
            "resistance_ohm": r,
            "voltage": v,
            "current": i,
            "power": p,
            "resistance": r
        }

    def status(self) -> Dict[str, Any]:
        if not self.controller.connected:
            return {"connected": False, "output_on": False, "mode": "UNKNOWN"}
        raw = self.controller.get_status_raw()
        decoded = self.controller.decode_status(raw)
        out_state = self.controller.get_output_state()
        decoded["connected"] = True
        decoded["output_on"] = out_state
        try:
            decoded["mode"] = self.controller.get_mode()
        except Exception:
            decoded["mode"] = "UI"
        return decoded

    def command(self, raw: str) -> str:
        # Determine if command expects response
        raw_clean = raw.strip()
        expect_resp = any(raw_clean.startswith(q) for q in ["ID", "UA", "IA", "PA", "OVP", "SB", "MU", "MI", "STATUS", "MODE", "*IDN?", "?", "*OPC?"])
        if "," in raw_clean and not raw_clean.endswith("?"):
            expect_resp = False
        return self.controller._send(raw_clean, expect_response=expect_resp)

    @property
    def connected(self) -> bool:
        return self.controller.connected

    # Verified state-changing operations (write -> re-query -> return verified value)
    def set_voltage_verified(self, v: float) -> float:
        self.controller.set_voltage(v)
        time.sleep(0.04)
        return self.controller.get_voltage_setpoint()

    def set_current_verified(self, i: float) -> float:
        self.controller.set_current(i)
        time.sleep(0.04)
        return self.controller.get_current_setpoint()

    def set_power_verified(self, p: float) -> float:
        self.controller.set_power(p)
        time.sleep(0.04)
        return self.controller.get_power_setpoint()

    def set_ovp_verified(self, ovp: float) -> float:
        self.controller.set_ovp(ovp)
        time.sleep(0.04)
        return self.controller.get_ovp()

    def set_output_verified(self, enable: bool) -> bool:
        if enable:
            self.controller.output_on()
        else:
            self.controller.output_off()
        time.sleep(0.06)
        return self.controller.get_output_state()
