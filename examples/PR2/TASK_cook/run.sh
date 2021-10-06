#!/bin/bash
name=$1
for i in {1..50}; do
(   
    if [ `ls log | grep $name | wc -l` = 0 ]; then
        filename=$name.log
    else
        filename=$name`ls log | grep $name | wc -l`.log
    fi
    python3 run_idtmp_cook.py >> "log/$filename"
)
done