# -*- coding: utf-8 -*-
# create MC/MCV files from curve data
#
import femagtools
import logging
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s')

mcvData = [
    dict(curve=[dict(
        bi=[0.0, 0.09, 0.179, 0.267, 0.358,
            0.45, 0.543, 0.6334, 0.727,
            0.819, 0.9142, 1.0142, 1.102,
            1.196, 1.314, 1.3845, 1.433,
            1.576, 1.677, 1.745, 1.787,
            1.81, 1.825, 1.836],

        hi=[0.0, 22.16, 31.07, 37.25, 43.174,
            49.54, 56.96, 66.11, 78.291,
            95, 120.64, 164.6, 259.36,
            565.86, 1650.26, 3631.12, 5000, 10000,
            15000, 20000, 25000, 30000, 35000, 40000])],
         desc=u"Demo Steel",
         name='M270-35A-TKS',
         ch=4.0,
         cw_freq=2.0,
         cw=1.68,
         losses={
             'B': [(0.501115444, 0.601001754, 0.709139143, 0.801875189,
                    0.901502631, 1.001380145, 1.101819375, 1.200520677,
                    1.301972757, 1.401627846, 1.50304851, 1.604167581,
                    1.710961625, 1.8082002),
                   (0.496874294, 0.602940745, 0.698878702, 0.796758162, 0.90143603,
                    1.001916729, 1.102661322, 1.199897385, 1.299174226, 1.401627846,
                    1.502341023, 1.604794642, 1.713320332),
                   (0.50269001, 0.599665949, 0.70078502, 0.800917631, 0.898520632,
                    0.998393119, 1.100120402, 1.200053208, 1.299933235, 1.400235492,
                    1.503259625),
                   (0.199302638, 0.299572222, 0.401450302, 0.500562524,
                    0.600974108, 0.700524896, 0.801111153, 0.899983357,
                    0.998855561, 1.099289765, 1.199781774, 1.301678704)],
             'f': [50., 100., 200., 400.],
             'pfe': [(0.45, 0.62, 0.8, 1.01, 1.24, 1.49, 1.77,
                      2.09, 2.46, 2.91, 3.45, 3.92, 4.29, 4.71),
                     (1.17, 1.62, 2.14, 2.73, 3.39, 4.13, 4.95, 5.88, 6.91,
                      8.17, 9.74, 11.13, 12.4),
                     (3.23, 4.52, 6.05, 7.85, 9.93, 12.34, 15.03, 18.08,
                      21.55, 25.9, 30.66),
                     (1.71, 3.55, 5.98, 9.21, 13.17,
                      17.95, 23.87, 30.84, 39.24, 48.9, 60.23, 73.1)]
    }),

    dict(curve=[{"angle": 0.0,
                 "bi": [0.0, 0.5001193881034851, 0.6001256704330444,
                        0.700133204460144, 0.8001407384872437,
                        0.9001495242118835, 1.0001596212387085,
                        1.1001709699630737, 1.2001848220825195,
                        1.3002337217330933, 1.4003480672836304,
                        1.500654697418213, 1.6016123294830322,
                        1.7040778398513794, 1.8085501194000244,
                        1.9156187772750854, 1.9730873107910156],
                 "hi": [0.0, 95.0, 100.0, 106.0, 112.0, 119.0, 127.0,
                        136.0, 147.0, 186.0, 277.0, 521.0, 1283.0,
                        3245.0, 6804.0, 12429.0, 16072.6748046875]},
                {"angle": 90.0,
                 "bi": [0.0, 0.5002199411392212, 0.6002413034439087,
                        0.7002626061439514, 0.8002877831459045,
                        0.9003154039382935, 1.0003480911254883,
                        1.1003907918930054, 1.2004486322402954,
                        1.3005428314208984, 1.4007363319396973,
                        1.5012717247009277, 1.6028035879135132,
                        1.7061727046966553, 1.8115723133087158,
                        1.918825626373291, 1.9763903617858887],
                 "hi": [0.0, 175.0, 192.0, 209.0, 229.0, 251.0,
                        277.0, 311.0, 357.0, 432.0, 586.0,
                        1012.0, 2231.0, 4912.0, 9209.0, 14981.0,
                        18718.376953125]}],
         ctype=femagtools.mcv.ORIENT_CRV,
         desc="Magnetic Curve",
         rho=7.65,
         bsat=0.0,
         name="V800-50A_aniso",
         cw=0.0,
         cw_freq=0.0,
         fillfac=1.0,
         bref=0.0,
         b_coeff=0.0,
         fe_sat_mag=2.15,
         ch_freq=0.0,
         remz=0.0,
         Bo=1.5,
         ch=0.0,
         fo=50.0)
]

userdir = os.path.expanduser('~')
workdir = os.path.join(userdir, 'femag')
try:
    os.makedirs(workdir)
except OSError:
    pass

mcv = femagtools.mcv.MagnetizingCurve(mcvData)
for m in mcvData:
    mcv.writefile(m['name'])
