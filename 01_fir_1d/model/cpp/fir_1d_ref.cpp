// fir_1d_ref.cpp
// Direct Form I
#include "fir_1d_ref.h"

#include <iostream>

Fir1D::Fir1D(const std::vector<double>& h) { set_taps(h); }

void Fir1D::set_taps(const std::vector<double>& h) {
  h_ = h;
  reg_.assign(h_.size(), 0.0);  // 0.0으로 모든 탭의 값을 초기화
}

const std::vector<double>& Fir1D::taps() const { return h_; }

double Fir1D::process_sample(double x_n) {
  if (h_.empty()) {
    return 0.0;
  }
  // 오른쪽으로 한 칸 데이터 이동
  for (std::size_t i = reg_.size() - 1; i > 0; --i) {
    reg_[i] = reg_[i - 1];
  }
  // 새 데이터 입력
  reg_[0] = x_n;

  // 가중합
  double y_n = 0.0;
  for (std::size_t k = 0; k < h_.size(); ++k) {
    y_n += h_[k] * reg_[k];
  }
  return y_n;
}

void Fir1D::reset() { reg_.assign(h_.size(), 0.0); }

std::vector<double> Fir1D::fir_1d_golden(const std::vector<double>& x,
                                         const std::vector<double>& h) {
  const std::size_t n_len = x.size();  // 입력 길이
  const std::size_t l_len = h.size();  // 계수 길이

  if (n_len == 0 || l_len == 0) {
    return {};
  }
  // 출력 길이 = n + l - 1
  const std::size_t y_len = n_len + l_len - 1;
  std::vector<double> y(y_len, 0.0);

  for (std::size_t n = 0; n < y_len; ++n) {
    double result = 0.0;
    for (std::size_t k = 0; k < l_len; ++k) {
      if (n >= k) {
        const std::size_t x_idx = n - k;
        if (x_idx < n_len) {
          result += h[k] * x[x_idx];
        }
      }
    }
    y[n] = result;
  }

  return y;
}
