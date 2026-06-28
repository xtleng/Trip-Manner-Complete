# t-SNE可视化实验方案：偏好解耦模块效果验证

## 1. 实验目的

通过t-SNE降维可视化，直观展示模型中**偏好解耦模块**（Preference Disentanglement）的有效性：
- K=4个偏好因子（z_stack中的各head输出）在有解耦约束时是否被有效分离
- 对比有/无解耦损失时因子表示的分布差异

## 2. 核心原理

模型中的解耦模块：
- **位置**: `model.py` 第390-399行，`disentangle_heads`（K=4个MLP head）
- **输入**: `h_u = cat([h_seq, s_u])` (序列编码+语义编码拼接)
- **输出**: `z_stack` shape=[B, K, H]，K个独立偏好因子
- **约束**: `_decouple_semantic_loss`（第640-649行）最小化因子间cosine similarity → 正交约束

**预期**：有约束时4个factor在embedding空间中形成4个分离簇；无约束时混杂在一起。

## 3. 实验步骤

### Step 1: 训练消融版本（无解耦损失）

在两个数据集上各跑一次 `lambda_decouple=0, lambda_semantic=0` 的消融训练：

```bash
# Foursquare 消融
python main.py --dataset_name Foursquare \
  --ori_data ../../Foursquare/home.txt \
  --dst_data ../../Foursquare/oot.txt \
  --trans_data ../../Foursquare/travel.txt \
  --save_path ../../Foursquare/model_save_ablation_decouple \
  --data_split_path ../../Foursquare/data_split_new.pkl \
  --lambda_decouple 0.0 --lambda_semantic 0.0 \
  --name ablation_no_decouple \
  --epoch 30 --best_save \
  [其余超参数保持与最终实验一致]

# Yelp 消融
python main.py --dataset_name Yelp \
  --ori_data ../../Yelp/home.txt \
  --dst_data ../../Yelp/oot.txt \
  --trans_data ../../Yelp/travel.txt \
  --save_path ../../Yelp/model_save_ablation_decouple \
  --data_split_path ../../Yelp/data_split_new.pkl \
  --lambda_decouple 0.0 --lambda_semantic 0.0 \
  --name ablation_no_decouple \
  --epoch 30 --best_save \
  [其余超参数保持与最终实验一致]
```

**重要**：使用相同的 `data_split_path` 确保测试集划分一致。

### Step 2: 编写可视化脚本

新建 `code/visualize_tsne_decouple.py`，核心流程：

