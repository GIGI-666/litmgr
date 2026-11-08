# AD-GBC：一种用于基于 UNet 的医学图像分割的各向异性粒球跳跃连接优化模块

**英文标题：** AD-GBC: Anisotropic Granular-Ball Skip-Connection Refiner for UNet-Based Medical Image Segmentation

**作者：** Xiya Shen、Qinglin Zhao、Li Feng*

**作者单位：** 澳门科技大学计算机科学与工程学院，中国澳门（School of Computer Science and Engineering, Macau University of Science and Technology, Macau, China）

**电子邮箱：**

shenxy@zjou.edu.cn

qlzhao@must.edu.mo

lfeng@must.edu.mo

**\* 通讯作者。**

**出版说明：** 本 CVPR 论文是由计算机视觉基金会（Computer Vision Foundation，CVF）提供的开放获取版本。除水印外，该版本与录用版本完全一致；会议论文集的最终正式出版版本可通过 IEEE Xplore 获取。

# 摘要

近年来，原型（Prototype）模块或区域注意力（Region-Attention）模块改善了医学图像分割的性能，但仍存在两个根本性局限：1）它们将每个语义概念表示为一个点或各向同性区域，无法捕获真实特征分布所固有的各向异性几何结构；2）其中许多方法依赖不可微的聚类或单向核加权机制，这限制了它们形成一致的区域级表示的能力。为解决上述问题，我们提出了各向异性可微粒球（Anisotropic Differentiable Granular-Ball，AD-GBC）模块。该模块将原型推广为由中心和各向异性向量尺度参数化的可学习几何区域。AD-GBC 将局部特征聚合为区域级语义表示，并以完全可微的方式将细化后的表示重新分配给像素，从而能够在现代 UNet 风格的架构中实现几何感知的特征优化。

我们引入了两种几何正则化方法，即基于 Wasserstein 的多样性损失和尺度一致性损失，以缓解中心塌缩问题，并促进形成稳定且结构良好的区域几何表示。将 AD-GBC 集成到两个性能较强的骨干网络（Rolling-UNet 和 U-KAN）后，在四个广泛使用的医学图像分割基准数据集（BUSI、GlaS、CVC-ClinicDB、ISIC17）上均取得了一致的性能提升，表明所提出的几何区域建模方法能够很好地泛化到不同的医学成像条件。

代码已公开于：https://github.com/SiaShen-dot/AD-GBC

> **图 1. 研究动机。** （a）点原型无法有效表示多模态、不规则的区域。（b）采用标量半径的各向同性球难以良好拟合这些区域。（c）我们提出的模块利用各向异性区域几何结构对每种语义模态进行建模。

# 1 引言

医学图像的语义分割（Semantic Segmentation）对于临床诊断至关重要，它能够支持对肿瘤和病灶等结构进行定量分析 [3, 21]。UNet 架构凭借其编码器—解码器（Encoder–Decoder）结构和跳跃连接（Skip Connections），已成为该任务事实上的标准方法 [8, 21]。然而，标准跳跃连接中采用的简单特征拼接往往会引入语义不一致性和噪声 [19, 24]，尤其是在病灶边界模糊、背景纹理复杂等具有挑战性的情况下。

为解决这一问题，近年来的研究不再局限于简单的特征拼接，而是在编码器—解码器骨干网络之上引入基于原型或槽位（Slot）的特征细化机制。ProtoSeg [26] 和 Slot Attention [10, 15] 等方法将跳跃连接中的特征融合重新解释为像素特征与一组紧凑的可学习原型（或“槽位”）之间的交互。这些原型充当语义锚点（Semantic Anchors），有助于将原始特征组织为更加一致的模态，从而改善区域一致性和边界划分效果 [19, 26]。

然而，尽管这些方法能够有效细化跳跃连接中的特征，它们仍然将每个语义概念建模为特征空间中的一个点，并依赖单向或迭代式注意力机制，而没有对区域几何结构进行任何显式控制。因此，如图 1 所示，对于真实病灶区域中因外观模糊和边界不规则而产生的多模态特征分布、各向异性形状及特征重叠模式，这些方法难以进行充分建模。

**1）多模态特征分布（Multi-Mode Feature Distributions）。** 单个语义类别（例如“病灶”）在特征空间中通常并非单一簇，而是呈现多模态分布，由多个不同的视觉模态组成（例如深色核心区域与发炎边缘）。我们在补充材料中提供了这种多模态结构的可视化证据。如图 1(a) 所示，传统的点原型方法 [19, 26]，尤其是采用 $K=M$（即为 $M$ 个类别设置 $K$ 个原型）的方法，从根本上无法对这种多模态分布进行建模 [19]。

**2）各向异性特征几何结构（Anisotropic Feature Geometry）。** 尽管粒球计算（Granular-Ball Computing，GBC）[28] 等更先进的方法通过使用 $K\gg M$ 个粒球来解决多模态问题，但它们依赖一个关键且存在缺陷的假设：每种模态的特征分布都是各向同性的（Isotropic），即可以通过一个标量半径或一个“圆”来表示。如图 1(b) 所示，我们认为现实世界中的特征簇本质上具有各向异性（Anisotropic），即呈现“椭圆形”。

**3）模糊性（特征重叠）与类别不平衡（Ambiguity (Overlapping Features) and Class Imbalance）。** 这种根本性的几何不匹配，即各向异性数据（图 1(b) 中的数据）与各向同性模型（图 1(b) 中的虚线圆）之间的冲突，会受到另外两个挑战的严重放大：语义模糊性（即特征重叠）和类别不平衡（密集背景与稀疏病灶）。

当各向同性（标量球）原型试图对各向异性数据进行建模时，它会面临一种严重的权衡：为了覆盖特征簇的长轴，原型必须变得“过大”，如图 1(b) 所示。这个代表稀疏“病灶”类别的过大原型，不可避免地会与周围密集的“背景”特征簇产生大范围的错误重叠。这种直接由各向同性假设导致的几何缺陷，使模型在刻画类别边界处真实而细微的模糊性时出现严重失败。

为解决上述问题，我们提出了各向异性可微粒球（Anisotropic Differentiable Granular-Ball，AD-GBC）模块。AD-GBC 使用由向量尺度 $\boldsymbol{\sigma}_k\in\mathbb{R}^{D}$ 参数化的可学习各向异性区域替代点原型（图 1(c)），使每个锚点能够对特征簇的真实形状及其覆盖范围进行建模。

该模块以完全可微的方式，将像素特征聚合为区域级表示，并将细化后的语义信息反馈给像素。进一步地，我们通过权重共享的语义跳跃连接（图 2 上部），将 AD-GBC 集成到基于 UNet 的模型中，以确保特征融合之前实现一致且具有几何感知能力的特征对齐。

我们的贡献主要包括以下三个方面：

- 我们提出了 AD-GBC 模块，将点原型推广为具有各向异性且有界的几何区域，并引入两种相互耦合的几何正则化方法（$\mathcal{L}_{\text{W-div}}$ 和 $\mathcal{L}_{\text{scale-con}}$），以防止锚点塌缩并确保区域几何结构的一致性。

- 我们设计了一种权重共享的语义跳跃连接优化模块，将 AD-GBC 集成到基于 UNet 的架构中，在特征融合之前细化语义对齐关系。

- 在四个医学图像分割基准数据集（BUSI、GlaS、CVC-ClinicDB、ISIC17）上，AD-GBC 均为性能较强的骨干网络（Rolling-UNet [14]、U-KAN [13]）带来了一致的性能提升，证明了所提出的几何区域建模方法的有效性和鲁棒性。

# 2 相关工作

**编码器—解码器架构（Encoder–Decoder Architectures）。** U-Net [20] 及其变体构成了医学图像分割的基础。UNet++ [31, 32] 等方法通过嵌套式跳跃连接增强多尺度特征融合，而基于金字塔的设计 [2, 12, 25] 则进一步改善了语义信息与空间信息的整合。这些架构具备较强的特征提取与多尺度信息整合能力，但它们通常依赖逐像素特征表示，而缺乏显式的区域建模机制。

**基于原型和槽位的分割（Prototype- and Slot-Based Segmentation）。** 基于原型的方法 [30] 使用带有软分配机制的点锚点来表示语义结构。高斯注意力（Gaussian Attention）[16] 引入协方差加权核，以建模锚点周围的空间影响；而槽位注意力（Slot Attention）[10, 15] 则通过迭代更新槽位表示来捕获以对象为中心的结构。然而，这些方法主要依赖具有隐式空间支持的点式锚点，而不是显式建模有界区域。

**粒球计算（Granular-Ball Computing，GBC）。** GBC [9, 27–29] 使用由中心和半径定义的局部球来表示数据，从而实现数据空间的多粒度建模。然而，现有 GBC 方法依赖不可微的聚类过程，并假设区域具有各向同性，这限制了它们与端到端深度神经网络的集成。

表 1 总结了现有基于原型的方法与我们的方法之间的概念性差异。高斯注意力和基于槽位的方法依赖具有隐式空间支持的点锚点，而经典 GBC 建模的是各向同性区域。相比之下，我们的方法引入了各向异性区域粒球表示，该表示完全可微，并且兼容端到端训练。

**表 1. 从点锚点到各向异性区域表示的概念性比较。**

| 方法 | 锚点类型 | 空间支持 | 几何结构 |
|---|---|---|---|
| Gaussian Attention [16] | 点 | 隐式核 | 无界 |
| Slot Attention [10, 15] | 点式槽位 | 隐式 | 无 |
| 原始 GBC [9, 27–29] | 中心 | 显式区域 | 各向同性 |
| AD-GBC（本文方法） | 中心 | 显式区域 | 各向异性 |

# 3 方法

如图 2 所示，我们提出了各向异性可微粒球计算（Anisotropic Differentiable Granular-Ball Computing，AD-GBC）模块，并将其作为一种新型语义细化模块集成到 UNet 架构中，以解决第 1 节中指出的几何缺陷。

本节采用自顶向下的组织结构。首先，我们介绍整体网络架构和所提出的集成策略（第 3.1 节）；随后详细阐述核心 AD-GBC 模块（第 3.2 节）；接着介绍支持其功能实现的几何正则化损失（第 3.3 节）、最终的复合优化目标（第 3.4 节），以及计算复杂度分析（第 3.5 节）。

> **图 2. AD-GBC 模块集成方式的概念性概览。** 图中展示了第 3 级跳跃连接处的特征细化过程。两个 AD-GBC 模块共享权重，以确保编码器路径与解码器路径之间进行一致的语义细化。

