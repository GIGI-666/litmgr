# DocLayout-YOLO：采用网格引导合成预训练的轴向注意力文档版面检测器

DocLayout-YOLO: Axis-Attentive Document Layout Detector with Mesh-Guided Synthetic Pretraining

## 论文正文

作者：Zhiyuan Zhao、Hengrui Kang、Guang Liang、Bin Wang、Conghui He

机构：上海人工智能实验室（Shanghai AI Laboratory）

arXiv:2610.28171v1 [cs.CV]，2026 年 10 月 20 日。

**图 1：** 在 M6Doc 上，与主流实时检测器在延迟与精度（左）、FLOPs 与精度（右）权衡方面的比较。

### 摘要

准确且高效的文档版面分析对现代文档解析系统至关重要。然而，尽管 YOLO 框架是实时检测器的主流范式，其对异构文档的适配仍未得到充分探索。为填补这一空白，我们提出 DocLayout-YOLO，这是一种面向文档的专用实时检测器，融合了多样化合成文档预训练与页面轴向上下文建模。从数据角度，我们引入 MeshLayout-1M，这是使用所提出的网格候选最佳适配（Mesh-candidate BestFit）算法生成的合成预训练语料库，能够提供大规模、多样化的文档版面以进行预训练，并改善对异构文档场景的适应能力。从模型角度，我们提出页面轴向版面注意力（Page-Axis Layout Attention，PALA），沿页面水平轴和垂直轴捕获长程依赖，同时保持较高的计算效率。大量实验表明，DocLayout-YOLO 在四个异构文档基准上取得了最先进的性能，在 D4LA、M6Doc、HJDataset 和 PRIMA-LAD 上分别达到 72.4%/75.5%/96.0%/73.1% 的 $\mathrm{mAP}_{50:95}$。与现有实时检测器相比，DocLayout-YOLO 在文档版面分析中实现了更优的精度与效率权衡。代码、模型和数据可在 https://github.com/opendatalab/DocLayout-YOLO/tree/release-v2 获取。

### 1 引言

文档版面分析（Document Layout Analysis，DLA）（Zhong et al., 2019; Pfitzmann et al., 2022; Cheng et al., 2023）旨在定位文本、表格和图像等语义区域并对其分类，为文档解析和理解提供必要的结构信息（Wang et al., 2026; Cui et al., 2026; Li et al., 2026; Yu et al., 2026）。随着大语言模型（large language models，LLMs）（OpenAI, 2023; Yang et al., 2025）与检索增强生成（retrieval-augmented generation，RAG）（Yu et al., 2025; Cho et al., 2024; Chen et al., 2025）的快速发展，对高质量结构化文档数据的需求大幅增长，要求实时文档检测器同时具备更高的准确性和效率。

在现有实时目标检测器中，YOLO 系列（Jocher et al., 2026; Tian et al., 2025; Jocher et al., 2023）在精度与效率之间取得了良好平衡，但其在文档版面分析中的潜力仍未得到充分探索。然而，将 YOLO 检测器适配到文档场景并非易事，主要面临两个关键挑战。在数据层面，将检测器适配到文档场景需要有效的文档领域预训练，这依赖于规模大、结构多样且覆盖丰富版面变化的语料库。然而，现有数据集在数据规模、版面多样性、标注质量等方面存在权衡（如表 1 所示），而构建具有细粒度版面标注的大规模文档语料库仍然代价高昂（Zhong et al., 2019; Li et al., 2020）。在模型层面，准确定位文档元素需要有效的结构上下文建模，因为文档版面在文本行、段落栏、表格网格以及图像与图注对之间存在复杂的长程依赖（Wang et al., 2024b; Da et al., 2023）。然而，传统的卷积式 YOLO 架构缺少捕获这些依赖的显式机制，而 YOLOv12（Tian et al., 2025）近期引入的区域注意力（Area Attention）主要面向高效的通用视觉建模设计，并未显式利用文档页面的水平与垂直组织结构。

为应对这些挑战，我们提出 DocLayout-YOLO，一种面向文档的专用实时检测器，通过多样化合成文档预训练与页面轴向上下文建模提升检测性能。在数据层面，我们引入 MeshLayout-1M，这是基于二维装箱（2D Bin-packing）（Lodi et al., 2002）原理、由所提出的 Mesh-candidate BestFit 算法生成的大规模合成预训练数据集。通过合成在元素、尺度和版面结构方面具有变化的多样化文档版面，MeshLayout-1M 提供了更多样的预训练语料，使模型能够更好地适应异构文档场景。

在模型层面，我们提出 PALA，显式捕获文档页面水平轴与垂直轴上的长程依赖。通过利用页面的固有结构，PALA 能够高效聚合版面元素之间的上下文，同时避免全局注意力带来的计算开销。结合结构多样的合成预训练与页面轴向上下文建模，DocLayout-YOLO 取得了良好的精度与效率权衡，如图 1 所示。本文的贡献总结如下：

- 我们引入 MeshLayout-1M，这是通过所提出的 Mesh-candidate BestFit 算法生成的结构多样化合成预训练数据集，支持具有多样元素和版面组织的大规模文档领域预训练。
- 我们提出 PALA，这是一种高效的上下文建模机制，沿页面水平轴与垂直轴捕获长程依赖，在保持高效计算的同时显式利用文档版面固有的结构组织。
- 我们提出 DocLayout-YOLO，一种融合合成版面预训练与页面轴向上下文建模的文档专用实时检测器。该方法在四个异构基准上取得最先进的性能，并相较现有实时检测器实现了更优的精度与效率权衡。

### 2 相关工作

#### 2.1 文档版面分析数据集

当前文档数据集总结于表 1。现有数据集通过提供大规模标注，例如 PubLayNet（Zhong et al., 2019）和 DocBank（Li et al., 2020），或提供多样的文档类型及细粒度类别，例如 DocLayNet（Pfitzmann et al., 2022）、D4LA（Da et al., 2023）和 M6Doc（Cheng et al., 2023），推动了文档版面分析的发展。然而，现有数据集在规模、版面多样性、元素覆盖或标注成本方面仍存在局限。与此同时，现有文档生成方法（Zhang et al., 2023b; Inoue et al., 2023; Hui et al., 2023; Jiang et al., 2023; Kong et al., 2022; Gupta et al., 2021）主要关注学术风格版面，限制了其支持多样化文档领域预训练的能力。

#### 2.2 文档版面分析方法

现有 DLA 方法大体可分为多模态方法与单模态方法。多模态方法，例如 LayoutLMv3（Huang et al., 2022）、VGT（Da et al., 2023）、近期的 M2Doc（Zhang et al., 2024）与 DoPTA-HR（R. et al., 2024），通过利用文本与视觉的交互提升性能。相比之下，单模态方法（Shen et al., 2021; Banerjee et al., 2023; 2024a; Biswas et al., 2022; Li et al., 2022; Chen et al., 2024b）主要依赖视觉特征和通用检测架构。然而，这些方法要么引入额外的多模态复杂性，要么缺乏对文档特有结构依赖的显式建模。对于实时检测器，近期基于 YOLO 的实时检测器（Jocher et al., 2023; Wang et al., 2024a; Tian et al., 2025; Jocher et al., 2026）通过检测架构和注意力机制的进展，在精度与效率之间取得了良好平衡。然而，它们主要针对自然图像优化，并未显式利用文档版面的结构特征。

**表 1：现有文档预训练数据集的比较。**

| 数据集 | 页数 | 元素数 | 元素类型数 | 版面多样性 | 标注类型 |
|---|---:|---:|---:|---|---|
| IIT-CDIP（Lewis et al., 2006） | 42M | -（无） | -（无） | 11（多样） | 未标注 |
| PRIMA-LAD（Antonacopoulos et al., 2009） | 478 | 7,453 | 5 | 5（多样） | 自动 |
| PubLayNet（Zhong et al., 2019） | 360K | 3,311,660 | 5 | 1（学术） | 自动 |
| HJDataset（Shen et al., 2020） | 2,271 | 250,000+ | 7 | 4（历史） | 半自动 |
| DocBank（Li et al., 2020） | 500K | 6,715,907 | 13 | 1（学术） | 自动 |
| DocLayNet（Pfitzmann et al., 2022） | 80,863 | 1,107,470 | 11 | 6（多样） | 人工 |
| M6Doc（Cheng et al., 2023） | 9,080 | 237,116 | 74 | 7（多样） | 人工 |
| D4LA（Da et al., 2023） | 11,092 | 293,692 | 27 | 12（多样） | 人工 |
| IndicDLP（Nath et al., 2025） | 121,198 | 1,856,241 | 42 | 12（多样） | 人工 |
| **MeshLayout-1M（本文）** | **1M** | **14,549,846** | **11** | **高度多样** | **自动** |

**图 2：** Mesh-candidate BestFit 示意图。给定初始页面及标注（A），构建按类别组织的元素池（B）。随后，我们的方法通过迭代的候选元素与网格匹配，生成多样且协调的版面，并形成合成页面（C）。

### 3 多样化预训练文档合成

预训练文档的多样性主要来自两个方面：（1）元素多样性，覆盖不同的元素类别和尺度；（2）版面多样性，涵盖单栏、多栏、杂志风格等不同页面组织。为构建多样且可扩展的文档预训练语料库，我们提出 Mesh-candidate BestFit，这是一个联合考虑元素多样性和版面多样性的合成框架（如图 2 所示）。与随机放置或现有生成方法不同，我们的方法显式控制元素组成、尺度分布和空间排列，以生成真实且多样的文档版面。

#### 3.1 预处理：确保元素多样性

在预处理阶段，为确保包含多样的文档元素，我们使用含文档页面与标注的初始数据语料作为元素来源。在初始数据的选择上，我们使用 DocBank（Li et al., 2020）作为元素来源，因为它具有多样的元素级标注，覆盖各种文档组成部分、外观与尺度。因此，我们首先从原始标注构建元素池，提取区域，并过滤带噪声的过小元素。最后，将保留下来的裁剪图块整理为各类别专属的池，用于后续采样。

#### 3.2 版面生成：确保版面多样性

给定一张空白页面，Mesh-candidate BestFit 通过尺度分层采样与基于网格的最佳适配匹配迭代放置元素。与随机放置或现有生成方法不同，我们的方法在版面多样性与结构合理性之间取得平衡。

1. **尺度分层候选采样。** 直接从整个元素池中采样，可能使版面中小元素过多，妨碍形成稳定的全局结构。为解决这一问题，我们根据归一化尺寸将元素划分为大尺度组与小尺度组，并按预定比例采样候选元素。这一策略在保留细粒度元素的同时，保证有足够的大区域来构成协调的页面结构，并建立主要页面区域。
2. **网格构建。** 基于已有版面构建网格，并过滤与已插入元素重叠的无效网格。只有剩余网格才能在后续步骤中参与候选元素匹配。
3. **最佳适配对搜索。** 对每个候选元素，遍历所有满足尺寸要求的网格，寻找填充率最高的候选元素与网格对。随后，从候选集合中移除最优候选元素，并更新版面。
4. **迭代版面填充。** 最后，调整选中候选元素的尺寸，将其居中放入所分配的网格，并合成到页面上。重复步骤 2～4，直到没有满足尺寸要求的有效候选元素与网格对，或达到最大元素数量。

通过上述过程，元素被逐步放置到合适区域，从而产生更加规则、紧凑的文档版面，如图 3 所示。同时，生成的版面还表现出更好的对齐性和更高的页面占用率。所生成的页面构成 MeshLayout-1M，这是一个包含多样元素与版面组织的大规模合成预训练语料库，使预训练模型能够有效适应各种真实世界文档类型。更详细的分析和解释见附录 E、F。

**图 3：** 合成文档页面示例。

### 4 页面轴向版面注意力

文档版面沿页面的水平轴和垂直轴呈现出很强的结构规律，包括文本行、段落栏、表格结构以及跨区域对应关系。捕获这种具备轴向感知能力的长程上下文，对准确的文档元素检测十分重要。尽管全局注意力（Wang et al., 2018）能够建模这些依赖，但对于高分辨率文档特征，其计算成本高得难以承受。YOLOv12（Tian et al., 2025）中的 Area Attention 通过将交互限制在局部区域内来提高效率，但这种划分可能中断跨区域边界的长程依赖。受文档版面特征启发，我们提出 PALA，以更有效地沿页面轴向建模文档中的长程依赖。

具体而言，给定投影后的查询、键和值特征 $Q,K,V\in\mathbb{R}^{B\times C\times H\times W}$，PALA 沿页面的两个轴重新组织它们，并通过两个并行的注意力分支建模水平与垂直长程上下文。对于垂直分支，沿垂直轴将特征重组为 $Q_{\mathrm{ver}},K_{\mathrm{ver}},V_{\mathrm{ver}}\in\mathbb{R}^{(BW)\times M\times H\times d}$，其中 $M$ 是注意力头数，$d=C/M$。每条序列包含共享同一水平坐标的 $H$ 个空间位置，使每个 token 能关注垂直方向上的全部位置。垂直注意力与特征聚合计算如下：

$$
Y_{\mathrm{ver}}=\operatorname{Softmax}\left(\frac{Q_{\mathrm{ver}}K_{\mathrm{ver}}^{T}}{\sqrt{d}}\right)V_{\mathrm{ver}}. \tag{1}
$$

**图 4：** 页面轴向版面注意力（PALA）示意图。

类似地，对于水平分支，将特征重组为 $Q_{\mathrm{hor}},K_{\mathrm{hor}},V_{\mathrm{hor}}\in\mathbb{R}^{(BH)\times M\times W\times d}$，其中每条序列对应特征图的一行，使得上下文可以在整个水平方向上直接聚合。水平注意力与特征聚合计算如下：

$$
Y_{\mathrm{hor}}=\operatorname{Softmax}\left(\frac{Q_{\mathrm{hor}}K_{\mathrm{hor}}^{T}}{\sqrt{d}}\right)V_{\mathrm{hor}}. \tag{2}
$$

遵循 Area Attention 的投影与位置编码设计，通过沿通道维拆分 $QK=\phi_{qk}(X)$ 得到 $Q$ 和 $K$，同时令 $V=\phi_v(X)$，并将局部空间线索编码为 $P=\operatorname{DWConv}_{5\times5}(V)$。最后，对这两个具有轴向感知能力的特征进行形状恢复和融合：

$$
Y=\operatorname{Proj}(Y_{\mathrm{ver}}+Y_{\mathrm{hor}}+P). \tag{3}
$$

不同于将交互限制在预定义区域内的 Area Attention，PALA 保留了贯穿完整水平轴与垂直轴的长程上下文。同时，它的并行分支与独立归一化设计（如图 4 所示）避免了方向顺序依赖和跨轴竞争，使互补的结构上下文得到有效建模。

我们进一步分析 PALA 的注意力复杂度：忽略相同的线性投影后，全局注意力、具有 $A$ 个等大区域的 Area Attention 和 PALA 的注意力聚合复杂度分别为：

