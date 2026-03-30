# -*- coding: utf-8 -*-
"""
TTPlus Data Tool  –  Version 6.0
Developed by Nature4.0 and FEM teams.

Changes in v6.0 (redesign for robustness):
  - All processing logic extracted into top-level functions 
  - Logging to file + live GUI output window 
  - Per-device error isolation: one bad device never aborts the full run
  - Input validation before any processing starts
  - Nighttime dTmax filter (8 pm – 8 am) applied to BOTH 4D and 45
  - Lookup tables and calibration constants at module level
"""

# ── IMPORTS ───────────────────────────────────────────────────────────────────
import ssl
import sys
import os
import glob
import json
import logging
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import pytz
import urllib.request
from scipy.interpolate import interp1d
import plotly.express as px
import plotly
import FreeSimpleGUI as sg


# ── CONSTANTS ─────────────────────────────────────────────────────────────────

TREE_TYPES = ["diffuse-porous", "dluhosch_10-50"]

# ---- TT+3.1 (device type 45) temperature lookup ----
# Raw ADC counts → temperature in 1/10 °C  (divide result by 10 afterwards)
LUT_45_X = [
    1453, 1456.5, 1460, 1463.5, 1467, 1470.5, 1474, 1477.5, 1481, 1484.5,
    1488, 1491.6, 1495.2, 1498.8, 1502.4, 1506, 1509.6, 1513.2, 1516.8,
    1520.4, 1524, 1527.6, 1531.2, 1534.8, 1538.4, 1542, 1545.6, 1549.2,
    1552.8, 1556.4, 1560, 1563.7, 1567.4, 1571.1, 1574.8, 1578.5, 1582.2,
    1585.9, 1589.6, 1593.3, 1597, 1600.9, 1604.8, 1608.7, 1612.6, 1616.5,
    1620.4, 1624.3, 1628.2, 1632.1, 1636, 1639.9, 1643.8, 1647.7, 1651.6,
    1655.5, 1659.4, 1663.3, 1667.2, 1671.1, 1675, 1679.1, 1683.2, 1687.3,
    1691.4, 1695.5, 1699.6, 1703.7, 1707.8, 1711.9, 1716, 1720.1, 1724.2,
    1728.3, 1732.4, 1736.5, 1740.6, 1744.7, 1748.8, 1752.9, 1757, 1761.3,
    1765.6, 1769.9, 1774.2, 1778.5, 1782.8, 1787.1, 1791.4, 1795.7, 1800,
    1804.3, 1808.6, 1812.9, 1817.2, 1821.5, 1825.8, 1830.1, 1834.4, 1838.7,
    1843, 1847.5, 1852, 1856.5, 1861, 1865.5, 1870, 1874.5, 1879, 1883.5,
    1888, 1892.5, 1897, 1901.5, 1906, 1910.5, 1915, 1919.5, 1924, 1928.5,
    1933, 1937.7, 1942.4, 1947.1, 1951.8, 1956.5, 1961.2, 1965.9, 1970.6,
    1975.3, 1980, 1984.8, 1989.6, 1994.4, 1999.2, 2004, 2008.8, 2013.6,
    2018.4, 2023.2, 2028, 2032.9, 2037.8, 2042.7, 2047.6, 2052.5, 2057.4,
    2062.3, 2067.2, 2072.1, 2077, 2082, 2087, 2092, 2097, 2102, 2107,
    2112, 2117, 2122, 2127, 2132.2, 2137.4, 2142.6, 2147.8, 2153, 2158.2,
    2163.4, 2168.6, 2173.8, 2179, 2184.3, 2189.6, 2194.9, 2200.2, 2205.5,
    2210.8, 2216.1, 2221.4, 2226.7, 2232, 2237.5, 2243, 2248.5, 2254,
    2259.5, 2265, 2270.5, 2276, 2281.5, 2287, 2292.5, 2298, 2303.5, 2309,
    2314.5, 2320, 2325.5, 2331, 2336.5, 2342, 2347.8, 2353.6, 2359.4,
    2365.2, 2371, 2376.8, 2382.6, 2388.4, 2394.2, 2400, 2405.8, 2411.6,
    2417.4, 2423.2, 2429, 2434.8, 2440.6, 2446.4, 2452.2, 2458, 2464.1,
    2470.2, 2476.3, 2482.4, 2488.5, 2494.6, 2500.7, 2506.8, 2512.9, 2519,
    2525.1, 2531.2, 2537.3, 2543.4, 2549.5, 2555.6, 2561.7, 2567.8, 2573.9,
    2580, 2586.4, 2592.8, 2599.2, 2605.6, 2612, 2618.4, 2624.8, 2631.2,
    2637.6, 2644, 2650.5, 2657, 2663.5, 2670, 2676.5, 2683, 2689.5, 2696,
    2702.5, 2709, 2715.6, 2722.2, 2728.8, 2735.4, 2742, 2748.6, 2755.2,
    2761.8, 2768.4, 2775, 2781.8, 2788.6, 2795.4, 2802.2, 2809, 2815.8,
    2822.6, 2829.4, 2836.2, 2843, 2850, 2857, 2864, 2871, 2878, 2885,
    2892, 2899, 2906, 2913, 2920.1, 2927.2, 2934.3, 2941.4, 2948.5, 2955.6,
    2962.7, 2969.8, 2976.9, 2984, 2991.3, 2998.6, 3005.9, 3013.2, 3020.5,
    3027.8, 3035.1, 3042.4, 3049.7, 3057, 3064.5, 3072, 3079.5, 3087,
    3094.5, 3102, 3109.5, 3117, 3124.5, 3132, 3139.6, 3147.2, 3154.8,
    3162.4, 3170, 3177.6, 3185.2, 3192.8, 3200.4, 3208, 3215.8, 3223.6,
    3231.4, 3239.2, 3247, 3254.8, 3262.6, 3270.4, 3278.2, 3286, 3294,
    3302, 3310, 3318, 3326, 3334, 3342, 3350, 3358, 3366, 3374.2, 3382.4,
    3390.6, 3398.8, 3407, 3415.2, 3423.4, 3431.6, 3439.8, 3448, 3456.3,
    3464.6, 3472.9, 3481.2, 3489.5, 3497.8, 3506.1, 3514.4, 3522.7, 3531,
    3539.6, 3548.2, 3556.8, 3565.4, 3574, 3582.6, 3591.2, 3599.8, 3608.4,
    3617, 3625.8, 3634.6, 3643.4, 3652.2, 3661, 3669.8, 3678.6, 3687.4,
    3696.2, 3705, 3713.9, 3722.8, 3731.7, 3740.6, 3749.5, 3758.4, 3767.3,
    3776.2, 3785.1, 3794, 3803.3, 3812.6, 3821.9, 3831.2, 3840.5, 3849.8,
    3859.1, 3868.4, 3877.7, 3887, 3896.5, 3906, 3915.5, 3925, 3934.5,
    3944, 3953.5, 3963, 3972.5, 3982, 3991.7, 4001.4, 4011.1, 4020.8,
    4030.5, 4040.2, 4049.9, 4059.6, 4069.3, 4079, 4088.9, 4098.8, 4108.7,
    4118.6, 4128.5, 4138.4, 4148.3, 4158.2, 4168.1, 4178, 4188.1, 4198.2,
    4208.3, 4218.4, 4228.5, 4238.6, 4248.7, 4258.8, 4268.9, 4279, 4289.2,
    4299.4, 4309.6, 4319.8, 4330, 4340.2, 4350.4, 4360.6, 4370.8, 4381,
    4391.5, 4402, 4412.5, 4423, 4433.5, 4444, 4454.5, 4465, 4475.5, 4486,
    4496.7, 4507.4, 4518.1, 4528.8, 4539.5, 4550.2, 4560.9, 4571.6, 4582.3,
    4593, 4604, 4615, 4626, 4637, 4648, 4659, 4670, 4681, 4692, 4703,
    4714.1, 4725.2, 4736.3, 4747.4, 4758.5, 4769.6, 4780.7, 4791.8, 4802.9,
    4814, 4825.3, 4836.6, 4847.9, 4859.2, 4870.5, 4881.8, 4893.1, 4904.4,
    4915.7, 4927, 4938.5, 4950, 4961.5, 4973, 4984.5, 4996, 5007.5, 5019,
    5030.5, 5042, 5053.7, 5065.4, 5077.1, 5088.8, 5100.5, 5112.2, 5123.9,
    5135.6, 5147.3, 5159, 5171, 5183, 5195, 5207, 5219, 5231, 5243, 5255,
    5267, 5279, 5291.1, 5303.2, 5315.3, 5327.4, 5339.5, 5351.6, 5363.7,
    5375.8, 5387.9, 5400, 5412.3, 5424.6, 5436.9, 5449.2, 5461.5, 5473.8,
    5486.1, 5498.4, 5510.7, 5523, 5535.6, 5548.2, 5560.8, 5573.4, 5586,
    5598.6, 5611.2, 5623.8, 5636.4, 5649, 5661.7, 5674.4, 5687.1, 5699.8,
    5712.5, 5725.2, 5737.9, 5750.6, 5763.3, 5776, 5788.9, 5801.8, 5814.7,
    5827.6, 5840.5, 5853.4, 5866.3, 5879.2, 5892.1, 5905, 5918.1, 5931.2,
    5944.3, 5957.4, 5970.5, 5983.6, 5996.7, 6009.8, 6022.9, 6036, 6049.2,
    6062.4, 6075.6, 6088.8, 6102, 6115.2, 6128.4, 6141.6, 6154.8, 6168,
    6181.5, 6195, 6208.5, 6222, 6235.5, 6249, 6262.5, 6276, 6289.5, 6303,
    6316.6, 6330.2, 6343.8, 6357.4, 6371, 6384.6, 6398.2, 6411.8, 6425.4,
    6439, 6452.8, 6466.6, 6480.4, 6494.2, 6508, 6521.8, 6535.6, 6549.4,
    6563.2, 6577, 6590.9, 6604.8, 6618.7, 6632.6, 6646.5, 6660.4, 6674.3,
    6688.2, 6702.1, 6716, 6730.1, 6744.2, 6758.3, 6772.4, 6786.5, 6800.6,
    6814.7, 6828.8, 6842.9, 6857, 6871.3, 6885.6, 6899.9, 6914.2, 6928.5,
    6942.8, 6957.1, 6971.4, 6985.7, 7000, 7014.5, 7029, 7043.5, 7058,
    7072.5, 7087, 7101.5, 7116, 7130.5, 7145, 7159.5, 7174, 7188.5, 7203,
    7217.5, 7232, 7246.5, 7261, 7275.5, 7290, 7304.8, 7319.6, 7334.4,
    7349.2, 7364, 7378.8, 7393.6, 7408.4, 7423.2, 7438, 7452.8, 7467.6,
    7482.4, 7497.2, 7512, 7526.8, 7541.6, 7556.4, 7571.2, 7586, 7601,
    7616, 7631, 7646, 7661, 7676, 7691, 7706, 7721, 7736, 7751.1, 7766.2,
    7781.3, 7796.4, 7811.5, 7826.6, 7841.7, 7856.8, 7871.9, 7887, 7902.2,
    7917.4, 7932.6, 7947.8, 7963, 7978.2, 7993.4, 8008.6, 8023.8, 8039,
    8054.3, 8069.6, 8084.9, 8100.2, 8115.5, 8130.8, 8146.1, 8161.4, 8176.7,
    8192, 8207.3, 8222.6, 8237.9, 8253.2, 8268.5, 8283.8, 8299.1, 8314.4,
    8329.7, 8345, 8360.4, 8375.8, 8391.2, 8406.6, 8422, 8437.4, 8452.8,
    8468.2, 8483.6, 8499, 8514.4, 8529.8, 8545.2, 8560.6, 8576, 8591.4,
    8606.8, 8622.2, 8637.6, 8653, 8668.5, 8684, 8699.5, 8715, 8730.5,
    8746, 8761.5, 8777, 8792.5, 8808, 8823.5, 8839, 8854.5, 8870, 8885.5,
    8901, 8916.5, 8932, 8947.5, 8963, 8978.6, 8994.2, 9009.8, 9025.4,
    9041, 9056.6, 9072.2, 9087.8, 9103.4, 9119, 9134.6, 9150.2, 9165.8,
    9181.4, 9197, 9212.6, 9228.2, 9243.8, 9259.4, 9275, 9290.6, 9306.2,
    9321.8, 9337.4, 9353, 9368.6, 9384.2, 9399.8, 9415.4, 9431, 9446.6,
    9462.2, 9477.8, 9493.4, 9509, 9524.6, 9540.2, 9555.8, 9571.4, 9587,
    9602.6, 9618.2, 9633.8, 9649.4, 9665, 9680.6, 9696.2, 9711.8, 9727.4,
    9743, 9758.6, 9774.2, 9789.8, 9805.4, 9821, 9836.6, 9852.2, 9867.8,
    9883.4, 9899, 9914.5, 9930, 9945.5, 9961, 9976.5, 9992, 10007.5, 10023,
    10038.5, 10054, 10069.5, 10085, 10100.5, 10116, 10131.5, 10147, 10162.5,
    10178, 10193.5, 10209, 10224.4, 10239.8, 10255.2, 10270.6, 10286,
    10301.4, 10316.8, 10332.2, 10347.6, 10363, 10378.3, 10393.6, 10408.9,
    10424.2, 10439.5, 10454.8, 10470.1, 10485.4, 10500.7, 10516, 10531.3,
    10546.6, 10561.9, 10577.2, 10592.5, 10607.8, 10623.1, 10638.4, 10653.7,
    10669, 10684.1, 10699.2, 10714.3, 10729.4, 10744.5, 10759.6, 10774.7,
    10789.8, 10804.9, 10820, 10835, 10850, 10865, 10880, 10895, 10910,
    10925, 10940, 10955, 10970, 10984.9, 10999.8, 11014.7, 11029.6,
    11044.5, 11059.4, 11074.3, 11089.2, 11104.1, 11119, 11133.8, 11148.6,
    11163.4, 11178.2, 11193, 11207.8, 11222.6, 11237.4, 11252.2, 11267,
    11281.6, 11296.2, 11310.8, 11325.4, 11340, 11354.6, 11369.2, 11383.8,
    11398.4, 11413, 11427.5, 11442, 11456.5, 11471, 11485.5, 11500,
    11514.5, 11529, 11543.5, 11558, 11572.3, 11586.6, 11600.9, 11615.2,
    11629.5, 11643.8, 11658.1, 11672.4, 11686.7, 11701, 11715.1, 11729.2,
    11743.3, 11757.4, 11771.5, 11785.6, 11799.7, 11813.8, 11827.9, 11842,
    11855.9, 11869.8, 11883.7, 11897.6, 11911.5, 11925.4, 11939.3, 11953.2,
    11967.1, 11981, 11994.8, 12008.6, 12022.4, 12036.2, 12050, 12063.8,
    12077.6, 12091.4, 12105.2, 12119, 12132.6, 12146.2, 12159.8, 12173.4,
    12187, 12200.6, 12214.2, 12227.8, 12241.4, 12255, 12268.4, 12281.8,
    12295.2, 12308.6, 12322, 12335.4, 12348.8, 12362.2, 12375.6, 12389,
    12402.2, 12415.4, 12428.6, 12441.8, 12455, 12468.2, 12481.4, 12494.6,
    12507.8, 12521, 12534, 12547, 12560, 12573, 12586, 12599, 12612,
    12625, 12638, 12651, 12663.7, 12676.4, 12689.1, 12701.8, 12714.5,
    12727.2, 12739.9, 12752.6, 12765.3, 12778, 12790.5, 12803, 12815.5,
    12828, 12840.5, 12853, 12865.5, 12878, 12890.5, 12903, 12915.2,
    12927.4, 12939.6, 12951.8, 12964, 12976.2, 12988.4, 13000.6, 13012.8,
    13025, 13037.1, 13049.2, 13061.3, 13073.4, 13085.5, 13097.6, 13109.7,
    13121.8, 13133.9, 13146, 13157.7, 13169.4, 13181.1, 13192.8, 13204.5,
    13216.2, 13227.9, 13239.6, 13251.3, 13263, 13274.5, 13286, 13297.5,
    13309, 13320.5, 13332, 13343.5, 13355, 13366.5, 13378, 13389.1,
    13400.2, 13411.3, 13422.4, 13433.5, 13444.6, 13455.7, 13466.8, 13477.9,
    13489, 13500, 13511, 13522, 13533, 13544, 13555, 13566, 13577, 13588,
    13599, 13609.6, 13620.2, 13630.8, 13641.4, 13652, 13662.6, 13673.2,
    13683.8, 13694.4, 13705, 13715.4, 13725.8, 13736.2, 13746.6, 13757,
    13767.4, 13777.8, 13788.2, 13798.6, 13809, 13819.2, 13829.4, 13839.6,
    13849.8, 13860, 13870.2, 13880.4, 13890.6, 13900.8, 13911, 13920.8,
    13930.6, 13940.4, 13950.2, 13960, 13969.8, 13979.6, 13989.4, 13999.2,
    14009, 14018.6, 14028.2, 14037.8, 14047.4, 14057, 14066.6, 14076.2,
    14085.8, 14095.4, 14105, 14114.4, 14123.8, 14133.2, 14142.6, 14152,
    14161.4, 14170.8, 14180.2, 14189.6, 14199, 14208, 14217, 14226, 14235,
    14244, 14253, 14262, 14271, 14280, 14289,
]
LUT_45_Y = list(range(1000, -201, -1))   # 1000 → -200  (1201 values)

