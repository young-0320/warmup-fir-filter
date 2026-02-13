# model/cpp/CMakeList
# model/cpp 파일을 라이브러리화
add_library(fir_1d_ref STATIC fir_1d_ref.cpp)

target_include_directories(fir_1d_ref
    PUBLIC 
        ${CMAKE_CURRENT_SOURCE_DIR}
)

# 범용 라이브러리를 fir_1d_ref와 연결
target_link_libraries(fir_1d_ref PUBLIC mycomplex)



