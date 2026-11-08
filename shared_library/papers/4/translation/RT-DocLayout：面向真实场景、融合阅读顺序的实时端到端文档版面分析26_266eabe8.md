# RT-DocLayout：面向真实场景、融合阅读顺序的实时端到端文档版面分析

**原文标题：** RT-DocLayout: Real-Time End-to-End Document Layout Analysis with Reading Order in the Wild

**作者：** Cheng Cui, Tingquan Gao, Xueqing Wang, Changda Zhou, Hongen Liu, Ting Sun, Yubo Zhang, Zelun Zhang, Jiaxuan Liu, Manhui Lin, Yue Zhang, Suyin Liang, Yiqing Xiang, Yi Liu

**单位：** PaddlePaddle 团队，百度公司

**邮箱：** paddleocr@baidu.com

---

## 摘要

准确的文档版面分析仍然是文档解析系统中的一个关键瓶颈，这是由于异构文档版面元素、几何畸变（例如纸张翘曲与弯曲、透视变化）以及不同版面结构中的阅读顺序之间存在复杂的耦合关系。现有方法通常依赖彼此割裂的多阶段流水线，或者计算开销较大的生成式 Transformer 架构，从而导致误差传播以及计算效率受限。

本文提出 **RT-DocLayout**，一种用于文档版面分析的高效端到端框架，旨在作为文档解析任务的前端模块。所提出的模型在一个仅包含 **3300 万参数**的统一架构中，实现了版面元素的分类、检测、像素级分割以及阅读顺序预测。

RT-DocLayout 建立在 RT-DETR 基础之上。本文的核心贡献是在一个基于查询的解码器中构建统一的多任务建模方式，使模型能够同时完成类别分类、边界框回归、掩码生成以及元素间关系构建，从而推断阅读顺序。

通过联合学习几何表示与结构表示，RT-DocLayout 引入了多任务优化机制，显著提高了模型面对真实世界文档畸变时的鲁棒性。

在多个公开基准数据集上的大量实验表明，该模型在保持 **132.1 FPS 实时推理速度**的同时，在文档版面分析任务上取得了当前最先进水平的性能。

当与下游 OCR 引擎结合使用时，RT-DocLayout 能够显著提升完整文档的重建质量，为真实世界中的文档智能系统提供一种具有可扩展性和实用性的基础方案。

RT-DocLayout 已在 PaddleOCR 中以 **PP-DocLayoutV3** 的名称发布。

RT-DocLayout 是本文学术论文中使用的名称，而 PP-DocLayoutV3 是 PaddleOCR 开源项目中采用的名称。

模型权重公开地址：

`https://huggingface.co/PaddlePaddle/PP-DocLayoutV3`

**arXiv：2606.23344v1 [cs.CV]，2026 年 6 月 22 日**

---

## 图 1｜RT-DocLayout 的性能与鲁棒性

本文提出的方法在文档版面分析任务上取得了新的当前最先进水平，在准确率、实时速度以及鲁棒性方面均表现出显著优势。

### 图 1(a)

比较不同方法的性能（综合准确率）、推理速度（FPS）以及模型参数量，其中气泡大小表示模型参数量。

本文提出的 RT-DocLayout（红色气泡）仅包含 **3300 万参数**，却实现了：

- 综合准确率：**92.46%**
- 推理速度：**132.1 FPS**

在准确率、速度和模型规模三个指标上，RT-DocLayout 均显著超过此前的领先方法，例如 PP-DocLayoutV2 和 MinerU2.5。

综合准确率为图 1(b) 所示六个维度得分的平均值。

所有实验均采用 **PaddleOCR-VL-1.5-0.9B** 作为下游识别器。

推理速度在 **NVIDIA A100 GPU** 上进行测试，批大小设置为 **32**。

### 图 1(b)

在 OmniDocBench v1.5 和 Real5-OmniDocBench 中六个具有挑战性的维度上进行直接比较。

六个维度分别为：

- 原始文档
- 扫描
- 翘曲
- 屏幕拍摄
- 光照
- 倾斜

RT-DocLayout 在所有维度上均持续取得最高得分，证明了其在多种真实世界条件下具有出色的鲁棒性和泛化能力。

---

# 1. 引言

文档版面分析（Document Layout Analysis，DLA）是实现自动化文档智能的一项基础性前提。

尽管深度学习在版面元素检测方面已经取得显著成功，但在移动设备拍摄、装订档案数字化等复杂场景中，由于几何形变十分普遍，文档解析仍然面临两个主要挑战：

1. 结构建模的割裂性；
2. 几何表示的粗粒度性。

当前方法通常沿着两条并不理想的技术路线发展。

第一类方法采用级联式流水线，通过在版面检测器之后叠加额外的关系模型，例如图神经网络（GNN）[1] 或启发式排序方法 [2]，以重建文档的阅读顺序。

这类系统天然较为脆弱，因为检测阶段产生的误差会沿后续阶段持续传播。

此外，由于缺乏端到端集成，模型难以捕获版面结构与拓扑关系之间的协同依赖。

第二类方法采用大规模预训练 Transformer 和视觉语言模型（VLM），例如 LayoutLMv3 [3]、DiT [4]、MinerU [5] 和 Dolphin [6]。

这些模型虽然取得了令人瞩目的结果，但计算成本仍然较高。

此外，这些模型主要依赖粗粒度的边界框表示，而边界框无法提供在翘曲、弯曲或倾斜文档中分离版面元素所需的像素级掩码。

这种几何精度的不足往往会导致背景噪声或相邻元素对内容产生干扰，从而限制下游解析结果的保真度。

为解决上述问题，我们提出 **RT-DocLayout**，这是一种基于 RT-DETR [7] 架构、包含 **3300 万参数**的统一框架。

RT-DocLayout 打破了传统任务边界，在一个基于查询的 Transformer 解码器中统一完成：

- 分类；
- 检测；
- 分割；
- 阅读顺序预测。

在一次前向传播过程中，每个对象查询同时完成类别预测、边界框回归、针对复杂几何区域的高保真掩码生成以及阅读顺序预测。

RT-DocLayout 的核心优势在于能够提供一种**多维结构表示**。

通过生成精确的像素级掩码，而不是简单的矩形边界框，该模型能够向下游 OCR 引擎提供更加纯净的输入，从而有效减轻文档形变所造成的干扰。

这种统一的多任务学习范式使几何形状与逻辑顺序能够在共享特征空间中共同建模，从而获得更加优异的结构一致性。

值得注意的是，RT-DocLayout 仅使用紧凑的 **3300 万参数**，便在多个基准数据集上取得了当前最先进水平（SOTA）的性能，为实时工业文档解析提供了一种高效且具有良好可扩展性的解决方案。

本文的主要贡献总结如下：

1. 我们提出 RT-DocLayout，这是一种包含 3300 万参数的统一 Transformer 文档版面分析框架，可端到端实现分类、检测、像素级掩码生成以及阅读顺序预测。
2. 我们证明，相较于传统的基于边界框的方法，为非刚性形变区域提供像素级掩码可以显著提高文档解析的鲁棒性。
3. 大量实验结果表明，RT-DocLayout 在保持实时推理效率的同时取得了当前最先进水平的准确率，验证了其作为文档解析系统实用前端模块的有效性。