$$
\begin{aligned}
\mathcal{O}_{\mathrm{Global}}&=O(BH^2W^2C),\quad \mathcal{O}_{\mathrm{AA}}=O\left(B\frac{H^2W^2}{A}C\right),\\
\mathcal{O}_{\mathrm{PALA}}&=O(BWH^2C+BHW^2C)=O(BHW(H+W)C).
\end{aligned} \tag{4}
$$

对于正方形特征图（$H=W=S$），PALA 在保留完整水平与垂直交互的同时，将全局注意力的二次复杂度从 $O(BS^4C)$ 降低到 $O(BS^3C)$。与 Area Attention 相比，PALA 避免将上下文聚合限制在预定义区域内，为文档页面提供了更高效的轴向感知注意力机制。

### 5 实验

#### 5.1 实验设置

**基准与对比方法。** 我们在四个异构 DLA 基准上评估 DocLayout-YOLO：D4LA（Da et al., 2023）、M6Doc（Cheng et al., 2023）、HJDataset（Shen et al., 2020）和 PRIMA-LAD（Antonacopoulos et al., 2009）。这些数据集涵盖多样的文档场景，横跨现代与历史来源、多种语言以及多种页面结构。DocLayout-YOLO 与两类方法进行比较：（1）实时检测器，包括基于 YOLO 的模型（Jocher et al., 2023; Wang et al., 2024a; Khanam & Hussain, 2024; Tian et al., 2025; Jocher et al., 2026）和 RT-DETRv3（Wang et al., 2025）；（2）专门的 DLA 方法，包括具有代表性的单模态和多模态方法。对比方法与基准的详细信息见附录 B。

**表 2：在四个文档版面分析基准上与高效实时检测器的比较。** 精度以 $\mathrm{mAP}_{50:95}$（%）报告，FLOPs 在输入分辨率为 $1600\times1600$ 时测量。TensorRT FP16 延迟在 NVIDIA H200 GPU 上以批大小 1 测量。

| 方法 | FLOPs（G） | 参数量（M） | 延迟（ms） | D4LA | M6Doc | HJDataset | PRIMA-LAD |
|---|---:|---:|---:|---:|---:|---:|---:|
| YOLOv8-N（Jocher et al., 2023） | 45.9 | 2.8 | 1.1 | 64.6 | 60.2 | 87.8 | 61.3 |
| YOLOv10-N（Wang et al., 2024a） | 38.2 | 2.1 | 1.4 | 66.9 | 61.5 | 92.9 | 58.7 |
| YOLOv11-N（Khanam & Hussain, 2024） | 33.1 | 2.3 | 1.3 | 65.3 | 62.6 | 88.3 | 60.5 |
| YOLOv12-N（Tian et al., 2025） | 30.2 | 2.2 | 1.7 | 66.5 | 64.5 | 89.6 | 60.4 |
| YOLOv26-N（Jocher et al., 2026） | 38.2 | 2.6 | 1.6 | 65.2 | 62.6 | 91.5 | 59.5 |
| **DocLayout-YOLO-N** | **30.2** | **2.2** | **1.5** | **67.2** | **66.2** | **93.6** | **67.7** |
| YOLOv8-S（Jocher et al., 2023） | 171.5 | 10.8 | 1.5 | 65.7 | 65.4 | 88.1 | 63.2 |
| YOLOv10-S（Wang et al., 2024a） | 139.8 | 7.4 | 1.9 | 69.1 | 68.1 | 95.9 | 61.2 |
| YOLOv11-S（Khanam & Hussain, 2024） | 127.1 | 9.1 | 1.8 | 67.8 | 67.5 | 91.4 | 62.6 |
| YOLOv12-S（Tian et al., 2025） | 114.8 | 8.8 | 2.3 | 69.2 | 69.5 | 91.7 | 64.1 |
| YOLOv26-S（Jocher et al., 2026） | 142.7 | 10.0 | 2.3 | 67.7 | 68.4 | 92.2 | 63.7 |
| **DocLayout-YOLO-S** | **114.8** | **8.8** | **2.0** | **70.6** | **71.1** | **94.8** | **70.3** |
| YOLOv8-M（Jocher et al., 2023） | 489.8 | 25.7 | 2.8 | 69.3 | 69.3 | 94.7 | 67.0 |
| RT-DETRv3-R18（Wang et al., 2025） | 322.5 | 21.1 | 2.4 | 69.6 | 68.1 | 94.1 | 65.7 |
| RT-DETRv3-R34（Wang et al., 2025） | 511.7 | 32.4 | 2.9 | 70.5 | 70.5 | 94.9 | 68.8 |
| YOLOv10-M（Wang et al., 2024a） | 391.0 | 16.1 | 3.3 | 70.6 | 69.0 | 94.1 | 63.8 |
| YOLOv11-M（Khanam & Hussain, 2024） | 427.7 | 20.1 | 3.0 | 69.0 | 69.0 | 94.9 | 66.0 |
| YOLOv12-M（Tian et al., 2025） | 377.1 | 19.7 | 3.7 | 70.2 | 70.9 | 93.4 | 66.3 |
| YOLOv26-M（Jocher et al., 2026） | 471.2 | 21.9 | 3.4 | 68.7 | 69.6 | 94.2 | 65.3 |
| **DocLayout-YOLO-M** | **377.1** | **19.7** | **3.1** | **70.7** | **73.3** | **95.3** | **71.3** |
| YOLOv8-L（Jocher et al., 2023） | 1035.3 | 43.7 | 4.0 | 70.9 | 71.7 | 95.7 | 68.6 |
| RT-DETRv3-R50（Wang et al., 2025） | 766.5 | 43.7 | 4.1 | 72.1 | 72.4 | 94.3 | 70.4 |
| YOLOv10-L（Wang et al., 2024a） | 798.1 | 25.9 | 4.6 | 71.6 | 72.4 | 95.6 | 65.7 |
| YOLOv11-L（Khanam & Hussain, 2024） | 547.0 | 25.4 | 4.1 | 71.4 | 72.1 | 94.9 | 67.9 |
| YOLOv12-L（Tian et al., 2025） | 519.9 | 26.5 | 5.8 | 71.1 | 72.5 | 94.9 | 66.9 |
| YOLOv26-L（Jocher et al., 2026） | 586.2 | 26.3 | 4.5 | 69.8 | 70.9 | 95.1 | 64.6 |
| **DocLayout-YOLO-L** | **519.9** | **26.5** | **4.7** | **72.0** | **75.1** | **95.7** | **73.4** |
| YOLOv8-X（Jocher et al., 2023） | 1615.2 | 68.2 | 6.0 | 71.0 | 72.2 | 95.4 | 69.6 |
| RT-DETRv3-R101（Wang et al., 2025） | 1533.8 | 84.6 | 6.4 | 72.2 | 72.7 | 93.0 | 70.3 |
| YOLOv10-X（Wang et al., 2024a） | 1072.6 | 31.8 | 6.5 | 72.1 | 72.0 | 94.0 | 61.1 |
| YOLOv11-X（Khanam & Hussain, 2024） | 1223.9 | 56.9 | 6.1 | 71.7 | 73.9 | 95.4 | 65.5 |
| YOLOv12-X（Tian et al., 2025） | 1161.1 | 59.4 | 8.5 | 70.8 | 74.0 | 94.0 | 67.0 |
| YOLOv26-X（Jocher et al., 2026） | 1309.6 | 59.0 | 6.6 | 70.8 | 71.3 | 95.7 | 65.8 |
| **DocLayout-YOLO-X** | **1161.1** | **59.4** | **6.9** | **72.4** | **75.5** | **96.0** | **73.1** |

**实现细节。** DocLayout-YOLO 基于 YOLOv12（Tian et al., 2025）构建，并在 PALA 中集成 FlashAttention（Dao et al., 2022; Dao, 2024）。每个模型首先在 MeshLayout-1M 上预训练，随后使用 $1600\times1600$ 的输入分辨率，在 8 张 H200 GPU 上针对下游基准微调。所有模型均使用 SGD 优化器训练 500 个轮次，初始学习率为 0.02，与 YOLOv12 一致。采用线性学习率衰减策略，并在前 3 个轮次进行线性预热。所有模型的延迟均在一张 H200 GPU 上使用 TensorRT FP16 测试。完整实现细节见附录 A。

#### 5.2 与最先进实时检测器的比较

表 2 比较了 DocLayout-YOLO 与现有实时检测器。**N 尺度：** DocLayout-YOLO-N 在四个基准上相比基线 YOLOv12-N 分别提高 0.7%/1.7%/4.0%/7.3% mAP，同时将延迟降低 11.8%。在相近推理速度下，其相较 YOLOv8-N、YOLOv10-N 和 YOLOv26-N 的提升最高达到 9.0%。**S 尺度：** DocLayout-YOLO-S 相比 YOLOv12-S 提高 1.4%/1.6%/3.1%/6.2%，同时延迟降低 13.0%。相较 YOLOv26-S 和 RT-DETRv3-R18，其提升分别最高达 6.6% 和 4.6%。**M 尺度：** 在延迟为 3.1 ms 的情况下，DocLayout-YOLO-M 相比 YOLOv12-M 提高 0.5%/2.4%/1.9%/5.0%，并实现 16.2% 的加速。它还在 FLOPs 减少 26.3% 的同时，比 RT-DETRv3-R34 最高提高 2.8%。**L 尺度：** DocLayout-YOLO-L 相较 YOLOv12-L 提高 0.9%/2.6%/0.8%/6.5%，同时将延迟从 5.8 ms 降至 4.7 ms。**X 尺度：** DocLayout-YOLO-X 在四个基准上取得总体最佳的 72.4%/75.5%/96.0%/73.1% mAP。相较 YOLOv12-X，其提高 1.6%/1.5%/2.0%/6.1%，同时延迟降低 18.8%；在相近推理延迟下，相较 RT-DETRv3-R101 最高提高 3.0%。此外，PALA 保留了与 YOLOv12 中 Area Attention 相同的特征投影和位置编码，而标准 FLOPs 分析不计入注意力聚合，因此参数量和 GFLOPs 数相同；尽管如此，PALA 通过更高效的逐轴聚合始终获得更低的延迟。

**表 3：在公开基准上与现有最先进（state-of-the-art，SOTA）方法的性能比较。** 最佳与次佳结果予以突出显示（此处分别用粗体和下划线）。† 表示预测时使用了真实文本级边界框与 OCR 标注。V、L 分别表示视觉与语言模态。

| 方法 | 发表场所 | 骨干网络 | V | L | 参数量 | D4LA | M6Doc | HJDataset | PRIMA-LAD |
|---|---|---|:---:|:---:|---:|---:|---:|---:|---:|
| LayoutParser（Shen et al., 2021） | ICDAR 2021 | ResNext（Xie et al., 2017） | ✓ | ✗ | 6.6M | - | - | 81.6 | <u>64.7</u> |
| DocSegTr（Biswas et al., 2022） | arXiv 2022 | ResNet（He et al., 2016） | ✓ | ✗ | 84.2M | - | 60.3 | 83.1 | 42.5 |
| DiT-L（Li et al., 2022） | ACM MM 2022 | ViT-L（Dosovitskiy et al., 2021） | ✓ | ✗ | 361.6M | 68.2 | 70.2 | - | - |
| SelfDocSeg（Maity et al., 2023） | ICDAR 2023 | ResNet-50（He et al., 2016） | ✓ | ✗ | 63.7M | - | - | 78.8 | 52.1 |
| SwinDocSegmenter（Banerjee et al., 2023） | ICDAR 2023 | Swin（Liu et al., 2021） | ✓ | ✗ | 220.9M | - | 47.1 | 84.6 | 54.4 |
| GraphKD（Banerjee et al., 2024a） | ICDAR 2024 | ResNet（He et al., 2016） | ✓ | ✗ | 136.6M | - | - | 79.7 | 41.9 |
| SemiDocSeg（Banerjee et al., 2024b） | IJDAR 2024 | Swin-L（Liu et al., 2021） | ✓ | ✗ | 220.9M | - | - | 81.1 | 45.9 |
| RoDLA（Chen et al., 2024b） | CVPR 2024 | InternImage（Wang et al., 2023） | ✓ | ✗ | 338.9M | - | 70.0 | - | - |
| PARL（Liu et al., 2026） | arXiv 2026 | HRNetv2（Sun et al., 2019） | ✓ | ✗ | 65M | <u>70.9</u> | <u>72.9</u> | - | - |
| HybriDLA（Chen et al., 2026） | AAAI 2026 | InternImage（Wang et al., 2023） | ✓ | ✗ | 392M | - | 71.4 | - | - |
| LayoutLMv3（Huang et al., 2022） | ACM MM 2022 | RoBERTa-B（Liu et al., 2019） | ✓ | ✓ | 138.4M | 60.0 | 64.3 | 82.7 | 40.3 |
| VGT（Da et al., 2023） | ICCV 2023 | ViT-B（Dosovitskiy et al., 2021） | ✓ | ✓ | 266.8M | 68.8 | - | - | - |
| M2Doc†（Zhang et al., 2024） | AAAI 2024 | ResNet（He et al., 2016） | ✓ | ✓ | 266.5M | - | 69.9 | - | - |
| DoPTA-HR（R. et al., 2024） | arXiv 2024 | ViT-B（Dosovitskiy et al., 2021） | ✓ | ✓ | 85M | 70.7 | 69.5 | - | - |
| DocSAM（Li et al., 2025） | CVPR 2025 | Swin-L（Liu et al., 2021） | ✓ | ✓ | 317M | 55.5 | 50.0 | <u>90.5</u> | - |
| PromptDLA（Zhang et al., 2026） | TMM 2026 | ViT-B（Dosovitskiy et al., 2021） | ✓ | ✓ | - | 69.2 | 69.1 | - | - |
| **DocLayout-YOLO-X** | - | v12x，采用 PALA | ✓ | ✗ | **59.4M** | **72.4** | **75.5** | **96.0** | **73.1** |

**表 4：不同模型规模下 MeshLayout-1M 预训练与 PALA 的消融研究。**

| 规模 | MeshLayout-1M | PALA | D4LA | M6Doc | HJDataset | PRIMA-LAD |
|---|:---:|:---:|---:|---:|---:|---:|
| N | | | 66.5 | 64.5 | 89.6 | 60.4 |
| N | | ✓ | 67.0 | 65.3 | 91.0 | 62.6 |
| N | ✓ | | 66.9 | 65.4 | 92.1 | 65.8 |
| N | ✓ | ✓ | **67.2** | **66.2** | **93.6** | **67.7** |
| S | | | 69.2 | 69.5 | 91.7 | 64.1 |
| S | | ✓ | 70.2 | 70.1 | 92.9 | 66.8 |
| S | ✓ | | 69.8 | 70.4 | 93.9 | 68.6 |
| S | ✓ | ✓ | **70.6** | **71.1** | **94.8** | **70.3** |
| M | | | 70.2 | 70.9 | 93.4 | 66.3 |
| M | | ✓ | 70.6 | 71.5 | 95.2 | 69.2 |
| M | ✓ | | 70.6 | 72.6 | 95.0 | 70.0 |
| M | ✓ | ✓ | **70.7** | **73.3** | **95.3** | **71.3** |
| L | | | 71.1 | 72.5 | 94.9 | 66.9 |
| L | | ✓ | 71.6 | 73.7 | 95.3 | 69.1 |
| L | ✓ | | 71.7 | 74.5 | 95.4 | 71.9 |
| L | ✓ | ✓ | **72.0** | **75.1** | **95.7** | **73.4** |
| X | | | 70.8 | 74.0 | 94.0 | 67.0 |
| X | | ✓ | 71.8 | 74.5 | 95.2 | 67.8 |
| X | ✓ | | 71.5 | 75.0 | 95.8 | 71.8 |
| X | ✓ | ✓ | **72.4** | **75.5** | **96.0** | **73.1** |

