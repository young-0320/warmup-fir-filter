# FIR 1D 5-Tap Ideal vs Fixed 성능 비교 분석 보고서 (Rev 1.0)

## 1. 보고 목적

본 문서는 5-tap FIR 필터에 대해 `ideal(float64)` 모델과 `fixed(uint8, Q4.12)` 모델의 출력 차이를 정량 분석하고, 필터별 오차 특성 및 설계적 의미를 해석하기 위해 작성하였다.

분석 대상 리포트:

- `fir_1d/sim/vector/output/report_5tap/compare_5tap_cases.csv`
- `fir_1d/sim/vector/output/report_5tap/compare_5tap_summary.json`
  
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
- `max_abs_err`: `|fixed - ideal|`의 최대값
- `mae`: 평균 절대 오차
- `rmse`: 제곱 평균 제곱근 오차
- `mean_err`: 평균 부호 오차(양수면 fixed가 평균적으로 큼)
- `sat_ratio`: fixed 출력이 `0` 또는 `255`인 비율
- `clip_needed_ratio`: ideal 출력이 `[0,255]`를 벗어난 비율

---

## 3. 전체 결과 요약

### 3.1 리포트 기본 평균(케이스 단순 평균)

| 항목                  |         값 |
| --------------------- | ---------: |
| num_cases             |         28 |
| num_samples_total     | 67,975,252 |
| avg_mae               |     1.1302 |
| avg_rmse              |     2.9380 |
| avg_mean_err          |     0.8871 |
| avg_sat_ratio         |     0.2579 |
| avg_clip_needed_ratio |     0.1137 |
| max_max_abs_err       |   118.0625 |

해석:

- 단순 평균 기준에서도 5-tap은 오차 크기가 상대적으로 낮게 관측된다.
- 다만 `edge`, `sharpen` 계수에서 clip 영향이 여전히 지배적이다.

### 3.2 샘플 수 가중 평균(추가 계산)

`compare_5tap_cases.csv`에서 샘플 수 기준으로 가중 평균을 별도 계산하였다.

| 항목                       |       값 |
| -------------------------- | -------: |
| weighted_mae               |   0.3243 |
| weighted_rmse              |   1.2739 |
| weighted_mean_err          |   0.2343 |
| weighted_sat_ratio         |   0.6661 |
| weighted_clip_needed_ratio |   0.0582 |
| weighted_psnr              | 46.03 dB |

해석:

- 픽셀 수 비중을 반영한 오차는 매우 작다(`RMSE < 2` gray level).
- large 이미지의 히스토그램 특성(0/255 다수)으로 `sat_ratio`는 높게 나타난다.

---

## 4. 필터별 성능 분석

### 4.1 케이스 단순 평균 기준

| Coeff      | avg_mae | avg_rmse | avg_mean_err | avg_sat_ratio | avg_clip_needed_ratio | max_abs_err(최대) |
| ---------- | ------: | -------: | -----------: | ------------: | --------------------: | ----------------: |
| edge       |  3.5577 |   8.1020 |       3.4714 |        0.6621 |                0.4255 |           95.6250 |
| moving_avg |  0.2038 |   0.2570 |      -0.0010 |        0.1142 |                0.0000 |            0.4000 |
| sharpen    |  0.5526 |   3.1345 |       0.0536 |        0.1407 |                0.0294 |          118.0625 |
| simple_lp  |  0.2066 |   0.2586 |       0.0242 |        0.1147 |                0.0000 |            0.5000 |

핵심 해석:

- `edge`가 가장 큰 오차군이며, `sharpen`이 그 다음이다.
- `moving_avg`, `simple_lp`는 매우 낮은 오차 범위를 유지한다.

### 4.2 필터별 오차 원인

1. `edge = [-1/8, -2/8, 0, 2/8, 1/8]`

- 1차 미분 성분을 강화하는 구조로 음수/양수 출력이 모두 빈번하다.
- `uint8` 출력 단계에서 음수는 `0`으로 clip되므로 오차가 커진다.

