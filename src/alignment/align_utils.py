import subprocess
import time
import os
import pysam
import re
import string
import sys
sys.path.append( os.path.join(os.path.dirname(__file__), "..", "utils") )
import utils




###
# work on chunk.
# write sequences into file
# and call bowtie2.
# results are parsed as sam format
###
def mapping(i, pref, methods, ptn, args):
  # write files on temp
  # get references
  if not os.path.exists( args.tempbase ):
    os.makedirs( args.tempbase )

  ref_path = os.path.join( args.tempbase, "ref" )

  if not os.path.exists( os.path.join(args.ref, "index") ):
    utils.read_hdfs( os.path.join(args.ref, "index"), ref_path )

  # check file existence
  iPath = os.path.join( args.tempbase, "iv_%s_%d.fa" % (pref, i) )

  save_pair( iPath, ptn )

  # run bowtie2
  for method in methods:
    oPath = os.path.join( args.tempbase, "%s_%d.sam" % (method, i))

    query = gen_bowtie_query(\
      os.path.join( ref_path, method),\
      iPath,\
      oPath)

    print(query)
    proc = subprocess.Popen(query).communicate()

  # get result
  for method in methods:
    oPath = os.path.join( args.tempbase, "%s_%d.sam" % (method, i))
    for k, v in read_sam( oPath, method):
      yield (k, v)





###
# get filename, <read_id, seq> data, return value
# and write data to file in FASTA format
# output: return value
###
def save_pair(f, it):
  with open(f, 'w') as fp:
    for read_id, seq in it:
      fp.write(">%s\n%s\n" % (read_id, seq))





###
# bowtie2 command
###
def gen_bowtie_query(ref_prefix, input_file, output_file):
  return  ["bowtie2",
           "--local",
           "--quiet",
           "-D", "50",
           "--norc",
           "--sam-nohead",
           "-k", "2",
           "-x", ref_prefix,
           "-f",
           "-U", input_file,
           "-S", output_file]
           # "-p", "2",



###
# read samfile into tuples
###
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
          yield (QNAME.encode('ascii','replace'), (method, mismatches, RNAME, int(POS)-1, CIGAR.encode('ascii','replace')))
      except ValueError:
        print filename
        print line



###
# select the most probable transformation
# and find uniq alignment
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


  if raw is None:
    print "[ERROR] raw seq cannot be null"
    return None

  uniq = find_uniq_alignment( group)

  if uniq is None:
    return None

  return (uniq, raw)



###
# find_uniq alignment
###
def find_uniq_alignment(group):
  methods = {"W_C2T": 0, "C_C2T": 1, "W_G2A": 2, "C_G2A": 3}
  sorted_list = []
  for _, i in methods.iteritems():
    muniq = get_and_uniq( group[i], 1 ) # (value, is_uniq)
    if muniq != None:
      sorted_list.append( muniq)


  sorted_list = sorted(sorted_list, key=lambda x: x[0][1]) # by mismatch
  length = len(sorted_list)


  if length >= 1:
    curr = sorted_list[0]
    next = sorted_list[1] if length >= 2 else ([None, None], False)

    if curr[0][1] != next[0][1] and curr[1]:
      return curr[0]
  
  return None    
      
  




###
# get uniq element from list.
# each element is a tuple
# and can be compared with i-th value.
###
def get_and_uniq(lst, i):
  # i is criteria
  tmp_lst = sorted(lst, key=lambda x: x[i])
  l = len( tmp_lst)

  if l == 0:
    return None
  elif l == 1:
    return (tmp_lst[0], True) # uniq
  else:
    curr = tmp_lst[0]
    next = tmp_lst[1]

    if curr[i] != next[i]:
      return (curr, True) # uniq
    else:
      return (curr, False) # not uniq






def dep_find_uniq_alignment(group):
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
      # # count num
      # cnt = 1
      # for i in range(idx+1, length):
      #   if curr[1] == sorted_list[i][1]:
      #     cnt += 1
      #   else:
      #     break
      # value = curr
      # uniq = "M%d" % cnt
      return None
      
  # TODO: maybe some methyl level call here
  return (uniq,) + value





###
# get uniq element from list.
# each element is a tuple
# and can be compared with i-th value.
###
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




###
# calculate methylation level
###

def calc_methyl(pair, ref_dict, num_mm):
  # add ref seq
  (read_id, (info, origin_seq)) = pair

  # (uniq, method, mismatches, chrm, pos, cigar_str) = info
  uniq = "U"
  (method, mismatches, chrm, pos, cigar_str) = info
  ref_chrm, ref_length = ref_dict[chrm]
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
    target_seq = origin_seq.translate( utils.make_trans_with("C") )[::-1]
    cigar = list(reversed(cigar))

  elif method == "C_G2A": # BSWR - GA
    target_strand = "W"
    start_pos = ref_length - pos - ref_targeted_length
    target_seq = origin_seq.translate( utils.make_trans_with("C") )[::-1]
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
    ref_seq = ref_seq.translate( utils.make_trans_with("C") )[::-1]
    # swap prev and next
    tmp = prev2_seq.translate( utils.make_trans_with("C") )[::-1]
    prev2_seq = next2_seq.translate( utils.make_trans_with("C") )[::-1]
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

  if mismatches > num_mm:
    return None

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

  # make cigar
  # if method == "C_C2T" or method == "C_G2A":
  if method == "C_C2T":
    cigar = list(reversed(cigar))
    cigar_str = ""
    for sym, n in cigar:
      cigar_str += "%d%s" % (n, sym)


  return (read_id, (mismatches, method, chrm, target_strand, start_pos, cigar_str, target_seq, methy, "%s_%s_%s" % (prev2_seq, g_aln, next2_seq), uniq))




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
# convert tuple to string
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
          start_pos+1,\
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
