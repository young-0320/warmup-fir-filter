// mycomplex.cpp

#include "mycomplex.h"

void MyComplex::show() const {
  using std::cout, std::endl;
  char c;
  c = (y_ > 0) ? '+' : '-';
  cout << x_ << " " << c << " " << "i" << y_;
}

MyComplex MyComplex::operator+(const MyComplex& t) const {
  return MyComplex((x_ + t.x_), (y_ + t.y_));
}

MyComplex MyComplex::operator-(const MyComplex& t) const {
  return MyComplex((x_ - t.x_), (y_ - t.y_));
}
// * 오버로딩
MyComplex MyComplex::operator*(double n) const {
  return MyComplex(x_ * n, y_ * n);
}

// 복소수 끼리의 나눗셈
MyComplex MyComplex::operator/(const MyComplex& t) const {
  double check = (t.x_) * (t.x_) + (t.y_) * (t.y_);  // 분모가 0일때
  if (check == 0) {
    return MyComplex(0, 0);
  }
  double new_x = (x_ * t.x_ + y_ * t.y_) / check;
  double new_y = (y_ * t.x_ - x_ * t.y_) / check;

  return MyComplex(new_x, new_y);
}
// 프렌드 오버로딩
MyComplex operator+(double a, const MyComplex& t) {
  return MyComplex(t.x_ + a, t.y_);
}
MyComplex operator-(double a, const MyComplex& t) {
  return MyComplex(t.x_ - a, t.y_);
}
MyComplex operator*(double a, const MyComplex& t) { return t * a; }

std::ostream& operator<<(std::ostream& os, const MyComplex& t) {
  t.show();
  return os;
}