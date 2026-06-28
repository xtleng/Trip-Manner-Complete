import torch
import argparse
import numpy as np
import torch.nn as nn
import pickle
import json
import time
from torch.nn import functional as F
from config import Config, Logger
from torch.utils.tensorboard import SummaryWriter
from torch.optim.lr_scheduler import LambdaLR
from data_process.preprocess import processOriData
from data_process.dataloader import create_dataloaders
from model.AE_model import *
from model.embeddings import *
from model.RouteGenerator import *
from model.test_BiMamba import *
from model.trendPre_model import *
from model.strategy_model import *
from utils_new.metric import calc_F1, calc_pairsF1, count_repetition_percentage
from utils_new.util import *


parser = argparse.ArgumentParser()
device = torch.device("cuda:2" if torch.cuda.is_available() else "cpu")

# dataset parameter
parser.add_argument('--city_name', type=str, default='Toro')
parser.add_argument('--batch_size', type=int, default=8)#8
parser.add_argument('--divide_index', type=int, default=2, help='this parameter will influence the way of how to devide training dataset and test dataset')

# model parameter
parser.add_argument('--d_intermediate', type=int, default=256, help='the middle layer dimmension in encoder,decoder and generator')#512，256
parser.add_argument('--d_model', type=int, default=128)#256，64
parser.add_argument('--dynamic_training', type=bool, default=False, help='if there is pre-trained weights in embedding model')
parser.add_argument('--n_layer', type=int, default=2)#1
parser.add_argument('--ssm_layer', type=str, default='Mamba1')
parser.add_argument('--dropout', type=float, default= 0.399)#0.399,0.246
parser.add_argument('--num_heads', type=int, default=8)
parser.add_argument('--norm_epsilon', type=float, default=1e-6)
parser.add_argument('--rms_norm', type=bool, default=False)
parser.add_argument('--residual_in_fp32', type=bool, default=True)
parser.add_argument('--fused_add_norm', type=bool, default=False)
#BiMamba parameter
parser.add_argument('--conv_dim', type=int, default=4)#4
parser.add_argument('--expand', type=int, default=3)#3
parser.add_argument('--tem_depth', type=int, default=5)#5,4
parser.add_argument('--p_dropout', type=float, default=0.4)#0.3,0.1
#trendPredictor parameter
parser.add_argument('--n_poiCat', type=int, default=8)#Osak:5,Edin:7,Glas:8,Melb:10,Toro:7
parser.add_argument('--n_traj_len', type=int, default=9)#Osak:7,Edin:14,Glas:9,Melb:21,Toro:14
parser.add_argument('--d_trend_embed', type=int, default=128)#16
parser.add_argument('--d_trend_vec', type=int, default=256)#512,128

# Loss function and Optimizer parameter
parser.add_argument('--lr_AE', type=float, default=0.001)#0.029
parser.add_argument('--optimizer', choices=['sgd', 'adam', 'adamax'], default='adam', help='Optimizer: sgd, adagrad, adam or adamax.')
parser.add_argument('--lr_Gen', type=float, default=0.01)
parser.add_argument('--lr_Enc', type=float, default=0.01)
parser.add_argument('--lr_RG', type=float, default=0.0020)#0.0023

# train parameter
parser.add_argument('--epochs', type=int, default=20)
parser.add_argument('--stu_epochs', type=int, default=50)
parser.add_argument('--KD_temp', type=int, default=10)#14
parser.add_argument('--KD_alpha', type=float, default= 0.375)#0.375
parser.add_argument('--Multi_alpha', type=float, default= 0.1) #0.2                                           
parser.add_argument('--save_dir', type=str, default='./saved_models')
parser.add_argument('--save_epochs', type=int, default=5, help='Save model checkpoints every k epochs.')
parser.add_argument('--early_stop', type=bool, default=True)
parser.add_argument('--patience', type=int, default=10)
parser.add_argument('--resume', type=bool, default=False)
parser.add_argument('--resume_path', type=str, default='./saved_models/model_best.pt')
parser.add_argument('--log_step', type=int, default=20)

#ARTrip Strategy
parser.add_argument('--Guiding', default=False, help='ablation: using guiding')
parser.add_argument('--decoding_type', type=str, default='Greedy',
                        help='post-hoc decoding methods to fix the repetition problem. Candidate: Greedy, '
                             'Advanced-Greedy, Top-N, Top-NP, Adapting')
