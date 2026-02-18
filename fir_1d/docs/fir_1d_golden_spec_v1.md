# FIR 1D Golden Specification (Rev 1.2)

## 1. 개요

* **목적:** 64x64 Grayscale 이미지 필터링 가속기 설계를 위한 전단 1D FIR 하드웨어 동작 정의.
* **적용 분야:** 노이즈 제거(LPF), 엣지 검출(Sobel/Prewitt), 샤프닝(Sharpening).
* **주요 특징:** 16-bit Q4.12 포맷을 통한 고정밀 연산 및 FPGA DSP 블록(DSP48 등) 활용 최적화.

---

## 2. Fixed-Point Golden Model

### 2.1 함수 시그니처

* **함수명:** `fir_1d_fixed_golden`
* **입력:**
  * `x: list[int|float]` (입력 픽셀 데이터, 0~255)
  * `h: list[float]` (실수형 필터 계수)
* **파라미터 (Default):**
  * `frac_bits: int = 12` (Q4.12 포맷 기준)
  * `acc_bits: int = 32` (Internal Accumulator 비트 폭)
  * `coeff_bits: int = 16` (계수 저장 비트 폭)
* **출력:**
  * `y_out: np.ndarray[np.uint8]` (0~255 Saturation Output)

### 2.2 데이터 경로 및 제약

#### A. 입력 데이터 전처리

* **유효성 검사:** `NaN`,`+Inf`,`-Inf`입력 시 `ValueError` 발생.
* **전처리 단계:**
  1. **Rounding:** `round-half-up` (0.5를 더한 뒤 버림) 적용.
  2. **Saturation:** `[0, 255]` 범위로 Clamp 수행.
  3. **Type Casting:** 내부 연산을 위해 `uint8`형으로 변환.

#### B. 계수 무결성 및 변환

* **비트 폭 제약:** `coeff_bits`는 `{8, 16, 32}`만 허용하여 메모리 정렬 최적화.
* **동적 범위(Dynamic Range) 검사:**
  * `h`는 빈 리스트를 허용하지 않는다.
  * 모든 `x, h`는 유한 실수여야 한다. (`NaN`, `+Inf`, `-Inf` 금지)
  * 모든  `h[i]`는 Q4.12 표현 가능 범위 내에 있어야 한다.
  * *준수 범위:* **$-8.0 \le h < 7.99975$** (Signed 16-bit 기준).
  * 위 조건 위반 시 `ValueError`를 발생시킨다.

#### C. 계수 양자화 (Quantization)

* **변환식:** **$H_{fixed} = \text{round}(h \times 2^{\text{frac\_bits}})$**
* **타입:** `int16` (계수 가변형 레지스터 인터페이스 대응).

#### D. MAC 연산 및 인덱싱

* **Convolution Mode:** **Same Mode (Center Aligned)**

  * **정의:** 출력 이미지의 위상(Phase)이 입력과 정확히 일치하도록(Zero-phase), 필터 커널의 중심을 현재 픽셀에 정렬한다.
  * **Offset 설정:** **$\text{center} = \text{floor}(L / 2)$** (예: 3탭 **$\rightarrow$** 1, 9탭 **$\rightarrow$** 4).
  * **인덱싱 수식:**
    $$
    y[n] = \sum_{k=0}^{L-1} h_{fixed}[k] \times x_{pad}[n - k + \text{center}]
    $$
  * **동작 설명:** 위 수식은 논리적으로 **미래의 데이터(**$n+\text{center}$**)**를 참조하는 구조임. 이는 하드웨어 구현 시 **라인 버퍼(Line Buffer)를 통한 지연(Latency)**으로 매핑됨.
* **경계 처리 (Padding):** Zero-padding
* **누산기 (Accumulator):**

  * **MAC 동작:** 매 단계마다 `acc = (acc + term) & mask` (Overflow 발생 시 비트 절삭을 통한 Wrap-around 모사).
  * **부호 복원:** 마스킹 후 Unsigned(양수)로 변환된 값을, 최상위 비트(MSB) 검사를 통해 **Signed(음수 포함) 2의 보수 형태**로 재해석(Re-interpretation). (추후 Shift 연산 시 부호 비트 유지 위함)

#### E. 출력 보정 (Post-processing)

1. **Rounding (반올림 구현):**

   * **Bias Addition:** `acc = acc + (1 << (frac_bits - 1))` (시프트 전 0.5 값 가산).
2. **Re-scaling:**

   * `final_val = acc >> frac_bits` (고정소수점 복원).
3. **Saturation:**

   * `final_val > 255` → `255`, `final_val < 0` → `0` (Underflow 방지 로직 필수).

---

### 2.3 설계 근거 및 권장 설정 (Design Rationale)

#### A. 고정 소수점 포맷: 16-bit Q4.12 선정 근거

본 설계는 **하드웨어 자원 최적화(Resource Optimization)**와 **필터 범용성(Kernel Versatility)** 사이의 Trade-off를 분석하여, **Signed 16-bit Fixed-point (Q4.12)**를 최종 표준으로 확정한다.