# ---- TT+3.2 (device type 4D) temperature lookup ----
# Raw ADC counts → temperature in °C (direct)
LUT_4D_X = [
    57159, 56799, 56423, 56039, 55647, 55239, 54822, 54398, 53958, 53514,
    53054, 52585, 52101, 51612, 51112, 50604, 50084, 49557, 49021, 48478,
    47927, 47370, 46806, 46233, 45653, 45069, 44477, 43882, 43282, 42679,
    42068, 41455, 40839, 40219, 39599, 38975, 38351, 37727, 37103, 36479,
    35856, 35235, 34614, 33997, 33380, 32768, 32156, 31548, 30944, 30344,
    29753, 29161, 28581, 28002, 27430, 26867, 26310, 25758, 25214, 24674,
    24146, 23622, 23106, 22598, 22094, 21602, 21117, 20637, 20168, 19708,
    19256, 18812, 18372, 17944, 17524, 17116, 16712, 16316, 15928, 15548,
    15177, 14821, 14469, 14125, 13793, 13465, 13145, 12834, 12530, 12231,
    11940, 11655, 11375, 11103, 10839, 10579, 10323, 10079, 9836, 9604,
    9373, 9152, 8931, 8718, 8509, 8309, 8113, 7921, 7733, 7553,
    7374, 7202, 7030, 6866, 6702, 6547, 6391, 6243, 6099, 5955, 5816,
]
LUT_4D_Y = list(range(-20, 101))   # -20 → 100  (121 values)

