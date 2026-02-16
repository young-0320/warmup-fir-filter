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
- 입력 `x`는 연산 전 8-bit unsigned 범위 `[0, 255]`로 saturation(clamp)한다.
- 출력 `y`는 floating-point 값을 유지하며 별도 saturation/wrap을 적용하지 않는다.

### 2.3 계수(`h`) 유효성 정책

- `h`는 빈 리스트를 허용하지 않는다. (`h=[]`이면 `ValueError`)
- 모든 `h[i]`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
- 모든 `h[i]`는 `|h[i]| <= 1e6`을 만족해야 한다.
- TODO: 현재 `1e6`은 임시 값이며, 추후 Fixed 모델 계수 허용 실수 범위(`MIN_COEFF_REAL ~ MAX_COEFF_REAL`) 기준으로 변경한다.
- 위 조건 위반 시 `fir_1d_ideal`은 `ValueError`를 발생시킨다.

---

### 3. 함수 2: Fixed-Point Golden Model

### 3.1 함수 시그니처

- 함수명: `fir_1d_fixed_golden`
- 입력:
- `x: list[int|float]` (입력 샘플)
- `h: list[float]` (실수 계수, 내부에서 고정소수점 정수로 양자화)
- 파라미터:
- `data_bits: int = 8`
- `frac_bits: int = 7`
- `acc_bits: int = 16`
- `coeff_bits: int = 8`
- 출력:
- `y_out: np.ndarray[np.uint8]` (unsigned pixel)

### 3.2 데이터 경로 및 제약

#### A. 입력 데이터

- 입력 `x[i]`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
- `x[i]`는 연산 전 `[0, (1 << data_bits) - 1]` 범위로 saturation(clamp)한다.
- saturation 후 내부 저장은 `np.uint8` 배열로 변환한다.
- 출력 saturation 범위도 `[0, (1 << data_bits) - 1]`를 사용한다.

#### B. 계수 무결성 체크 (실수 입력 범위)

- `coeff_bits`는 `{8, 16, 32, 64}`만 허용한다. 그 외 값은 `ValueError`.
- 계수 정수 범위:
- `MIN_COEFF = -(1 << (coeff_bits - 1))`
- `MAX_COEFF = (1 << (coeff_bits - 1)) - 1`
- 실수 허용 범위:
- `MIN_COEFF_REAL = MIN_COEFF / (1 << frac_bits)`
- `MAX_COEFF_REAL = MAX_COEFF / (1 << frac_bits)`
- 모든 `h[i]`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
- 모든 `h[i]`는 위 실수 범위를 만족해야 하며, 벗어나면 `ValueError`를 발생시킨다.

#### C. 계수 양자화

- `H_fixed = rint(h * 2^frac_bits)` (원소별 반올림)
- 이후 `MIN_COEFF ~ MAX_COEFF` 범위로 clip 적용
- `H_fixed`는 `coeff_bits`에 대응되는 정수 dtype(`int8/int16/int32/int64`)으로 변환

#### D. MAC 및 누산

- 탭 수: `L = len(h_fixed)`
- 출력 길이: `N` (tail `L-1` 구간은 계산하지 않음)
- 경계 처리: Zero-padding
- MAC 곱셈은 `term = int(pixel) * int(h_fixed[k])`로 수행
- 누산기 overflow 정책: wrap-around
- 구현 정책: 매 MAC 단계마다 `acc = (acc + term) & ((1 << acc_bits) - 1)`
- 누산 종료 후 signed 복원:
- `if acc & (1 << (acc_bits - 1)): acc -= (1 << acc_bits)`

#### E. 출력 보정

1. Re-scaling: `final_val = acc >> frac_bits`
2. Saturation: `[0, (1 << data_bits) - 1]`로 클램프
3. 반환 타입: `np.ndarray` (`dtype=np.uint8`)
4. 구현 제약: 최종 반환 dtype이 `uint8`이므로 bit-true 기준 권장 설정은 `data_bits=8`이다.