---

# 2. 相关工作

## 2.1 文档版面元素检测

早期方法将 Faster R-CNN [8] 和 Mask R-CNN [9] 应用于文档图像 [10, 11]。

DiT [4] 将自监督预训练引入文档 Transformer，而 LayoutLM 系列 [12, 13, 3] 则率先实现了文本、版面和视觉信息的联合预训练。

DocLayout-YOLO [14] 进一步提高了实际部署场景中的推理速度。

尽管上述方法取得了显著进展，但这些方法仍然局限于使用**轴对齐边界框**。

在存在几何畸变时，此类边界框会降低 OCR 的识别保真度，并且上述方法均没有对阅读顺序进行联合建模。

---

## 2.2 阅读顺序预测

基于规则的 XYCut [2] 在复杂版面中较为脆弱。

数据驱动的方法通常将阅读顺序问题建模为：

- 序列生成问题；
- 关系预测问题。

例如，LayoutReader [15] 在 ReadingBank 基准数据集上对自回归 Transformer 进行预训练。

XYLayoutLM [16] 则将空间阅读顺序融入版面感知预训练过程。

然而，这些方法均作为独立检测器之后的后处理模块运行，因此形成了容易产生误差传播的级联式流水线。

---

## 2.3 统一文档解析框架

Donut [17] 和 Nougat [18] 使用无需 OCR 的编码器—解码器模型生成结构化标记。

UDOP [19] 则进一步在生成式框架中统一了视觉、文本和版面信息。

包括 Dolphin [6]、MinerU2.5 [5]、MinerU2 [20] 和 dots.ocr [21] 在内的大型视觉语言模型将这一思路扩展到多任务文档解析，但相应的计算成本较高。

与本文方法更为接近的是 DLAFormer [22]。

该方法在基于 DETR 的端到端框架中，通过统一标签空间联合预测版面区域和阅读顺序。

PP-DocLayoutV2 [23] 则在 RT-DETR [7] 后附加一个解耦的阅读顺序模块，以实现紧凑的实时解析。

然而，这两种方法仍然局限于使用轴对齐边界框，无法有效处理由纸张翘曲、透视变化或倾斜造成的几何畸变。

### 本文方法

RT-DocLayout 采用一种紧凑的纯视觉架构，解决上述全部局限。

基于“检测与分割可以通过统一查询联合优化”这一思想 [24]，我们扩展 RT-DETR [7]，使其支持端到端分割。

本文提出的统一多任务建模方法能够在一次前向传播过程中同时预测：

- 边界框；
- 高保真像素级掩码；
- 阅读顺序。

该方法以**确定性的非自回归解码方式**同时取代自回归生成和级联式流水线。

---

# 3. 所提出的方法

## 3.1 框架概述

RT-DocLayout 建立在高效的 RT-DETR 检测器基础之上，将文档版面分析重新表述为一个统一的、**以掩码为中心的预测任务**。

与依赖传统边界框表示不同，该框架能够生成像素级精确的版面元素位置，并在同一个 Transformer 架构中联合建模阅读顺序关系。

这种设计使模型在页面倾斜或存在几何畸变等具有挑战性的条件下，仍然能够可靠地分离不同文档版面元素。

在上述场景中，基于边界框的方法往往会引入歧义以及背景干扰。

通过将检测任务与阅读顺序预测统一到同一框架中，RT-DocLayout 消除了冗余的后处理阶段，并在各种几何变化条件下促进了具有结构一致性和鲁棒性的文档版面分析。

---

## 3.2 架构设计

RT-DocLayout 建立在高效的 RT-DETR 目标检测器 [7] 基础之上，并将传统检测范式扩展为面向文档版面分析的统一结构预测，如图 2 所示。

模型不再仅依赖边界框表示，而是增加了一个基于掩码的检测头，用于生成像素级精确的分割区域。

因此，即使面对倾斜、弯曲或其他几何畸变的页面，模型仍可以精确分离版面元素。

在上述条件下，轴对齐边界框通常会引入歧义和背景污染。

与此前系统 [23] 所采用的解耦式指针网络设计不同，RT-DocLayout 将阅读顺序预测直接集成到 Transformer 解码器中，从而能够对几何感知能力以及阅读顺序的关系表示进行联合优化。

遵循基于查询的建模范式，解码器迭代优化 $N$ 个对象查询：

$$
Q = \{q_i\}_{i=1}^{N} \in \mathbb{R}^{N \times d}
$$

其中，每个查询同时编码空间语义和结构语义。

模型根据优化后的查询嵌入计算相对阅读顺序的逻辑值矩阵，然后通过基于投票的排序策略，为所有元素确定绝对阅读顺序。

具体而言，首先将优化后的查询投影到共享关系空间中，并计算成对的先后顺序得分：

$$
S_{i,j}
=
\frac{
q_i^{\top} W_q^{\top} W_k q_j
-
q_j^{\top} W_q^{\top} W_k q_i
}{
\sqrt{d_h}
}
\tag{1}
$$

---

## 图 2｜RT-DocLayout 的统一架构

该架构包含并行的分割预测头与阅读顺序预测头。

其中：

$$
W_q, W_k \in \mathbb{R}^{d_h \times d}
$$

为可学习的投影矩阵，用于将查询映射到关系嵌入空间。

$d_h$ 表示预测头维度。

由此得到的关系矩阵为：

$$
S \in \mathbb{R}^{N \times N}
$$

该矩阵天然具有反对称性：

$$
S_{i,j} = -S_{j,i}
$$

当：

$$
S_{i,j} > 0
$$

时，表示元素 $i$ 位于元素 $j$ 之前。

在推理阶段，模型采用一种基于投票的排序策略，将成对关系转换为全局一致的序列。

应用 Sigmoid 函数后，元素 $j$ 的前序投票数通过对所有指向该元素的关系进行求和得到：

$$
V_j
=
\sum_{i=1}^{N}
\sigma(S_{i,j}),
\qquad
S_{i,i}=0
\tag{2}
$$

其中，$V_j$ 表示预计位于元素 $j$ 之前的元素数量。

最终的阅读顺序通过按照 $V_j$ 的升序对所有元素进行排序得到。

也就是说，前序元素数量较少的元素将在序列中更早出现。

通过在一个以视觉为核心的架构中联合优化分类、检测、分割以及成对顺序关系，RT-DocLayout 能够在一次前向传播过程中生成完整的文档结构，同时输出：

- 类别标签；
- 边界框；
- 像素级掩码；
- 阅读顺序。

这种统一建模方式在消除冗余后处理和独立特征提取阶段的同时，提高了文档版面分析的结构一致性和几何鲁棒性。

---

## 3.3 损失函数设计

RT-DocLayout 的训练目标被表述为一个多任务优化问题，同时对以下内容进行监督：

- 分类；
- 边界框；
- 分割掩码；
- 成对阅读顺序关系。

