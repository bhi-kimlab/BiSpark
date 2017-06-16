import subprocess
import time
import os
import pysam
import re
import string
import sys
from shutil import rmtree
from collections import defaultdict
from pyspark.storagelevel import StorageLevel
from pyspark import SparkContext, SparkConf
from pyspark.shuffle import ExternalSorter
from pyspark.rdd import _parse_memory


###
# test flag
# if set true, it runs on small data
# else, it runs on bigger data
###
TEST = True

ref_path = os.path.join( "/data", "project", "SparkMethyl", "test", "ref_genomes" )
out_path = os.path.join( "/data", "project", "SparkMethyl", "test", "pytmp" )


###
# align function
###
def align(sc, machine):
  machine = 21
  i_file = "hdfs:///data/input/srr_10m.myf"
  o_file = "hdfs:///data/output/%s" % sc.applicationId

  ## read from hadoop
  # hadoop_conf = {}
  # in_seqs = sc.newAPIHadoopFile(i_file, "org.apache.hadoop.mapreduce.lib.input.TextInputFormat", "org.apache.hadoop.io.LongWritable", "org.apache.hadoop.io.Text", conf=hadoop_conf) \
  #             .map( lambda x: myf_to_key_value( x[1]))
  in_seqs = sc.textFile( i_file ) \
          .map( lambda x: myf_to_key_value( x)) \
          .repartition( machine)

  ## transform and get result of bowtie
  combined_seqs = in_seqs.mapPartitionsWithIndex( lambda i, ptn: bowtie_on_chunk(i, ptn) )

  # get uniq
  joined_seqs = combined_seqs\
                  .mapValues( lambda x: select_and_find_uniq_alignment( x))\
                  .filter( lambda (k, v): not (v is None))


  chrkey_rdd = joined_seqs\
                .map( lambda (k, v): (v[0][3], (k, v)) )\
                .repartitionAndSortWithinPartitions(machine)
  
  res_rdd = chrkey_rdd\
    .mapPartitions( lambda ptn: calc_methyl_partitions(ptn) )
  

  res_rdd.map( lambda x: res_to_string(x))\
    .saveAsTextFile( o_file )


###
# align fit on partition
###
def align_repartition(sc, x_machine):
  machine = 21
  i_file = "hdfs:///data/input/srr_10m.myf"
  o_file = "hdfs:///data/output/%s" % sc.applicationId


  ## read from hadoop
  # hadoop_conf = {}
  # in_seqs = sc.newAPIHadoopFile(i_file, "org.apache.hadoop.mapreduce.lib.input.TextInputFormat", "org.apache.hadoop.io.LongWritable", "org.apache.hadoop.io.Text", conf=hadoop_conf) \
  #             .map( lambda x: myf_to_key_value( x[1])) \
  #             .repartition(machine) \
  #             .cache()
  in_seqs = sc.textFile( i_file ) \
            .map( lambda x: myf_to_key_value( x)) \
            .repartition(machine) \
            .cache()


  ## transform and get result of bowtie
  wc2t_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "C", "T")) ) \
                    .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get(i, "C2T", ["W_C2T", "C_C2T"], ptn, ref_path) )
  
  wg2a_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "G", "A")) ) \
                    .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get(i, "G2A", ["W_G2A", "C_G2A"], ptn, ref_path) )

  # wc2t_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "C", "T")) ) \
  #                   .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get_pipe(i, "C2T", ["W_C2T", "C_C2T"], ptn, ref_path) )
  
  # wg2a_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "G", "A")) ) \
  #                   .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get_pipe(i, "G2A", ["W_G2A", "C_G2A"], ptn, ref_path) )


  
  combined_seqs = sc.union( [in_seqs, wc2t_seqs, wg2a_seqs] )\
                    .combineByKey( lambda v: [v],\
                                  lambda lst, v: lst + [v],\
                                  lambda l1, l2: l1 + l2 )

  # get uniq
  joined_seqs = combined_seqs\
                  .mapValues( lambda x: select_and_find_uniq_alignment( x))\
                  .filter( lambda (k, v): not (v is None))


  # chrkey_rdd = joined_seqs\
  #               .map( lambda (k, v): (v[0][3], (k, v)) )\
  #               .repartitionAndSortWithinPartitions(machine)

  chrkey_rdd = joined_seqs\
                .map( lambda (k, v): (v[0][3], (k, v)) )\
                .persist(StorageLevel.MEMORY_AND_DISK) \
                .sortByKey(numPartitions=machine)
  
  res_rdd = chrkey_rdd\
    .mapPartitions( lambda ptn: calc_methyl_partitions(ptn) )
  

  res_rdd.map( lambda x: res_to_string(x))\
    .saveAsTextFile( o_file )



