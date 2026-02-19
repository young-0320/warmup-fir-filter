# FIR 1D Ideal Specification (Rev 1.2)

---

## 1. 개요

* **목적:** 2D 이미지 필터링 가속기의 전단 1D FIR IDEAL 모델 동작 정의.
* **적용 분야:** Grayscale 이미지(0~255) 기반 노이즈 제거, 엣지 검출, 샤프닝.
* **핵심 역할:** 고정소수점(Golden) 모델의 비트 폭 설정을 위한 **Dynamic Range(최대/최소값)** 분석 및 수학적 무결성 검증.

---

## 2. 함수 : Ideal Floating-Point Model

### 2.1 함수 시그니처

* **함수명:** `fir_1d_ideal`
* **입력:**
  * `x: list[int|float]` (입력 데이터)
  * `h: list[float]` (필터 계수)
* **출력:**
  * `y: list[float]` (필터링 결과)


### 2.2 동작 사양 (Behavior Specification)

* **Convolution Mode:** **Same Mode (Center Aligned)**
  * **정의:** 출력 길이를 입력 길이 `N`과 동일하게 유지하며, 필터 커널의 중심(Center)을 현재 입력 픽셀 위치에 정렬한다.
  * **Center Offset:** `center = len(h) // 2` (Integer Division).
  * **연산 수식:**

    $$
    y[n] = \sum_{k=0}^{L-1} h[k] \times x[n - k + \text{center}]
    $$

    *(단, 인덱스 $n-k+\text{center}$가 **$0 \sim N-1$** 범위를 벗어나면 0으로 처리)*
* **경계 처리 (Padding):** Zero-padding.
* **데이터 정밀도:** Python `float` (64-bit Double Precision) 연산 수행.
* **입력 전처리 정책 (Input Preprocessing):**
  * 모든 `x`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
  * **Rounding:** `round-half-up` 적용 (`floor(x + 0.5)`).
  * **Clamp:** 반올림 결과를 `[0, 255]` 범위로 Saturation.
* **출력 정책:**
  * **Output:** **Pass-through (No Clamp).**
    * *목적:* 필터링 후 발생하는 Overshoot/Undershoot(예: -150, +765) 값을 날것(Raw) 그대로 관찰하여, Golden Model의 `acc_bits` 및 `output_stage` 설계를 위한 근거 데이터로 활용함.

### 2.3 계수(`h`) 유효성 정책

* `h`는 빈 리스트를 허용하지 않는다. (`h=[]`이면 `ValueError`)
* 모든 `x, h`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
* 모든 `h[i]`는 `|h[i]| <= 8.0`을 만족해야 한다.
* 위 조건 위반 시 `fir_1d_ideal`은 `ValueError`를 발생시킨다.

---

### 2.4 설계 근거: Center Alignment의 필요성 (Design Rationale)

본 Ideal 모델에서 일반적인 Convolution(**$n-k$**) 대신 **Center Offset(**$n-k+\text{center}$**)** 방식을 채택한 이유는 다음과 같다.

**1. 위상 지연(Group Delay) 보정**

* **문제:** 일반적인 FIR 필터링(**$y[n] = \sum h[k]x[n-k]$**)은 필터 탭 수(**$L$**)에 비례하여 출력 신호가 **$\frac{L-1}{2}$** 샘플만큼 뒤로 밀리는 **위상 지연(Phase Shift)**이 발생한다.
* **영향:** 이미지 처리에서 이를 보정하지 않으면, 필터링된 이미지 속 물체가 원래 위치보다 우측/하단으로 밀려나게 되어 원본과의 정합성(Overlay)이 깨진다.
* **해결:** 미래의 데이터를 참조하는(Look-ahead) 형태의 Center Offset을 적용하여 입출력 간의 위상 차(Phase Difference)를 **0(Zero-phase)**으로 만든다.

**2. 하드웨어 라인 버퍼(Line Buffer)와의 동작 일치**

* **하드웨어 구조:** 실제 RTL 설계 시, 3x3 등의 2D 필터는 라인 버퍼를 통해 주변 픽셀(위, 아래, 좌, 우)을 동시에 참조한다. 이는 물리적으로 Center Alignment 로직과 동일하다.
* **검증 효율:** Ideal 모델 단계에서부터 Center Alignment를 적용해야만, 추후 RTL 시뮬레이션 결과와 픽셀 단위(Pixel-wise) 비교가 가능하다.

**3. 입출력 해상도 1:1 매핑 (Resolution Matching)**

* **목적:** 64x64 입력에 대해 정확히 64x64 출력을 얻기 위함.
* **효과:** `Same Mode`를 적용함으로써, 이미지의 해상도 변경 없이 순수한 필터링 효과만을 분석할 수 있다.
