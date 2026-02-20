# FIR 1D 3-Tap Ideal vs Fixed 성능 비교 분석 보고서 (Rev 1.0)

## 1. 보고 목적

본 문서는 3-tap FIR 필터에 대해 `ideal(float64)` 모델과 `fixed(uint8, Q4.12)` 모델의 출력 차이를 정량 분석하고, 필터별 오차 특성 및 설계적 의미를 해석하기 위해 작성하였다.

분석 대상 리포트:

- `fir_1d/sim/vector/output/report_3tap/compare_3tap_cases.csv`
- `fir_1d/sim/vector/output/report_3tap/compare_3tap_summary.json`

---

## 2. 비교 조건 및 지표 정의

### 2.1 비교 조건

- 입력: 7개 grayscale 이미지 (총 67,975,252 samples)
- 필터: `edge`, `moving_avg`, `sharpen`, `simple_lp` (각 7케이스, 총 28케이스)
- 비교식: `diff = fixed - ideal`
- fixed 출력: `uint8` saturation 포함 (`0~255`)
- ideal 출력: float raw 출력 (클리핑 없음)

### 2.2 주요 지표

- `num_samples`: 케이스 내 총 샘플(픽셀) 수
- `max_abs_err`: 최악 1픽셀 오차. `|fixed - ideal|`로 계산.
- `mae`: 평균 절대 오차. 전체 평균 오차 (전반 정확도)
- `rmse`: 제곱 평균 제곱근 오차 (큰 오차에 더 민감한 평균 오차)
- `mean_err`: 평균 부호 오차. +/- 편향 확인
- `sat_ratio`: fixed 출력이 `0` 또는 `255`인 비율
- `clip_needed_ratio`: ideal 출력이 `[0,255]`를 벗어난 비율

---

## 3. 전체 결과 요약

### 3.1 리포트 기본 평균(케이스 단순 평균)

| 항목                  |         값 |
| --------------------- | ---------: |
| num_cases             |         28 |
| num_samples_total     | 67,975,252 |
| avg_mae               |     2.4078 |
| avg_rmse              |     5.8063 |
| avg_mean_err          |     2.2903 |
| avg_sat_ratio         |     0.2440 |
| avg_clip_needed_ratio |     0.1024 |
| max_max_abs_err       |      255.0 |

해석:

- 단순 평균 기준에서는 오차가 큰 일부 케이스(특히 edge)가 전체 평균을 크게 끌어올린다.

### 3.2 샘플 수 가중 평균(추가 계산)

`compare_3tap_cases.csv`에서 샘플 수 기준으로 가중 평균을 별도 계산하였다.

| 항목                       |     값 |
| -------------------------- | -----: |
| weighted_mae               | 0.6592 |
| weighted_rmse              | 2.6526 |
| weighted_mean_err          | 0.6067 |
| weighted_sat_ratio         | 0.6567 |
| weighted_clip_needed_ratio | 0.0498 |

해석:

- 실제 픽셀 수 비중을 반영하면 오차 크기는 단순 평균보다 낮아진다.
- 반면 `sat_ratio`는 대형 이미지의 히스토그램 특성(원본 이미지 자체에 0/255 픽셀 다수) 때문에 높아진다.

---

## 4. 필터별 성능 분석

### 4.1 케이스 단순 평균 기준

| Coeff      | avg_mae | avg_rmse | avg_mean_err | avg_sat_ratio | avg_clip_needed_ratio | max_abs_err(최대) |
| ---------- | ------: | -------: | -----------: | ------------: | --------------------: | ----------------: |
| edge       |  9.0162 |  21.9354 |       9.0162 |        0.6213 |                0.3977 |             255.0 |
| moving_avg |  0.1829 |   0.2432 |      -0.0010 |        0.1152 |                0.0000 |            0.3333 |
| sharpen    |  0.2298 |   0.7780 |       0.0492 |        0.1244 |                0.0118 |           44.8750 |
| simple_lp  |  0.2023 |   0.2686 |       0.0968 |        0.1149 |                0.0000 |            0.5000 |

핵심 해석:

- `edge`가 오차를 지배한다.
- `moving_avg`, `simple_lp`는 매우 낮은 오차 수준을 보인다.
- `sharpen`은 LPF 계열보다 오차가 크지만 `edge` 대비 훨씬 안정적이다.

### 4.2 필터별 오차 원인

