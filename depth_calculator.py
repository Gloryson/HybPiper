#!/usr/bin/env python

helptext='''This script will use bwa and samtools to determine the depth of coverage 
across a sequence generated by HybSeqPipeline. Reads will be mapped against the coding
sequence. The coding sequence will be aligned to the reference gene, and depth estimates
will be relative to the reference.

By default the script will do this for the CDS generated for the gene.
If you have run the "get_introns.py" script on the gene, you can get coverage for those
regions instead with --introns

'''

import sys,os,argparse,shutil
from Bio import SeqIO

def cmd_runner(cmd):
	sys.stderr.write("[CMD] {}\n".format(cmd))
	os.system(cmd)


def merge_seqs(genelist,prefix,file_type="coding"):
	'''Given a list of gene sequences, retreive the sequences and generate a single FASTA file.'''
	with open("{}_sequences.fasta".format(file_type),"w") as outfile:
		for gene in genelist:
			if file_type == "coding":
				seqfile = "{}/{}/sequences/FNA/{}.FNA".format(gene,prefix,gene)
			else:
				seqfile = "{}/{}/sequences/intron/gene_supercontig.fasta".format(gene,prefix)	
			
			seq = SeqIO.read(seqfile,'fasta')
			#seq.id = seq.id + "-" + gene
			SeqIO.write(seq,outfile,'fasta')

def build_index(file_type="coding"):
	bwa_index_cmd = "bwa index {}_sequences.fasta".format(file_type)
	cmd_runner(bwa_index_cmd)

	samtools_index_cmd = "samtools faidx {}_sequences.fasta".format(file_type)
	cmd_runner(samtools_index_cmd)

def map_reads(readfiles,file_type="coding",ncpu=6):
	'''Map the original reads to the sequences using bwa mem and samtools. Generates sorted bam file'''
	bwa_samtools_cmd = "bwa mem -t {} {}_sequences.fasta  {} | samtools view -bS - | samtools sort - {}.sorted".format(ncpu,file_type," ".join(readfiles),file_type)
	cmd_runner(bwa_samtools_cmd)

	samtools_index_cmd = "samtools index -b {}.sorted.bam".format(file_type)
	cmd_runner(samtools_index_cmd)
	
def make_pileup(file_type="coding"):
	'''Generate a pileup file for depth at all sequences'''
	mpileup_cmd = "samtools mpileup -f {}_sequences.fasta {}.sorted.bam > {}.mpileup".format(file_type,file_type,file_type)
	cmd_runner(mpileup_cmd)

def make_depth(file_type="coding"):
	'''Generate a depth file for depth at all sequences'''
	depth_cmd = "samtools depth {}.sorted.bam > {}.depth".format(file_type,file_type,file_type)
	cmd_runner(depth_cmd)	

def main():
	parser = argparse.ArgumentParser(description=helptext,formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument("--introns",help="Calculate coverage from complete exonerate contigs, not just surviving coding sequence.",default=False,action='store_true')
	#parser.add_argument("-c","--cds_fn",help="Fasta file of coding domain sequences (nucleotides), should have same names as corresponding protein file.",default=None)
	parser.add_argument("--genelist",help="Optional list of genes to retreive coverage. Default is to use genes_with_seqs.txt")

	parser.add_argument("-r","--readfiles",help="FULL PATH to FastQ read file(s) for mapping to the sequence.",nargs='+',required=True)
	parser.add_argument("--prefix",help="Prefix of sample directory generated by HybSeqPipeline",required=True)
	parser.add_argument("--pileup",help="Generate pileup of all reads that map against the gene sequences. Default is no.", action="store_true",default=False)
	
	args=parser.parse_args()
	
	if len(sys.argv) < 2:
		print helptext
		sys.exit(1)

	if os.path.isdir(args.prefix):
		basedir = os.getcwd()
		os.chdir(args.prefix)
	else:	
		sys.stderr.write("Directory {} not found!\n".format(args.prefix))
		sys.exit(1)	
		
	if args.genelist:
		genelist = [x.rstrip() for x in open(args.genelist).readlines()]
	else:
		genelist = [x.split()[0] for x in open('genes_with_seqs.txt').readlines()]
	
	if args.introns:
		if os.path.exists("intron_stats.txt"):
			file_type = "fullgene"
		else:
			sys.stderr.write("Intron stats not found, please run intronerate first!\n")
			sys.exit(1)	
	else:
		file_type = "coding"
	
	readfiles = [os.path.abspath(f) for f in args.readfiles]
	
	merge_seqs(genelist,args.prefix,file_type=file_type)
	build_index(file_type=file_type)				
	map_reads(readfiles,file_type=file_type)
	if args.pileup:
		make_pileup(file_type=file_type)
	else:
		make_depth(file_type=file_type)	


if __name__ == '__main__': main()