#### 5.3 与最先进专用 DLA 方法的比较

表 3 比较了 DocLayout-YOLO 与专用文档版面分析方法。DocLayout-YOLO-X 在全部四个基准上取得最先进的性能，在 D4LA、M6Doc、HJDataset 和 PRIMA-LAD 上分别达到 72.4%/75.5%/96.0%/73.1% mAP。值得注意的是，DocLayout-YOLO 仅依赖视觉输入，并始终优于纯视觉单模态方法和视觉语言多模态方法。与此前表现最好的单模态方法相比，DocLayout-YOLO 在 D4LA 和 M6Doc 上分别提高 1.5% 和 2.6%，同时仅使用 59.4M 参数，显著少于大多数具有竞争力的 DLA 模型。此外，与 LayoutLMv3、VGT 和 DoPTA-HR 等多模态方法不同，DocLayout-YOLO 在推理时不需要 OCR 标注或语义语言特征，表明通过高效的纯视觉建模即可实现较强的文档版面感知。另外，许多方法依赖大型骨干网络，而 DocLayout-YOLO 保持了基于 YOLO 的轻量架构，以显著更低的模型复杂度实现了更优性能。

**表 5：不同文档预训练数据集在 M6Doc 各文档类型上的比较。**

| 预训练数据 | 数量 | 书籍 | 杂志 | 报纸 | 笔记 | 论文 | 试卷 | 教科书 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 无 | - | 53.5 | 74.2 | 74.4 | 64.9 | 71.5 | 71.5 | 65.7 |
| DocBank（Li et al., 2020） | 400K | 53.9（+0.4） | 74.7（+0.5） | 74.8（+0.4） | 65.5（+0.6） | 72.7（+1.2） | 71.1（-0.4） | 66.1（+0.4） |
| PubLayNet（Zhong et al., 2019） | 340K | 53.7（+0.2） | 74.0（-0.2） | 74.5（+0.1） | 64.0（-0.9） | 70.5（-1.0） | 71.6（+0.1） | 65.9（+0.2） |
| DocSynth（Biswas et al., 2021） | 300K | 53.2（-0.3） | 73.7（-0.5） | 73.5（-0.9） | 62.7（-2.2） | 69.9（-1.6） | 69.4（-2.1） | 65.0（-0.7） |
| RanLayNet（Anand et al., 2023） | 7K | 53.9（+0.4） | 73.2（-1.0） | 72.8（-1.6） | 62.3（-2.6） | 70.7（-0.8） | 70.3（-1.3） | 65.2（-0.5） |
| LayoutDM（Inoue et al., 2023） | 300K | 53.3（-0.2） | 74.7（+0.5） | 74.5（+0.1） | 62.3（-2.6） | 69.7（-1.8） | 69.9（-1.6） | 64.5（-1.3） |
| LACE（Chen et al., 2024a） | 300K | 54.0（+0.5） | 74.0（-0.2） | 74.3（-0.1） | 64.2（-0.7） | 71.8（+0.3） | 71.3（-0.2） | 65.7（0.0） |
| MeshLayout | 300K | 53.9（+0.4） | 74.9（+0.7） | 75.1（+0.7） | 65.7（+0.8） | 72.2（+0.7） | 72.0（+0.5） | 65.5（-0.2） |
| MeshLayout | 500K | 54.7（+1.2） | 75.2（+1.0） | 75.3（+0.9） | 65.6（+0.7） | 72.9（+1.4） | 72.4（+0.9） | 66.4（+0.7） |
| **MeshLayout** | **1M** | **55.6（+2.1）** | **76.0（+1.8）** | **75.9（+1.5）** | **66.7（+1.8）** | **74.6（+3.1）** | **72.6（+1.1）** | **66.9（+1.2）** |

**图 5：** 随机放置、扩散模型与 Mesh-candidate BestFit 的定性比较。

#### 5.4 消融研究

**组件有效性分析。** 表 4 进一步分离了 MeshLayout-1M 预训练与 PALA 的贡献。具体而言，仅 MeshLayout 的设置对应在 MeshLayout-1M 上预训练的原始 YOLOv12，而仅 PALA 的设置则将 Area Attention 替换为 PALA，不进行预训练。在五种模型规模上取平均，仅使用 PALA 在 D4LA、M6Doc、HJDataset 和 PRIMA-LAD 上分别提高 0.7%/0.7%/1.2%/2.2% mAP，而仅使用 MeshLayout-1M 预训练则分别带来 0.5%/1.3%/1.7%/4.7% 的增益。组合两个组件始终取得最佳结果，相比 YOLOv12 基线平均提高 1.0%/2.0%/2.4%/6.2%。这些结果表明，DocLayout-YOLO 的增益既来自 PALA 的架构设计，也来自 MeshLayout-1M 的文档领域预训练，两个组件带来了互补收益。

**预训练数据集比较。** 表 5 比较了 MeshLayout-1M 与具有代表性的真实及合成文档预训练数据集。真实数据集包括 PubLayNet（Zhong et al., 2019）和 DocBank（Li et al., 2020），它们提供带标注的真实科学文献页面。合成替代方案包括 DocSynth（Biswas et al., 2021），它使用源自 PubLayNet 的版面合成页面，而 RanLayNet（Anand et al., 2023）采用随机放置。对于基于扩散的方法，我们使用在 DocBank 上训练的 LayoutDM（Inoue et al., 2023）和 LACE（Chen et al., 2024a）生成版面，再使用 DocBank 元素进行渲染。图 5 定性比较了随机放置、基于扩散的生成以及 Mesh-candidate BestFit 所生成的合成版面与页面。为公平比较，我们在相同设置下，使用不同数据集预训练 DocLayout-YOLO-S，并评估下游性能。现有数据集在不同文档类型上的迁移表现不一致，而随着预训练规模扩大，MeshLayout 的增益越来越稳定。在 1M 页规模下，其使全部七种文档类型的 mAP 提高 1.1%～3.1%，表明该方法向异构版面的迁移具有可扩展性和稳健性。

**MeshLayout 组件消融。** 表 6 使用 DocLayout-YOLO-S 对 Mesh-candidate BestFit 的各组件进行消融。对于每种变体，我们都生成相同数量的预训练页面（1M），并比较下游微调性能。1）移除网格构建后，合成退化为无约束的随机放置，产生杂乱的版面（图 5），使 M6Doc、HJDataset 和 PRIMA-LAD 上的性能分别下降 1.2%/2.6%/3.1%。2）不使用尺度分层采样时，小元素占比过高，削弱版面结构，使性能分别下降 0.3%/0.4%/1.1%。3）不使用 BestFit 匹配时，随机的候选元素与区域分配会导致尺寸不匹配和过多空白区域，造成 0.7%/0.5%/1.8% 的下降。这些结果表明，三个组件共同保证了结构合理性、尺度一致性以及有效的下游迁移。

**表 6：Mesh-candidate BestFit 核心组件的消融研究。**

| 方法 | 网格构建 | 尺度分层采样 | BestFit 匹配 | M6Doc | HJDataset | PRIMA-LAD |
|---|:---:|:---:|:---:|---:|---:|---:|
| 基线（无 MeshLayout 预训练） | - | - | - | 70.1 | 92.9 | 66.8 |
| 无网格构建 | ✗ | ✓ | - | 69.9 | 92.2 | 67.2 |
| 无尺度分层采样 | ✓ | ✗ | ✓ | 70.8 | 94.4 | 69.2 |
| 无 BestFit 匹配 | ✓ | ✓ | ✗ | 70.4 | 94.3 | 68.5 |
| **完整 MeshLayout** | ✓ | ✓ | ✓ | **71.1** | **94.8** | **70.3** |

**表 7：局部注意力比较。**

| 规模 | 注意力类型 | 显存（G） | CUDA FP32 | CUDA FP16 | M6Doc |
|---|---|---:|---:|---:|---:|
| N | Global（Wang et al., 2018） | 0.295 | 9.498 | 2.123 | 64.5 |
| N | Area（Tian et al., 2025） | 0.295 | 5.250 | 1.656 | 64.5 |
| N | Criss-Cross（Huang et al., 2019） | 0.301 | 3.187 | 1.847 | 64.7 |
| N | Swin（Liu et al., 2021） | 0.295 | 2.988 | 1.656 | 62.3 |
| N | CSWin（Dong et al., 2022） | 0.295 | 3.587 | 1.755 | 63.6 |
| N | Axial（Wang et al., 2020） | 0.295 | 3.690 | 1.643 | 64.2 |
| N | 仅水平 | 0.295 | 2.867 | 1.378 | 64.1 |
| N | 仅垂直 | 0.295 | 2.901 | 1.398 | 63.9 |
| **N** | **PALA（本文）** | **0.295** | **3.596** | **1.500** | **65.3** |
| L | Global（Wang et al., 2018） | 0.514 | 61.524 | 9.184 | 73.0 |
| L | Area（Tian et al., 2025） | 0.512 | 30.956 | 5.637 | 71.1 |
| L | Criss-Cross（Huang et al., 2019） | 0.516 | 19.399 | 6.588 | 73.2 |
| L | Swin（Liu et al., 2021） | 0.512 | 18.847 | 5.485 | 71.7 |
| L | CSWin（Dong et al., 2022） | 0.514 | 21.559 | 5.905 | 72.6 |
| L | Axial（Wang et al., 2020） | 0.512 | 22.266 | 5.223 | 72.4 |
| L | 仅水平 | 0.512 | 17.862 | 4.325 | 72.7 |
| L | 仅垂直 | 0.512 | 17.912 | 4.378 | 71.4 |
| **L** | **PALA（本文）** | **0.512** | **20.709** | **4.694** | **73.7** |

**表 8：速度、显存与效率。**

| 模型 | FLOPs（G） | 显存（GiB） | CUDA 延迟 FP32（ms） | CUDA 延迟 FP16（ms） | M6Doc |
|---|---:|---:|---:|---:|---:|
| YOLOv8-N（Jocher et al., 2023） | 45.9 | 0.29 | 2.4 | 1.1 | 60.2 |
| YOLOv10-N（Wang et al., 2024a） | 38.2 | 0.31 | 2.8 | 1.4 | 61.5 |
| YOLOv12-N（Tian et al., 2025） | 30.2 | 0.30 | 5.3 | 1.7 | 64.5 |
| **DocLayout-YOLO-N** | **30.2** | **0.30** | **3.6** | **1.5** | **66.2** |
| YOLOv8-S（Jocher et al., 2023） | 171.5 | 0.34 | 5.5 | 1.5 | 65.4 |
| YOLOv10-S（Wang et al., 2024a） | 139.8 | 0.48 | 5.6 | 1.9 | 68.1 |
| YOLOv12-S（Tian et al., 2025） | 114.8 | 0.35 | 9.9 | 2.3 | 69.5 |
| **DocLayout-YOLO-S** | **114.8** | **0.35** | **6.7** | **2.0** | **71.1** |
| YOLOv8-M（Jocher et al., 2023） | 489.8 | 0.44 | 13.2 | 2.8 | 69.3 |
| YOLOv10-M（Wang et al., 2024a） | 391.0 | 0.53 | 12.0 | 3.3 | 69.0 |
| YOLOv12-M（Tian et al., 2025） | 377.1 | 0.49 | 19.4 | 3.7 | 70.9 |
| **DocLayout-YOLO-M** | **377.1** | **0.49** | **14.0** | **3.1** | **73.3** |
| YOLOv8-L（Jocher et al., 2023） | 1035.3 | 0.57 | 22.3 | 4.0 | 71.7 |
| YOLOv10-L（Wang et al., 2024a） | 798.1 | 0.61 | 19.0 | 4.6 | 72.4 |
| YOLOv12-L（Tian et al., 2025） | 519.9 | 0.51 | 31.2 | 5.8 | 72.5 |
| **DocLayout-YOLO-L** | **519.9** | **0.51** | **20.7** | **4.7** | **75.1** |
| YOLOv8-X（Jocher et al., 2023） | 1615.2 | 0.69 | 36.3 | 6.0 | 72.2 |
| YOLOv10-X（Wang et al., 2024a） | 1072.6 | 0.71 | 27.4 | 6.5 | 72.0 |
| YOLOv12-X（Tian et al., 2025） | 1161.1 | 0.70 | 53.1 | 8.5 | 74.0 |
| **DocLayout-YOLO-X** | **1161.1** | **0.70** | **37.9** | **6.9** | **75.5** |

**页面轴向版面注意力。** 表 7 比较了不同注意力机制在 M6Doc 上的表现。为保证公平性，延迟在相同的 H200 上获取，而显存占用使用 TensorRT 模型测量（$bs=1$）。遵循 YOLOv12（Tian et al., 2025），我们调整通道数，以保证所有模型具有相近的参数量与 FLOPs，并禁用 Flash-Attention。相比 Global Attention，PALA 在显著降低延迟的同时取得更高精度，这表明不受约束的全局交互可能引入跨区域干扰，而逐轴约束更符合文档结构。Swin 的表现较差，因为它的局部窗口限制了跨越长文档结构的直接交互；Criss-Cross 和 CSWin 则沿水平与垂直方向扩展注意力，以更好地捕获这些依赖。PALA 进一步结合两个页面轴，在 N/L 尺度上取得最佳的 65.3%/73.7% mAP。仅水平方向始终优于仅垂直方向，而结合两者又带来进一步增益，表明水平与垂直依赖在文档版面中具有重要性和互补性。更多解释和分析见附录 D。

**速度、显存与效率。** 表 8 在相同的 H200 GPU 硬件设置下，评估了 DocLayout-YOLO 在五种模型尺度上的速度、显存占用及精度与效率权衡。尽管与 YOLOv12 参数量相同，DocLayout-YOLO 始终获得更低的延迟，凸显出 PALA 注意力聚合在实际中的效率。与 YOLOv12 相比，从 N 到 X 尺度，DocLayout-YOLO 分别将 FP32 延迟降低 1.7/3.2/5.4/10.5/15.2 ms，将 FP16 延迟降低 0.2/0.3/0.6/1.1/1.6 ms，同时保持相近的峰值显存占用。与此同时，相比 YOLOv8 与 YOLOv10，DocLayout-YOLO 进一步在推理速度、显存占用和检测精度之间提供了良好的平衡。

### 6 结论

