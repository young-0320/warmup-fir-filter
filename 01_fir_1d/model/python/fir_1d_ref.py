# FIR  Filter 1D Golden Model

def fir_1d_golden(x : list, h : list)->list:
    N = len(x)      # 입력 x의 길이
    L = len(h)      # 필터 h의 길이
    # M = L - 1       # 차수
    Ny = N + L - 1  # 출력 신호 길이 

    y = [0.0] * Ny

    for n in range(Ny):
        result = 0.0
        for k in range(L):
            # 인덱스 경계 검사: x[n-k]가 유효한 범위인지 확인
            if 0 <= n - k < N:
                result += h[k] * x[n - k]
        y[n] = result
        
    return y
        