## 3.1 整体架构：作为语义跳跃连接优化模块的 AD-GBC

由于具有强大的跳跃连接机制，UNet 架构 [20] 已成为医学图像分割的标准架构。这些连接将编码器中具有深层语义信息的特征与解码器中具有较高分辨率的浅层特征融合，从而实现精确定位。然而，标准跳跃连接通常仅执行简单的拼接或相加操作。这种方式可能并非最优，因为深层编码器特征虽然包含语义信息，但也可能包含噪声或无关的上下文，从而污染具有高保真度的解码器路径。

为解决这一问题，我们提出将 AD-GBC 模块作为语义跳跃连接优化模块（Semantic Skip-Connection Refiner）进行集成，而不是简单地用它替换瓶颈层（Bottleneck）。其目标是确保跨越跳跃连接进行融合的特征不仅具有高层语义信息，而且经过 AD-GBC 模块的语义对齐与净化。

**集成策略（Integration Strategy）。** 如图 2 的概念性示意所示，我们将 AD-GBC 模块部署到 UNet 较深层、具有更强语义信息的跳跃连接路径上（例如编码器和解码器的第 3 层）。这种集成采用双路径、权重共享策略：

- **编码器路径细化（Encoder Path Refinement）：** 首先，将来自编码器的特征图（例如 Encoder Block 3 的输出）输入“共享 AD-GBC（Shared AD-GBC）”模块。该步骤通过将编码器的原始语义特征投影到 $K$ 个可学习粒球上，实现对这些特征的细化。

- **解码器路径细化（Decoder Path Refinement）：** 与此同时，将解码器上采样得到的对应特征图（例如来自 Decoder Block 4 的特征图）输入完全相同的“共享 AD-GBC”模块。

- **语义融合（Semantic Fusion）：** 对细化后的编码器特征和解码器特征进行融合（例如通过逐元素相加），形成共享的语义表示，并将其作为下一个解码器块（例如 Decoder Block 3）的跳跃连接输入。

这种权重共享策略使编码器和解码器的特征在融合之前都被投影到同一个学习得到的语义流形（Semantic Manifold）上，从而确保高度的语义一致性。接下来，我们将详细介绍 AD-GBC 模块实现这种特征净化的具体机制。

## 3.2 各向异性可微粒球计算（AD-GBC）模块

传统的基于原型的模块使用一组可学习的点来表示语义。尽管这种“点原型”在全局分类任务中表现良好，但对于区域内部存在平滑外观过渡和模糊边界的分割目标而言，这种表示方式过于简化。因此，有必要从基于点的锚定方式转向基于软区域的锚定方式（Soft Region Anchoring），使每个概念由特征空间中的一个区域而非单个点来表示。

GBC 通过粒球体现了这种区域建模思想，并展现出在自适应多尺度表示方面的巨大潜力。然而，其经典形式仍然不可微，并依赖人工定义的半径，因此无法无缝集成到基于梯度优化的深度网络中。

为解决这一问题，我们提出了各向异性可微粒球计算（AD-GBC）模块。每个粒球均被视为一个可学习的软区域锚点，由中心和各向异性半径（尺度）进行参数化，并通过可微的集合→粒球→集合（Set→Ball→Set）路径与像素特征进行交互：首先将特征软分配给粒球，然后将其聚合为区域级共识表示，最后将区域信息广播回像素，以细化原始特征图。

粒球的所有参数（中心和半径）均通过完全数据驱动的端到端方式学习，使 AD-GBC 能够作为一种即插即用（Plug-and-Play）的区域几何层，集成到类似 UNet 的架构中。

> **图 3. AD-GBC 处理过程的可视化。**
>
> （a）聚合（Aggregation，Set→Ball）。
>
> （b）广播（Broadcast，Ball→Set）。

### 3.2.1 模块概览（Module Overview）

如图 2 所示，AD-GBC 模块旨在将输入特征图 $\mathbf{X}\in\mathbb{R}^{B\times C_{in}\times H\times W}$ 细化为具有相同维度的输出特征图 $\mathbf{Y}$，使其包含更加丰富的上下文信息。

输入 $\mathbf{X}$ 首先经过特征投影和展平操作。该模块的核心是作用于展平特征空间中的两阶段交互过程：聚合（Aggregation，Set→Ball）和广播（Broadcast，Ball→Set）。

这一交互过程由一组 $K$ 个可学习的粒球（Granular-Ball，GB）锚点实现。这些锚点是模块功能的核心，由以下参数进行描述：

- **锚点位置（中心）（Anchor Locations (Centers)）：** 中心集合 $\mathbf{C}=\{\mathbf{c}_1,\ldots,\mathbf{c}_K\}\in\mathbb{R}^{K\times D}$，用于表示语义位置。

- **各向异性锚点尺度（半径）（Anisotropic Anchor Scales (Radii)）：** $\boldsymbol{\Sigma}=\{\boldsymbol{\sigma}_1,\ldots,\boldsymbol{\sigma}_K\}$ 定义每个锚点在 $D$ 维特征空间中的软覆盖范围。传统的各向同性尺度采用标量半径（$\sigma_k\in\mathbb{R}$），从而将区域形状限制为超球体。相比之下，我们采用各向异性向量尺度 $\boldsymbol{\sigma}_k\in\mathbb{R}^{D}$（通过 Softplus 约束其为正），使每个锚点能够在特征空间中形成可学习的超椭球体。

最后，将处理后的特征恢复为原始空间结构，通过残差连接（Residual Connection）与原始输入融合，并经过一个细化块（Refinement Block），生成输出 $\mathbf{Y}$。

### 3.2.2 前向计算（Forward Computation）

按照图 2 所示的路径，前向计算主要包括以下三个阶段。

**1）特征投影与展平（Feature Projection and Flattening）**

鉴于 AD-GBC 的锚点工作在 $D$ 维空间中，输入特征图 $\mathbf{X}$ 首先进行可选的特征投影。当输入通道维度 $C_{in}$ 与 $D$ 不同时，通过一个轻量级 $1\times1$ 卷积（Convolution，Conv）及随后的批归一化（Batch Normalization，BN）构成的 $f_{\text{proj}}$，将通道维度从 $C_{in}$ 对齐至 $D$。

$$
\mathbf{Z}=
\begin{cases}
f_{\text{proj}}(\mathbf{X}), & C_{in}\ne D,\\
\mathbf{X}, & C_{in}=D.
\end{cases}
\tag{1}
$$

随后，将得到的特征图 $\mathbf{Z}\in\mathbb{R}^{B\times D\times H\times W}$ 展平为包含 $N=HW$ 个像素特征的序列 $\mathbf{Z}_{\text{flat}}\in\mathbb{R}^{B\times N\times D}$，记为 $\{\mathbf{z}_i\}_{i=1}^{N}$。

**2）核心 AD-GBC 交互（Set ↔ Ball）（Core AD-GBC Interaction）**

该阶段涉及像素特征（“集合”，Set）与粒球锚点（“粒球”，Ball）之间的双向信息流。图 3 对这一过程进行了概念性可视化。

首先，我们计算每个像素特征 $\mathbf{z}_i$ 对每个粒球锚点 $(\mathbf{c}_k,\boldsymbol{\sigma}_k)$ 的软隶属度（Soft Membership）。

这一计算并非基于简单的相似度，而是基于尺度化距离（Scaled Distance）。该距离衡量像素与中心 $\mathbf{c}_k$ 之间相隔多少个“半径” $\boldsymbol{\sigma}_k$：

$$
d_{i,k}
=
\left\|
(\mathbf{z}_i-\mathbf{c}_k)
\oslash
\boldsymbol{\sigma}_k
\right\|_2^2.
\tag{2}
$$

其中，$\oslash$ 表示逐元素除法。

随后，通过带有温度参数 $\tau$ 的 Softmax 对这些距离进行归一化，生成模糊分配权重 $\alpha_{i,k}$，表示像素 $\mathbf{z}_i$ 属于第 $k$ 个粒球的软分配权重：

$$
\alpha_{i,k}
=
\frac{\exp(-d_{i,k}/\tau)}
{\sum_{j=1}^{K}\exp(-d_{i,j}/\tau)}.
\tag{3}
$$

利用这些权重 $\alpha_{i,k}$，交互过程分为以下两个步骤。

**聚合（Aggregation，Set→Ball）：**

如图 3(a) 所示，模块从像素“集合”中收集信息，以形成新的区域描述符 $\mathbf{c}'_k$。

每个描述符都是所有像素特征的加权和，用于概括属于该软区域的特征所形成的共识：

$$
\mathbf{c}'_k
=
\sum_{i=1}^{N}
\alpha_{i,k}\mathbf{z}_i.
\tag{4}
$$

**广播（Broadcast，Ball→Set）：**

如图 3(b) 所示，模块随后将学习到的区域级上下文信息广播回像素“集合”。

每个像素细化后的表示 $\hat{\mathbf{z}}_i$ 通过使用相同的权重 $\alpha_{i,k}$ 对区域描述符进行加权求和构建：

$$
\hat{\mathbf{z}}_i
=
\sum_{k=1}^{K}
\alpha_{i,k}\mathbf{c}'_k.
\tag{5}
$$

**3）残差融合与细化（Residual Fusion and Refinement）**

细化后的像素特征序列 $\{\hat{\mathbf{z}}_i\}$ 通过“逆展平”（Unflatten）操作重新恢复为特征图 $\hat{\mathbf{Z}}\in\mathbb{R}^{B\times D\times H\times W}$。

随后，该特征图经过一个可选的 $1\times1$ 卷积及 BN，记为 $\tilde{f}_{\text{proj}}$，将其通道维度从 $D$ 投影回 $C_{in}$，得到 $\hat{\mathbf{X}}$。

按照图 2 中的残差路径，将具有上下文感知能力的特征图 $\hat{\mathbf{X}}$ 与原始输入 $\mathbf{X}$ 相加。该连接有助于稳定训练过程，并保留原始局部细节。

最终，融合后的特征图通过一个轻量级“细化”（Refine）块 $f_{\text{refine}}$（由 $3\times3$ Conv-BN-ReLU（Rectified Linear Unit，修正线性单元）序列构成），以增强局部一致性。

模块最终输出 $\mathbf{Y}$ 为：

$$
\mathbf{Y}
=
f_{\text{refine}}
\left(
\mathbf{X}+\hat{\mathbf{X}}
\right).
\tag{6}
$$

