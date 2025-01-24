from collections import defaultdict
import logging
import numpy as np
import os
import wandb
import socket
import torch as th

def create_dir(path):
    try:
        os.makedirs(path)
        print("目录创建成功！")
    except FileExistsError:
        print("目录已存在！")

class Logger:
    def __init__(self, console_logger):
        self.console_logger = console_logger

        self.use_tb = False
        self.use_sacred = False
        self.use_hdf = False
        self.use_wandb = False

        self.stats = defaultdict(lambda: [])

    def setup_tb(self, directory_name):
        # Import here so it doesn't have to be installed if you don't use it
        from tensorboard_logger import configure, log_value
        configure(directory_name)
        self.tb_logger = log_value
        self.use_tb = True

    def setup_sacred(self, sacred_run_dict):
        self.sacred_info = sacred_run_dict.info
        self.use_sacred = True

    def setup_wandb(self, args, directory_name, unique_token):
        create_dir(directory_name)


        name = "seed" + str(args.seed) + unique_token

        wandb.init(config=args,
                               project="IRMARL",
                               entity=args.user_name,
                               notes=socket.gethostname(),
                               name=name,
                               group=args.env_args['scenario_name'],
                               dir=directory_name,
                               job_type="training",
                               reinit=True)
        self.use_wandb = True


    def log_stat(self, key, value, t, to_sacred=True):
        self.stats[key].append((t, value))

        if self.use_tb:
            self.tb_logger(key, value, t)

        if self.use_sacred and to_sacred:
            if key in self.sacred_info:
                self.sacred_info["{}_T".format(key)].append(t)
                self.sacred_info[key].append(value)
            else:
                self.sacred_info["{}_T".format(key)] = [t]
                self.sacred_info[key] = [value]

        if self.use_wandb:
            wandb.log({key: value}, step=t)

    def print_recent_stats(self):
        log_str = "Recent Stats | t_env: {:>10} | Episode: {:>8}\n".format(*self.stats["episode"][-1])
        i = 0
        for (k, v) in sorted(self.stats.items()):
            if k == "episode":
                continue
            i += 1
            window = 5 if k != "epsilon" else 1
            item = "{:.4f}".format(th.mean(th.tensor([float(x[1]) for x in self.stats[k][-window:]])))
            log_str += "{:<25}{:>8}".format(k + ":", item)
            log_str += "\n" if i % 4 == 0 else "\t"
        self.console_logger.info(log_str)
        # Reset stats to avoid accumulating logs in memory
        self.stats = defaultdict(lambda: [])


# set up a custom logger
def get_logger():
    logger = logging.getLogger()
    logger.handlers = []
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s %(asctime)s] %(name)s %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel('DEBUG')

    return logger