parser.add_argument('--confidence', type=float, default=0.5, help='the re-scale degree')

# other
parser.add_argument('--cuda', type=bool, default=torch.cuda.is_available())
parser.add_argument('--config_file', type=str, default='./config_KD_BiMamba.json')
parser.add_argument('--seed', type=int, default=1234)

args = parser.parse_args()
logger = Logger()

cfg = Config(logger=logger, args=args)
cfg.print_config()
cfg.save_config(cfg.config['config_file'])
torch.manual_seed(cfg.config['seed'])
torch.cuda.manual_seed(cfg.config['seed'])
torch.backends.cudnn.enabled = False
np.random.seed(cfg.config['seed'])

#load data
train_data, test_data = processOriData(cfg.config['city_name'], cfg.config['divide_index'], cfg.config['batch_size'])

# Load vocab_to_int from the file
with open('./dataset/vocab/vocab_to_int_'+cfg.config['city_name']+'.pkl', 'rb') as f:
    vocab_to_int = pickle.load(f)
vocab_size = len(vocab_to_int)
# Load poi_id_location from the file(location is string fomula)
poi_id_latlon_file = f"./dataset/data/{cfg.config['city_name']}_poi_id_latlon.json"
with open(poi_id_latlon_file, 'r', encoding='utf-8') as f:
    poi_id_latlon = json.load(f)
# Load max distance between POI in trajectorys(distance is string fomula)
max_dis_file = f"./dataset/data/{cfg.config['city_name']}_max_distance.json"
with open(max_dis_file, 'r', encoding='utf-8') as f:
    max_distance_data = json.load(f)
    max_distance = max_distance_data["max_distance"]

# model
ssm_cfg = {"layer": cfg.config['ssm_layer']}
attn_layer_idx = []
attn_cfg = {"num_heads": cfg.config['num_heads'], "dropout": cfg.config['dropout']}
initializer_cfg=None
AE = BiMambaAEModel(max_distance, poi_id_latlon, cfg.config['d_model'], cfg.config['n_layer'], cfg.config['d_intermediate'], vocab_size, cfg.config['expand'], cfg.config['conv_dim'], cfg.config['tem_depth'], cfg.config['p_dropout'], ssm_cfg, attn_layer_idx, attn_cfg, cfg.config['norm_epsilon'], cfg.config['rms_norm'], initializer_cfg, cfg.config['fused_add_norm'], cfg.config['residual_in_fp32'], device)
enc = AE.encoder
generator = BiMamba(d_model=cfg.config['d_model'], d_intermediate=cfg.config['d_intermediate'], vocab_size=vocab_size, expand=cfg.config['expand'], conv_dim=cfg.config['conv_dim'], tem_depth=cfg.config['tem_depth'], p_dropout=cfg.config['p_dropout'], d_trend=cfg.config['d_trend_vec'])
trendEncoder = TrajFeatureEnc(n_startPOI_ID=vocab_size, n_startPOI_Cat=cfg.config['n_poiCat'], n_endPOI_ID=vocab_size, n_endPOI_Cat=cfg.config['n_poiCat'], n_traj_len=cfg.config['n_traj_len'], embedding_dim=cfg.config['d_trend_embed'], hidden_dim=cfg.config['d_trend_vec'])
trendPredict = TrendPredict(in_dim=cfg.config['d_trend_vec'], out_dim=4)

routeGenerator = RG_BiMamba_AR(vocab_size, cfg.config['d_model'], max_distance, poi_id_latlon, generator, AE.decoder, trendEncoder, trendPredict, cfg.config['Guiding'], cfg.config['decoding_type'])

if torch.cuda.is_available():
    AE = AE.to(device)
    enc = enc.to(device)
    generator = generator.to(device)
    routeGenerator = routeGenerator.to(device)

# loss and optimizer
loss_func_AE = nn.CrossEntropyLoss()
hard_loss = nn.CrossEntropyLoss()
soft_loss = nn.MSELoss()
loss_trendPre = nn.CrossEntropyLoss() 

opt_AE = torch.optim.Adam(AE.parameters(), lr=cfg.config['lr_AE'])
opt_Gen = torch.optim.RMSprop(generator.parameters(), lr=cfg.config['lr_Gen'])
opt_enc = torch.optim.Adam(enc.parameters(), lr=cfg.config['lr_Enc'])
optimizer_modelS = torch.optim.Adam(routeGenerator.parameters(), lr = cfg.config['lr_RG'])


