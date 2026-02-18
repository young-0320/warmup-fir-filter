# FIR  Filter 1D Idel Model
# 64bits 부동소수점 : 부호(1) + 지수(11) + 가수(52)
import math

MAX_ABS_H_COEFF = 1e6

# 필터 계수 입력 예외 처리
def _validate_h_coefficients(h: list[float]) -> None:
    # 빈 필터 계수
    if len(h) == 0:
        raise ValueError("Invalid h: h coefficients must not be empty.")

    for index, coeff in enumerate(h):
        # 무한대 계수
        if not math.isfinite(coeff):
            raise ValueError(
                f"Invalid h[{index}]={coeff}: h coefficients must be finite."
            )
        # 매우 큰 계수
        if abs(coeff) > MAX_ABS_H_COEFF:
            raise ValueError(
                f"Invalid h[{index}]={coeff}: |h| must be <= {MAX_ABS_H_COEFF}."
            )


def _validate_and_clamp_x(x: list[float]) -> list[float]:
    x_sat: list[float] = []
    for index, sample in enumerate(x):
        if not math.isfinite(sample):
            raise ValueError(f"Invalid x[{index}]={sample}: x must be finite.")
        x_sat.append(max(0.0, min(255.0, float(sample))))
    return x_sat


def fir_1d_ideal(x: list[float], h: list[float]) -> list[float]:
    _validate_h_coefficients(h)
    x_sat = _validate_and_clamp_x(x)

    N = len(x_sat)
    L = len(h)  # 필터 h의 길이
    center = L // 2

    y: list[float] = [0.0] * N

    for n in range(N):
        acc = 0.0  # Accumulator 
        for k in range(L):
            input_idx = n - k + center
            if 0 <= input_idx < N:
                acc += h[k] * x_sat[input_idx]

        # Ideal spec: output is pass-through float (no clamp)
        y[n] = acc

    return y