本工作提出 DocLayout-YOLO，这是一种专为文档版面分析设计的实时检测器。DocLayout-YOLO 将基于 MeshLayout-1M 的大规模合成文档预训练，与基于 PALA 的高效长程页面轴向建模相结合，使 YOLO 范式适应异构文档版面。大量实验表明，DocLayout-YOLO 在多个基准上取得最先进的结果，并始终相较现有实时检测器实现更优的精度与效率权衡。

### 参考文献

Avinash Anand, Raj Jaiswal, Mohit Gupta, Siddhesh S. Bangar, Pijush Bhuyan, Naman Lal, Rajeev Singh, Ritika Jha, Rajiv Ratn Shah, and Shin’ichi Satoh. Ranlaynet: A dataset for document layout detection used for domain adaptation and generalization（RanLayNet：用于领域适应与泛化的文档版面检测数据集）. 载于 ACM Multimedia Asia（ACM 亚洲多媒体会议）, 2023.

Apostolos Antonacopoulos, David Bridson, Christos Papadopoulos, and Stefan Pletschacher. A realistic dataset for performance evaluation of document layout analysis（用于文档版面分析性能评估的真实数据集）. 载于 ICDAR（国际文档分析与识别会议）, 2009.

Ayan Banerjee, Sanket Biswas, Josep Lladós, and Umapada Pal. Graphkd: Exploring knowledge distillation towards document object detection with structured graph creation（GraphKD：通过结构化图构建探索面向文档目标检测的知识蒸馏）. 载于 ICDAR（国际文档分析与识别会议）, 2024a.

Ayan Banerjee, Sanket Biswas, Josep Lladós, and Umapada Pal. Semidocseg: Harnessing semi-supervised learning for document layout analysis（SemiDocSeg：利用半监督学习进行文档版面分析）. International Journal on Document Analysis and Recognition（《国际文档分析与识别期刊》）, 2024b.

Ayan Banerjee et al. Swindocsegmenter: An end-to-end unified domain adaptive transformer for document instance segmentation（SwinDocSegmenter：用于文档实例分割的端到端统一领域自适应 Transformer）. 载于 ICDAR（国际文档分析与识别会议）, 2023.

Sanket Biswas, Pau Riba, Josep Lladós, and Umapada Pal. Docsynth: A layout guided approach for controllable document image synthesis（DocSynth：一种版面引导的可控文档图像合成方法）. 载于 ICDAR（国际文档分析与识别会议）, 2021.

Sanket Biswas et al. DocSegTr: An instance-level end-to-end document image segmentation transformer（DocSegTr：一种实例级端到端文档图像分割 Transformer）. arXiv 预印本 arXiv:2201.11438, 2022.

Zhaowei Cai and Nuno Vasconcelos. Cascade R-CNN: Delving into high quality object detection（Cascade R-CNN：深入探索高质量目标检测）. 载于 CVPR（计算机视觉与模式识别会议）, 2018.

Jian Chen, Ruiyi Zhang, Yufan Zhou, and Changyou Chen. Towards aligned layout generation via diffusion model with aesthetic constraints（通过带美学约束的扩散模型实现对齐的版面生成）. 载于 ICLR（国际学习表征会议）, 2024a.

Jun Chen, Dannong Xu, Junjie Fei, Chun-Mei Feng, and Mohamed Elhoseiny. Document haystacks: Vision-language reasoning over piles of 1000+ documents（Document Haystacks：在含 1000 多份文档的文档堆上进行视觉语言推理）. 载于 CVPR（计算机视觉与模式识别会议）, 2025.

Yufan Chen, Omar Moured, Ruiping Liu, Junwei Zheng, Kunyu Peng, Jiaming Zhang, and Rainer Stiefelhagen. Hybridla: Hybrid generation for document layout analysis（HybriDLA：用于文档版面分析的混合生成）. 载于 AAAI（AAAI 人工智能会议）, 2026.

Yufan Chen et al. Rodla: Benchmarking the robustness of document layout analysis models（RoDLA：对文档版面分析模型的鲁棒性进行基准评估）. 载于 CVPR（计算机视觉与模式识别会议）, 2024b.

Hiuyi Cheng, Peirong Zhang, Sihang Wu, Jiaxin Zhang, Qiyuan Zhu, Zecheng Xie, Jing Li, Kai Ding, and Lianwen Jin. M6doc: A large-scale multi-format, multi-type, multi-layout, multi-language, multi-annotation category dataset for modern document layout analysis（M6Doc：面向现代文档版面分析的大规模多格式、多类型、多版面、多语言、多标注类别数据集）. 载于 CVPR（计算机视觉与模式识别会议）, 2023.

Jaemin Cho, Debanjan Mahata, Ozan Irsoy, Yujie He, and Mohit Bansal. M3docrag: Multi-modal retrieval is what you need for multi-page multi-document understanding（M3DocRAG：多页多文档理解需要多模态检索）. arXiv 预印本 arXiv:2411.04952, 2024.

Cheng Cui, Ting Sun, Suyin Liang, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Xueqing Wang, Changda Zhou, Hongen Liu, Manhui Lin, Yue Zhang, Yubo Zhang, Jing Zhang, Jun Zhang, Xing Wei, Yi Liu, Dianhai Yu, and Yanjun Ma. Boosting document parsing efficiency and performance with coarse-to-fine visual processing（通过由粗到细的视觉处理提升文档解析效率与性能）. 载于 CVPR（计算机视觉与模式识别会议）, 2026.

Cheng Da, Chuwei Luo, Qi Zheng, and Cong Yao. Vision grid transformer for document layout analysis（用于文档版面分析的视觉网格 Transformer）. 载于 ICCV（国际计算机视觉会议）, 2023.

Tri Dao. Flashattention-2: Faster attention with better parallelism and work partitioning（FlashAttention-2：通过更好的并行性和工作划分实现更快的注意力）. 载于 ICLR（国际学习表征会议）, 2024.

Tri Dao, Daniel Y. Fu, Stefano Ermon, Atri Rudra, and Christopher Ré. FlashAttention: Fast and memory-efficient exact attention with IO-awareness（FlashAttention：具备 IO 感知能力的快速、内存高效的精确注意力）. 载于 NeurIPS（神经信息处理系统大会）, 第 35 卷, 2022.

Xiaoyi Dong, Jianmin Bao, Dongdong Chen, Weiming Zhang, Nenghai Yu, Lu Yuan, Dong Chen, and Baining Guo. CSWin transformer: A general vision transformer backbone with cross-shaped windows（CSWin Transformer：采用十字形窗口的通用视觉 Transformer 骨干网络）. 载于 CVPR（计算机视觉与模式识别会议）, 2022.

Alexey Dosovitskiy, Lucas Beyer, Alexander Kolesnikov, Dirk Weissenborn, Xiaohua Zhai, Thomas Unterthiner, Mostafa Dehghani, Matthias Minderer, Georg Heigold, Sylvain Gelly, Jakob Uszkoreit, and Neil Houlsby. An image is worth 16x16 words: Transformers for image recognition at scale（一张图像抵得上 16×16 个词：面向大规模图像识别的 Transformer）. 载于 ICLR（国际学习表征会议）, 2021.

Kamal Gupta, Justin Lazarow, Alessandro Achille, Larry Davis, Vijay Mahadevan, and Abhinav Shrivastava. Layouttransformer: Layout generation and completion with self-attention（LayoutTransformer：使用自注意力进行版面生成与补全）. 载于 ICCV（国际计算机视觉会议）, 2021.

Kaiming He, Xiangyu Zhang, Shaoqing Ren, and Jian Sun. Deep residual learning for image recognition（用于图像识别的深度残差学习）. 载于 CVPR（计算机视觉与模式识别会议）, 2016.

Kaiming He, Georgia Gkioxari, Piotr Dollár, and Ross B. Girshick. Mask R-CNN（Mask R-CNN）. 载于 ICCV（国际计算机视觉会议）, 2017.

Yupan Huang, Tengchao Lv, Lei Cui, Yutong Lu, and Furu Wei. Layoutlmv3: Pre-training for document AI with unified text and image masking（LayoutLMv3：通过统一文本和图像掩码进行文档 AI 预训练）. 载于 ACM MM（ACM 国际多媒体会议）, 2022.

Zilong Huang, Xinggang Wang, Lichao Huang, Chang Huang, Yunchao Wei, and Wenyu Liu. CCNet: Criss-cross attention for semantic segmentation（CCNet：用于语义分割的十字交叉注意力）. 载于 ICCV（国际计算机视觉会议）, 2019.

Mude Hui, Zhizheng Zhang, Xiaoyi Zhang, Wenxuan Xie, Yuwang Wang, and Yan Lu. Unifying layout generation with a decoupled diffusion model（使用解耦扩散模型统一版面生成）. 载于 CVPR（计算机视觉与模式识别会议）, 2023.

Naoto Inoue, Kotaro Kikuchi, Edgar Simo-Serra, Mayu Otani, and Kota Yamaguchi. Layoutdm: Discrete diffusion model for controllable layout generation（LayoutDM：用于可控版面生成的离散扩散模型）. 载于 CVPR（计算机视觉与模式识别会议）, 2023.

Zhaoyun Jiang, Jiaqi Guo, Shizhao Sun, Huayu Deng, Zhongkai Wu, Vuksan Mijovic, Zijiang James Yang, Jian-Guang Lou, and Dongmei Zhang. Layoutformer++: Conditional graphic layout generation via constraint serialization and decoding space restriction（LayoutFormer++：通过约束序列化和解码空间限制进行条件图形版面生成）. 载于 CVPR（计算机视觉与模式识别会议）, 2023.

Glenn Jocher, Ayush Chaurasia, and Jing Qiu. Ultralytics YOLO（Ultralytics YOLO）, 2023. URL https://github.com/ultralytics/ultralytics.

Glenn Jocher, Jing Qiu, Mengyu Liu, Shuai Lyu, Fatih Cagatay Akyon, and Muhammet Esat Kalfaoglu. Ultralytics YOLO26: Unified real-time end-to-end vision models（Ultralytics YOLO26：统一的实时端到端视觉模型）. arXiv 预印本 arXiv:2606.03748, 2026.

Rahima Khanam and Muhammad Hussain. YOLOv11: An overview of the key architectural enhancements（YOLOv11：关键架构改进概述）. arXiv 预印本 arXiv:2410.17725, 2024.

Kotaro Kikuchi, Edgar Simo-Serra, Mayu Otani, and Kota Yamaguchi. Constrained graphic layout generation via latent optimization（通过潜在空间优化进行受约束的图形版面生成）. 载于 ACM MM（ACM 国际多媒体会议）, 2021.

Xiang Kong, Lu Jiang, Huiwen Chang, Han Zhang, Yuan Hao, Haifeng Gong, and Irfan Essa. BLT: bidirectional layout transformer for controllable layout generation（BLT：用于可控版面生成的双向版面 Transformer）. 载于 ECCV（欧洲计算机视觉会议）, 2022.

David D. Lewis, Gady Agam, Shlomo Argamon, Ophir Frieder, David A. Grossman, and Jefferson Heard. Building a test collection for complex document information processing（为复杂文档信息处理构建测试集）. 载于 International ACM SIGIR Conference on Research and Development in Information Retrieval（ACM SIGIR 国际信息检索研究与开发会议）, 2006.

Gengluo Li, Pengyuan Lyu, Chengquan Zhang, Huawen Shen, Liang Wu, Xingyu Wan, Gangyan Zeng, Han Hu, Can Ma, and Yu Zhou. Towards real-world document parsing via realistic scene synthesis and document-aware training（通过真实场景合成与文档感知训练迈向真实世界文档解析）. 载于 CVPR（计算机视觉与模式识别会议）, 2026.

Jianan Li, Jimei Yang, Jianming Zhang, Chang Liu, Christina Wang, and Tingfa Xu. Attribute-conditioned layout GAN for automatic graphic design（用于自动图形设计的属性条件版面 GAN）. IEEE TVCG（《IEEE 可视化与计算机图形学汇刊》）, 2021.

Junlong Li, Yiheng Xu, Tengchao Lv, Lei Cui, Cha Zhang, and Furu Wei. Dit: Self-supervised pre-training for document image transformer（DiT：文档图像 Transformer 的自监督预训练）. 载于 ACM MM（ACM 国际多媒体会议）, 2022.

Minghao Li, Yiheng Xu, Lei Cui, Shaohan Huang, Furu Wei, Zhoujun Li, and Ming Zhou. Docbank: A benchmark dataset for document layout analysis（DocBank：用于文档版面分析的基准数据集）. 载于 International Conference on Computational Linguistics（国际计算语言学会议）, 2020.

Xiao-Hui Li, Fei Yin, and Cheng-Lin Liu. DocSAM: Unified document image segmentation via query decomposition and heterogeneous mixed learning（DocSAM：通过查询分解与异构混合学习实现统一文档图像分割）. 载于 CVPR（计算机视觉与模式识别会议）, 2025.

Fuyuan Liu, Dianyu Yu, He Ren, Nayu Liu, Xiaomian Kang, Delai Qiu, Fa Zhang, Genpeng Zhen, Shengping Liu, Jiaen Liang, et al. Parl: Position-aware relation learning network for document layout analysis（PARL：用于文档版面分析的位置感知关系学习网络）. arXiv 预印本 arXiv:2601.07620, 2026.

Yinhan Liu, Myle Ott, Naman Goyal, Jingfei Du, Mandar Joshi, Danqi Chen, Omer Levy, Mike Lewis, Luke Zettlemoyer, and Veselin Stoyanov. Roberta: A robustly optimized BERT pretraining approach（RoBERTa：一种稳健优化的 BERT 预训练方法）. arXiv 预印本 arXiv:1907.11692, 2019.

Ze Liu, Yutong Lin, Yue Cao, Han Hu, Yixuan Wei, Zheng Zhang, Stephen Lin, and Baining Guo. Swin transformer: Hierarchical vision transformer using shifted windows（Swin Transformer：采用移位窗口的层次化视觉 Transformer）. 载于 ICCV（国际计算机视觉会议）, 2021.

Andrea Lodi, Silvano Martello, and Daniele Vigo. Recent advances on two-dimensional bin packing problems（二维装箱问题的最新进展）. Discrete Applied Mathematics（《离散应用数学》）, 2002.

Subhajit Maity, Sanket Biswas, Siladittya Manna, Ayan Banerjee, Josep Lladós, Saumik Bhattacharya, and Umapada Pal. Selfdocseg: A self-supervised vision-based approach towards document segmentation（SelfDocSeg：一种面向文档分割的视觉自监督方法）. 载于 ICDAR（国际文档分析与识别会议）, 2023.

Oikantik Nath, Sahithi Kukkala, Mitesh Khapra, and Ravi Kiran Sarvadevabhatla. IndicDLP: A foundational dataset for multi-lingual and multi-domain document layout parsing（IndicDLP：面向多语言、多领域文档版面解析的基础数据集）. 载于 ICDAR（国际文档分析与识别会议）, 2025.

