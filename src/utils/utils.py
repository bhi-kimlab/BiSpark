import time
import os
import pysam
import re
import string
import sys
import subprocess
import random
import tempfile
import shutil
from datetime import datetime

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
      
      # chrom_id = sanitize_seq_id.sub('_', line.split()[0][1:]).encode('ascii','replace')
      chrom_id = line.split()[0][1:].encode('ascii','replace')
      chrom_seq = ''
    else:
      chrom_seq += sanitize.sub('N', line.strip().upper()).encode('ascii','replace')

  yield chrom_id, chrom_seq

  input.close()


### 
# mkdir -p
###
def mkdir(d):
  if not os.path.exists(d):
    os.makedirs(d)


###
# rm -rf
###
def rm_rf(d):
  shutil.rmtree(d)



###
# read file from hdfs
###
def read_hdfs(hdfs_file, f):
  pipe = subprocess.Popen(["hdfs", "dfs", "-get", hdfs_file, f])
  pipe.wait()


###
# write file from hdfs
###
def write_hdfs(f, hdfs_file):
  pipe = subprocess.Popen(["hdfs", "dfs", "-mkdir", "-p", os.path.dirname(hdfs_file)])
  pipe.wait()

  pipe = subprocess.Popen(["hdfs", "dfs", "-put", f, hdfs_file])
  pipe.wait()


###
# write file from hdfs
###
def copy_to_hdfs(d, hdfs_dir, remove_original = False):
  pipe = subprocess.Popen(["hdfs", "dfs", "-mkdir", "-p", hdfs_dir])
  pipe.wait()

  f = os.path.join(d, "*")
  pipe = subprocess.Popen(" ".join(["hdfs", "dfs", "-put", f, hdfs_dir]), shell=True)
  pipe.wait()

  if remove_original:
    rm_rf(d)



###
# merge files in drectory
###
def merge_hdfs(d, f):
  pipe = subprocess.Popen(["hdfs", "dfs", "-getmerge", d, f])
  pipe.wait()


###
# gen tempfile
###
def gen_file():
  s = "/tmp/spm-%s" % (''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
  # s = "/home/dane2522/project/SparkMethyl/SparkMethyl/tmp/spm-%s" % (''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
  s += str(int(time.time()))
  return s


###
# convert to myf
###
def convert_to_myf(inf, outf, remove_tmp=True):
  tmprfile = gen_file()
  tmpwfile = tmprfile + "w"

  read_hdfs(inf, tmprfile)

  with open( tmpwfile, 'w') as wt:
    for read_id, seq in read_fasta( tmprfile): 
      wt.write("%s,%s\n" % (read_id, seq))

  write_hdfs(tmpwfile, outf)

  if remove_tmp:
    os.remove(tmprfile)
    os.remove(tmpwfile)

  return tmprfile, tmpwfile


###
# logging
###
def logging(s, args):
  logdir = os.path.dirname( args.log )
  mkdir( logdir )

  s = "%s: %s" % (datetime.now(), s)
  with open(args.log, 'a') as fw:
    fw.write("%s\n" % s)
  print(s)


###
# line to key-value pair
###
def line2kv(s):
  tmp = s.encode('ascii','replace').split(",")
  return ( tmp[0], tmp[1] )



###
# transform DNA character
# by default, it capitalize all characters
# and if it's reverse strand(Watson strand), change a character to corresponding one.
# if a_from and a_to is given, additional transform should be applied.
###
def make_trans_with(strand, a_from = None, a_to = None):
  if strand == "W":
    ref_from = 'acgtACGT'
    ref_to = 'ACGTACGT'
  else:
    ref_from = 'acgtACGT'
    ref_to = 'TGCATGCA'

  if a_from != None and a_to != None:
    ref_to = ref_to.translate( string.maketrans(a_from, a_to))

  return string.maketrans(ref_from, ref_to)