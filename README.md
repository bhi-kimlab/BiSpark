# SparkMethyl

## Prerequisite
- Spark should be installed.
- HDFS should be installed and accessible.
- bowtie2 should be installed.
  - command 'bowtie2' and 'bowtie2-build' must be callable for spark user.
- temporary files would be located under /tmp.



## Usage
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
  6. --local_save: Local output sam file path.
  7. --testmode: Switching testmode for experiment. Should be one of 'balancing' or 'plain'.
  8. --appname: Application name that are used for Spark's application name.