在计算损失之前，我们采用**匈牙利算法**在预测结果和真实标注之间建立最优二分匹配。

### 总体目标

总损失由六个损失项加权组合得到：

$$
\mathcal{L}_{\text{total}}
=
\sum_{k \in \mathcal{K}}
\lambda_k \mathcal{L}_k
\tag{3}
$$

其中：

$$
\mathcal{K}
=
\{
\text{cls},
\text{bbox},
\text{giou},
\text{mask},
\text{dice},
\text{order}
\}
$$

各损失项对应的权重设置为：

$$
\lambda_{\text{cls}} = 4
$$

$$
\lambda_{\text{bbox}} = 5
$$

$$
\lambda_{\text{giou}} = 2
$$

$$
\lambda_{\text{mask}} = 5
$$

$$
\lambda_{\text{dice}} = 5
$$

$$
\lambda_{\text{order}} = 50
$$

阅读顺序损失被赋予明显更高的权重，主要有两个原因。

第一，这是为了缓解**梯度稀释问题**。

阅读顺序损失作用于：

$$
O(N^2)
$$

个元素对，因此每一个成对预测所接收到的梯度大约会被稀释 $N/2$ 倍。

相比之下，其他对象级损失按照：

$$
O(N)
$$

的规模增长，因此能够保持更加直接的梯度影响。

第二，其他损失可以受益于所有解码器层上的**深度监督**。

对于具有 $L$ 层的模型，这相当于可以获得 $L$ 倍的梯度更新。

而阅读顺序损失仅在最后一个解码器层计算，因此在整个训练过程中得到的优化信号显著更少。

---

### 分类与检测损失

对于类别预测，我们采用 Focal Loss，并设置：

$$
\alpha = 0.25
$$

$$
\gamma = 2.0
$$

以解决类别不平衡问题。

分类损失为：

$$
\mathcal{L}_{\text{cls}}
=
-
\frac{1}{N}
\sum_i
\alpha_{y_i}
(1-p_i)^{\gamma}
\log(p_i)
\tag{4}
$$

其中，$p_i$ 表示模型对真实类别 $y_i$ 的预测概率。

边界框回归由 $\ell_1$ 损失和 GIoU 损失共同组成：

$$
\mathcal{L}_{\text{bbox}}
=
\|b_i-\hat{b}_i\|_1
$$

$$
\mathcal{L}_{\text{giou}}
=
1-\operatorname{GIoU}(b_i,\hat{b}_i)
\tag{5}
$$

其中，$b_i$ 和 $\hat{b}_i$ 分别表示预测边界框和真实边界框。

---

### 掩码分割损失

像素级掩码监督由二元交叉熵损失和 Dice 损失构成：

$$
\mathcal{L}_{\text{mask}}
=
\operatorname{BCE}(m_i,\hat{m}_i)
$$

$$
\mathcal{L}_{\text{dice}}
=
1-
\frac{
2|m_i \cap \hat{m}_i|+1
}{
|m_i|+|\hat{m}_i|+1
}
\tag{6}
$$

遵循 MaskDINO 的设计，我们采用具有重要性加权的基于点的采样策略，以高效计算掩码损失。

每个掩码采样：

$$
K=12544
$$

个点，其中 **75%** 的采样点分配给不确定区域。

---

### 相对阅读顺序损失

本文损失函数设计的一个核心贡献是对**成对阅读顺序关系进行监督**。

给定 $N$ 个完成匹配的版面元素，其真实阅读顺序索引为：

$$
\{o_1,o_2,\ldots,o_N\}
$$

我们构建二值目标矩阵：

$$
T \in \{0,1\}^{N\times N}
$$

其中：

$$
T_{i,j}
=
\begin{cases}
1, & o_i < o_j \quad \text{（元素 } i \text{ 位于元素 } j \text{ 之前）} \\
0, & \text{其他情况}
\end{cases}
\tag{7}
$$

反对称成对评分器预测成对逻辑值矩阵：

$$
S \in \mathbb{R}^{N\times N}
$$

并满足：

$$
S_{i,j}
=
\frac{
f(q_i,q_j)-f(q_j,q_i)
}{
\sqrt{d_h}
}
$$

其中：

$$
f(q_i,q_j)
=
(W_q q_i)^{\top}
(W_k q_j)
\tag{8}
$$

这一设计能够确保：

$$
S_{i,j}=-S_{j,i}
$$

从而保证顺序关系的一致性。

为了更加重视局部顺序预测的正确性，我们进一步引入了**局部性感知加权机制**。

对于动态邻居窗口：

$$
k=\max(5,0.3N)
$$

以内的元素对，我们设置更高的权重：

$$
w_{\text{local}}=2.0
$$

具体而言：

$$
w_{i,j}
=
\begin{cases}
w_{\text{local}},
& 0 < |o_i-o_j| \leq k \\
1.0,
& \text{其他情况}
\end{cases}
\tag{9}
$$

为了处理潜在的标注噪声，我们采用带有标签平滑的广义交叉熵损失（Generalized Cross Entropy，GCE），其中：

$$
\varepsilon=0.01
$$

阅读顺序损失定义为：

$$
\mathcal{L}_{\text{order}}
=
\frac{1}{|P|}
\sum_{(i,j)\in P}
w_{i,j}
\cdot
\operatorname{GCE}(S_{i,j},T_{i,j})
\tag{10}
$$

其中，$P$ 表示所有有效的上三角元素对集合，不包含对角线元素。

GCE 定义为：

$$
\operatorname{GCE}(z,t)
=
\frac{1-p_t^q}{q}
$$

其中：

$$
p_t
=
\begin{cases}
\sigma(z), & t=1 \\
1-\sigma(z), & t\neq1
\end{cases}
$$

并设置：

$$
q=0.7
$$

以提高模型对噪声的鲁棒性。

---

### 深度监督

来自中间解码器层的辅助损失为分类、检测和分割任务提供深度监督，从而改善梯度传播和模型收敛。

然而，阅读顺序损失仅在解码器的最后一层计算。

这一设计选择源于以下观察：

准确的阅读顺序预测从根本上依赖于精确的目标定位和分类。

中间层的表示尚未获得充分的空间信息和语义信息精炼，因此无法提供具有实际意义的阅读顺序监督。

---

## 3.4 物理空间感知数据增强

在真实场景中，由移动设备拍摄的文档图像通常具有复杂的几何畸变。

这些畸变可以被划分为两种不同的物理过程：

1. 内在表面形变；
2. 外在投影变换。

然而，标准文档数据集通常只提供轴对齐边界框或者平面多边形标注，因此无法表达页面翘曲在像素级上的细微特征。

---

## 图 3｜物理空间感知数据增强流水线

为缩小这一领域差距，我们提出一种在线的**物理空间感知数据增强流水线**，如图 3 所示。

该方法将数据增强解耦为一个级联过程：

首先模拟纸张表面的非刚性物理翘曲，随后对随机相机视角进行建模。

