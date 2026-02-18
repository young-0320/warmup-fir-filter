# FIR  Filter 1D Fixed Golden Model_v1

# 기본 설정은 Q4.12 (coeff_bits=16, frac_bits=12)
# TODO : 내부 오버플로우 방어 로직
# TODO : 포멧 변경 인터페이스
import numpy as np


def fir_1d_fixed_golden(
    x,           
    h,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16
):
    """
    범용 1D FIR 필터 하드웨어 동작 시뮬레이션 모델
    
    Args:
        x: Grayscale 이미지 입력 픽셀 리스트 (0 ~ 255) 범위의 int
        h: 실수형 필터 계수 값 
        frac_bits: 계수 양자화를 위한 소수점 비트 (기본 12)
        acc_bits: 누산기 비트 폭 (기본 32)
        coeff_bits: 계수 비트 폭 (기본 16)
    
    Returns:
        y_out: 하드웨어 출력 값 (0 ~ 255)
    """
    dtype_int_map = {
      8: np.int8,
      16: np.int16,
      32: np.int32,
    }
    if coeff_bits not in dtype_int_map:
        valid_bits = ", ".join(str(bits) for bits in dtype_int_map)
        raise ValueError(
            f"Invalid coeff_bits={coeff_bits}. "
            f"Supported coeff_bits are: {valid_bits}."
        )
    if frac_bits <= 0:
        raise ValueError(f"Invalid frac_bits={frac_bits}. frac_bits must be > 0.")
    if acc_bits <= 0:
        raise ValueError(f"Invalid acc_bits={acc_bits}. acc_bits must be > 0.")
    dtype = dtype_int_map[coeff_bits]
    # 1. Parameter Calculation (하드웨어 제약사항)
    MAX_PIXEL = 255
    MIN_PIXEL = 0
    MIN_COEFF = -(1 << (coeff_bits - 1))
    MAX_COEFF = (1 << (coeff_bits - 1)) - 1
    SCALE = (1 << frac_bits)
    MIN_COEFF_REAL = MIN_COEFF / SCALE
    MAX_COEFF_REAL = MAX_COEFF / SCALE

    # 2. 필터 계수 데이터 무결성 확인
    if len(h) == 0:
        raise ValueError("Invalid h: h coefficients must not be empty.")
    for i, num in enumerate(h):
        if not np.isfinite(num):
            raise ValueError(
                f"h[{i}]={num} must be finite (no NaN/Inf)."
            )
        if num < MIN_COEFF_REAL or num > MAX_COEFF_REAL:
            raise ValueError(
                f"h[{i}]={num} out of Q-format real range "
                f"[{MIN_COEFF_REAL}, {MAX_COEFF_REAL}] "
                f"(coeff_bits={coeff_bits}, frac_bits={frac_bits})"
            )
    # 3. 입력 x 데이터 무결성 확인 + round-half-up + saturation(0 ~ 255)
    x_sat = []
    for i, sample in enumerate(x):
        if not np.isfinite(sample):
            raise ValueError(
                f"x[{i}]={sample} must be finite (no NaN/Inf)."
            )
        rounded = int(np.floor(float(sample) + 0.5))
        x_sat.append(
            MIN_PIXEL if rounded < MIN_PIXEL else MAX_PIXEL if rounded > MAX_PIXEL else rounded
        )

    # 4. 입력/계수를 내부 연산용 배열로 변환
    x = np.array(x_sat, dtype=np.uint8)
    h = np.array(h, dtype=np.float64)

    # 5. h 실수 원소 -> 고정소수점 정수 변환(계수 먼저 양자화)
    # 알고리즘 시작

    h_fixed = np.rint(h * SCALE)                      # 원소별 반올림
    h_fixed = np.clip(h_fixed, MIN_COEFF, MAX_COEFF)  # 범위 제한
    h_fixed = h_fixed.astype(dtype)                   # 고정소수점

    N = len(x)
    L = len(h_fixed) # 탭 수 
    offset = L // 2
    y_out = []

    # 6. Convolution Loop (Sliding Window)
    # Verilog의 파이프라인 동작을 순차적으로 흉내 냄
    # 결과의 tail 부분은 무시. N+L-1 대신 N만 계산

    # acc_bits 폭 마스크
    mask = (1 << acc_bits) - 1
    for n in range(N):
        acc = 0 # Acc Reset
        
        for k in range(L):
            # Zero Padding Check (이미지 경계 처리)
            idx = n - k + offset
            if 0 <= idx < N:
                pixel = int(x[idx])
            else:
                pixel = 0
            
            term = pixel * int(h_fixed[k])
            acc += term
            # 하위 acc_bits만 남김
            acc = acc & mask


        # (acc_bits - 1) -> 1000 0000 0000 0000 즉 최상위 부호 비트 판단
        # 결과가 1이면 음수, 0이면 양수인 것
        if acc & (1 << (acc_bits - 1)): 
            acc -= (1 << acc_bits)      # 음수 값으로 복원

        # 7. Re-scaling & Saturation
        acc += (1 << (frac_bits - 1))
        # 정수 * 고정소수점 계수 -> frac_bits만큼 쉬프트해 복원
        final_val = acc >> frac_bits 
        
        # Saturation (0 ~ 255 Clipping)
        if final_val > MAX_PIXEL:
            final_val = MAX_PIXEL
        elif final_val < MIN_PIXEL:
            final_val = MIN_PIXEL
            
        y_out.append(final_val)

    return np.array(y_out, dtype=np.uint8)
