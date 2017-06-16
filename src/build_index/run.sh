#!/bin/bash

input="hdfs:////test/raw/chr1.fa"
output="hdfs:///test/ref/chr1"
log="/home/dane2522/project/SparkMethyl/SparkMethyl/log.txt"


hdfs dfs -rm -r -f $output


basepath=$(dirname $0)



python "${basepath}/build_index.py" \
  --input $input \
  --output $output \
  --log $log