# ---- Spectrometer calibration denominators (device type 49) ----
SPEC_CALIB = {
    'AS7263_610': 989.1,  'AS7263_680': 957.1,  'AS7263_730': 943.2,
    'AS7263_760': 915.2,  'AS7263_810': 1000.9, 'AS7263_860': 994.3,
    'AS7262_450': 2214.6, 'AS7262_500': 2002.7, 'AS7262_550': 1715.4,
    'AS7262_570': 1690.9, 'AS7262_600': 1605.8, 'AS7262_650': 1542.6,
}

# Column output definitions (col → (unit description, plot_type))
COLS_45 = {
    'Vbat':              'Battery voltage (mV)',
    'airT':              'Air Temperature (°C)',
    'RH':                'relative humidity (%)',
    'dT1':               'Temp diff heater+ref (°C)',
    'dTmax1':            'dT1 rolling-24H max (°C)',
    'dTmax1_filtered':   'dT1 nighttime rolling-24H max (°C)',
    'dT2':               'Temp diff heater only (°C)',
    'dTmax2':            'dT2 rolling-24H max (°C)',
    'dTmax2_filtered':   'dT2 nighttime rolling-24H max (°C)',
    'SFD1':              'Sap flux density TDM – both probes (g m⁻² s⁻¹)',
    'SFD2':              'Sap flux density TDM – heater only (g m⁻² s⁻¹)',
    'dis':               'Growth sensor dist from bark (mm)',
    'yaw':               'Stability Z (°)',
    'pitch':             'Stability Y (°)',
    'roll':              'Stability X (°)',
}

COLS_4D = {
    'Vbat':    'Battery voltage (mV)',
    'airT':    'Air Temperature (°C)',
    'RH':      'relative humidity (%)',
    'dT1':     'Temp diff heater+ref (°C)',
    'dTmax1':  'dT1 rolling-24H max (°C)',
    'dTmax1_filtered': 'dT1 nighttime rolling-24H max (°C)',
    'dT2':     'Temp diff heater only (°C)',
    'dTmax2':  'dT2 rolling-24H max (°C)',
    'dTmax2_filtered': 'dT2 nighttime rolling-24H max (°C)',
    'SFD1':    'Sap flux density TDM – both probes (g m⁻² s⁻¹)',
    'SFD2':    'Sap flux density TDM – heater only (g m⁻² s⁻¹)',
    'dis':     'Growth sensor dist from bark (mm)',
    'yaw':     'Stability Z (°)',
    'pitch':   'Stability Y (°)',
    'roll':    'Stability X (°)',
}

COLS_4B = {
    'Vbat':      'Cloud battery level (mV)',
    'GSM field': 'Signal strength',
}

COLS_49 = {
    'ndvi': 'Normalized Difference Vegetation Index (NDVI)',
}


# ── LOGGING ───────────────────────────────────────────────────────────────────

class _GUILogHandler(logging.Handler):
    """Routes log records to a FreeSimpleGUI Output element."""

    def __init__(self, window, key: str):
        super().__init__()
        self._win = window
        self._key = key

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        try:
            self._win[self._key].print(msg)
        except Exception:
            pass  # window may be closed


def setup_logging(log_path: Path, gui_window=None, gui_key: str = '-LOG-') -> logging.Logger:
    """Create (or reconfigure) the 'TTplus' logger with file + optional GUI handlers."""
    logger = logging.getLogger('TTplus')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler – always on
    fh = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s  [%(levelname)-8s]  %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fh)

    # GUI handler – only when a window is provided
    if gui_window is not None:
        gh = _GUILogHandler(gui_window, gui_key)
        gh.setLevel(logging.INFO)
        gh.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(gh)

    return logger


# ── CONFIG I/O ────────────────────────────────────────────────────────────────

def save_config(values: dict, file_path: str) -> None:
    with open(file_path, 'w') as f:
        json.dump(values, f, indent=4)


def load_config(file_path: str) -> dict:
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}


# ── INPUT VALIDATION ──────────────────────────────────────────────────────────

