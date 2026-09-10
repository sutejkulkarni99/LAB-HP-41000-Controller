"""Scope UI Package: Screen, Channel, Timebase, Trigger, Math, and Softkey components."""
from .scope_screen import ScopeScreen
from .channel_control import ChannelControlWidget
from .timebase_control import TimebaseControlWidget
from .trigger_control import TriggerControlWidget
from .math_panel import MathPanelWidget
from .softkey_bar import SoftkeyBar

__all__ = [
    "ScopeScreen",
    "ChannelControlWidget",
    "TimebaseControlWidget",
    "TriggerControlWidget",
    "MathPanelWidget",
    "SoftkeyBar"
]