2. `moving_avg = [1/5, 1/5, 1/5, 1/5, 1/5]`

- `1/5`는 Q4.12에서 정확 표현 불가(`819/4096` 근사).
- 계수 양자화 오차는 작지만 지속적으로 누적된다.

3. `simple_lp = [1,4,6,4,1]/16`

- Q4.12에서 정확 표현 가능.
- 오차의 대부분은 계수 양자화가 아니라 출력 반올림/정수화 단계에서 발생한다.

4. `sharpen = [-1,-4,26,-4,-1]/16`

- Q4.12에서 정확 표현 가능하나 중심 계수 이득이 커서 overshoot/undershoot가 커진다.
- 결과적으로 `clip_needed_ratio`, `max_abs_err`가 증가한다.

### 4.3 `edge` 계수의 음수 원소가 주는 영향

5-tap edge 계수는 좌우 비대칭 차분을 확장한 형태이며, 본질적으로 부호가 있는 출력(gradient)을 생성한다.

주요 영향:

1. 부호 손실

- ideal에서는 음수 gradient를 유지하지만 fixed `uint8`에서는 `0`으로 clip된다.

2. 평균 오차 편향

- 음수 영역에서 `fixed - ideal = 0 - (음수)`가 되어 양의 오차가 누적된다.
- 실제로 `edge`의 `mean_err`가 양수(단순 평균 `+3.4714`)로 나타난다.

3. clip 지표 동반 상승

- `edge`의 `avg_clip_needed_ratio=0.4255`, `avg_sat_ratio=0.6621`로 타 계수 대비 현저히 높다.
- 따라서 `edge`의 MAE/RMSE는 정밀도 문제라기보다 출력 포맷 제약의 영향이 크다.

---

## 5. Worst-case 분석

RMSE 상위 5개 케이스는 모두 `edge` 계수 조합이다.

| 순위 | Key                                     |    RMSE |    MAE | clip_needed_ratio | sat_ratio |
| ---: | --------------------------------------- | ------: | -----: | ----------------: | --------: |
|    1 | case_004_img_005_64x64_noise_gray__edge | 13.4034 | 7.4164 |            0.5720 |    0.5876 |
|    2 | case_003_img_004_64x64_gray__edge       | 13.1737 | 7.1697 |            0.5757 |    0.5977 |
|    3 | case_006_img_007_1280x641_gray__edge    |  8.1734 | 3.4708 |            0.4818 |    0.5320 |
|    4 | case_001_img_002_640x762_gray__edge     |  7.0299 | 2.4094 |            0.4128 |    0.6134 |
|    5 | case_002_img_003_1280x854_gray__edge    |  6.3843 | 1.7632 |            0.4031 |    0.7525 |

해석:

- high-error 샘플은 주로 부호를 가진 edge 응답이 clip되는 구간과 일치한다.

---

## 6. 케이스 특성 관찰

### 6.1 `case_005_img_006_4499x2999_gray`의 특이점

- 입력에서 `0` 비율이 매우 높은 이미지 특성으로 인해 출력 `sat_ratio`가 높다.
- 본 케이스는 `edge`에서도 `RMSE`가 상대적으로 낮게 나타나며(`3.0438`), 이는 저명도 픽셀 지배 분포와 연관된다.

### 6.2 edge 대비 non-edge 오차 배율

이미지별로 `edge RMSE / (moving_avg, sharpen, simple_lp 평균 RMSE)`를 계산하면 약 `5.6x ~ 11.1x` 범위이다.
즉, 5-tap에서도 주된 오차 원인은 `edge`와 `uint8 clip` 결합 효과다.

---

## 7. 결론