###
# align fit on partition
# without repartition by key
###
def align_internal_sort(sc, x_machine):
  machine = 21
  i_file = "hdfs:///data/input/srr_10m.myf"
  o_file = "hdfs:///data/output/%s" % sc.applicationId


  memory = _parse_memory( sc.getConf().get("spark.python.worker.memory", "512m"))
  def internalPartition(iterator):
    sort = ExternalSorter(memory * 0.9).sorted
    return iter( sort( iterator, key=lambda x: x[0], reverse=False))


  ## read from hadoop
  # hadoop_conf = {}
  # in_seqs = sc.newAPIHadoopFile(i_file, "org.apache.hadoop.mapreduce.lib.input.TextInputFormat", "org.apache.hadoop.io.LongWritable", "org.apache.hadoop.io.Text", conf=hadoop_conf) \
  #             .map( lambda x: myf_to_key_value( x[1])) \
  #             .repartition(machine) \
  #             .cache()
  in_seqs = sc.textFile( i_file ) \
            .map( lambda x: myf_to_key_value( x)) \
            .repartition(machine) \
            .cache()


  ## transform and get result of bowtie
  wc2t_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "C", "T")) ) \
                    .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get(i, "C2T", ["W_C2T", "C_C2T"], ptn, ref_path) )
  
  wg2a_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "G", "A")) ) \
                    .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get(i, "G2A", ["W_G2A", "C_G2A"], ptn, ref_path) )

  # wc2t_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "C", "T")) ) \
  #                   .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get_pipe(i, "C2T", ["W_C2T", "C_C2T"], ptn, ref_path) )
  
  # wg2a_seqs = in_seqs.mapValues( lambda x: x.translate( make_trans_with("W", "G", "A")) ) \
  #                   .mapPartitionsWithIndex( lambda i, ptn: run_bowtie2_and_get_pipe(i, "G2A", ["W_G2A", "C_G2A"], ptn, ref_path) )


  
  combined_seqs = sc.union( [in_seqs, wc2t_seqs, wg2a_seqs] )\
                    .combineByKey( lambda v: [v],\
                                  lambda lst, v: lst + [v],\
                                  lambda l1, l2: l1 + l2 )

  # get uniq
  joined_seqs = combined_seqs\
                  .mapValues( lambda x: select_and_find_uniq_alignment( x))\
                  .filter( lambda (k, v): not (v is None))


  chrkey_rdd = joined_seqs\
                .map( lambda (k, v): (v[0][3], (k, v)) )\
                .mapPartitions(internalPartition)

  
  res_rdd = chrkey_rdd\
    .mapPartitions( lambda ptn: calc_methyl_partitions(ptn) )
  

  res_rdd.map( lambda x: res_to_string(x))\
    .saveAsTextFile( o_file )



###
def res_to_string(obj):
  (read_id, (mismatches, method, chrm, strand, start_pos, cigar_str, \
          bs_seq, methyl, ref_contig, uniq)) = obj

  optional = "%s\t%s\t%s\t%s\t%s\t%s" % (\
              ("XO:Z:%s" % method),\
              ("XS:i:%d" % 0),\
              ("NM:i:%d" % mismatches),\
              ("XM:Z:%s" % methyl),\
              ("XG:Z:%s" % ref_contig),\
              ("XU:Z:%s" % uniq)\
              )  

  res = "%s\t%d\t%s\t%d\t%d\t%s\t%s\t%d\t%d\t%s\t%s\t%s" % (\
          read_id,\
          (16 if strand == "C" else 0),\
          chrm,\
          start_pos,\
          255,\
          cigar_str,\
          "*",\
          0,\
          0,\
          bs_seq,\
          "*",\
          optional\
          )

  return res


