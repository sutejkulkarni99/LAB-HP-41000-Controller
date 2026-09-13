import os
import json
import numpy as np

class WaveformStore:
    """Waveform serialization and persistence using compressed NumPy archives."""

    @staticmethod
    def save_npz(path: str, time: np.ndarray, channels: dict[str, np.ndarray], metadata: dict) -> str:
        """Saves time vector, channel arrays, and JSON metadata to an NPZ archive."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        save_dict = {
            "time": np.asarray(time, dtype=np.float64),
            "__metadata__": np.array(json.dumps(metadata), dtype=object)
        }
        for ch_name, data in channels.items():
            save_dict[f"ch_{ch_name}"] = np.asarray(data, dtype=np.float32)
        np.savez_compressed(path, **save_dict)
        return path

    @staticmethod
    def load_npz(path: str) -> dict:
        """Loads NPZ archive, returning dict with time, channels, and metadata."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Waveform archive not found: {path}")
        with np.load(path, allow_pickle=True) as data:
            meta = {}
            if "__metadata__" in data:
                meta = json.loads(str(data["__metadata__"]))
            channels = {}
            for k in data.files:
                if k.startswith("ch_"):
                    ch_key = k[3:]
                    channels[ch_key] = data[k]
            time_arr = data["time"] if "time" in data else np.array([], dtype=np.float64)
            return {
                "time": time_arr,
                "channels": channels,
                "metadata": meta
            }