该流水线能够利用标准平面标注动态合成真实的畸变效果，从而为训练具有形变感知能力的分割模型提供稳健基础。

---

### 阶段 1：内在表面形变（Intrinsic Surface Deformation，ISD）

为了描述物理文档所具有的非刚性几何先验，例如装订书籍中的页面卷曲现象，我们提出了一种基于网格的翘曲算子。

与标准线性变换不同，ISD 使用平滑且具有周期性的位移场来模拟纸张形变。

对于每个像素 $(x,y)$，其形变后的坐标 $(x',y')$ 计算如下：

$$
x'
=
x
+
A\cdot
f_x(\omega_y\cdot y)
\cdot d_x
$$

$$
y'
=
y
+
A\cdot
f_y(\omega_x\cdot x)
\cdot d_y
\tag{11}
$$

其中：

$$
f_x,f_y\in\{\sin,\cos\}
$$

为随机采样得到的波函数。

位移幅度定义为：

$$
A=\alpha\min(H,W)
$$

其大小与图像分辨率成比例，其中 $\alpha$ 从可配置范围内采样。

空间频率由下式控制：

$$
\omega_x
=
\frac{\beta\pi}{W}
$$

$$
\omega_y
=
\frac{\beta\pi}{H}
$$

其中，$\beta$ 采用均匀采样。

同时：

$$
d_x,d_y\in\{-1,1\}
$$

用于随机改变位移方向。

该算子支持两种随机模式。

第一种为**单轴模式**，仅沿某一个坐标轴施加位移，以模拟单方向页面卷曲。

第二种为**强形变模式**，同时沿两个坐标轴施加位移，以模拟复合型形变。

图像和掩码分别使用：

- 双线性插值；
- 最近邻插值；

进行重映射。

边界填充根据最大位移幅度动态计算，以确保所有文档内容均得到保留。

---

### 阶段 2：外在投影变换（Extrinsic Projective Transformation，EPT）

由于相机视角存在变化，文档图像经常会发生几何畸变。

为了模拟这一现象，EPT 对非受控环境中的相机视角变化进行建模。

我们将这一过程表述为复合单应性变换 $M$，将经过上一阶段翘曲后的表面映射到具有三维感知能力的透视空间。

变换矩阵满足：

$$
M\in\mathbb{R}^{3\times3}
$$

并被分解为：

$$
M=S\cdot R\cdot P
\tag{12}
$$

其中，$P$ 通过投影参数 $p_{20}$ 和 $p_{21}$ 引入透视缩短效应，以模拟倾斜观察视角。

$R$ 和 $S$ 则分别表示：

- 平面内旋转；
- 角度剪切。

这些变换用于模拟自然的手持设备拍摄过程。

最后，根据经过变换的像素级精确掩码重新提取轴对齐边界框，以更新实例级真实标注。

---

# 4. 实验

## 4.1 实验设置

### 4.1.1 数据集

为了确保模型能够在多样化的真实文档场景中保持稳定性能，我们构建了一个用于版面分析的内部数据集。

该数据集包含约 **3.8 万张文档图像**，覆盖多个不同领域，包括：

- 学术论文；
- 教材；
- 市场分析报告；
- 金融报告；
- 幻灯片；
- 报纸；
- 教学补充材料；
- 试卷；
- 各类发票；
- 各类收据。

数据集对 **25 类不同的版面元素**进行了细致的人工标注：

1. 段落标题；
2. 图像；
3. 文本；
4. 编号；
5. 摘要；
6. 正文内容；
7. 图标题；
8. 独立公式；
9. 表格；
10. 参考文献；
11. 文档标题；
12. 脚注；
13. 页眉；
14. 算法；
15. 页脚；
16. 印章；
17. 图表；
18. 公式编号；
19. 旁注文本；
20. 参考文献内容；
21. 页眉图像；
22. 页脚图像；
23. 行内公式；
24. 竖排文本；
25. 视觉脚注。

所有文档均人工标注了元素级边界以及相应的阅读顺序，因此可以同时有效训练和评估：

- 版面元素检测任务；
- 阅读顺序预测任务。

这些高质量真实标注能够确保模型准确恢复复杂文档的空间结构以及逻辑信息流。

本文所有实验均使用该内部数据集进行训练。

在评估阶段，我们采用：

- OmniDocBench v1.5 [25]；
- Real5-OmniDocBench [26]。

Real5-OmniDocBench 是面向真实世界文档场景构建的 OmniDocBench 衍生数据集。

---

### 4.1.2 评估指标

目前尚缺乏能够综合评估版面分析能力，同时覆盖版面检测和阅读顺序预测的标准化评价指标。

因此，我们通过**下游文档解析基准**对 RT-DocLayout 进行评估。

与仅依赖几何检测准确率的方法不同，该评估方案直接考察预测得到的版面结构是否能够在真实场景中有效支持结构化文档解析。

具体而言，我们在 OmniDocBench v1.5 及其真实场景扩展数据集 Real5-OmniDocBench 上进行评估，并分别衡量：

- 公式；
- 表格；
- 文本内容；
- 阅读顺序。

这些指标能够共同反映：

- 空间定位准确性；
- 版面结构一致性；
- 语义一致性。

---

## 表 1｜不同版面分析模块与不同识别系统组合在 OmniDocBench v1.5 上的性能比较

由于 DocLayout-YOLO 不输出阅读顺序，因此我们采用 XYCut 算法作为其后处理步骤。

