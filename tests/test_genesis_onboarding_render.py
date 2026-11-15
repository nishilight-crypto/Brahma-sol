import os
import sys
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont

app = QApplication.instance() or QApplication(sys.argv)

for font_name in ["segoeui.ttf", "segoeuib.ttf", "seguisym.ttf", "arial.ttf"]:
    fpath = Path("C:/Windows/Fonts") / font_name
    if fpath.exists():
        QFontDatabase.addApplicationFont(str(fpath))

app.setFont(QFont("Segoe UI", 9))

import genesis_onboarding
genesis_onboarding.QWebEngineView = None
from genesis_onboarding import GenesisOnboardingWindow

try:
    win = GenesisOnboardingWindow()
    win.show()
    app.processEvents()

    for step in [0, 1, 2, 5]:
        win._apply_step(step)
        app.processEvents()
        pix = win.grab()
        out_path = f"test_genesis_step{step}.png"
        pix.save(out_path)
        print(f"Saved {out_path}")

    win.close()
    print("ALL STEPS CAPTURED!")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
