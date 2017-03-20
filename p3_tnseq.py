
#!/usr/bin/env 
import os, sys
import argparse
import requests


def get_genome(parameters):
    genome_url= "data_url/genome_sequence/?eq(genome_id,gid)&limit(25000)".replace("data_url",parameters["data_url"]).replace("gid",parameters["gid"])
    print genome_url
    headers = {"accept":"application/sralign+dna+fasta"}
    #print "switch THE HEADER BACK!"
    #headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
    req = requests.Request('GET', genome_url, headers=headers)
    prepared = req.prepare()
    #pretty_print_POST(prepared)
    s = requests.Session()
    response=s.send(prepared)
    handle = open(os.path.join(parameters["output_dir"],parameters["gid"]+".fna"), 'w')
    if not response.ok:
        sys.stderr.write("API not responding. Please try again later.\n")
        sys.exit(2)
    else:
        for block in response.iter_content(1024):
            handle.write(block)

def get_annotation(parameters):
    annotation_url= "data_url/genome_feature/?and(eq(genome_id,gid),eq(annotation,PATRIC),or(eq(feature_type,CDS),eq(feature_type,tRNA),eq(feature_type,rRNA)))&limit(25000)".replace("data_url",parameters["data_url"]).replace("gid",parameters["gid"])
    print annotation_url
    headers = {"accept":"application/cufflinks+gff"}
    #print "switch THE HEADER BACK!"
    #headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
    req = requests.Request('GET', annotation_url, headers=headers)
    prepared = req.prepare()
    #pretty_print_POST(prepared)
    s = requests.Session()
    response=s.send(prepared)
    handle = open(os.path.join(parameters["output_dir"],parameters["gid"]+".gff"), 'w')
    if not response.ok:
        sys.stderr.write("API not responding. Please try again later.\n")
        sys.exit(2)
    else:
        for block in response.iter_content(1024):
            handle.write(block)

def get_files(job_data, server_data):
    genome_dirs=[job_data.output_dir]
    job_data["data_url"]=server_data.data_url
    for g in job_data.genome_ids:
        get_annotation(job_data)
        get_genome(job_data)
    return genome_dirs

def run_alignment(genome_list, library_dict, parameters, output_dir): 
    #modifies library_dict sub replicates to include 'bowtie' dict recording output files
    for genome in genome_list:
        genome_link=os.path.join(output_dir, os.path.basename(genome["genome"]))
        final_cleanup=[]
        if not os.path.exists(genome_link):
            subprocess.check_call(["ln","-s",genome["genome"],genome_link])
        cmd=["tpp", "-bwa", "bwa", "-ref", genome.genome]
        #thread_count=multiprocessing.cpu_count()
        #cmd+=["-p",str(thread_count)]
        #if genome["dir"].endswith('/'):
        #    genome["dir"]=genome["dir"][:-1]
        #genome["dir"]=os.path.abspath(genome["dir"])
        #genome["output"]=os.path.join(output_dir,os.path.basename(genome["dir"]))
        for library in library_dict:
            rcount=0
            for r in library_dict[library]["replicates"]:
                cur_cleanup=[]
                rcount+=1
                target_dir=output_dir
            #    target_dir=os.path.join(genome["output"],library,"replicate"+str(rcount))
            #    target_dir=os.path.abspath(target_dir)
            #    subprocess.call(["mkdir","-p",target_dir])
                cur_cmd=list(cmd)
                if "read2" in r:
                    cur_cmd+=["-reads1",r["read1"]," -reads2",r["read2"]]
                    name1=os.path.splitext(os.path.basename(r["read1"]))[0]
                    name2=os.path.splitext(os.path.basename(r["read2"]))[0]
                    base_name=os.path.join(target_dir,name1+"_"+name2)
                else:
                    cur_cmd+=["-reads1",r["read1"]]
                    name1=os.path.splitext(os.path.basename(r["read1"]))[0]
                    base_name=os.path.join(target_dir,name1)
                sam_file = base_name+".sam"
                cur_cleanup.append(sam_file)
                bam_file=sam_file[:-4]+".bam"
                r[genome["genome"]]={}
                r[genome["genome"]]["bam"]=bam_file
                cur_cmd+=["-S",sam_file]
                if os.path.exists(bam_file):
                    sys.stderr.write(bam_file+" alignments file already exists. skipping\n")
                else:
                    print cur_cmd
                    subprocess.check_call(cur_cmd) #call bowtie2
                if not os.path.exists(bam_file):
                    subprocess.check_call("samtools view -Su "+sam_file+" | samtools sort -o - - > "+bam_file, shell=True)#convert to bam
                    subprocess.check_call("samtools index "+bam_file, shell=True)
                    #subprocess.check_call('samtools view -S -b %s > %s' % (sam_file, bam_file+".tmp"), shell=True)
                    #subprocess.check_call('samtools sort %s %s' % (bam_file+".tmp", bam_file), shell=True)
                for garbage in cur_cleanup:
                    subprocess.call(["rm", garbage])
        for garbage in final_cleanup:
            subprocess.call(["rm", garbage])