| 版面分析方法 | 参数量 | FPS | 识别方法 | 综合得分 ↑ | 文本编辑距离 ↓ | 公式 CDM ↑ | 表格 TEDS ↑ | 阅读顺序编辑距离 ↓ |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| DocLayout-YOLO [14] | 20M | 107.4 | MonkeyOCR [27] | 85.10 | 0.130 | 85.99 | 82.31 | 0.169 |
| DocLayout-YOLO [14] | 20M | 107.4 | MinerU2.5 [5] | 85.73 | 0.138 | 87.26 | 83.73 | 0.177 |
| DocLayout-YOLO [14] | 20M | 107.4 | Dolphin-v2 [28] | 84.14 | 0.150 | 83.92 | 83.47 | 0.178 |
| DocLayout-YOLO [14] | 20M | 107.4 | PaddleOCR-VL-1.5-0.9B [29] | 87.29 | 0.127 | 88.74 | 85.83 | 0.169 |
| MinerU2.5 [5] | 1.2B | 2.4 | MonkeyOCR [27] | 89.69 | 0.047 | 87.06 | 86.71 | 0.050 |
| MinerU2.5 [5] | 1.2B | 2.4 | MinerU2.5 [5] | 90.17 | 0.052 | 87.81 | 87.95 | 0.053 |
| MinerU2.5 [5] | 1.2B | 2.4 | Dolphin-v2 [28] | 88.25 | 0.068 | 83.55 | 88.02 | 0.062 |
| MinerU2.5 [5] | 1.2B | 2.4 | PaddleOCR-VL-1.5-0.9B [29] | 91.31 | 0.046 | 87.57 | 90.92 | 0.051 |
| Dolphin-v2 [28] | 3B | 0.9 | MonkeyOCR [27] | 89.14 | 0.051 | 87.28 | 85.24 | 0.061 |
| Dolphin-v2 [28] | 3B | 0.9 | MinerU2.5 [5] | 89.58 | 0.055 | 87.71 | 86.57 | 0.067 |
| Dolphin-v2 [28] | 3B | 0.9 | Dolphin-v2 [28] | 87.49 | 0.073 | 83.04 | 86.69 | 0.067 |
| Dolphin-v2 [28] | 3B | 0.9 | PaddleOCR-VL-1.5-0.9B [29] | 90.36 | 0.049 | 87.60 | 88.36 | 0.060 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | MonkeyOCR [27] | 91.32 | 0.038 | 89.41 | 88.41 | 0.045 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | MinerU2.5 [5] | 92.00 | 0.042 | 90.51 | 89.66 | 0.051 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | Dolphin-v2 [28] | 87.49 | 0.073 | 83.04 | 86.69 | 0.067 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | PaddleOCR-VL-1.5-0.9B [29] | 93.56 | 0.034 | 92.09 | 92.03 | 0.042 |
| RT-DocLayout | 33M | 132.1 | MonkeyOCR [27] | 92.51 | 0.039 | 92.37 | 89.07 | 0.044 |
| RT-DocLayout | 33M | 132.1 | MinerU2.5 [5] | 92.68 | 0.043 | 92.19 | 90.12 | 0.049 |
| RT-DocLayout | 33M | 132.1 | Dolphin-v2 [28] | 90.72 | 0.060 | 89.17 | 89.00 | 0.058 |
| RT-DocLayout | 33M | 132.1 | PaddleOCR-VL-1.5-0.9B [29] | **94.50** | 0.035 | **94.21** | **92.76** | **0.042** |

---

### 4.1.3 实现细节

模型采用 **PP-DocLayout_plus-L** 的预训练权重进行初始化。

我们将训练语料规模扩展至超过 **3.8 万个高质量文档样本**。

每个样本均经过严格的人工标注，以提供真实标注信息，包括：

- 坐标；
- 类别标签；
- 每个版面元素的绝对阅读顺序。

为了增强模型对不同环境条件的鲁棒性，我们设计了一种专门的**畸变感知数据增强流水线**。

不同于标准数据增强方式，该流水线专门模拟真实移动设备拍摄过程中出现的复杂物理形变。

我们使用 AdamW 优化器，其权重衰减设置为：

$$
0.0001
$$

学习率保持恒定，为：

$$
2\times10^{-4}
$$

该学习率设置旨在确保集成的反对称成对评分器以及掩码预测头能够稳定收敛。

模型共训练：

$$
150
$$

个轮次。

总批大小为：

$$
32
$$

---

## 表 2｜不同版面分析与识别系统组合在 Real5-OmniDocBench 上的性能比较

由于 DocLayout-YOLO 不输出阅读顺序，因此我们使用 XYCut 算法进行后处理。

综合得分为以下五种场景的平均值：

- 扫描；
- 翘曲；
- 屏幕拍摄；
- 光照；
- 倾斜。

| 版面分析方法 | 参数量 | FPS | 识别方法 | 综合 ↑ | 扫描 ↑ | 翘曲 ↑ | 屏幕拍摄 ↑ | 光照 ↑ | 倾斜 ↑ |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| DocLayout-YOLO [14] | 20M | 107.4 | MonkeyOCR [27] | 73.57 | 84.09 | 74.81 | 76.89 | 81.99 | 50.06 |
| DocLayout-YOLO [14] | 20M | 107.4 | MinerU2.5 [5] | 72.92 | 85.00 | 72.92 | 77.38 | 82.68 | 46.62 |
| DocLayout-YOLO [14] | 20M | 107.4 | Dolphin-v2 [28] | 72.72 | 83.40 | 73.59 | 75.90 | 81.00 | 49.71 |
| DocLayout-YOLO [14] | 20M | 107.4 | PaddleOCR-VL-1.5-0.9B [29] | 74.07 | 85.57 | 74.70 | 77.67 | 83.65 | 48.74 |
| MinerU2.5 [5] | 1.2B | 2.4 | MonkeyOCR [27] | 85.23 | 88.70 | 84.10 | 87.16 | 87.63 | 78.56 |
| MinerU2.5 [5] | 1.2B | 2.4 | MinerU2.5 [5] | 84.55 | 88.37 | 82.85 | 88.29 | 88.02 | 75.20 |
| MinerU2.5 [5] | 1.2B | 2.4 | Dolphin-v2 [28] | 82.48 | 87.20 | 82.72 | 85.89 | 86.17 | 70.45 |
| MinerU2.5 [5] | 1.2B | 2.4 | PaddleOCR-VL-1.5-0.9B [29] | 85.67 | 89.74 | 83.92 | 89.24 | 89.29 | 76.16 |
| Dolphin-v2 [28] | 3B | 0.9 | MonkeyOCR [27] | 69.74 | 87.86 | 58.41 | 81.01 | 68.31 | 53.12 |
| Dolphin-v2 [28] | 3B | 0.9 | MinerU2.5 [5] | 60.88 | 87.70 | 45.38 | 76.75 | 58.54 | 36.01 |
| Dolphin-v2 [28] | 3B | 0.9 | Dolphin-v2 [28] | 67.40 | 85.72 | 58.08 | 73.30 | 64.03 | 55.84 |
| Dolphin-v2 [28] | 3B | 0.9 | PaddleOCR-VL-1.5-0.9B [29] | 67.66 | 88.66 | 52.58 | 81.06 | 66.15 | 49.84 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | MonkeyOCR [27] | 85.10 | 90.47 | 85.90 | 81.60 | 88.86 | 78.65 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | MinerU2.5 [5] | 83.87 | 90.98 | 83.88 | 81.98 | 89.06 | 73.44 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | Dolphin-v2 [28] | 84.16 | 89.46 | 84.54 | 81.11 | 87.97 | 77.71 |
| PP-DocLayoutV2 [23] | 53M | 110.9 | PaddleOCR-VL-1.5-0.9B [29] | 85.83 | 92.04 | 86.00 | 83.28 | 90.80 | 77.03 |
| RT-DocLayout | 33M | 132.1 | MonkeyOCR [27] | 89.79 | 91.73 | 89.38 | 89.67 | 89.72 | 88.44 |
| RT-DocLayout | 33M | 132.1 | MinerU2.5 [5] | 89.89 | 91.74 | 88.96 | 90.38 | 90.31 | 88.06 |
| RT-DocLayout | 33M | 132.1 | Dolphin-v2 [28] | 88.97 | 90.36 | 88.47 | 88.61 | 89.39 | 88.04 |
| RT-DocLayout | 33M | 132.1 | PaddleOCR-VL-1.5-0.9B [29] | **92.05** | **93.43** | **91.25** | **91.76** | **92.16** | **91.66** |

---

## 4.2 主要实验结果

### 4.2.1 OmniDocBench v1.5

