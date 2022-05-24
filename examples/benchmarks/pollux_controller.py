# to be run in manager
import socket
import threading
from threading import Thread
import socketserver
import time
from datetime import datetime
import os
import subprocess
import sys

is_morphing = False
available_machines_list = sys.argv[1]
running_machines_list = sys.argv[2]     # TODO: check race confitions here
PORT = int(sys.argv[3])

my_ip = socket.gethostbyname(socket.gethostname())
HOST = my_ip

cnt=0
is_morphing=False

class Handler(socketserver.BaseRequestHandler):

     triggermorph = threading.Lock()

     def kill_all():

        print("kill all processes", flush=True)
        p = None
        try:
            p = subprocess.call(['bash', 'kill_all.sh', running_machines_list])
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print("signal timed/errored out: ",e)
            if p is not None:
                p.kill()


     def move_logs(i):
        print("Move old logs", flush=True)

        old_path = "/home/fot/adaptdl/examples/benchmarks/ssh_logs"
        new_path="/home/fot/adaptdl/examples/benchmarks/ssh_logs_" + str(i)
        cmd = "scp -r " + old_path + " " + new_path
        os.system(cmd)


     @staticmethod
     def start_remote(master_ip, master_port):
        global available_machines_list, my_ip
        cmd = f"python3 run_pollux.py --machine-list {available_machines_list} --gpus-per-node 4 --master-ip {master_ip} --master-port {master_port} --training-script /home/fot/adaptdl/examples/benchmarks/train_ddp_image.py --training_script_args --batch-size 128 --arch resnet50 --nclasses 10 --train-dir /cifar/train --num-dl 4 --autoscale-bsz"
        print(cmd)
        os.system(cmd)


     def handle(self):
        global cnt, is_morphing
        data = str(self.request.recv(1024), 'ascii')
        cur_thread = threading.current_thread()
        recv_time = datetime.now()
        print("{} got something from {}: {}".format(recv_time, self.client_address, data), flush=True)

        if 'change' in data:

            if (not Handler.triggermorph.acquire(timeout=1)):
                print("Morph in progress - abort")
                return

            print("Lock acquired by morph",flush=True)
            try:
                if not is_morphing:
                    print("Morphing!",flush=True)
                    is_morphing = True

                    Handler.kill_all()

                    time.sleep(5)
                    # save logs

                    Handler.move_logs(cnt)
                    cnt += 1

                    print("Ready to restart")
                    tokens = data.split()

                    num_machines = int(tokens[1])
                    master_ip = tokens[2]
                    master_port = tokens[3]
                    print(f"Change resources, num machines is {num_machines}, master_ip is {master_ip}, master_port is {master_port}")
                    Handler.start_remote(master_ip, master_port) # TODO: add resume from checkpoint here
                    is_morphing = False
                else:
                    print("morph change was already detected", is_morphing)
            except Exception as e:
                print("Caught exception while morphing:", e)
                is_morphing = False
            Handler.triggermorph.release()
            print("Lock released by morph:", is_morphing)

        else:
            print("Not supported message")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    pass

if __name__ == "__main__":
    server = ThreadedTCPServer((HOST, PORT), Handler)

    print("Started server with IP: ", my_ip, ", host is: ", HOST)

    with server:
        server.serve_forever()