###
def myf_to_key_value(s):
  tmp = s.encode('ascii','replace').split(",")
  return ( tmp[0], tmp[1] )


def to_iv_path(pref, i):
  return os.path.join( out_path, "iv_%s_%d.fa" % (pref, i))

###
# work on chunk
# chunk size is 128MB
###
def bowtie_on_chunk(i, ptn):
  # for return
  res = defaultdict(list)
  ## write trans sequence to file
  methods = [("C2T", ["W_C2T", "C_C2T"]), ("G2A", ["W_G2A", "C_G2A"])]

  c2t_trans_path = to_iv_path("C2T", i)
  g2a_trans_path = to_iv_path("G2A", i)

  stime = time.time()
  # write trans inputs
  with open( c2t_trans_path, 'w') as c2t_file, open( g2a_trans_path, 'w') as g2a_file:
    for rid, seq in ptn:
      c2t_file.write(">%s\n%s\n" % (rid, seq.translate( make_trans_with( "W", "C", "T")) ))
      g2a_file.write(">%s\n%s\n" % (rid, seq.translate( make_trans_with( "W", "G", "A")) ))
      res[ rid ].append( seq )

  print("[INFO] On Chunk. trans took: " + str( time.time() - stime ))

  stime = time.time()
  # launch bowtie
  for pref, mlst in methods:
    iv_path = to_iv_path( pref, i)
    for method in mlst:
      o_path = os.path.join( out_path, "%s_%d.sam" % (method, i))

      query = gen_bowtie_query(\
        os.path.join( ref_path, method),\
        iv_path,\
        o_path)

      proc = subprocess.Popen(query).communicate()

  print("[INFO] On Chunk. bowtie 4 took: " + str( time.time() - stime ))


  # get output
  for pref, mlst in methods:
    for method in mlst:
      o_path = os.path.join( out_path, "%s_%d.sam" % (method, i))
      for k, v in read_sam( o_path, method):
        res[ k ].append( v )

  # return iterator
  # return res.items()
  return iter(res.items())


###
def run_bowtie2_and_get(i, pref, methods, ptn, ref_path):
  # check file existence
  iPath = os.path.join( out_path, "iv_%s_%d.fa" % (pref, i) )
  if os.path.exists( iPath):
    os.remove( iPath )

  save_pair( iPath, ptn)

  # run bowtie2
  for method in methods:
    oPath = os.path.join( out_path, "%s_%d.sam" % (method, i))
    if os.path.exists(oPath):
      os.remove(oPath)

    query = gen_bowtie_query(\
      os.path.join( ref_path, method),\
      iPath,\
      oPath)

    proc = subprocess.Popen(query).communicate()


  for method in methods:
    oPath = os.path.join( out_path, "%s_%d.sam" % (method, i))
    for k, v in read_sam( oPath, method):
      yield (k, v)


def run_bowtie2_and_get_pipe(i, pref, methods, ptn, ref_path):
  # check file existence
  iPath = os.path.join( out_path, "iv_%s_%d.fa" % (pref, i) )
  if os.path.exists( iPath):
    os.remove( iPath )

  save_pair( iPath, ptn)

  # run bowtie2
  for method in methods:
    oPath = os.path.join( out_path, "%s_%d.sam" % (method, i))
    if os.path.exists(oPath):
      os.remove(oPath)

    query = gen_bowtie_query(\
      os.path.join( ref_path, method),\
      iPath,\
      oPath)

    proc = subprocess.Popen(query, stdout=subprocess.PIPE)
    for line in proc.stdout:
      yield parse_sam( line )





