#!/bin/bash

basepath=$(dirname $0)

"${basepath}/build_index.py" \
--input "hdfs:////test/raw/chr1.fa" \
--output "hdfs:///test/ref/chr1" \
--log_path "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/test1/log.txt"
