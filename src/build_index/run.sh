#!/bin/bash

###
# $1: input_reference
# $2: index_prefix
# $3: log_file
###

# bowtie2-build -f $1 $2 > $3



basepath=$(dirname $0)



python "${basepath}/build_index.py" \
  --input "hdfs:////test/raw/chr1.fa" \
  --output "hdfs:///test/ref/chr1" \
  --log_path "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/test1/log.txt"
