#!/bin/bash
export DECA_BIN_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export DECA_ROOT_DIR=$( cd -- ${DECA_BIN_DIR} &> /dev/null && cd ".." && pwd )
export N_PROC=$(grep "^cpu\\scores" /proc/cpuinfo | uniq |  awk '{print $4}')
export CC="/usr/bin/gcc-10"
export CXX="/usr//bin/g++-10"

cd "${DECA_ROOT_DIR}"
git submodule update --init --recursive


# setup C++
(
mkdir -p build  &&
cd build  &&
cmake ..  &&
make -j ${N_PROC}  &&
mkdir -p "${DECA_ROOT_DIR}/root/bin/"  &&
mkdir -p "${DECA_ROOT_DIR}/root/lib/"  &&
cp cpp/bin2xml/bin2xml "${DECA_ROOT_DIR}/root/bin/"
cp cpp/process_image/process_image.so "${DECA_ROOT_DIR}/root/lib/"
) &&

# setup python
python3 -m venv venv  &&
. venv/bin/activate  &&
pip install wheel  &&
pip install -r python/requirements.txt  &&
pip install -e python/deca  &&
pip install -e python/deca_gui
