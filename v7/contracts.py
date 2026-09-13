from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

class ChannelKind(Enum):
    ANALOG = "analog"
    DIGITAL = "digital"

@dataclass
class Channel:
    key: str
    label: str
    kind: ChannelKind
    unit: str
    color: str

@dataclass
class InstrumentConfig:
    short_id: str
    idn: str
    settings: dict = field(default_factory=dict)

class Instrument(ABC):
    name: str
    short_id: str
    default_resource_hint: str = ""
    supports_waveform: bool = False
    supports_events: bool = False

    @abstractmethod
    def connect(self, resource: str) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def idn(self) -> str: ...
    @abstractmethod
    def channels(self) -> list[Channel]: ...
    @abstractmethod
    def measurement_columns(self) -> list[str]: ...
    @abstractmethod
    def poll_measurements(self) -> dict[str, Any]: ...
    @abstractmethod
    def status(self) -> dict[str, Any]: ...
    @abstractmethod
    def command(self, raw: str) -> str: ...
    @property
    @abstractmethod
    def connected(self) -> bool: ...

    def configuration(self) -> dict: return {}
    def capture_waveform(self, channels: list[str]) -> dict: return {}
    def events(self) -> list[dict]: return []

class Transport(ABC):
    @abstractmethod
    def write(self, data: bytes) -> None: ...
    @abstractmethod
    def read_until(self, terminator: bytes, timeout_s: float) -> bytes: ...
    @abstractmethod
    def read_bytes(self, n: int, timeout_s: float) -> bytes: ...
    @abstractmethod
    def close(self) -> None: ...

CANONICAL_MEASUREMENTS = ["vrms", "vpp", "vmean", "freq", "period", "duty", "rise", "fall"]
