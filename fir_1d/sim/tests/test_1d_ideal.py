# --- User draft (preserved) -----------------------------------------------
# # fir_1d_ref.py test code
# # unit test

import pytest

from fir_1d.model.python.fir_1d_ref import MAX_ABS_H_COEFF, fir_1d_ideal


@pytest.fixture
def h_coeff():
    return [0.1, 0.5, 0.3, 0.1]


def test_ideal_impulse_response(h_coeff):
    x_impulse = [1, 0, 0, 0]
    expected = h_coeff + [0.0] * (len(x_impulse) - 1)

    result = fir_1d_ideal(x_impulse, h_coeff)

    assert result == pytest.approx(expected, abs=1e-12)


def test_zero_input_returns_all_zeros(h_coeff):
    x = [0, 0, 0, 0, 0, 0]
    expected = [0.0] * (len(x) + len(h_coeff) - 1)

    result = fir_1d_ideal(x, h_coeff)

    assert result == pytest.approx(expected, abs=1e-12)


def test_output_length_matches(h_coeff):
    x = [3, -1, 2, 4, 0]

    result = fir_1d_ideal(x, h_coeff)

    assert len(result) == len(x) + len(h_coeff) - 1


def test_single_tap_filter_matches_saturated_input():
    x = [25, -15, 30, 300]
    h = [1.0]
    expected = [25, 0, 30, 255]

    result = fir_1d_ideal(x, h)

    assert result == pytest.approx(expected, abs=1e-12)


def test_single_sample_input_with_multi_tap_filter():
    x = [2]
    h = [0.1, 0.5, 0.3, 0.1]
    expected = [0.2, 1.0, 0.6, 0.2]

    result = fir_1d_ideal(x, h)

    assert result == pytest.approx(expected, abs=1e-12)


def test_mixed_negative_input():
    x = [1, -20, 5]
    h = [0.25, -0.75]
    expected = [0.25, -0.75, 1.25, -3.75]

    result = fir_1d_ideal(x, h)

    assert result == pytest.approx(expected, abs=1e-12)

# h 계수 유효성 검증
# bad_coeff에 nan, inf, -inf 값을 대입해가며 테스트
@pytest.mark.parametrize("bad_coeff", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_h_coeff_raises_value_error(bad_coeff):
    x = [1, 2, 3]
    h = [0.1, bad_coeff, 0.2]

    with pytest.raises(ValueError, match="finite"):
        fir_1d_ideal(x, h)


def test_overly_large_h_coeff_raises_value_error():
    x = [1, 2, 3]
    h = [MAX_ABS_H_COEFF + 1.0, 0.1]

    with pytest.raises(ValueError, match=r"\|h\| must be <="):
        fir_1d_ideal(x, h)


def test_empty_h_coeff_raises_value_error():
    x = [1, 2, 3]
    h = []

    with pytest.raises(ValueError, match="must not be empty"):
        fir_1d_ideal(x, h)