需要注意的是，当各向异性半径 $\boldsymbol{\sigma}_k$ 退化为标量，并移除共识聚合步骤时，AD-GBC 将退化为标准的高斯核加权方法 [16]。

## 3.3 AD-GBC 的几何正则化（Geometric Regularization for AD-GBC）

AD-GBC 模块引入可学习锚点 $\{\mathbf{c}_k\}$ 和各向异性尺度 $\{\boldsymbol{\sigma}_k\}$ 来表示语义区域。然而，如果仅使用任务损失进行训练，这些参数可能发生退化，导致锚点塌缩或尺度估计不稳定。为确保获得具有实际意义的几何表示，我们引入了两种互补的正则化损失。

> **图 4. 粒球（GB）中心分布的概念性示意图。** （a）一组具有高秩且分布多样的中心能够张成语义空间。（b）一组低秩、发生塌缩的中心无法捕获多样化的语义模态。

### 3.3.1 粒球中心的多样性正则化（Diversity Regularization for GB Centers）

在 AD-GBC 模块中，$K$ 个粒球中心 $\{\mathbf{c}_k\}$ 充当可学习的语义锚点。为了确保 Set→Ball→Set 过程具有充分的表达能力，这些锚点必须具有多样性，并分别专注于不同的视觉模态。

如果多个中心塌缩到一个低维子空间中，它们便无法表示不同的语义模态。我们将这种失败现象称为**语义塌缩（Semantic Collapse）**。如图 4(b) 所示，这会使“广播”（Broadcast）步骤退化为简单的特征混合，从而严重损害模块的表示能力和可解释性。

**一种启发式方法及其局限性（A Heuristic Approach and Its Limitations）：**

一种鼓励多样性的常见启发式方法是强制不同锚点之间保持两两不相似。我们可以采用基于平方余弦相似度（Squared Cosine Similarity）的惩罚项，以鼓励相互正交：

$$
\mathcal{L}_{\text{cos-div}}(\mathbf{C})
=
\frac{1}{K(K-1)}
\sum_{j\neq k}
\left(
\frac{
\mathbf{c}_j^\top\mathbf{c}_k
}{
\|\mathbf{c}_j\|_2
\|\mathbf{c}_k\|_2
}
\right)^2.
\tag{7}
$$

其中，$\mathbf{C}\in\mathbb{R}^{K\times D}$ 表示由 $K$ 个粒球中心构成的集合。

然而，公式（7）中的损失 $\mathcal{L}_{\text{cos-div}}$ 无法约束这些中心所张成子空间的维度。这一局限性通过定理 1 进行形式化描述。

**定理 1（余弦损失无法检测语义塌缩，Cosine Loss Cannot Detect Semantic Collapse）。**

设 $\mathbf{C}\in\mathbb{R}^{K\times D}$ 为一组非零中心，$\mathbf{G}(\mathbf{C})$ 为其归一化 Gram 矩阵。

如果

$$
\operatorname{rank}(\mathbf{G}(\mathbf{C}))=r<K,
$$

则存在

$$
\widetilde{\mathbf{C}}\in\mathbb{R}^{K\times r},
$$

使得

$$
\mathbf{G}(\widetilde{\mathbf{C}})
=
\mathbf{G}(\mathbf{C}),
$$

这意味着

$$
\mathcal{L}_{\text{cos-div}}(\widetilde{\mathbf{C}})
=
\mathcal{L}_{\text{cos-div}}(\mathbf{C}).
$$

**证明（Proof）。** 请参阅补充材料（Supplementary Material）。

**一种具有理论依据的解决方案（基于 Wasserstein 的均匀性）（A Principled Solution (Wasserstein-based Uniformity)）：**

为克服两两度量的局限性，我们不再仅对中心之间的两两关系进行正则化，而是对全部 $K$ 个中心的整体分布进行正则化。

受到文献 [11] 中 Wasserstein 均匀性（Wasserstein Uniformity）公式的启发，我们采用以下损失：

$$
\mathcal{L}_{\text{W-div}}(\mathbf{C})
=
\underbrace{
\|\hat{\mu}_C\|_2^2
}_{\text{中心化}}
+
\underbrace{
\operatorname{tr}(\hat{\Sigma}_C)
-
\frac{2}{\sqrt{D}}
\operatorname{tr}
\left(
\hat{\Sigma}_C^{1/2}
\right)
}_{\text{谱均匀性正则化}}.
\tag{8}
$$

其中，$\hat{\mu}_C$ 和 $\hat{\Sigma}_C$ 分别表示中心的经验均值和经验协方差矩阵：

$$
\hat{\mu}_C
=
\frac{1}{K}
\sum_{k=1}^{K}
\mathbf{c}_k,
$$

$$
\hat{\Sigma}_C
=
\frac{1}{K}
\sum_{k=1}^{K}
(\mathbf{c}_k-\hat{\mu}_C)
(\mathbf{c}_k-\hat{\mu}_C)^\top.
$$

这一公式鼓励特征空间中的中心形成分布充分分散且具有高秩的表示。我们在补充材料中提供了对这一约束最优解的理论分析。

在实际应用中，如图 4(a) 所示，该正则化项能够促进形成一组具有多样性的锚点。

### 3.3.2 面向各向异性的尺度一致性正则化（Scale Consistency Regularization for Anisotropy）

各向异性（向量）尺度 $\boldsymbol{\sigma}_k\in\mathbb{R}^{D}$ 是 AD-GBC 的核心组成部分，但仅依靠任务损失只能提供较弱的监督信号，因此 $\boldsymbol{\sigma}_k$ 容易发生塌缩，或者出现几何上不一致的取值。

为了提供显式约束，我们引入了尺度一致性损失（Scale Consistency Loss）$\mathcal{L}_{\text{scale-con}}$。

**观测各向异性尺度 $\mathbf{s}_k$（目标）（Observed Anisotropic Scale $\mathbf{s}_k$ (The Target)）：**

首先，我们定义观测各向异性方差 $\mathbf{s}_k^2$。它是一个 $\mathbb{R}^{D}$ 向量，表示分配给某个粒球的特征在各个维度上的几何分布范围（方差）：

$$
\mathbf{s}_k^2
=
\frac{
\sum_{i=1}^{N}
\alpha_{i,k}
\cdot
(\mathbf{z}_i-\mathbf{c}_k)^{\circ 2}
}{
\left(
\sum_{i=1}^{N}
\alpha_{i,k}
\right)
+
\epsilon
}.
\tag{9}
$$

其中，$\alpha_{i,k}$ 表示软隶属度（由公式（3）计算），$(\cdot)^{\circ 2}$ 表示逐元素平方，$\epsilon$ 是一个用于数值稳定性的小常数（例如 $10^{-6}$），以防止除零问题。

随后，通过对该方差逐元素开平方，得到观测各向异性尺度（标准差）：

$$
\mathbf{s}_k
=
\sqrt{\mathbf{s}_k^2}.
$$

**尺度一致性损失 $\mathcal{L}_{\text{scale-con}}$（约束）（The Scale Consistency Loss $\mathcal{L}_{\text{scale-con}}$ (The Constraint)）：**

最后，$\mathcal{L}_{\text{scale-con}}$ 通过最小化观测方差（$\mathbf{s}_k^2$，作为目标）与学习得到的方差（$\boldsymbol{\sigma}_k^2$，作为预测）之间的欧氏距离（L2），实现尺度一致性约束：

$$
\mathcal{L}_{\text{scale-con}}
=
\frac{1}{K}
\sum_{k=1}^{K}
\left\|
\operatorname{detach}(\mathbf{s}_k^2)
-
\boldsymbol{\sigma}_k^2
\right\|_2^2.
\tag{10}
$$

我们比较的是方差（$\mathbf{s}_k^2$ 与 $\boldsymbol{\sigma}_k^2$），而不是尺度（$\mathbf{s}_k$ 与 $\boldsymbol{\sigma}_k$），以提高数值稳定性，并避免平方根操作。因为当观测方差接近零时，平方根操作的梯度可能发生爆炸。

$\operatorname{detach}(\cdot)$ 算子可以防止形成循环依赖关系：$\boldsymbol{\sigma}_k$ 会影响 $\alpha_{i,k}$，而 $\alpha_{i,k}$ 又会影响 $\mathbf{s}_k^2$。因此，该算子确保形成稳定的单向约束，推动学习得到的尺度向观测尺度靠近。

## 3.4 复合损失函数（Composite Loss Function）

我们的模型通过复合损失函数进行端到端训练，该损失函数将主要分割任务损失 $\mathcal{L}_{\text{task}}$（例如交叉熵损失（Cross-Entropy Loss）与 Dice 损失的组合）与两种几何正则化项结合起来。

这两种正则化项分别为基于 Wasserstein 的多样性损失 $\mathcal{L}_{\text{W-div}}$（公式（8））和尺度一致性损失 $\mathcal{L}_{\text{scale-con}}$（公式（10））。

最终的优化目标为：

$$
\mathcal{L}_{\text{total}}
=
\mathcal{L}_{\text{task}}
+
\lambda\mathcal{L}_{\text{W-div}}
+
\beta\mathcal{L}_{\text{scale-con}}.
\tag{11}
$$

其中，$\lambda$ 和 $\beta$ 是超参数，分别用于平衡主要任务目标与多样性正则化、尺度一致性正则化之间的关系。

## 3.5 复杂度与效率比较（Complexity and Efficiency Comparison）

我们从计算成本（以浮点运算次数（Floating Point Operations，FLOPs）衡量）和参数数量两个方面分析 AD-GBC 模块的效率。

设 $N=HW$ 为像素数量，$K$ 为粒球数量，$D$ 为投影维度，$C_{in}$ 为输入通道数量。关于这一分析的详细逐步推导见补充材料。

模块的完整计算成本由投影层、核心 GBC 交互过程以及最终细化块共同决定。

所有步骤的计算复杂度均随 $N$ 线性增长，因此总复杂度为：

$$
\mathcal{O}
\left(
N\cdot
(C_{in}D+KD+C_{in}^2)
\right).
$$

模块的参数数量为：

$$
\mathcal{O}
\left(
KD+C_{in}D+C_{in}^2
\right).
$$

这一参数数量是固定的，与输入分辨率 $N$ 无关。

因此，AD-GBC 模块不仅具有较高的参数效率，而且能够很好地扩展到高分辨率图像。

# 4 实验（Experiments）

**数据集（Datasets）。**