1. `edge = [-1, 0, 1]`

- 미분형 필터 특성상 음수 출력이 빈번하다.
- fixed `uint8` 출력에서 음수는 `0`으로 clip되어 정보 손실이 크게 발생한다.
- 결과적으로 `clip_needed_ratio`와 `rmse`가 크게 증가한다.

2. `moving_avg = [1/3, 1/3, 1/3]`

- `1/3`은 Q4.12에서 정확 표현 불가(`1365/4096` 근사).
- 계수 양자화 오차가 누적되어 소규모 오차가 지속된다.

3. `simple_lp = [0.25, 0.5, 0.25]`

- Q4.12에서 정확 표현 가능.
- 주요 오차는 계수 양자화가 아니라 최종 반올림/정수화 단계에서 발생한다.

4. `sharpen = [-0.125, 1.25, -0.125]`

- Q4.12에서 정확 표현 가능.
- 고주파 강조로 일부 overshoot/undershoot가 발생하여 clip 영향이 제한적으로 나타난다.

### 4.3 `edge` 계수의 음수 원소가 주는 영향

3-tap center-aligned `edge = [-1, 0, 1]`는 수식적으로 아래 형태와 동일하다.

\[
y[n] = -x[n-1] + x[n+1] = x[n+1] - x[n-1]
\]

즉, 좌우 차분(1차 미분) 성분을 추출하는 고역 통과 성격을 갖는다. 이때 다음 현상이 발생한다.

1. 부호가 있는 출력 생성

- 경계 방향에 따라 출력이 양수/음수 모두 가능하다.
- ideal에서는 음수 값을 그대로 유지하지만, fixed `uint8`에서는 음수가 `0`으로 clip된다.

2. 비대칭 오차 증가

- 음수 구간에서 `fixed - ideal = 0 - (음수)`가 되어 양의 큰 오차가 생긴다.
- 본 리포트에서 `edge`의 `mean_err`가 지속적으로 양수(단순 평균 `+9.0162`)인 이유가 여기에 해당한다.

3. 클리핑 지표 동반 상승

- `edge`의 `clip_needed_ratio` 단순 평균은 `0.3977`, `sat_ratio` 단순 평균은 `0.6213`으로 타 계수 대비 압도적으로 높다.
- 따라서 `edge`의 큰 MAE/RMSE는 "고정소수점 연산 정밀도"보다 "부호 정보가 없는 `uint8` 출력 포맷 제약"의 영향이 크다.

---

## 5. Worst-case 분석

RMSE 상위 5개 케이스는 모두 `edge` 계수 조합이다.

| 순위 | Key                                     |    RMSE |     MAE | clip_needed_ratio | sat_ratio |
| ---: | --------------------------------------- | ------: | ------: | ----------------: | --------: |
|    1 | case_004_img_005_64x64_noise_gray__edge | 36.4074 | 18.8247 |            0.5522 |    0.5667 |
|    2 | case_003_img_004_64x64_gray__edge       | 36.0053 | 18.2788 |            0.5430 |    0.5671 |
|    3 | case_006_img_007_1280x641_gray__edge    | 23.1992 |  9.3913 |            0.4698 |    0.5063 |
|    4 | case_001_img_002_640x762_gray__edge     | 17.8918 |  5.5127 |            0.3811 |    0.5628 |
|    5 | case_002_img_003_1280x854_gray__edge    | 16.8474 |  4.2148 |            0.3430 |    0.6511 |

해석:

- high-error 영역은 대부분 "엣지 결과의 부호/범위 정보"가 `uint8` clipping에서 손실되는 구간이다.

---

## 6. 케이스 특성 관찰

### 6.1 `case_005_img_006_4499x2999_gray`의 특이점

- 해당 이미지는 입력 히스토그램에서 `0` 픽셀 비율이 매우 높다(약 73%).
- 따라서 필터 종류와 무관하게 fixed 출력의 `sat_ratio`가 높게 관측된다.
- 그러나 `clip_needed_ratio`는 `edge` 외 계수에서 낮거나 0이므로, 이를 "모델 정확도 저하"로 단정하기는 어렵다.

### 6.2 edge 대비 non-edge 오차 배율

이미지별로 `edge RMSE / (moving_avg, sharpen, simple_lp 평균 RMSE)`를 계산하면 약 `42.5x ~ 73.4x` 범위이다.
즉, 본 보고서의 주된 오차 원인은 필터 자체(특히 edge)와 출력 포맷(`uint8 clip`)의 조합이다.

