import os
import torch
from torch import nn, optim
from torch.optim import Optimizer
import numpy as np
import torch.nn.functional as F
import random


### IO
def check_dir(d):
    if not os.path.exists(d):
        print("Directory {} does not exist. Exit.".format(d))
        exit(1)

def check_files(files):
    for f in files:
        if f is not None and not os.path.exists(f):
            print("File {} does not exist. Exit.".format(f))
            exit(1)

def ensure_dir(d, verbose=True):
    if not os.path.exists(d):
        if verbose:
            print("Directory {} do not exist; creating...".format(d))
        os.makedirs(d)



def get_optimizer(name, parameters, lr, l2=0):
    if name == 'sgd':
        return torch.optim.SGD(parameters, lr=lr, weight_decay=l2)
    elif name == 'adagrad':
        # use my own adagrad to allow for init accumulator value
        return torch.optim.Adagrad(parameters, lr=lr, initial_accumulator_value=0.1, weight_decay=l2)
    elif name == 'adam':
        return torch.optim.Adam(parameters, weight_decay=l2) # use default lr
    elif name == 'adamax':
        return torch.optim.Adamax(parameters, weight_decay=l2) # use default lr
    elif name == 'adadelta':
        return torch.optim.Adadelta(parameters, lr=lr, weight_decay=l2)
    else:
        raise Exception("Unsupported optimizer: {}".format(name))

def change_lr(optimizer, new_lr):
    for param_group in optimizer.param_groups:
        param_group['lr'] = new_lr

def set_cuda(var, cuda):
    if cuda:
        return var.cuda()
    return var

def keep_partial_grad(grad, topk):
    """
    Keep only the topk rows of grads.
    """
    assert topk < grad.size(0)
    grad.data[topk:].zero_()
    return grad

# model.apply(initialize_weights)
def initialize_weights(model):
    if hasattr(model, 'weight') and model.weight.dim() > 1:
        nn.init.xavier_uniform_(model.weight.data)
    
def calc_dist_vec(longitudes1, latitudes1, longitudes2, latitudes2):
    """Calculate the distance (unit: km) between two places on earth, vectorised"""
    # convert degrees to radians
    lng1 = np.radians(longitudes1)
    lat1 = np.radians(latitudes1)
    lng2 = np.radians(longitudes2)
    lat2 = np.radians(latitudes2)
    radius = 6371.0088 # mean earth radius, en.wikipedia.org/wiki/Earth_radius#Mean_radius

    # The haversine formula, en.wikipedia.org/wiki/Great-circle_distance
    dlng = np.fabs(lng1 - lng2)
    dlat = np.fabs(lat1 - lat2)
    dist =  2 * radius * np.arcsin( np.sqrt(
                (np.sin(0.5*dlat))**2 + np.cos(lat1) * np.cos(lat2) * (np.sin(0.5*dlng))**2 ))
    return dist

# Define a function to generate a mask matrix, with filled positions corresponding to 0 and non-filled positions corresponding to 1
def sequence_mask(lengths, max_length):
    device = lengths.device
    batch_size = lengths.size(0)
    mask = torch.zeros(batch_size, max_length, dtype=torch.int64, device=device)
    for i in range(batch_size):
        L = lengths[i].item() 
        if L > 0: 
            mask[i, 0] = 1 
            mask[i, L - 1] = 1  
    return mask

def transformer_mask(target_sequence_length):
    mask = torch.ones(target_sequence_length[0], target_sequence_length[0])
    for i, length in enumerate(target_sequence_length):
        mask[length:, :length] = 0
        
    mask = mask.triu(diagonal=1)  
    return mask

def pad_time_batch(time_batch):
   
    max_sentence = max([len(sentence) for sentence in time_batch])  # 取最大长度
    return [sentence + [0] * (max_sentence - len(sentence)) for sentence in time_batch]

def pad_sentence_batch(sentence_batch, pad_int):
   
    max_sentence = max([len(sentence) for sentence in sentence_batch])  # 取最大长度
    return [sentence + [pad_int] * (max_sentence - len(sentence)) for sentence in sentence_batch]

def eos_sentence_batch(sentence_batch, eos_in):
    return [sentence + [eos_in] for sentence in sentence_batch]

def pad_dist_batch(dist_batch):
    
    max_sentence = max([len(sentence) for sentence in dist_batch])  # 取最大长度
    return [sentence + [sentence[-1]] * (max_sentence - len(sentence)) for sentence in dist_batch]

# for BTS module in Mamba, generate temporal delta
def get_delta(m):
    _, T= m.shape
    d_forw = torch.zeros_like(m).cuda()
    d_back = torch.zeros_like(m).cuda()
    m_flip = torch.flip(m, dims=[1]) # [B T]
    for t in range(1, T):
        d_forw[:,t] = 1 + torch.sub(1, m[:,t])*d_forw[:,t-1]
        d_back[:,t] = 1 + torch.sub(1, m_flip[:,t])*d_back[:,t-1]
    return [d_forw, d_back]

