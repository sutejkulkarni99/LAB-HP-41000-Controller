"""UI Tabs Package: PSU, Scope, Session, Plots, SOA, and Terminal workspaces."""
from .psu_tab import PSUTab
from .scope_tab import ScopeTab
from .session_tab import SessionTab
from .plots_tab import PlotsTab
from .soa_tab import SOATab
from .terminal_tab import TerminalTab

__all__ = [
    "PSUTab",
    "ScopeTab",
    "SessionTab",
    "PlotsTab",
    "SOATab",
    "TerminalTab"
]