OpenAI. GPT-4 technical report（GPT-4 技术报告）. arXiv 预印本 arXiv:2303.08774, 2023.

Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter W. J. Staar. Doclaynet: A large human-annotated dataset for document-layout segmentation（DocLayNet：用于文档版面分割的大规模人工标注数据集）. 载于 ACM SIGKDD Conference on Knowledge Discovery and Data Mining（ACM SIGKDD 知识发现与数据挖掘会议）, 2022.

Nikitha S. R., Tarun Ram Menta, and Mausoom Sarkar. Dopta: Improving document layout analysis using patch-text alignment（DoPTA：利用图像块与文本对齐改善文档版面分析）. arXiv 预印本 arXiv:2412.12902, 2024.

Shaoqing Ren, Kaiming He, Ross Girshick, and Jian Sun. Faster R-CNN: Towards real-time object detection with region proposal networks（Faster R-CNN：通过区域提议网络实现实时目标检测）. 载于 NeurIPS（神经信息处理系统大会）, 2015.

Zejiang Shen, Kaixuan Zhang, and Melissa Dell. A large dataset of historical japanese documents with complex layouts（具有复杂版面的历史日文文档大型数据集）. 载于 CVPRW（计算机视觉与模式识别会议研讨会）, 2020.

Zejiang Shen et al. Layoutparser: A unified toolkit for deep learning based document image analysis（LayoutParser：用于基于深度学习的文档图像分析的统一工具包）. 载于 ICDAR（国际文档分析与识别会议）, 2021.

Ke Sun, Yang Zhao, Borui Jiang, Tianheng Cheng, Bin Xiao, Dong Liu, Yadong Mu, Xinggang Wang, Wenyu Liu, and Jingdong Wang. High-resolution representations for labeling pixels and regions（用于像素与区域标注的高分辨率表征）. arXiv 预印本 arXiv:1904.04514, 2019.

Yunjie Tian, Qixiang Ye, and David Doermann. YOLOv12: Attention-centric real-time object detectors（YOLOv12：以注意力为核心的实时目标检测器）. 载于 NeurIPS（神经信息处理系统大会）, 2025.

Ao Wang, Hui Chen, Lihao Liu, Kai Chen, Zijia Lin, Jungong Han, and Guiguang Ding. Yolov10: Real-time end-to-end object detection（YOLOv10：实时端到端目标检测）. 载于 NeurIPS（神经信息处理系统大会）, 2024a.

Bin Wang, Tianyao He, Linke Ouyang, Fan Wu, Zhiyuan Zhao, Tao Chu, Yuan Qu, Zhenjiang Jin, Weijun Zeng, Ziyang Miao, Bangrui Xu, Junbo Niu, Mengzhang Cai, Jiantao Qiu, Qintong Zhang, Dongsheng Ma, Yuefeng Sun, Hejun Dong, Wenzheng Zhang, Jutao Xiao, Jiayong Shi, Pengyu Liao, Xiaomeng Zhao, Huaping Zhong, Liqun Wei, Jing Yu, Jie Yang, Wei Li, Shasha Wang, Qianqian Wu, Xuanhe Zhou, Weijia Li, Zhenxiang Li, Zhongying Tu, Jiang Wu, Lijun Wu, Chao Xu, Kai Chen, Wentao Zhang, Yu Qiao, Bowen Zhou, Dahua Lin, and Conghui He. Mineru2.5-pro: Pushing the limits of data-centric document parsing at scale（MinerU2.5-Pro：突破大规模数据驱动文档解析的极限）. arXiv 预印本 arXiv:2604.04771, 2026.

Huiyu Wang, Yukun Zhu, Bradley Green, Hartwig Adam, Alan L. Yuille, and Liang-Chieh Chen. Axial-deeplab: Stand-alone axial-attention for panoptic segmentation（Axial-DeepLab：用于全景分割的独立轴向注意力）. 载于 ECCV（欧洲计算机视觉会议）, 2020.

Jiawei Wang, Kai Hu, and Qiang Huo. DLAFormer: An end-to-end transformer for document layout analysis（DLAFormer：用于文档版面分析的端到端 Transformer）. 载于 ICDAR（国际文档分析与识别会议）, 2024b.

Shuo Wang, Chunlong Xia, Feng Lv, and Yifeng Shi. RT-DETRv3: Real-time end-to-end object detection with hierarchical dense positive supervision（RT-DETRv3：采用层次化密集正样本监督的实时端到端目标检测）. 载于 IEEE/CVF Winter Conference on Applications of Computer Vision（IEEE/CVF 计算机视觉应用冬季会议）, 2025.

Wenhai Wang, Jifeng Dai, Zhe Chen, Zhenhang Huang, Zhiqi Li, Xizhou Zhu, Xiaowei Hu, Tong Lu, Lewei Lu, Hongsheng Li, et al. InternImage: Exploring large-scale vision foundation models with deformable convolutions（InternImage：利用可变形卷积探索大规模视觉基础模型）. 载于 CVPR（计算机视觉与模式识别会议）, 2023.

Xiaolong Wang, Ross B. Girshick, Abhinav Gupta, and Kaiming He. Non-local neural networks（非局部神经网络）. 载于 CVPR（计算机视觉与模式识别会议）, 2018.

Saining Xie, Ross B. Girshick, Piotr Dollár, Zhuowen Tu, and Kaiming He. Aggregated residual transformations for deep neural networks（面向深度神经网络的聚合残差变换）. 载于 CVPR（计算机视觉与模式识别会议）, 2017.

An Yang, Anfeng Li, Baosong Yang, Beichen Zhang, Binyuan Hui, Bo Zheng, Bowen Yu, et al. Qwen3 technical report（Qwen3 技术报告）. arXiv 预印本 arXiv:2505.09388, 2025.

Shi Yu, Chaoyue Tang, Bokai Xu, Junbo Cui, Junhao Ran, Yukun Yan, Zhenghao Liu, Shuo Wang, Xu Han, Zhiyuan Liu, and Maosong Sun. Visrag: Vision-based retrieval-augmented generation on multi-modality documents（VisRAG：多模态文档上基于视觉的检索增强生成）. 载于 ICLR（国际学习表征会议）, 2025.

Xinlei Yu, Chengming Xu, Zhangquan Chen, Yudong Zhang, Shilin Lu, Cheng Yang, Jiangning Zhang, Shuicheng Yan, and Xiaobin Hu. Visual document understanding and reasoning: A multi-agent collaboration framework with agent-wise adaptive test-time scaling（视觉文档理解与推理：具备逐智能体自适应测试时扩展能力的多智能体协作框架）. 载于 CVPR（计算机视觉与模式识别会议）, 2026.

Hao Zhang, Feng Li, Shilong Liu, Lei Zhang, Hang Su, Jun Zhu, Lionel M. Ni, and Heung-Yeung Shum. DINO: DETR with improved denoising anchor boxes for end-to-end object detection（DINO：采用改进去噪锚框、用于端到端目标检测的 DETR）. 载于 ICLR（国际学习表征会议）, 2023a.

Junyi Zhang, Jiaqi Guo, Shizhao Sun, Jian-Guang Lou, and Dongmei Zhang. Layoutdiffusion: Improving graphic layout generation by discrete diffusion probabilistic models（LayoutDiffusion：利用离散扩散概率模型改善图形版面生成）. 载于 ICCV（国际计算机视觉会议）, 2023b.

Ning Zhang, Hiuyi Cheng, Jiayu Chen, Zongyuan Jiang, Jun Huang, Yang Xue, and Lianwen Jin. M2doc: A multi-modal fusion approach for document layout analysis（M2Doc：用于文档版面分析的多模态融合方法）. 载于 AAAI（AAAI 人工智能会议）, 2024.

Zirui Zhang, Yaping Zhang, Lu Xiang, Yang Zhao, Feifei Zhai, Yu Zhou, and Chengqing Zong. Promptdla: A domain-aware prompt document layout analysis framework with descriptive knowledge as a cue（PromptDLA：以描述性知识为线索、具备领域感知能力的提示式文档版面分析框架）. IEEE TMM（《IEEE 多媒体汇刊》）, 2026.

Xu Zhong, Jianbin Tang, and Antonio Jimeno-Yepes. Publaynet: Largest dataset ever for document layout analysis（PubLayNet：迄今最大的文档版面分析数据集）. 载于 ICDAR（国际文档分析与识别会议）, 2019.

Zhuofan Zong, Guanglu Song, and Yu Liu. DETRs with collaborative hybrid assignments training（采用协作式混合分配训练的 DETR）. 载于 ICCV（国际计算机视觉会议）, 2023.

### 附录目录

| 章节 | 原 PDF 页码 |
|---|---:|
| A 更多实现细节 | 15 |
| B 基准与对比方法细节 | 17 |
| B.1 公开基准详情 | 17 |
| B.2 对比方法 | 18 |
| C 更多实验 | 19 |
| C.1 在更多对比数据集上的结果 | 19 |
| C.2 鲁棒性评估 | 19 |
| C.3 热力图可视化 | 20 |
| C.4 MeshLayout-1M 上基于设计启发式的指标评估评估 [原文如此] | 20 |
| C.5 预训练数据量消融 | 21 |
| C.6 MeshLayout-1M 预训练对长尾分布的影响 | 21 |
| D 页面轴向版面注意力（PALA）的补充分析 | 23 |
| D.1 不同局部注意力的更多分析与比较 | 23 |
| D.2 区分 PALA 与 Criss-Cross 及 Axial Attention | 24 |
| D.3 Area Attention 与 PALA：PALA 总是更高效吗？ | 25 |
| E Mesh-candidate BestFit 细节 | 27 |
| E.1 基于 DocBank 的元素池构建 | 27 |
| E.2 尺度分层候选采样 | 27 |
| E.3 Mesh-candidate BestFit 算法 | 27 |
| F MeshLayout-1M 的视觉诊断 | 29 |
| F.1 合成文档展示 | 29 |
| F.2 版面多样性 | 29 |
| F.3 元素尺度与形状分布 | 31 |
| G 版面分析示例 | 32 |
| H 局限性与未来工作 | 35 |

### A 更多实现细节

**训练细节。** 所有 DocLayout-YOLO 变体首先在 MeshLayout-1M 上预训练，随后在各下游基准上微调。两个阶段均使用 $1600\times1600$ 输入分辨率，全局批大小为 64，分布在 8 张 H200 GPU 上。我们采用 SGD，动量为 0.9，权重衰减为 $5\times10^{-4}$。对于下游微调，初始学习率设为 0.02，并线性衰减到 $2\times10^{-4}$。预训练进行 50 个轮次，下游微调进行 500 个轮次。遵循 YOLOv12 随尺度变化的数据增强策略，下游微调时，N/S/M/L/X 变体分别使用 0/0/0/0.15/0.20 的 Mixup 比率和 0/0/0/0.50/0.60 的复制粘贴比率。详细超参数总结于表 S1。在与实时检测器的比较中，YOLOv8、YOLOv10、YOLOv11 和基线 YOLOv12 均在各下游数据集上从头训练，使用完全相同的输入分辨率、优化器和学习率，并作少量调整以确保公平比较。对于专用 DLA 方法，我们报告其原始论文提供的结果。

**表 S1：DocLayout-YOLO 的 MeshLayout-1M 预训练与下游微调超参数。**

| 分组 | 超参数 | MeshLayout-1M 预训练 | 下游微调 |
|---|---|---|---|
| 训练配置 | 模型尺度 | N/S/M/L/X | N/S/M/L/X |
| 训练配置 | 输入分辨率 | $1600\times1600$ | $1600\times1600$ |
| 训练配置 | 最大轮次数 | 50 | 500 |
| 训练配置 | 优化器 | SGD | SGD |
| 训练配置 | 动量 | 0.9 | 0.9 |
| 训练配置 | 全局批大小 | 64 | 64 |
| 训练配置 | GPU 数量 | 8 | 8 |
| 训练配置 | 权重衰减 | $5\times10^{-4}$ | $5\times10^{-4}$ |
| 训练配置 | 预热轮次数 | 3 | 3 |
| 训练配置 | 预热动量 | 0.8 | 0.8 |
| 训练配置 | 预热偏置学习率 | 0.0 | 0.0 |
| 训练配置 | 初始学习率 | 0.02 | 0.02 |
| 训练配置 | 最终学习率 | $2\times10^{-4}$ | $2\times10^{-4}$ |
| 训练配置 | 学习率策略 | 线性衰减 | 线性衰减 |
| 损失参数 | 边界框损失增益 | 7.5 | 7.5 |
| 损失参数 | 分类损失增益 | 0.5 | 0.5 |
| 损失参数 | DFL 损失增益 | 1.5 | 1.5 |
| 增强参数 | HSV 色调增强 | 0.015 | 0.015 |
| 增强参数 | HSV 饱和度增强 | 0.7 | 0.7 |
| 增强参数 | HSV 明度增强 | 0.4 | 0.4 |
| 增强参数 | 平移增强 | 0.1 | 0.1 |
| 增强参数 | 缩放增强 | 0.5 | 0.5 |
| 增强参数 | Mosaic 增强 | 1.0 | 1.0 |
| 增强参数 | Mixup 增强 | 0 | 0/0/0/0.15/0.20 |
| 增强参数 | 复制粘贴增强 | 0 | 0/0/0/0.50/0.60 |
| 增强参数 | 关闭 Mosaic 的轮次数 | 10 | 10 |

**架构细节。** DocLayout-YOLO 保留了基线 YOLOv12 的宏观架构与缩放配置，例如 R-ELAN 特征聚合。注意力块的数量与位置也保持不变。在每个块内部，我们保留原始的查询、键和值投影、输出投影、位置编码分支、MLP、归一化层及残差连接。唯一的架构修改是将 Area Attention 替换为 PALA。

**YOLOv26 实现。** 我们仔细调整 YOLOv26，以获得最优性能并保证公平比较。具体而言，每个模型均在 $1600\times1600$ 输入分辨率下，使用 8 张 NVIDIA H200 GPU 和 64 的全局批大小训练 500 个轮次。遵循 YOLOv26，我们采用 MuSGD，初始学习率为 0.02，动量为 0.937，权重衰减为 $5\times10^{-4}$。学习率线性衰减到 $2\times10^{-4}$，并进行 3 个轮次的预热。训练期间启用自动混合精度（automatic mixed precision，AMP）。我们采用与 YOLOv12 相同的数据增强设置。

**RT-DETRv3 实现。** 我们也仔细调整 RT-DETR 设置，以获得最优性能并保证公平比较。遵循默认设置，所有模型均在 8 张 NVIDIA H200 GPU 上训练，每张 GPU 使用 8 张图像，全局批大小为 64，并使用相应的 ImageNet 预训练权重初始化。评估分辨率固定为 $1600\times1600$，而训练采用 1216～1984 像素的多尺度输入，该范围由官方 RT-DETRv3 增强范围按比例缩放得到。训练流程包括随机光度畸变、扩展、裁剪、水平翻转和多尺度尺寸调整。我们采用 AdamW，基础学习率为 $4\times10^{-4}$，权重衰减为 $1\times10^{-4}$，梯度裁剪的最大范数为 0.1，并使用衰减率为 0.9999 的指数移动平均（exponential moving average，EMA）。R18/R34/R50 的骨干学习率乘数为 0.1，R101 为 0.01。启用 AMP，目标查询数固定为 300。考虑到数据集规模差异显著，D4LA、M6Doc、HJDataset 和 PRIMA-LAD 分别训练 96/120/240/500 个轮次，预热迭代数分别为 700/450/120/50。

