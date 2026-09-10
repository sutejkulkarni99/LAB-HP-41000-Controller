"""RTB2000Instrument — High-level InstrumentBase wrapper for Rohde & Schwarz RTB2000."""
import time
from typing import Dict, Any, List, Optional
from ...core.instrument_base import InstrumentBase
from .driver import RTB2000Driver


class RTB2000Instrument(InstrumentBase):
    """
    Instrument wrapper exposing the Rohde & Schwarz RTB2000 oscilloscope
    under the unified InstrumentBase contract.
    """

    def __init__(self):
        self.driver = RTB2000Driver()
        self._cached_idn: str = ""
        self._status_cache: Dict[str, Any] = {}
        self._status_cache_time: float = 0.0
        self._cached_columns: Optional[List[str]] = None

    @property
    def short_id(self) -> str:
        return "rtb2000"

    @property
    def name(self) -> str:
        return "Rohde & Schwarz RTB2000 Oscilloscope"

    @property
    def connected(self) -> bool:
        return self.driver.connected

    def connect(self, ip: str, port: int = 5025) -> None:
        """Connects to the scope and initializes configuration. Propagates errors."""
        self.driver.connect(ip, port)
        self._cached_idn = self.driver.get_idn()
        self._status_cache.clear()
        self._status_cache_time = 0.0
        self.invalidate_columns_cache()

    def disconnect(self) -> None:
        """Disconnects socket and clears caches."""
        self.driver.disconnect()
        self._cached_idn = ""
        self._status_cache.clear()
        self._status_cache_time = 0.0
        self._cached_columns = None

    def idn(self) -> str:
        """Query instrument identification string."""
        if not self.driver.connected:
            return ""
        if not self._cached_idn:
            self._cached_idn = self.driver.get_idn()
        return self._cached_idn

    def command(self, raw: str) -> str:
        """Send raw SCPI command string and return response if query."""
        if not self.driver.connected:
            raise ConnectionError("RTB2000 not connected")
        if "?" in raw:
            return self.driver.query(raw)
        else:
            self.driver.send(raw)
            return ""

    def status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Queries operational status of the oscilloscope.
        Returns cached dict if younger than 2.0 seconds unless force_refresh=True.
        """
        if not self.driver.connected:
            return {"connected": False, "running": False}

        now = time.monotonic()
        if not force_refresh and self._status_cache and (now - self._status_cache_time < 2.0):
            return dict(self._status_cache)

        status_dict = {"connected": True}
        try:
            status_dict["timebase_scale"] = self.driver.get_timebase_scale()
            status_dict["trigger_mode"] = self.driver.get_trigger_mode()
            status_dict["trigger_source"] = self.driver.get_trigger_source()
            status_dict["ch1_on"] = self.driver.get_channel_state(1)
            status_dict["ch2_on"] = self.driver.get_channel_state(2)
            status_dict["ch1_scale"] = self.driver.get_channel_scale(1)
            status_dict["ch2_scale"] = self.driver.get_channel_scale(2)
        except Exception:
            pass

        self._status_cache = status_dict
        self._status_cache_time = now
        return dict(status_dict)

    def measurement_columns(self) -> List[str]:
        """
        Dynamically returns list of CSV column identifiers for enabled channels.
        Caches the list after query; invalidated on channel state change.
        """
        if self._cached_columns is not None:
            return self._cached_columns

        if not self.driver.connected:
            return []

        cols = []
        for n in range(1, 5):
            try:
                if self.driver.get_channel_state(n):
                    cols.extend([f"ch{n}_vrms", f"ch{n}_vpp", f"ch{n}_freq_hz"])
            except Exception:
                pass

        self._cached_columns = cols
        return self._cached_columns

    def invalidate_columns_cache(self) -> None:
        """Invalidates cached column list."""
        self._cached_columns = None

    def poll_measurements(self) -> Dict[str, Any]:
        """
        Polls instant scalar metrics across channels.
        Driver exceptions are propagated without fabricating zeros.
        """
        if not self.driver.connected:
            raise ConnectionError("RTB2000 not connected")

        ch1_rms = self.driver.measure_parameter(1, "RMS")
        ch1_vpp = self.driver.measure_parameter(1, "PEAK")
        ch1_freq = self.driver.measure_parameter(1, "FREQuency")

        ch2_rms = self.driver.measure_parameter(2, "RMS")
        ch2_vpp = self.driver.measure_parameter(2, "PEAK")
        ch2_freq = self.driver.measure_parameter(2, "FREQuency")

        return {
            "ch1_vrms": round(ch1_rms, 4),
            "ch1_vpp": round(ch1_vpp, 4),
            "ch1_freq_hz": round(ch1_freq, 2),
            "ch2_vrms": round(ch2_rms, 4),
            "ch2_vpp": round(ch2_vpp, 4),
            "ch2_freq_hz": round(ch2_freq, 2),
        }

    def get_waveform(self, channel: int = 1):
        """
        Fetches a calibrated WaveformTrace for the specified channel.
        Driver exceptions are propagated.
        """
        if not self.driver.connected:
            raise ConnectionError("RTB2000 not connected")

        from .waveform import WaveformTrace
        t_arr, v_arr = self.driver.fetch_channel_waveform(channel)
        v_scale = self.driver.get_channel_scale(channel)
        tb_scale = self.driver.get_timebase_scale()

        return WaveformTrace(
            channel=channel,
            time_array=t_arr,
            volt_array=v_arr,
            v_scale=v_scale,
            timebase_scale=tb_scale
        )

    # Verified Hardware Setters using *OPC? synchronization
    def set_timebase_scale_verified(self, scale: float) -> float:
        self.driver.set_timebase_scale(scale)
        self.driver.query("*OPC?", timeout=2.0)
        return self.driver.get_timebase_scale()

    def set_channel_scale_verified(self, ch: int, scale: float) -> float:
        self.driver.set_channel_scale(ch, scale)
        self.driver.query("*OPC?", timeout=2.0)
        return self.driver.get_channel_scale(ch)

    def set_channel_state_verified(self, ch: int, state: bool) -> bool:
        self.driver.set_channel_state(ch, state)
        self.driver.query("*OPC?", timeout=2.0)
        self.invalidate_columns_cache()
        return self.driver.get_channel_state(ch)

    def set_trigger_level_verified(self, level: float, ch: int = 1) -> float:
        self.driver.set_trigger_level(level, ch=ch)
        self.driver.query("*OPC?", timeout=2.0)
        return self.driver.get_trigger_level(ch=ch)
