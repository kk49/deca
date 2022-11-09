#!/bin/bash
python3 -m venv venv
. venv/bin/activate
pip install wheel
pip install -r requirements_latest.txt
gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so