def random_choice_by_probability(probability_list):

    cumulative_probabilities = []
    cumulative_prob = 0
    for prob in probability_list:
        cumulative_prob += prob
        cumulative_probabilities.append(cumulative_prob)

    random_number = random.random()

    for i, cumulative_prob in enumerate(cumulative_probabilities):
        if random_number <= cumulative_prob:
            return i
        
def select_top_p_indices(probabilities, threshold=0.8):

    sorted_indices = np.argsort(probabilities)[::-1]  # re-order the probability
    cumulative_prob = 0.0
    selected_indices = []

    for idx in sorted_indices:
        cumulative_prob += probabilities[idx]
        selected_indices.append(idx)
        if cumulative_prob >= threshold:
            break

    return selected_indices[-1]

def ad_top_np_recommendation(batch_candidate, batch_similarity, confidence, threshold=0.8):

    # the top_np method to recommend trajectory
    top_candidates = batch_candidate[:, :, 0].cpu()  # [b,l]
    batch_similarity = batch_similarity.cpu()

    for batch in range(batch_candidate.shape[0]):
        for middle_index in range(batch_candidate.shape[1]):

            batch_similarity[batch, middle_index] = F.softmax(batch_similarity[batch, middle_index] *
                                                              confidence[middle_index], dim=0)

            top_p_indices = select_top_p_indices(batch_similarity[batch, middle_index].tolist(), threshold)
            batch_similarity[batch, middle_index, :(top_p_indices+1)] = \
                F.softmax(batch_similarity[batch, middle_index, :(top_p_indices+1)], dim=0)

            batch_similarity[batch, middle_index, (top_p_indices+1):] = torch.tensor(0)

            batch_probability_list = batch_similarity[batch, middle_index].tolist()
            nonzero_probability_list = [x for x in batch_probability_list if x != 0]

            new_top_p_index = random_choice_by_probability(nonzero_probability_list)
            top_candidates[batch, middle_index] = batch_candidate[batch, middle_index, new_top_p_index]

    return top_candidates

# ==================== transfer matrix ==============================

# generate transfer matrix
def poi_adjacent(traj_list, poi_size):
    #traj_list = dataset['venue_ID'].tolist()

    AM = np.zeros((poi_size, poi_size), dtype=int)
    for traj in traj_list:
        for index in range(len(traj)-1):
            curr_poi = traj[index]
            next_poi = traj[index + 1]
            AM[curr_poi][next_poi] += 1  # [v,v] pi -> pi+1

    row_sums = AM.sum(axis=1)
    AM = AM / row_sums[:, np.newaxis]
    AM[np.isnan(AM)] = 0

    return AM.astype(np.float32)

def poi_position(traj_list, poi_size, max_length):
    #traj_list = dataset['venue_ID'].tolist()

    PM = np.zeros((poi_size, max_length))
    for traj in traj_list:
        for index in range(len(traj)):
            PM[traj[index]][index] += 1  # [v,l_max]

    row_sums = PM.sum(axis=1)
    PM = PM / row_sums[:, np.newaxis]
    PM[np.isnan(PM)] = 0

    zero_counts = np.count_nonzero(PM == 0, axis=0)
    total_points = PM.shape[0]
    confidence = zero_counts / total_points
    confidence = [min(0.5, val) for val in confidence]
    # print(PM)
    return PM.astype(np.float32), confidence

# Advanced-Greedy:
def find_duplicates_and_indices(input_tensor):

    duplicates_dict = {}
    input_tensor = input_tensor.tolist()
    for index, value in enumerate(input_tensor):
        if input_tensor.count(value) > 1:
            if value not in duplicates_dict:
                duplicates_dict[value] = [index, ]
            else:
                duplicates_dict[value] += [index, ]

    return duplicates_dict

def advanced_greedy_recommendation(batch_candidate, batch_similarity):

    top_candidates = batch_candidate[:, :, 0].cpu()  # [b,l]
    batch_similarity = batch_similarity.cpu()

    for batch in range(batch_candidate.shape[0]):
        if len(top_candidates[batch]) == len(np.unique(top_candidates[batch])):
            pass
        else:

            position_top_k = [0] * top_candidates.shape[1]

            while len(top_candidates[batch]) != len(np.unique(top_candidates[batch])):

                repetition_dict = find_duplicates_and_indices(top_candidates[batch])

                for key in repetition_dict.keys():
                    confidence_list = []
                    for item in repetition_dict[key]:
                        confidence = batch_similarity[batch, item, position_top_k[item]].item()
                        confidence_list.append(confidence)

                    max_item = repetition_dict[key][confidence_list.index(max(confidence_list))]
                    left_item_list = list(filter(lambda x: x != max_item, repetition_dict[key]))
                    for left_item in left_item_list:

                        position_top_k[left_item] += 1
                        top_candidates[batch, left_item] = batch_candidate[batch, left_item, position_top_k[left_item]]

    return top_candidates

