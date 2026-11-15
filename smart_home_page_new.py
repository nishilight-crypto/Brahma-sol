from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QEasingCurve, QDateTime, QPropertyAnimation, QRect, Qt, QTimer, pyqtSignal, QEvent, QEventLoop
from PyQt6.QtGui import QFont, QPixmap, QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)

from smart_home import SmartHomeService


BG = "#020305"
PANEL = "#07080b"
PANEL_2 = "#0d0f14"
ACCENT = "#00e5ff"
ACCENT_SOFT = "rgba(0, 229, 255, 0.12)"
ACCENT_LINE = "rgba(0, 229, 255, 0.22)"
TEXT = "#ffffff"
TEXT_MED = "rgba(255,255,255,0.85)"
TEXT_DIM = "rgba(255,255,255,0.65)"
GREEN = "#37ff5f"


@dataclass(frozen=True)
class PlatformRow:
    key: str
    name: str
    available: bool
    auth_fields: list[tuple[str, str, str, bool]]


class ClickableFrame(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


def _panel_style(border_alpha: int = 34) -> str:
    alpha = border_alpha / 255.0
    return (
        "QFrame { "
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(16, 18, 26, 0.75), stop:1 rgba(8, 10, 15, 0.88)); "
        f"border: 1.5px solid rgba(0, 229, 255, {alpha:.3f}); "
        "border-radius: 18px; "
        "}"
    )


def _soft_button_style() -> str:
    return (
        f"QPushButton {{ background: rgba(255,255,255,0.03); color: {TEXT}; "
        "border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0 12px; }}"
        f"QPushButton:hover {{ border: 1px solid {ACCENT}; background: rgba(0, 229, 255,0.08); }}"
    )