```python
"""
t-SNE可视化：对比有/无偏好解耦约束时K个偏好因子的分布
"""
import argparse
import os
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'serif'  # 论文风格字体

from data import TravelDatasetV2, random_split
from model import CrossCityLLMCPR
from spot_utils import collate_fn, set_seeds
from trainer import load_checkpoint


def extract_z_stack(model, dataloader, device):
    """从测试集提取所有样本的z_stack [N, K, H]"""
    model.eval()
    all_z = []
    with torch.no_grad():
        for batch_data in dataloader:
            batch = unpack_batch(batch_data, device)
            h_seq, s_u, z_stack, mix = model._encode_home(batch)
            all_z.append(z_stack.cpu().numpy())  # [B, K, H]
    return np.concatenate(all_z, axis=0)  # [N, K, H]


def plot_tsne_comparison(z_full, z_ablation, dataset_name, output_dir, pref_num=4):
    """绘制对比t-SNE图"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']  # 4色方案
    labels = [f'Factor {i+1}' for i in range(pref_num)]

    for ax, z_data, title in [
        (axes[0], z_full, '(a) w/ Decoupling Loss'),
        (axes[1], z_ablation, '(b) w/o Decoupling Loss'),
    ]:
        N, K, H = z_data.shape
        # 拉平为 [N*K, H]，标签为 factor index
        X = z_data.reshape(N * K, H)
        y = np.repeat(np.arange(K), N)  # 注意reshape顺序
        # 正确方式：先transpose再reshape
        X = z_data.transpose(1, 0, 2).reshape(K * N, H)  # [K*N, H]

        # t-SNE降维
        tsne = TSNE(n_components=2, perplexity=30, random_state=42,
                    n_iter=1000, init='pca', learning_rate='auto')
        X_2d = tsne.fit_transform(X)

        # 绘制散点图
        for i in range(K):
            mask = (y == i)
            ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                      c=colors[i], label=labels[i],
                      alpha=0.6, s=15, edgecolors='none')

        ax.set_title(title, fontsize=14)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f'tsne_decouple_{dataset_name}.pdf')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.savefig(save_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    print(f"Saved: {save_path}")
    plt.close()


def unpack_batch(batch_data, device):
    """复用trainer.py中的unpack逻辑"""
    (uid, pad_ori_ck, pad_dst_ck, pad_masked_dst_ck,
     pad_o_hour, pad_d_hour, pad_masked_d_hour,
     pad_ori_t, pad_dst_t, pad_ori_l, pad_dst_l,
     ori_pad, dst_pad, ori_rg, dst_rg,
     pad_ori_tag, pad_dst_tag,
     query_start_poi, query_start_hour,
     query_end_poi, query_end_hour, query_len,
     user_profile, query_vec, home_prompt_text) = batch_data

    return {
        'uid': uid.to(device),
        'ori_ck': pad_ori_ck.to(device),
        'dst_ck': pad_dst_ck.to(device),
        'masked_dst_ck': pad_masked_dst_ck.to(device),
        'o_hour': pad_o_hour.to(device),
        'd_hour': pad_d_hour.to(device),
        'masked_d_h': pad_masked_d_hour.to(device),
        'ori_t': pad_ori_t.to(device),
        'dst_t': pad_dst_t.to(device),
        'ori_l': pad_ori_l.to(device),
        'dst_l': pad_dst_l.to(device),
        'ori_pad': ori_pad.to(device),
        'dst_pad': dst_pad.to(device),
        'ori_rg': ori_rg.to(device),
        'dst_rg': dst_rg.to(device),
        'ori_tag': pad_ori_tag.to(device),
        'dst_tag': pad_dst_tag.to(device),
        'query_start_poi': query_start_poi.to(device),
        'query_start_hour': query_start_hour.to(device),
        'query_end_poi': query_end_poi.to(device),
        'query_end_hour': query_end_hour.to(device),
        'query_len': query_len.to(device),
        'user_profile': user_profile.to(device),
        'query_vec': query_vec.to(device),
        'home_prompt_text': home_prompt_text,
    }


def main():
    parser = argparse.ArgumentParser(description='t-SNE visualization for decoupling module')
    parser.add_argument('--dataset_name', type=str, required=True)
    parser.add_argument('--ckpt_full', type=str, required=True,
                        help='完整模型checkpoint路径')
    parser.add_argument('--ckpt_ablation', type=str, required=True,
                        help='消融模型(无解耦)checkpoint路径')
    parser.add_argument('--ori_data', type=str, required=True)
    parser.add_argument('--dst_data', type=str, required=True)
    parser.add_argument('--trans_data', type=str, required=True)
    parser.add_argument('--data_split_path', type=str, required=True)
    parser.add_argument('--output_dir', type=str, default='./tsne_figures/')
    parser.add_argument('--device', type=str, default='cuda:0')
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--seed', type=int, default=2050)
    parser.add_argument('--perplexity', type=int, default=30)
    parser.add_argument('--max_samples', type=int, default=0,
                        help='最大采样数,0表示用全部测试集')
    # 模型构建所需参数（需与训练时一致）
    parser.add_argument('--hidden_size', type=int, default=128)
    parser.add_argument('--dropout', type=float, default=0.1)
    parser.add_argument('--nhead', type=int, default=4)
    parser.add_argument('--semantic_layers', type=int, default=2)
    parser.add_argument('--seq_num_layers', type=int, default=2)
    parser.add_argument('--pref_factor_k', type=int, default=4)
    parser.add_argument('--use_mamba_backbone', type=int, default=1)
    parser.add_argument('--mamba_d_state', type=int, default=16)
    parser.add_argument('--mamba_d_conv', type=int, default=4)
    parser.add_argument('--mamba_expand', type=int, default=2)
    parser.add_argument('--semantic_backend', type=str, default='qwen')
    parser.add_argument('--llm_model_name', type=str, default='Qwen/Qwen2.5-0.5B-Instruct')
    parser.add_argument('--llm_cache_dir', type=str, default='../../code/params')
    parser.add_argument('--llm_max_length', type=int, default=256)
    parser.add_argument('--llm_micro_batch', type=int, default=4)
    parser.add_argument('--llm_max_traj_tokens', type=int, default=64)
    parser.add_argument('--soft_prompt_len', type=int, default=8)
    parser.add_argument('--profile_dim', type=int, default=7)
    parser.add_argument('--query_dim', type=int, default=7)
    parser.add_argument('--temperature', type=float, default=0.07)
    parser.add_argument('--gamma_city', type=float, default=0.5)
    parser.add_argument('--lambda_decouple', type=float, default=0.1)
    parser.add_argument('--lambda_semantic', type=float, default=0.1)
    parser.add_argument('--lambda_gen', type=float, default=1.0)
    parser.add_argument('--lambda_pair', type=float, default=0.2)
    parser.add_argument('--lambda_transition', type=float, default=0.3)
    parser.add_argument('--eta_fixed', type=float, default=-1.0)
    parser.add_argument('--use_beam_search', type=int, default=1)
    parser.add_argument('--beam_size', type=int, default=4)
    parser.add_argument('--beam_len_penalty', type=float, default=0.2)
    parser.add_argument('--use_no_repeat_mask', type=int, default=1)
    parser.add_argument('--pop_bias_scale', type=float, default=0.1)
    parser.add_argument('--city_memory_momentum', type=float, default=0.95)
    parser.add_argument('--city_memory_prior_k', type=float, default=20.0)
    parser.add_argument('--decode_constraint_mode', type=str, default='hard')
    parser.add_argument('--soft_constraint_scale', type=float, default=0.2)
    parser.add_argument('--soft_constraint_dist_emb_dim', type=int, default=32)
    parser.add_argument('--enforce_start_end_constraints', type=int, default=1)
    parser.add_argument('--enable_pairwise_loss', type=int, default=1)
    parser.add_argument('--pair_max_future', type=int, default=4)
    parser.add_argument('--transition_logit_scale', type=float, default=0.5)
    parser.add_argument('--gen_loss_chunk_len', type=int, default=16)
    parser.add_argument('--ellipse_filter', action='store_true')
    parser.add_argument('--ellipse_beta', type=float, default=1.2)
    parser.add_argument('--ablate_generator_no_spatial_context', type=int, default=0)

    args = parser.parse_args()
    set_seeds(args.seed)

    # ========== 加载数据 ==========
    print(f"[INFO] Loading dataset: {args.dataset_name}")
    dataset = TravelDatasetV2(args, args.ori_data, args.dst_data, args.trans_data)
    _, _, test_data = random_split(dataset, args.data_split_path, seed=args.seed, args=args)

    if args.max_samples > 0 and len(test_data) > args.max_samples:
        from torch.utils.data import Subset
        indices = np.random.choice(len(test_data), args.max_samples, replace=False)
        test_data = Subset(test_data, indices)

    test_loader = DataLoader(test_data, batch_size=args.batch_size,
                            shuffle=False, collate_fn=collate_fn)
    print(f"[INFO] Test set size: {len(test_data)}")

    # ========== 加载完整模型并提取 ==========
    print(f"[INFO] Loading full model: {args.ckpt_full}")
    model_full = CrossCityLLMCPR(args, dataset.poi_num, dataset.tag_num,
                                  dataset.region_num, dataset.poi_coords_tensor)
    model_full = load_checkpoint(model_full, args.ckpt_full, device=args.device)
    model_full = model_full.to(args.device)
    z_stack_full = extract_z_stack(model_full, test_loader, args.device)
    print(f"[INFO] Full model z_stack shape: {z_stack_full.shape}")
    del model_full
    torch.cuda.empty_cache()

    # ========== 加载消融模型并提取 ==========
    print(f"[INFO] Loading ablation model: {args.ckpt_ablation}")
    model_abl = CrossCityLLMCPR(args, dataset.poi_num, dataset.tag_num,
                                 dataset.region_num, dataset.poi_coords_tensor)
    model_abl = load_checkpoint(model_abl, args.ckpt_ablation, device=args.device)
    model_abl = model_abl.to(args.device)
    z_stack_ablation = extract_z_stack(model_abl, test_loader, args.device)
    print(f"[INFO] Ablation model z_stack shape: {z_stack_ablation.shape}")
    del model_abl
    torch.cuda.empty_cache()

    # ========== 绘制t-SNE ==========
    print(f"[INFO] Running t-SNE and plotting...")
    plot_tsne_comparison(z_stack_full, z_stack_ablation,
                         args.dataset_name, args.output_dir,
                         pref_num=args.pref_factor_k)
    print("[DONE] t-SNE visualization complete.")


if __name__ == '__main__':
    main()
```

