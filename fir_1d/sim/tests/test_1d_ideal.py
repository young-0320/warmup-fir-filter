# fir_1d_ref.py test code
# unit test
# Arrange (준비): 테스트에 필요한 재료(입력 신호, 필터 계수, 기대값)를 세팅합니다.

# Act (실행): 실제로 검증할 함수(FIR_1D)를 딱 한 번 실행합니다.

# Assert (검증): 결과가 기대값과 오차 범위 내에서 일치하는지 확인합니다.

import pytest

from fir_1d.model.python.fir_1d_ref import fir_1d_ideal as FIR_1D

class TestFir1DIdeal:
    # 준비
    def setup_method(self):
        self.h_coeff = [0.1, 0.5, 0.3, 0.1]

    def test_ideal_impulse_response(self):
        impulse = [1 ,0, 0, 0]
        # 실행
        result = FIR_1D(impulse, self.h_coeff)
        # 검증
        assert result[:len(self.h_coeff)] == pytest.approx(self.h_coeff, abs=1e-12)

    




    
    
