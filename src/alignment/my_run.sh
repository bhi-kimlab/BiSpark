
basepath=$(dirname $0)
nodes=20

size=$1
testmode=$2

#size=10_000_000
#size=50_000_000
#size=100_000_000
#size=200_000_000
#size=1000
#size=100_000
#input="hdfs:///user/hadoop/fa_data/1000.fa"
#output="hdfs:///user/hadoop/result/test_1000"
#local="alignment_1000.txt"
input=hdfs:///user/hadoop/fa_data/$size.fa
#input=hdfs:///user/hadoop/fa_data/$size.myf
output=hdfs:///user/hadoop/result/test_$size
local=alignment_$size.txt
name=$size\_balacning_test

# input="hdfs:////test/data/1000.myf"
ref="hdfs:///user/hadoop/ref/chr1"

hdfs dfs -rm -r -f $output

echo $size $testmode >> time.txt

{ time spark-submit \
  --executor-memory 5G \
  "${basepath}/align.py" \
  --input $input \
  --output $output \
  --ref $ref \
  --log "./log.txt" \
  --local_save $local \
  --nodes $nodes \
  --testmode $testmode \
  --appname $name; } 2>> time.txt


#  --conf spark.driver.maxResultSize=2g \
#  --conf spark.network.timeout=10000 \
#  --conf spark.executor.heartbeatInterval=100 \
#  --master spark://master1:7077 \
#  --driver-memory 8G \

