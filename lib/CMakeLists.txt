# lib/CMakeLists.txt

add_library(mycomplex STATIC 
    mycomplex.cpp 
    mycomplex.h
)

# 이 라이브러리를 사용하는 다른 타겟들이 헤더 위치를 알 수 있게 공개합니다.
target_include_directories(mycomplex PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})