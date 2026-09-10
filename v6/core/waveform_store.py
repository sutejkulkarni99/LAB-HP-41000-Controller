"""WaveformStore — Compact binary storage and loading for oscilloscope and digitizer traces."""
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


class WaveformStore:
    """Manages reading and writing compressed waveform archives (.npz) within session folders."""

    @staticmethod
    def save(
        target: str,
        arg2: Any = None,
        wall_ts: Optional[str] = None,
        channels_dict: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Saves waveform capture channels into a compressed .npz archive.
        Supports both:
          1. WaveformStore.save(filepath, data_dict, metadata=...)
          2. WaveformStore.save(session_dir, short_id, wall_ts, channels_dict)
        """
        target_path = Path(target)

        # Check if target is a direct file path ending with .npz or .json
        if target_path.suffix in [".npz", ".json"] or arg2 is not None and isinstance(arg2, dict):
            out_path = target_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            data_to_save = dict(arg2) if isinstance(arg2, dict) else {}
            if metadata:
                data_to_save["metadata"] = metadata
        else:
            session_dir = target
            short_id = str(arg2)
            waveforms_dir = Path(session_dir) / "waveforms"
            waveforms_dir.mkdir(parents=True, exist_ok=True)

            safe_ts = re.sub(r'[^0-9a-zA-Z_-]', '_', str(wall_ts or time.time()))
            filename = f"{short_id}_wave_{safe_ts}.npz"
            out_path = waveforms_dir / filename
            data_to_save = dict(channels_dict) if channels_dict else {}
            if metadata:
                data_to_save["metadata"] = metadata

        save_dict = {}
        for key, val in data_to_save.items():
            if HAVE_NUMPY:
                if isinstance(val, (list, tuple)):
                    save_dict[key] = np.array(val)
                elif isinstance(val, np.ndarray):
                    save_dict[key] = val
                else:
                    save_dict[key] = np.array(val, dtype=object)
            else:
                save_dict[key] = val

        if HAVE_NUMPY:
            np.savez_compressed(str(out_path), **save_dict)
        else:
            import json
            fallback_path = out_path.with_suffix(".json")
            clean_dict = {}
            for k, v in data_to_save.items():
                if hasattr(v, 'tolist'):
                    clean_dict[k] = v.tolist()
                elif isinstance(v, (list, dict, str, int, float, bool)):
                    clean_dict[k] = v
                else:
                    clean_dict[k] = str(v)
            with open(fallback_path, "w", encoding="utf-8") as f:
                json.dump(clean_dict, f)
            return str(fallback_path)

        return str(out_path)

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        """Loads .npz waveform file and returns dictionary of arrays and metadata."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Waveform archive not found: {path}")

        if p.suffix == ".json":
            import json
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

        if HAVE_NUMPY:
            with np.load(str(p), allow_pickle=True) as data:
                res = {}
                for key in data.files:
                    val = data[key]
                    if val.dtype == object and val.ndim == 0:
                        res[key] = val.item()
                    else:
                        res[key] = val
                return res
        else:
            raise RuntimeError("NumPy is required to unpack .npz waveform archives.")
