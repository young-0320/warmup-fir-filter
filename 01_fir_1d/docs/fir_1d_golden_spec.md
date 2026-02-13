
# FIR 1D Golden Specification (Dual Model)

## 1. 개요 및 페르소나 (Persona)

* **목적** : 본 문서는 **2D 이미지 필터링 가속기**의 라인 버퍼(Line Buffer) 및 연산 코어 설계를 위한 1차원 FIR 필터의 동작을 정의한다.
* **적용 분야** : Grayscale 이미지(0~255)의 엣지 검출(Edge Detection) 및 노이즈 제거(Smoothing).
* **검증 전략** :

1. **Ideal Model (Float-64)** : 알고리즘의 논리적 정합성(Zero-padding, Sliding Window) 확인.
2. **Hardware Model (Fixed-8)** : RTL 구현과 비트 단위(Bit-exact)로 일치해야 하는  **Golden Reference** .

---

## 2. 함수 1: Ideal Floating-Point Model (논리 검증용)

하드웨어 제약 없이 순수 수학적 알고리즘이 올바르게 동작하는지 확인하는 기준이다.

### 2.1 함수 시그니처

* **함수명** : `fir_1d_idel`
* **입력** :
* `x`: `list[float]` (정규화된 픽셀 값, 범위 **$0.0 \sim 255.0$**)
* `h`: `list[float]` (실수형 필터 계수, 예: **$1/9, -1.0$**)
* **출력** :
* `y`: `list[float]` (제한 없는 실수형 결과)

### 2.2 동작 사양

* **데이터 범위** : 제한 없음 (음수, 소수점 모두 유지).
* **경계 처리 (Padding)** : `Zero-padding`을 적용하여 입력 배열 `x`의 범위를 벗어나는 인덱스는 `0.0`으로 계산한다.
* **용도** : "필터가 영상의 엣지 부분에서 튕기지 않고 계산을 수행하는가?"를 검증.

---

## 3. 함수 2: Hardware Fixed-Point Model (RTL 검증용)

**Verilog HDL로 구현될 회로의 동작을 소프트웨어로 완벽하게 흉내 낸(Bit-true) 모델이다.** 이 함수의 출력값은 RTL 시뮬레이션 파형과 100% 일치해야 한다.

### 3.1 함수 시그니처

* **함수명** : `fir_1d_fixed_golden`
* **입력** :
* `x`: `list[int]` ( **8-bit Unsigned Integer** , 0~255)
* `h`: `list[float]` (내부에서 정수로 양자화됨)
* **파라미터 (Hardware Constraints)** :
* `data_bits`: **8** (Pixel Depth)
* `frac_bits`: **7** (Coefficient Precision, **$Q1.7$**)
* `acc_bits`: **16** (Accumulator Width)
* **출력** :
* `y_out`: `list[int]` ( **8-bit Unsigned Integer** , 0~255)

### 3.2 데이터 경로 및 제약 사항 (Data Path Specification)

#### A. 입력 데이터 규격 (Input Constraint)

* 모든 입력 `x`는 `uint8` 처리된다. (**$0 \le x \le 255$**)
* 음수 픽셀이나 255를 초과하는 입력은 허용하지 않는다.

#### B. 계수 양자화 (Coefficient Quantization)

* 실수 계수 `h`는 다음 공식을 통해 정수로 변환된다.
  * **$H_{fixed} = \text{round}(h \times 2^{\text{frac\_bits}})$**
  * 예: **$1/9 \approx 0.111 \xrightarrow{\times 128} 14$**

#### C. 연산 및 누적 (MAC & Accumulation)

* **곱셈** : `8-bit` 입력 **$\times$** `8-bit` 계수 **$\rightarrow$** `16-bit` 결과 생성.
* **누적 (Accumulator)** :
* 누산기 폭은 `acc_bits`(16-bit)로 제한된다.
* **Overflow Policy** : 누산 중 `16-bit` 범위를 초과하는 경우, 상위 비트는 버려진다( **Wrap-around** ).
  * *설계 의도: 하드웨어 비용 절감 및 2D 필터의 작은 커널 크기(**$3 \times 3$**) 감안.*

#### D. 출력 보정 (Post-Processing)

연산이 끝난 `acc` 값은 다음 3단계 후처리를 거쳐 최종 8비트로 변환된다.

1. **Re-scaling** : 고정소수점 복원을 위해 `frac_bits`만큼 우측 시프트한다. (`acc >> 7`)
2. **Saturation (Clamping)** :

* 결과가 **음수**인 경우(샤프닝 필터 등) **$\rightarrow$** **0**으로 고정.
* 결과가 **255를 초과**하는 경우 **$\rightarrow$** **255**로 고정.

1. **Truncation** : 소수점 이하는 버림 처리한다.