我们在四个公开基准数据集上评估所提出的方法。这些数据集涵盖超声成像（Ultrasound）、组织病理学成像（Histopathology）、结肠镜成像（Colonoscopy）和皮肤镜成像（Dermoscopy）。

**BUSI [1]：** 包含 647 张具有肿瘤标注的乳腺超声图像，统一调整为 $256\times256$ 的分辨率。

**GlaS [22]：** 包含 165 张带有腺体掩码的组织病理学图像，统一调整为 $512\times512$ 的分辨率。

**CVC-ClinicDB [4]：** 包含 612 帧具有息肉掩码的结肠镜图像，统一调整为 $256\times256$ 的分辨率。

**ISIC17 [7]：** 使用 ISIC 2017 训练集，其中包含 2,000 张带有病灶掩码的皮肤镜图像，统一调整为 $256\times256$ 的分辨率。

**评价指标（Evaluation Metrics）。**

我们报告三种广泛应用于医学图像分割的评价指标：

- Dice/F1 和交并比（Intersection-over-Union，IoU），用于评价区域级分割准确性。
- 95% Hausdorff 距离（95% Hausdorff Distance，HD95），用于对分割边界进行敏感性评价。

**实现细节（Implementation Details）。**

我们遵循文献 [13, 14] 的实验方案，并采用相同的设置，包括：

使用 80%/20% 的随机训练集/验证集划分，在三个不同的随机数据种子下重复实验；固定训练 400 个 Epoch，不使用提前停止（Early Stopping）；根据验证集上的最佳 IoU 选择模型。

所有模型均使用 PyTorch 实现，并在单张具有 32 GB 显存的 NVIDIA A100 GPU 上进行训练。

为了验证 AD-GBC 模块的通用性，我们将其集成到两个骨干网络中：Rolling-UNet [14] 和 U-KAN [13]。

模型使用 Adam 优化器训练 400 个 Epoch，初始学习率设置为 $1\times10^{-4}$，批大小（Batch Size）为 8，而 GBC 参数采用单独的学习率 $1\times10^{-2}$。

我们将粒球数量设置为 $K=32$，并使特征维度 $D$ 与 $C_{in}$ 保持一致，而不使用额外的投影操作。

任务损失 $\mathcal{L}_{\text{task}}$ 由二元交叉熵（Binary Cross-Entropy，BCE）损失和 Dice 损失组合而成。

损失权重设置为：

$$
\lambda\in\{0.01,0.1\},
$$

用于 $\mathcal{L}_{\text{W-div}}$；

$$
\beta\in\{0.1,0.05\},
$$

用于 $\mathcal{L}_{\text{scale-con}}$。

## 4.1 性能比较（Performance Comparison）

**主要结果（Main Results）。**

我们针对当前最先进（State-of-the-Art，SOTA）的方法以及多个骨干网络进行了全面的定量评估。

结果分别列于表 2（各数据集上的性能）和表 3（计算效率与平均性能）。

这些结果表明了两个关键发现。

首先，如表 2 所示，我们的方法在四个数据集上均实现了极具竞争力的性能。

我们的完整模型（Rolling-UNet-L + AD-GBC）在 GlaS、CVC-ClinicDB 和 ISIC17 上取得了最佳结果，而 U-KAN + AD-GBC 变体在 BUSI 上取得了最高分数。

其次，我们的 AD-GBC 模块被证明是一种通用且有效的即插即用组件，其带来的性能提升具有一致性且十分明显。

例如，在 BUSI 数据集上，集成 AD-GBC 后，U-KAN 骨干网络的 IoU 获得了显著的 +4.10% 提升（65.76 → 69.86）。

**表 2. 在 BUSI、GlaS、CVC-ClinicDB 和 ISIC17 数据集上的定量比较。** 对于每个骨干网络，其下方一行报告了集成所提出的 AD-GBC 模块后的性能。结果为三次运行的平均值，并给出标准差。最佳结果以粗体表示。

| 方法 | BUSI [1] IoU↑ | BUSI [1] F1↑ | GlaS [22] IoU↑ | GlaS [22] F1↑ | CVC [4] IoU↑ | CVC [4] F1↑ | ISIC17 [7] IoU↑ | ISIC17 [7] F1↑ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| U-Net (2015) [20] | 64.75±1.41 | 77.43±1.30 | 87.26±0.67 | 92.82±0.56 | 83.88±0.73 | 91.15±0.35 | 77.38±0.51 | 87.19±0.33 |
| Att-UNet (2018) [18] | 66.36±1.65 | 79.22±1.55 | 86.98±1.71 | 92.89±0.89 | 84.70±0.47 | 91.55±0.25 | 76.24±0.23 | 86.53±0.10 |
| U-Net++ (2018) [31] | 66.51±1.88 | 79.34±1.78 | 87.74±0.72 | 92.96±0.49 | 84.52±1.44 | 91.50±0.87 | 78.72±1.01 | 86.20±0.76 |
| U-NeXt (2022) [23] | 61.47±1.51 | 74.67±1.03 | 84.18±0.71 | 91.55±0.75 | 74.58±0.27 | 85.21±0.18 | 82.16±0.06 | 90.07±0.11 |
| U-Mamba (2024) [17] | 65.89±2.98 | 78.55±3.02 | 87.48±0.42 | 93.02±0.33 | 84.35±0.63 | 91.63±0.37 | 81.23±0.32 | 89.33±0.42 |
| Rolling-UNet-S (2024) [14] | 65.38±2.96 | 78.34±2.19 | 86.05±0.49 | 92.71±0.07 | 82.87±1.40 | 90.48±0.85 | 82.14±1.33 | 90.22±0.90 |
| + AD-GBC | 65.62±0.79 | 79.08±0.51 | 86.55±0.08 | 92.78±0.04 | 84.90±0.86 | 91.76±0.50 | 84.90±0.10 | 91.67±0.04 |
| Rolling-UNet-M (2024) [14] | 66.41±1.19 | 79.02±0.83 | 85.86±1.56 | 92.55±0.73 | 84.93±0.65 | 91.71±0.44 | 83.51±0.50 | 90.67±0.33 |
| + AD-GBC | 67.36±0.97 | 80.42±0.70 | 88.16±0.25 | 93.70±0.14 | 87.07±0.86 | 93.04±0.50 | 84.88±0.09 | 91.64±0.04 |
| Rolling-UNet-L (2024) [14] | 67.85±1.76 | 80.22±1.14 | 87.99±0.31 | 93.47±0.29 | 85.77±0.40 | 92.11±0.23 | 84.10±0.38 | 91.10±0.21 |
| + AD-GBC | 69.30±0.83 | 81.69±0.54 | **89.37±0.12** | **94.38±0.06** | **87.45±0.68** | **93.25±0.40** | **84.95±0.08** | **91.72±0.08** |
| U-KAN (2025) [13] | 65.76±1.45 | 79.03±1.27 | 87.65±0.31 | 93.47±0.06 | 84.94±0.64 | 91.78±0.39 | 84.52±0.44 | 91.43±0.26 |
| + AD-GBC | **69.86±0.75** | **82.12±0.48** | 88.64±0.33 | 93.97±0.19 | 85.03±0.07 | 91.85±0.01 | 84.59±0.06 | 91.50±0.05 |

表 3 进一步表明，这种性能提升所需的额外成本很低。

AD-GBC 模块仅引入约 2% 的额外参数（约 0.15–0.6M），GFLOPs 仅增加约 15%–20%。

这证实了我们的方法实现了非常有利的精度与成本权衡（Accuracy-to-Cost Trade-Off），验证了各向异性粒球建模方法的效率。

**表 3. 计算效率与平均分割性能的比较。** 最佳结果以粗体表示。

| 方法 | 参数量（M）↓ | GFLOPs↓ | 平均 IoU↑ | 平均 F1↑ | IoU 增益（$\Delta$）↑ | F1 增益（$\Delta$）↑ |
|---|---:|---:|---:|---:|---:|---:|
| U-Net (2015) [20] | 31.04 | 524.2 | 78.32±0.83 | 87.15±0.64 | | |
| Att-UNet (2018) [18] | 34.88 | 533.1 | 78.57±1.02 | 87.55±0.70 | | |
| U-Net++ (2018) [31] | 36.63 | 1109.0 | 79.37±1.26 | 87.50±0.98 | | |
| U-NeXt (2022) [23] | **1.47** | **4.58** | 75.60±0.64 | 85.38±0.52 | | |
| U-Mamba (2024) [17] | 86.30 | 2087.0 | 79.74±1.09 | 88.13±1.04 | | |
| Rolling-UNet-S (2024) [14] | 1.78 | 16.82 | 79.11±1.55 | 87.94±1.00 | | |
| Rolling-UNet-S + AD-GBC | 1.82 | 19.91 | 80.49±0.46 | 88.82±0.27 | +1.38 | +0.88 |
| Rolling-UNet-M (2024) [14] | 7.10 | 66.25 | 80.18±0.98 | 88.49±0.58 | | |
| Rolling-UNet-M + AD-GBC | 7.25 | 77.27 | 81.87±0.54 | 89.70±0.35 | +1.69 | +1.21 |
| Rolling-UNet-L (2024) [14] | 28.32 | 262.96 | 81.43±0.71 | 89.23±0.47 | | |
| Rolling-UNet-L + AD-GBC | 28.92 | 304.32 | **82.77±0.43** | **90.26±0.27** | +1.34 | +1.04 |
| U-KAN (2025) [13] | 6.35 | 14.02 | 80.72±0.71 | 88.93±0.50 | | |
| U-KAN + AD-GBC | 6.51 | 16.77 | 82.03±0.30 | 89.86±0.18 | +1.31 | +0.93 |

图 5 为上述定量性能提升提供了定性证据。可视化结果突出表明，我们的模型能够处理研究动机（图 1）中提出的关键挑战，即模糊且不规则的边界。

更多定性示例见补充材料。

**基于锚点可视化的可解释性（Interpretability via Anchor Visualization）。**

图 6 将所选锚点的软分配结果可视化为热力图。

不同的锚点分别专注于不同的语义区域（例如病灶核心与健康皮肤），这证实了 AD-GBC 能够将特征空间分解为具有可解释性的区域组成部分。

> **图 5. BUSI 数据集中一个具有挑战性的样本上的定性比较。** 第一个子图为原始图像，绿色轮廓表示真实标注（Ground Truth）。在可视化的分割结果中，紫色表示过度分割（Over-Segmentation），黄色表示分割不足（Under-Segmentation）。

