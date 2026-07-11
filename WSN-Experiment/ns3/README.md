# NS-3.35 WSN Experiment Setup

此目录包含在 NS-3.35 中运行 WSN 双层优化实验所需的全部代码。

## 前置条件

- **Linux 环境**（WSL2 / Ubuntu 22.04+ / 物理 Linux）
- 至少 4 GB 可用内存（编译 NS-3.35 需要）
- 约 2 GB 磁盘空间（NS-3.35 + 构建产物）

## 快速开始

### 1. 安装 WSL Ubuntu（如果尚未安装）

```powershell
# 在 Windows PowerShell 中执行（管理员权限）
wsl --install -d Ubuntu-22.04
```

重启后打开 Ubuntu 终端。

### 2. 复制脚本到 WSL

```bash
# 在 WSL Ubuntu 中
cp -r /mnt/d/Workspace/JavaSource/Repositories/ProductLine/SCI-Title/SCI-Session02/WSN-TwoLayer/WSN-Experiment/ns3/ ~/wsn-ns3/
cd ~/wsn-ns3/
```

### 3. 安装 NS-3.35 并编译

```bash
bash setup_ns3.sh
```

此过程需要 15-30 分钟（编译 NS-3.35）。

### 4. 运行实验

```bash
# 完整实验（4 个规模 × 6 个协议 × 30 轮）
bash batch_run.sh

# 或手动运行
cd ~/ns-allinone-3.35/ns-3.35
./ns3 run scratch/wsn_two_layer_sim -- --scales=100,200,300,500 --runs=30 --output=output/
```

### 5. 将结果复制回 Windows

```bash
cp -r ~/ns-allinone-3.35/ns-3.35/output/ /mnt/d/Workspace/JavaSource/Repositories/ProductLine/SCI-Title/SCI-Session02/WSN-TwoLayer/WSN-Experiment/output/
```

## 硬件模型

仿真使用 TelosB 节点真实参数：

| 参数 | 值 | 来源 |
|------|-----|------|
| TX 电流 (0 dBm) | 17.4 mA | CC2420 datasheet |
| TX 电流 (-25 dBm) | 8.5 mA | CC2420 datasheet |
| RX 电流 | 19.7 mA | CC2420 datasheet |
| 空闲电流 | 1.0 mA | CC2420 datasheet |
| 睡眠电流 | 0.001 mA | CC2420 datasheet |
| 电压 | 3.0 V | TelosB 规格 |
| 初始能量 | 2.5 J | 2×AA 电池 |
| RAM | 10 kB | MSP430F1611 |
| ROM | 48 kB | MSP430F1611 |

## 输出格式

输出 CSV 文件与 WSN-Figures 管道完全兼容：

```
output/
├── scale_100/
│   ├── hnd_by_scale.csv        # HND, 能效, 交付率, 收敛时间, 公平性
│   ├── energy_timeseries.csv   # 能耗时序
│   └── jain_fairness.csv       # Jain 公平性指数
├── scale_200/
├── scale_300/
├── scale_500/
├── ablation_study.csv          # 消融实验
└── run_metadata.json           # 运行元数据
```

## 与 Python 实现的区别

| 特性 | Python 实现 | NS-3.35 实现 |
|------|------------|-------------|
| 算法 | 相同 | 相同 |
| 拓扑 | 随机几何图 | 随机几何图 |
| 能耗模型 | CC2420 参数 | CC2420 参数 |
| 信道模型 | SNR 公式 | Log-distance + Nakagami 衰落 |
| MAC 层 | 无 | 802.15.4 CSMA/CA（可选） |
| 包级仿真 | 无 | 支持（需启用） |
| 可复现性 | 种子控制 | 种子控制 |
| 平台 | 跨平台 | Linux only |

## 启用 NS-3 完整网络仿真

当前实现使用算法级仿真以提高速度。要启用 NS-3 的完整 802.15.4 包级仿真，
修改 `wsn_two_layer_sim.cc` 中的 `USE_NS3_NETWORKING` 宏：

```cpp
#define USE_NS3_NETWORKING 1  // 启用 NS-3 网络栈
```

注意：包级仿真会显著增加运行时间（300 节点 × 200 轮 ≈ 数小时）。