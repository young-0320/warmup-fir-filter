// main
#include <iostream>

#include "fir_1d_ref.h"

int main() {
  const std::vector<double> x = {1.0, 3.0, 5.0};
  const std::vector<double> h = {0.5, 0.5};
  const std::vector<double> y = Fir1D::fir_1d_golden(x, h);
  std::cout << "START" << std::endl;
  std::cout << "y = [";
  for (std::size_t i = 0; i < y.size(); ++i) {
    std::cout << y[i];
    if (i + 1 < y.size()) {
      std::cout << ", ";
    }
  }
  std::cout << "]\n";
  return 0;
}
