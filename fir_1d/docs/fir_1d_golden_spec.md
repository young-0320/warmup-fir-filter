# FIR 1D Golden Specification

## 1. 개요

- 목적: 본 문서는 2D 이미지 필터링 가속기의 전단 1D FIR 모델 동작을 정의한다.
- 적용 분야: Grayscale 이미지(0~255) 기반 노이즈 제거, 엣지 검출, 샤프닝.
- 검증 전략:

1. Ideal Model (float): 알고리즘 정합성(Zero-padding, Sliding Window) 확인.
2. Fixed Model (bit-true): RTL과 비트 단위 일치 검증.

---

## 2. 함수 1: Ideal Floating-Point Model

### 2.1 함수 시그니처

- 함수명: `fir_1d_ideal`
- 입력:
- `x: list[int]`
- `h: list[float]`
- 출력:
- `y: list[float]`

### 2.2 동작 사양

- 출력 길이: `N + L - 1` (`N=len(x)`, `L=len(h)`).
- 경계 처리: Zero-padding (`x` 범위 밖 인덱스는 0으로 처리).
- 연산: `y[n] = sum(h[k] * x[n-k])`.
- 본 모델은 saturation/wrap 같은 하드웨어 제약을 적용하지 않는다.

---

### 3. 함수 2: Fixed-Point Golden Model

### 3.1 함수 시그니처

- 함수명: `fir_1d_fixed_golden`
- 입력:
- `x: list[int]` (unsigned pixel, 기본 8-bit 기준 0~255)
- `h: list[float]` (실수 계수, 내부에서 고정소수점 정수로 양자화)
- 파라미터:
- `data_bits: int = 8`
- `frac_bits: int = 7`
- `acc_bits: int = 16`
- `coeff_bits: int = 8`
- 출력:
- `y_out: list[int]` (unsigned pixel, 기본 0~255)

### 3.2 데이터 경로 및 제약

#### A. 입력 데이터

- `x`는 정수 픽셀 입력을 가정한다.
- 기본 설정(`data_bits=8`)에서 출력 saturation 범위는 `[0, 255]`.

#### B. 계수 무결성 체크 (실수 입력 범위)

- 계수 정수 범위:
- `MIN_COEFF = -(1 << (coeff_bits - 1))`
- `MAX_COEFF = (1 << (coeff_bits - 1)) - 1`
- 실수 허용 범위:
- `MIN_COEFF_REAL = MIN_COEFF / (1 << frac_bits)`
- `MAX_COEFF_REAL = MAX_COEFF / (1 << frac_bits)`
- 모든 `h[i]`는 위 실수 범위를 만족해야 하며, 벗어나면 `ValueError`를 발생시킨다.

#### C. 계수 양자화

- `H_fixed = round(h * 2^frac_bits)`
- 구현: `quantized = int(round(num * (1 << frac_bits)))`

#### D. MAC 및 누산

- 탭 수: `L = len(h_fixed)`
- 출력 길이: `N` (tail `L-1` 구간은 계산하지 않음)
- 경계 처리: Zero-padding
- 누산기 overflow 정책: wrap-around
- 구현 정책: 매 MAC 단계마다 `acc = (acc + term) & ((1 << acc_bits) - 1)`
- 누산 종료 후 signed 복원:
- `if acc & (1 << (acc_bits - 1)): acc -= (1 << acc_bits)`

#### E. 출력 보정

1. Re-scaling: `final_val = acc >> frac_bits`
2. Saturation: `[0, (1 << data_bits) - 1]`로 클램프
3. 출력 타입: 정수
