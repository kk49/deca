#!/bin/bash
echo Process TAB/ARC
python3 process_tab_arc.py ${version} ${src_root} ${dst_root}out/

echo Relabel Files
python3 process_file_ext.py ${dst_root}out/

echo Expand AAF files
find ${dst_root}out/ | grep aaf$ | xargs -n1 -P4 python3 process_aaf.py

echo Relabel Files
python3 process_file_ext.py ${dst_root}out/

echo Get hashes
pushd ${dst_root}out/
find -type f > ../hash_list.txt
popd

echo Expand SARC files
find ${dst_root}out/ | grep sarc$ | xargs -n1 -P4 python3 process_sarc.py ${dst_root} 