def validate_inputs(values: dict) -> tuple:
    """Return (ok: bool, error_message: str).  Empty string means ok."""
    if not values.get('folder'):
        return False, "Output folder is required."
    if values.get('timezone') not in pytz.all_timezones:
        return False, f"Invalid timezone: '{values.get('timezone')}'"
    if not values.get('start_date') or not values.get('end_date'):
        return False, "Start and end dates are required."
    try:
        pd.to_datetime(values['start_date'])
        pd.to_datetime(values['end_date'])
    except Exception:
        return False, "Could not parse start/end date.  Use format YYYY-MM-DD HH:MM:SS"
    if values.get('tree_probe') and values.get('soil_probe'):
        return False, "Select Tree OR Soil probe, not both."
    if not values.get('tree_probe') and not values.get('soil_probe'):
        return False, "Select at least one probe type (Tree or Soil)."
    if not values.get('item_id') and not values.get('manual_upload'):
        return False, "Provide a device serial number or a manual data folder."
    species = values.get('species_type', '')
    if values.get('tree_probe') and species not in TREE_TYPES:
        return False, f"Invalid species type: '{species}'.  Choose from {TREE_TYPES}"
    return True, ''


# ── DATA LOADING ──────────────────────────────────────────────────────────────

def read_server_data(url: str, logger: logging.Logger) -> list:
    """Fetch ALL data rows from a remote TT cloud URL.  Returns list-of-lists.

    Note: no row limit is applied — the server file may contain years of
    history and the date filter happens downstream.  A row limit here would
    silently discard older data if the server returns newest rows first.
    """
    all_rows = []
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, context=context) as resp:
            for line in resp:
                decoded = line.decode('UTF-8').strip().replace(',', ';')
                if decoded:
                    all_rows.append(decoded.split(';'))
        logger.info(f"Server: loaded {len(all_rows)} rows from {url}")
    except Exception as exc:
        logger.warning(f"Could not load from {url}: {exc}")
    return all_rows


def read_folder_files(folder_path: str, logger: logging.Logger) -> list:
    """Read all .csv and .txt files in folder.  Prepends a dummy '0' server_time column."""
    all_rows = []
    for ext in ('*.csv', '*.txt'):
        for fp in glob.glob(os.path.join(folder_path, ext)):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            fields = ['0'] + line.strip().split(';')
                            all_rows.append(fields)
            except Exception as exc:
                logger.warning(f"Could not read {fp}: {exc}")
    logger.info(f"Local files: loaded {len(all_rows)} rows from '{folder_path}'")
    return all_rows


def merge_and_pad(server_rows: list, local_rows: list) -> pd.DataFrame:
    """Combine server and local rows into a single padded DataFrame."""
    all_rows = server_rows + local_rows
    if not all_rows:
        return pd.DataFrame()
    maxlen = max(len(r) for r in all_rows)
    padded = [r + [''] * (maxlen - len(r)) for r in all_rows]
    return pd.DataFrame(padded)


# ── SHARED HELPERS ────────────────────────────────────────────────────────────

def _timestamp_to_local(series: pd.Series, timezone) -> pd.Series:
    """Convert a Unix-timestamp Series to localised naive datetimes."""
    return (pd.to_datetime(series, unit='s')
              .dt.tz_localize('UTC')
              .dt.tz_convert(timezone)
              .dt.tz_localize(None))


def _log_date_filter(df_before: pd.DataFrame, df_after: pd.DataFrame,
                     date_col: str, start: str, end: str,
                     tag: str, logger: logging.Logger) -> None:
    """Log the data's actual date range and warn if the filter removed everything."""
    if df_before.empty or date_col not in df_before.columns:
        return
    actual_min = df_before[date_col].min()
    actual_max = df_before[date_col].max()
    logger.info(f"  {tag} actual date range in data: {actual_min}  →  {actual_max}")
    if df_after.empty:
        logger.warning(
            f"  {tag} date filter removed ALL rows!\n"
            f"    Requested: {start}  →  {end}\n"
            f"    Data spans: {actual_min}  →  {actual_max}\n"
            f"    → Update your Start/End dates to match the data range above."
        )


def _night_dTmax(df_indexed: pd.DataFrame, dt_col: str) -> tuple:
    """
    Given a date-indexed DataFrame, compute:
      - dTmax_24h          : rolling 24-hour max (all hours)
      - dTmax_night        : rolling 24-hour max restricted to 8 pm – 8 am

    Returns (dTmax_24h, dTmax_night) as two Series aligned to df_indexed.
    """
    dTmax_24h = df_indexed[dt_col].rolling('24H', center=True).max()
    night_mask = (df_indexed.index.hour < 8) | (df_indexed.index.hour >= 20)
    night_series = df_indexed[dt_col].where(night_mask, other=np.nan)
    dTmax_night = night_series.rolling('24H', center=True).max()
    return dTmax_24h, dTmax_night


def _apply_iqr_filter(series: pd.Series, factor: float = 2.5) -> pd.Series:
    """Replace values outside  Q1 ± factor*IQR  with NaN."""
    Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
    IQR = Q3 - Q1
    lo, hi = Q1 - factor * IQR, Q3 + factor * IQR
    return series.where(series.between(lo, hi), other=np.nan)


def _sfd_from_K(K: pd.Series, species: str) -> pd.Series:
    """Compute sap flux density from a K1 series given a species string."""
    if species == 'diffuse-porous':
        sfd = 5.5750 * K
    elif species == 'dluhosch_10-50':
        sfd = 4.65 * K
    else:
        # Granier (original 1985) coefficients
        alpha, beta = 119.0, 1.231
        sfd = alpha * (K ** beta)
    sfd = sfd.clip(lower=0, upper=60)
    sfd[sfd <= 0] = np.nan
    return sfd


def _calc_stability(df: pd.DataFrame) -> pd.DataFrame:
    """Add yaw / pitch / roll columns computed from accelerometer axes x, y, z."""
    x = df['x'].round(2).abs()
    y = df['y'].round(2).abs()
    z = df['z'].round(2).abs()
    df['yaw']   = np.degrees(np.arctan(np.sqrt(x**2 + y**2) / z))
    df['pitch'] = np.degrees(np.arctan(x / np.sqrt(y**2 + z**2)))
    df['roll']  = np.degrees(np.arctan(y / np.sqrt(x**2 + z**2)))
    return df


def _calc_growth(df: pd.DataFrame, mv_col: str) -> pd.DataFrame:
    """
    Add 'dis' (distance from bark, mm) column using Sharp IR sensor millivolt value.
    Applies IQR filter and trailing rolling median smoothing.
    """
    df['dis'] = (24.8272) + (-26.9287) * df[mv_col] / (342.88 + df[mv_col])
    df.loc[~df['dis'].between(1.5, 5.0), 'dis'] = np.nan
    df['dis'] = _apply_iqr_filter(df['dis'], factor=2.5)
    df['dis'] = (df['dis'].max() - df['dis']).rolling(window=72, center=True).median()
    return df


def _calc_stem_saturation(df_indexed: pd.DataFrame,
                          freq_col: str, tref_col: str) -> pd.DataFrame:
    """Add 'sat%' column to a date-indexed DataFrame."""
    df_indexed['frequi'] = df_indexed[freq_col].rolling(window=100, center=True).median()
    MIN_ECF = 18000
    df_indexed['frequi_0'] = df_indexed['frequi'].where(df_indexed['frequi'] >= MIN_ECF, other=np.nan)
    if not df_indexed['frequi_0'].isnull().all():
        freq_n = df_indexed['frequi_0'].copy()
        T_sat = df_indexed.loc[freq_n.idxmin(), tref_col]
        ECFsat = (-74.15 * (df_indexed[tref_col] - T_sat)) + freq_n.min()
        df_indexed['sat%'] = (1 - (freq_n - ECFsat) / ECFsat) * 100
    else:
        df_indexed['sat%'] = 0.0
    return df_indexed


