"""WaveformTrace — Structured container for oscilloscope channel acquisitions."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


@dataclass
class WaveformTrace:
    """Represents an acquired oscilloscope waveform trace with calibrated physical units."""
    channel: int
    time_array: Any               # numpy 1D array or list of floats
    volt_array: Any               # numpy 1D array or list of floats
    sample_rate: float = 1e6
    timebase_scale: float = 1e-3  # seconds / div
    v_scale: float = 1.0          # volts / div
    v_offset: float = 0.0         # volts
    coupling: str = "DC"
    unit: str = "V"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def x_time(self):
        return self.time_array

    @property
    def y_volts(self):
        return self.volt_array

    def to_dict(self) -> Dict[str, Any]:
        t_data = self.time_array.tolist() if hasattr(self.time_array, 'tolist') else list(self.time_array)
        v_data = self.volt_array.tolist() if hasattr(self.volt_array, 'tolist') else list(self.volt_array)
        return {
            "channel": self.channel,
            "time": t_data,
            "voltage": v_data,
            "sample_rate": self.sample_rate,
            "timebase_scale": self.timebase_scale,
            "v_scale": self.v_scale,
            "v_offset": self.v_offset,
            "coupling": self.coupling,
            "unit": self.unit,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WaveformTrace":
        t_arr = d.get("time", [])
        v_arr = d.get("voltage", [])
        if HAVE_NUMPY:
            t_arr = np.array(t_arr, dtype=float)
            v_arr = np.array(v_arr, dtype=float)
        return cls(
            channel=int(d.get("channel", 1)),
            time_array=t_arr,
            volt_array=v_arr,
            sample_rate=float(d.get("sample_rate", 1e6)),
            timebase_scale=float(d.get("timebase_scale", 1e-3)),
            v_scale=float(d.get("v_scale", 1.0)),
            v_offset=float(d.get("v_offset", 0.0)),
            coupling=str(d.get("coupling", "DC")),
            unit=str(d.get("unit", "V")),
            metadata=dict(d.get("metadata", {}))
        )