表 1 展示了不同版面分析模块与不同识别方法组合后，在 OmniDocBench v1.5 上的性能。

在所有被评估的识别方法上，RT-DocLayout 均获得了最佳的综合性能。

当与 PaddleOCR-VL-1.5-0.9B 搭配使用时，RT-DocLayout 的综合得分达到：

$$
94.50
$$

这是所有被评估组合中的最高值。

当 RT-DocLayout 分别与 MonkeyOCR、MinerU2.5 和 Dolphin-v2 结合时，同样可以观察到稳定的性能提升。

这说明 RT-DocLayout 对不同类型的识别架构具有良好的兼容性。

除综合指标外，RT-DocLayout 在多个评估维度上也获得了稳定提升，包括：

- 文本准确率，即编辑距离；
- 公式识别性能，即 CDM；
- 表格结构相似度，即 TEDS；
- 阅读顺序预测性能，即编辑距离。

这些结果表明，提高版面分析质量能够以整体性的方式促进下游识别性能。

此外，RT-DocLayout 仅包含 **3300 万参数**，推理速度达到：

$$
132.1\ \text{FPS}
$$

因此，在所有被评估的版面分析模块中，RT-DocLayout 同时实现了：

- 最高推理速度；
- 最佳综合准确率。

---

### 4.2.2 Real5-OmniDocBench

为了进一步评估模型面对真实世界物理畸变时的鲁棒性，我们在 Real5-OmniDocBench 上开展实验。

该数据集包含五种具有挑战性的场景：

- 扫描；
- 翘曲；
- 屏幕拍摄；
- 光照；
- 倾斜。

如表 2 所示，RT-DocLayout 在不同识别系统下均持续取得优异性能。

当与 PaddleOCR-VL-1.5-0.9B 结合时，其综合得分达到：

$$
92.05\%
$$

为所有配置中的最高值。

在翘曲和倾斜等具有较大几何挑战的场景中，这一性能提升尤其明显。

例如，当采用 PaddleOCR-VL-1.5-0.9B 时：

翘曲场景性能达到：

$$
91.25\%
$$

倾斜场景性能达到：

$$
91.66\%
$$

相比之下，基于边界框的版面分析方法在上述场景中表现出更加明显的性能下降。

这一现象说明，更精确的几何建模能够提高模型在各种畸变条件下的鲁棒性。

此外，RT-DocLayout 在不同识别方法上均表现出一致的性能提升。

这说明这些改进并非针对某个特定的下游模型，而是源自**版面分析本身能力的增强**。

---

## 4.3 消融实验与分析

我们在 OmniDocBench v1.5 和 Real5-OmniDocBench 上进行了结构化消融实验，以分析 RT-DocLayout 中各个组成部分对于统一文档版面分析的贡献。

所有实验均采用 PaddleOCR-VL-1.5-0.9B 作为下游识别器。

实验结果汇总于表 3。

---

## 表 3｜RT-DocLayout 各组成模块的消融实验

该表比较模型在 OmniDocBench v1.5 及其真实世界退化子集 Real5-OmniDocBench 上的性能。

我们分析以下因素：

- 定位方法：边界框与掩码；
- 阅读顺序模块；
- 本文提出的数据增强方法。

评估指标包括：

- 综合准确率 $O$，越高越好；
- 阅读顺序距离 $RO$，越低越好。

完整模型，即最后一行，获得最佳性能，证明了各组成模块的有效性。

| 定位方式 | 阅读顺序方法 | 数据增强 | Omni $O↑$ | Omni $RO↓$ | 扫描 $O↑$ | 扫描 $RO↓$ | 翘曲 $O↑$ | 翘曲 $RO↓$ | 屏幕拍摄 $O↑$ | 屏幕拍摄 $RO↓$ | 光照 $O↑$ | 光照 $RO↓$ | 倾斜 $O↑$ | 倾斜 $RO↓$ |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bbox | XYCut [2] | × | 93.81 | 0.082 | 90.30 | 0.749 | 84.44 | 0.720 | 88.35 | 0.744 | 88.90 | 0.747 | 77.18 | 0.662 |
| bbox + mask | XYCut [2] | × | 94.33 | 0.074 | 90.22 | 0.742 | 84.40 | 0.721 | 88.55 | 0.744 | 89.14 | 0.747 | 75.63 | 0.673 |
| bbox + mask | 解耦式 | × | 93.87 | 0.189 | 92.85 | 0.192 | 85.91 | 0.238 | 91.22 | 0.195 | 91.55 | 0.188 | 76.24 | 0.325 |
| bbox + mask | 耦合式 | × | 94.39 | 0.041 | 93.29 | 0.045 | 86.68 | 0.092 | 91.55 | 0.050 | 92.12 | 0.054 | 77.55 | 0.146 |
| bbox + mask | 耦合式 | ✓ | **94.50** | 0.042 | **93.43** | 0.045 | **91.25** | **0.063** | **91.76** | 0.059 | **92.16** | **0.051** | **91.66** | **0.061** |

---

### 基于掩码定位的有效性

如表 3 前两行所示，将单纯的边界框监督替换为联合掩码预测：

$$
\text{bbox}+\text{mask}
$$

之后，模型在 OmniDocBench v1.5 上的综合准确率 $O$ 从：

$$
93.81\%
$$

提高到：

$$
94.33\%
$$

像素级掩码的引入能够提供更加精细的结构线索，使模型能够更好地区分相互重叠或者紧密排列的元素。

这一优势也体现在 Real5-OmniDocBench 的大多数场景中，综合准确率均获得了较为一致的提升。

---

### 耦合式阅读顺序学习

RT-DocLayout 的一个关键贡献是对阅读顺序进行**端到端预测**。

与启发式 XYCut [2] 相比，本文提出的耦合式学习方法，也就是表中倒数第二行，将 OmniDocBench v1.5 上的阅读顺序距离 $RO$ 从：

$$
0.074
$$

显著降低至：

$$
0.041
$$

更重要的是，在“翘曲”这一复杂子集上，$RO$ 距离从 XYCut 的：

$$
0.721
$$

大幅下降到：

$$
0.092
$$

值得注意的是，采用**解耦式学习策略**时，也就是将阅读顺序作为一个独立模型进行训练，而不进行联合优化，其 OmniDocBench v1.5 上的阅读顺序距离为：

$$
0.189
$$

明显差于 XYCut 的：

$$
0.074
$$

然而，通过联合优化，这一性能劣势被有效逆转。

这进一步验证了：

**将阅读顺序直接集成到版面感知阶段，可以使模型更加有效地捕获全局结构依赖关系。**

---

### 通过真实感数据增强提升鲁棒性

Real5-OmniDocBench 上最显著的性能跃升来自本文提出的数据增强方法。

启用数据增强之后，也就是表 3 最后一行，模型在“翘曲”和“倾斜”子集上的性能分别提高：

$$
4.57
$$

个百分点，即：

$$
86.68\%
\rightarrow
91.25\%
$$

以及：

$$
14.11
$$

个百分点，即：

$$
77.55\%
\rightarrow
91.66\%
$$

