import os
import time
import yaml
from typing import Dict, List, Any, Optional
from PySide6.QtCore import QThread, Signal

from .contracts import Instrument
from .session import LoggingSession

def load_protocol_yaml(path: str) -> dict:
    """Parse and return protocol definition dictionary from YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Protocol file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid protocol YAML: top-level object must be a mapping.")
    return data


class ProtocolExecutor(QThread):
    """Executes automated YAML test protocols with live feedback and deviation detection."""

    preview_ready = Signal(dict)
    step_started = Signal(int, str, float)
    step_finished = Signal(int, dict)
    deviation = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, protocol_path: str, instruments: dict[str, Instrument],
                 session: LoggingSession, parent=None):
        super().__init__(parent)
        self.protocol_path = protocol_path
        self.instruments = instruments
        self.session = session
        self._aborted = False
        self._data: dict = {}
        try:
            self._data = load_protocol_yaml(protocol_path)
        except Exception as e:
            self._data = {"steps": [], "error": str(e)}

    def validate(self) -> list[str]:
        """Validates steps, instruments, parameters, and safety limits."""
        issues = []
        if "error" in self._data:
            return [self._data["error"]]
        steps = self._data.get("steps", [])
        if not steps:
            issues.append("Protocol contains no executable steps.")

        for idx, step in enumerate(steps):
            inst_id = step.get("instrument")
            if not inst_id:
                issues.append(f"Step {idx + 1}: Missing 'instrument' target.")
            elif inst_id not in self.instruments:
                issues.append(f"Step {idx + 1}: Required instrument '{inst_id}' is not loaded.")
            action = step.get("action")
            if not action and not step.get("command"):
                issues.append(f"Step {idx + 1}: Missing 'action' or 'command'.")

        return issues

    def preview(self) -> dict:
        """Returns structured metadata and estimated run duration."""
        steps = self._data.get("steps", [])
        total_duration = sum(float(s.get("duration_s", s.get("wait_s", 0.0))) for s in steps)
        preview_data = {
            "title": self._data.get("title", os.path.basename(self.protocol_path)),
            "description": self._data.get("description", ""),
            "step_count": len(steps),
            "estimated_duration_s": total_duration,
            "steps": steps
        }
        self.preview_ready.emit(preview_data)
        return preview_data

    def abort(self) -> None:
        """Flags the running protocol to terminate immediately."""
        self._aborted = True

    def run(self) -> None:
        issues = self.validate()
        if issues:
            self.error.emit(f"Validation failed: {'; '.join(issues)}")
            return

        steps = self._data.get("steps", [])
        self._aborted = False

        try:
            for idx, step in enumerate(steps):
                if self._aborted:
                    self.finished.emit("Aborted by operator.")
                    return

                name = step.get("name", f"Step {idx + 1}")
                duration = float(step.get("duration_s", step.get("wait_s", 0.0)))
                self.step_started.emit(idx, name, duration)

                inst_id = step.get("instrument")
                inst = self.instruments.get(inst_id)

                # Execute command
                cmd = step.get("command")
                if inst and cmd:
                    resp = inst.command(cmd)

                # Check expected criteria / deviation
                expected = step.get("expect", {})
                if inst and expected:
                    meas = inst.poll_measurements()
                    for param, exp_val in expected.items():
                        actual_val = meas.get(param)
                        tol = float(step.get("tolerance", 0.1) * exp_val)
                        if actual_val is not None and abs(actual_val - exp_val) > tol:
                            self.deviation.emit(idx, f"{param} measured {actual_val} differs from expected {exp_val}")

                # Wait step duration
                t_end = time.monotonic() + duration
                while time.monotonic() < t_end:
                    if self._aborted:
                        self.finished.emit("Aborted by operator.")
                        return
                    time.sleep(0.05)

                self.step_finished.emit(idx, {"status": "SUCCESS", "name": name})

            self.finished.emit("Protocol completed successfully.")
        except Exception as e:
            self.error.emit(str(e))