> **图 6. 所提出的 AD-GBC 模块在 ISIC17 上学习得到的代表性粒球锚点。**
>
> （a）原始图像与真实标注边界。
>
> （b）纹理感知锚点（Texture-Aware Anchor）。
>
> （c）边界敏感锚点（Boundary-Sensitive Anchor）。
>
> （d）背景抑制锚点（Background-Suppression Anchor）。

## 4.2 消融实验（Ablation Study）

为了验证 AD-GBC 模块的设计选择，我们在具有代表性的数据集（GlaS 和 BUSI）上开展了一系列全面的消融实验。

我们分析核心组件的贡献，以及模型对粒球数量 $K$ 的敏感性。

**核心组件与损失函数的影响（Impact of Core Components and Losses）。**

我们评估了 AD-GBC 三个关键组件的必要性，即各向异性尺度 $\boldsymbol{\sigma}_k$、多样性损失 $\mathcal{L}_{\text{W-div}}$ 和尺度一致性损失 $\mathcal{L}_{\text{scale-con}}$。实验结果如表 4 所示。

以 Rolling-UNet-L 基线模型（IoU 为 87.99%）为起点，引入采用各向同性（标量）尺度的 GBC 模块仅带来了微小的性能提升（+0.13%）。

将其替换为我们提出的各向异性（向量）尺度后，性能提高至 88.28%，表明对特征空间各向异性进行建模具有重要意义。

在这一各向异性基线的基础上，两种几何正则化方法均能够带来进一步的性能提升。

$\mathcal{L}_{\text{W-div}}$ 和 $\mathcal{L}_{\text{scale-con}}$ 分别将准确率提高至 88.70% 和 88.78%，凸显了它们在防止锚点塌缩和确保几何一致性方面的作用。

同时使用两种损失会产生明显的协同效应，使 IoU 达到 89.63%，构成我们的完整模型。

总体而言，各向异性尺度、多样性正则化和尺度一致性这三个组成部分对于 AD-GBC 的有效性都至关重要。

**表 4. 在 GlaS 数据集上对损失组件进行的消融实验。**

| 配置 | $\mathcal{L}_{\text{W-div}}$ | $\mathcal{L}_{\text{scale-con}}$ | IoU↑ | F1↑ | HD95↓ |
|---|:---:|:---:|---:|---:|---:|
| 基线（Rolling-UNet-L）[14] | × | × | 87.99 | 93.47 | 0.65 |
| + GBC（各向同性，标量 $\sigma_k$） | × | × | 88.12 | 93.67 | 0.63 |
| + GBC（各向异性，向量 $\boldsymbol{\sigma}_k$） | × | × | 88.28 | 93.88 | 0.59 |
| + GBC（各向异性，向量 $\boldsymbol{\sigma}_k$） | √ | × | 88.70 | 94.00 | 0.56 |
| + GBC（各向异性，向量 $\boldsymbol{\sigma}_k$） | × | √ | 88.78 | 94.05 | 0.56 |
| + GBC（各向异性，向量 $\boldsymbol{\sigma}_k$） | √ | √ | **89.63** | **94.51** | **0.51** |

**对 $K$、温度参数（$\tau$）和稀疏性的敏感性（Sensitivity to $K$, Temperature ($\tau$), and Sparsity）。**

表 5 分析了 AD-GBC 在 BUSI 数据集上对中心数量 $K$、温度参数 $\tau$ 以及稀疏性的敏感性。

对于适中的中心数量（$K=16$ 或 $32$），$\tau=1.0$ 表现最佳；而对于更大的 $K=64$，较小的温度参数（$\tau=0.01$）则更加有效。

这表明，当锚点集合变得密集时，较低的 $\tau$ 有助于使分配结果更加集中。

稀疏性同样能够改善性能，尤其是在 $K$ 较大时。

例如，当 $K=64$ 时，将分配限制为 Top-5 锚点能够获得高于 Top-10 的 IoU。

总体而言，$K=32$ 且 $\tau=1.0$ 提供了一种稳定的配置。

**表 5. BUSI 数据集上对温度参数 $\tau$ 和稀疏性（Top-5 / Top-10）的敏感性分析（IoU）。**

| 设置 | $K=16$ | $K=32$ | $K=64$ |
|---|---:|---:|---:|
| $\tau=0.01$ | 69.13 | 68.09 | 69.65 |
| $\tau=0.1$ | 66.76 | 69.90 | 69.16 |
| $\tau=1.0$ | 69.58 | **70.71** | 66.30 |
| Top-5 | 69.26 | 70.46 | 69.33 |
| Top-10 | 68.04 | 67.67 | 68.22 |

# 5 讨论（Discussion）

我们的实验结果表明，将原型重新定义为各向异性的有界几何区域，能够相较于各向同性建模方式带来明显的性能提升。

如表 4 所证实，引入各向异性尺度能够显著提高边界准确性（HD95 从 0.63 降至 0.59）。

然而，只有在得到适当稳定化的情况下，这种几何建模才能发挥有效作用：两种正则化方法 $\mathcal{L}_{\text{W-div}}$ 和 $\mathcal{L}_{\text{scale-con}}$ 具有协同效应，共同使 AD-GBC 发挥出完整性能（IoU 从 88.78% 提高至 89.63%）。

与高斯注意力（Gaussian Attention）[16] 和槽位注意力（Slot Attention）[10, 15] 不同，AD-GBC 显式建模有界的各向异性区域，并在像素与区域锚点之间执行共识更新。

此外，当前研究主要聚焦于基于卷积神经网络（Convolutional Neural Network，CNN）的编码器—解码器架构。

尽管 AD-GBC 模块完全可微，并且有可能通过像素—原型交互集成到基于 Transformer 的分割模型（例如 TransUNet [6] 或 Swin-UNet [5]）中，但这一方向仍有待未来研究探索。

# 致谢（Acknowledgments）

本研究得到中国澳门特别行政区科学技术发展基金（Science and Technology Development Fund, Macau SAR）的支持，项目编号为 0077/2025/RIA2 和 0008/2025/RIB1。

# 参考文献（References）

[1] Walaa Al-Dhabyani, Mohammed Gomaa, Hala Khaled, and Aly Fahmy.

**Dataset of breast ultrasound images.**

**中文译名：** 乳腺超声图像数据集。

Data in Brief（《数据简报》）, 28:104863, 2020.

原文引用页码：6, 7。

[2] Yu Ao, Weili Shi, Bai Ji, Yu Miao, Wei He, and Zhengang Jiang.

**MS-TCNet: An effective transformer-cnn combined network using multi-scale feature learning for 3d medical image segmentation.**

**中文译名：** MS-TCNet：一种利用多尺度特征学习进行三维医学图像分割的高效 Transformer-CNN 组合网络。

Computers in Biology and Medicine（《生物学与医学计算机》）, 170:108057, 2024.

原文引用页码：2。

[3] Reza Azad, Ehsan Khodapanah Aghdam, Amelie Rauland, Yiwei Jia, Atlas Haddadi Avval, Afshin Bozorgpour, Sanaz Karimijafarbigloo, Joseph Paul Cohen, Ehsan Adeli, and Dorit Merhof.

**Medical image segmentation review: The success of U-Net.**

**中文译名：** 医学图像分割综述：U-Net 的成功。

IEEE Transactions on Pattern Analysis and Machine Intelligence（IEEE《模式分析与机器智能汇刊》）, 46(12):10076–10095, 2024.

原文引用页码：1。

[4] Jorge Bernal, Francisco Javier Sánchez, Gloria Fernández-Esparrach, Debora Gil, Cristina Rodríguez, and Fernando Vilariño.

**Wm-dova maps for accurate polyp highlighting in colonoscopy: Validation vs. saliency maps from physicians.**

**中文译名：** 用于结肠镜检查中准确突出显示息肉的 Wm-dova 图：与医生生成的显著性图进行验证比较。

Computerized Medical Imaging and Graphics（《计算机化医学成像与图形学》）, 43:99–111, 2015.

原文引用页码：6, 7。

[5] Hu Cao, Yueyue Wang, Joy Chen, Dongsheng Jiang, Xiaopeng Zhang, Qi Tian, and Manning Wang.

**Swin-Unet: Unet-like pure transformer for medical image segmentation.**

**中文译名：** Swin-Unet：一种用于医学图像分割的类 UNet 纯 Transformer 网络。

In European Conference on Computer Vision（ECCV，欧洲计算机视觉会议）, pages 205–218. Springer, 2022.

原文引用页码：8。

[6] Jieneng Chen, Jieru Mei, Xianhang Li, Yongyi Lu, Qihang Yu, Qingyue Wei, Xiangde Luo, Yutong Xie, Ehsan Adeli, Yan Wang, Matthew P. Lungren, Shaoting Zhang, Lei Xing, Le Lu, Alan Yuille, and Yuyin Zhou.

**TransUNet: Rethinking the U-Net architecture design for medical image segmentation through the lens of transformers.**

**中文译名：** TransUNet：从 Transformer 的视角重新思考用于医学图像分割的 U-Net 架构设计。

Medical Image Analysis（《医学图像分析》）, 97:103280, 2024.

原文引用页码：8。

[7] Noel C. F. Codella, David Gutman, M. Emre Celebi, Brian Helba, Michael A. Marchetti, Stephen W. Dusza, Aadi Kalloo, Konstantinos Liopyris, Nabin Mishra, Harald Kittler, and Allan Halpern.

**Skin lesion analysis toward melanoma detection: A challenge at the 2017 international symposium on biomedical imaging (ISBI), hosted by the international skin imaging collaboration (ISIC).**

**中文译名：** 面向黑色素瘤检测的皮肤病灶分析：由国际皮肤影像协作组织（ISIC）在 2017 年国际生物医学成像研讨会（ISBI）上举办的挑战赛。

In International Symposium on Biomedical Imaging（ISBI，国际生物医学成像研讨会）, pages 168–172, 2018.

原文引用页码：6, 7。

[8] Pierre-Henri Conze, Gustavo Andrade-Miranda, Vivek Kumar Singh, Vincent Jaouen, and Dimitris Visvikis.

**Current and emerging trends in medical image segmentation with deep learning.**

**中文译名：** 基于深度学习的医学图像分割：当前趋势与新兴发展方向。

IEEE Transactions on Radiation and Plasma Medical Sciences（IEEE《辐射与等离子体医学科学汇刊》）, 7(6):545–569, 2023.

原文引用页码：1。

[9] Dawei Dai, Fan Chen, Shuyin Xia, Long Yang, Guan Wang, Guoyin Wang, and Xinbo Gao.

