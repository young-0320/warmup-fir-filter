# define coefficient of h
h_coeff_3tap_map ={
    "moving_avg" : [1/3, 1/3, 1/3],
    "simple_lp" : [0.25, 0.5, 0.25],
    "edge" : [-1.0, 0, 1.0],
    "sharpen" : [-0.125, 1.25, -0.125]
}


h_coeff_5tap_map ={
    "moving_avg" : [1/5, 1/5, 1/5, 1/5, 1/5],
    "simple_lp" : [1/16, 4/16, 6/16, 4/16, 1/16],
    "edge" : [-1/8, -2/8, 0, 2/8, 1/8],
    "sharpen" : [-1/16, -4/16, 26/16, -4/16, -1/16]
}