def _calc_soil_vwc(df: pd.DataFrame, freq_col: str, tref_col: str) -> pd.DataFrame:
    """Add volumetric water content columns 'vwc' and 'vwc1'."""
    df.loc[~df[freq_col].between(50000, 1800000), freq_col] = np.nan
    m = -758
    df['freqi'] = df[freq_col] - (m * (df[tref_col] - 20))
    df['vwc'] = (-1.7915173e-17 * df['freqi']**3
                 + 9.5651517e-11 * df['freqi']**2
                 - 0.000128698 * df['freqi']
                 + 50.44138201)
    b1, b2, b3 = 7.09e-12, -1.78e-05, 17
    df['vwc1'] = b1 * df['freqi']**2 + b2 * df['freqi'] + b3
    return df


# ── DEVICE PROCESSORS ─────────────────────────────────────────────────────────

def process_4B(dfall: pd.DataFrame, timezone, start_date: str,
               end_date: str, logger: logging.Logger):
    """Process gateway data (device type 4B).  Returns cleaned DataFrame or None."""
    if '4B' not in dfall[3].values:
        logger.info("No '4B' records found – skipping gateway processing.")
        return None

    logger.info("Processing 4B (gateway) data …")
    df = dfall[dfall[3] == '4B'].copy()
    df = df.replace('', pd.NA).dropna(how='all', axis=1)

    COLS = ['ID', 'record_number', 'device type', 'timestamp',
            'records in memory', 'pending records', 'MCC', 'MNC',
            'GSM registration', 'GSM field', 'Vbat', 'Firmware']
    if len(df.columns) != len(COLS):
        logger.warning(f"4B column count mismatch ({len(df.columns)} vs {len(COLS)}) – "
                       "assigning what we can.")
        COLS = COLS[:len(df.columns)]
    df.columns = COLS

    df = df.apply(pd.to_numeric, errors='ignore')
    df['date'] = _timestamp_to_local(df['timestamp'], timezone)
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    _log_date_filter(df, df_filtered, 'date', start_date, end_date, '4B', logger)
    df = df_filtered
    df['DOY'] = df['date'].dt.dayofyear
    df = df.reset_index(drop=True)

    logger.info(f"4B: {len(df)} rows, {df['ID'].nunique()} device(s).")
    return df


def process_45(dfall: pd.DataFrame, timezone, start_date: str, end_date: str,
               data_freq: str, species: str, logger: logging.Logger):
    """Process TT+3.1 sensor data (device type 45).  Returns cleaned DataFrame or None."""
    if '45' not in dfall[3].values:
        logger.info("No '45' records found – skipping TT+3.1 processing.")
        return None

    logger.info("Processing 45 (TT+3.1) data …")
    df = dfall[dfall[3] == '45'].copy()
    df = df.replace('', pd.NA).dropna(how='all', axis=1).reset_index(drop=True)

    COLS = ['ID', 'record_number', 'device type', 'timestamp',
            'Tref_start', 'Theat_start', 'Sharp sensor [d.n]',
            'adc_bat[d.n.]', 'No_of_bits', 'RH', 'airT',
            'x', 'g_z(std.dev) [d.n.]', 'y', 'g_y (std.dev) [d.n.]',
            'z', 'g_x (std.dev) [d.n.]', 'Tref_end', 'Theat_end', 'freq']
    if len(df.columns) != len(COLS):
        logger.warning(f"45 column count mismatch ({len(df.columns)} vs {len(COLS)}).")
        COLS = COLS[:len(df.columns)]
    df.columns = COLS

    df = df.apply(pd.to_numeric, errors='ignore')
    df['ID'] = df['ID'].astype(str)
    df['date'] = _timestamp_to_local(df['timestamp'], timezone)
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    _log_date_filter(df, df_filtered, 'date', start_date, end_date, '45', logger)
    df = df_filtered
    df['DOY']   = df['date'].dt.dayofyear
    df['year']  = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day']   = df['date'].dt.day
    df['hour']  = df['date'].dt.hour
    df = df.reset_index(drop=True)

    if df.empty:
        logger.warning("45: no rows remain after date filter – skipping.")
        return None

    # ---- Temperature conversion (ADC → °C, via 2-step LUT) ----
    y_interp      = interp1d(LUT_45_X, LUT_45_Y)
    y_interp_back = interp1d(LUT_45_Y, LUT_45_X)
    temp_cols = ['Tref_start', 'Theat_start', 'Tref_end', 'Theat_end']
    df[temp_cols] = df[temp_cols].clip(lower=-200, upper=1000)
    for col in temp_cols:
        adc = y_interp_back(df[col])
        adc_c = (adc * 43690.67) / df['adc_bat[d.n.]']
        adc_c = adc_c.clip(lower=1453, upper=14289)
        df[col] = y_interp(adc_c)
    df[temp_cols] = df[temp_cols] / 10
    df['airT'] = df['airT'] / 10

    # ---- Physical bounds ----
    for col in temp_cols:
        df.loc[~df[col].between(-19.9, 35), col] = np.nan
    df.loc[~df['airT'].between(-30, 40),  'airT'] = np.nan
    df.loc[~df['RH'].between(0, 100),     'RH']   = np.nan

    # ── Per-device processing ──────────────────────────────────────────────────
    device_frames = []
    for device_id, sub in df.groupby('ID'):
        try:
            d = sub.copy()
            # Remove duplicate rows
            d = d[~(d == d.shift(1)).all(axis=1)]
            d = d.sort_values('date').reset_index(drop=True)

            # ---- Sap flow differentials ----
            d['dTon']  = (d['Theat_end']   - d['Tref_end']).round(2)
            d['dToff'] = (d['Theat_start'] - d['Tref_start']).round(2)
            d['dT1']   = (d['dTon'] - d['dToff']).round(2)
            d.loc[~d['dT1'].between(0, 10), 'dT1'] = np.nan

            d['dT2'] = (d['Theat_end'] - d['Theat_start']).round(2)

            # ---- Nighttime dTmax (shared helper, requires date index) ----
            d = d.sort_values('date').set_index('date')
            d['dTmax1'], d['dTmax1_filtered'] = _night_dTmax(d, 'dT1')
            d['dTmax2'], d['dTmax2_filtered'] = _night_dTmax(d, 'dT2')
            d = d.reset_index()

            # ---- K1 ratios ----
            d['K1_hr'] = ((d['dTmax1_filtered'] - d['dT1']) / d['dT1']).round(2)
            d['K1_h']  = ((d['dTmax2_filtered'] - d['dT2']) / d['dT2']).round(2)

            # ---- Sap flux density ----
            if data_freq == 'tree':
                d['SFD1'] = _sfd_from_K(d['K1_hr'], species)
                d['SFD2'] = _sfd_from_K(d['K1_h'],  species)
            else:
                d['SFD1'] = np.nan
                d['SFD2'] = np.nan

            # ---- Tree stability ----
            d = _calc_stability(d)

            # ---- Battery ----
            d['Vbat'] = 650 + (131072 * 1100) / d['adc_bat[d.n.]']
            d.loc[~d['Vbat'].between(1000, 5000), 'Vbat'] = np.nan

            # ---- Growth (Sharp IR) ----
            d.loc[~d['Sharp sensor [d.n]'].between(48000, 95000), 'Sharp sensor [d.n]'] = np.nan
            d.loc[d['Vbat'] < 3500, 'Sharp sensor [d.n]'] = np.nan
            d['mv'] = (d['Sharp sensor [d.n]'] / d['adc_bat[d.n.]']) * 1100
            d = _calc_growth(d, 'mv')

            # ---- Frequency / stem saturation or soil VWC ----
            if data_freq == 'tree':
                d['freq'].iloc[:400] = np.nan
                d = d.set_index('date')
                d = _calc_stem_saturation(d, 'freq', 'Tref_start')
                d = d.reset_index()
                logger.info(f"  Device {device_id} (45): tree data processed.")
            elif data_freq == 'soil':
                d = _calc_soil_vwc(d, 'freq', 'Tref_start')
                logger.info(f"  Device {device_id} (45): soil data processed.")

            device_frames.append(d)

        except Exception as exc:
            logger.error(f"  Device {device_id} (45) FAILED: {exc}\n"
                         + traceback.format_exc())

    if not device_frames:
        logger.warning("45: no device frames produced.")
        return None

    result = pd.concat(device_frames, ignore_index=True)
    logger.info(f"45: finished – {len(result)} rows across {len(device_frames)} device(s).")
    return result