**TensorRT 细节。** GPU 延迟在单张 NVIDIA H200 GPU 上使用 TensorRT 10.16.1.11 测量，批大小为 1，静态输入形状为 $1\times3\times1600\times1600$。模型导出为经过简化的 FP32 ONNX 图，使用 opset 17，并分别编译成 FP32 和 FP16 引擎。预热 30 次迭代后，对同步引擎执行进行至少 5,000 次迭代且至少 60 秒的测量，不包括数据传输、预处理、解码和非极大值抑制（non-maximum suppression，NMS）。我们报告平均延迟，所有报告测量值的 95% 置信区间半宽均低于 0.10 ms。

### B 基准与对比方法细节

#### B.1 公开基准详情

为评估 DocLayout-YOLO 在不同文档场景中的泛化能力，我们在四个主要 DLA 基准上开展实验，包括 M6Doc（Cheng et al., 2023）、D4LA（Da et al., 2023）、HJDataset（Shen et al., 2020）和 PRIMA-LAD¹（Antonacopoulos et al., 2009）。这些基准涵盖广泛的文档类型，包括现代和历史文档、多语言内容及多样的版面结构。

此外，我们在另外三个广泛使用的文档版面数据集上提供补充评估，包括 PubLayNet（Zhong et al., 2019）、DocLayNet（Pfitzmann et al., 2022）和 IndicDLP（Nath et al., 2025），进一步考察本方法跨不同文档领域的鲁棒性。所有基准的详细统计，包括数据量、文档类型、类别及示例图像，汇总于表 S2。

**表 S2：用于评估的公开基准详情。**

| 基准 | 训练数 | 测试数 | 文档类型 | 类别 | 示例文档 |
|---|---:|---:|---|---|---|
| M6Doc | 5,448 | 2,724 | 书籍、杂志、报纸、笔记、论文、试卷、教科书 | 74 个细粒度类别 | 原 PDF 表中示例图像 |
| D4LA | 8,868 | 2,224 | 预算、电子邮件、表单、发票、信件、备忘录、新闻、演示文稿、简历 | 文档标题（DocTitle）、列表文本（ListText）、信头（LetterHead）、问题（Question）、区域列表（RegionList）、表名（TableName）、图名（FigureName）、底部内容（Footer）、数字（Number）、段落标题（ParaTitle）、区域标题（RegionTitle）、信件称呼（LetterDear）、其他文本（OtherText）、摘要（Abstract）、表格（Table）、公式（Equation）、页眉（PageHeader）、目录（Catalog）、段落文本（ParaText）、日期（Date）、信件签名（LetterSign）、区域键值（RegionKV）、作者（Author）、图像（Figure）、参考文献（Reference）、页脚（PageFooter）、页码（PageNumber） | 原 PDF 表中示例图像 |
| HJDataset | 1,589 | 341 | 主要内容、广告、索引、其他 | 正文（Body）、行（Row）、标题（Title）、传记（Bio）、姓名（Name）、职位（Position）、其他（Other） | 原 PDF 表中示例图像 |
| PRIMA-LAD | 382 | 96 | 杂志、技术文章 | 图像（Figure）、表格（Table）、段落（Paragraph）、页眉（Header）、页码（Page-number）、浮动内容（Floating）、图注（Caption）、署名（Credit）、首字下沉（Drop-capital）、标题（Heading）、页脚（Footer） | 原 PDF 表中示例图像 |
| PubLayNet | 335,703 | 11,245 | 学术 | 文本（Text）、标题（Title）、列表（List）、表格（Table）、图像（Figure） | 原 PDF 表中示例图像 |
| DocLayNet | 69,103 | 6,480 | 财务、科学、专利、手册、法律、招标文件 | 图注（Caption）、脚注（Footnote）、公式（Formula）、列表项（List-item）、页脚（Page-footer）、页眉（Page-header）、图片（Picture）、节标题（Section-header）、表格（Table）、文本（Text）、标题（Title） | 原 PDF 表中示例图像 |
| IndicDLP | 95,824 | 11,994 | 法案与规章、宣传册、表单、杂志、手册、报纸、通知、小说、试卷、研究论文、教学大纲、教科书 | 42 个细粒度类别 | 原 PDF 表中示例图像 |

¹ 对于 PRIMA-LAD，我们使用实验中采用的 11 类标注配置，478 页中包含 8,942 个有效区域。

#### B.2 对比方法

我们将 DocLayout-YOLO 与三类具有代表性的方法比较：（1）实时目标检测器，侧重于取得良好的精度与效率权衡；（2）专用单模态 DLA 方法，主要依赖视觉信息理解文档版面；（3）专用多模态 DLA 方法，通过视觉语言建模利用额外的 OCR 标注与语言语义表征。完整对比方法列表汇总于表 S3。

**表 S3：对比方法汇总。**

| 类别 | 方法 |
|---|---|
| 实时检测器 | YOLOv8（Jocher et al., 2023）、YOLOv10（Wang et al., 2024a）、YOLOv11（Khanam & Hussain, 2024）、YOLOv12（Tian et al., 2025）、YOLOv26（Jocher et al., 2026）、RT-DETRv3（Wang et al., 2025） |
| 专用 DLA：单模态 | LayoutParser（Shen et al., 2021）、DocSegTr（Biswas et al., 2022）、DiT-L（Li et al., 2022）、SelfDocSeg（Maity et al., 2023）、SwinDocSegmenter（Banerjee et al., 2023）、GraphKD（Banerjee et al., 2024a）、SemiDocSeg（Banerjee et al., 2024b）、RoDLA（Chen et al., 2024b）、PARL（Liu et al., 2026）、HybriDLA（Chen et al., 2026）、DocSAM（Li et al., 2025） |
| 专用 DLA：多模态 | LayoutLMv3（Huang et al., 2022）、VGT（Da et al., 2023）、M2Doc（Zhang et al., 2024）、DoPTA-HR（R. et al., 2024）、PromptDLA（Zhang et al., 2026） |

### C 更多实验

#### C.1 在更多对比数据集上的结果

如表 S4 所示，我们进一步在三个额外的文档版面基准上评估 DocLayout-YOLO，包括 PubLayNet、DocLayNet 和 IndicDLP。相较 YOLOv12-X，DocLayout-YOLO-X 分别稳定地提高 0.6%/1.3%/0.6% mAP。在具有不同文档领域和版面特征的数据集上均获得稳定增益，进一步表明了所提出方法的泛化能力。

**表 S4：在 PubLayNet、DocLayNet 和 IndicDLP 上的对比结果。**

| 方法 | PubLayNet | DocLayNet | IndicDLP |
|---|---:|---:|---:|
| YOLOv12-X | 96.9 | 81.0 | 56.3 |
| **DocLayout-YOLO-X** | **97.5** | **82.3** | **56.9** |

#### C.2 鲁棒性评估

表 S5 和 S6 分别在 PubLayNet-P 与 M6Doc-P 上，评估了 12 种文档扰动、每种 3 个严重程度下的鲁棒性（Chen et al., 2024b）。P-Avg 表示所有扰动下的平均精度，mRD 衡量归一化的性能退化；更低的 mRD 和更高的 P-Avg 表示更强的鲁棒性。在 PubLayNet-P 上，DocLayout-YOLO-X 达到 97.5% 的干净样本 mAP、85.8% 的 P-Avg 和 48.7 的 mRD，相比基线 YOLOv12-X，干净样本 mAP/P-Avg 提高 0.6%/9.1%，mRD 降低 30.7。其 P-Avg 还比此前最佳的 RoDLA 高 15.8%，同时 mRD 降低 67.3。在 M6Doc-P 上，DocLayout-YOLO-X 达到 75.5% 的干净样本 mAP、68.0% 的 P-Avg 和 118.8 的 mRD，相比基线 YOLOv12-X，干净样本 mAP/P-Avg 提高 1.5%/0.3%，mRD 降低 2.6。相较此前最佳结果，其进一步使干净样本 mAP/P-Avg 提高 5.3%/6.3%，mRD 降低 28.8。这些结果表明，DocLayout-YOLO 能提高对多种文档退化的鲁棒性，而不会明显损害干净文档上的性能。

**表 S5：PubLayNet-P 数据集上的鲁棒性评估。** V、L、T 分别表示视觉、版面和文本模态。最佳与次佳结果分别用粗体和下划线突出显示。空间扰动为 P1～P3，内容扰动为 P4～P5，不一致扰动为 P6～P8，模糊为 P9～P10，噪声为 P11～P12。

| 方法 | 骨干网络 | V | L | T | 干净样本 | 空间 P1 | 空间 P2 | 空间 P3 | 内容 P4 | 内容 P5 | 不一致 P6 | 不一致 P7 | 不一致 P8 | 模糊 P9 | 模糊 P10 | 噪声 P11 | 噪声 P12 | P-Avg↑ | mRD↓ |
|---|---|:---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LayoutParser（Shen et al., 2021） | ResNeXt（Xie et al., 2017） | ✓ | ✗ | ✗ | 89.0 | 35.8 | 78.1 | 68.0 | 84.8 | 45.9 | 79.0 | 85.8 | 82.6 | 51.4 | 31.1 | 53.6 | 0.3 | 58.0 | 212.7 |
| Faster R-CNN（Ren et al., 2015） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 90.2 | **44.2** | 75.3 | 74.3 | 78.9 | 53.2 | 81.4 | 82.7 | 80.2 | 80.6 | 63.2 | 55.7 | 24.3 | 66.2 | 175.5 |
| DocSegTr（Biswas et al., 2022） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 90.4 | 28.3 | 76.0 | 71.2 | 85.2 | 46.2 | 69.3 | 86.2 | 68.9 | 50.8 | 19.8 | 60.2 | 0.4 | 55.2 | 233.0 |
| Mask R-CNN（He et al., 2017） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 91.0 | <u>40.0</u> | 74.0 | 71.8 | 76.9 | 48.7 | 79.0 | 80.6 | 77.4 | 78.2 | 54.2 | 55.1 | 31.9 | 64.0 | 192.7 |
| SwinDocSegmenter（Banerjee et al., 2023） | Swin（Liu et al., 2021） | ✓ | ✗ | ✗ | 93.7 | 39.0 | 83.3 | 61.3 | 88.9 | 46.6 | 87.9 | 88.1 | 86.6 | 37.3 | 29.2 | 36.1 | 0.5 | 57.1 | 214.4 |
| Cascade R-CNN（Cai & Vasconcelos, 2018） | DiT（Li et al., 2022） | ✓ | ✗ | ✗ | 94.5 | 31.9 | **86.5** | **82.2** | 92.1 | 79.6 | 87.2 | 92.0 | 91.6 | 93.8 | 71.3 | 69.9 | 41.8 | <u>76.7</u> | 95.8 |
| Cascade R-CNN（Cai & Vasconcelos, 2018） | LayoutLMv3（Huang et al., 2022） | ✓ | ✓ | ✓ | 95.1 | 32.7 | <u>85.9</u> | 79.8 | 92.3 | 68.5 | 86.5 | 93.1 | 86.7 | 82.9 | 47.0 | <u>82.1</u> | <u>45.1</u> | 73.6 | 116.2 |
| Co-DINO（Zong et al., 2023） | Swin（Liu et al., 2021） | ✓ | ✗ | ✗ | 94.3 | 22.4 | 43.0 | 24.7 | 92.6 | 56.8 | 86.4 | 72.6 | 75.8 | 35.0 | 20.2 | 55.4 | 14.9 | 50.0 | 254.1 |
| Cascade R-CNN（Cai & Vasconcelos, 2018） | InternImage（Wang et al., 2023） | ✓ | ✗ | ✗ | 94.1 | 27.7 | 80.2 | 79.7 | 89.6 | 56.6 | 83.8 | 91.6 | 89.6 | 84.9 | 54.0 | 55.2 | 0.2 | 66.1 | 141.9 |
| DINO（Zhang et al., 2023a） | InternImage（Wang et al., 2023） | ✓ | ✗ | ✗ | 95.4 | 34.4 | 82.2 | **82.2** | 92.3 | 57.7 | 91.7 | 92.8 | 92.1 | 90.9 | 63.4 | 47.3 | 1.3 | 69.0 | 120.7 |
| Co-DINO（Zong et al., 2023） | InternImage（Wang et al., 2023） | ✓ | ✗ | ✗ | 94.2 | 19.1 | 48.3 | 35.7 | 91.3 | 60.6 | 87.9 | 81.4 | 87.6 | 37.9 | 27.9 | 49.7 | 11.2 | 53.2 | 230.3 |
| RoDLA（Chen et al., 2024b） | InternImage（Wang et al., 2023） | ✓ | ✗ | ✗ | 96.0 | 31.6 | 79.3 | 80.6 | 92.9 | 61.6 | 91.6 | 92.6 | 91.6 | 91.3 | 67.7 | 58.8 | 0.3 | 70.0 | 116.0 |
| YOLOv12-X（Tian et al., 2025） | v12-X | ✓ | ✗ | ✗ | <u>96.9</u> | 29.4 | 79.5 | <u>81.7</u> | <u>95.9</u> | <u>87.1</u> | <u>95.0</u> | <u>96.7</u> | <u>95.9</u> | <u>96.2</u> | <u>72.9</u> | 76.9 | 13.2 | <u>76.7</u> | <u>79.4</u> |
| **DocLayout-YOLO-X** | v12-X + PALA | ✓ | ✗ | ✗ | **97.5** | 21.2 | 85.7 | 80.3 | **97.4** | **96.4** | **97.5** | **97.2** | **96.3** | **96.4** | **76.3** | **89.3** | **95.9** | **85.8** | **48.7** |

**表 S6：M6Doc-P 数据集上的鲁棒性评估。**

| 方法 | 骨干网络 | V | L | T | 干净样本 | P-Avg↑ | mRD↓ |
|---|---|:---:|:---:|:---:|---:|---:|---:|
| DocSegTr（Biswas et al., 2022） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 60.3 | 43.2 | 212.6 |
| Mask R-CNN（He et al., 2017） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 61.9 | 48.9 | 216.7 |
| Faster R-CNN（Ren et al., 2015） | ResNet（He et al., 2016） | ✓ | ✗ | ✗ | 62.0 | 49.6 | 192.2 |
| SwinDocSegmenter（Banerjee et al., 2023） | Swin（Liu et al., 2021） | ✓ | ✗ | ✗ | 47.1 | 39.7 | 239.2 |
| Cascade R-CNN（Cai & Vasconcelos, 2018） | DiT（Li et al., 2022） | ✓ | ✗ | ✗ | 70.2 | 60.6 | 164.8 |
| Cascade R-CNN（Cai & Vasconcelos, 2018） | LayoutLMv3（Huang et al., 2022） | ✓ | ✓ | ✓ | 64.3 | 57.0 | 176.1 |
| RoDLA（Chen et al., 2024b） | InternImage（Wang et al., 2023） | ✓ | ✗ | ✗ | 70.0 | 61.7 | 147.6 |
| YOLOv12-X（Tian et al., 2025） | v12-X | ✓ | ✗ | ✗ | <u>74.0</u> | <u>67.7</u> | <u>121.4</u> |
| **DocLayout-YOLO-X** | v12-X + PALA | ✓ | ✗ | ✗ | **75.5** | **68.0** | **118.8** |

