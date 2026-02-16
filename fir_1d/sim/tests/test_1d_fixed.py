from fir_1d.model.python.fir_1d_fixed_ref import fir_1d_fixed_golden as FIR_1D_GOLDEN
from fir_1d.model.python.fir_1d_ref import fir_1d_ideal

import numpy as np
import pytest

class TestFir1DFixed:
    def setup_method(self):
        # Q1.7 real range: -1.0 ~ 0.9921875
        self.h_coeff = [0.1, 0.5, 0.3, 0.1]

    def test_fixed_full_scale_impulse_response(self):
        # Fixed model interprets input as 0~255 integer pixels.
        impulse = [255, 0, 0, 0]
        result = FIR_1D_GOLDEN(impulse, self.h_coeff)

        # h -> Q1.7 quantized: [13, 64, 38, 13]
        # output = (255 * h_q) >> 7 => [25, 127, 75, 25]
        expected = [25, 127, 75, 25]
        assert result[: len(expected)].tolist() == expected

    def test_fixed_matches_ideal_on_q17_exact_case(self):
        # h=[0.5, 0.5] is exactly representable in Q1.7 (64/128).
        x = [10, 20, 30, 40]
        h = [0.5, 0.5]

        fixed = FIR_1D_GOLDEN(x, h)
        ideal = fir_1d_ideal(x, h)

        expected = [int(v) for v in ideal[: len(x)]]
        assert fixed.tolist() == expected

    def test_x_nan_raises_value_error(self):
        with pytest.raises(ValueError, match="x\\[1\\]=nan"):
            FIR_1D_GOLDEN([10, np.nan, 20], [0.5])

    def test_x_inf_raises_value_error(self):
        with pytest.raises(ValueError, match="x\\[0\\]=inf"):
            FIR_1D_GOLDEN([np.inf, 10, 20], [0.5])

    def test_x_bankers_rounding_ties_to_even(self):
        x = [0.5, 1.5, 2.5, 3.5]
        h = [0.5]

        result = FIR_1D_GOLDEN(x, h)
        # x rounded by np.rint -> [0, 2, 2, 4], then *0.5
        expected = [0, 1, 1, 2]
        assert result.tolist() == expected

    def test_x_saturation_before_filtering(self):
        x = [-10, 300]
        h = [0.5]

        result = FIR_1D_GOLDEN(x, h)
        # x saturated to [0, 255], then *0.5
        expected = [0, 127]
        assert result.tolist() == expected

    def test_h_empty_raises_value_error(self):
        with pytest.raises(ValueError, match="must not be empty"):
            FIR_1D_GOLDEN([10, 20, 30], [])

    def test_h_nan_raises_value_error(self):
        with pytest.raises(ValueError, match="h\\[0\\]=nan"):
            FIR_1D_GOLDEN([10, 20, 30], [np.nan])

    # h 경계값 테스트
    def test_h_q17_boundaries_are_accepted(self):
        # Q1.7 boundaries: -1.0 and 127/128
        result = FIR_1D_GOLDEN([255, 255], [-1.0, 127 / 128])
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert len(result) == 2

    def test_h_above_q17_range_raises(self):
        with pytest.raises(ValueError, match="out of Q-format real range"):
            FIR_1D_GOLDEN([10, 20], [1.0])

    def test_h_below_q17_range_raises(self):
        with pytest.raises(ValueError, match="out of Q-format real range"):
            FIR_1D_GOLDEN([10, 20], [-1.01])

    def test_invalid_coeff_bits_raises(self):
        with pytest.raises(ValueError, match="Invalid coeff_bits=12"):
            FIR_1D_GOLDEN([10, 20], [0.5], coeff_bits=12)

    def test_negative_frac_bits_raises(self):
        with pytest.raises(ValueError):
            FIR_1D_GOLDEN([10, 20], [0.5], frac_bits=-1)

    def test_zero_acc_bits_raises(self):
        with pytest.raises(ValueError):
            FIR_1D_GOLDEN([10, 20], [0.5], acc_bits=0)

    # 출력 계약 테스트
    def test_output_contract_dtype_length_range(self):
        x = [255, 255, 255, 255]
        h = [127 / 128, 127 / 128]

        result = FIR_1D_GOLDEN(x, h)

        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert len(result) == len(x)
        assert np.all((result >= 0) & (result <= 255))
