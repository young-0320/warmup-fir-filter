// FIR Filter 1D idel Model using C++
// fir_1d_ref.h

#pragma once
#include <vector>

// reg_ 값이 곧 필터의 탭 수. 곧 필터 계수 h[n]의 원소 개수
class Fir1D {
 public:
  Fir1D() = default;
  explicit Fir1D(const std::vector<double>& h);

  void set_taps(const std::vector<double>& h);
  const std::vector<double>& taps() const;

  // Stateful sample-by-sample FIR: y[n] = sum(h[k] * x[n-k]).
  double process_sample(double x_n);
  void reset();

  // Block-based idel model equivalent to python fir_1d_idel(x, h).
  static std::vector<double> fir_1d_idel(const std::vector<double>& x,
                                           const std::vector<double>& h);

 private:
  std::vector<double> h_;    // 필터 계수
  std::vector<double> reg_;  // 과거 입력 값 메모리 -> 탭 개수
};