#### C.3 热力图可视化

为进一步考察所学习的空间表征，我们可视化了 X 尺度 YOLOv12 基线与 DocLayout-YOLO 的第三阶段（S3）特征图。如图 S1 所示，基线 YOLOv12 产生相对弥散的响应，尤其是在具有密集文本、表格结构与多栏版面的页面上。相比之下，DocLayout-YOLO 产生更具结构性的激活，与文本块、表格单元格、图像及其周围边界等语义上有意义的区域更加对齐。这种改进在具有强水平与垂直依赖的版面中尤为明显：PALA 能在相关元素之间保持连贯响应，同时抑制无关背景激活。这些观察在定性上支持 PALA 能够增强长程页面上下文建模与文档版面分析中元素级表征的有效性。

**图 S1：** YOLOv12 与所提出的 DocLayout-YOLO 的热力图比较。相比 YOLOv12，DocLayout-YOLO 表现出更清晰的目标感知能力。

#### C.4 MeshLayout-1M 上基于设计启发式的指标评估评估 [原文如此]

本节定量评估 Mesh-Candidate BestFit 生成的合成文档页面是否符合人类设计原则。评估采用 Align 和 Density 指标，分别从文档对齐与密度方面衡量版面的美学质量。对于 Align，我们使用 LayoutGAN++（Kikuchi et al., 2021; Li et al., 2021）的指标，测量文档中元素的对齐程度：

$$
L_{\mathrm{alg}}=\sum_{i=1}^{N}\min\begin{pmatrix}
g(\Delta x_i^L),g(\Delta x_i^C),g(\Delta x_i^R)\\
g(\Delta y_i^T),g(\Delta y_i^C),g(\Delta y_i^B)
\end{pmatrix}. \tag{5}
$$

其中，$x_i^*\ (*=L,C,R)$、$y_i^*\ (*=T,C,B)$ 分别表示文档中第 $i$ 个元素在 $x$ 轴上的左侧/中心/右侧，以及在 $y$ 轴上的顶部/中心/底部，$g(x)=-\log(1-x)$，$\Delta x_i^*\ (*=L,C,R)$ 计算如下：

$$
\Delta x_i^*=\min_{\forall j\ne i}|x_i^*-x_j^*|. \tag{6}
$$

$\Delta y_i^*\ (*=T,C,B)$ 可类似计算。对于 Density，我们计算版面中已填充面积的比例：

$$
L_{\mathrm{dst}}=\frac{\sum_{i=1}^{N}|e_i|}{|L|}. \tag{7}
$$

其中，$|e_i|$ 表示 $L$ 中元素 $e_i$ 的面积，$|L|$ 表示整张版面的面积。对于 Align，数值越低表示文档越对齐；对于 Density，数值越大表示版面越紧凑、密集。实验结果见表 S7。结果表明，Mesh-candidate BestFit 方法在对齐与密度两方面均显著优于扩散和随机方法。视觉结果进一步证实，Mesh-candidate BestFit 生成的版面更加符合人类审美标准与设计原则。

**表 S7：不同版面生成方法的定量比较。**

| 版面生成方法 | Align↓ | Density↑ |
|---|---:|---:|
| 随机 | 0.0171 | 0.259 |
| 扩散（LACE） | 0.0032 | 0.476 |
| **Mesh-candidate BestFit（本文）** | **0.0009** | **0.645** |

#### C.5 预训练数据量消融

**图 S2：** 预训练数据量消融。

我们对 MeshLayout-1M 的预训练数据量开展消融实验。具体而言，使用不同数量的 Mesh-candidate 生成数据对 DocLayout-YOLO-L 预训练，数据量从 0 到 1M 页不等，随后在 M6Doc 上微调。结果如图 S2 所示。总体上，随着预训练数据量增加，模型性能得到提升，尽管在中间规模出现小幅波动。mAP 从无预训练时的 73.7%，提升到使用 500K 页时的 74.4%，在 800K 页时达到 74.8%，在 1M 页时进一步提高到 75.1%。这些结果表明，扩大合成预训练语料库具有明确收益，但在数据量较大时，边际增益会减小。

#### C.6 MeshLayout-1M 预训练对长尾分布的影响

我们分析了长尾类别分布下 MeshLayout-1M 预训练的影响。M6Doc 和 PRIMA-LAD 上的逐类别结果分别见图 S3a 和 S3b。左侧 $y$ 轴报告每个类别的 AP 变化，右侧 $y$ 轴表示实例数量。$\Delta\mathrm{mAP}$ 表示 DocLayout-YOLO-L 使用与不使用 MeshLayout-1M 预训练时的性能差异。

总体上，MeshLayout-1M 在广泛的下游类别上带来改进，但少数类别出现性能退化。若干低频类别的增益尤其明显，表明多样化合成预训练能够在一定程度上缓解长尾效应。例如，在 M6Doc 上，译者（translator）、目录（catalog）与编者按（editor’s note）的提升分别达到 7.6%、10.8% 和 9.3%。在 PRIMA-LAD 上，图注（caption）、署名（credit）与表格（table）分别提高 10.4%、11.2% 和 12.4%。

图 S3 子图：（a）M6Doc；（b）PRIMA-LAD。

**图 S3：** 逐类别指标分析。左侧 Y 轴表示逐类别 AP，右侧 Y 轴表示各类别实例数量。

### D 页面轴向版面注意力（PALA）的补充分析

#### D.1 不同局部注意力的更多分析与比较

**与不同注意力机制的比较。** 图 S4 展示了 PALA 与具有代表性的局部注意力机制之间的结构差异。Swin Attention 将交互限制在局部窗口内，而 Area Attention 将特征图划分为互不相交的区域，阻止跨区域边界的直接上下文聚合。Criss-Cross Attention 沿两个空间轴并行扩展交互，但对水平与垂直注意力权重进行联合归一化。Axial Attention 则顺序执行分别归一化的逐轴注意力，使第二个方向依赖于第一个方向的输出。相比之下，PALA 并行执行水平与垂直注意力，并分别归一化，使两个方向的上下文独立建模，同时保留两个页面轴上的长程依赖。这一设计保留了互补的水平与垂直结构线索，同时避免局部分区、跨轴竞争或方向顺序依赖。

**图 S4：** 具有代表性的局部注意力机制与所提出 PALA 的比较。

**水平与垂直上下文建模。** 在表 7 的基础上，我们进一步在表 S8 中分离 PALA 的水平与垂直分支。在两个数据集和两种模型尺度上，仅水平分支始终优于仅垂直分支：对于 N/L 模型，M6Doc 上的 mAP 增益分别为 0.2%/1.3%，PRIMA-LAD 上分别为 0.5%/2.1%。我们注意到，这种不对称性与文档元素的几何性质一致。如表 S9 所示，M6Doc 和 PRIMA-LAD 中分别有 89.0% 和 83.8% 的元素宽大于高，分别有 63.9% 和 58.2% 的元素宽高比至少为 2:1。因此，水平注意力能更好地覆盖文本行、标题、图注和表格行等细长结构。逐行上下文也可能具有更强的语义连贯性，因为同一行的 token 通常属于同一个版面元素。尽管如此，垂直注意力对于建模段落栏、表格列、垂直堆叠区域和跨区域对应关系仍具有互补作用。

**表 S8：仅水平、仅垂直及完整 PALA 的比较。**

| 数据集 | 规模 | 仅水平 | 仅垂直 | PALA | $\Delta(H-V)$ |
|---|---|---:|---:|---:|---:|
| M6Doc | N | 64.1 | 63.9 | 65.3 | +0.2 |
| M6Doc | L | 72.7 | 71.4 | 73.7 | +1.3 |
| PRIMA-LAD | N | 60.6 | 60.1 | 62.6 | +0.5 |
| PRIMA-LAD | L | 67.0 | 64.9 | 69.1 | +2.1 |

**为什么 Global Attention 不如 Criss-Cross 和 PALA。** 在表 7 的基础上，我们对 Global Attention 开展诊断分析，如表 S10 所示。Global Attention 在三个变体中取得最高召回率（76.8%），但其精确率显著低于 Criss-Cross 与 PALA（83.0% 对比 86.7%/88.1%），导致 mAP 最低（64.5% 对比 64.7%/65.3%）。较高召回率但较低精确率表明，Global Attention 的性能退化主要源于额外的误检，而非漏检。这说明不受约束的全局交互可能在视觉相似但空间上不相关的文档区域之间引入干扰。相比之下，Criss-Cross 和 PALA 将长程交互约束在页面轴向，在保留结构相关依赖的同时减少无关的跨区域上下文。

**表 S9：官方数据集划分中有效文档元素的几何统计。** 宽高比根据像素空间中轴对齐的边界框计算。

| 数据集 | 边界框数 | 宽大于高 | 宽高比≥2:1 | 宽高比≥4:1 | 平均宽高比 | 几何平均宽高比 |
|---|---:|---:|---:|---:|---:|---:|
| M6Doc | 237,116 | 89.0% | 63.9% | 41.5% | 5.22 | 3.19 |
| PRIMA-LAD | 8,942 | 83.8% | 58.2% | 40.1% | 6.05 | 3.02 |

**表 S10：Global、Criss-Cross 与 PALA 的检测诊断。**

| 数据集 | 注意力 | 精确率 | 召回率 | $\mathrm{mAP}_{50:95}$ |
|---|---|---:|---:|---:|
| M6Doc | Global | 83.0 | 76.8 | 64.5 |
| M6Doc | Criss-Cross | 86.7 | 75.5 | 64.7 |
| M6Doc | PALA | 88.1 | 76.3 | 65.3 |

#### D.2 区分 PALA 与 Criss-Cross 及 Axial Attention

为阐明 PALA、Criss-Cross Attention 与 Axial Attention 的关系，我们沿两个关键维度比较其公式形式。尽管这三种注意力均沿水平轴和垂直轴建模长程上下文，但它们在轴向执行方式（并行与顺序）以及注意力归一化（联合与独立）方面存在差异，如表 S11 所示。

**表 S11：Criss-Cross Attention、Axial Attention 与 PALA 的结构差异。**

| 方法 | 轴向执行方式 | 注意力归一化 |
|---|---|---|
| Criss-Cross Attention | 并行 | 联合 |
| Axial Attention | 顺序 | 独立 |
| PALA | 并行 | 独立 |

**PALA 与 Criss-Cross Attention。** PALA 与 Criss-Cross Attention 均并行聚合水平与垂直上下文。主要区别在于两个轴的注意力权重如何归一化。对于给定查询，令 $s_{\mathrm{hor}}$ 和 $s_{\mathrm{ver}}$ 分别表示其水平与垂直上下文的注意力 logits。Criss-Cross Attention 将两组 logits 拼接起来，并施加联合 softmax：

$$
[A_{\mathrm{hor}}^{\mathrm{CC}},A_{\mathrm{ver}}^{\mathrm{CC}}]=\operatorname{Softmax}([s_{\mathrm{hor}},s_{\mathrm{ver}}]). \tag{8}
$$

因此，水平与垂直上下文在同一个注意力分布内竞争，使一个轴上的强响应可能抑制另一个轴上的注意力。

相比之下，PALA 对两个轴分别归一化：

$$
A_{\mathrm{hor}}^{\mathrm{PALA}}=\operatorname{Softmax}(s_{\mathrm{hor}}),\quad A_{\mathrm{ver}}^{\mathrm{PALA}}=\operatorname{Softmax}(s_{\mathrm{ver}}). \tag{9}
$$

这一设计将水平与垂直上下文视为两个独立的结构信息来源。这种分离非常适合文档版面，因为两个轴通常表示不同关系，例如水平方向的文本行和表格行，以及垂直方向的段落栏和垂直堆叠区域。

**PALA 与 Axial Attention。** PALA 和 Axial Attention 都对水平与垂直注意力分别归一化，但两个轴的执行方式不同。Axial Attention 顺序施加两个方向的注意力：

$$
Y^{\mathrm{Axial}}=\mathcal{A}_{\mathrm{hor}}(\mathcal{A}_{\mathrm{ver}}(X)), \tag{10}
$$

其中，第二次注意力操作接收已经由第一次操作变换后的特征。PALA 则从同一组投影特征并行计算两个方向：

$$
Y_{\mathrm{hor}}=\mathcal{A}_{\mathrm{hor}}(X),\quad Y_{\mathrm{ver}}=\mathcal{A}_{\mathrm{ver}}(X). \tag{11}
$$

任何一个分支都不依赖另一个分支的输出，从而避免顺序依赖和方向顺序敏感性，同时保留两个页面轴上独立归一化的上下文。

**实验结果。** 如表 S12 所示，PALA 在四种设置中的三种取得最佳性能。与“顺序执行＋独立归一化”相比，并行执行始终使 mAP 提高 0.8%～3.2%，说明避免两轴之间的顺序依赖具有益处。与“并行执行＋联合归一化”相比，独立归一化在 M6Doc 上取得相近性能，并在 PRIMA-LAD 上提高 0.2%～2.8% [原文如此]，表明避免跨轴竞争通常能够提供更稳健的结构上下文建模。

**表 S12：PALA 执行与归一化策略的消融研究。**

| 数据集 | 规模 | 并行＋独立（PALA） | 并行＋联合 | 顺序＋独立 |
|---|---|---:|---:|---:|
| M6Doc | N | 65.3 | **65.5** | 63.4 |
| M6Doc | L | **73.7** | 73.1 | 72.9 |
| PRIMA-LAD | N | **62.6** | 59.8 | 59.6 |
| PRIMA-LAD | L | **69.1** | 67.6 | 65.9 |

**总结。** 因此，PALA 通过结合并行轴向执行与独立轴向归一化，与这两种相关设计区分开来。相较 Criss-Cross Attention，PALA 消除了水平与垂直注意力分布之间的竞争；相较 Axial Attention，PALA 消除了两个方向操作之间的顺序依赖。

#### D.3 Area Attention 与 PALA：PALA 总是更高效吗？

一个自然的问题是，PALA 是否总是比 Area Attention 更高效，或者 Area Attention 能否通过更细的区域划分实现更低延迟。我们从理论复杂度与实际推理性能两方面研究这一问题。

**理论分析。** 忽略线性投影后，Global Attention、具有 $A$ 个等大区域的 Area Attention，以及 PALA 的注意力聚合复杂度分别为 $O(BH^2W^2C)$、$O(BH^2W^2C/A)$ 和 $O(BHW(H+W)C)$。令后两者相等，可得复杂度边界：

$$
A^*=\frac{HW}{H+W}. \tag{12}
$$

