import socket
from datetime import datetime
import os
import time
import sys
from random import randint
import subprocess
import argparse

parser = argparse.ArgumentParser(description='Poll for updates and notify')

parser.add_argument('--server-ip', default="127.0.0.1", type=str, help='IP address of the morph server')
parser.add_argument('--server-port', default=1234, type=int, help='Port of the morph server')
parser.add_argument('--from-sim', default=False, action='store_true', help='Whether or not to get available VMs from simulator')
parser.add_argument('--zone', default="us-west1-a", type=str, help='Cluster zone')
parser.add_argument('--available_machines_list', default="", type=str, help='File of the available machine IPs')
parser.add_argument('--running_machines_list', default="", type=str, help='File of the currently running machine IPs')
parser.add_argument('--simulated_machines_list', default="", type=str, help='File of the simulated machine IPs')
parser.add_argument('--log_file', default="", type=str, help='File to write the number of available VMs')

# cluster = sys.argv[1]
counter = 0
possibly_dead_nodes = []

args = parser.parse_args()


def get_ip(x):
    cmd =  "gcloud compute instances describe " + x + " --format get(networkInterfaces[0].networkIP) --zone " + args.zone
    ip_addr = subprocess.run(cmd.split(), stdout=subprocess.PIPE).stdout.decode()
    ip_addr = ip_addr.strip()
    return ip_addr


def client(ip, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(bytes(message, 'ascii'))

def poll_and_update(f):
    print(str(datetime.now()), flush=True)
    current_machines = get_current_machines()
    current_num_machines = len(current_machines)
    print("Current:", current_machines,flush=True)

    new_machines = get_available_machines_sim()
    print("New", new_machines, flush=True)

    if False: #sorted(new_machines) == sorted(current_machines):
        print("no change", flush=True)
    else:
        # machines_added = [m for m in new_machines if m not in current_machines]
        master_port = 1234
        master_ip = get_ip(new_machines[0])
        msg = f"change {len(new_machines)} {master_ip} {master_port}"
        client(args.server_ip, args.server_port, msg)
        print(msg, flush=True)
    status = str(time.time()) + "," + str(len(new_machines)) + "\n"
    f.write(status)
    f.flush()

def get_current_machines():
    f = open(args.running_machines_list,"r")
    machines = f.read().split("\n")
    machines = [m for m in machines if len(m) > 0]
    return machines

def get_avail(vm_list, get_ip, sim=False):

    avail_vm_list = vm_list
    f = open(args.available_machines_list, 'w')
    for v in avail_vm_list: # TODO: what if someone is reading from this file?
        f.write(v + "\n")
    f.flush()
    return avail_vm_list


def get_available_machines_sim():
    f = open(args.simulated_machines_list,"r")
    machines = f.read().split("\n")
    machines = [m for m in machines if len(m) > 0]
    return get_avail(machines, get_ip=False, sim=True)


def notify():
     f=open(args.log_file, 'w')
     while True:
        poll_and_update(f)
        time.sleep(60)

if __name__ == "__main__":
    notify()