**An adaptive multi-granularity graph representation of image via granular-ball computing.**

**中文译名：** 基于粒球计算的图像自适应多粒度图表示。

IEEE Transactions on Image Processing（IEEE《图像处理汇刊》）, 34:2986–2999, 2025.

原文引用页码：2。

[10] Ke Fan, Zechen Bai, Tianjun Xiao, Tong He, Max Horn, Yanwei Fu, Francesco Locatello, and Zheng Zhang.

**Adaptive slot attention: Object discovery with dynamic slot number.**

**中文译名：** 自适应槽位注意力：利用动态槽位数量实现对象发现。

In IEEE Conference on Computer Vision and Pattern Recognition（CVPR，IEEE 计算机视觉与模式识别会议）, pages 23062–23071, 2024.

原文引用页码：1, 2, 8。

[11] Xianghong Fang, Jian Li, Qiang Sun, and Benyou Wang.

**Rethinking the uniformity metric in self-supervised learning.**

**中文译名：** 重新思考自监督学习中的均匀性度量。

In International Conference on Learning Representations（ICLR，国际学习表征会议）, 2024.

原文引用页码：5。

[12] Siyu Feng, Huaying Zhao, Fang Shi, Xiangyi Cheng, Mingzhi Wang, Yixiao Xiang, Dong Zhu, and Xin Chen.

**Cpfnet: Context pyramid fusion network for medical image segmentation.**

**中文译名：** CPFNet：用于医学图像分割的上下文金字塔融合网络。

IEEE Transactions on Medical Imaging（IEEE《医学成像汇刊》）, 39(9):3008–3018, 2020.

原文引用页码：2。

[13] Chenxin Li, Xinyu Liu, Wuyang Li, Cheng Wang, Hengyu Liu, Yifan Liu, Zhen Chen, and Yixuan Yuan.

**U-KAN makes strong backbone for medical image segmentation and generation.**

**中文译名：** U-KAN：为医学图像分割与生成提供强大的骨干网络。

In AAAI Conference on Artificial Intelligence（AAAI，人工智能促进协会年会）, pages 4652–4660, 2025.

原文引用页码：2, 6, 7。

[14] Yutong Liu, Haijiang Zhu, Mengting Liu, Huaiyuan Yu, Zihan Chen, and Jie Gao.

**Rolling-UNet: Revitalizing MLP’s ability to efficiently extract long-distance dependencies for medical image segmentation.**

**中文译名：** Rolling-UNet：重新激活 MLP 高效提取长距离依赖关系的能力以实现医学图像分割。

In AAAI Conference on Artificial Intelligence（AAAI，人工智能促进协会年会）, pages 3819–3827, 2024.

原文引用页码：2, 6, 7, 8。

[15] Francesco Locatello, Stefan Bauer, Mario Lucic, Gunnar Rätsch, Sylvain Gelly, Bernhard Schölkopf, and Olivier Bachem.

**Object-centric learning with slot attention.**

**中文译名：** 基于槽位注意力的以对象为中心的学习。

In Advances in Neural Information Processing Systems（NeurIPS，神经信息处理系统大会）, pages 11525–11538, 2020.

原文引用页码：1, 2, 8。

[16] Ao Luo, Fan Yang, Xin Li, Lang Nie, Chunyu Lin, Haoqiang Fan, and Shuaicheng Liu.

**GAFlow: Incorporating gaussian attention into optical flow.**

**中文译名：** GAFlow：将高斯注意力引入光流估计。

In International Conference on Computer Vision（ICCV，国际计算机视觉会议）, pages 9642–9651, 2023.

原文引用页码：2, 5, 8。

[17] Jun Ma, Feifei Li, and Bo Wang.

**U-mamba: Enhancing long-range dependency for biomedical image segmentation.**

**中文译名：** U-Mamba：增强生物医学图像分割中的长距离依赖关系。

arXiv preprint arXiv:2401.04722, 2024.

原文引用页码：7。

[18] Ozan Oktay, Jo Schlemper, Liangzhi Le, Mattias Heinrich, Kazunari Misawa, Kensaku Mori, Steven McDonagh, Nils Y. Hammerla, Bernhard Kainz, Ben Glocker, and Daniel Rueckert.

**Attention U-Net: Learning where to look for the pancreas.**

**中文译名：** Attention U-Net：学习在何处关注胰腺。

arXiv preprint arXiv:1804.03999, 2018.

原文引用页码：7。

[19] Ledan Qian, Caiyun Wen, Yi Li, Zhongyi Hu, Xiao Zhou, Xiaonyu Xia, and Soo-Hyung Kim.

**Multi-scale context UNet-like network with redesigned skip connections for medical image segmentation.**

**中文译名：** 一种用于医学图像分割的多尺度上下文类 UNet 网络：重新设计跳跃连接。

Computer Methods and Programs in Biomedicine（《生物医学计算机方法与程序》）, 243:107885, 2023.

原文引用页码：1, 2。

[20] Olaf Ronneberger, Philipp Fischer, and Thomas Brox.

**U-net: Convolutional networks for biomedical image segmentation.**

**中文译名：** U-Net：用于生物医学图像分割的卷积网络。

In Medical Image Computing and Computer-Assisted Intervention（MICCAI，医学图像计算与计算机辅助干预国际会议）, pages 234–241, 2015.

原文引用页码：2, 3, 7。

[21] Nafisa Siddique, Sajib Paheding, Craig Elkin, and Venkatakrishna Devabhaktuni.

**U-Net and its variants for medical image segmentation: A review of theory and applications.**

**中文译名：** 用于医学图像分割的 U-Net 及其变体：理论与应用综述。

IEEE Access（IEEE《开放获取期刊》）, 9:82031–82057, 2020.

原文引用页码：1。

[22] Khunarnon Sirinukunwattana, Josien P. W. Pluim, Ejaz Ahmed, and Nasir M. Rajpoot.

**Gland segmentation in colon histology images: The GlaS challenge contest.**

**中文译名：** 结肠组织学图像中的腺体分割：GlaS 挑战赛。

In Medical Image Computing and Computer-Assisted Intervention（MICCAI，医学图像计算与计算机辅助干预国际会议）, pages 369–377, 2017.

原文引用页码：6, 7。

[23] Jeya Maria Jose Valanarasu and Vishal M. Patel.

**UNeXt: MLP-based rapid medical image segmentation network.**

**中文译名：** UNeXt：一种基于 MLP 的快速医学图像分割网络。

In Medical Image Computing and Computer-Assisted Intervention（MICCAI，医学图像计算与计算机辅助干预国际会议）, pages 23–33, 2022.

原文引用页码：7。

[24] Haonan Wang, Peng Cao, Jinzhu Yang, and Osmar Ramon Zaiane.

**Narrowing the semantic gaps in U-Net with learnable skip connections: The case of medical image segmentation.**

**中文译名：** 通过可学习跳跃连接缩小 U-Net 中的语义差距：以医学图像分割为例。

Neural Networks（《神经网络》）, 178:106546, 2024.

原文引用页码：1。

[25] Xiang Wang, Zhen Li, Yulan Huang, and Yanjun Jiao.

**Multimodal medical image segmentation using multi-scale context-aware network.**

**中文译名：** 使用多尺度上下文感知网络进行多模态医学图像分割。

Neurocomputing（《神经计算》）, 486:135–146, 2021.

原文引用页码：2。

[26] YongChao Wang, Bin Xiao, Xiuli Bi, Weisheng Li, and Xinbo Gao.

**Boundary-aware prototype in semi-supervised medical image segmentation.**

**中文译名：** 半监督医学图像分割中的边界感知原型。

IEEE Transactions on Image Processing（IEEE《图像处理汇刊》）, 33:5456–5467, 2024.

原文引用页码：1, 2。

[27] Shuyin Xia, Xiaochuan Dai, Guoyin Wang, Xinbo Gao, and Elisabeth Giem.

**An efficient and adaptive granular-ball generation method in classification problem.**

**中文译名：** 一种用于分类问题的高效自适应粒球生成方法。

IEEE Transactions on Neural Networks and Learning Systems（IEEE《神经网络与学习系统汇刊》）, 35:5319–5331, 2022.

原文引用页码：2。

[28] Shuyin Xia, Guoyin Wang, Xinbo Gao, and Xiaoyu Lian.

**Granular-ball computing: an efficient, robust, and interpretable adaptive multi-granularity representation and computation method.**

**中文译名：** 粒球计算：一种高效、鲁棒且可解释的自适应多粒度表示与计算方法。

arXiv preprint arXiv:2304.11171, 2023.

原文引用页码：2。

[29] Jiang Xie, Weiyu Kong, Shuyin Xia, Guoyin Wang, and Xinbo Gao.

**An efficient spectral clustering algorithm based on granular-ball.**

**中文译名：** 一种基于粒球的高效谱聚类算法。

IEEE Transactions on Knowledge and Data Engineering（IEEE《知识与数据工程汇刊》）, 35(9):9743–9753, 2023.

原文引用页码：2。

[30] Tianfei Zhou and Wenguan Wang.

**Prototype-based semantic segmentation.**

**中文译名：** 基于原型的语义分割。

IEEE Transactions on Pattern Analysis and Machine Intelligence（IEEE《模式分析与机器智能汇刊》）, 46(10):6858–6872, 2024.

原文引用页码：2。

[31] Zongwei Zhou, Md Mahfuzur Rahman Siddiquee, Nima Tajbakhsh, and Jianming Liang.

**UNet++: A nested U-Net architecture for medical image segmentation.**

**中文译名：** UNet++：一种用于医学图像分割的嵌套式 U-Net 架构。

In International Workshop on Deep Learning in Medical Image Analysis（医学图像分析深度学习国际研讨会）, pages 3–11. Springer, 2018.

原文引用页码：2, 7。

[32] Zongwei Zhou, Md Mahfuzur Rahman Siddiquee, Nima Tajbakhsh, and Jianming Liang.

**UNet++: Redesigning skip connections to exploit multiscale features in image segmentation.**

**中文译名：** UNet++：重新设计跳跃连接以利用图像分割中的多尺度特征。

IEEE Transactions on Medical Imaging（IEEE《医学成像汇刊》）, 39(6):1856–1867, 2020.

原文引用页码：2。

# AD-GBC：一种用于基于 UNet 的医学图像分割的各向异性粒球跳跃连接优化模块

**英文标题：** AD-GBC: Anisotropic Granular-Ball Skip-Connection Refiner for UNet-Based Medical Image Segmentation

**补充材料（Supplementary Material）**