###
# fasta file to dictionary
###
def fasta2dic(f):
  res = defaultdict()
  for chrid, seq in read_fasta( f):
    res[ chrid ] = seq
    #print( chrid[:10] + "\t" + seq[:10] + "\n" )
  return res

###
def select_and_find_uniq_alignment(lst):
  methods = {"W_C2T": 0, "C_C2T": 1, "W_G2A": 2, "C_G2A": 3}
  group = [ [], [], [], [] ] # each index is method index
  raw = None

  for elem in lst:
    if isinstance(elem, str): # raw
      raw = elem
    else:
      group[ methods[ elem[0] ] ].append( elem)
      # group.append( elem)

  if raw is None:
    print "[ERROR] raw seq cannot be null"
    return None

  uniq = find_uniq_alignment( group)

  if uniq is None:
    return None

  return (uniq, raw)



def get_uniq(lst, i):
  # i is criteria
  tmp_lst = sorted(lst, key=lambda x: x[i])
  l = len( tmp_lst)

  if l == 0:
    return None
  elif l == 1:
    return tmp_lst[0]
  else:
    curr = tmp_lst[0]
    next = tmp_lst[1]

    if curr[i] != next[i]:
      return curr
    else:
      return None


def find_uniq_alignment(group):
  methods = {"W_C2T": 0, "C_C2T": 1, "W_G2A": 2, "C_G2A": 3}
  sorted_list = []
  for _, i in methods.iteritems():
    muniq = get_uniq( group[i], 1) # by mismatch
    if not muniq is None:
      sorted_list.append( muniq)


  sorted_list = sorted(sorted_list, key=lambda x: x[1]) # by mismatch
  length = len(sorted_list)
  idx = 0


  # no other in next?
  if length == 0:
    return None
  elif idx == length - 1:
    value = sorted_list[idx]
    uniq = "U"
  else:
    curr = sorted_list[idx]
    next = sorted_list[idx+1]
    
    # is unique?
    if curr[1] != next[1]:
      value = curr
      uniq = "U"
    else:
      # count num
      cnt = 1
      for i in range(idx+1, length):
        if curr[1] == sorted_list[i][1]:
          cnt += 1
        else:
          break
      value = curr
      uniq = "M%d" % cnt
      #DEBUG
      return None
      
  # TODO: maybe some methyl level call here
  return (uniq,) + value

###
# calculate methylation level
###
def calc_methyl_partitions(ptn):
  # we know that rows are sorted in chr level
  curr_chrm_name = ""
  curr_chrm_seq = ""
  curr_chrm_length = 0

  for (chrm_name, d) in ptn:
    if curr_chrm_name != chrm_name:
      print "[INFO] chrm change from %s to %s" % (curr_chrm_name, chrm_name)
      curr_chrm_name = chrm_name

      # load chrm file
      ref_file = os.path.join( ref_path, "splitted", "%s.fa" % curr_chrm_name)

      for _, seq in read_fasta( ref_file):
        curr_chrm_seq = seq

      curr_chrm_length = len(curr_chrm_seq)

    
    # get result
    yield calc_methyl(d, curr_chrm_seq, curr_chrm_length)



