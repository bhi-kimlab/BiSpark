hdfs dfs -mkdir /test
hdfs dfs -mkdir /test/data
hdfs dfs -put ~/100_000.fa /test/data


basepath=$(dirname $0)
nodes=$1
# input="hdfs:////test/data/100_000.fa"
# input="hdfs:////test/data/1000.myf"
input="hdfs:////test/data/100_000.fa"
output="hdfs:///test/result/100_000"
ref="hdfs:///test/ref/chr1"

hdfs dfs -rm -r -f $output


spark-submit \
  --conf spark.driver.maxResultSize=2g \
  --conf spark.network.timeout=10000 \
  --conf spark.executor.heartbeatInterval=100 \
  --master spark://yarnmaster:7077 \
  --driver-memory 6G \
  --executor-memory 6G \
  "${basepath}/align.py" \
  --input $input \
  --output $output \
  --ref $ref \
  --log "./log_100_000.txt" \
  --local_save "./alignment_100_000.txt" \
  --nodes $nodes \
  --testmode "balancing" \
  --appname "100_000"