当 $A<A^*$ 时，PALA 的注意力聚合复杂度低于 Area Attention；而足够细粒度的划分（$A>A^*$）可以使 Area Attention 在理论上更加高效。因此，对于任意区域配置，PALA 并不一定在理论上更高效。我们进一步考察不同区域设置下实际的精度与效率权衡。

**实验设置与结果。** 为公平比较，我们在相同的 $1600\times1600$ 输入分辨率、训练方案与 TensorRT 推理协议下，使用不同区域数量训练 YOLOv12-N。精度与延迟权衡结果见图 S5。对于 Area Attention，记号 $A_{P4}/A_{P5}$ 表示 P4 和 P5 特征层分别使用的区域数量；例如，4/1 是默认 YOLOv12 配置，而 16/4 则在两个层级采用更细的划分。在 $1600\times1600$ 输入分辨率下，$A_{P4}$ 和 $A_{P5}$ 的理论边界 $A^*$ 分别为 50 和 25。考虑 YOLOv12 默认的 4/1 配置，我们进一步评估 1/1、4/2、8/4 和 16/4 配置，考察不同区域划分程度下的精度与效率权衡。

如图 S5 所示，增加区域数量会减小每个注意力区域的尺寸，并通常降低计算延迟。相应地，Area Attention 的 FP32 延迟从 4/1 时的 5.250 ms 降到 16/4 时的 3.650 ms。然而，更细的划分也将上下文限制在越来越小的区域内，导致明显的精度退化：16/4 配置在 M6Doc/PRIMA-LAD 上仅取得 63.0%/57.9% mAP，而默认 4/1 配置为 64.5%/60.4%。相比之下，PALA 以 3.596/1.500 ms 的 FP32/FP16 延迟取得 65.3%/62.6% mAP，既保留完整的水平与垂直交互，又比精度相近的 Area Attention 配置更快。

图 S5 子图：（a）M6Doc，FP32；（b）M6Doc，FP16；（c）PRIMA-LAD，FP32；（d）PRIMA-LAD，FP16。

**图 S5：** Global Attention、不同 $A_{P4}/A_{P5}$ 配置的 Area Attention，以及 PALA 的精度与延迟权衡。

**总结。** 总而言之，Area Attention 并非本质上比 PALA 低效：足够精细的划分可以进一步降低计算成本，但代价是上下文受限与检测精度下降。综上，PALA 通过将高效逐轴注意力与长程文档上下文建模相结合，提供更好的速度与精度权衡。

### E Mesh-candidate BestFit 细节

#### E.1 基于 DocBank 的元素池构建

我们仅使用 DocBank（Li et al., 2020）的训练划分构建元素池，不从任何下游评估基准中提取元素。我们排除 Date 类别，因为它数量稀少、视觉上同质，主要来自 LaTeX 的 `\date...`、`\today` 或期刊模板的 `Dated:` 字段，因而容易产生来源特有的过拟合；同时排除 Section 类别，因为其弱监督标注存在大量碎片化和标签噪声。对于每个标注区域，我们裁剪相应的视觉内容，连同边界框几何信息一并保存，并保留基于 DocBank 分类体系的语义标签。无效框被丢弃，归一化宽度或高度小于 $\epsilon=0.01$ 的元素被移除。这一过滤过程抑制了几乎不提供有用视觉或结构信息的标注碎片及极薄裁剪图块。保留的实例被组织到各类别专属的池中，后续从中构建页面级候选集合。

#### E.2 尺度分层候选采样

直接从完整元素池采样，可能使小元素或狭窄元素占比过高，导致主要内容区域尚未建立稳定结构，页面就已被碎片化区域填满。因此，我们根据归一化尺度，将过滤后的元素划分为大尺度组与小尺度组。当某个元素的归一化宽度和高度均不小于 $\tau_s=0.05$ 时，将其分配至大尺度组；其余有效元素构成小尺度组。对于每张合成页面，按照预定义的大元素与小元素比例 $\rho:(1-\rho)$，分别对两层独立采样，构建大小固定为 $K=500$ 的候选元素集合，其中 $\rho=0.99$。然后将采样子集合并，并随机抽取一个候选元素来初始化页面。这一策略在保留细粒度元素的同时，优先形成主要版面区域。将 BestFit 匹配限制在固定大小的候选集合内，也限制了搜索开销，并引入了页面之间的组成多样性。

#### E.3 Mesh-candidate BestFit 算法

初始化后，Mesh-candidate BestFit 迭代更新页面中的可用区域，并搜索最兼容的元素与区域对。算法 1 总结了 Mesh-candidate BestFit 的完整过程。给定当前版面 $L$，MESHENGINE 根据页面边界以及已放置元素的水平、垂直边界，构建一组互不重叠的空网格。对于候选元素 $e_i$ 和空网格 $g_j$，匹配分数定义为：

$$
\operatorname{match}(e_i,g_j)=\begin{cases}
\dfrac{w_ih_i}{w_jh_j}, & w_i\le w_j\ \text{且}\ h_i\le h_j,\\
0, & \text{其他情况},
\end{cases} \tag{13}
$$

其中，$(w_i,h_i)$ 和 $(w_j,h_j)$ 分别表示元素和网格的宽度与高度。该分数偏好在满足尺寸约束的同时紧凑占据可用区域的候选元素。在每次迭代中，选择分数最高的候选元素与网格对，将候选元素居中放入匹配网格，并重新计算网格划分。当版面包含 $N=35$ 个元素，或不存在分数超过 $fr_{\mathrm{thr}}=10^{-4}$ 的有效匹配对时，生成停止。

版面确定后，创建空白文档画布：宽度采样为 $W\sim U_{\mathrm{int}}(1200,2000)$，宽高关系采样为 $r=H/W\sim U(0.7,1.5)$，并将 $H$ 的上限设为 3000 像素。将每个已放置候选框从归一化坐标映射到画布，再分别沿宽度与高度方向，以从 $U(0.8,0.95)$ 采样的因子围绕其中心独立收缩。随后，将相应元素裁剪图块调整尺寸以适配所得框，并合成到页面上，同时保留其坐标与语义标签作为标注。

**算法 1：Mesh-candidate BestFit 算法。**

**输入：** 元素池 $P$；候选集合大小 $K$；版面最大元素数量 $N$；过滤阈值 $\epsilon$；尺度阈值 $\tau_s$；大元素比例 $\rho$；匹配阈值 $fr_{\mathrm{thr}}$。

**输出：** 生成的版面 $L$。

| 行号 | 操作 |
|---:|---|
| | **阶段 I：元素过滤与尺度感知候选采样** |
| 1 | $P\leftarrow\operatorname{Filter}(P,\epsilon)$； |
| 2 | $P_{\mathrm{large}},P_{\mathrm{small}}\leftarrow\operatorname{ScalePartition}(P,\tau_s)$； |
| 3 | $C_{\mathrm{large}}\leftarrow\operatorname{Sample}(P_{\mathrm{large}},\lfloor\rho K\rfloor)$； |
| 4 | $C_{\mathrm{small}}\leftarrow\operatorname{Sample}(P_{\mathrm{small}},K-\lfloor\rho K\rfloor)$； |
| 5 | $C_{\mathrm{set}}\leftarrow C_{\mathrm{large}}\cup C_{\mathrm{small}}$； |
| | **阶段 II：版面初始化** |
| 6 | $e^*\leftarrow\operatorname{RandomSample}(C_{\mathrm{set}})$； |
| 7 | $L\leftarrow\operatorname{Initialize}(e^*)$； |
| 8 | $C_{\mathrm{set}}\leftarrow C_{\mathrm{set}}\setminus\{e^*\}$； |
| | **阶段 III：迭代网格构建与 BestFit 匹配** |
| 9 | 当 $\lvert L\rvert<N\land C_{\mathrm{set}}\ne\varnothing$ 时执行： |
| | 　// 根据当前版面构建候选区域 |
| 10 | 　$M_{\mathrm{set}}\leftarrow\operatorname{MeshEngine}(L)$； |
| | 　// 初始化最佳元素与区域匹配 |
| 11 | 　$fr_{\max}\leftarrow0$； |
| 12 | 　$e_{\mathrm{best}}\leftarrow\varnothing$； |
| 13 | 　$g_{\mathrm{best}}\leftarrow\varnothing$； |
| | 　// 搜索全局最优 BestFit 匹配 |
| 14 | 　对每个 $e_i\in C_{\mathrm{set}}$ 执行： |
| 15 | 　　对每个 $g_j\in M_{\mathrm{set}}$ 执行： |
| 16 | 　　　$fr\leftarrow\operatorname{Match}(e_i,g_j)$； |
| 17 | 　　　若 $fr>fr_{\max}$，则： |
| 18 | 　　　　$fr_{\max}\leftarrow fr$； |
| 19 | 　　　　$e_{\mathrm{best}}\leftarrow e_i$； |
| 20 | 　　　　$g_{\mathrm{best}}\leftarrow g_j$； |
| 21 | 　　　结束条件分支 |
| 22 | 　　结束内层遍历 |
| 23 | 　结束外层遍历 |
| | 　// 若无有效匹配则终止 |
| 24 | 　若 $e_{\mathrm{best}}=\varnothing\lor fr_{\max}<fr_{\mathrm{thr}}$，则： |
| 25 | 　　跳出循环； |
| 26 | 　结束条件分支 |
| | 　// 放置选中元素并更新候选集合 |
| 27 | 　$L\leftarrow L\cup\{\operatorname{PlaceCenter}(e_{\mathrm{best}},g_{\mathrm{best}})\}$； |
| 28 | 　$C_{\mathrm{set}}\leftarrow C_{\mathrm{set}}\setminus\{e_{\mathrm{best}}\}$； |
| 29 | 结束循环 |
| 30 | 返回 $L$； |

### F MeshLayout-1M 的视觉诊断

本节开展一系列视觉分析，以展示合成预训练数据集的多样性，以及所提出文档合成方法的有效性。

#### F.1 合成文档展示

首先，图 S6 展示了 Mesh-candidate BestFit 生成文档的更丰富可视化。S、M、L 分别表示小、中、大元素，用于指示页面上相对丰富的组成部分。可以看出，我们生成的数据类别丰富，具有较强多样性。它既能生成包含大量小元素的密集版面，也能生成由少量大元素构成的稀疏版面，类似于基于扩散的模型所生成的版面。

**图 S6：** 生成的多样版面及渲染后相应页面的可视化。S、M、L 分别表示小、中、大元素，用于指示页面上相对丰富的组成部分。

#### F.2 版面多样性

接下来，我们对 PubLayNet（图 S7a）、DocBank（图 S7b）和 MeshLayout-1M（图 S7c）的文档版面多样性进行可视化比较。从可视化结果看，PubLayNet 和 DocBank 中的文档版面明显呈现学术论文典型的双栏格式和曼哈顿版面（Manhattan layout），缺乏多样性。相比之下，Mesh-candidate BestFit 生成的文档版面表现出显著的变化与多样性。

图 S7 子图：（a）PubLayNet 的文档版面分布；（b）DocBank 的文档版面分布；（c）MeshLayout-1M 的文档版面分布。

**图 S7：** （a）PubLayNet、（b）DocBank 和（c）MeshLayout-1M 的文档版面分布。$N$ 表示可视化所用文档数量。相比 PubLayNet 或 DocBank 中的双栏学术风格版面，MeshLayout-1M 中由 Mesh-candidate BestFit 合成的文档版面展现出显著的变化与多样性。

#### F.3 元素尺度与形状分布

我们使用归一化的轴对齐边界框，描述完整 MeshLayout-1M 训练划分中全部 14,549,846 个标注的几何性质。图 S8 报告了各类别相对面积与宽高比的边缘分布。这些统计描述了预训练语料库的几何覆盖范围，并不假设任何单一类别遵循单峰分布或标准模板。

**尺度覆盖。** 元素面积中位数从 Paragraph 的页面面积的 0.62%，到 Author 的 27.15% 不等，类别间跨度超过 40 倍。Paragraph 和 Title 的第 5～95 百分位区间较宽，分别为 0.022%～27.29% 和 1.73%～29.59%；而 Caption、Table 与 Abstract 则占据更集中的尺度区间。Paragraph 和 Reference 等高频类别的多峰分布进一步表明，语料库包含若干反复出现的尺寸模式，而非单一元素尺度。

**依赖类别的形状。** 不同语义类别的形状分布差异显著。Caption、Table 与 Abstract 主要呈水平延展，其宽高比中位数分别为 11.50、15.26 和 16.08。相比之下，Figure 和 Author 近似正方形，中位宽高比分别为 1.17 和 1.02，其中分别有 58.1% 和 67.2% 的实例落在近似正方形区间 $[2/3,1.5]$ 内。我们将这些类别特有的分布特征作为生成语料库的属性报告；不能仅凭边缘分布推断合成与真实数据之间的对应关系。

**图 S8：** 完整 MeshLayout-1M 训练划分中各类别元素的几何性质。（a）边界框面积相对页面面积的比例。（b）宽高比。

### G 版面分析示例

此处展示了 D4LA（图 S9）、M6Doc（图 S10）、HJDataset（图 S11）、PRIMA-LAD（图 S12）、PubLayNet（图 S13）、DocLayNet（图 S14）和 IndicDLP（图 S15）上的定性版面分析示例。

**图 S9：** D4LA 上的版面分析示例。

**图 S10：** M6Doc 上的版面分析示例。

**图 S11：** HJDataset 上的版面分析示例。

**图 S12：** PRIMA-LAD 上的版面分析示例。

**图 S13：** PubLayNet 上的版面分析示例。

**图 S14：** DocLayNet 上的版面分析示例。

**图 S15：** IndicDLP 上的版面分析示例。

### H 局限性与未来工作

**跨部署环境的效率。** PALA 借助经过优化的注意力实现取得了良好的实际效率。由于算子内核优化和内存访问的差异，其实际加速幅度可能随硬件平台和推理后端变化。进一步的算子级优化有助于改善其在更广泛部署环境中的可移植性与效率。

**PALA 的建模范围。** PALA 围绕文档版面中占主导的水平与垂直组织结构设计，能够沿两个页面轴高效建模长程上下文。尽管这一设计能够较好覆盖常见文档结构，但对于存在明显旋转、透视畸变或非轴对齐排列的高度不规则版面，更灵活的交互模式可能更加有益。通过自适应方向建模扩展 PALA，是面向此类场景的一个有前景的方向。

**MeshLayout 的合成范围。** MeshLayout 通过可控的几何版面合成着重增加结构多样性，其当前元素池主要由 DocBank 构建。扩展元素来源，可进一步增加内容、语言和视觉外观的多样性。此外，融入更丰富的语义关系与真实文档变化，可进一步缩小合成文档与真实文档之间的差距。

**未来工作。** 后续工作将探索可移植性更强的 PALA 实现，以及面向不规则文档结构的自适应上下文建模。对于 MeshLayout，我们计划扩展多语言、多来源元素池，融入更丰富的语义与视觉变化，进一步提高合成文档预训练的多样性和真实性。