更为关键的是，这种鲁棒性提升并不仅体现在定位能力上，同时也扩展到了阅读顺序预测。

在“倾斜”子集上，阅读顺序距离从：

$$
0.146
$$

显著降低至：

$$
0.061
$$

在“翘曲”子集上，该指标则从：

$$
0.092
$$

降低至：

$$
0.063
$$

由于本文模型能够输出掩码级结果，因此数据增强过程可以在保持像素级真实标注的同时，模拟页面卷曲、相机倾斜等真实几何畸变。

上述实验结果表明，通过在**掩码引导的合成畸变数据**上进行训练，RT-DocLayout 能够在非线性变换条件下依旧保持空间结构与逻辑结构的一致性。

因此，在不牺牲 OmniDocBench v1.5 准确率的前提下，本文模型实现了针对真实世界物理形变的当前最先进水平鲁棒性。

---

## 图 4｜四种真实场景下的定性比较

每组结果从左至右依次为：

- 原始图像；
- PP-DocLayoutV2；
- 本文方法。

其中：

- (a) 倾斜；
- (b) 页面翘曲；
- (c) 非均匀光照；
- (d) 屏幕拍摄。

---

## 4.4 定性分析与案例观察

图 4 将 RT-DocLayout 与此前处于当前最先进水平的实时文档版面分析方法 PP-DocLayoutV2 进行了比较。

比较涉及四种真实世界场景：

1. 倾斜；
2. 页面翘曲；
3. 非均匀光照；
4. 屏幕拍摄。

在图 4(a) 和图 4(b) 中，当文档几何结构偏离正对相机的平面时，轴对齐边界框会同时覆盖背景区域以及相邻元素。

而 RT-DocLayout 生成的掩码能够在各种畸变条件下贴合元素的真实边界。

在图 4(c) 中，由于低对比度问题，PP-DocLayoutV2 会漏检较暗区域中的内容。

相比之下，RT-DocLayout 能够在整个版面范围内生成一致的预测结果。

在图 4(d) 中，PP-DocLayoutV2 会将表格、文本块以及标题混合成较粗粒度的区域。

RT-DocLayout 在屏幕拍摄条件下仍然能够恢复细粒度的元素边界。

这些案例表明，面对多种真实世界退化情况，RT-DocLayout 都能够生成准确且具有几何一致性的版面预测结果。

---

# 5. 结论

本文提出了 **RT-DocLayout**，一种统一且高效的、基于 Transformer 的实时文档版面分析框架。

与传统的以边界框为中心的建模范式不同，RT-DocLayout 在单次非自回归前向传播过程中统一完成：

- 版面检测；
- 像素级分割；
- 阅读顺序预测。

这种统一建模方式能够提升文档结构一致性和几何鲁棒性，对于存在复杂形变的文档尤其有效。

大量实验结果表明，RT-DocLayout 仅包含 **3300 万参数**，却能够在准确率与效率之间取得优异平衡。

与规模显著更大的模型相比，RT-DocLayout 在以下两个方面均表现出更强的能力：

- 几何保真度；
- 实时部署能力。

RT-DocLayout 为下一代文档智能系统建立了一种**具有可扩展性且具备结构感知能力的基础架构**。

---

# 参考文献

## [1]

Chen-Yu Lee, Chun-Liang Li, Chu Wang, Renshen Wang, Yasuhisa Fujii, Siyang Qin, Ashok Popat, Tomas Pfister.

**RoPE：用于基于图的文档信息抽取的阅读顺序等变位置编码。**

2021。

URL：

`https://arxiv.org/abs/2106.10786`

---

## [2]

Jaekyu Ha, Robert M Haralick, Ihsin T Phillips.

**基于连通组件边界框的递归 XY 切分方法。**

载于第三届国际文档分析与识别会议论文集，第 2 卷，第 952–955 页。

IEEE，1995。

---

## [3]

Yupan Huang, Tengchao Lv, Lei Cui, Yutong Lu, Furu Wei.

**LayoutLMv3：基于统一文本与图像掩码的文档人工智能预训练方法。**

2022。

URL：

`https://arxiv.org/abs/2204.08387`

---

## [4]

Junlong Li, Yiheng Xu, Tengchao Lv, Lei Cui, Cha Zhang, Furu Wei.

**DiT：面向文档图像 Transformer 的自监督预训练。**

2022。

URL：

`https://arxiv.org/abs/2203.02378`

---

## [5]

Junbo Niu, Zheng Liu, Zhuangcheng Gu, Bin Wang, Linke Ouyang, Zhiyuan Zhao, Tao Chu, Tianyao He, Fan Wu, Qintong Zhang, Zhenjiang Jin, Guang Liang, Rui Zhang, Wenzheng Zhang, Yuan Qu, Zhifei Ren, Yuefeng Sun, Yuanhong Zheng, Dongsheng Ma, Zirui Tang, Boyu Niu, Ziyang Miao, Hejun Dong, Siyi Qian, Junyuan Zhang, Jingzhou Chen, Fangdong Wang, Xiaomeng Zhao, Liqun Wei, Wei Li, Shasha Wang, Ruiliang Xu, Yuanyuan Cao, Lu Chen, Qianqian Wu, Huaiyu Gu, Lindong Lu, Keming Wang, Dechen Lin, Guanlin Shen, Xuanhe Zhou, Linfeng Zhang, Yuhang Zang, Xiaoyi Dong, Jiaqi Wang, Bo Zhang, Lei Bai, Pei Chu, Weijia Li, Jiang Wu, Lijun Wu, Zhenxiang Li, Guangyu Wang, Zhongying Tu, Chao Xu, Kai Chen, Yu Qiao, Bowen Zhou, Dahua Lin, Wentao Zhang, Conghui He.

**MinerU2.5：用于高效高分辨率文档解析的解耦式视觉语言模型。**

2025。

URL：

`https://arxiv.org/abs/2509.22186`

---

## [6]

Hao Feng, Shu Wei, Xiang Fei, Wei Shi, Yingdong Han, Lei Liao, Jinghui Lu, Binghong Wu, Qi Liu, Chunhui Lin, Jingqun Tang, Hao Liu, Can Huang.

**Dolphin：通过异构锚点提示实现文档图像解析。**

2025。

URL：

`https://arxiv.org/abs/2505.14059`

---

## [7]

Yian Zhao, Wenyu Lv, Shangliang Xu, Jinman Wei, Guanzhong Wang, Qingqing Dang, Yi Liu, Jie Chen.

**实时目标检测中 DETR 超越 YOLO。**

2024。

URL：

`https://arxiv.org/abs/2304.08069`

---

## [8]

Shaoqing Ren, Kaiming He, Ross Girshick, Jian Sun.

**Faster R-CNN：利用区域候选网络迈向实时目标检测。**

2016。

URL：

`https://arxiv.org/abs/1506.01497`

---

## [9]

Kaiming He, Georgia Gkioxari, Piotr Dollár, Ross Girshick.

**Mask R-CNN。**

2018。

URL：

`https://arxiv.org/abs/1703.06870`

