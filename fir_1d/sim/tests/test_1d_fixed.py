import numpy as np
import pytest

from fir_1d.model.python.fir_1d_fixed_ref import fir_1d_fixed_golden


def test_same_mode_center_aligned_q412_exact_case():
    x = [10, 20, 30, 40]
    h = [0.25, 0.5, 0.25]

    result = fir_1d_fixed_golden(x, h)

    # Q4.12 exact taps [1024, 2048, 1024], bias rounding + right shift
    assert result.tolist() == [10, 20, 30, 28]


def test_input_preprocessing_round_half_up_then_clamp():
    x = [-1.2, 0.5, 1.5, 254.6, 300.2]
    h = [1.0]

    result = fir_1d_fixed_golden(x, h)
    assert result.tolist() == [0, 1, 2, 255, 255]


def test_output_saturates_high():
    x = [255, 255]
    h = [7.999755859375]

    result = fir_1d_fixed_golden(x, h)
    assert result.tolist() == [255, 255]


def test_output_saturates_low():
    x = [255, 255]
    h = [-8.0]

    result = fir_1d_fixed_golden(x, h)
    assert result.tolist() == [0, 0]


@pytest.mark.parametrize("bad_x", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_x_raises_value_error(bad_x):
    with pytest.raises(ValueError, match=r"x\[1\].*finite"):
        fir_1d_fixed_golden([10, bad_x, 20], [0.5])


@pytest.mark.parametrize("bad_h", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_h_raises_value_error(bad_h):
    with pytest.raises(ValueError, match=r"h\[0\].*finite"):
        fir_1d_fixed_golden([10, 20], [bad_h])


def test_empty_h_raises_value_error():
    with pytest.raises(ValueError, match="must not be empty"):
        fir_1d_fixed_golden([10, 20], [])


def test_invalid_coeff_bits_raises_value_error():
    with pytest.raises(ValueError, match="Invalid coeff_bits=12"):
        fir_1d_fixed_golden([10, 20], [0.5], coeff_bits=12)


@pytest.mark.parametrize(
    ("frac_bits", "acc_bits"),
    [
        (0, 32),
        (-1, 32),
        (12, 0),
        (12, -1),
    ],
)
def test_invalid_frac_or_acc_bits_raise_value_error(frac_bits, acc_bits):
    with pytest.raises(ValueError):
        fir_1d_fixed_golden([10, 20], [0.5], frac_bits=frac_bits, acc_bits=acc_bits)


def test_h_q412_upper_boundary_is_accepted():
    result = fir_1d_fixed_golden([10, 20], [7.999755859375])
    assert len(result) == 2


def test_h_q412_value_above_upper_boundary_raises():
    with pytest.raises(ValueError, match="out of Q-format real range"):
        fir_1d_fixed_golden([10, 20], [8.0])


def test_h_out_of_qrange_for_custom_format_raises():
    # coeff_bits=8, frac_bits=7 -> valid real range [-1.0, 0.9921875]
    with pytest.raises(ValueError, match="out of Q-format real range"):
        fir_1d_fixed_golden([10, 20], [1.0], frac_bits=7, coeff_bits=8)


def test_output_contract_dtype_length_and_range():
    x = [255, 255, 255, 255]
    h = [0.5, 0.25]

    result = fir_1d_fixed_golden(x, h)

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8
    assert len(result) == len(x)
    assert np.all((result >= 0) & (result <= 255))
