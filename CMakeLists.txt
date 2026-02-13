# Root CMakeLists.txt
cmake_minimum_required(VERSION 3.10)
project(CPP_PRACTICE VERSION 1.0)

# 하위 디렉토리 추가 (컴파일 순서 제어)
add_subdirectory(lib)

add_subdirectory(01_fir_1d/model/cpp)
add_subdirectory(02_fir_2d/model/cpp)
