#!/bin/sh
ROOT=./test/gz
python3 process_magic.py ${ROOT}/files ${ROOT}/out > ${ROOT}/file_prefixs.txt
#python3 process_file_ext.py  > ${ROOT}/file_prefixs.txt
sort < ${ROOT}/file_prefixs.txt > ${ROOT}/file_prefixs_sorted.txt
