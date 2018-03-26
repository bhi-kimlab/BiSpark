[Link to website](https://bhi-kimlab.github.io/BiSpark/)

# About BiSpark

BiSpark is a highly parallelized bisulfite-treated read aligner algorithm that utilizes distributed environment to significantly improve aligning performance and scalability. BiSpark is designed based on the Apache Spark distributed framework and shows highly efficient scalability.

![Figure](https://github.com/bhi-kimlab/BiSpark/blob/master/docs/BisPark_workflow.png?raw=true)


# Features

* Fast and well scalable to both data size and cluster size.
* Based on Apache Spark: Easy to use. No restriction on the number of nodes.
* Using HDFS: Do not need to consider files to be distributed by user.


# Installation

BiSpark is implemented on [Apache Spark](https://spark.apache.org/) framework and [HDFS](https://hadoop.apache.org/docs/r2.7.2/hadoop-project-dist/hadoop-hdfs/HdfsUserGuide.html) file system. [Bowtie2](http://bowtie-bio.sourceforge.net/bowtie2/index.shtml) is also used to alignment, thus all three frameworks and programs should be installed before running BiSpark. Bowtie2 should be callable on all slave nodes.

## Requirements

* Python: 2.6, 2.7
* Apache Spark: >= 1.6
* HDFS: 2.6

# Usage

- Building Index (reference: ./src/build_index/run.sh)
  1. --input: Input reference FASTA file located in HDFS.
  2. --output: Output directory for indexing files in HDFS.
  3. --log: Local log file path.
- Alignment (reference: ./src/alignment/run.sh)
  1. --input: Input reference FASTA file located in HDFS.
  2. --output: Output directory for indexing files in HDFS.
  3. --log: Local log file path.
  4. --ref: Index dicrectory in HDFS. Should be same path as denoted as '--output'.
  5. --nodes: The number of executors. = (# of nodes of cluster) * (# of spark executors in each node)
  6. --num_mm: The number of maximum mismatches (default: 4)
  6. --local_save: Local output sam file path.
  7. --testmode: Switching testmode for experiment. Should be one of 'balancing' or 'plain'.
  8. --appname: Application name that are used for Spark's application name.

# Test data set in the publication
http://xxx

# Contact
If you have any question or problem, please send a email to [dane2522@gmail.com](mailto:dane2522@gmail.com)