def process_4D(dfall: pd.DataFrame, timezone, start_date: str, end_date: str,
               data_freq: str, species: str, logger: logging.Logger):
    """Process TT+3.2 sensor data (device type 4D).  Returns cleaned DataFrame or None."""
    if '4D' not in dfall[3].values:
        logger.info("No '4D' records found – skipping TT+3.2 processing.")
        return None

    logger.info("Processing 4D (TT+3.2) data …")
    df = dfall[dfall[3] == '4D'].copy()
    df = df.replace('', pd.NA).dropna(how='all', axis=1).reset_index(drop=True)

    COLS = ['ID', 'record_number', 'device type', 'timestamp',
            'T_ref_start', 'T_heat_start', 'Sharp sensor [d.n]',
            'adc_bandgap [d.n.]', 'No_of_bits', 'RH', 'airT',
            'x', 'g_z(std.dev) [d.n.]', 'y', 'g_y (std.dev) [d.n.]',
            'z', 'g_x (std.dev) [d.n.]', 'T_ref_end', 'T_heat_end',
            'freq', 'adc_Vbat [d.n.]']
    if len(df.columns) != len(COLS):
        logger.warning(f"4D column count mismatch ({len(df.columns)} vs {len(COLS)}).")
        COLS = COLS[:len(df.columns)]
    df.columns = COLS

    df = df.apply(pd.to_numeric, errors='ignore')
    df['ID'] = df['ID'].astype(str)
    df['date'] = _timestamp_to_local(df['timestamp'], timezone)
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    _log_date_filter(df, df_filtered, 'date', start_date, end_date, '4D', logger)
    df = df_filtered
    df['DOY']   = df['date'].dt.dayofyear
    df['year']  = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day']   = df['date'].dt.day
    df['hour']  = df['date'].dt.hour

    if df.empty:
        logger.warning("4D: no rows remain after date filter – skipping.")
        return None

    # ---- Battery voltage ----
    df['Vbat'] = 2 * 1100 * (df['adc_Vbat [d.n.]'] / df['adc_bandgap [d.n.]'])
    df.loc[~df['Vbat'].between(1000, 5000), 'Vbat'] = np.nan

    df = df.reset_index(drop=True)

    # ---- Temperature conversion (ADC → °C via single LUT) ----
    y_interp = interp1d(LUT_4D_X, LUT_4D_Y)
    raw_T_cols  = ['T_ref_start', 'T_heat_start', 'T_ref_end', 'T_heat_end']
    nice_T_cols = ['Tref_start',  'Theat_start',  'Tref_end',  'Theat_end']
    df[raw_T_cols] = df[raw_T_cols].clip(lower=5816, upper=57159)
    for raw, nice in zip(raw_T_cols, nice_T_cols):
        df[nice] = y_interp(df[raw])

    # ---- Physical bounds ----
    for col in nice_T_cols:
        df.loc[~df[col].between(-19.9, 45), col] = np.nan
    df['airT'] = df['airT'] / 10
    df.loc[~df['airT'].between(-30, 40), 'airT'] = np.nan
    df.loc[~df['RH'].between(0, 100),    'RH']   = np.nan

    # ── Per-device processing ──────────────────────────────────────────────────
    device_frames = []
    for device_id, sub in df.groupby('ID'):
        try:
            d = sub.copy()
            # Remove duplicate rows
            d = d[~(d == d.shift(1)).all(axis=1)]
            d = d.sort_values('date').reset_index(drop=True)

            # ---- Background temperature interpolation (best-effort) ----
            try:
                d_idx = d.set_index('date')
                grouped = d_idx.groupby(pd.Grouper(freq='10T')).mean()
                resampled = grouped.resample('10T').asfreq()
                interp_vals = resampled['Theat_start'].interpolate(method='linear')
                d.loc[0, 'Theat_start'] = interp_vals.iloc[1]
            except Exception as exc:
                logger.debug(f"  Device {device_id} (4D): background interp skipped – {exc}")

            # ---- Sap flow differentials ----
            d['dTon']  = (d['Theat_end']   - d['Tref_end']).round(2)
            d['dToff'] = (d['Theat_start'] - d['Tref_start']).round(2)
            d['dT1']   = (d['dTon'] - d['dToff']).round(2)
            d.loc[~d['dT1'].between(-10, 10), 'dT1'] = np.nan

            d['dT2'] = (d['Theat_end'] - d['Theat_start']).round(2)

            # ---- Nighttime dTmax (same logic as 45) ----
            d = d.sort_values('date').set_index('date')
            d['dTmax1'], d['dTmax1_filtered'] = _night_dTmax(d, 'dT1')
            d['dTmax2'], d['dTmax2_filtered'] = _night_dTmax(d, 'dT2')
            d = d.reset_index()

            # ---- K1 ratios ----
            d['K1_hr'] = ((d['dTmax1_filtered'] - d['dT1']) / d['dT1']).round(2)
            d['K1_h']  = ((d['dTmax2_filtered'] - d['dT2']) / d['dT2']).round(2)

            # ---- Sap flux density ----
            if data_freq == 'tree':
                # NOTE: 4D SFD1 uses K1_h (heater-only), SFD2 uses K1_hr (both probes)
                d['SFD1'] = _sfd_from_K(d['K1_h'],  species)
                d['SFD2'] = _sfd_from_K(d['K1_hr'], species)
            else:
                d['SFD1'] = np.nan
                d['SFD2'] = np.nan

            # ---- Tree stability ----
            d = _calc_stability(d)

            # ---- Growth (Sharp IR, 4D uses different mv formula) ----
            d.loc[~d['Sharp sensor [d.n]'].between(48000, 95000), 'Sharp sensor [d.n]'] = np.nan
            d.loc[d['Vbat'] < 3500, 'Sharp sensor [d.n]'] = np.nan
            d['mv'] = d['Sharp sensor [d.n]'] * 3300 / 2**17
            d = _calc_growth(d, 'mv')

            # ---- Frequency / stem saturation or soil VWC ----
            if data_freq == 'tree':
                d['freq'].iloc[:400] = np.nan
                d = d.set_index('date')
                d = _calc_stem_saturation(d, 'freq', 'Tref_start')
                d = d.reset_index()
                logger.info(f"  Device {device_id} (4D): tree data processed.")
            elif data_freq == 'soil':
                d = _calc_soil_vwc(d, 'freq', 'Tref_start')
                logger.info(f"  Device {device_id} (4D): soil data processed.")

            device_frames.append(d)

        except Exception as exc:
            logger.error(f"  Device {device_id} (4D) FAILED: {exc}\n"
                         + traceback.format_exc())

    if not device_frames:
        logger.warning("4D: no device frames produced.")
        return None

    result = pd.concat(device_frames, ignore_index=True)
    logger.info(f"4D: finished – {len(result)} rows across {len(device_frames)} device(s).")
    return result


