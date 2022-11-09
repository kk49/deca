#!/bin/bash
gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so
pyinstaller deca_gui.spec --clean --noconfirm
