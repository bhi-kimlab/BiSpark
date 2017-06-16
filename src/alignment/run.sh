
basepath=$(dirname $0)
nodes=1
input="hdfs:////test/data/100_000.fa"
# input="hdfs:////test/data/1000.myf"
output="hdfs:///test/result/test_100_000"

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
  --ref "hdfs:///test/ref/chr1" \
  --log "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/test_100_000/log.txt" \
  --local_save "/home/dane2522/project/SparkMethyl/SparkMethyl/exp/test_100_000/alignment.txt" \
  --nodes $nodes \
  --testmode "balancing" \
  --appname "100_000_balancing_test"

