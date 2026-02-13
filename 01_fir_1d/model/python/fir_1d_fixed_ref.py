# FIR  Filter 1D Fixed Golden Model

# Q-format control
# 내부 오버플로우 방어 로직


def fir_1d_fixed_golden(
    x: list[float],
    h: list[float],
    data_bits: int = 8,
    frac_bits: int = 7,
    acc_bits: int = 16,
) -> list[float]:
    """
    범용 1D FIR 필터 하드웨어 동작 시뮬레이션 모델
    
    Args:
        x: 입력 픽셀 리스트 (0 ~ 255)
        h: 실수형 필터 계수 (예: [0, -1, 5, -1, 0])
        data_bits: 입력 데이터 비트 폭 (기본 8)
        frac_bits: 계수 양자화를 위한 소수점 비트 (기본 7)
        acc_bits: 누산기 비트 폭 (기본 16)
    
    Returns:
        y_out: 하드웨어 출력 예상값 리스트 (0 ~ 255)
    """
# 1. Parameter Calculation (하드웨어 제약사항)
    MAX_PIXEL = (1 << data_bits) - 1  # 255
    MIN_PIXEL = 0
    
    # 2. Coefficient Quantization (실수 -> 고정소수점 정수 변환)
    # 하드웨어에서는 이 정수값들이 레지스터에 저장됩니다.
    h_fixed = []
    for val in h:
        quantized = int(round(val * (1 << frac_bits)))
        h_fixed.append(quantized)
        
    print(f"[Debug] Quantized Coeffs: {h_fixed}") # 검증용 출력

    N = len(x)
    L = len(h_fixed) # 탭 수 (Tap Num)
    y_out = []

    # 3. Convolution Loop (Sliding Window)
    # Verilog의 파이프라인 동작을 순차적으로 흉내 냄
    for n in range(N):
        acc = 0 # Accumulator Reset
        
        for k in range(L):
            # Zero Padding Check (이미지 경계 처리)
            if 0 <= n - k < N:
                pixel = x[n - k]
            else:
                pixel = 0
            
            # MAC Operation (Multiply-Accumulate)
            # Verilog: acc <= acc + (pixel * coeff);
            term = pixel * h_fixed[k]
            acc += term
            
        # 4. Accumulator Overflow Simulation (Wrap-around)
        # acc_bits(16비트)를 넘어가면 비트가 잘리는 현상 구현
        # 2의 보수 표현을 위해 마스킹 후 다시 Python 정수로 복원
        mask = (1 << acc_bits) - 1
        acc = acc & mask # 하위 16비트만 남김
        if acc & (1 << (acc_bits - 1)): # 부호 비트가 1이면 (음수면)
            acc -= (1 << acc_bits)      # 음수 값으로 복원

        # 5. Post-Processing (Re-scaling & Saturation)
        # bit-shift (나눗셈 대체)
        final_val = acc >> frac_bits 
        
        # Saturation (0 ~ 255 Clipping)
        if final_val > MAX_PIXEL:
            final_val = MAX_PIXEL
        elif final_val < MIN_PIXEL:
            final_val = MIN_PIXEL
            
        y_out.append(final_val)

    return y_out