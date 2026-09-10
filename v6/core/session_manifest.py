"""SessionManifest — JSON session metadata manifest serialization and deserialization."""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .clock import SessionClock


class SessionManifest:
    """Writes and reads session.json metadata files unifying multi-instrument runs."""

    @staticmethod
    def write(
        session_dir: str,
        clock: SessionClock,
        csv_paths: Dict[str, str],
        waveform_dir: Optional[str] = None,
        instruments_meta: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> str:
        """
        Writes session.json into session_dir with session_start, session_stop, and instruments mapping.
        """
        s_dir = Path(session_dir)
        s_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = s_dir / "session.json"

        instruments_dict = {}
        for short_id, csv_path in csv_paths.items():
            meta = (instruments_meta or {}).get(short_id, {})
            # Try to read header columns from the CSV if not provided
            cols = meta.get("columns", [])
            if not cols and Path(csv_path).exists():
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line:
                            cols = [c.strip() for c in first_line.split(",")]
                except Exception:
                    cols = []

            instruments_dict[short_id] = {
                "csv": Path(csv_path).name,
                "csv_full_path": str(csv_path),
                "columns": cols,
                "name": meta.get("name", short_id),
                "sample_rate_hz": meta.get("rate_hz", None)
            }

        manifest = {
            "session_start": clock.t0_wall_iso,
            "session_stop": clock.wall_iso(),
            "duration_seconds": round(clock.elapsed(), 4),
            "waveform_directory": Path(waveform_dir).name if waveform_dir else "waveforms",
            "instruments": instruments_dict
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return str(manifest_path)

    @staticmethod
    def read(session_dir: str) -> Dict[str, Any]:
        """Reads session.json from session_dir and returns the manifest dictionary."""
        manifest_path = Path(session_dir) / "session.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