def main(server_setup, job_data):
    required_data=["library_names","output_dir","read_files","genome_ids"]
    for data in required_data:
        if not data in job_data or len(job_data[data]) == 0:
            sys.stderr.write("Missing "+ data +"\n")
            sys.exit(2)
    
    library_dict={}
    library_list=[]
    library_list=job_data["library_names"]
    output_dir=job_data.output_dir
    for lib in library_list:
        library_dict[lib]={"library":lib}
    count=0
    #add read/replicate structure to library dict
    for read in job_data.readfiles:
        replicates=read.split(',')
        rep_store=library_dict[library_list[count]]["replicates"]=[]
        for rep in replicates:
            pair=rep.split('%')
            pair_dict={"read1":pair[0]}
            if len(pair) == 2:
                pair_dict["read2"]=pair[1]
            rep_store.append(pair_dict)
        count+=1
    genome_dirs=get_files(job_data.genome_ids)
    genome_list=[]
    for g in genome_dirs:
        cur_genome={"genome":[],"annotation":[],"dir":g,"hisat_index":[]}
        for f in os.listdir(g):
            if f.endswith(".fna") or f.endswith(".fa") or f.endswith(".fasta"):
                cur_genome["genome"].append(os.path.abspath(os.path.join(g,f)))
            elif f.endswith(".gff"):
                cur_genome["annotation"].append(os.path.abspath(os.path.join(g,f)))

        if len(cur_genome["genome"]) != 1:
            sys.stderr.write("Too many or too few fasta files present in "+g+"\n")
            sys.exit(2)
        else:
            cur_genome["genome"]=cur_genome["genome"][0]
        if len(cur_genome["annotation"]) != 1:
            sys.stderr.write("Too many or too few gff files present in "+g+"\n")
            sys.exit(2)
        else:
            cur_genome["annotation"]=cur_genome["annotation"][0]
        #if args.index:
        #    if len(cur_genome["hisat_index"]) != 1:
        #        sys.stderr.write("Missing hisat index tar file for "+g+"\n")
        #        sys.exit(2)
        #    else:
        #        cur_genome["hisat_index"]=cur_genome["hisat_index"][0]


        genome_list.append(cur_genome)
    output_dir=os.path.abspath(output_dir)
    subprocess.call(["mkdir","-p",output_dir])
    run_alignment(genome_list, library_dict, parameters, output_dir)
    run_transit(genome_list, library_dict, parameters, output_dir)
    cleanup(genome_list, library_dict, parameters, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    jobinfo = parser.add_mutually_exclusive_group(required=True)
    jobinfo.add_argument('--jfile', 
            help='json file for job {"genome_ids":[x],"library_names":[x], "transit_params":{key:value}, "output_dir":x, "read_files":x')
    jobinfo.add_argument('--jstring', help='json string from user input')
    serverinfo = parser.add_mutually_exclusive_group(required=True)
    serverinfo.add_argument('--sfile', help='server setup JSON file')
    serverinfo.add_argument('--sstring', help='server setup JSON string')

    #parser.add_argument('-g', help='genome ids to get *.fna and annotation *.gff', required=True)
    #parser.add_argument('-L', help='csv list of library names for comparison', required=True)
    #parser.add_argument('-p', help='JSON formatted parameter list for TRANSIT keyed to program', required=True)
    #parser.add_argument('-o', help='output directory. defaults to current directory.', required=False)
    #parser.add_argument('readfiles', nargs='+', help="whitespace sep list of read files. shoudld be \
    #        ws separates control (first) from experiment files (second),\
    #        a comma separates replicates, and a percent separates pairs.")
    if len(sys.argv) ==1:
        parser.print_help()
        sys.exit(2)
    args = parser.parse_args()
    try:
        job_data = json.loads(args.jstring) if args.jstring else json.load(open(args.jfile,'r'))
    except:
        sys.stderr.write("Failed to parse user provided form data \n")
        raise
    #parse setup data
    try:
        server_setup= json.loads(args.sstring) if args.sstring else json.load(open(args.sfile,'r'))
    except:
        sys.stderr.write("Failed to parse server data\n")
        raise
    
    main(server_setup, job_data)
