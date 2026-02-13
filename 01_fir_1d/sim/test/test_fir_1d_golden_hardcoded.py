#!/usr/bin/env python3
"""Hardcoded unit tests for model/python/fir_1d_ref.py.


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

from fir_1d_ref import fir_1d_golden as FIR_1D_GOLDEN


def _assert_close_list(tc: unittest.TestCase, got: list[float], exp: list[float], abs_tol: float = 1e-12, rel_tol: float = 1e-12) -> None:
    """Assert two float lists are numerically close element-wise.

    Args:
        tc: unittest.TestCase 인스턴스(self). assert API 호출에 사용한다.
        got: 실제 출력 리스트.
        exp: 기대 출력 리스트(하드코딩 정답).
        abs_tol: 절대 허용오차. 0 근처 값 비교 안정성을 위해 사용한다.
        rel_tol: 상대 허용오차. 값 크기에 비례한 오차 허용에 사용한다.

    Note:
        본 파일은 Python golden self-test이므로 기본 허용오차를 1e-12로
        엄격하게 둔다. C++/RTL 비교 단계에서는 연산/표현 차이를 고려해
        완화하거나(bit-exact 정책이면 별도 기준 사용) 조정한다.
    """
    tc.assertEqual(len(got), len(exp), f"Length mismatch: got={len(got)} exp={len(exp)}")
    for idx, (g, e) in enumerate(zip(got, exp)):
        tc.assertTrue(
            math.isclose(g, e, abs_tol=abs_tol, rel_tol=rel_tol),
            msg=f"Mismatch at idx={idx}: got={g}, exp={e}",
        )


class TestFir1DGoldenHardcoded(unittest.TestCase):
    def test_impulse_response(self):
        x = [1.0, 0.0, 0.0]
        h = [2.0, 3.0]
        exp = [2.0, 3.0, 0.0, 0.0]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_single_tap_passthrough(self):
        x = [0.5, -1.0, 2.0]
        h = [1.0]
        exp = [0.5, -1.0, 2.0]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_two_tap_average(self):
        x = [1.0, 3.0, 5.0]
        h = [0.5, 0.5]
        exp = [0.5, 2.0, 4.0, 2.5]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_differentiator(self):
        x = [0.0, 1.0, 1.0, 2.0]
        h = [1.0, -1.0]
        exp = [0.0, 1.0, 0.0, 1.0, -2.0]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_three_tap_triangle(self):
        x = [1.0, 2.0]
        h = [1.0, 2.0, 1.0]
        exp = [1.0, 4.0, 5.0, 2.0]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_fractional_and_negative(self):
        x = [-1.0, 0.5]
        h = [0.25, -0.5, 1.0]
        exp = [-0.25, 0.625, -1.25, 0.5]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_all_zero_input(self):
        x = [0.0, 0.0]
        h = [1.0, 2.0, 3.0]
        exp = [0.0, 0.0, 0.0, 0.0]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)

    def test_step_response(self):
        x = [1.0, 1.0, 1.0, 1.0]
        h = [0.2, 0.3, 0.5]
        exp = [0.2, 0.5, 1.0, 1.0, 0.8, 0.5]
        got = FIR_1D_GOLDEN(x, h)
        _assert_close_list(self, got, exp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
