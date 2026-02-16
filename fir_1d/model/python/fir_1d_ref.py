import math

# FIR  Filter 1D Idel Model
# 64bits 부동소수점 : 부호(1) + 지수(11) + 가수(52)
MAX_ABS_H_COEFF = 1e6
# TODO: 부동소수점의 너무 작은 값 0으로 클리핑하는 로직 추가
# 필터 계수 입력 예외 처리
def _validate_h_coefficients(h: list[float]) -> None:
    for index, coeff in enumerate(h):
        # 무한대 입력
        if not math.isfinite(coeff):
            raise ValueError(
                f"Invalid h[{index}]={coeff}: h coefficients must be finite."
            )
        # 매우 큰 값 입력
        if abs(coeff) > MAX_ABS_H_COEFF:
            raise ValueError(
                f"Invalid h[{index}]={coeff}: |h| must be <= {MAX_ABS_H_COEFF}."
            )


def fir_1d_ideal(x : list[int], h : list[float])->list:
    _validate_h_coefficients(h)

    # 입력 x를 8-bit unsigned 범위(0~255)로 saturation
    x_sat = [0 if sample < 0 else 255 if sample > 255 else sample for sample in x]

    N = len(x_sat)  # 입력 x의 길이
    L = len(h)      # 필터 h의 길이
    # M = L - 1     # 차수
    Ny = N + L - 1  # 출력 신호 길이 

    y = [0.0] * Ny

    for n in range(Ny):
        result = 0.0
        for k in range(L):
            # 인덱스 경계 검사: x[n-k]가 유효한 범위인지 확인
            if 0 <= n - k < N:
                result += h[k] * x_sat[n - k]
        y[n] = result
        
    return y
        