def calc_methyl(pair, ref_chrm, ref_length):
  # add ref seq
  (read_id, (info, origin_seq)) = pair

  (uniq, method, mismatches, chrm, pos, cigar_str) = info
  (cigar, ref_targeted_length) = parse_cigar(cigar_str)
  # # TODO
  # #["W_C2T", "C_C2T", "W_G2A", "C_G2A"]

  # preprocess
  if method == "W_C2T": # BSW - CT
    target_strand = "W"
    start_pos = pos
    target_seq = origin_seq

  elif method == "W_G2A": # BSCR - GA
    target_strand = "C"
    start_pos = pos
    target_seq = origin_seq.translate( make_trans_with("C") )[::-1]
    cigar = list(reversed(cigar))

  elif method == "C_G2A": # BSWR - GA
    target_strand = "W"
    start_pos = ref_length - pos - ref_targeted_length
    target_seq = origin_seq.translate( make_trans_with("C") )[::-1]
    cigar = list(reversed(cigar))

  elif method == "C_C2T": # BSC - CT
    target_strand = "C"
    start_pos = ref_length - pos - ref_targeted_length
    target_seq = origin_seq

  else:
    print method

  # get reference sequence
  # append before two letter and next two letter
  end_pos = start_pos + ref_targeted_length - 1
  prev2 = max(2-start_pos, 0)
  next2 = max(end_pos-ref_length+2, 0)
  
  prev2_seq = "N"*prev2 + ref_chrm[ (start_pos+prev2-2):start_pos ]
  ref_seq = ref_chrm[ start_pos:(end_pos+1) ]
  next2_seq = ref_chrm[ (end_pos+1):(end_pos+1+2-next2) ] + "N"*next2
  
  if target_strand == "C":
    ref_seq = ref_seq.translate( make_trans_with("C") )[::-1]
    # swap prev and next
    tmp = prev2_seq.translate( make_trans_with("C") )[::-1]
    prev2_seq = next2_seq.translate( make_trans_with("C") )[::-1]
    next2_seq = tmp


  # with contig, refseq, cigar
  # reconstruct alignment
  r_pos = cigar[0][1] if cigar[0][0] == "S" else 0
  g_pos = 0
  r_aln = g_aln = ""

  for (opt, count) in cigar:
    if opt == "M":
      r_aln += target_seq[ r_pos : (r_pos + count) ]
      g_aln += ref_seq[ g_pos : (g_pos + count) ]
      r_pos += count
      g_pos += count
    elif opt == "D":
      r_aln += '-'*count
      g_aln += ref_seq[ g_pos : (g_pos + count) ]
      g_pos += count
    elif opt == "I":
      r_aln += target_seq[ r_pos : (r_pos + count) ]
      g_aln += '-'*count
      r_pos += count

  
  # count mismatches
  slen = len(r_aln)
  if slen != len(g_aln):
    #TODO
    return None
  
  mismatches = 0
  for i in xrange( slen):
    if r_aln[i] != g_aln[i] and r_aln[i] != "N" and g_aln[i] != "N" and not( r_aln[i] == "T" and g_aln[i] == "C"):
      mismatches += 1

  # get methylation sequence
  methy = ""
  tmp = "-"
  read = r_aln
  gn_appended = g_aln + next2_seq
  # TODO: context should be added
  for i in xrange( slen):
    if gn_appended[i] == '-':
      continue
    elif r_aln[i] == "T" and gn_appended[i] == "C": # unmeth
      [n1, n2] = get_next2(gn_appended, i)
      if n1 == "G":
        tmp = "x"
      elif n2 == "G":
        tmp = "y"
      else:
        tmp = "z"
    elif r_aln[i] == "C" and gn_appended[i] == "C": # meth
      [n1, n2] = get_next2(gn_appended, i)
      if n1 == "G":
        tmp = "X"
      elif n2 == "G":
        tmp = "Y"
      else:
        tmp = "Z"
    else:
      tmp = "-"
    methy += tmp

  # return (read_id, mismatches, method, chrm, target_strand, start_pos, cigar, target_seq, methy, "%s_%s_%s" % (prev2_seq, g_aln, next2_seq))
  # return (read_id, (mismatches, method, chrm, target_strand, start_pos, cigar, target_seq, methy, "%s_%s_%s" % (prev2_seq, g_aln, next2_seq), uniq))
  return (read_id, (mismatches, method, chrm, target_strand, start_pos, cigar_str, target_seq, methy, "%s_%s_%s" % (prev2_seq, g_aln, next2_seq), uniq))




##############################
## helper from here
##############################

###
# get next 2 character of sequence
# except null character('-')
###
def get_next2(seq, pos):
  i = pos + 1
  res = ["N", "N"]
  rpos = 0

  for i in range((pos+1), len(seq)):
    if rpos >= 2:
      break
    elif seq[i] == "-":
      continue
    else:
      res[ rpos] = seq[i]
      rpos += 1

  return res