---

## [10]

Xu Zhong, Jianbin Tang, Antonio Jimeno Yepes.

**PubLayNet：迄今规模最大的文档版面分析数据集。**

2019。

URL：

`https://arxiv.org/abs/1908.07836`

---

## [11]

Zejiang Shen, Ruochen Zhang, Melissa Dell, Benjamin Charles Germain Lee, Jacob Carlson, Weining Li.

**LayoutParser：用于基于深度学习的文档图像分析的统一工具包。**

2021。

URL：

`https://arxiv.org/abs/2103.15348`

---

## [12]

Yiheng Xu, Minghao Li, Lei Cui, Shaohan Huang, Furu Wei, Ming Zhou.

**LayoutLM：面向文档图像理解的文本与版面预训练。**

载于第 26 届 ACM SIGKDD 知识发现与数据挖掘国际会议论文集，KDD '20，第 1192–1200 页。

ACM，2020 年 8 月。

DOI：

`10.1145/3394486.3403172`

URL：

`http://dx.doi.org/10.1145/3394486.3403172`

---

## [13]

Yang Xu, Yiheng Xu, Tengchao Lv, Lei Cui, Furu Wei, Guoxin Wang, Yijuan Lu, Dinei Florencio, Cha Zhang, Wanxiang Che, Min Zhang, Lidong Zhou.

**LayoutLMv2：面向视觉丰富文档理解的多模态预训练。**

2022。

URL：

`https://arxiv.org/abs/2012.14740`

---

## [14]

Zhiyuan Zhao, Hengrui Kang, Bin Wang, Conghui He.

**DocLayout-YOLO：通过多样化合成数据与全局到局部自适应感知增强文档版面分析。**

2024。

URL：

`https://arxiv.org/abs/2410.12628`

---

## [15]

Zilong Wang, Yiheng Xu, Lei Cui, Jingbo Shang, Furu Wei.

**LayoutReader：用于阅读顺序检测的文本与版面预训练。**

2021。

URL：

`https://arxiv.org/abs/2108.11591`

---

## [16]

Zhangxuan Gu, Changhua Meng, Ke Wang, Jun Lan, Weiqiang Wang, Ming Gu, Liqing Zhang.

**XYLayoutLM：面向视觉丰富文档理解的版面感知多模态网络。**

2022。

URL：

`https://arxiv.org/abs/2203.06947`

---

## [17]

Geewook Kim, Teakgyu Hong, Moonbin Yim, Jeongyeon Nam, Jinyoung Park, Jinyeong Yim, Wonseok Hwang, Sangdoo Yun, Dongyoon Han, Seunghyun Park.

**无需 OCR 的文档理解 Transformer。**

2022。

URL：

`https://arxiv.org/abs/2111.15664`

---

## [18]

Lukas Blecher, Guillem Cucurull, Thomas Scialom, Robert Stojnic.

**Nougat：面向学术文档的神经光学理解方法。**

2023。

URL：

`https://arxiv.org/abs/2308.13418`

---

## [19]

Zineng Tang, Ziyi Yang, Guoxin Wang, Yuwei Fang, Yang Liu, Chenguang Zhu, Michael Zeng, Cha Zhang, Mohit Bansal.

**统一视觉、文本与版面信息以实现通用文档处理。**

2023。

URL：

`https://arxiv.org/abs/2212.02623`

---

## [20]

opendatalab.

**MinerU2.0-2505-0.9B。**

2025。

URL：

`https://huggingface.co/opendatalab/MinerU2.0-2505-0.9B`

---

## [21]

Yumeng Li, Guang Yang, Hao Liu, Bowen Wang, Colin Zhang.

**dots.ocr：利用单一视觉语言模型实现多语言文档版面解析。**

2025。

URL：

`https://arxiv.org/abs/2512.02498`

---

## [22]

Jiawei Wang, Kai Hu, Qiang Huo.

**DLAFormer：一种用于文档版面分析的端到端 Transformer。**

2024。

URL：

`https://arxiv.org/abs/2405.11757`

---

## [23]

Cheng Cui, Ting Sun, Suyin Liang, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Xueqing Wang, Changda Zhou, Hongen Liu, Manhui Lin, Yue Zhang, Yubo Zhang, Handong Zheng, Jing Zhang, Jun Zhang, Yi Liu, Dianhai Yu, Yanjun Ma.

**PaddleOCR-VL：通过 0.9B 超紧凑视觉语言模型增强多语言文档解析。**

2025。

URL：

`https://arxiv.org/abs/2510.14528`

---

## [24]

Feng Li, Hao Zhang, Huaizhe Xu, Shilong Liu, Lei Zhang, Lionel M. Ni, Heung-Yeung Shum.

**Mask DINO：迈向统一的基于 Transformer 的目标检测与分割框架。**

2022。

URL：

`https://arxiv.org/abs/2206.02777`

---

## [25]

Linke Ouyang, Yuan Qu, Hongbin Zhou, Jiawei Zhu, Rui Zhang, Qunshu Lin, Bin Wang, Zhiyuan Zhao, Man Jiang, Xiaomeng Zhao, Jin Shi, Fan Wu, Pei Chu, Minghao Liu, Zhenxiang Li, Chao Xu, Bo Zhang, Botian Shi, Zhongying Tu, Conghui He.

**OmniDocBench：利用全面标注对多样化 PDF 文档解析进行基准评测。**

2025。

URL：

`https://arxiv.org/abs/2412.07626`

---

## [26]

Changda Zhou, Ziyue Gao, Xueqing Wang, Tingquan Gao, Cheng Cui, Jing Tang, Yi Liu.

**Real5-OmniDocBench：面向真实场景鲁棒文档解析的全尺度物理重建基准。**

2026。

URL：

`https://arxiv.org/abs/2603.04205`

---

## [27]

Zhang Li, Yuliang Liu, Qiang Liu, Zhiyin Ma, Ziyang Zhang, Shuo Zhang, Biao Yang, Zidun Guo, Jiarui Zhang, Xinyu Wang, Xiang Bai.

**MonkeyOCR：基于“结构—识别—关系”三元范式的文档解析方法。**

2026。

URL：

`https://arxiv.org/abs/2506.05218`

---

## [28]

Hao Feng, Wei Shi, Ke Zhang, Xiang Fei, Lei Liao, Dingkang Yang, Yongkun Du, Xuecheng Wu, Jingqun Tang, Yang Liu, Hong Chen, Can Huang.

**Dolphin-v2：通过可扩展锚点提示实现通用文档解析。**

2026。

URL：

`https://arxiv.org/abs/2602.05384`

---

## [29]

Cheng Cui, Ting Sun, Suyin Liang, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Xueqing Wang, Changda Zhou, Hongen Liu, Manhui Lin, Yue Zhang, Yubo Zhang, Yi Liu, Dianhai Yu, Yanjun Ma.

**PaddleOCR-VL-1.5：迈向用于真实场景鲁棒文档解析的多任务 0.9B 视觉语言模型。**

2026。

URL：

`https://arxiv.org/abs/2601.21957`