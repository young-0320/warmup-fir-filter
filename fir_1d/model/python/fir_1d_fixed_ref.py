# FIR  Filter 1D Fixed Golden Model_v1

# 기본 설정은 Q4.12 (coeff_bits=16, frac_bits=12)
# TODO : 내부 오버플로우 방어 로직
# TODO : 포멧 변경 인터페이스
import numpy as np
import numpy.typing as npt
import math
from .fir_1d_ref import _validate_h_coefficients, _validate_x, _round_half_up_x, _clamp_x
MAX_ABS_H_COEFF = 8.0




def fir_1d_fixed_golden(
    x ,           
    h ,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16
) -> npt.NDArray[np.uint8]:
    """
    범용 1D FIR 필터 하드웨어 동작 시뮬레이션 모델
    
    Args:
        x: Grayscale 이미지 입력 픽셀 리스트 (0 ~ 255) 범위의 int|float
        h: 실수형 필터 계수 값 
        frac_bits: 계수 양자화를 위한 소수점 비트 (기본 12)
        acc_bits: 누산기 비트 폭 (기본 32)
        coeff_bits: 계수 비트 폭 (기본 16)
    
    Returns:
        y_out: 하드웨어 출력 값 numpy unit8 배열  (0 ~ 255)
    """
    # 입력 값 유효성 검증
    _validate_h_coefficients(h) # 필터 계수 
    x_1= _validate_x(x)
    x_2= _round_half_up_x(x_1)
    x_sat = _clamp_x(x_2) # 입력 

    # 입력 비트 유효성 검증
    if frac_bits <= 0:
        raise ValueError(f"Invalid frac_bits={frac_bits}. frac_bits must be > 0.")
    if acc_bits <= 0:
        raise ValueError(f"Invalid acc_bits={acc_bits}. acc_bits must be > 0.")
    valid_coeff_bits = (8, 16, 32)
    if coeff_bits not in valid_coeff_bits:
        raise ValueError(
            f"Invalid coeff_bits={coeff_bits}. coeff_bits must be one of {valid_coeff_bits}."
        )
    

    
    # 1. Parameter Calculation (하드웨어 제약사항)
    MAX_PIXEL = 255
    MIN_PIXEL = 0
    MIN_COEFF = -(1 << (coeff_bits - 1))
    MAX_COEFF = (1 << (coeff_bits - 1)) - 1
    SCALE = (1 << frac_bits)
    MIN_COEFF_REAL = MIN_COEFF / SCALE
    MAX_COEFF_REAL = MAX_COEFF / SCALE
    dtype_h_map = {
        8: np.int8,
        16: np.int16,
        32: np.int32
    }
    dtype = dtype_h_map[coeff_bits]

    # h는 현재 Q-format 실수 표현 범위를 벗어나면 예외 처리
    for index, coeff in enumerate(h):
        if coeff < MIN_COEFF_REAL or coeff > MAX_COEFF_REAL:
            raise ValueError(
                f"Invalid h[{index}]={coeff}: out of Q-format real range "
                f"[{MIN_COEFF_REAL}, {MAX_COEFF_REAL}]."
            )

    # 2. 입력/계수를 내부 연산용 배열로 변환
    x = np.array(x_sat, dtype=np.uint8)
    h = np.array(h, dtype=np.float64)

    # 3. h 실수 원소 -> 고정소수점 정수 변환(계수 먼저 양자화)
    h_fixed = np.rint(h * SCALE)                      # 원소별 반올림
    h_fixed = np.clip(h_fixed, MIN_COEFF, MAX_COEFF)  # 범위 제한
    h_fixed = h_fixed.astype(dtype)                   # 정수형으로 타입 변환
    
    N = len(x)
    L = len(h_fixed) # 탭 수 
    offset = L // 2
    y_out = []

    # 4. Convolution Loop (Sliding Window)
    # 결과의 tail 부분은 무시. N+L-1 대신 N만 계산

    # acc_bits 폭 마스크
    # (1 << acc_bits) = 1 0000 0000 0000 0000 0000 0000 0000 0000
    # mask = 0xFFFFFFFF
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
            
            term = pixel * int(h_fixed[k])  # MAC
            acc += term # 누산
        

        acc = acc & mask # 비트 마스크로 절삭

        # (acc_bits - 1) -> 1000 0000 0000 0000 즉 최상위 부호 비트 판단
        # 결과가 1이면 음수, 0이면 양수인 것
        if acc & (1 << (acc_bits - 1)): 
            acc -= (1 << acc_bits)      # 음수 값으로 복원

        # 5. Re-scaling & Saturation
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