# 6 多模态病灶特征的证据（Evidence of Multi-Mode Lesion Features）

为了支持引言中的论述，即“单个语义类别（例如病灶）在特征空间中通常并非单一簇，而是呈现多模态分布”，我们基于 AD-GBC 模块之前提取的编码器特征，提供了额外的可视化结果。

我们从 ISIC17 数据集中随机采样了 5 张图像及其对应的分割掩码。对于每张图像，我们在像素级提取编码器特征，并利用分割掩码区分病灶区域和背景区域。随后，我们进一步随机采样其中 50% 的像素用于可视化。

这些编码器特征经过展平处理，并使用 t 分布随机邻域嵌入（t-distributed Stochastic Neighbor Embedding，T-SNE）投影到二维空间。

如图 7 所示，病灶像素并未形成单个紧凑的特征簇，而是分裂为多个不同的模态，每种模态对应不同的视觉外观，例如深色核心区域、发炎边界或平滑的病灶区域。

这种多模态行为为我们使用 AD-GBC 进行几何区域建模提供了有力的动机。

> **图 7. 在 AD-GBC 之前提取的编码器特征的 T-SNE 可视化。**
>
> （a）背景特征与病灶特征（Background vs. Lesion Encoder Features）。
>
> （b）仅对病灶特征进行聚类，显示出三个不同的模态（黑色“×”标记表示聚类中心）。

# 7 定理 1 的证明（Proof of Theorem 1）

**证明（Proof）。**

设 $\mathbf{C}\in\mathbb{R}^{K\times D}$ 为一组非零中心，$\mathbf{G}(\mathbf{C})\in\mathbb{R}^{K\times K}$ 为其归一化 Gram 矩阵，即：

$$
\mathbf{G}(\mathbf{C})_{ij}
=
\frac{
\mathbf{c}_i^\top\mathbf{c}_j
}{
\|\mathbf{c}_i\|_2
\|\mathbf{c}_j\|_2
},
\quad
i,j=1,\ldots,K.
$$

根据构造方式，$\mathbf{G}(\mathbf{C})$ 是一个对称半正定矩阵，并且对于所有 $i$，都有：

$$
\mathbf{G}(\mathbf{C})_{ii}=1,
$$

因为它是由单位向量构成的 Gram 矩阵。

假设：

$$
\operatorname{rank}(\mathbf{G}(\mathbf{C}))=r<K.
$$

由于 $\mathbf{G}(\mathbf{C})$ 是一个秩为 $r$ 的对称半正定矩阵，因此它存在如下分解：

$$
\mathbf{G}(\mathbf{C})
=
\mathbf{B}\mathbf{B}^\top,
$$

其中，$\mathbf{B}\in\mathbb{R}^{K\times r}$，且：

$$
\operatorname{rank}(\mathbf{B})=r.
$$

例如，可以取 $\mathbf{G}(\mathbf{C})$ 的前 $r$ 个特征向量，以及对应特征值的平方根来构造这一分解。

令 $\mathbf{b}_i^\top$ 表示 $\mathbf{B}$ 的第 $i$ 行。

那么，$\mathbf{G}(\mathbf{C})$ 的第 $(i,i)$ 个元素满足：

$$
\mathbf{G}(\mathbf{C})_{ii}
=
\left(
\mathbf{B}\mathbf{B}^\top
\right)_{ii}
=
\mathbf{b}_i^\top\mathbf{b}_i
=
\|\mathbf{b}_i\|_2^2.
$$

由于对于所有 $i$ 都有：

$$
\mathbf{G}(\mathbf{C})_{ii}=1,
$$

因此，对于每个 $i=1,\ldots,K$，可得：

$$
\|\mathbf{b}_i\|_2=1.
$$

因此，$\mathbf{B}$ 的每一行都是 $\mathbb{R}^{r}$ 中的单位向量。

现在定义：

$$
\widetilde{\mathbf{C}}
:=
\mathbf{B}
\in
\mathbb{R}^{K\times r},
$$

并将其第 $i$ 行表示为 $\tilde{\mathbf{c}}_i^\top$。

由于 $\widetilde{\mathbf{C}}$ 的所有行均具有单位范数，因此其归一化 Gram 矩阵可以直接表示为：

$$
\begin{aligned}
\mathbf{G}(\widetilde{\mathbf{C}})_{ij}
&=
\tilde{\mathbf{c}}_i^\top
\tilde{\mathbf{c}}_j\\
&=
\mathbf{b}_i^\top\mathbf{b}_j\\
&=
\left(
\mathbf{B}\mathbf{B}^\top
\right)_{ij}\\
&=
\mathbf{G}(\mathbf{C})_{ij}.
\end{aligned}
$$

上述等式对于所有 $i,j$ 均成立。

因此：

$$
\mathbf{G}(\widetilde{\mathbf{C}})
=
\mathbf{G}(\mathbf{C}).
$$

根据假设，余弦多样性损失（Cosine Diversity Loss）仅通过中心的归一化 Gram 矩阵依赖于这些中心。

也就是说，存在一个函数：

$$
\Phi:
\mathbb{R}^{K\times K}
\rightarrow
\mathbb{R},
$$

使得：

$$
\mathcal{L}_{\text{cos-div}}(\mathbf{C})
=
\Phi\left(
\mathbf{G}(\mathbf{C})
\right).
$$

利用：

$$
\mathbf{G}(\widetilde{\mathbf{C}})
=
\mathbf{G}(\mathbf{C}),
$$

可得：

$$
\begin{aligned}
\mathcal{L}_{\text{cos-div}}
(\widetilde{\mathbf{C}})
&=
\Phi\left(
\mathbf{G}(\widetilde{\mathbf{C}})
\right)\\
&=
\Phi\left(
\mathbf{G}(\mathbf{C})
\right)\\
&=
\mathcal{L}_{\text{cos-div}}
(\mathbf{C}).
\end{aligned}
$$

因此，只要：

$$
\operatorname{rank}
\left(
\mathbf{G}(\mathbf{C})
\right)
=
r<K,
$$

就存在一个位于 $r$ 维子空间中的：

$$
\widetilde{\mathbf{C}}
\in
\mathbb{R}^{K\times r},
$$

使其产生完全相同的归一化 Gram 矩阵，以及相同的余弦多样性损失值。

$\square$

# 8 Wasserstein 均匀性损失在秩约束下的最小化解证明（Proof of the Rank-Constrained Minimizer of the Wasserstein Uniformity Loss）

在正文中，我们指出 Wasserstein 均匀性损失 $\mathcal{L}_{\text{W-div}}$ 直接作用于协方差矩阵 $\hat{\Sigma}_C$。

受到 Fang 等人 [11] 所提出公式的启发，我们在此给出一个自包含的推导，并使其适用于经验协方差的情形。

在这种情况下，$\hat{\Sigma}_C$ 由有限数量的样本构建，因此受到秩约束。

**定理 2（秩约束下的最小化解，Rank-Constrained Minimizer）。**

设：

$$
\hat{\mu}_C\in\mathbb{R}^{D}
$$

和：

$$
\hat{\Sigma}_C\in\mathbb{R}^{D\times D}
$$

分别表示由 $K$ 个样本构建的中心经验均值和经验协方差矩阵。

令：

$$
\lambda_1,\ldots,\lambda_D\geq0
$$

为 $\hat{\Sigma}_C$ 的特征值，并定义：

$$
r:=\min(D,K-1).
$$

考虑 Wasserstein 均匀性损失：

$$
\mathcal{L}_{\text{W-div}}
=
\|\hat{\mu}_C\|_2^2
+
\operatorname{tr}(\hat{\Sigma}_C)
-
\frac{2}{\sqrt{D}}
\operatorname{tr}
\left(
\hat{\Sigma}_C^{1/2}
\right).
$$

那么，该损失在可行集合上的最小值于以下条件下取得：

$$
\hat{\mu}_C=\mathbf{0},
\quad
\lambda_1=\cdots=\lambda_r=\frac{1}{D},
\quad
\lambda_{r+1}=\cdots=\lambda_D=0.
$$

**证明（Proof）。**

由于 $\hat{\Sigma}_C$ 是对称半正定矩阵，因此其所有特征值均满足：

$$
\lambda_k\geq0,
\quad
k=1,\ldots,D.
$$

此外，由于 $\hat{\Sigma}_C$ 由 $K$ 个样本构建，其秩受到以下约束：

$$
m:=
\operatorname{rank}(\hat{\Sigma}_C)
\leq
r:=
\min(D,K-1).
$$

不失一般性，我们可以假设前 $m$ 个特征值严格大于零，而其余 $D-m$ 个特征值均为零。

根据谱计算（Spectral Calculus），迹运算（Trace Operations）仅依赖于这 $m$ 个非零特征值：

$$
\operatorname{tr}(\hat{\Sigma}_C)
=
\sum_{k=1}^{m}\lambda_k,
\qquad
\operatorname{tr}
\left(
\hat{\Sigma}_C^{1/2}
\right)
=
\sum_{k=1}^{m}\sqrt{\lambda_k}.
$$

因此，该损失可以重写为对这 $m$ 个特征值的求和：

$$
\mathcal{L}_{\text{W-div}}
=
\|\hat{\mu}_C\|_2^2
+
\sum_{k=1}^{m}
\left(
\lambda_k
-
\frac{2}{\sqrt{D}}
\sqrt{\lambda_k}
\right).
$$

对于每个：

$$
k\in\{1,\ldots,m\},
$$

定义：

$$
x_k:=\sqrt{\lambda_k}>0.
$$

通过配方（Completing the Square），可得：

$$
\begin{aligned}
\lambda_k
-
\frac{2}{\sqrt{D}}
\sqrt{\lambda_k}
&=
x_k^2
-
\frac{2}{\sqrt{D}}x_k\\
&=
\left(
x_k-\frac{1}{\sqrt{D}}
\right)^2
-
\frac{1}{D}.
\end{aligned}
$$

将这一恒等式代入损失函数，得到：

$$
\mathcal{L}_{\text{W-div}}
=
\|\hat{\mu}_C\|_2^2
+
\sum_{k=1}^{m}
\left(
x_k-\frac{1}{\sqrt{D}}
\right)^2
-
\frac{m}{D}.
$$

对于任意可行的 $\hat{\Sigma}_C$，前两项均为非负项之和。

为了使整体损失最小化，我们必须使被减去的项：

$$
\frac{m}{D}
$$

尽可能大。

这要求将秩 $m$ 最大化至其上界 $r$。