---

## 7. 결론

1. 3-tap fixed 모델은 `moving_avg`, `simple_lp`에서 ideal 대비 매우 작은 오차를 보이며, 정수 출력 모델로서 충분히 안정적이다.
2. `sharpen`은 중간 수준의 오차를 보이지만, 대부분 clipping/rounding의 자연스러운 부산물이다.
3. `edge`는 알고리즘 특성상 음수/범위 초과가 본질적으로 많아 `uint8` 출력과 결합 시 큰 오차가 발생한다.
4. 따라서 현재 리포트는 "고정소수점 정밀도 문제"보다는 "출력 표현 범위 제약(clip)"의 영향을 강하게 반영한다.

---

## 8. 향후 개선 제안

1. `edge` 계수에 대해 별도 signed 출력 경로(`int16` 등)를 추가해, clipping 영향과 정밀도 오차를 분리 평가할 필요가 있다.
2. 현재 지표(`fixed raw` vs `ideal raw`) 외에 `clip(ideal)` 대비 비교 지표를 병행하면 하드웨어 포맷 적합성 평가가 명확해진다.
3. 최종 보고서에는 케이스 단순 평균과 샘플 가중 평균을 함께 제시하여 통계 해석의 편향을 줄이는 것이 바람직하다.

---

## 9. 근거 기반 정밀도 손실 판정

### 9.1 "표준 임계값"에 대한 정리

- MAE/RMSE의 절대 임계값은 필터 종류, 데이터 분포, 출력 포맷에 따라 달라지므로 보편 단일 기준을 두기 어렵다.
- 또한 MSE/PSNR 계열 지표는 인간 지각 품질과 완전히 일치하지 않으며, 특히 콘텐츠가 달라지면 해석 신뢰도가 낮아질 수 있다.
- 따라서 본 과제에서는 "동일 입력·동일 필터 조건에서의 fixed 구현 충실도"를 기준으로 해석하는 것이 타당하다.

### 9.2 본 보고서 데이터로 본 정량 근거

`edge`를 제외한 계수(`moving_avg`, `simple_lp`, `sharpen`)를 샘플 수 가중으로 합산하면:

- `MAE = 0.0927` gray level
- `RMSE = 0.2106` gray level
- `PSNR = 61.66 dB` (RMSE 기준 환산)
- `clip_needed_ratio = 0.00857`

이는 8-bit full scale(255) 대비 매우 작은 오차이며, 평균 오차가 1 gray level보다 훨씬 작은 "sub-LSB급" 수준으로 해석 가능하다.

### 9.3 양자화 이론 관점 교차 검증

반올림 양자화 오차를 `[-0.5, 0.5]` 균등 분포로 가정하면 기준 RMSE는 다음과 같다.

`RMSE_quant = sqrt(1/12) ≈ 0.2887`

본 리포트의 non-edge 가중 RMSE(`0.2106`)는 이 기준보다 낮으며, 계수별 가중 RMSE도
`moving_avg=0.1648`, `simple_lp=0.1787`, `sharpen=0.2883`로 양자화 한계 근방 또는 그 이하이다.

결론적으로 non-edge 계수군에서는 "정밀도 손실이 작다"고 판단할 정량 근거가 충분하다.

### 9.4 `edge` 케이스 판정 방법

- `edge`의 높은 RMSE(`weighted 9.9785`)는 clip으로 인한 부호 정보 손실이 핵심 요인이다.
- 따라서 `edge`까지 동일 기준으로 "정밀도 손실 과다"라고 결론 내리면 해석이 왜곡된다.
- `edge`는 아래 중 하나로 별도 판정하는 것이 권장된다.
  - signed 출력(`int16` 등) 기준 비교
  - `clip(ideal)` 후 비교(표현 포맷 정합 비교)

---

## 10. 참고 문헌

1. Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). *Image Quality Assessment: From Error Visibility to Structural Similarity*. IEEE TIP, 13(4), 600-612.Link: https://ece.uwaterloo.ca/~z70wang/publications/ssim.pdf
2. Huynh-Thu, Q., & Ghanbari, M. (2008). *Scope of validity of PSNR in image/video quality assessment*. Electronics Letters, 44(13), 800-801.
   DOI: https://doi.org/10.1049/el:20080522
