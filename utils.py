import json
import math

from tqdm import tqdm
from collections import Counter

import nltk
from nltk.util import ngrams
from nltk import word_tokenize, sent_tokenize

from datasets import Dataset
import torch.nn as nn


def label_smoothed_nll_loss(lprobs, target, epsilon, ignore_index=-100):
    """
    loss with label smoothing
    from fairseq, edit by Bin
    """

    lprobs = lprobs[~target.eq(-100)]
    target = target[~target.eq(-100)]

    if target.dim() == lprobs.dim() - 1:
        target = target.unsqueeze(-1)

    nll_loss = -lprobs.gather(dim=-1, index=target)
    smooth_loss = -lprobs.sum(dim=-1, keepdim=True)

    # mean()? Scared to break other math.
    # bin: change from sum to mean
    nll_loss = nll_loss.mean()
    smooth_loss = smooth_loss.mean()
    eps_i = epsilon / lprobs.size(-1)
    loss = (1.0 - epsilon) * nll_loss + eps_i * smooth_loss
    return loss, nll_loss


def postprocess_text(preds, labels):
    """
    use for decoding
    """
    preds = [pred.strip() for pred in preds]
    labels = [label.strip() for label in labels]

    # rougeLSum expects newline after each sentence
    preds = ["\n".join(nltk.sent_tokenize(pred)) for pred in preds]
    labels = ["\n".join(nltk.sent_tokenize(label)) for label in labels]

    return preds, labels


