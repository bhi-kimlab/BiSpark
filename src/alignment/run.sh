
basepath=$(dirname $0)
nodes=20
# input="hdfs:////test/data/100_000.fa"
# input="hdfs:////test/data/1000.myf"
input="hdfs:////test/data/random_e2_1_000_000.fa"
output="hdfs:///test/result/random_e2_1_000_000"
ref="hdfs:///test/ref/chr1"

hdfs dfs -rm -r -f $output


/home/dane2522/programs/spark-2.0.2-bin-hadoop2.6/bin/spark-submit \
  --conf spark.driver.maxResultSize=2g \
  --conf spark.network.timeout=10000 \
  --conf spark.executor.heartbeatInterval=100 \
  --master spark://hadoop-slave-2:7077 \
  --driver-memory 8G \
  --executor-memory 8G \
  "${basepath}/align.py" \
  --input $input \
  --output $output \
  --ref $ref \
  --log "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/random_e2_1_000_000/log.txt" \
  --local_save "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/random_e2_1_000_000/alignment.txt" \
  --nodes $nodes \
  --testmode "balancing" \
  --appname "random_e2_1_000_000"

