"""ModernMetricCard — Sleek vector metric card (inherited verbatim from v5)."""
from ..qt_compat import QFrame, QVBoxLayout, QHBoxLayout, QLabel, Qt


class ModernMetricCard(QFrame):
    """
    Sleek, high-contrast vector metric readout card.
    Displays Primary Value, Unit, Target Setpoint, and Deviation (Delta).
    Supports dynamic dark (Slate Control) and light (Clean Laboratory) themes.
    """

    def __init__(self, title: str, *args, parent=None, **kwargs):
        # Determine parent widget safely: QFrame requires Optional[QWidget], never a str/int
        q_parent = parent if (parent is not None and not isinstance(parent, (str, bytes, int, float, list, dict))) else None

        # Parse flexible argument patterns:
        # 1) ModernMetricCard("VOLTAGE", "V", "#38BDF8")
        # 2) ModernMetricCard("OUTPUT VOLTAGE", "0.00", "V", "#38BDF8")
        # 3) ModernMetricCard("OUTPUT VOLTAGE", unit="V", color_hex="#38BDF8")
        initial_val = kwargs.get("initial_val", "0.00")
        unit = kwargs.get("unit", "")
        color_hex = kwargs.get("color_hex", "#38BDF8")

        if len(args) == 1:
            unit = str(args[0])
        elif len(args) == 2:
            unit = str(args[0])
            color_hex = str(args[1])
        elif len(args) >= 3:
            # Check if args[2] is color hex (e.g. #38BDF8 or starts with # / named color)
            # or if args[0] looks like initial value (e.g. "0.00", "0.0000", "---")
            if isinstance(args[2], str) and (args[2].startswith("#") or "color" in args[2].lower() or len(args[2]) == 7):
                initial_val = str(args[0])
                unit = str(args[1])
                color_hex = str(args[2])
                if len(args) >= 4 and q_parent is None and not isinstance(args[3], (str, bytes, int, float, list, dict)):
                    q_parent = args[3]
            else:
                unit = str(args[0])
                color_hex = str(args[1])
                if q_parent is None and not isinstance(args[2], (str, bytes, int, float, list, dict)):
                    q_parent = args[2]

        super().__init__(q_parent)
        self.title_text = title
        self.unit_text = unit
        self.accent_color = color_hex
        self.setpoint_val = 0.0
        self.actual_val = 0.0

        self.setObjectName("metric_card")
        self.setStyleSheet(f"""
            QFrame#metric_card {{
                background-color: #1A1D24;
                border: 1px solid #2F3540;
                border-radius: 8px;
            }}
            QFrame#metric_card:hover {{
                background-color: #262B33;
                border: 1px solid {self.accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header Row: Title & Unit Badge
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #8B95A5;")
        header_row.addWidget(self.lbl_title)

        header_row.addStretch()

        self.lbl_unit = QLabel(f"[{unit}]")
        self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
        header_row.addWidget(self.lbl_unit)
        layout.addLayout(header_row)

        # Primary Vector Digits
        self.lbl_value = QLabel(initial_val)
        self.lbl_value.setStyleSheet("""
            font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
            font-size: 26pt;
            font-weight: 700;
            color: #E8EDF2;
            margin: 2px 0;
        """)
        try:
            self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        except Exception:
            pass
        layout.addWidget(self.lbl_value)

        # Sub-stats row: Setpoint & Delta
        sub_row = QHBoxLayout()
        sub_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_setpoint = QLabel("Set: 0.00")
        self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #8B95A5;")
        sub_row.addWidget(self.lbl_setpoint)

        sub_row.addStretch()

        self.lbl_delta = QLabel("Δ 0.00")
        self.lbl_delta.setStyleSheet("font-size: 9pt; font-family: monospace; color: #8B95A5;")
        sub_row.addWidget(self.lbl_delta)
        layout.addLayout(sub_row)

    def set_theme(self, is_dark: bool, accent_color: str = None):
        """Adapt metric card styling to Slate Control or Clean Laboratory."""
        if accent_color:
            self.accent_color = accent_color

        if is_dark:
            self.setStyleSheet(f"""
                QFrame#metric_card {{
                    background-color: #1A1D24;
                    border: 1px solid #2F3540;
                    border-radius: 8px;
                }}
                QFrame#metric_card:hover {{
                    background-color: #262B33;
                    border: 1px solid {self.accent_color};
                }}
            """)
            self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #8B95A5;")
            self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
            self.lbl_value.setStyleSheet("""
                font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
                font-size: 26pt;
                font-weight: 700;
                color: #E8EDF2;
                margin: 2px 0;
            """)
            self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #8B95A5;")
        else:
            self.setStyleSheet(f"""
                QFrame#metric_card {{
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }}
                QFrame#metric_card:hover {{
                    background-color: #F1F5F9;
                    border: 1px solid {self.accent_color};
                }}
            """)
            self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #475569;")
            self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
            self.lbl_value.setStyleSheet("""
                font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
                font-size: 26pt;
                font-weight: 700;
                color: #0F172A;
                margin: 2px 0;
            """)
            self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #475569;")

    def _update_delta_label(self, decimals: int = 2):
        diff = self.actual_val - self.setpoint_val
        delta_sign = "+" if diff > 0.0001 else ("-" if diff < -0.0001 else "±")
        delta_str = f"Δ {delta_sign}{abs(diff):.{min(decimals, 3)}f} {self.unit_text}"

        if abs(diff) < 0.05:
            delta_color = "#22c55e"  # on target (green)
        elif abs(diff) < 1.0:
            delta_color = "#94a3b8"  # nominal (gray)
        else:
            delta_color = "#f59e0b"  # regulating or ramping (amber)

        self.lbl_delta.setText(delta_str)
        self.lbl_delta.setStyleSheet(f"font-size: 8.5pt; font-family: monospace; color: {delta_color};")

    def set_value(self, val):
        """Sets display value directly, accepting string (e.g. '0.00', '---') or float."""
        if isinstance(val, (int, float)):
            self.update_measurement(float(val))
        else:
            self.lbl_value.setText(str(val))
            try:
                cleaned = str(val).replace("k", "").replace("M", "").strip()
                self.actual_val = float(cleaned)
                self._update_delta_label()
            except (ValueError, TypeError):
                pass

    def update_measurement(self, actual: float, decimals: int = 2):
        self.actual_val = actual
        fmt = f"{{:.{decimals}f}}"
        self.lbl_value.setText(fmt.format(actual))
        self._update_delta_label(decimals)

    def set_setpoint(self, setpoint: float, decimals: int = 2):
        self.update_setpoint(setpoint, decimals)

    def update_setpoint(self, setpoint: float, decimals: int = 2):
        self.setpoint_val = setpoint
        fmt = f"Set: {{:.{decimals}f}} {self.unit_text}"
        self.lbl_setpoint.setText(fmt.format(setpoint))
        self.update_measurement(self.actual_val, decimals)
