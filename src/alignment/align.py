from collections import defaultdict
from pyspark.storagelevel import StorageLevel
from pyspark import SparkContext, SparkConf
from pyspark.shuffle import ExternalSorter
from pyspark.rdd import _parse_memory
import argparse
import os
import time


def align(sc, args):
  import utils as g_utils
  import align_utils as a_utils

  ## broadcast raw reference
  ref_file = os.path.join( args.tempbase, "ref.fa" )
  g_utils.read_hdfs( os.path.join(args.ref, "raw.fa"), ref_file )
  ref_dict = {}
  for chrid, seq in g_utils.read_fasta( ref_file ):
    ref_dict[ chrid ] = (seq, len(seq))

  g_utils.logging("[DEBUG] loading reference done", args)
  bc_refdict = sc.broadcast( ref_dict )



  ## read from hadoop
  readRDD = sc.textFile( args.input ) \
              .map( lambda x: g_utils.line2kv( x))

  if args.testmode == "balancing":
    readRDD = readRDD.partitionBy( args.nodes )
                      
  readRDD = readRDD.cache()


  ## transform and get result of bowtie
  c2tTransRDD = readRDD.mapValues( lambda x: x.translate( g_utils.make_trans_with("W", "C", "T")) )
  c2tMapRDD   = c2tTransRDD.mapPartitionsWithIndex( lambda i, ptn: a_utils.mapping(i, "C2T", ["W_C2T", "C_C2T"], ptn, args) )
  
  g2aTransRDD = readRDD.mapValues( lambda x: x.translate( g_utils.make_trans_with("W", "G", "A")) )
  g2aMapRDD   = g2aTransRDD.mapPartitionsWithIndex( lambda i, ptn: a_utils.mapping(i, "G2A", ["W_G2A", "C_G2A"], ptn, args) )


  
  mergedRDD = sc.union( [readRDD, c2tMapRDD, g2aMapRDD] )
  combRDD = mergedRDD.combineByKey( lambda v: [v],\
                                    lambda lst, v: lst + [v],\
                                    lambda l1, l2: l1 + l2 )
  filteredRDD = combRDD.mapValues( lambda x: a_utils.select_and_find_uniq_alignment( x))\
                        .filter( lambda (k, v): v is not None )
                        # .filter( lambda (k, v): not (v is None))

  if args.testmode == "balancing":
    filteredRDD = filteredRDD.partitionBy( args.nodes )
                  

  methylRDD = filteredRDD.map( lambda x: a_utils.calc_methyl(x, bc_refdict.value, args.num_mm) )\
                          .filter( lambda x: x is not None )

  result_path = os.path.join( args.output, "alignment" )
  methylRDD.map( lambda x: a_utils.res_to_string(x) ).saveAsTextFile( result_path )

  return result_path





if __name__ == "__main__":
  parser = argparse.ArgumentParser()

  ### args
  parser.add_argument("--input", type=str, default="", help="input sequence file")
  parser.add_argument("--output", type=str, default="", help="output result path")
  parser.add_argument("--ref", type=str, default="", help="input reference path")
  parser.add_argument("--log", type=str, default="", help="log path")
  parser.add_argument("--nodes", type=int, default=1, help="number of nodes")
  parser.add_argument("--num_mm", type=int, default=4, help="number of mismatches")
  parser.add_argument("--local_save", type=str, default="", help="local path to save result")
  parser.add_argument("--testmode", type=str, default="plain", help="testmode: <balancing> | <plain>")
  parser.add_argument("--appname", type=str, default="DefaultApp", help="application name of spark")


  parser.parse_args()
  args, unparsed = parser.parse_known_args()

  
  conf = SparkConf().setAppName(args.appname)
  sc = SparkContext(conf=conf)


  sc.addPyFile( os.path.join( os.path.dirname(__file__), "align_utils.py") )
  sc.addPyFile( os.path.join( os.path.dirname(__file__), "..", "utils", "utils.py") )


  import utils

  utils.logging("[INFO] Appplication <%s> is launched." % (args.appname), args)
  for k, v in vars(args).iteritems():
    utils.logging("[INFO] Loggin arguments: %s : %s." % (str(k), str(v)), args)


  if args.input == "" or args.output == "" or args.ref == "":
    utils.logging("[ERROR] Input, Output and Reference File must be correctly set.")
    sys.exit()

  
  utils.mkdir( os.path.dirname(args.log) )


  ## set temp working dir
  args.tempbase = utils.gen_file()
  utils.mkdir(args.tempbase)

  ## preprocess for input file
  input_ext = os.path.splitext(args.input)[1]

  ## node--
  args.nodes = args.nodes - 1

  if input_ext != ".myf":
    utils.logging("[INFO] Transform input file to myf.", args)
    myf_input = os.path.join(args.output, "input.myf")
    utils.convert_to_myf(args.input, myf_input)
    args.input = myf_input

  
  bc_args = sc.broadcast( args )


  utils.logging("[INFO] Start BiSpark.", args)
  start_time = time.time()
  result_path = align(sc, bc_args.value)
  end_time = time.time()
  utils.logging("[INFO] BiSpark took : " + str(end_time - start_time), args)

  

  # remove temp files
  # utils.rm_rf(args.tempbase)

  # for DEBUG
  if args.local_save != "":
    utils.logging("[INFO] Save to local.", args)
    utils.merge_hdfs( result_path, args.local_save )