def len_adjust(args, split_dict, split_type=None):
    """add length to the input"""

    id_list = split_dict["id"]
    dialogue_list = split_dict["dialogue"]
    summary_list = split_dict["summary"]
    topic_list = split_dict["topic"]
    if args.contrastive == "synonym" or args.contrastive == "combine":
        synonym_list = split_dict["synonym_topic"]
    if args.contrastive == "random" or args.contrastive == "combine":
        random_list = split_dict["random_topic"]
    if args.tagging != "no":
        if args.contrastive == "synonym" or args.contrastive == "combine":
            dialogue_synonym_list = split_dict["synonym_dialogue"]
        if args.contrastive == "random" or args.contrastive == "combine":
            dialogue_random_list = split_dict["random_dialogue"]

    if args.len_input == "no":
        new_dialogue_list = dialogue_list

    elif args.len_input == "topic":
        new_dialogue_list = []
        for dialogue, topic in zip(dialogue_list, topic_list):
            new_dialogue = "Topic of Summary: {}. Dialogue: ".format(topic) + dialogue
            if args.tagging == "word":
                new_dialogue = (
                    "Topic of Summary: <t>{}</t>. Dialogue: ".format(
                        topic
                    )
                    + dialogue
                )
            elif args.tagging == "prompt":
                new_dialogue = (
                    "<t>Topic of Summary: {}</t>. Dialogue: ".format(
                        topic
                    )
                    + dialogue
                )
            else:
                new_dialogue = (
                    "Topic of Summary: {}. Dialogue: ".format(
                        topic
                    )
                    + dialogue
                )
            new_dialogue_list.append(new_dialogue)

    elif args.len_input == "length":
        new_dialogue_list = []
        for dialogue, summary in zip(dialogue_list, summary_list):
            sum_len = len(summary.split(" "))
            new_dialogue = (
                "Length of Summary: {}. Dialogue: ".format(sum_len) + dialogue
            )
            new_dialogue_list.append(new_dialogue)

    elif args.len_input == "topic-length":
        new_dialogue_list = []
        for dialogue, topic, summary in zip(dialogue_list, topic_list, summary_list):
            sum_len = len(summary.split(" "))
            if args.tagging == "word":
                new_dialogue = (
                    "Topic of Summary: <t>{}</t>. Length of Summary: {}. Dialogue: ".format(
                        topic, sum_len
                    )
                    + dialogue
                )
            elif args.tagging == "prompt":
                new_dialogue = (
                    "<t>Topic of Summary: {}</t>. Length of Summary: {}. Dialogue: ".format(
                        topic, sum_len
                    )
                    + dialogue
                )
            else:
                new_dialogue = (
                    "Topic of Summary: {}. Length of Summary: {}. Dialogue: ".format(
                        topic, sum_len
                    )
                    + dialogue
                )
            new_dialogue_list.append(new_dialogue)

    if args.contrastive == "synonym" or args.contrastive == "combine":
        if args.tagging != "no":
            dialogue_list = dialogue_synonym_list
        new_synonym_list = []
        for dialogue, synonym, summary in zip(
            dialogue_list, synonym_list, summary_list
        ):
            sum_len = len(summary.split(" "))
            if args.tagging == "word":
                new_dialogue = (
                    "Topic of Summary: <t>{}</t>. Length of Summary: {}. Dialogue: ".format(
                        synonym, sum_len
                    )
                    + dialogue
                )
            elif args.tagging == "prompt":
                new_dialogue = (
                    "<t>Topic of Summary: {}</t>. Length of Summary: {}. Dialogue: ".format(
                        synonym, sum_len
                    )
                    + dialogue
                )
            else:
                new_dialogue = (
                    "Topic of Summary: {}. Length of Summary: {}. Dialogue: ".format(
                        synonym, sum_len
                    )
                    + dialogue
                )
            new_synonym_list.append(new_dialogue)

    if args.contrastive == "random" or args.contrastive == "combine":
        if args.tagging != "no":
            dialogue_list = dialogue_random_list
        new_random_list = []
        for dialogue, random, summary in zip(dialogue_list, random_list, summary_list):
            sum_len = len(summary.split(" "))
            if args.tagging == "word":
                new_dialogue = (
                    "Topic of Summary: <t>{}</t>. Length of Summary: {}. Dialogue: ".format(
                        random, sum_len
                    )
                    + dialogue
                )
            elif args.tagging == "prompt":
                new_dialogue = (
                    "<t>Topic of Summary: {}</t>. Length of Summary: {}. Dialogue: ".format(
                        random, sum_len
                    )
                    + dialogue
                )
            else:
                new_dialogue = (
                    "Topic of Summary: {}. Length of Summary: {}. Dialogue: ".format(
                        random, sum_len
                    )
                    + dialogue
                )
            new_random_list.append(new_dialogue)

    # elif args.len_input == 'surface':
    #     new_dialogue_list = []
    #     for dialogue in dialogue_list:
    #         utt_diag  = dialogue.split('\n')
    #         num_utt   = len(utt_diag)
    #         word_diag = [utt.split(' ') for utt in utt_diag]
    #         word_diag = [word for utt in word_diag for word in utt]
    #         num_word  = len(word_diag)

    #         new_dialogue = 'Number of utterrance: {}. Length of Dialogue: {}. Dialogue: {}'.format(num_utt, num_word, dialogue)
    #         new_dialogue_list.append(new_dialogue)

    # elif args.len_input == 'real' or split_type != 'test':
    #     new_dialogue_list = []
    #     for dialogue, summary in zip(dialogue_list, summary_list):
    #         sum_len = len(summary.split(' '))
    #         new_dialogue = 'Length of Summary: {}. Dialogue: '.format(sum_len) + dialogue
    #         new_dialogue_list.append(new_dialogue)

    # elif args.len_input == 'predict':
    #     if split_type == 'test':
    #         new_dialogue_list = []
    #         if 'dialogsum' in args.train_file:
    #             with open('./data/dialogsum/predicted_len.txt', 'r') as f:
    #                 lines = f.readlines()
    #         elif 'samsum' in args.train_file:
    #             with open('./data/samsum/predicted_len.txt', 'r') as f:
    #                 lines = f.readlines()

    #         for line, dialogue in zip(lines, dialogue_list):
    #             index, length = line.strip().split('\t')
    #             length = int(length)
    #             new_dialogue = 'Length of Summary: {}. Dialogue: '.format(length) + dialogue
    #             new_dialogue_list.append(new_dialogue)

    if args.len_output == "no" or split_type == "val" or split_type == "test":
        new_summary_list = summary_list

    # elif args.len_output == 'real':
    #     new_summary_list = []
    #     for summary in summary_list:
    #         sum_len = len(summary.split(' '))
    #         new_summary = 'Length of Summary: {}. Summary: '.format(sum_len) + summary
    #         new_summary_list.append(new_summary)

    split_dict = {
        "id": id_list,
        "dialogue": new_dialogue_list,
        "summary": new_summary_list,
    }

    if args.contrastive == "synonym" or args.contrastive == "combine":
        split_dict["synonym_dialogue"] = new_synonym_list
    if args.contrastive == "random" or args.contrastive == "combine":
        split_dict["random_dialogue"] = new_random_list

    split_dict = Dataset.from_dict(split_dict)

    return split_dict


def cosine_embedding_loss(pos, neg, contrastive, margin=0.5):
    cs_loss = nn.CosineEmbeddingLoss(margin)
    loss_cosine_embedding = cs_loss(pos, neg, contrastive)
    return loss_cosine_embedding
