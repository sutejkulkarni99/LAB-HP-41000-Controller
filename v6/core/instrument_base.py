"""InstrumentBase — Abstract Base Class defining the unified contract for laboratory instruments."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class InstrumentBase(ABC):
    """
    Abstract contract for laboratory instruments (Power Supplies, Oscilloscopes, Loads, DMMs).
    Every instrument plugin must implement these core hooks so workers and UI can manage
    them uniformly.
    """

    name: str = "Generic Instrument"
    short_id: str = "generic"
    default_port: int = 10001
    supports_waveform: bool = False

    @abstractmethod
    def connect(self, ip: str, port: int) -> None:
        """Establish network or interface connection to device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully terminate connection and release socket/resources."""
        pass

    @abstractmethod
    def idn(self) -> str:
        """Query instrument identification string."""
        pass

    @abstractmethod
    def measurement_columns(self) -> List[str]:
        """
        Ordered list of column names for CSV logging.
        Must match keys returned by poll_measurements().
        """
        pass

    @abstractmethod
    def poll_measurements(self) -> Dict[str, Any]:
        """
        Query high-speed telemetry / telemetry dictionary from device.
        Keys should correspond to measurement_columns().
        """
        pass

    @abstractmethod
    def status(self) -> Dict[str, Any]:
        """Query decoded operating status (mode, output state, alarms/faults)."""
        pass

    @abstractmethod
    def command(self, raw: str) -> str:
        """Send raw command string (SCPI or ASCII) and return response if any."""
        pass

    def capture_waveform(self, channels: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Capture high-resolution waveform traces (scopes, digitizers).
        Returns dict with keys: 'time', 'ch1', 'ch2', ..., 'metadata'.
        Default implementation returns empty dict for instruments that do not support waveforms.
        """
        return {}

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Return True if connection is currently active."""
        pass
