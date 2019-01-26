#!/bin/bash
"C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvars64.bat"
"cl.exe /D_USRDLL /D_WINDLL deca/process_image.c /link /DLL /OUT:process_image.dll"
pyinstaller deca_gui.spec --clean --noconfirm
