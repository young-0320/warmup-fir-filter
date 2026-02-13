# # FIR  Filter 1D Fixed Golden Model

def fir_1d_fixed_golden(
    x: list[float],
    h: list[float],
    data_bits: int = 16,
    frac_bits: int = 15,
    acc_bits: int = 32,
) -> list[float]:
    """
    Fixed-point 1D FIR golden model (Q(data_bits-frac_bits).frac_bits).
    - input/tap: float -> quantize to signed Q format
    - multiply/accumulate: integer domain
    - output: requantize back to input Q format with rounding + saturation
    - return: de-quantized float list
    """

    data_min = -(1 << (data_bits - 1))
    data_max = (1 << (data_bits - 1)) - 1
    acc_min = -(1 << (acc_bits - 1))
    acc_max = (1 << (acc_bits - 1)) - 1
    scale = 1 << frac_bits

    def sat(v: int, vmin: int, vmax: int) -> int:
        if v < vmin:
            return vmin
        if v > vmax:
            return vmax
        return v

    def round_shift_right(v: int, shift: int) -> int:
        if shift <= 0:
            return v
        add = 1 << (shift - 1)
        if v >= 0:
            return (v + add) >> shift
        return -(((-v) + add) >> shift)

    def q_from_float(v: float) -> int:
        q = int(round(v * scale))
        return sat(q, data_min, data_max)

    x_q = [q_from_float(v) for v in x]
    h_q = [q_from_float(v) for v in h]

    n_len = len(x_q)
    l_len = len(h_q)
    if n_len == 0 or l_len == 0:
        return []

    y_len = n_len + l_len - 1
    y_q = [0] * y_len

    for n in range(y_len):
        acc = 0
        for k in range(l_len):
            x_idx = n - k
            if 0 <= x_idx < n_len:
                prod = x_q[x_idx] * h_q[k]  # Q(2*frac_bits)
                acc = sat(acc + prod, acc_min, acc_max)

        y_n_q = round_shift_right(acc, frac_bits)  # back to Q(frac_bits)
        y_q[n] = sat(y_n_q, data_min, data_max)

    return [v / scale for v in y_q]