###
# bowtie2 command
###
def gen_bowtie_query(ref_prefix, input_file, output_file):
  return  ["bowtie2",
           "--local",
           "--quiet",
           # "-p", "1",
           "-p", "2",
           "-D", "50",
           "--norc",
           "--sam-nohead",
           "-k", "2",
           "-x", ref_prefix,
           "-f",
           "-U", input_file,
           "-S", output_file]

           

###
# get filename, <read_id, seq> data, return value
# and write data to file in FASTA format
# output: return value
###
def save_pair(f, it):
  with open(f, 'w') as fp:
    for (read_id, seq) in it:
      fp.write(">%s\n%s\n" % (read_id, seq))
  return

###
# transform DNA character
# by default, it capitalize all characters
# and if it's reverse strand(Watson strand), change a character to corresponding one.
# if a_from and a_to is given, additional transform should be applied.
###
def make_trans_with(strand, a_from = None, a_to = None):
  #logfile = open( os.path.join(out_path, "log.txt"), "a" )
  if strand == "W":
    ref_from = 'acgtACGT'
    ref_to = 'ACGTACGT'
  else:
    ref_from = 'acgtACGT'
    ref_to = 'TGCATGCA'
  #logfile.write( 'make trans with\n' )
  #logfile.write( '%s %s\n' % (ref_from, ref_to) )
  #logfile.flush()
  if a_from != None and a_to != None:
    ref_to = ref_to.translate( string.maketrans(a_from, a_to))
  #logfile.close()
  return string.maketrans(ref_from, ref_to)

###
# parsing cigar string, which is a part of alinger result.
# this information is used to restore alignment information.
# get string, output is < [<'type', length>], reference's length >
###
def parse_cigar(cigar):
  CIGARS = ["M", "I", "D", "S"]
  start = end = 0
  res = []
  ref_length = 0

  while end < len(cigar):
    if cigar[ end ] in CIGARS:
      # for cigar
      num = int( cigar[start:end])
      res.append( (cigar[end], num) )
      
      # for reference gemone length
      # TODO: soft clipping  not used?
      if cigar[ end ] == "M" or cigar[ end ] == "D":
        ref_length += num

      start = end = end + 1
    else:
      end += 1
  return (res, ref_length)


###
# similar to parse cigar
# but only used in writing sam section.
###
def encode_cigar(cigar):
  CIGARS = {"M": 0, "I": 1, "D": 2, "S": 4}
  res = []
  for (s, cnt) in cigar:
    res.append( (CIGARS[s], cnt) )
  return res

###
# read SAM format file (which is the result of alignment)
# and parse it to < read_id, (others) >
###
def parse_sam(line):
  (QNAME, FLAG, RNAME, POS, MAPQ, CIGAR, RNEXT, PNEXT, TLEN, SEQ, QUAL, OPTIONAL) = line.split("\t", 11)

  unmapped = int(FLAG) & 4

  # TODO: something for unmapped
  if not unmapped:
    # get mismatches
    mismatches = sys.maxint
    for tk in OPTIONAL.split("\t"):
      # if tk[:2] == "XM":
      #   mismatches = int( tk[5:] )
      if tk[:2] == "AS":
        mismatches = 1-int( tk[5:] )
    # res.append( (QNAME, [(method, mismatches, RNAME, int(POS)-1, CIGAR, SEQ, OPTIONAL)]) )
    return (QNAME.encode('ascii','replace'), (method, mismatches, RNAME, int(POS)-1, CIGAR.encode('ascii','replace')))  



