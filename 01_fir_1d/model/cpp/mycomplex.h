// myMyComplex.h

#pragma once
#ifndef MY_COMPLEX_H
#define MY_COMPLEX_H
#include <cmath>
#include <iostream>
inline const double PI = acos(-1.0);
// x+iy
class MyComplex {
 public:
  // 생성자
  MyComplex() = default;
  MyComplex(double x, double y) : x_(x), y_(y) {}
  explicit MyComplex(double theta) : x_(cos(theta)), y_(sin(theta)) {}

  // 멤버 함수
  double get_magnitude() const { return std::sqrt(x_ * x_ + y_ * y_); }

  void show() const;
  void set_value(double a, double b) {
    x_ = a;
    y_ = b;
  }

  // 연산자 오버로딩
  MyComplex operator+(const MyComplex& t) const;
  MyComplex operator-(const MyComplex& t) const;
  MyComplex operator*(double n) const;
  MyComplex operator/(const MyComplex& t) const;


  // 프렌드 함수
  friend MyComplex operator+(double a, const MyComplex& t);
  friend MyComplex operator-(double a, const MyComplex& t);
  friend std::ostream& operator<<(std::ostream& os, const MyComplex& t);
  friend MyComplex operator*(double a, const MyComplex& t);

 private:
  double x_ = 0.0, y_ = 0.0;
};
#endif