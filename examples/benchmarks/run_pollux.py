
import os, subprocess
from argparse import ArgumentParser, REMAINDER
import socket, time
import sys


running_machines_list = "run_list"

def get_env_vars(file):

    if not os.path.exists(file):
        return ""
    f =  open(file,"r")
    envstr = ""
    for line in f:
        envstr += line.strip("\n")
        return envstr

def parse_args():
    parser = ArgumentParser(description="Pollux - script that starts training processes at each node") 
    parser.add_argument("--machine-list", type=str, default="available_machines.out",
                    help = "path to a file with the names of the VMs to start training. These should be available to gcloud-ssh into through the manager ")
    
    parser.add_argument("--gpus-per-node", type=int, default=4,
                                    help = "number of GPUs per machine")

    parser.add_argument("--master-ip", type=str, default=None,
                                        help= "IP address of the rank-0 training process.")

    parser.add_argument("--master-port", type=str, default=None,
                                        help= "Port address for the rank-0 training process.")

    parser.add_argument("--training-script", type=str, default=None, nargs='?',
                                            help="The full path to the single GPU training program/script to be launched in parallel")


    parser.add_argument("checkpoint-path", type=str, default=None, nargs='?',
                                            help="Checkpoint path")


    # rest from the training program
    parser.add_argument('--training_script_args', nargs=REMAINDER)
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    with open(args.machine_list, "r") as f:
        content = f.read()
        reachable_machines = content.split("\n")
        reachable_machines = [m for m in reachable_machines if len(m) > 0]  
        with open(running_machines_list, "w") as of:
            of.write(content)
    print(reachable_machines)  
    
    reachable_count = len(reachable_machines)
    num_replicas = reachable_count * args.gpus_per_node

    if reachable_count == 0:
        print("Empty machine list, nothing to run!")
        exit()

    os.makedirs("ssh_logs", exist_ok=True)
   # current_env["PATH"] = "PATH=\"/home/varuna/anaconda3/bin:$PATH\""
    
    res_args = ' '.join((str(n) for n in args.training_script_args))  

    worker_rank = 0
    for i,machine in enumerate(reachable_machines):


            for j in range(args.gpus_per_node):

                out_file = open(f"ssh_logs/ssh_out_{worker_rank}", "w")
                err_file = open(f"ssh_logs/ssh_err_{worker_rank}", "w")

                launch_cmd = f"python3 {args.training_script} --local_rank {j} {res_args}" 

                cmd1 = f"gcloud compute ssh {machine} --zone us-west1-a --command \" echo \' {launch_cmd}\' > /home/fot/adaptdl/examples/benchmarks/launch_pollux.sh; ADAPTDL_MASTER_ADDR={args.master_ip} ADAPTDL_MASTER_PORT={args.master_port} ADAPTDL_NUM_REPLICAS={num_replicas} ADAPTDL_REPLICA_RANK={worker_rank} bash /home/fot/adaptdl/examples/benchmarks/launch_pollux.sh \" "

                # better with gcloud
                fname = "file_"+str(worker_rank)+".sh"
                f = open(fname, 'w')
                f.write(cmd1+'\n')
                f.flush()

                cmd = ["bash"]
                cmd.append(fname)
                print(" ".join(cmd ))
                worker_rank += 1
       
        
                process = subprocess.Popen(cmd,  
                                            stdout=out_file,
                                            stderr=err_file)
