# coding: utf-8

import random
import logging
from numpy.lib.function_base import average

import torch
import numpy as np
import os

from scipy.stats import pearsonr, spearmanr
from seqeval import metrics as seqeval_metrics
from sklearn import metrics as sklearn_metrics

from transformers import (
    BertConfig,
    ElectraConfig,
    BertTokenizer,
    ElectraTokenizer,
    BertForSequenceClassification,
    ElectraForSequenceClassification,
)

CONFIG_CLASSES = {
    "dbert": BertConfig,
    "delec": ElectraConfig,
}

TOKENIZER_CLASSES = {
    "dbert": BertTokenizer,
    "delec": ElectraTokenizer,
}

MODEL_FOR_SEQUENCE_CLASSIFICATION = {
    "dbert": BertForSequenceClassification,
    "delec": ElectraForSequenceClassification,
}


def init_logger():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=logging.INFO,
    )


def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if not args.no_cuda and torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)


def simple_accuracy(labels, preds):
    return (labels == preds).mean()


def acc_score(labels, preds):
    return {
        "acc": simple_accuracy(labels, preds),
    }


def pearson_and_spearman(labels, preds):
    pearson_corr = pearsonr(preds, labels)[0]
    spearman_corr = spearmanr(preds, labels)[0]
    return {
        "pearson": pearson_corr,
        "spearmanr": spearman_corr,
        "corr": (pearson_corr + spearman_corr) / 2,
    }


def f1_pre_rec(labels, preds, is_ner=True, average="micro"):
    if is_ner:
        return {
            "precision": seqeval_metrics.precision_score(labels, preds, suffix=True),
            "recall": seqeval_metrics.recall_score(labels, preds, suffix=True),
            "f1": seqeval_metrics.f1_score(labels, preds, suffix=True),
        }
    else:
        return {
            "precision": sklearn_metrics.precision_score(labels, preds, average=average),
            "recall": sklearn_metrics.recall_score(labels, preds, average=average),
            "f1": sklearn_metrics.f1_score(labels, preds, average=average),
        }


def confusion_matrix(labels, preds):
    cm = sklearn_metrics.confusion_matrix(labels, preds)
    return {'tp': cm[1, 1], 'fn': cm[1, 0], 'fp': cm[0, 1], 'tn': cm[0, 0]}


def f1(c):
    try:
        p = c[1,1]/(c[1,1]+c[0,1])
        r = c[1,1]/(c[1,1]+c[1,0])
        return 2*p*r/(p+r), p, r
    except:
        return 0, 0, 0


def acc(c):
    try:
        r = c[1,1]+c[0,0]
        return r/(r+c[1,0]+c[0,1])
    except:
        return 0


def multi_acc(labels, preds):
    cm = sklearn_metrics.multilabel_confusion_matrix(labels, preds)
    out = []
    for c in cm:
        cmx = {'tp': c[1, 1], 'fn': c[1, 0], 'fp': c[0, 1], 'tn': c[0, 0]}
        f, p, r = f1(c)
        a = acc(c)
        out.append({'acc':a, 'f1':f, 'precision':p, 'recall':r, 'cm': cmx})
    return out


def show_ner_report(labels, preds):
    return seqeval_metrics.classification_report(labels, preds, suffix=True)


def compute_metrics(task_name, labels, preds):
    if task_name == "class":
        f, p, r = f1(sklearn_metrics.confusion_matrix(labels, preds))
        return {'precision': p, 'recall': r, 'f1': f}
    else:
        return f1_pre_rec(labels, preds, is_ner=False, average="weighted")


def rename_result_file(file):
    if os.path.isfile(file):
        for i in range(1, 10):
            name = "{}{}{}".format(file[:-4], i, file[-4:])
            if not os.path.isfile(name):
                return name
    return file