# Top-N and Top-NP method:
def random_choice_by_probability(probability_list):

    cumulative_probabilities = []
    cumulative_prob = 0
    for prob in probability_list:
        cumulative_prob += prob
        cumulative_probabilities.append(cumulative_prob)

    random_number = random.random()

    for i, cumulative_prob in enumerate(cumulative_probabilities):
        if random_number <= cumulative_prob:
            return i
    
    return len(probability_list) - 1


def select_top_p_indices(probabilities, threshold=0.8):

    sorted_indices = np.argsort(probabilities)[::-1]  # re-order the probability
    cumulative_prob = 0.0
    selected_indices = []

    for idx in sorted_indices:
        cumulative_prob += probabilities[idx]
        selected_indices.append(idx)
        if cumulative_prob >= threshold:
            break

    return selected_indices[-1]

def top_n_recommendation(batch_candidate, batch_similarity, confidence=1):

    # the top_n method to recommend trajectory
    top_candidates = batch_candidate[:, :, 0].cpu()  # [b,l]
    batch_similarity = batch_similarity.cpu()

    for batch in range(batch_candidate.shape[0]):
        for middle_index in range(batch_candidate.shape[1]):

            # print(batch_similarity[batch, middle_index])
            batch_similarity[batch, middle_index] = F.softmax(batch_similarity[batch, middle_index] * confidence, dim=0)
            # print(batch_similarity[batch, middle_index])
            #new_top_k_index = random_choice_by_probability(batch_similarity[batch, middle_index].tolist())
            new_top_k_index = random_choice_by_probability(batch_similarity[batch, middle_index].tolist())
            top_candidates[batch, middle_index] = batch_candidate[batch, middle_index, new_top_k_index]

    return top_candidates  # [b,l]


def top_np_recommendation(batch_candidate, batch_similarity, confidence=1, threshold=0.8):

    # the top_np method to recommend trajectory
    top_candidates = batch_candidate[:, :, 0].cpu()  # [b,l]
    batch_similarity = batch_similarity.cpu()

    for batch in range(batch_candidate.shape[0]):
        for middle_index in range(batch_candidate.shape[1]):

            batch_similarity[batch, middle_index] = F.softmax(batch_similarity[batch, middle_index] * confidence, dim=0)

            top_p_indices = select_top_p_indices(batch_similarity[batch, middle_index].tolist(), threshold)
            batch_similarity[batch, middle_index, :(top_p_indices+1)] = \
                F.softmax(batch_similarity[batch, middle_index, :(top_p_indices+1)] * confidence, dim=0)

            batch_similarity[batch, middle_index, (top_p_indices+1):] = torch.tensor(0)

            batch_probability_list = batch_similarity[batch, middle_index].tolist()
            nonzero_probability_list = [x for x in batch_probability_list if x != 0]

            new_top_p_index = random_choice_by_probability(nonzero_probability_list)
            top_candidates[batch, middle_index] = batch_candidate[batch, middle_index, new_top_p_index]

    return top_candidates  # [b,l]

def ad_top_np_recommendation(batch_candidate, batch_similarity, confidence, threshold=0.8):

    # the top_np method to recommend trajectory
    top_candidates = batch_candidate[:, :, 0].cpu()  # [b,l]
    batch_similarity = batch_similarity.cpu()

    for batch in range(batch_candidate.shape[0]):
        for middle_index in range(batch_candidate.shape[1]):

            batch_similarity[batch, middle_index] = F.softmax(batch_similarity[batch, middle_index] *
                                                              confidence[middle_index], dim=0)

            top_p_indices = select_top_p_indices(batch_similarity[batch, middle_index].tolist(), threshold)
            batch_similarity[batch, middle_index, :(top_p_indices+1)] = \
                F.softmax(batch_similarity[batch, middle_index, :(top_p_indices+1)], dim=0)

            batch_similarity[batch, middle_index, (top_p_indices+1):] = torch.tensor(0)

            batch_probability_list = batch_similarity[batch, middle_index].tolist()
            nonzero_probability_list = [x for x in batch_probability_list if x != 0]

            new_top_p_index = random_choice_by_probability(nonzero_probability_list)
            top_candidates[batch, middle_index] = batch_candidate[batch, middle_index, new_top_p_index]

    return top_candidates