def read_sam(filename, method = ""):
  with open( filename, 'r') as fp:
    for line in fp:
      try:
        (QNAME, FLAG, RNAME, POS, MAPQ, CIGAR, RNEXT, PNEXT, TLEN, SEQ, QUAL, OPTIONAL) = line.split("\t", 11)

        unmapped = int(FLAG) & 4

        # TODO: something for unmapped
        if not unmapped:
          # get mismatches
          mismatches = sys.maxint
          for tk in OPTIONAL.split("\t"):
            # if tk[:2] == "XM":
            #   mismatches = int( tk[5:] )
            if tk[:2] == "AS":
              mismatches = 1-int( tk[5:] )
          # res.append( (QNAME, [(method, mismatches, RNAME, int(POS)-1, CIGAR, SEQ, OPTIONAL)]) )
          yield (QNAME.encode('ascii','replace'), (method, mismatches, RNAME, int(POS)-1, CIGAR.encode('ascii','replace')))
      except ValueError:
        print filename
        print line




###
# read FASTA format file (which is the raw sequence file)
# and parse it to < uniq_id, sequence string >
# (if it's reference file, uniq is "chromosome number",
# if it's sequencing file, uniq is read id.
###
def read_fasta(fasta_file):
  input = open(fasta_file, 'r')

  sanitize = re.compile(r'[^ACTGN]')
  sanitize_seq_id = re.compile(r'[^A-Za-z0-9]')

  chrom_seq = ''
  chrom_id = None

  for line in input:
    if line[0] == '>':
      if chrom_id is not None:
        yield chrom_id, chrom_seq
      
      chrom_id = sanitize_seq_id.sub('_', line.split()[0][1:]).encode('ascii','replace')
      chrom_seq = ''
    else:
      chrom_seq += sanitize.sub('N', line.strip().upper()).encode('ascii','replace')

  yield chrom_id, chrom_seq

  input.close()

###
# Writer class.
# Used to write the result in SAM format
###
class Writer:
  def __init__(self, filename, ref_genome):
    
    header = { 'HD' : { 'VN': '1.0'},
               'SQ' : [ {'LN' : len(v), 'SN' : k} for k, v in ref_genome.iteritems() ],
               'PG' : [ { 'ID' : 1, 'PN' : 'BSpark', 'CL' : "TODO"} ]
             }
    self.file = pysam.AlignmentFile(filename, 'wh', header = header)
    self.ref_id_dict = {}
    for i, d in enumerate( header['SQ']):
      self.ref_id_dict[ d['SN']] = i



  def close(self):
    self.file.close()

  def write(self, obj):
    (read_id, mismatches, method, chrm, strand, start_pos, cigar, \
            bs_seq, methyl, ref_contig, uniq) = obj


    o = pysam.AlignedSegment()
    o.query_name = read_id
    o.query_sequence = bs_seq
    o.flag = 0x10 if strand == "C" else 0
    o.reference_id = self.ref_id_dict[ chrm]
    o.reference_start = start_pos
    o.mapping_quality = 255
    o.cigartuples = encode_cigar( cigar)
    o.next_reference_id = -1
    o.next_reference_start = -1
    o.query_qualities = None

    o.set_tags( [ ('XO', method), \
                   ('XS', 0), \
                   ('NM', mismatches), \
                   ('XM', methyl), \
                   ('XG', ref_contig), \
                   ('XU', uniq) ])
    self.file.write( o)

def read_fasta_line(lines, broadcast_re):
    re_value = broadcast_re.value
    if len(lines[1]) == 0:
        return None
    sanitize = re_value[0]
    sanitize_seq_id = re_value[1] 
    test_line = lines[1].encode('ascii','ignore').split('\n')

    chrom_id = sanitize_seq_id.sub('_', test_line[0].replace('>',''))
    chrom_seq = sanitize.sub('N', test_line[1].strip().upper())

    return chrom_id, ''.join(chrom_seq)







##############################
## main
##############################
if __name__ == "__main__":
  conf = SparkConf().setAppName("inSort&p2Example")
  sc = SparkContext(conf=conf)

  try:
    rmtree( os.path.join( out_path, "toFile"))
  except OSError:
    print "res dir not exist"

  machine = sys.argv[1]
  bc_machine = sc.broadcast( machine)

  # align( sc, bc_machine.value)
  # align_repartition( sc, bc_machine.value)
  align_internal_sort(sc, bc_machine.value)