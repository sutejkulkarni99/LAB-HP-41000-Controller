"""ScopeMathEngine — Advanced waveform operations and automated scalar measurements."""
import math
from typing import Dict, Any, Tuple, Optional

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


class ScopeMathEngine:
    """Provides waveform mathematics (Addition, Subtraction, Multiplication, FFT) and scalar measurements."""

    @staticmethod
    def calculate_scalars(time_arr, volt_arr) -> Dict[str, float]:
        """Calculates Vmax, Vmin, Vpp, Vmean, Vrms, Frequency, and Period."""
        if len(volt_arr) == 0:
            return {
                "vmax": 0.0, "vmin": 0.0, "vpp": 0.0,
                "vmean": 0.0, "vrms": 0.0, "freq_hz": 0.0, "period_s": 0.0
            }

        if HAVE_NUMPY:
            v_arr = np.asarray(volt_arr, dtype=float)
            t_arr = np.asarray(time_arr, dtype=float)
            vmax = float(np.max(v_arr))
            vmin = float(np.min(v_arr))
            vpp = vmax - vmin
            vmean = float(np.mean(v_arr))
            vrms = float(np.sqrt(np.mean(v_arr ** 2)))
        else:
            v_arr = list(volt_arr)
            t_arr = list(time_arr)
            vmax = max(v_arr)
            vmin = min(v_arr)
            vpp = vmax - vmin
            vmean = sum(v_arr) / len(v_arr)
            vrms = math.sqrt(sum(x*x for x in v_arr) / len(v_arr))

        # Frequency & Period via midpoint zero-crossing analysis
        freq_hz = 0.0
        period_s = 0.0
        v_mid = (vmax + vmin) / 2.0

        crossings = []
        for i in range(1, len(v_arr)):
            if (v_arr[i-1] < v_mid <= v_arr[i]) or (v_arr[i-1] > v_mid >= v_arr[i]):
                # Linear interpolation for zero crossing timestamp
                dv = v_arr[i] - v_arr[i-1]
                if abs(dv) > 1e-12:
                    fraction = (v_mid - v_arr[i-1]) / dv
                    t_cross = t_arr[i-1] + fraction * (t_arr[i] - t_arr[i-1])
                    crossings.append((t_cross, v_arr[i] > v_arr[i-1]))  # time, is_rising

        rising_crossings = [t for t, is_rising in crossings if is_rising]
        if len(rising_crossings) >= 2:
            periods = [rising_crossings[k+1] - rising_crossings[k] for k in range(len(rising_crossings)-1)]
            avg_period = sum(periods) / len(periods)
            if avg_period > 1e-12:
                period_s = avg_period
                freq_hz = 1.0 / avg_period

        return {
            "vmax": round(vmax, 4),
            "vmin": round(vmin, 4),
            "vpp": round(vpp, 4),
            "vmean": round(vmean, 4),
            "vrms": round(vrms, 4),
            "freq_hz": round(freq_hz, 2),
            "period_s": period_s
        }

    @staticmethod
    def multiply_traces(time_arr, v1_arr, v2_arr) -> Tuple[Any, Any]:
        """Calculates instantaneous product of two channels (e.g. Voltage x Current = Power)."""
        if HAVE_NUMPY:
            return np.asarray(time_arr), np.asarray(v1_arr) * np.asarray(v2_arr)
        min_len = min(len(time_arr), len(v1_arr), len(v2_arr))
        t_res = time_arr[:min_len]
        p_res = [v1_arr[k] * v2_arr[k] for k in range(min_len)]
        return t_res, p_res

    @staticmethod
    def add_traces(time_arr, v1_arr, v2_arr) -> Tuple[Any, Any]:
        """Calculates CH1 + CH2."""
        if HAVE_NUMPY:
            return np.asarray(time_arr), np.asarray(v1_arr) + np.asarray(v2_arr)
        min_len = min(len(time_arr), len(v1_arr), len(v2_arr))
        return time_arr[:min_len], [v1_arr[k] + v2_arr[k] for k in range(min_len)]

    @staticmethod
    def subtract_traces(time_arr, v1_arr, v2_arr) -> Tuple[Any, Any]:
        """Calculates CH1 - CH2."""
        if HAVE_NUMPY:
            return np.asarray(time_arr), np.asarray(v1_arr) - np.asarray(v2_arr)
        min_len = min(len(time_arr), len(v1_arr), len(v2_arr))
        return time_arr[:min_len], [v1_arr[k] - v2_arr[k] for k in range(min_len)]

    @staticmethod
    def compute_fft(time_arr, volt_arr) -> Tuple[Any, Any]:
        """Computes one-sided FFT spectrum magnitude in dBV or linear volts."""
        if len(volt_arr) < 4:
            return [0.0], [0.0]

        if not HAVE_NUMPY:
            # Pure Python DFT fallback for environments without numpy
            n = len(volt_arr)
            step = max(1, n // 128)
            v_sub = list(volt_arr[::step])
            t_sub = list(time_arr[::step])
            m = len(v_sub)
            dt = abs(t_sub[-1] - t_sub[0]) / max(1, m - 1) if m > 1 else 1e-3
            mean_v = sum(v_sub) / m
            num_bins = max(1, min(64, m // 2))
            freqs = []
            mag_dbv = []
            for k in range(num_bins):
                f = k / (m * dt) if dt > 0 else float(k)
                re_sum = 0.0
                im_sum = 0.0
                for j in range(m):
                    w = 0.5 * (1.0 - math.cos(2.0 * math.pi * j / (m - 1))) if m > 1 else 1.0
                    val = (v_sub[j] - mean_v) * w
                    angle = 2.0 * math.pi * k * j / m
                    re_sum += val * math.cos(angle)
                    im_sum -= val * math.sin(angle)
                mag_lin = (2.0 / m) * math.sqrt(re_sum * re_sum + im_sum * im_sum)
                rms_val = max(1e-9, mag_lin / math.sqrt(2.0))
                dbv = 20.0 * math.log10(rms_val)
                freqs.append(round(f, 2))
                mag_dbv.append(round(dbv, 2))
            return freqs, mag_dbv

        t = np.asarray(time_arr)
        v = np.asarray(volt_arr)
        n = len(v)
        dt = abs(float(np.mean(np.diff(t))))
        if dt <= 0:
            return [], []

        # Apply Hanning window to reduce spectral leakage
        window = np.hanning(n)
        v_win = (v - np.mean(v)) * window

        fft_vals = np.fft.rfft(v_win)
        freqs = np.fft.rfftfreq(n, d=dt)

        # Magnitude in dBV: 20*log10(RMS volts)
        mag_linear = (2.0 / n) * np.abs(fft_vals)
        mag_dbv = 20.0 * np.log10(np.maximum(mag_linear / np.sqrt(2.0), 1e-9))

        return freqs, mag_dbv
