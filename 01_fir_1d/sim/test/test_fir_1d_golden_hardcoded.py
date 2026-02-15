#!/usr/bin/env python3
"""
Hardcoded unit tests for model/python/fir_1d_ref.py.
"""

from __future__ import annotations

import math
import sys
import unittest     # 검증 라이브러리
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PYTHON_DIR = PROJECT_ROOT / "model" / "python"
if str(MODEL_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_PYTHON_DIR))

from fir_1d_fixed_ref import fir_1d_fixed_golden as FIR_1D_GOLDEN

