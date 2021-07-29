import os
import torch
import shutil
import pandas as pd
from .optimizers import *
# from config import configs
from torch import optim as optim_t
from tqdm import tqdm
from glob import glob
from itertools import chain
import time

time_local = time.localtime()  # clw modify

#### from ranger import Ranger  # this is from ranger.py

def get_optimizer(model,configs):
    if configs.optim == "adam":
        return optim_t.Adam(model.parameters(),
                            configs.lr,
                            betas=(configs.beta1, configs.beta2),
                            weight_decay=configs.wd)
    elif configs.optim == "radam":
        return RAdam(model.parameters(),
                    configs.lr,
                    betas=(configs.beta1,configs.beta2),
                    weight_decay=configs.wd)
    elif configs.optim == "ranger":
        return Ranger(model.parameters(), lr=1e-2)
    elif configs.optim == "over9000":
        return Over9000(model.parameters(),
                        lr = configs.lr,
                        betas=(configs.beta1,configs.beta2),
                        weight_decay=configs.wd)
    elif configs.optim == "ralamb":
        return Ralamb(model.parameters(),
                      lr = configs.lr,
                      betas=(configs.beta1,configs.beta2),
                      weight_decay=configs.wd)
    elif configs.optim == "sgd":
        return optim_t.SGD(model.parameters(),
                        lr = configs.lr,
                        momentum=configs.mom,
                        weight_decay=configs.wd,
                        nesterov=True)
    else:
        print("%s  optimizer will be add later"%configs.optim)

def save_checkpoint(state, is_best,configs):
    filename = configs.checkpoints + os.sep + configs.model_name + '_' + time.strftime("%Y_%m_%d_%H_%M_%S", time_local) + "-checkpoint.pth.tar" # clw add time
    torch.save(state, filename)
    if is_best:
        message = filename.replace("-checkpoint.pth.tar","-best_model.pth.tar")
        shutil.copyfile(filename, message)

def save_checkpoint_with_fold(state, is_best,configs):
    fold = state['fold']
    filename = configs.checkpoints + os.sep + configs.model_name + '_' + time.strftime("%Y_%m_%d_%H_%M_%S", time_local) + "_fold" + str(fold) + "-checkpoint.pth.tar" # clw add time
    torch.save(state, filename)
    if is_best:
        message = filename.replace("-checkpoint.pth.tar","-best_model.pth.tar")
        shutil.copyfile(filename, message)

def get_lr(optimizer):
    for param_group in optimizer.param_groups:
        return param_group['lr']

class AverageMeter(object):
    """Computes and stores the average and current value
       Imported from https://github.com/pytorch/examples/blob/master/imagenet/main.py#L247-L262
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

def accuracy(output, target, topk=(1,)):
    """
    Computes the precision@k for the specified values of k
    output: result of model(input)
    target: gt, not one-hot
    """

    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    # print("pred: ",pred)
    pred = pred.t()
    # print("pred: ",pred) 
    # correct = pred.eq(target.view(1, -1).expand_as(pred))

    _, t = target.topk(1, 1, True, True) #(batch_size,1) -> (1,batch_size)
    t = t.t()

    correct = pred.eq(t.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res

def accuracy_onehot(output, target, topk=(1,)):
    """
    Computes the precision@k for the specified values of k
    output: result of model(input)
    target: gt, not one-hot
    """

    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()

    ### clw modify: for mixup one-hot targets, choose the max as label, but is not accuracy enough    TODO
    target_max_value, target_max_index = target.max(1)
    target = target_max_index
    #################

    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res

def get_files(root,mode):
    if mode == "test":
        files = []
        for img in os.listdir(root):
            files.append(root + img)
        files = pd.DataFrame({"filename":files})
        return files
    else:
        all_data_path, labels = [], []
        image_folders = list(map(lambda x: root + x, os.listdir(root)))
        all_images = list(chain.from_iterable(list(map(lambda x: glob(x + "/*"), image_folders))))
        if mode == "val":
            print("loading val dataset")
        elif mode == "train":
            print("loading train dataset")
        else:
            raise Exception("Only have mode train/val/test, please check !!!")
        label_dict={}
        for file in tqdm(all_images):
            all_data_path.append(file)
            name=file.split(os.sep)[-2] #['', 'data', 'nextcloud', 'dbc2017', 'files', 'images', 'train', 'Diego_Rivera', 'Diego_Rivera_21.jpg']
            # print(name)
            if name not in label_dict:
                label_dict[name]=len(label_dict)
            labels.append(label_dict[name])
            # labels.append(int(file.split(os.sep)[-2]))
        print(label_dict)
        all_files = pd.DataFrame({"filename": all_data_path, "label": labels})
        return all_files

def adjust_learning_rate(optimizer, epoch):
    """Sets the learning rate to the initial LR decayed by 10 every 30 epochs"""
    lrs = [1e-4, 3e-5, 1e-5]  # bs 64 best
    if epoch<=2:  # if epoch<=10:
        lr = lrs[0]
    elif epoch>2 and epoch<=3:  #  elif epoch>10 and epoch<=16:
        lr = lrs[1]
    elif epoch>3 and epoch<=4:  # elif epoch>16 and epoch<=22:
        lr = lrs[2]
    # elif epoch>4 and epoch<=5:  # elif epoch>16 and epoch<=22:
    #     lr = lrs[3]
    # elif epoch>5 and epoch<=6:  # elif epoch>16 and epoch<=22:
    #     lr = lrs[4]
    else:
        lr = lrs[-1]
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr