from fir_1d.model.python.fir_1d_fixed_ref import fir_1d_fixed_golden as FIR_1D_GOLDEN


class TestFir1DFixed:
    def setup_method(self):
        # Q1.7 real range: -1.0 ~ 0.9921875
        self.h_coeff = [0.1, 0.5, 0.3, 0.1]

    def test_fixed_impulse_response(self):
        # Fixed model interprets input as 0~255 integer pixels.
        impulse = [255, 0, 0, 0]
        result = FIR_1D_GOLDEN(impulse, self.h_coeff)

        # h -> Q1.7 quantized: [13, 64, 38, 13]
        # output = (255 * h_q) >> 7 => [25, 127, 75, 25]
        expected = [25, 127, 75, 25]
        assert result[: len(expected)] == expected