def process_49(dfall: pd.DataFrame, timezone, start_date: str,
               end_date: str, logger: logging.Logger):
    """Process spectrometer data (device type 49).  Returns cleaned DataFrame or None."""
    if '49' not in dfall[3].values:
        logger.info("No '49' records found – skipping spectrometer processing.")
        return None

    logger.info("Processing 49 (spectrometer) data …")
    df = dfall[dfall[3] == '49'].copy()
    df = df.replace('', pd.NA).dropna(how='all', axis=1).reset_index(drop=True)

    COLS = ['ID', 'record_number', 'device type', 'timestamp',
            'AS7263_610 [d.n.]', 'AS7263_680 [d.n.]', 'AS7263_730 [d.n.]',
            'AS7263_760 [d.n.]', 'AS7263_810 [d.n.]', 'AS7263_860 [d.n.]',
            'AS7262_450 [d.n.]', 'AS7262_500 [d.n.]', 'AS7262_550 [d.n.]',
            'AS7262_570 [d.n.]', 'AS7262_600 [d.n.]', 'AS7262_650 [d.n.]',
            'integration time', 'gain']
    if len(df.columns) != len(COLS):
        logger.warning(f"49 column count mismatch ({len(df.columns)} vs {len(COLS)}).")
        COLS = COLS[:len(df.columns)]
    df.columns = COLS

    df = df.apply(pd.to_numeric, errors='coerce')
    df['ID'] = df['ID'].astype(str)
    df['date'] = _timestamp_to_local(df['timestamp'], timezone)
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    _log_date_filter(df, df_filtered, 'date', start_date, end_date, '49', logger)
    df = df_filtered

    if df.empty:
        logger.warning("49: no rows remain after date filter – skipping.")
        return None

    # ── Per-device processing ──────────────────────────────────────────────────
    device_frames = []
    for device_id, sub in df.groupby('ID'):
        try:
            d = sub.copy()
            d = d[~(d == d.shift(1)).all(axis=1)]
            d = d.sort_values('date').reset_index(drop=True)

            # Clip outliers (0–65000 valid range)
            spec_dn_cols = [c for c in d.columns if '[d.n.]' in c]
            for col in spec_dn_cols:
                d = d[(d[col] >= 0) & (d[col] <= 65000)]

            # Calibrated band columns (rolling median to smooth)
            d['NIR_610']   = (d['AS7263_610 [d.n.]'] / SPEC_CALIB['AS7263_610']).rolling(3).median().round(2)
            d['NIR_680']   = (d['AS7263_680 [d.n.]'] / SPEC_CALIB['AS7263_680']).rolling(3).median().round(2)
            d['NIR_730']   = (d['AS7263_730 [d.n.]'] / SPEC_CALIB['AS7263_730']).rolling(3).median().round(2)
            d['NIR_760']   = (d['AS7263_760 [d.n.]'] / SPEC_CALIB['AS7263_760']).rolling(3).median().round(2)
            d['NIR_810']   = (d['AS7263_810 [d.n.]'] / SPEC_CALIB['AS7263_810']).rolling(3).median().round(2)
            d['NIR_860']   = (d['AS7263_860 [d.n.]'] / SPEC_CALIB['AS7263_860']).rolling(3).median().round(2)
            d['VISBL_450'] = (d['AS7262_450 [d.n.]'] / SPEC_CALIB['AS7262_450']).rolling(3).median().round(2)
            d['VISBL_500'] = (d['AS7262_500 [d.n.]'] / SPEC_CALIB['AS7262_500']).rolling(3).median().round(2)
            d['VISBL_550'] = (d['AS7262_550 [d.n.]'] / SPEC_CALIB['AS7262_550']).rolling(3).median().round(2)
            d['VISBL_570'] = (d['AS7262_570 [d.n.]'] / SPEC_CALIB['AS7262_570']).rolling(3).median().round(2)
            d['VISBL_600'] = (d['AS7262_600 [d.n.]'] / SPEC_CALIB['AS7262_600']).rolling(3).median().round(2)
            d['VISBL_650'] = (d['AS7262_650 [d.n.]'] / SPEC_CALIB['AS7262_650']).rolling(3).median().round(2)

            # Restrict to morning window (avoid direct sunlight)
            d = d.set_index('date').between_time('7:00', '9:30').reset_index()

            # Temporal columns
            d['year']  = d['date'].dt.year
            d['month'] = d['date'].dt.month
            d['day']   = d['date'].dt.day
            d['hour']  = d['date'].dt.hour
            d['DOY']   = d['date'].dt.dayofyear

            # NDVI with IQR outlier removal
            d['NDVI_raw'] = ((d['NIR_810'].rolling(3).median() - d['VISBL_650'].rolling(3).median()) /
                             (d['NIR_810'].rolling(3).median() + d['VISBL_650'].rolling(3).median()))
            ndvi_clean = _apply_iqr_filter(d['NDVI_raw'], factor=2.0)
            d['ndvi'] = ndvi_clean

            logger.info(f"  Device {device_id} (49): {len(d)} spectrometer rows.")
            device_frames.append(d)

        except Exception as exc:
            logger.error(f"  Device {device_id} (49) FAILED: {exc}\n"
                         + traceback.format_exc())

    if not device_frames:
        logger.warning("49: no device frames produced.")
        return None

    result = pd.concat(device_frames, ignore_index=True)
    logger.info(f"49: finished – {len(result)} rows across {len(device_frames)} device(s).")
    return result


# ── PLOTTING ──────────────────────────────────────────────────────────────────

def save_plots(df: pd.DataFrame, col_units: dict, id_col: str, x_col,
               output_dir: Path, suffix: str, auto_open: bool,
               plot_type: str = 'line') -> None:
    """Save one HTML plot per variable in col_units."""
    for col, unit in col_units.items():
        if col not in df.columns:
            continue
        try:
            if plot_type == 'scatter':
                fig = px.scatter(df, x=x_col, y=col, color=id_col)
            else:
                fig = px.line(df, x=x_col, y=col, color=id_col)
            fig.update_layout(yaxis_title=f"{col} ({unit})")
            out_file = str(output_dir / f"{col}_{suffix}.html")
            plotly.offline.plot(fig, filename=out_file, auto_open=auto_open)
        except Exception:
            pass  # non-critical – proceed with other plots


# ── ANALYSIS ORCHESTRATOR ─────────────────────────────────────────────────────

