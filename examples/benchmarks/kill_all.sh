#!/bin/bash

kill -9 $(ps aux | grep train_ddp_image.py | grep -v grep | awk '{print $2}')