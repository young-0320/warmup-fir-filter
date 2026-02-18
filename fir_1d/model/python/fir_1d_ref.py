import math

# FIR  Filter 1D Idel Model
# 64bits 부동소수점 : 부호(1) + 지수(11) + 가수(52)
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


def fir_1d_ideal(x : list[int], h : list[float])->list[int]:
    _validate_h_coefficients(h)

    # 입력 x를 8-bit unsigned 범위(0~255)로 saturation
    x_sat = [max(0, min(255, sample)) for sample in x]
    N = len(x_sat)
    L = len(h)      # 필터 h의 길이
 
    center = L//2  

    y = [0] * N

    for n in range(N):
        acc = 0.0 # Accumulator
        for k in range(L):
            input_idx = n + (k - center)
            # 인덱스 경계 검사: x[n-k]가 유효한 범위인지 확인
            if 0 <= input_idx < N:
                pixel_val = x_sat[input_idx] # 유효 범위
            else:
                pixel_val = 0 

            acc += h[k] * pixel_val

        # 3. 출력 Saturation (하드웨어 출력 단)
        # 반올림 후 0~255 범위로 자름 (Clamping)
        y_val = int(round(acc))
        y[n] = max(0, min(255, y_val))
        
    return y