### Step 3: 运行可视化

```bash
# Foursquare
python visualize_tsne_decouple.py \
  --dataset_name Foursquare \
  --ckpt_full ../../Foursquare/model_save_new/<你的模型目录>/model_best.xhr \
  --ckpt_ablation ../../Foursquare/model_save_ablation_decouple/ablation_no_decouple/model_best.xhr \
  --ori_data ../../Foursquare/home.txt \
  --dst_data ../../Foursquare/oot.txt \
  --trans_data ../../Foursquare/travel.txt \
  --data_split_path ../../Foursquare/data_split_new.pkl \
  --output_dir ./tsne_figures/ \
  --device cuda:0

# Yelp
python visualize_tsne_decouple.py \
  --dataset_name Yelp \
  --ckpt_full ../../Yelp/model_save_new/<你的模型目录>/model_best.xhr \
  --ckpt_ablation ../../Yelp/model_save_ablation_decouple/ablation_no_decouple/model_best.xhr \
  --ori_data ../../Yelp/home.txt \
  --dst_data ../../Yelp/oot.txt \
  --trans_data ../../Yelp/travel.txt \
  --data_split_path ../../Yelp/data_split_new.pkl \
  --output_dir ./tsne_figures/ \
  --device cuda:0
```

## 4. 注意事项