# use tensorboard
writer = SummaryWriter(log_dir='logs/experiment2')

# train
def train(index):
    torch.cuda.empty_cache()
    train_data, test_data = processOriData(cfg.config['city_name'], index, cfg.config['batch_size'])
    train_loader, test_loader = create_dataloaders(train_data, test_data, cfg.config['batch_size'])

    train_AE_F1 = []
    train_AE_pairsF1 = []
    test_AE_F1 = []
    test_AE_pairsF1 = []
    test_gene_F1 = []
    test_gene_pairsF1 = []
    
    train_start_time = time.time()
    train_time1 = 0

    # PM matrix
    max_length = max(train_data[2])
    train_pm, confidence = poi_position(train_data[0], vocab_size, max_length)
    if cfg.config['decoding_type'] == 'Adapting':
        cfg.config['confidence'] = confidence

    for epoch in range(cfg.config['epochs']):
        print("Teacher Epoch - {} / {}".format(epoch + 1, cfg.config['epochs']))
        start_time = time.time() 

        AE.train(True)
        generator.train(True)
        enc.train(True)
        ae_f1 = []
        ae_pairsf1 = []
        
        for i, data in enumerate(train_loader, 0): 
            x = len(train_loader)
            print('-------The teacher training batch is:{}-----'.format(i))
            encode_batch, decode_batch, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = data['encoder_input'], data['decoder_input'], data['length'], data['time_input'], data['dist1_input'], data['dist2_input'], data['z_input'], data['z_time'], data['z_dist1'], data['z_dist2'], data['trend_feature'], data['trend_label']
            encode_batch, decode_batch, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = encode_batch.to(device), decode_batch.to(device), pad_lengths.to(device), input_time.to(device), dist_1.to(device), dist_2.to(device), z_in.to(device), z_time.to(device), z_dist1.to(device), z_dist2.to(device), trend_feature.to(device), trend_label.to(device)
            context = [input_time, dist_1, dist_2]
            z_context = [z_time, z_dist1, z_dist2]
            max_target_sequence_length = torch.max(pad_lengths)  
            
            # train AE model
            opt_AE.zero_grad()
            output, res, _= AE(encode_batch, context, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'])
            output = output.to(device)
            output = output.reshape(-1, output.shape[2])
            AE_labels = decode_batch.reshape(-1)
            loss_AE = loss_func_AE(output, AE_labels)
            
            loss_AE.backward()
            opt_AE.step()
            writer.add_scalar("train_AE_loss", loss_AE.item(), epoch * len(train_loader) + i)
        end_time = time.time()
        train_time1 += (end_time - start_time)


        # calculate F1 score and pairs-F1 score in training stage
        
        AE.eval()
        with torch.no_grad():
            for i, data in enumerate(test_loader, 0):
                encode_test, decode_test, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = data['encoder_input'], data['decoder_input'], data['length'], data['time_input'], data['dist1_input'], data['dist2_input'], data['z_input'], data['z_time'], data['z_dist1'], data['z_dist2'], data['trend_feature'], data['trend_label']
                encode_test, decode_test, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = encode_test.to(device), decode_test.to(device), pad_lengths.to(device), input_time.to(device), dist_1.to(device), dist_2.to(device), z_in.to(device), z_time.to(device), z_dist1.to(device), z_dist2.to(device), trend_feature.to(device), trend_label.to(device)
                context = [input_time, dist_1, dist_2]
                z_context = [z_time, z_dist1, z_dist2]
                max_target_sequence_length = torch.max(pad_lengths)

                
                _, ae_predicts, _= AE(encode_test, context, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'])
                ae_predicts = ae_predicts.to(device)
                ae_predicts = torch.round(ae_predicts).to(torch.int)
                decode_test = torch.round(decode_test).to(torch.int)
                for v in range(len(ae_predicts)):
                    length = pad_lengths[v] - 1
                    actual = decode_test[v][:length]
                    ae_recommend = torch.cat([actual[0].unsqueeze(0), ae_predicts[v][1:length - 1]], dim=0)
                    ae_recommend = torch.cat([ae_recommend, actual[-1].unsqueeze(0)], dim=0)
                    f = calc_F1(actual, ae_recommend)
                    p_f = calc_pairsF1(actual, ae_recommend)
                    ae_f1.append(f)
                    ae_pairsf1.append(p_f)
        train_AE_F1.append(np.mean(ae_f1))
        train_AE_pairsF1.append(np.mean(ae_pairsf1))
    avg_train_time1 = train_time1 / cfg.config['epochs']
            
    # train student model(start distillation)
    train_time2 = 0
    AE.eval()
    for s_epoch in range(cfg.config['stu_epochs']):
        print("Student Epoch - {} / {}".format(s_epoch + 1, cfg.config['stu_epochs']))
        time1 = time.time()
        routeGenerator.train(True)
        routeGenerator.decoder.eval()
        for i, data in enumerate(train_loader, 0): 
            print('-------The student training batch is:{}-----'.format(i))
            encode_batch, decode_batch, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = data['encoder_input'], data['decoder_input'], data['length'], data['time_input'], data['dist1_input'], data['dist2_input'], data['z_input'], data['z_time'], data['z_dist1'], data['z_dist2'], data['trend_feature'], data['trend_label']
            encode_batch, decode_batch, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label  = encode_batch.to(device), decode_batch.to(device), pad_lengths.to(device), input_time.to(device), dist_1.to(device), dist_2.to(device), z_in.to(device), z_time.to(device), z_dist1.to(device), z_dist2.to(device), trend_feature.to(device), trend_label.to(device)
            context = [input_time, dist_1, dist_2]
            z_context = [z_time, z_dist1, z_dist2]
            max_target_sequence_length = torch.max(pad_lengths)
            mask_lengths = pad_lengths - 1
            max_mask_length = torch.max(mask_lengths)
            mask = sequence_mask(mask_lengths, max_mask_length)

            
            
            #Core training process
            with torch.no_grad():
                output_t, res_t, latent_t= AE(encode_batch, context, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'])
                output_t = output_t.reshape(-1, output_t.shape[2])
                output_t = output_t.to(device)
                latent_t = latent_t.to(device)
            
          
            output_s, res_s, output_trend, latent_s= routeGenerator(z_in, z_context, trend_feature, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'], cfg.config['confidence'], train_pm)
            
            output_s = output_s.to(device)
            output_s = output_s.reshape(-1, output_s.shape[2])
            latent_s = latent_s.to(device)
            modelS_labels = decode_batch.reshape(-1)
            
            student_loss = hard_loss(output_s, modelS_labels)
            
            distillation_loss = soft_loss(
                latent_s,
                latent_t
            )
            trend_loss = loss_trendPre(output_trend, trend_label)
            modelS_loss = cfg.config['KD_alpha'] * student_loss + (1 - cfg.config['KD_alpha']) * distillation_loss
            modelS_loss = cfg.config['Multi_alpha'] * trend_loss + (1 - cfg.config['Multi_alpha']) * modelS_loss
        
            optimizer_modelS.zero_grad()
            modelS_loss.backward()
            optimizer_modelS.step()
            writer.add_scalar("train_KD_loss", modelS_loss.item(), s_epoch * len(train_loader) + i)
        time2 = time.time()
        train_time2 += (time2-time1)
    writer.close()
    avg_train_time2 = train_time2 / cfg.config['stu_epochs']
    avg_train_time = avg_train_time1 + avg_train_time2

    train_end_time = time.time()
    train_time = train_end_time - train_start_time
    # final test
    test_start_time = time.time()
    ae_test_f1, ae_test_pairs, gene_test_f1, gene_test_pairs, rep_test, case = test(test_loader, cfg.config['confidence'], train_pm)
    test_end_time = time.time()
    test_infer_time = test_end_time - test_start_time
    return train_AE_F1[-1], train_AE_pairsF1[-1], ae_test_f1, ae_test_pairs, gene_test_f1, gene_test_pairs, rep_test, train_time, avg_train_time, test_infer_time, case


def test(test_loader, confidence, train_pm):
    AE.eval()
    generator.eval()
    enc.eval()
    routeGenerator.eval()
    ae_test_f1 = []
    ae_test_pairs = []
    gene_test_f1 = []
    gene_test_pairs = []
    repetition_list = []
    
    with torch.no_grad():
        for k, test_data in enumerate(test_loader, 0): 
            encode_test, decode_test, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = test_data['encoder_input'], test_data['decoder_input'], test_data['length'], test_data['time_input'], test_data['dist1_input'], test_data['dist2_input'], test_data['z_input'], test_data['z_time'], test_data['z_dist1'], test_data['z_dist2'], test_data['trend_feature'], test_data['trend_label']
            encode_test, decode_test, pad_lengths, input_time, dist_1, dist_2, z_in, z_time, z_dist1, z_dist2, trend_feature, trend_label = encode_test.to(device), decode_test.to(device), pad_lengths.to(device), input_time.to(device), dist_1.to(device), dist_2.to(device), z_in.to(device), z_time.to(device), z_dist1.to(device), z_dist2.to(device), trend_feature.to(device), trend_label.to(device)
            context = [input_time, dist_1, dist_2]
            z_context = [z_time, z_dist1, z_dist2]
            max_target_sequence_length = torch.max(pad_lengths)
            
            mask_lengths = pad_lengths - 1
            max_mask_length = torch.max(mask_lengths)
            mask = sequence_mask(mask_lengths, max_mask_length)

            
            _, ae_predicts, latent_ae = AE(z_in, z_context, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'])
            
            outputs, gene_predicts, out_trend , latent_rg = routeGenerator(z_in, z_context, trend_feature, pad_lengths, max_target_sequence_length, cfg.config['batch_size'], vocab_to_int['GO'], vocab_to_int['PAD'], confidence, train_pm)
            
            ae_predicts = ae_predicts.to(device)
            gene_predicts = gene_predicts.to(device)
            out_trend = out_trend.to(device)
            ae_predicts = torch.round(ae_predicts).to(torch.int)
            gene_predicts = torch.round(gene_predicts).to(torch.int)
            decode_test = torch.round(decode_test).to(torch.int)
            out_trend = torch.round(out_trend).to(torch.int)
            predict_ids = gene_predicts
            for v in range(len(predict_ids)):
                length = pad_lengths[v] - 1
                actual = decode_test[v][:length]
                
                ae_recommend = torch.cat([actual[0].unsqueeze(0), ae_predicts[v][1:length - 1]], dim=0)
                ae_recommend = torch.cat([ae_recommend, actual[-1].unsqueeze(0)], dim=0)

                gene_recommend = torch.cat([actual[0].unsqueeze(0), predict_ids[v][1:length - 1]], dim=0)
                gene_recommend = torch.cat([gene_recommend, actual[-1].unsqueeze(0)], dim=0)
                
                f = calc_F1(actual, ae_recommend)
                p_f = calc_pairsF1(actual, ae_recommend)
                g_f = calc_F1(actual, gene_recommend)
                g_p_f = calc_pairsF1(actual, gene_recommend)
                repetition_ratio = count_repetition_percentage(gene_recommend)
                repetition_list.append(repetition_ratio)
                ae_test_f1.append(f)
                ae_test_pairs.append(p_f)
                gene_test_f1.append(g_f)
                gene_test_pairs.append(g_p_f)
    
    return np.mean(ae_test_f1), np.mean(ae_test_pairs), np.mean(gene_test_f1), np.mean(gene_test_pairs), np.mean(repetition_list)
        

if __name__ == "__main__":
    K=len(train_data) + len(test_data)
    print('trajectory number K:',K)
    
    AE_train_F1 = []
    AE_train_pairs_F1 = []
    AE_test_F1 = []
    AE_test_pairs_F1 = []
    Gene_test_F1 = []
    Gene_test_pairs_F1 = []
    REP = []
    train_time_total = 0
    test_time_total = 0
    epoch_train_total = 0
    for m in range(5):
        ae_train_F1, ae_train_pairs_F1, ae_test_F1, ae_test_pairs_F1, gene_test_F1, gene_test_pairs_F1, rep_test, train_time, epoch_train_time, test_time, case =train(m)
        AE_train_F1.append(ae_train_F1)
        AE_train_pairs_F1.append(ae_train_pairs_F1)
        AE_test_F1.append(ae_test_F1)
        AE_test_pairs_F1.append(ae_test_pairs_F1)
        Gene_test_F1.append(gene_test_F1)
        Gene_test_pairs_F1.append(gene_test_pairs_F1)
        REP.append(rep_test)
        train_time_total += train_time
        test_time_total += test_time
        epoch_train_total += epoch_train_time
        
    print('model output,', np.max(Gene_test_F1), np.max(Gene_test_pairs_F1), np.mean(REP))
    avg_train_time = train_time_total / 5
    avg_test_time = test_time_total / 5
    avg_train_epoch = epoch_train_total / 5
    print(f"Average training time : {avg_train_time:.2f} seconds")
    print(f"Average training time by epoch: {avg_train_epoch:.2f} seconds")
    print(f"Average testing time : {avg_test_time:.2f} seconds")