因此，当满足以下条件时，可行集合上的全局最小值能够取得：

$$
\hat{\mu}_C=\mathbf{0},
\qquad
m=r,
\qquad
x_k=\frac{1}{\sqrt{D}},
\quad
\text{对于所有 }k=1,\ldots,r.
$$

等价地：

$$
\lambda_1
=
\cdots
=
\lambda_r
=
\frac{1}{D},
\qquad
\lambda_{r+1}
=
\cdots
=
\lambda_D
=
0.
$$

因此，当可行秩达到其最大值 $r$，并且所有非零特征值均等于 $1/D$ 时，损失函数取得最小值。

这对应于可行的 $r$ 维子空间内一种谱均匀分布（Spectrally Uniform Distribution），能够促进形成分布充分分散的中心集合，同时不会与单个区域的各向异性建模相矛盾。

# 9 AD-GBC 模块的详细复杂度与效率比较（Detailed Complexity and Efficiency Comparison of the AD-GBC Module）

我们对正文第 3.5 节所给出的复杂度分析进行详细分解。

设输入特征图的形状为：

$$
B\times C_{in}\times H\times W,
$$

其中，像素数量为：

$$
N=H\times W,
$$

粒球数量为 $K$，投影维度为 $D$。

在本次分析中，我们假设 $B=1$，因为 FLOPs 随批大小线性增长。

## 9.1 计算复杂度（Computational Complexity，FLOPs）

我们对前向传播各步骤的 FLOPs 进行求和，具体过程如正文图 2 所示。

**1）投影层（Projection Layers，$f_{\text{proj}}$、$\tilde{f}_{\text{proj}}$）**

初始 $1\times1$ 卷积：

$$
C_{in}\rightarrow D
$$

需要：

$$
\mathcal{O}(N\cdot C_{in}\cdot D)
$$

次浮点运算。

最终的 $1\times1$ 卷积：

$$
D\rightarrow C_{in}
$$

同样需要：

$$
\mathcal{O}(N\cdot D\cdot C_{in})
$$

次浮点运算。

因此，投影层的总计算成本为：

$$
\mathcal{O}(N\cdot C_{in}\cdot D).
$$

**2）D-GBC 核心交互（D-GBC Core Interaction）**

这是模块的主要组成部分。

**（1）尺度化距离（Scaled Distance，$d_{i,k}$）**

计算尺度化欧氏距离的平方：

$$
\left\|
(\mathbf{z}_i-\mathbf{c}_k)
\oslash
\boldsymbol{\sigma}_k
\right\|_2^2.
$$

该操作需要将全部 $N$ 个像素分别与 $K$ 个粒球进行比较，其中每个特征具有 $D$ 个维度。

计算涉及减法、除法、平方和求和操作，因此产生：

$$
\mathcal{O}(N\cdot K\cdot D)
$$

次浮点运算。

**（2）Softmax（$\alpha_{i,k}$）**

对大小为：

$$
N\times K
$$

的距离矩阵进行归一化，需要：

$$
\mathcal{O}(N\cdot K)
$$

次运算。

与复杂度为：

$$
\mathcal{O}(N\cdot K\cdot D)
$$

的步骤相比，这一成本可以忽略不计。

**（3）聚合（Aggregation，Set→Ball，$\mathbf{c}'_k$）**

聚合过程是一个加权求和：

$$
\sum_i\alpha_{i,k}\mathbf{z}_i.
$$

该操作等价于矩阵乘法：

$$
\boldsymbol{\alpha}^\top\mathbf{Z},
$$

其中，矩阵的维度分别为：

$$
\mathbb{R}^{K\times N}
\times
\mathbb{R}^{N\times D}.
$$

因此，该步骤需要：

$$
\mathcal{O}(N\cdot K\cdot D)
$$

次浮点运算。

**（4）广播（Broadcast，Ball→Set，$\hat{\mathbf{z}}_i$）**

广播过程同样是一个加权求和：

$$
\sum_k\alpha_{i,k}\mathbf{c}'_k.
$$

该操作等价于矩阵乘法：

$$
\boldsymbol{\alpha}\mathbf{C}',
$$

其中，矩阵维度分别为：

$$
\mathbb{R}^{N\times K}
\times
\mathbb{R}^{K\times D}.
$$

因此，该步骤也需要：

$$
\mathcal{O}(N\cdot K\cdot D)
$$

次浮点运算。

综上，核心交互过程的总复杂度为：

$$
\mathcal{O}(N\cdot K\cdot D).
$$

**3）细化块（Refinement Block，$f_{\text{refine}}$）**

$3\times3$ 深度卷积（Depthwise Convolution）：

$$
C_{in}\rightarrow C_{in}
$$

所需的 FLOPs 与输出大小：

$$
N\cdot C_{in}
$$

以及卷积核运算：

$$
C_{in}\cdot3\cdot3
$$

成正比。

这产生：

$$
\mathcal{O}(N\cdot C_{in}^2)
$$

次浮点运算。

将上述组件的计算成本相加，得到总计算复杂度：

$$
\begin{aligned}
&\mathcal{O}\left(
N\cdot C_{in}\cdot D
+
N\cdot K\cdot D
+
N\cdot C_{in}^2
\right)\\
&=
\mathcal{O}\left(
N\cdot
(C_{in}D+KD+C_{in}^2)
\right).
\end{aligned}
$$

由于 $C_{in}$、$K$ 和 $D$ 均为固定的超参数，因此模块的计算成本随像素数量 $N$ 线性增长。

## 9.2 参数复杂度（Parameter Complexity）

**1）粒球锚点（GB Anchors）**

$K$ 个中心：

$$
\mathbf{c}_k\in\mathbb{R}^{D}
$$

以及 $K$ 个各向异性尺度：

$$
\boldsymbol{\sigma}_k\in\mathbb{R}^{D}
$$

共需要：

$$
K\cdot D+K\cdot D=2KD
$$

个参数。

**2）可选投影层（Optional Projection Layers）**

前向投影层 $f_{\text{proj}}$ 由以下结构组成：

$$
1\times1\ \text{Conv}
\ (C_{in}\rightarrow D)
+
\text{BN}.
$$

该结构使用：

$$
C_{in}D
$$

个卷积权重，以及：

$$
2D
$$

个 BN 参数。

反向投影层使用：

$$
DC_{in}
$$

个卷积权重，以及：

$$
2C_{in}
$$

个 BN 参数。

**3）细化块（Refinement Block）**

细化块 $f_{\text{refine}}$ 由以下结构组成：

$$
3\times3\ \text{Conv}
\ (C_{in}\rightarrow C_{in})
+
\text{BN}.
$$

该结构需要：

$$
C_{in}\cdot C_{in}\cdot9
$$

个卷积权重，以及来自 BN 的：

$$
2C_{in}
$$

个参数（缩放参数和偏移参数）。

因此，总参数数量为：

$$
\mathcal{O}
\left(
KD+C_{in}D+C_{in}^2
\right).
$$

一旦超参数确定，参数数量便保持固定，不会随 $N$ 增长。

# 10 额外的可视化与诊断分析（Additional Visualizations and Diagnostic Analyses）

## 10.1 扩展定性比较（Extended Qualitative Comparisons）

本节提供扩展的定性比较，以补充主论文中的实验内容。

图 8 以逐行排列的方式展示了四个数据集上更多的可视化示例：

- BUSI（乳腺超声，Breast Ultrasound）。
- GlaS（结肠组织学，Colon Histology）。
- CVC-ClinicDB（结肠镜成像，Colonoscopy）。
- ISIC17（皮肤镜成像，Dermoscopy）。

BUSI 数据集的可视化结果也已在主论文中展示（图 5）；在此，我们进一步纳入另外三个数据集，以更全面地评估所提出方法的通用性。

对于每个数据集，我们首先展示带有真实标注（Ground Truth，GT）轮廓的输入图像，随后展示七种竞争方法的预测结果。

这些扩展示例进一步验证了主论文报告的研究发现：AD-GBC 模块能够提供更加稳定、具有几何感知能力的区域建模，从而在不同医学成像模态下产生明显更加准确和一致的分割边界。

在所有数据集上，配备所提出 AD-GBC 模块的模型，在模糊或不规则边界处表现出持续减少的紫色和黄色区域带，这表明过度分割和分割不足的伪影更少。

相比之下，未采用 AD-GBC 的基线模型经常产生锯齿状、不完整或过度扩张的轮廓。

这种现象在低对比度图像（BUSI）、紧密排列的腺体结构（GlaS）、细长的息肉结构（CVC-ClinicDB）或模糊的病灶边界（ISIC17）等情况下尤为明显。

> **图 8. 跨数据集的额外定性比较。**
>
> 从上到下依次为 BUSI、GlaS、CVC-ClinicDB 和 ISIC17 数据集。
>
> 第一列为原始图像，其中绿色轮廓表示真实标注（Ground Truth）。
>
> 在可视化的分割结果中，紫色表示过度分割（Over-Segmentation），黄色表示分割不足（Under-Segmentation）。

## 10.2 AD-GBC 中心激活的诊断可视化（Diagnostic Visualization of AD-GBC Center Activations）

图 9 展示了针对一张具有代表性的 ISIC17 图像，所有学习得到的 AD-GBC 中心（$K=32$）的诊断可视化结果。

这些激活图并不用于定性比较，而是用于对 AD-GBC 模块所学习到的激活模式进行内部检查。

需要注意的是，这些中心并不是为了单独形成具有可解释性的“组成部分”（Parts）而设计的。

由于 AD-GBC 模块采用软分配加权和多区域聚合，因此大多数中心专注于子区域或中间特征模式，而不是形成完整的语义形状。

因此，只有一部分中心表现出与病灶明显对齐的响应，而其他中心则突出纹理、颜色变化或过渡性边界结构。

这种行为符合预期，并且与我们的多中心设计相一致。

这些可视化结果仅用于展示中心响应的多样性和专门化特征。

最终的分割质量来源于所有中心的联合聚合，而不是任何单个激活图的可解释性。

因此，尽管单个中心可能呈现出噪声较多或仅覆盖局部区域的响应，但它们的组合效果能够产生主论文中所展示的稳定且具有几何感知能力的分割边界。

> **图 9. 一张具有代表性的 ISIC17 图像中全部 32 个 AD-GBC 中心的诊断可视化。**
>
> 第一列展示了原始图像及其真实标注边界，随后依次展示所有 AD-GBC 中心的激活图。
>
> 这些可视化结果用于诊断分析，并使展示内容更加完整。