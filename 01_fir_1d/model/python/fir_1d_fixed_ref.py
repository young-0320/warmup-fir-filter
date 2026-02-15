# FIR  Filter 1D Fixed Golden Model_v1

# Q1.7 선택
# Q1.7 format -> -1.0에서 0.992875 해상도는 0.0078
# Q2.6 format -> -2.0에서 1.984375 해상도는 0.015625(Q1.7에 비해 해상도가 절반)
# TODO : 내부 오버플로우 방어 로직
# TODO : 포멧 변경 인터페이스

def fir_1d_fixed_golden(
    x: list[int],           
    h: list[float],
    data_bits: int = 8,     
    frac_bits: int = 7,     
    acc_bits: int = 16,
    coeff_bits: int = 8,     
) -> list[int]:
    """
    범용 1D FIR 필터 하드웨어 동작 시뮬레이션 모델
    
    Args:
        x: Grayscale 이미지 입력 픽셀 리스트 (0 ~ 255)
        h: 실수형 필터 계수 값 (예: [0.1, -1.25, 5, -1, 0])
        data_bits: 입력 데이터 비트 폭 (기본 8)
        frac_bits: 계수 양자화를 위한 소수점 비트 (기본 7)
        acc_bits: 누산기 비트 폭 (기본 16)
        coeff_bits: 계수 비트 폭 (기본 8)
    
    Returns:
        y_out: 하드웨어 출력 값 (0 ~ 255)
    """
    # 1. Parameter Calculation (하드웨어 제약사항)
    MAX_PIXEL = (1 << data_bits) - 1  # 255가 MAX default
    MIN_PIXEL = 0
    MIN_COEFF = -(1 << (coeff_bits - 1))      # -128
    MAX_COEFF = (1 << (coeff_bits - 1)) - 1   # 127
    SCALE = (1 << frac_bits)                  # 128
    MIN_COEFF_REAL = MIN_COEFF / SCALE        # -128/128 = -1
    MAX_COEFF_REAL = MAX_COEFF / SCALE        # 127/128 = 0.9921875

    # 2. 필터 계수 데이터 무결성 확인
    for i, num in enumerate(h):
        if num < MIN_COEFF_REAL or num > MAX_COEFF_REAL:
            raise ValueError(
                f"h[{i}]={num} out of Q-format real range "
                f"[{MIN_COEFF_REAL}, {MAX_COEFF_REAL}] "
                f"(coeff_bits={coeff_bits}, frac_bits={frac_bits})"
            )

    # 3. h 실수 원소 -> 고정소수점 정수 변환
    # 하드웨어에서는 이 정수값들이 레지스터에 저장됩니다.
    h_fixed = []
    for num in h:
        # h_fixed = h * (2^frac_bits), 가장 가까운 정수로 반올림
        # 부동소수점의 소수점 아래 frac_bits만큼을 보존하기 위해서 2^frac_bits을 곱해 소수점을 뒤로 미는거임.
        # 10진수 1.25의 소수점 아래 2자리를 보존하기 위해 10^2을 곱하는 것과 같은 맥락 
        quantized = int(round(num * SCALE))
        h_fixed.append(quantized)

    N = len(x)
    L = len(h_fixed) # 탭 수 
    y_out = []

    # 4. Convolution Loop (Sliding Window)
    # Verilog의 파이프라인 동작을 순차적으로 흉내 냄
    # 결과의 tail 부분은 무시. N+L-1 대신 N만 계산

    # 16비트 마스크 1111 1111 1111 1111
    mask = (1 << acc_bits) - 1
    for n in range(N):
        acc = 0 # Acc Reset
        
        for k in range(L):
            # Zero Padding Check (이미지 경계 처리)
            if 0 <= n - k < N:
                pixel = x[n - k]
            else:
                pixel = 0
            
            term = pixel * h_fixed[k]
            acc += term
            # 하위 16비트만 남김
            acc = acc & mask


        # (acc_bits - 1) -> 1000 0000 0000 0000 즉 최상위 부호 비트 판단
        # 결과가 1이면 음수, 0이면 양수인 것
        if acc & (1 << (acc_bits - 1)): 
            acc -= (1 << acc_bits)      # 음수 값으로 복원

        # 5. Re-scaling & Saturation
        # 정수 * (Q1.7 8비트 고정소수점) -> 즉 frac_bits(7비트)만큼 밀어 복원
        final_val = acc >> frac_bits 
        
        # Saturation (0 ~ 255 Clipping)
        if final_val > MAX_PIXEL:
            final_val = MAX_PIXEL
        elif final_val < MIN_PIXEL:
            final_val = MIN_PIXEL
            
        y_out.append(final_val)

    return y_out
