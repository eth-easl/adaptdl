import os
import argparse
from platform import node
import sys
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from torchvision import models, datasets, transforms
from torch.nn.parallel import DistributedDataParallel as DDP
import torch.nn.functional as F
import torch.nn as nn
from torch.multiprocessing import Pool, Process, set_start_method, Manager, Value, Lock
from datetime import timedelta
import random
import numpy as np
import time
import signal

import adaptdl
import adaptdl.torch as adl

from torch.optim.lr_scheduler import MultiStepLR

parser = argparse.ArgumentParser(description='PyTorch ImageNet Training')

parser.add_argument('--batch-size', default=-1, type=int, help='Global batch size (of training)')
parser.add_argument('--local_rank', default=-1, type=int, help='process rank in the local node')
parser.add_argument('--arch', default=None, type=str, help='model architecture')
parser.add_argument('--nclasses', default=-1, type=int, help='number of classes in the train dataset')
parser.add_argument('--train-dir', default=None, type=str, help='Training set directory')
parser.add_argument('--num-epochs', default=1, type=int, help='Number of epochs')
parser.add_argument('--num-dl', default=4, type=int, help='Number data loading workers')
parser.add_argument('--ch-freq', default=10, type=int, help='Checkpoint iteration interval')
parser.add_argument('--resume', default=False, action='store_true', help='Load from the latest checkpoint (if exists)')
parser.add_argument('--autoscale-bsz', dest='autoscale_bsz', default=False,
                    action='store_true', help='pollux - autoscale batchsize')


def train(args): # how to set batch size, chunk size?

    world_size = os.getenv("ADAPTDL_NUM_REPLICAS")
    rank = os.getenv("ADAPTDL_REPLICA_RANK")
    criterion = nn.CrossEntropyLoss()

    print("rank is: ", rank, ", world size is: ", world_size)

    adaptdl.torch.init_process_group("nccl" if torch.cuda.is_available() else "gloo") # TODO: check this

    print("Global batch size is: ", args.batch_size)

    print("Configure dataset")

    trainset = \
            datasets.ImageFolder(args.train_dir,
                                    transform=transforms.Compose([
                                        transforms.RandomResizedCrop(224),
                                        transforms.RandomHorizontalFlip(),
                                        transforms.ToTensor(),
                                        transforms.Normalize(mean=[0.4914, 0.4822, 0.4465],
                                            std=[0.2023, 0.1994, 0.2010])

                                        ]))


    # check sampling here
    trainloader = adl.AdaptiveDataLoader(trainset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_dl, drop_last=True)


    model = models.__dict__[args.arch](num_classes=args.nclasses)
    model = model.to(args.local_rank)

    optimizer = torch.optim.SGD(model.parameters(), lr=0.1,
                                momentum=0.9,
                                weight_decay=1e-4)
    model = adl.AdaptiveDataParallel(model, optimizer, None, None)

    for epoch in range(args.num_epochs):

        print("Start epoch: ", epoch)
        model.train()

        start = time.time()
        start_iter = time.time()

        i=0

        for inputs, targets in trainloader:

            optimizer.zero_grad()
            inputs, targets = inputs.to(args.local_rank), targets.to(args.local_rank)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            if args.local_rank==0:
                print(f"Iteration {i} took {time.time() - start_iter}", flush=True)
            start_iter = time.time()
            i += 1

        if args.local_rank==0:
            print(f"---- From worker with rank: {args.rank}, Timestamp is: {time.time()}, Epoch {epoch} took: {time.time()-start}", flush=True)


if __name__ == "__main__":

    args = parser.parse_args()

    def handler(signum,_):
        print("Got a signal - do nothing for now, just exit")
        exit()

    signal.signal(signal.SIGUSR1, handler)

    train(args)
