# File: test_1d_ideal.py
# Role: fir_1d_ideal의 동작, 전처리 규칙, 예외 정책을 단위 테스트한다.
import pytest

from fir_1d.model.python.fir_1d_ref import MAX_ABS_H_COEFF, fir_1d_ideal


def test_same_mode_center_aligned_matches_manual_reference():
    x = [10, 20, 30, 40]
    h = [0.25, 0.5, 0.25]

    result = fir_1d_ideal(x, h)

    # center=1, zero-padding
    expected = [10.0, 20.0, 30.0, 27.5]
    assert result == pytest.approx(expected, abs=1e-12)


def test_output_length_equals_input_length_in_same_mode():
    x = [3, 7, 11, 15, 19]
    h = [0.1, 0.5, 0.3, 0.1]

    result = fir_1d_ideal(x, h)
    assert len(result) == len(x)


def test_input_preprocessing_round_half_up_then_clamp():
    x = [-1.2, 0.49, 0.5, 1.5, 254.6, 300.2]
    h = [1.0]

    result = fir_1d_ideal(x, h)

    # round-half-up -> [-1, 0, 1, 2, 255, 300], then clamp -> [0, 0, 1, 2, 255, 255]
    assert result == pytest.approx([0.0, 0.0, 1.0, 2.0, 255.0, 255.0], abs=1e-12)


def test_output_is_not_clamped():
    x = [255, 255]
    h = [5.0]

    result = fir_1d_ideal(x, h)
    assert result == pytest.approx([1275.0, 1275.0], abs=1e-12)


@pytest.mark.parametrize("bad_x", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_x_raises_value_error(bad_x):
    with pytest.raises(ValueError, match=r"x\[1\].*finite"):
        fir_1d_ideal([10, bad_x, 20], [1.0])


@pytest.mark.parametrize("bad_h", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_h_raises_value_error(bad_h):
    with pytest.raises(ValueError, match=r"h\[0\].*finite"):
        fir_1d_ideal([10, 20, 30], [bad_h])


def test_empty_h_raises_value_error():
    with pytest.raises(ValueError, match="must not be empty"):
        fir_1d_ideal([10, 20, 30], [])


def test_h_magnitude_above_limit_raises_value_error():
    with pytest.raises(ValueError, match=r"\|h\| must be <="):
        fir_1d_ideal([10, 20, 30], [MAX_ABS_H_COEFF + 1e-6])


def test_h_limit_boundaries_are_accepted():
    result = fir_1d_ideal([10, 20], [-8.0, 8.0])
    assert len(result) == 2
