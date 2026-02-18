# sim/test/CMakeLists

# 실행 파일 생성
# add_executable(test_fir_1d
    test_fir_1d_golden.cpp
  )

# fir_1d_ref가 PUBLIC으로 공개한 헤더 경로와 컴파일 옵션을 자동으로 상속받습니다.
# target_link_libraries(test_fir_1d PRIVATE fir_1d_ref)