class AddDeviceDialog(QWidget):
    """
    In-Window Modal Overlay for Adding Smart Home Devices.
    Renders strictly inside the Brahma Sol application window with a dimmed backdrop.
    Never spawns an external desktop OS window.
    """
    def __init__(self, service: SmartHomeService, parent=None):
        target_parent = parent
        if target_parent and hasattr(target_parent, "window"):
            target_parent = target_parent.window()
            if hasattr(target_parent, "centralWidget") and target_parent.centralWidget():
                target_parent = target_parent.centralWidget()
        super().__init__(target_parent)
        self._service = service
        self._provider_key: str | None = None
        self._provider_label = ""
        self._preview: dict[str, Any] = {}
        self._result: dict[str, Any] = {}
        self._fields: dict[str, QLineEdit] = {}
        self._checks: list[tuple[str, QCheckBox]] = []
        self._platform_buttons: list[ClickableFrame] = []
        self._loop = None
        self._result_code = QDialog.DialogCode.Rejected if hasattr(QDialog, "DialogCode") else 0

        self.setObjectName("AddDeviceModalBackdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#AddDeviceModalBackdrop {
                background: rgba(15, 23, 42, 0.45);
            }
        """)

        if target_parent:
            self.setGeometry(target_parent.rect())
            target_parent.installEventFilter(self)

        backdrop_layout = QVBoxLayout(self)
        backdrop_layout.setContentsMargins(16, 16, 16, 16)
        backdrop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Modal Card Frame
        self._card_frame = QFrame(self)
        self._card_frame.setObjectName("AddDeviceCardFrame")
        card_w = min(840, target_parent.width() - 32) if target_parent else 840
        card_h = min(670, target_parent.height() - 32) if target_parent else 670
        self._card_frame.setFixedSize(max(500, card_w), max(400, card_h))
        self._card_frame.setStyleSheet("""
            QFrame#AddDeviceCardFrame {
                background: #F8F6F0;
                border: 1.5px solid #E2E8F0;
                border-radius: 16px;
            }
            QLabel {
                background: transparent;
                color: #0F172A;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit, QComboBox {
                background: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                min-height: 38px;
                padding: 0 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1.5px solid #0284C7;
                background: #FFFFFF;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        try:
            shadow = QGraphicsDropShadowEffect(self._card_frame)
            shadow.setBlurRadius(36)
            shadow.setColor(QColor(15, 23, 42, 70))
            shadow.setOffset(0, 10)
            self._card_frame.setGraphicsEffect(shadow)
        except Exception:
            pass

        backdrop_layout.addWidget(self._card_frame)

        root = QVBoxLayout(self._card_frame)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Header Section
        header_lay = QHBoxLayout()
        header_lay.setSpacing(12)

        icon_box = QLabel("⚡")
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFont(QFont("Segoe UI", 15))
        icon_box.setStyleSheet(
            "background: #FFF7ED; color: #D97706; border: 1.5px solid #FDE68A; border-radius: 20px;"
        )
        header_lay.addWidget(icon_box)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Add Smart Device")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #0D1829; letter-spacing: 0.3px;")

        sub = QLabel("Select a platform to authenticate, scan your local network or cloud, and sync your devices.")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #5A6B82;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_lay.addLayout(title_box, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #64748B;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: #E2E8F0;
                color: #0F172A;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_lay.addWidget(close_btn)

        root.addLayout(header_lay)

        # Step Progress Pills
        self._step_indicators = QHBoxLayout()
        self._step_indicators.setSpacing(8)
        self._step_labels = []
        steps_text = ["1. Platform", "2. Authenticate", "3. Discover", "4. Complete"]
        for idx, st_name in enumerate(steps_text):
            lbl = QLabel(st_name)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(28)
            self._step_labels.append(lbl)
            self._step_indicators.addWidget(lbl, 1)
        root.addLayout(self._step_indicators)

        # Stack Pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_platform_page())
        self._stack.addWidget(self._build_auth_page())
        self._stack.addWidget(self._build_scan_page())
        self._stack.addWidget(self._build_finish_page())
        root.addWidget(self._stack, 1)

        # Bottom Actions Bar
        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 0)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setMinimumHeight(38)
        self._cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #64748B;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                padding: 0 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F1F5F9;
                color: #0F172A;
                border-color: #94A3B8;
            }
            """
        )
        self._cancel_btn.clicked.connect(self.reject)
        row.addWidget(self._cancel_btn)

        row.addStretch(1)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setMinimumHeight(38)
        self._back_btn.setStyleSheet(
            """
            QPushButton {
                background: #F8FAFC;
                color: #475569;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                padding: 0 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F1F5F9;
                color: #0F172A;
                border-color: #CBD5E1;
            }
            QPushButton:disabled {
                background: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }
            """
        )
        self._back_btn.clicked.connect(self._go_back)
        row.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setMinimumHeight(38)
        self._next_btn.setStyleSheet(
            """
            QPushButton {
                background: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0 24px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #0369A1;
            }
            QPushButton:disabled {
                background: #CBD5E1;
                color: #FFFFFF;
            }
            """
        )
        self._next_btn.clicked.connect(self._go_next)
        row.addWidget(self._next_btn)

        root.addLayout(row)
        self._sync_buttons()

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            if hasattr(self, "_card_frame"):
                card_w = min(840, self.parent().width() - 32)
                card_h = min(670, self.parent().height() - 32)
                self._card_frame.setFixedSize(max(500, card_w), max(400, card_h))
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if hasattr(self, "_card_frame") and not self._card_frame.geometry().contains(event.pos()):
            self.reject()
            event.accept()
            return
        super().mousePressEvent(event)

    def exec(self) -> int:
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._loop = QEventLoop()
        self._loop.exec()
        return self._result_code

    def accept(self):
        accepted_code = QDialog.DialogCode.Accepted if hasattr(QDialog, "DialogCode") else 1
        self._result_code = accepted_code
        if self._loop and self._loop.isRunning():
            self._loop.quit()
        if self.parent():
            try:
                self.parent().removeEventFilter(self)
            except Exception:
                pass
        self.hide()
        self.deleteLater()

    def reject(self):
        rejected_code = QDialog.DialogCode.Rejected if hasattr(QDialog, "DialogCode") else 0
        self._result_code = rejected_code
        if self._loop and self._loop.isRunning():
            self._loop.quit()
        if self.parent():
            try:
                self.parent().removeEventFilter(self)
            except Exception:
                pass
        self.hide()
        self.deleteLater()

    def result_payload(self) -> dict[str, Any]:
        return dict(self._result)

    def _card(self, title: str, subtitle: str = "") -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            """
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(3)
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #0D1829; border: none; background: transparent;")
        lay.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setFont(QFont("Segoe UI", 9))
            sub.setStyleSheet("color: #64748B; border: none; background: transparent;")
            lay.addWidget(sub)
        return frame

    def _brand_glyph(self, key: str) -> str:
        return {
            "havells": "⚡",
            "atomberg": "🌀",
            "kasa": "🔌",
            "hue": "💡",
            "lg": "📺",
            "daikin": "❄️",
            "tuya": "⚙️",
            "nest": "🏠",
            "smartthings": "📡"
        }.get(key, "⚙️")

    def _brand_badge_style(self, key: str) -> str:
        return {
            "havells": "background: #FFF7ED; color: #EA580C; border: 1.5px solid #FFEDD5; border-radius: 20px;",
            "atomberg": "background: #ECFDF5; color: #059669; border: 1.5px solid #D1FAE5; border-radius: 20px;",
            "kasa": "background: #E0F2FE; color: #0284C7; border: 1.5px solid #BAE6FD; border-radius: 20px;",
            "hue": "background: #FEF3C7; color: #D97706; border: 1.5px solid #FDE68A; border-radius: 20px;",
            "lg": "background: #FAF5FF; color: #9333EA; border: 1.5px solid #F3E8FF; border-radius: 20px;",
            "daikin": "background: #F0F9FF; color: #0284C7; border: 1.5px solid #E0F2FE; border-radius: 20px;",
            "tuya": "background: #FFF1F2; color: #E11D48; border: 1.5px solid #FFE4E6; border-radius: 20px;",
            "nest": "background: #F1F5F9; color: #2563EB; border: 1.5px solid #E2E8F0; border-radius: 20px;",
            "smartthings": "background: #EEF2FF; color: #4F46E5; border: 1.5px solid #E0E7FF; border-radius: 20px;",
        }.get(key, "background: #F8FAFC; color: #0284C7; border: 1.5px solid #E2E8F0; border-radius: 20px;")

    def _build_platform_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        header_card = self._card("Step 1: Choose Your Platform", "Select an ecosystem to discover connected lights, fans, plugs, and appliances.")
        lay.addWidget(header_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        grid_host = QWidget()
        grid_host.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 2, 8, 2)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        for idx, platform in enumerate(self._platforms()):
            card = ClickableFrame()
            card.setObjectName(f"PlatformCard_{platform.key}")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            lay_c = QHBoxLayout(card)
            lay_c.setContentsMargins(16, 14, 16, 14)
            lay_c.setSpacing(14)

            badge = QLabel(self._brand_glyph(platform.key))
            badge.setFixedSize(40, 40)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFont(QFont("Segoe UI", 15))
            badge.setStyleSheet(self._brand_badge_style(platform.key))
            lay_c.addWidget(badge)

            text_lay = QVBoxLayout()
            text_lay.setSpacing(3)

            p_name = QLabel(platform.name)
            p_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p_name.setStyleSheet("color: #0F172A; border: none; background: transparent;")

            subtitle = {
                "havells": "Smart fans, lights, geysers & switches",
                "atomberg": "Ceiling fans & smart air flow",
                "kasa": "Plugs, switches, & smart sockets",
                "hue": "Smart lights, strips, & hue sync",
                "lg": "LG webOS smart TVs & apps",
                "daikin": "Split ACs & climate controls",
                "tuya": "IoT switches & generic appliances",
                "nest": "Thermostats & home security",
                "smartthings": "Samsung hub & IoT integrations",
            }.get(platform.key, "Smart home cloud connection")

            p_sub = QLabel(subtitle)
            p_sub.setFont(QFont("Segoe UI", 9))
            p_sub.setStyleSheet("color: #64748B; border: none; background: transparent;")

            text_lay.addWidget(p_name)
            text_lay.addWidget(p_sub)
            lay_c.addLayout(text_lay, 1)

            card.setMinimumHeight(68)
            card.setStyleSheet(
                """
                QFrame {
                    background: #FFFFFF;
                    border: 1.5px solid #E2E8F0;
                    border-radius: 14px;
                }
                QFrame:hover {
                    background: #F8FAFC;
                    border: 1.5px solid #38BDF8;
                }
                """
            )

            card.clicked.connect(lambda key=platform.key, label=platform.name: self._choose_provider(key, label))
            self._platform_buttons.append(card)
            grid.addWidget(card, idx // 2, idx % 2)

        scroll.setWidget(grid_host)
        lay.addWidget(scroll, 1)
        return page

    def _build_auth_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self._auth_header_card = self._card("Step 2: Authenticate Account", "Provide connection credentials to authorize local device discovery.")
        lay.addWidget(self._auth_header_card)

        form_container = QFrame()
        form_container.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            """
        )
        form_box = QVBoxLayout(form_container)
        form_box.setContentsMargins(22, 20, 22, 20)
        form_box.setSpacing(14)

        self._auth_desc = QLabel("Select a platform to build the authentication form.")
        self._auth_desc.setFont(QFont("Segoe UI", 10))
        self._auth_desc.setStyleSheet("color: #475569; border: none;")
        form_box.addWidget(self._auth_desc)

        self._auth_form_host = QWidget()
        self._auth_form_host.setStyleSheet("background: transparent; border: none;")
        self._auth_form = QFormLayout(self._auth_form_host)
        self._auth_form.setContentsMargins(0, 8, 0, 8)
        self._auth_form.setVerticalSpacing(14)
        self._auth_form.setHorizontalSpacing(16)
        form_box.addWidget(self._auth_form_host)

        note_lbl = QLabel("🔒 Privacy Notice: All API keys and credentials are encrypted and stored locally on your machine.")
        note_lbl.setFont(QFont("Segoe UI", 9))
        note_lbl.setStyleSheet("color: #64748B; border: none; padding-top: 6px;")
        form_box.addWidget(note_lbl)

        lay.addWidget(form_container, 1)
        return page

    def _build_scan_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._card("Step 3: Device Discovery", "Scanning your network and cloud services for compatible smart home hardware."))

        scan_card = QFrame()
        scan_card.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            """
        )
        s_box = QVBoxLayout(scan_card)
        s_box.setContentsMargins(20, 18, 20, 18)
        s_box.setSpacing(12)

        self._scan_label = QLabel("Searching for devices...")
        self._scan_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._scan_label.setStyleSheet("color: #0D1829; border: none;")
        s_box.addWidget(self._scan_label)

        self._scan_bar = QProgressBar()
        self._scan_bar.setRange(0, 100)
        self._scan_bar.setValue(25)
        self._scan_bar.setTextVisible(False)
        self._scan_bar.setFixedHeight(8)
        self._scan_bar.setStyleSheet(
            """
            QProgressBar {
                background: #E2E8F0;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
                border-radius: 4px;
            }
            """
        )
        s_box.addWidget(self._scan_bar)

        self._scan_scroll = QScrollArea()
        self._scan_scroll.setWidgetResizable(True)
        self._scan_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scan_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scan_host = QWidget()
        self._scan_host.setStyleSheet("background: transparent;")
        self._scan_list = QVBoxLayout(self._scan_host)
        self._scan_list.setSpacing(10)
        self._scan_list.addStretch(1)
        self._scan_scroll.setWidget(self._scan_host)
        s_box.addWidget(self._scan_scroll, 1)

        lay.addWidget(scan_card, 1)
        return page

    def _build_finish_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._card("Step 4: Connection Summary", "Devices are ready to be integrated into your Brahma Sol environment."))

        finish_card = QFrame()
        finish_card.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            """
        )
        f_box = QVBoxLayout(finish_card)
        f_box.setContentsMargins(28, 28, 28, 28)
        f_box.setSpacing(16)
        f_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        success_icon = QLabel("✓")
        success_icon.setFixedSize(54, 54)
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_icon.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        success_icon.setStyleSheet(
            "background: #ECFDF5; color: #059669; border: 2px solid #A7F3D0; border-radius: 27px;"
        )
        f_box.addWidget(success_icon)

        succ_title = QLabel("Devices Connected Successfully")
        succ_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        succ_title.setStyleSheet("color: #0D1829; border: none;")
        succ_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_box.addWidget(succ_title)

        self._finish_summary = QLabel("")
        self._finish_summary.setWordWrap(True)
        self._finish_summary.setFont(QFont("Segoe UI", 10))
        self._finish_summary.setStyleSheet("color: #475569; border: none; line-height: 140%;")
        self._finish_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_box.addWidget(self._finish_summary)

        f_box.addStretch(1)
        lay.addWidget(finish_card, 1)
        return page

    def _platforms(self) -> list[PlatformRow]:
        return [
            PlatformRow("havells", "Havells Sync", True, [("username", "Email / Mobile", "Registered Havells Sync email or mobile number", False), ("password", "Password", "Havells Sync account password", True), ("home_id", "Home ID (Optional)", "Optional specific Havells home ID", False)]),
            PlatformRow("atomberg", "Atomberg Home", True, [("api_key", "API Key", "Atomberg developer API key", False), ("refresh_token", "Refresh Token", "Atomberg refresh token", True)]),
            PlatformRow("hue", "Philips Hue", True, [("bridge_ip", "Bridge IP Address", "Optional - bridge IP address", False), ("api_key", "API Key / Token", "Optional developer API key", False)]),
            PlatformRow("kasa", "TP-Link Kasa / Tapo", True, [("host", "Device IP / Host", "Optional - leave empty to scan local network", False), ("username", "Username", "Optional cloud username", False), ("password", "Password", "Optional cloud password", True)]),
            PlatformRow("daikin", "Daikin Smart AC", True, [("ip", "AC IP Address", "Optional local IP of AC unit", False), ("username", "Daikin Username", "Optional cloud account username", False), ("password", "Password", "Optional cloud password", True)]),
            PlatformRow("tuya", "Tuya / Smart Life", True, [("access_id", "Access ID / Client ID", "Tuya IoT platform developer ID", False), ("secret", "Access Secret / Client Secret", "Tuya IoT access secret key", True)]),
            PlatformRow("lg", "LG ThinQ", True, [("username", "Email / Username", "LG ThinQ account email", False), ("password", "Password", "LG ThinQ password", True)]),
            PlatformRow("nest", "Nest / Google Home", True, [("project_id", "Project ID", "Nest device access project ID", False), ("client_secret", "Client Secret", "Nest OAuth client secret", True)]),
            PlatformRow("smartthings", "Samsung SmartThings", True, [("token", "Access Token", "SmartThings personal access token", True)]),
        ]

    def _choose_provider(self, key: str, label: str):
        self._provider_key = key
        self._provider_label = label
        for card in self._platform_buttons:
            is_selected = card.objectName() == f"PlatformCard_{key}"
            if is_selected:
                card.setStyleSheet(
                    """
                    QFrame {
                        background: #F0F9FF;
                        border: 2px solid #0284C7;
                        border-radius: 14px;
                    }
                    """
                )
            else:
                card.setStyleSheet(
                    """
                    QFrame {
                        background: #FFFFFF;
                        border: 1.5px solid #E2E8F0;
                        border-radius: 14px;
                    }
                    QFrame:hover {
                        background: #F8FAFC;
                        border: 1.5px solid #38BDF8;
                    }
                    """
                )
        self._build_auth_form()
        self._stack.setCurrentIndex(1)
        self._sync_buttons()

    def _build_auth_form(self):
        while self._auth_form.count():
            item = self._auth_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._fields.clear()
        if not self._provider_key:
            self._auth_desc.setText("Select a platform to build the right authentication form.")
            return

        self._auth_desc.setText(
            f"Enter your credentials for {self._provider_label}. Connections are saved locally and fully authenticated."
        )

        for key, label, placeholder, secret in next((p.auth_fields for p in self._platforms() if p.key == self._provider_key), []):
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            if secret:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._fields[key] = edit

            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            lbl.setStyleSheet("color: #0F172A; border: none;")
            self._auth_form.addRow(lbl, edit)

        self._account_label = QLineEdit()
        self._account_label.setPlaceholderText(f"Example: {self._provider_label} Hub, Living Room")
        lbl_acc = QLabel("Device Label")
        lbl_acc.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        lbl_acc.setStyleSheet("color: #0F172A; border: none;")
        self._auth_form.addRow(lbl_acc, self._account_label)

    def _build_scan_results(self):
        while self._scan_list.count():
            item = self._scan_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._checks.clear()
        devices = self._preview.get("devices", [])
        if not devices:
            no_lbl = QLabel("No devices discovered. Verify your credentials or ensure hardware is powered on.")
            no_lbl.setFont(QFont("Segoe UI", 10))
            no_lbl.setStyleSheet("color: #64748B; padding: 20px 0;")
            self._scan_list.addWidget(no_lbl)
            self._scan_list.addStretch(1)
            return

        for device in devices:
            d_card = QFrame()
            d_card.setStyleSheet(
                """
                QFrame {
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                }
                """
            )
            d_lay = QHBoxLayout(d_card)
            d_lay.setContentsMargins(14, 10, 14, 10)
            d_lay.setSpacing(12)

            box = QCheckBox(f"{device['name']}")
            box.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            box.setChecked(True)
            box.setStyleSheet(
                """
                QCheckBox {
                    color: #0F172A;
                    spacing: 8px;
                    border: none;
                    background: transparent;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 1.5px solid #CBD5E1;
                    background: #FFFFFF;
                }
                QCheckBox::indicator:checked {
                    background: #0284C7;
                    border-color: #0284C7;
                }
                """
            )
            d_lay.addWidget(box, 1)

            room_lbl = QLabel(f"{device.get('room', 'Home')}  •  {device.get('manufacturer', self._provider_label)}")
            room_lbl.setFont(QFont("Segoe UI", 9))
            room_lbl.setStyleSheet("color: #64748B; border: none; background: transparent;")
            d_lay.addWidget(room_lbl)

            self._scan_list.addWidget(d_card)
            self._checks.append((str(device["external_id"]), box))
        self._scan_list.addStretch(1)

    def _go_next(self):
        idx = self._stack.currentIndex()
        if idx == 0:
            if not self._provider_key:
                return
            self._stack.setCurrentIndex(1)
        elif idx == 1:
            if not self._provider_key:
                return
            credentials = {k: e.text().strip() for k, e in self._fields.items()}
            try:
                self._preview = self._service.preview_discovery(self._provider_key, credentials)
            except Exception as exc:
                self._auth_desc.setText(f"❌ Authentication failed: {exc}")
                self._auth_desc.setStyleSheet("color: #DC2626; font-weight: bold; border: none;")
                return
            self._scan_bar.setValue(100)
            self._scan_label.setText("Discovered Devices")
            self._build_scan_results()
            self._stack.setCurrentIndex(2)
        elif idx == 2:
            selected = [ext_id for ext_id, check in self._checks if check.isChecked()]
            self._result = {
                "provider_key": self._provider_key,
                "account_label": self._account_label.text().strip() or self._provider_label,
                "credentials": {k: e.text().strip() for k, e in self._fields.items()},
                "selected_external_ids": selected,
            }
            self._finish_summary.setText(
                f"{len(selected)} device(s) selected from {self._provider_label}.\n"
                "Connected devices are stored locally and will immediately appear under MY DEVICES."
            )
            self._stack.setCurrentIndex(3)
        else:
            self.accept()
        self._sync_buttons()

    def _go_back(self):
        idx = self._stack.currentIndex()
        if idx > 0:
            self._stack.setCurrentIndex(idx - 1)
        self._sync_buttons()

    def _sync_buttons(self):
        idx = self._stack.currentIndex()
        self._back_btn.setEnabled(idx > 0)
        self._next_btn.setText("Connect Devices" if idx == 2 else "Finish" if idx == 3 else "Next →")
        self._next_btn.setEnabled(True if idx != 0 else bool(self._provider_key))

        # Update step pills
        for i, lbl in enumerate(self._step_labels):
            if i == idx:
                lbl.setStyleSheet(
                    "background: #0284C7; color: #FFFFFF; border-radius: 14px; font-weight: bold;"
                )
            elif i < idx:
                lbl.setStyleSheet(
                    "background: #E0F2FE; color: #0284C7; border-radius: 14px; font-weight: bold;"
                )
            else:
                lbl.setStyleSheet(
                    "background: #F1F5F9; color: #94A3B8; border-radius: 14px; font-weight: 500;"
                )


class _DeviceTile(ClickableFrame):
    action_requested = pyqtSignal(str, str, dict)
    select_requested = pyqtSignal(str)

    def __init__(self, device: dict[str, Any], parent=None):
        super().__init__(parent)
        self.device = device
        self.setObjectName("DeviceTileFrame")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(180)
        self.setMaximumHeight(194)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        # Header Row (Power Button in top right)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addStretch(1)
        
        self.power_btn = QPushButton("⏻")
        self.power_btn.setFixedSize(26, 26)
        self.power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_btn.setFont(QFont("Segoe UI", 10))
        
        is_on = bool(device.get("is_on"))
        self.power_btn.clicked.connect(lambda: self.action_requested.emit(str(self.device.get("id", "")), "power", {"is_on": not is_on}))
        header_row.addWidget(self.power_btn)
        lay.addLayout(header_row)
        
        # Product Image Center Container
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setFixedHeight(58)
        
        kind = str(device.get("device_type", "device")).lower()
        img_path = f"assets/{kind}.jpg"
        from pathlib import Path
        if Path(img_path).exists():
            pix = QPixmap(img_path).scaled(88, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img_lbl.setPixmap(pix)
        else:
            self.img_lbl.setText(self._glyph(kind))
            self.img_lbl.setFont(QFont("Segoe UI", 18))
            self.img_lbl.setStyleSheet("color: #ffffff;")
        lay.addWidget(self.img_lbl)
        
        # Device details
        self.name_lbl = QLabel(str(device.get("name", "Device")))
        self.name_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.name_lbl.setStyleSheet("color: #ffffff;")
        
        self.sub_lbl = QLabel(str(device.get("manufacturer", "")))
        self.sub_lbl.setFont(QFont("Segoe UI", 8))
        self.sub_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        
        lay.addWidget(self.name_lbl)
        lay.addWidget(self.sub_lbl)
        
        # Controls area
        self._control_area = QVBoxLayout()
        self._control_area.setSpacing(3)
        self._control_area.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self._control_area)
        self._build_controls()
        
        self.set_active(False)

    def _glyph(self, kind: str) -> str:
        return {"fan": "🌀", "light": "💡", "ac": "❄️", "tv": "📺", "plug": "🔌", "sensor": "📡", "curtain": "🪟", "vacuum": "🧹"}.get(kind, "⚙️")

    def _make_slider(self, minv: int, maxv: int, value: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minv, maxv)
        slider.setValue(value)
        slider.setCursor(Qt.CursorShape.SplitHCursor)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: rgba(255, 255, 255, 0.1);
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: #00e5ff;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #ffffff;
                width: 10px;
                height: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
            }}
        """)
        return slider

    def _build_controls(self):
        kind = str(self.device.get("device_type", "device")).lower()
        is_on = bool(self.device.get("is_on"))
        traits = self.device.get("traits") if isinstance(self.device.get("traits"), dict) else {}
        
        if kind == "fan":
            current_speed = traits.get("speed", 4)
            try:
                current_speed = int(current_speed)
            except Exception:
                current_speed = 4
                
            self.val_lbl = QLabel(f"Speed {current_speed}" if is_on else "Off")
            self.val_lbl.setFont(QFont("Segoe UI", 8))
            self.val_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
            self._control_area.addWidget(self.val_lbl)
            
            # Segment Speed Indicators
            seg_row = QHBoxLayout()
            seg_row.setSpacing(4)
            seg_row.addStretch(0)
            for s in range(1, 6):
                seg = QFrame()
                seg.setFixedHeight(5)
                seg.setFixedWidth(24)
                if is_on and s <= current_speed:
                    seg.setStyleSheet("background: #00e5ff; border-radius: 2.5px;")
                else:
                    seg.setStyleSheet("background: rgba(255, 255, 255, 0.15); border-radius: 2.5px;")
                seg_row.addWidget(seg)
            seg_row.addStretch(1)
            self._control_area.addLayout(seg_row)
            
        elif kind == "light":
            try:
                current_brightness = int(traits.get("brightness", 70))
            except Exception:
                current_brightness = 70
            self.val_lbl = QLabel(f"Brightness {current_brightness}%" if is_on else "Off")
            self.val_lbl.setFont(QFont("Segoe UI", 8))
            self.val_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
            self._control_area.addWidget(self.val_lbl)
            
        elif kind == "tv":
            status_row = QHBoxLayout()
            on_lbl = QLabel("On" if is_on else "Off")
            on_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            on_lbl.setStyleSheet(f"color: {GREEN};" if is_on else f"color: {TEXT_DIM};")
            status_row.addWidget(on_lbl)
            
            if is_on:
                try:
                    current_vol = int(traits.get("volume", 18))
                except Exception:
                    current_vol = 18
                vol_lbl = QLabel(f"Volume {current_vol}")
                vol_lbl.setFont(QFont("Segoe UI", 8))
                vol_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
                status_row.addWidget(vol_lbl)
                status_row.addStretch(1)
                self._control_area.addLayout(status_row)
                
                # Volume track slider
                self.slider = self._make_slider(0, 100, current_vol)
                self.slider.valueChanged.connect(lambda value: self.action_requested.emit(str(self.device.get("id", "")), "volume", {"volume": value}))
                self._control_area.addWidget(self.slider)
            else:
                status_row.addStretch(1)
                self._control_area.addLayout(status_row)
                
        elif kind == "ac":
            try:
                current_temp = int(traits.get("temperature", 24))
            except Exception:
                current_temp = 24
            temp_lbl = QLabel(f"{current_temp}°C" if is_on else "Off")
            temp_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            temp_lbl.setStyleSheet("color: #7bd3f7;" if is_on else f"color: {TEXT_DIM};")
            self._control_area.addWidget(temp_lbl)
            
            if is_on:
                tags_row = QHBoxLayout()
                tags_row.setSpacing(6)
                cool_lbl = QLabel("❄️ Cool")
                cool_lbl.setFont(QFont("Segoe UI", 8))
                cool_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 2px 6px;")
                
                fan_lbl = QLabel("🌀 Fan Auto")
                fan_lbl.setFont(QFont("Segoe UI", 8))
                fan_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 2px 6px;")
                
                tags_row.addWidget(cool_lbl)
                tags_row.addWidget(fan_lbl)
                tags_row.addStretch(1)
                self._control_area.addLayout(tags_row)
                
        elif kind == "plug":
            self.val_lbl = QLabel("On" if is_on else "Off")
            self.val_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            self.val_lbl.setStyleSheet(f"color: {GREEN};" if is_on else f"color: {TEXT_DIM};")
            self._control_area.addWidget(self.val_lbl)
            
        else:
            self._control_area.addWidget(QLabel("No additional controls."))

    def set_active(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QFrame#DeviceTileFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #12141d, stop:1 #08090e);
                    border: 1.5px solid {ACCENT};
                    border-radius: 18px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#DeviceTileFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f111a, stop:1 #07080b);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 18px;
                }}
                QFrame#DeviceTileFrame:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141726, stop:1 #0a0b12);
                    border: 1px solid rgba(0, 229, 255, 0.35);
                }}
            """)
            
        is_on = bool(self.device.get("is_on"))
        if is_on:
            self.power_btn.setStyleSheet("QPushButton { color: #37ff5f; background: rgba(55, 255, 95, 0.08); border: 1px solid rgba(55, 255, 95, 0.25); border-radius: 13px; } QPushButton:hover { background: rgba(55, 255, 95, 0.15); }")
        else:
            self.power_btn.setStyleSheet("QPushButton { color: rgba(255, 255, 255, 0.4); background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 13px; } QPushButton:hover { border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.06); }")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            device_id = self.device.get("id")
            if device_id is None:
                return
            self.select_requested.emit(str(device_id))


class BrahmaHomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = SmartHomeService()
        self._selected_device_id: str | None = None
        self._voice_state = "Listening"
        self._voice_phase = 0
        self._drawer_anim = None
        self._device_tiles: list[_DeviceTile] = []
        self._activity_items: list[dict[str, Any]] = []
        self._device_columns_cached = 0

        self.setObjectName("BrahmaHomePageModern")
        self.setStyleSheet(f"QWidget#BrahmaHomePageModern {{ background: transparent; }} QScrollArea {{ background: transparent; border: none; }}")

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        self._main_frame = QFrame()
        self._main_frame.setStyleSheet(
            "QFrame {"
            "background: transparent;"
            "border: none;"
            "}"
        )
        main_lay = QVBoxLayout(self._main_frame)
        main_lay.setContentsMargins(20, 20, 20, 20)
        main_lay.setSpacing(14)
        root.addWidget(self._main_frame, 1)

        self._build_header(main_lay)

        # Split layout for body: Devices (Left) + Recent Activity Feed (Right)
        self._body_layout = QHBoxLayout()
        self._body_layout.setSpacing(16)
        
        # Left side: Devices container
        self._left_container = QWidget()
        self._left_lay = QVBoxLayout(self._left_container)
        self._left_lay.setContentsMargins(0, 0, 0, 0)
        self._left_lay.setSpacing(10)
        self._build_my_devices(self._left_lay)
        self._body_layout.addWidget(self._left_container, 3)
        
        # Recent Activity panel
        self._right_container = QFrame()
        self._right_container.setObjectName("ActivityPanel")
        self._right_container.setStyleSheet(f"""
            QFrame#ActivityPanel {{
                background: rgba(10, 10, 10, 0.4);
                border: 1px solid rgba(0, 229, 255, 0.4);
                border-radius: 16px;
            }}
            QFrame#ActivityPanel:hover {{
                border: 1px solid rgba(0, 229, 255, 0.9);
                background: rgba(0, 229, 255, 0.08);
            }}
        """)
        self._right_lay = QVBoxLayout(self._right_container)
        self._right_lay.setContentsMargins(16, 16, 16, 16)
        self._right_lay.setSpacing(12)
        
        act_title = QLabel("RECENT ACTIVITY")
        act_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        act_title.setStyleSheet(f"color: {TEXT}; letter-spacing: 1px;")
        self._right_lay.addWidget(act_title)
        
        act_scroll = QScrollArea()
        act_scroll.setWidgetResizable(True)
        act_scroll.setFrameShape(QFrame.Shape.NoFrame)
        act_scroll.setStyleSheet("background: transparent; border: none;")
        
        act_host = QWidget()
        act_host.setStyleSheet("background: transparent;")
        self._activity_list = QVBoxLayout(act_host)
        self._activity_list.setContentsMargins(0, 0, 0, 0)
        self._activity_list.setSpacing(8)
        self._activity_list.addStretch(1)
        
        act_scroll.setWidget(act_host)
        self._right_lay.addWidget(act_scroll, 1)
        
        # Link button: View All Activity
        self._view_all_act_btn = QPushButton("View All Activity  >")
        self._view_all_act_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._view_all_act_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {ACCENT}; border: none; font-size: 11px; font-weight: bold; text-align: left; padding-left: 4px; }} QPushButton:hover {{ color: #ff6b6b; }}")
        self._right_lay.addWidget(self._view_all_act_btn)
        
        self._body_layout.addWidget(self._right_container, 1)
        main_lay.addLayout(self._body_layout, 1)

        self._drawer = self._build_drawer()
        self._drawer.hide()

        self._refresh()

    def refresh(self):
        self._refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _section_card(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(_panel_style(32))
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        head = QLabel(title)
        head.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        head.setStyleSheet(f"color: {TEXT}; letter-spacing: 1px;")
        lay.addWidget(head)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.08);")
        lay.addWidget(line)
        return frame

    def _build_header(self, lay: QVBoxLayout):
        row = QHBoxLayout()
        row.setSpacing(12)
        text = QVBoxLayout()
        title = QLabel("BRAHMA EVO HOME")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Black))
        title.setStyleSheet(f"color: {TEXT}; letter-spacing: 1px;")
        subtitle = QLabel("Control your smart home with Brahma Evo.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {TEXT_DIM};")
        text.addWidget(title)
        text.addWidget(subtitle)
        row.addLayout(text, 1)
        self._status_chip = QLabel()
        self._status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_chip.setStyleSheet(f"QLabel {{ background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 6px 14px; min-width: 110px; }}")
        row.addWidget(self._status_chip)
        self._voice_button = QPushButton("▮▮")
        self._voice_button.setFixedSize(48, 48)
        self._voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_button.setStyleSheet(f"QPushButton {{ background: rgba(255, 255, 255, 0.02); color: {TEXT}; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; font-size: 16px; }} QPushButton:hover {{ border: 1px solid {ACCENT}; background: rgba(0, 229, 255,0.08); }}")
        self._voice_button.clicked.connect(self._toggle_voice_mode)
        row.addWidget(self._voice_button)
        lay.addLayout(row)

    def _build_voice_card(self, lay: QVBoxLayout):
        self._voice_frame = QFrame()
        self._voice_frame.setStyleSheet(_panel_style(36))
        vf = QHBoxLayout(self._voice_frame)
        vf.setContentsMargins(18, 16, 18, 16)
        vf.setSpacing(16)
        self._mic_orb = QLabel("🎤")
        self._mic_orb.setFixedSize(86, 86)
        self._mic_orb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mic_orb.setFont(QFont("Segoe UI", 26))
        self._mic_orb.setStyleSheet(f"QLabel {{ background: rgba(0, 229, 255,0.12); color: {TEXT}; border: 2px solid rgba(0, 229, 255,0.55); border-radius: 43px; }}")
        vf.addWidget(self._mic_orb)
        middle = QVBoxLayout()
        self._voice_state_lbl = QLabel("Listening...")
        self._voice_state_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._voice_state_lbl.setStyleSheet(f"color: {TEXT};")
        self._voice_cmd_lbl = QLabel('"Turn bedroom fan to speed 4"')
        self._voice_cmd_lbl.setStyleSheet(f"color: {TEXT_MED};")
        middle.addWidget(self._voice_state_lbl)
        middle.addWidget(self._voice_cmd_lbl)
        vf.addLayout(middle, 1)
        self._wave = QHBoxLayout()
        self._wave.setSpacing(3)
        self._wave_bars: list[QFrame] = []
        for _ in range(36):
            bar = QFrame()
            bar.setFixedSize(4, 12)
            bar.setStyleSheet("background: rgba(0, 229, 255,0.20); border-radius: 2px;")
            self._wave.addWidget(bar, alignment=Qt.AlignmentFlag.AlignVCenter)
            self._wave_bars.append(bar)
        vf.addLayout(self._wave)
        lay.addWidget(self._voice_frame)

    def _build_my_devices(self, lay: QVBoxLayout):
        header = QHBoxLayout()
        title = QLabel("MY DEVICES")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch(1)
        self._add_btn = QPushButton("+ Add Device")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setFixedHeight(38)
        self._add_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT}; border: 1px solid {ACCENT}; border-radius: 12px; padding: 0 14px; }} QPushButton:hover {{ background: rgba(0, 229, 255,0.10); }}")
        self._add_btn.clicked.connect(self._open_add_device)
        header.addWidget(self._add_btn)
        lay.addLayout(header)

        self._empty_state = QFrame()
        self._empty_state.setObjectName("EmptyStateCard")
        self._empty_state.setStyleSheet(f"""
            QFrame#EmptyStateCard {{
                background: rgba(10, 10, 10, 0.4);
                border: 1px solid rgba(0, 229, 255, 0.4);
                border-radius: 16px;
            }}
            QFrame#EmptyStateCard:hover {{
                border: 1px solid rgba(0, 229, 255, 0.9);
                background: rgba(0, 229, 255, 0.08);
            }}
        """)
        empty_lay = QVBoxLayout(self._empty_state)
        empty_lay.setContentsMargins(28, 32, 28, 32)
        empty_lay.setSpacing(10)
        empty_title = QLabel("No devices added.")
        empty_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        empty_title.setStyleSheet(f"color: {TEXT}; background: transparent; border: none;")
        empty_sub = QLabel("Add a device to start controlling your home.")
        empty_sub.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")
        empty_lay.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignHCenter)
        empty_lay.addWidget(empty_sub, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._empty_add_btn = QPushButton("Add Device")
        self._empty_add_btn.setFixedSize(150, 42)
        self._empty_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._empty_add_btn.setStyleSheet(f"QPushButton {{ background: rgba(0, 229, 255,0.12); color: {TEXT}; border: 1px solid {ACCENT}; border-radius: 12px; }} QPushButton:hover {{ background: rgba(0, 229, 255,0.18); }}")
        self._empty_add_btn.clicked.connect(self._open_add_device)
        empty_lay.addWidget(self._empty_add_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self._empty_state)

        self._device_scroll = QScrollArea()
        self._device_scroll.setWidgetResizable(True)
        self._device_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._device_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._device_content = QWidget()
        self._device_content.setStyleSheet("background: transparent;")
        self._device_grid = QGridLayout(self._device_content)
        self._device_grid.setContentsMargins(0, 0, 0, 0)
        self._device_grid.setHorizontalSpacing(12)
        self._device_grid.setVerticalSpacing(12)
        self._device_scroll.setWidget(self._device_content)
        lay.addWidget(self._device_scroll, 1)

    def _build_voice_control_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("VoiceControlCard")
        frame.setStyleSheet(f"""
            QFrame#VoiceControlCard {{
                background: rgba(10, 10, 10, 0.4);
                border: 1px solid rgba(0, 229, 255, 0.4);
                border-radius: 16px;
            }}
            QFrame#VoiceControlCard:hover {{
                border: 1px solid rgba(0, 229, 255, 0.9);
                background: rgba(0, 229, 255, 0.08);
            }}
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        
        left = QVBoxLayout()
        left.setSpacing(6)
        
        title = QLabel("VOICE CONTROL")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; letter-spacing: 1px;")
        left.addWidget(title)
        
        wake_lay = QVBoxLayout()
        wake_lay.setSpacing(2)
        lbl = QLabel("Wake word")
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color: {TEXT_DIM};")
        
        word = QLabel("Brahma Evo")
        word.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        word.setStyleSheet(f"color: {ACCENT};")
        
        wake_lay.addWidget(lbl)
        wake_lay.addWidget(word)
        left.addLayout(wake_lay)
        lay.addLayout(left, 1)
        
        # Micro wave button on right
        mic_btn = QPushButton("🎙️")
        mic_btn.setFixedSize(38, 38)
        mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mic_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 229, 255,0.08);
                color: {TEXT};
                border: 1px solid rgba(0, 229, 255,0.3);
                border-radius: 19px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(0, 229, 255,0.18);
                border: 1px solid {ACCENT};
            }}
        """)
        mic_btn.clicked.connect(self._toggle_voice_mode)
        lay.addWidget(mic_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        return frame

    def _build_drawer(self) -> QFrame:
        drawer = QFrame(self)
        drawer.setObjectName("DetailsDrawerFrame")
        drawer.setStyleSheet("""
            QFrame#DetailsDrawerFrame {
                background: rgba(8, 9, 13, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }
        """)
        drawer.setGeometry(0, 0, 0, 0)
        lay = QVBoxLayout(drawer)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        
        top = QHBoxLayout()
        title = QLabel("DEVICE DETAILS")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT};")
        top.addWidget(title)
        top.addStretch(1)
        
        close_btn = QPushButton("X")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self._close_drawer)
        close_btn.setStyleSheet(_soft_button_style())
        top.addWidget(close_btn)
        lay.addLayout(top)
        
        card_style = """
            QFrame {
                background: rgba(13, 15, 19, 235);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """
        
        # 1. Name Card
        self._name_card = QFrame()
        self._name_card.setStyleSheet(card_style)
        nc_lay = QVBoxLayout(self._name_card)
        nc_lay.setContentsMargins(14, 14, 14, 14)
        self._drawer_name = QLabel("")
        self._drawer_name.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._drawer_name.setStyleSheet("color: #ffffff; border: none;")
        nc_lay.addWidget(self._drawer_name)
        lay.addWidget(self._name_card)
        
        # 2. Meta Card
        self._meta_card = QFrame()
        self._meta_card.setStyleSheet(card_style)
        mc_lay = QVBoxLayout(self._meta_card)
        mc_lay.setContentsMargins(14, 14, 14, 14)
        self._drawer_meta = QLabel("")
        self._drawer_meta.setStyleSheet("border: none;")
        mc_lay.addWidget(self._drawer_meta)
        lay.addWidget(self._meta_card)
        
        # 3. State Card
        self._state_card = QFrame()
        self._state_card.setStyleSheet(card_style)
        sc_lay = QVBoxLayout(self._state_card)
        sc_lay.setContentsMargins(14, 14, 14, 14)
        self._drawer_state = QLabel("")
        self._drawer_state.setStyleSheet("border: none;")
        sc_lay.addWidget(self._drawer_state)
        lay.addWidget(self._state_card)
        
        # 4. Info Card
        self._info_card = QFrame()
        self._info_card.setStyleSheet(card_style)
        ic_lay = QVBoxLayout(self._info_card)
        ic_lay.setContentsMargins(14, 14, 14, 14)
        self._drawer_info = QLabel("")
        self._drawer_info.setStyleSheet("border: none;")
        ic_lay.addWidget(self._drawer_info)
        lay.addWidget(self._info_card)
        
        lay.addStretch(1)
        
        self._drawer_actions = QHBoxLayout()
        self._drawer_actions.setSpacing(8)
        lay.addLayout(self._drawer_actions)
        return drawer

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._drawer.isVisible():
            width = min(390, max(330, int(self.width() * 0.28)))
            self._drawer.setGeometry(self.width() - width - 12, 12, width, self.height() - 24)
        self._reflow_devices()
        
        pass

    def _device_columns(self) -> int:
        viewport = self._device_scroll.viewport().width() if hasattr(self, "_device_scroll") else 0
        available = max(1, viewport or self.width())
        if available >= 1240:
            return 4
        if available >= 980:
            return 3
        return 2

    def _reflow_devices(self):
        if not hasattr(self, "_device_grid"):
            return
        columns = self._device_columns()
        if columns == self._device_columns_cached:
            return
        self._device_columns_cached = columns
        self._refresh_devices(self._service.list_devices())

    def _animate_drawer(self, open_: bool):
        if self._drawer_anim and self._drawer_anim.state() == QPropertyAnimation.State.Running:
            self._drawer_anim.stop()
        current = self._drawer.geometry()
        width = min(360, max(300, int(self.width() * 0.28)))
        start = QRect(self.width() - 12, 12, 0, self.height() - 24) if not open_ else current
        end = QRect(self.width() - width - 12, 12, width, self.height() - 24) if open_ else QRect(self.width() - 12, 12, 0, self.height() - 24)
        if open_:
            self._drawer.show()
        self._drawer_anim = QPropertyAnimation(self._drawer, b"geometry", self)
        self._drawer_anim.setDuration(260)
        self._drawer_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._drawer_anim.setStartValue(start)
        self._drawer_anim.setEndValue(end)
        if not open_:
            self._drawer_anim.finished.connect(self._drawer.hide)
        self._drawer_anim.start()

    def _open_drawer(self, device: dict[str, Any]):
        self._selected_device_id = str(device.get("id", ""))
        self._drawer_name.setText(str(device.get("name", "Device")))
        
        self._drawer_meta.setText(f"""
            <div style='line-height: 140%;'>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Manufacturer:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{device.get('manufacturer', '')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Room:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{device.get('room', '')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Connection:</span> <span style='color: #35ff75; font-weight: bold; font-size: 10pt;'>Local</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Last Updated:</span> <span style='color: rgba(255,255,255,0.7); font-size: 10pt;'>now</span>
            </div>
        """)
        
        traits = device.get("traits") if isinstance(device.get("traits"), dict) else {}
        is_on = bool(device.get("is_on"))
        state_color = "#35ff75" if is_on else "rgba(255,255,255,0.4)"
        self._drawer_state.setText(f"""
            <div style='line-height: 140%;'>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Power:</span> <span style='color: {state_color}; font-weight: bold; font-size: 10pt;'>{'On' if is_on else 'Off'}</span>
            </div>
        """)
        
        self._drawer_info.setText(f"""
            <div style='line-height: 140%;'>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Firmware:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{traits.get('firmware', 'Current')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>MAC:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{traits.get('mac', 'Local')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>IP:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{traits.get('ip', 'Local')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Battery:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{traits.get('battery', 'N/A')}</span><br>
                <span style='color: rgba(255,255,255,0.45); font-size: 10pt;'>Power Consumption:</span> <span style='color: #ffffff; font-weight: bold; font-size: 10pt;'>{traits.get('energy_usage', traits.get('power_usage', 'N/A'))}</span>
            </div>
        """)
        
        while self._drawer_actions.count():
            item = self._drawer_actions.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for text, slot in (("Rename", self._rename_selected), ("Restart", self._restart_selected), ("Forget", self._forget_selected)):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(slot)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.03);
                    color: {TEXT};
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background: rgba(0, 229, 255, 0.08);
                    border: 1px solid {ACCENT};
                    color: #ffffff;
                }}
            """)
            self._drawer_actions.addWidget(btn)
        self._animate_drawer(True)

    def _close_drawer(self):
        self._animate_drawer(False)

    def _rename_selected(self):
        if not self._selected_device_id:
            return
        device = self._service.get_device(self._selected_device_id)
        if not device:
            return
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Device", "New name:", text=str(device.get("name", "")))
        if ok and new_name.strip():
            self._service.rename_device(self._selected_device_id, new_name.strip())
            self._refresh()

    def _restart_selected(self):
        if self._selected_device_id:
            self._service.restart_device(self._selected_device_id)
            self._refresh()

    def _forget_selected(self):
        if self._selected_device_id:
            self._service.forget_device(self._selected_device_id)
            self._selected_device_id = None
            self._close_drawer()
            self._refresh()

    def _refresh(self):
        devices = self._service.list_devices()
        self._refresh_devices(devices)
        self._refresh_activity()
        
        if devices:
            status_html = (
                "<div style='line-height: 1.3;'>"
                "<span style='color: rgba(255,255,255,0.4); font-size: 10px; font-weight: bold;'>SYSTEM</span><br/>"
                "<span style='color: #35ff75; font-size: 12px; font-weight: bold;'>●</span> "
                "<span style='color: #ffffff; font-size: 11px; font-weight: bold;'>Connected</span>"
                "</div>"
            )
        else:
            status_html = (
                "<div style='line-height: 1.3;'>"
                "<span style='color: rgba(255,255,255,0.4); font-size: 10px; font-weight: bold;'>SYSTEM</span><br/>"
                "<span style='color: #ffcc00; font-size: 12px; font-weight: bold;'>●</span> "
                "<span style='color: #ffffff; font-size: 11px; font-weight: bold;'>Ready</span>"
                "</div>"
            )
        self._status_chip.setText(status_html)
        self._empty_state.setVisible(not devices)
        self._device_scroll.setVisible(bool(devices))

    def _refresh_devices(self, devices: list[dict[str, Any]]):
        while self._device_grid.count():
            item = self._device_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._device_tiles.clear()
        
        # Reset row stretches
        for r in range(self._device_grid.rowCount() + 1):
            self._device_grid.setRowStretch(r, 0)
            
        if not devices:
            return
        columns = self._device_columns()
        self._device_columns_cached = columns
        for idx, device in enumerate(devices):
            tile = _DeviceTile(device)
            tile.select_requested.connect(self._on_tile_selected)
            tile.action_requested.connect(self._on_device_action)
            tile.set_active(str(device.get("id")) == self._selected_device_id)
            self._device_grid.addWidget(tile, idx // columns, idx % columns)
            self._device_tiles.append(tile)
            
        # Add stretch on the last row to absorb extra vertical space
        last_row = (len(devices) - 1) // columns + 1
        self._device_grid.setRowStretch(last_row, 1)

    def _refresh_activity(self):
        while self._activity_list.count():
            item = self._activity_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._activity_items = self._service.recent_activity(10)
        if not self._activity_items:
            empty = QLabel("No recent activity yet.")
            empty.setStyleSheet(f"color: {TEXT_DIM};")
            self._activity_list.addWidget(empty)
            self._activity_list.addStretch(1)
            return
            
        for row in self._activity_items:
            item = QFrame()
            item.setStyleSheet("QFrame { background: transparent; border: none; }")
            box = QHBoxLayout(item)
            box.setContentsMargins(4, 4, 4, 4)
            box.setSpacing(12)
            
            # Timestamp (e.g. 12:08 PM)
            time_str = QDateTime.fromMSecsSinceEpoch(int(row["created_at"])).toString("h:mm AP")
            time_lbl = QLabel(time_str)
            time_lbl.setFont(QFont("Segoe UI", 9))
            time_lbl.setStyleSheet(f"color: {TEXT_DIM}; min-width: 60px;")
            box.addWidget(time_lbl)
            
            # Icon Badge
            kind = str(row.get("device_type", "device")).lower()
            badge = QLabel(self._activity_glyph(kind))
            badge.setFixedSize(32, 32)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFont(QFont("Segoe UI", 11))
            
            badge_style = {
                "fan": "background: rgba(53, 255, 117, 0.08); color: #35ff75; border: 1px solid rgba(53, 255, 117, 0.25); border-radius: 16px;",
                "light": "background: rgba(255, 165, 0, 0.08); color: #ffa500; border: 1px solid rgba(255, 165, 0, 0.25); border-radius: 16px;",
                "ac": "background: rgba(123, 211, 247, 0.08); color: #7bd3f7; border: 1px solid rgba(123, 211, 247, 0.25); border-radius: 16px;",
                "tv": "background: rgba(0, 180, 216, 0.08); color: #00b4d8; border: 1px solid rgba(0, 180, 216, 0.25); border-radius: 16px;",
                "plug": "background: rgba(255, 255, 255, 0.05); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 16px;",
            }.get(kind, "background: rgba(255, 255, 255, 0.05); color: #ffffff; border-radius: 16px;")
            badge.setStyleSheet(badge_style)
            box.addWidget(badge)
            
            # Details Text
            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            title = QLabel(str(row["title"]))
            title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            title.setStyleSheet("color: #ffffff;")
            
            detail = QLabel(str(row["detail"]))
            detail.setFont(QFont("Segoe UI", 9))
            detail.setStyleSheet(f"color: {TEXT_DIM};")
            text_box.addWidget(title)
            text_box.addWidget(detail)
            
            box.addLayout(text_box, 1)
            self._activity_list.addWidget(item)
            
        self._activity_list.addStretch(1)

    def _activity_glyph(self, kind: str) -> str:
        return {"fan": "🌀", "light": "💡", "ac": "❄️", "tv": "📺", "plug": "🔌"}.get(kind, "⚙️")

    def _on_tile_selected(self, device_id: str):
        device = self._service.get_device(device_id)
        if not device:
            return
        self._selected_device_id = device_id
        for tile in self._device_tiles:
            tile.set_active(str(tile.device.get("id")) == device_id)
        self._open_drawer(device)

    def _on_device_action(self, device_id: str, action: str, payload: dict):
        try:
            self._service.execute_device_action(device_id, action, payload)
        except Exception:
            return
        self._refresh()
        device = self._service.get_device(device_id)
        if device:
            self._open_drawer(device)

    def _toggle_voice_mode(self):
        states = ["Idle", "Listening", "Thinking", "Executing", "Completed"]
        self._voice_phase = (self._voice_phase + 1) % len(states)
        self._voice_state = states[self._voice_phase]
        # Some UI paths may call this before voice widgets are built; guard access.
        if hasattr(self, "_voice_state_lbl") and isinstance(getattr(self, "_voice_state_lbl"), QLabel):
            try:
                self._voice_state_lbl.setText(f"{self._voice_state}...")
            except Exception:
                pass
        if hasattr(self, "_voice_state_small") and isinstance(getattr(self, "_voice_state_small"), QLabel):
            try:
                self._voice_state_small.setText(self._voice_state)
            except Exception:
                pass

    def _animate_voice(self):
        self._voice_phase += 1
        if hasattr(self, "_wave_bars") and self._wave_bars:
            for idx, bar in enumerate(self._wave_bars):
                height = 8 + int(18 * abs(((self._voice_phase + idx) % 14) - 7) / 7)
                bar.setFixedHeight(max(8, min(40, height)))
                bar.setStyleSheet(f"background: {'rgba(0, 229, 255,0.55)' if self._voice_state in ('Listening', 'Executing') else 'rgba(255,255,255,0.18)'}; border-radius: 2px;")
        if hasattr(self, "_voice_small_bars") and self._voice_small_bars:
            for idx, bar in enumerate(self._voice_small_bars):
                height = 6 + int(10 * abs(((self._voice_phase + idx) % 10) - 5) / 5)
                bar.setFixedHeight(max(6, min(24, height)))
                bar.setStyleSheet(f"background: {'rgba(0, 229, 255,0.35)' if self._voice_state in ('Listening', 'Executing') else 'rgba(255,255,255,0.15)'}; border-radius: 2px;")
        if hasattr(self, "_voice_cmd_lbl") and self._voice_cmd_lbl:
            self._voice_cmd_lbl.setText({"Idle": '"Brahma Evo"', "Listening": '"Turn bedroom fan to speed 4"', "Thinking": '"Understanding..."', "Executing": '"Applying command..."', "Completed": '"Done"'}.get(self._voice_state, '"Brahma Evo"'))
        if hasattr(self, "_mic_orb") and self._mic_orb:
            self._mic_orb.setText("🎙️" if self._voice_state in ("Listening", "Executing") else "🎙️")

    def _open_add_device(self):
        dialog = AddDeviceDialog(self._service, self.window())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.result_payload()
        provider_key = str(payload.get("provider_key", ""))
        selected = list(payload.get("selected_external_ids", []))
        if not provider_key or not selected:
            return
        creds = dict(payload.get("credentials", {}))
        label = str(payload.get("account_label", "Home"))
        try:
            self._service.connect_devices(provider_key, label, creds, selected)
        except Exception:
            return
        self._refresh()
