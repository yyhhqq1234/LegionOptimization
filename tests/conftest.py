"""pytest 根配置：把 src/ 放入 sys.path（与 pytest.ini pythonpath 双保险）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
