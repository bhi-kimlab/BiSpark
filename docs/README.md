[Link to website](https://bhi-kimlab.github.io/BiSpark/)

# About BiSpark

BiSpark is a highly parallelized bisulfite-treated read aligner algorithm that utilizes distributed environment to significantly improve aligning performance and scalability. BiSpark is designed based on the Apache Spark distributed framework and shows highly efficient scalability.

![Figure](https://github.com/bhi-kimlab/BiSpark/blob/master/docs/BisPark_workflow_v2.png?raw=true)

Analysis workflow within BiSpark consists of 4 processing phases: (1) Distributing the reads into key-value pairs, (2) Transforming reads into ‘three-letter’ reads and mapping to transformed reference genome, (3) Aggregating mapping results and filtering ambiguous reads, and (4) Profiling the methylation information for each read. The figure depicts the case when library of input data is a non-directional.

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

# BiSpark on Amazon cloud

Now pre-built BiSpark AMI(AMI#: xxx, Region: Ohio) on the Amazon EC2. Belows are step by step procedure.
  
- Creating cluster instance based on BiSpark AMI.
  1. xxx.

- Initializing the Spark & HDFS.
  1. xxx.

- Checking if the cluster is correctly deployed.
  1. xxx.

- Test run with test data set.
  1. xxx.

# Test data set in the publication

\[[1.6GB](http://epigenomics.snu.ac.kr/BiSpark/10_000_000.fa)/
[7.9GB](http://epigenomics.snu.ac.kr/BiSpark/50_000_000.fa)/
[16GB](http://epigenomics.snu.ac.kr/BiSpark/100_000_000.fa)/
[32GB](http://epigenomics.snu.ac.kr/BiSpark/200_000_000.fa)\]

# Recommended pre-processing for quality control

To improve the mappability and alignment accuracy, snitizing the poor reads before the main BiSpark phase is highly recommended. 
  *. Run XXX [fastq].
  
# Contact

If you have any question or problem, please send a email to [dane2522@gmail.com](mailto:dane2522@gmail.com)