1. **load_checkpoint函数**：确认`spot_utils.py`或`trainer.py`中已有该函数，若无需根据现有checkpoint保存格式编写
2. **dataset属性**：需确认`dataset.poi_num`、`dataset.tag_num`、`dataset.region_num`、`dataset.poi_coords_tensor`在加载数据后可用
3. **内存管理**：t-SNE对大数据集较慢，如测试集过大可用`--max_samples 500`限制采样数
4. **perplexity参数**：如果样本数很少（<100），需降低perplexity到5-10
5. **结果不理想时**：可尝试调整perplexity（5/15/30/50）、n_iter（2000-5000）
6. **消融训练**：除`lambda_decouple`和`lambda_semantic`设为0外，所有其他超参数应与完整模型训练一致

## 5. 预期结果

| 模型版本 | t-SNE预期表现 |
|---------|-------------|
| 完整模型(w/ Decoupling) | 4种颜色形成4个分离的簇，表明各factor学到了不同的偏好维度 |
| 消融版本(w/o Decoupling) | 4种颜色混杂重叠，无法区分各factor |

## 6. 论文写作建议

- 图表标题建议：*"t-SNE visualization of disentangled preference factors"*
- 在文中解释：解耦损失通过最小化因子间cosine similarity实现正交约束，使K个head分别捕获不同维度的用户偏好
- 量化补充（可选）：计算各factor间的平均cosine similarity值，作为表格形式的定量证据