**1. 워드 길이(Word Length) 선정: 16-bit**

* **DSP 블록 효율성 (DSP Efficiency):**
  * Target FPGA(Xilinx Artix/Kintex/Zynq 등)의 **DSP48 슬라이스**는 기본적으로 **$18 \times 25$** 비트 곱셈기를 내장하고 있음.
  * **8-bit 사용 시:** DSP 입력 비트의 절반 이상이 낭비됨(Under-utilization).
  * **32-bit 사용 시:** 하나의 곱셈을 위해 DSP 슬라이스 2~3개를 연결(Cascade)해야 하므로 면적과 전력 소모가 3배 이상 급증함.
  * **16-bit 사용 시:** DSP 슬라이스 1개에 완벽하게 매핑되며, 메모리(BRAM) 데이터 정렬(2-Byte Alignment)에도 가장 유리함.

**2. Q-Format 상세 분석: Q4.12 (S1.I3.F12)**

* **구조:** Sign(1-bit) + Integer(3-bit) + Fraction(12-bit) = **Total 16-bit**
* **[결정 요인 1] 정수부(Integer) 4-bit (범위: **$-8.0 \le h < +7.99$**)**
  * *Why 4-bit?* 영상 처리에서 필수적인 **샤프닝(Sharpening) 필터**의 중심 계수는 통상 **$+5.0$**임.
  * 만약 정수부를 3-bit(Q3.13)로 설정할 경우, 표현 범위가 **$-4.0 \sim +3.99$**로 제한되어 계수 **$+5.0$**을 표현할 때 **Overflow**가 발생함.
  * 따라서 계수 **$+5.0$**과 Edge Detection의 **$-4.0$** 등을 모두 수용하기 위한 최소 안전 마진(Safety Margin)은 **$\pm 8.0$ (4-bit)**임.
* **[결정 요인 2] 소수부(Fraction) 12-bit (정밀도: **$2^{-12} \approx 0.00024$**)**
  * *Why 12-bit?* 입력 데이터인 8-bit Grayscale 이미지의 최소 변화량(1 LSB)은 **$1/256 \approx 0.0039$**임.
  * 필터 계수의 양자화 오차(Quantization Error)가 입력 데이터 정밀도보다 **10배 이상 작아야(10x Rule)** 화질 열화가 발생하지 않음.
  * **$0.00024$** (Q4.12 정밀도)는 **$0.0039$**

**3. 비교 분석 표**

| **포맷 (Format)** | **표현 범위 (Range)**   | **정밀도 (Precision)**              | **샤프닝(5.0) 지원**  | **DSP 효율** | **판정**               |
| ----------------------- | ----------------------------- | ----------------------------------------- | --------------------------- | ------------------ | ---------------------------- |
| **Q2.14**         | **$-2.0 \sim +1.99$** | Ultra High                                | **불가능 (Overflow)** | 좋음               | **기각**               |
| **Q3.13**         | **$-4.0 \sim +3.99$** | High                                      | **불가능 (Overflow)** | 좋음               | **기각**               |
| **Q4.12**         | **$-8.0 \sim +7.99$** | **Optimal (**$0.00024$**)** | **가능 (Safe)**       | **최적**     | **채택 (Standard)**    |
| **Q8.8**          | **$-128 \sim +127$**  | Low (**$0.0039$**)                | 가능                        | 좋음               | **보류 (정밀도 부족)** |

#### **B. 아키텍처 선정: Center Alignment & Same Mode (신설)**

**1. 위상 정합성 (Phase Consistency) 확보**

* **문제:** 일반적인 DSP 필터링(**$y[n] = \sum h[k]x[n-k]$**)을 이미지에 그대로 적용하면, 필터 탭 수(**$L$**)에 따라 이미지가 **$\frac{L-1}{2}$** 픽셀만큼 우측/하단으로 밀리는 **Group Delay**가 발생함.
* **해결:** Golden Model 단계에서 **Center Offset**을 적용하여 입출력 픽셀의 위치를 1:1로 강제 정렬함. 이는 **RTL 시뮬레이션 결과와 원본 이미지를 픽셀 단위로 비교(Pixel-wise Diff)**하기 위한 필수 조건임.

**2. 하드웨어 라인 버퍼 동작 모사 (Hardware Behavior Modeling)**

* **물리적 의미:** 1D Golden Model의 `offset` 로직은 2D 하드웨어의 **라인 버퍼(Line Buffer)** 깊이를 결정하는 기준이 됨.
* **매핑:**
  * Golden Model의 `idx = n + 1` (미래 참조)
  * **$\downarrow$**
  * Hardware의 `Line Buffer Wait` (데이터가 들어올 때까지 출력 지연)
* **결론:** Golden Model에 이 로직을 명시함으로써, RTL 설계 시 **"데이터를 얼마나 지연시켜야 중심이 맞는가?"**에 대한 정확한 타이밍 스펙을 인지할 수 있음.
