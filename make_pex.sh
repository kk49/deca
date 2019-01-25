#!/bin/bash
pex -vvvvv . -r requirements.txt -m deca.gui.main --disable-cache -o deca_gui.pex
