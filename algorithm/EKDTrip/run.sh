python train_test.py --city_name Glas --batch_size 8 --n_poiCat 8 --n_traj_len 9 --lr_AE 0.003 --lr_RG 0.001 --KD_alpha 0.375 --Multi_alpha 0.1 --dropout 0.49022287493050654 --d_model 320 --d_intermediate 128 --d_trend_embed 64 --d_trend_vec 320 --n_layer 1 --expand 3 --conv_dim 2 --tem_depth 1 --p_dropout 0.1 --epochs 10 --stu_epochs 60

python train_test.py --city_name Osak --batch_size 8 --n_poiCat 5 --n_traj_len 7 --lr_AE 0.003 --lr_RG 0.001 --KD_alpha 0.165 --Multi_alpha 0.2  --dropout 0.4597521416314947 --d_model 64 --d_intermediate 64 --d_trend_embed 64 --d_trend_vec 320 --n_layer 1 --expand 4 --conv_dim 3 --tem_depth 2 --p_dropout 0.3 --epochs 60 --stu_epochs 70 

python train_test.py --city_name Toro --batch_size 8 --n_poiCat 7 --n_traj_len 14 --lr_AE 0.003 --lr_RG 0.001 --KD_alpha 0.375 --Multi_alpha 0.6 --dropout 0.19536391137001052 --d_model 128 --d_intermediate 64 --d_trend_embed 128 --d_trend_vec 256 --n_layer 2 --expand 4 --conv_dim 2 --tem_depth 2 --p_dropout 0.1 --epochs 10 --stu_epochs 40

python train_test.py --city_name TKY_split200 --batch_size 8 --n_poiCat 3 --n_traj_len 8 --lr_AE 0.003 --lr_RG 0.001 --KD_alpha 0.497 --Multi_alpha 0.6  --dropout 0.12817439859231727 --d_model 64 --d_intermediate 64 --d_trend_embed 32 --d_trend_vec 320 --n_layer 1 --expand 4 --conv_dim 3 --tem_depth 2 --p_dropout 0.1 --epochs 70 --stu_epochs 20