1. 5-tap fixed 모델은 `moving_avg`, `simple_lp`에서 ideal 대비 매우 작은 오차를 보이며 충분히 안정적이다.
2. `sharpen`은 계수 자체는 정확히 표현되더라도 high-gain 특성으로 인해 clip 유발 오차가 증가한다.
3. `edge`는 부호 기반 응답을 `uint8`로 투영하면서 오차가 커지는 구조적 한계를 가진다.
4. 따라서 본 리포트는 "계수 양자화 한계"보다 "출력 표현 포맷(clip) 제약"의 영향이 큰 경우를 명확히 보여준다.

---

## 8. 향후 개선 제안

1. `edge/sharpen`에 대해 signed 출력(`int16`) 비교를 병행해 clip 영향과 계산 정밀도를 분리 평가할 필요가 있다.
2. 현행 지표(`fixed raw` vs `ideal raw`) 외에 `clip(ideal)` 대비 비교 지표를 함께 산출하면 해석 정확도가 높아진다.
3. 합성 이후 RTL 검증 단계에서는 본 통계 지표보다 픽셀 단위 bit-exact 비교를 우선 pass/fail 기준으로 사용해야 한다.

---

## 9. 근거 기반 정밀도 손실 판정

### 9.1 "표준 임계값"에 대한 정리

- MAE/RMSE 절대 임계값은 영상 종류, 필터 종류, 포맷 제약에 따라 달라 단일 고정 기준을 두기 어렵다.
- MSE/PSNR 계열 지표는 해석이 단순하지만 지각 품질과 완전히 일치하지 않는다.
- 따라서 본 과제에서는 동일 입력군에서의 모델 충실도와 구현 가능성을 함께 고려해야 한다.

### 9.2 본 보고서 데이터로 본 정량 근거

`edge`를 제외한 계수(`moving_avg`, `simple_lp`, `sharpen`)를 샘플 수 가중으로 합산하면:

- `MAE = 0.1247` gray level
- `RMSE = 0.4372` gray level
- `PSNR = 55.32 dB` (RMSE 기준 환산)
- `clip_needed_ratio = 0.01421`

이는 full scale(255) 대비 `RMSE = 0.171%` 수준으로, 평균적으로 정밀도 손실이 작은 편에 속한다.

### 9.3 양자화 이론 관점 교차 검증

반올림 양자화 오차를 `[-0.5, 0.5]` 균등 분포로 가정하면 기준 RMSE는 다음과 같다.

`RMSE_quant = sqrt(1/12) ≈ 0.2887`

5-tap non-edge 가중 RMSE(`0.4372`)는 위 기준보다 다소 크지만, 이는 `sharpen`의 고이득 구조에서 발생하는 클리핑 영향이 반영된 결과이다.
반면 `moving_avg=0.1757`, `simple_lp=0.1742`는 양자화 기준 이하로 유지된다.

결론적으로 5-tap에서도 low-pass 계열은 정밀도 손실이 매우 작고, 고이득 계수(`sharpen`, `edge`)는 clip-aware 해석이 필요하다.

### 9.4 `edge` 케이스 판정 방법

- `edge`의 높은 오차는 부호 정보 손실과 clipping의 결합 효과가 지배적이다.
- 따라서 `edge`를 동일 잣대로 "정밀도 부족"으로 결론내리면 해석이 왜곡될 수 있다.
- 권장 판정:
  - signed 출력 비교(`int16`)
  - 또는 `clip(ideal)` 기준 보조 리포트 병행

---

## 10. 참고 문헌

1. Wang, Z., Bovik, A. C., Sheikh, H. R., & Simoncelli, E. P. (2004). *Image Quality Assessment: From Error Visibility to Structural Similarity*. IEEE TIP, 13(4), 600-612.Link: https://ece.uwaterloo.ca/~z70wang/publications/ssim.pdf
2. Huynh-Thu, Q., & Ghanbari, M. (2008). *Scope of validity of PSNR in image/video quality assessment*. Electronics Letters, 44(13), 800-801.
   DOI: https://doi.org/10.1049/el:20080522
