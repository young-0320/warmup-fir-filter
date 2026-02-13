# lib/CMakeLists.txt
# lib 폴더 내부의 파일을 범용 라이브러리로 생성
add_library(mycomplex STATIC 
    mycomplex.cpp 
)
# 이 라이브러리를 사용하는 다른 타겟들이 헤더 위치를 알 수 있게 공개합니다.
target_include_directories(mycomplex PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})