import os
import numpy as np
import pandas as pd

db = pd.read_csv('./test/gz/file_prefixs.txt', delimiter='\t')

fl = db[(db['ftype'] == 'raw_image') | (db['ftype'] == 'AVTX')]
fl = fl.sort_values(by=['file_size', 'path'])
file_list = [v for v in fl['path']]

for file in file_list:
    syscall = 'python3 process_avtx.py {}'.format(file)
    res = os.system(syscall)
    if res != 0:
        raise Exception('Sys call failed: {}: {}'.format(res, syscall))