def run_analysis(values: dict, logger: logging.Logger) -> None:
    """Load data, process all device types, save CSVs and HTML plots."""

    output_dir  = Path(values['folder'])
    timezone    = pytz.timezone(values['timezone'])
    start_date  = values['start_date']
    end_date    = values['end_date']
    data_freq   = 'tree' if values['tree_probe'] else 'soil'
    species     = values.get('species_type', '')
    auto_open   = (values.get('plot_option', '') == 'Store and visualize')
    site_id     = values.get('item_id', '').strip()

    logger.info("=" * 60)
    logger.info(f"Run started  |  site={values.get('site_name','')}  "
                f"| probe={data_freq}  | species={species}")
    logger.info(f"Period: {start_date}  →  {end_date}  [{values['timezone']}]")
    logger.info("=" * 60)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    server_rows = []
    if site_id:
        for url in [f"http://naturetalkers.altervista.org/{site_id}/ttcloud.txt",
                    f"http://ittn.altervista.org/{site_id}/ttcloud.txt"]:
            server_rows += read_server_data(url, logger)

    local_rows = []
    if values.get('manual_upload'):
        local_rows = read_folder_files(values['manual_upload'], logger)

    dfall = merge_and_pad(server_rows, local_rows)
    if dfall.empty:
        logger.error("No data loaded – check serial number and/or manual upload folder.")
        return

    dfall[1] = dfall[1].astype(str)
    dfall.drop_duplicates(inplace=True)
    dfall.drop(columns=[0], inplace=True, errors='ignore')
    # After dropping col 0, re-index columns to 1-based integers for consistency
    dfall.columns = range(1, len(dfall.columns) + 1)

    logger.info(f"Combined data: {dfall.shape[0]} rows, "
                f"{dfall[1].nunique()} device ID(s).")

    # ── Diagnostic: show raw timestamp range and device types found ───────────
    try:
        raw_ts = pd.to_numeric(dfall[4], errors='coerce').dropna()
        if not raw_ts.empty:
            ts_min = pd.to_datetime(raw_ts.min(), unit='s', utc=True).tz_convert(timezone)
            ts_max = pd.to_datetime(raw_ts.max(), unit='s', utc=True).tz_convert(timezone)
            logger.info(f"Raw data timestamp range: {ts_min.strftime('%Y-%m-%d')} "
                        f"→ {ts_max.strftime('%Y-%m-%d')}")
    except Exception:
        pass
    dtype_counts = dfall[3].value_counts().to_dict()
    logger.info(f"Device types in raw data: {dtype_counts}")

    # ── 2. Process each device type ───────────────────────────────────────────

    # --- 4B (gateway) ---
    df4B = process_4B(dfall, timezone, start_date, end_date, logger)
    if df4B is not None:
        df4B.to_csv(output_dir / 'df4B.csv', index=False)
        save_plots(df4B, COLS_4B, 'ID', 'date', output_dir, '4B', auto_open)
        logger.info("4B: CSV and plots saved.")

    # --- 45 (TT+3.1) ---
    df45 = process_45(dfall, timezone, start_date, end_date,
                      data_freq, species, logger)
    if df45 is not None:
        out_cols = [c for c in ['ID', 'device type', 'date',
                                'Vbat', 'airT', 'dT1', 'dTmax1', 'dTmax1_filtered',
                                'dT2', 'dTmax2', 'dTmax2_filtered',
                                'SFD1', 'SFD2', 'dis', 'yaw', 'pitch', 'roll']
                    if c in df45.columns]
        df45[out_cols].to_csv(output_dir / 'df45.csv', index=False)
        save_plots(df45, COLS_45, 'ID', 'date', output_dir, '45', auto_open)
        logger.info("45: CSV and plots saved.")

    # --- 4D (TT+3.2) ---
    df4D = process_4D(dfall, timezone, start_date, end_date,
                      data_freq, species, logger)
    if df4D is not None:
        out_cols = [c for c in ['ID', 'device type', 'date',
                                'Vbat', 'airT', 'RH',
                                'dT1', 'dTmax1', 'dTmax1_filtered',
                                'dT2', 'dTmax2', 'dTmax2_filtered',
                                'SFD1', 'SFD2', 'dis', 'yaw', 'pitch', 'roll']
                    if c in df4D.columns]
        df4D[out_cols].to_csv(output_dir / 'df4D.csv', index=False)
        save_plots(df4D, COLS_4D, 'ID', 'date', output_dir, '4D', auto_open)
        logger.info("4D: CSV and plots saved.")

    # --- 49 (spectrometer) ---
    df49 = process_49(dfall, timezone, start_date, end_date, logger)
    if df49 is not None:
        out_cols = [c for c in ['ID', 'device type', 'date', 'DOY', 'month', 'year',
                                'VISBL_450', 'VISBL_500', 'VISBL_550', 'VISBL_570',
                                'VISBL_600', 'VISBL_650',
                                'NIR_610', 'NIR_680', 'NIR_730', 'NIR_760',
                                'NIR_810', 'NIR_860', 'ndvi']
                    if c in df49.columns]
        df49[out_cols].to_csv(output_dir / 'df49.csv', index=False)
        save_plots(df49, COLS_49, 'ID', 'date', output_dir, '49', auto_open,
                   plot_type='scatter')
        logger.info("49: CSV and plots saved.")

    logger.info("=" * 60)
    logger.info("Run complete.")
    logger.info("=" * 60)


# ── GUI ───────────────────────────────────────────────────────────────────────

_CONFIG_FILE = 'ttplus_config.json'


def _make_main_layout(saved: dict) -> list:
    return [
        [sg.Text('Load config'), sg.Input(saved.get('load', ''), key='load'),
         sg.FileBrowse(file_types=(("JSON Files", "*.json"),)), sg.Button('Load')],
        [sg.Text('Site name'), sg.InputText(saved.get('site_name', ''), key='site_name')],
        [sg.Text('Serial No. (e.g. 81238007,81238008,…)'),
         sg.InputText(saved.get('item_id', ''), key='item_id')],
        [sg.Text('Manual data folder'), sg.Input(saved.get('manual_upload', ''), key='manual_upload'),
         sg.FolderBrowse()],
        [sg.Text('Output folder'), sg.Input(saved.get('folder', ''), key='folder'),
         sg.FolderBrowse()],
        [sg.Text('Timezone'), sg.Combo(pytz.all_timezones,
                                       default_value=saved.get('timezone', 'Europe/Rome'),
                                       key='timezone')],
        [sg.Text('Start Date (YYYY-MM-DD HH:MM:SS)'),
         sg.InputText(saved.get('start_date', ''), key='start_date')],
        [sg.Text('End Date   (YYYY-MM-DD HH:MM:SS)'),
         sg.InputText(saved.get('end_date', ''), key='end_date')],
        [sg.Checkbox('Tree probe', default=saved.get('tree_probe', False), key='tree_probe'),
         sg.Checkbox('Soil probe', default=saved.get('soil_probe', False), key='soil_probe')],
        [sg.Text('Species type'), sg.Combo(TREE_TYPES, key='species_type',
                                           default_value=saved.get('species_type', '')),
         sg.Text('Plot'), sg.Combo(['Store and visualize', 'Store only'],
                                   key='plot_option',
                                   default_value=saved.get('plot_option', 'Store only'))],
        [sg.Text('Save config'), sg.Input(saved.get('save', ''), key='save'),
         sg.FileSaveAs(file_types=(("JSON Files", "*.json"),)), sg.Button('Save')],
        [sg.Button('START', button_color=('white', 'green')),
         sg.Button('CANCEL', button_color=('white', 'red'))],
    ]


def main() -> None:
    saved = load_config(_CONFIG_FILE)

    main_win = sg.Window('TreeTalker TT+ Data Analyzer v6',
                         _make_main_layout(saved), finalize=True)

    log_layout = [[sg.Multiline(size=(110, 30), key='-LOG-',
                                autoscroll=True, disabled=True,
                                background_color='black', text_color='lime',
                                font=('Courier', 9))]]
    log_win = sg.Window('Processing Log', log_layout, finalize=True,
                        resizable=True, location=(0, 600))

    # Patch the Multiline widget so print() works like sg.Output
    log_win['-LOG-'].update('')

    # Wire up logging
    log_path = Path(_CONFIG_FILE).parent / 'TTplus_DT.log'
    logger   = setup_logging(log_path, gui_window=log_win, gui_key='-LOG-')
    logger.info("TTplus Data Tool v6.0 started.")

    while True:
        win, event, values = sg.read_all_windows(timeout=100)

        if win == sg.TIMEOUT_KEY or win is None:
            continue

        if win == main_win:
            if event in (sg.WIN_CLOSED, 'CANCEL'):
                break

            elif event == 'Save':
                fp = values.get('save', '')
                if fp:
                    save_config(values, fp)
                    logger.info(f"Config saved to {fp}")

            elif event == 'Load':
                fp = values.get('load', '')
                if fp:
                    saved = load_config(fp)
                    for k in ['site_name', 'item_id', 'manual_upload', 'folder',
                              'timezone', 'start_date', 'end_date',
                              'tree_probe', 'soil_probe', 'species_type', 'plot_option']:
                        if k in saved:
                            main_win[k].update(saved[k])
                    logger.info(f"Config loaded from {fp}")

            elif event == 'START':
                ok, msg = validate_inputs(values)
                if not ok:
                    logger.error(f"Validation failed: {msg}")
                else:
                    try:
                        run_analysis(values, logger)
                    except Exception as exc:
                        logger.error(f"Unexpected error: {exc}\n" + traceback.format_exc())

        elif win == log_win:
            if event == sg.WIN_CLOSED:
                log_win.hide()

    main_win.close()
    log_win.close()


if __name__ == '__main__':
    main()
