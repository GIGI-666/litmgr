# DocLayout-YOLO：通过多样化合成数据和从全局到局部的自适应感知增强文档版面分析

DocLayout-YOLO: Enhancing Document Layout Analysis through Diverse Synthetic Data and Global-to-Local Adaptive Perception

## 论文正文

**作者**　Zhiyuan Zhao*、Hengrui Kang*、Bin Wang、Conghui He†  
**机构**　上海人工智能实验室（Shanghai Artificial Intelligence Laboratory）  
* 两位作者贡献相同。† 通讯作者。  
arXiv:2410.12628v1 [cs.CV]，2024 年 10 月 16 日。

### 摘要

文档版面分析是现实文档理解系统的关键环节，却面临速度与精度之间难以兼顾的问题。利用文本与视觉特征的多模态方法精度较高，但延迟较大；只依赖视觉特征的单模态方法处理速度较快，却牺牲了精度。为解决这一矛盾，我们提出 DocLayout-YOLO，在预训练和模型设计两方面针对文档进行优化，在保持速度优势的同时提高精度。为实现稳健的文档预训练，我们提出网格–候选元素最佳适配（Mesh-candidate BestFit）算法，将文档合成表述为二维装箱问题，生成大规模、多样化的 DocSynth-300K 数据集。在该数据集上预训练，显著改善了模型在多种文档类型上的微调表现。在模型优化方面，我们提出从全局到局部的可控感受野模块，更好地处理文档元素的多尺度变化。为验证模型在不同文档类型上的性能，我们还引入复杂且具有挑战性的基准 DocStructBench。大量下游实验表明，DocLayout-YOLO 在速度和精度两方面均有出色表现。代码、数据及模型见 https://github.com/opendatalab/DocLayout-YOLO 。

### 1　引言

随着大语言模型和检索增强生成（Retrieval-Augmented Generation，RAG）研究迅速发展（Lewis 等，2020；Ram 等，2023；Edge 等，2024），对高质量文档内容解析（Wang 等，2024b）的需求日益迫切。解析中的核心步骤是文档版面分析（Document Layout Analysis，DLA），目的是精确定位文本、标题、表格、图形等不同区域。过去数年，DLA 算法取得显著进展，在常见文档类型上表现良好。然而，面对多样化的文档格式，现有版面分析算法（Huang 等，2022；Li 等，2022）仍难以兼顾速度和精度。

目前，文档解析主要有两类方法：结合视觉与文本信息的多模态方法，以及仅依赖视觉特征的单模态方法。多模态方法通常使用统一的图文编码器在文档图像上预训练，精度一般较高，但架构复杂，速度往往较慢。单模态方法只使用视觉特征，处理速度较快，但缺少面向文档数据的专门预训练和模型设计，精度往往不足。为了在多样化的真实文档上保持稳健性能并满足实时应用的需求，我们提出 DocLayout-YOLO 版面检测算法，结合两类方法的长处，快速、准确地识别文档中的各类区域。如图 1 所示，DocLayout-YOLO 在速度上可与单模态方法 YOLOv10（Wang 等，2024a）相提并论，在多样化评测集上的精度则超过已有方法，包括单模态 DINO-4scale（Zhang 等，2023a）和 YOLO-v10，以及多模态 LayoutLMv3（Huang 等，2022）和 DiT-Cascade（Li 等，2022）。具体而言，我们从两个方面优化 YOLOv10：使用带有视觉标注的多样化文档开展预训练，以及针对文档版面分析改进目标检测网络结构。

**图 1　DocLayout-YOLO 与现有先进 DLA 方法的比较。**（a）在 DocStructBench（学术文档、教材、市场分析和金融文档）上，以每秒图像数 FPS 和平均精度 mAP 比较本文方法与已有方法。（b）给出本文方法及其他方法在 D4LA、DocLayNet 和 DocStructBench 四个子集上的具体 mAP。原图概括称，DocLayout-YOLO 在速度和精度上均优于单模态和多模态方法。

我们观察到，LayoutLMv3 和 DiT-Cascade 等多模态版面分析方法通过在大规模无监督文档数据上预训练，显著增强了泛化能力。然而，单模态版面分析使用的现有数据集往往只含单一文档类型，如 PubLayNet（Zhong 等，2019）和 DocBank（Li 等，2020b）。在这类数据上微调的模型容易过拟合单一分布，难以泛化到真实场景中的多样版面。为此，我们提出自动构建多样化文档版面数据的流程，并引入 Mesh-candidate BestFit 算法。该算法借鉴二维装箱问题的原理，利用丰富的基础组件（文本、图片、表格）合成版面，生成大规模、多样化的预训练语料 DocSynth-300K。

YOLO（Jocher 等，2023；Wang 等，2024a）是目标检测中的代表算法，在自然图像上兼具精度与速度。为进一步改善它在文档图像上的表现，我们根据文档数据特点改造网络。在不同文档中，元素尺度差异很大，小到单行标题，大到占满整页的段落、图片或表格。为应对这种变化，我们引入从全局到局部的可控感受野模块（Global-to-Local Controllable Receptive Module，GL-CRM），使模型能够有效检测不同尺度的目标。本文的贡献如下。

- 提出用于多样化版面分析的 DocLayout-YOLO，利用大规模、多样化的 DocSynth-300K，并结合 GL-CRM 提高检测性能。
- 提出 Mesh-candidate BestFit 算法，利用文本、图片、表格等组件合成不同版面的文档，构建 DocSynth-300K。我们将开源该数据集，以支持进一步研究。
- 设计 GL-CRM，增强模型检测不同尺度元素的能力，从而提高检测精度。
- 在 D4LA、DocLayNet 和自建的多样化评测集 DocStructBench 上开展大量实验，DocLayout-YOLO 分别取得 70.3%、79.7% 和 78.8% 的先进 mAP 成绩，推理速度达到每秒 85.5 帧，支持多样化文档的实时版面分析。

### 2　相关工作

#### 2.1　文档版面分析方法

DLA 关注识别并定位文档中的文本、图像等组件。方法分为单模态和多模态两类。单模态方法把 DLA 视作一种特殊的目标检测问题，使用现成的通用检测器（Ren 等，2015；Zhong 等，2019；Carion 等，2020；Jocher 等，2023；Zhang 等，2023a）。多模态方法通过预训练对齐文本和视觉特征。LayoutLM 系列（Xu 等，2020、2021；Huang 等，2022）以统一框架实现多种预训练目标，在多项文档任务上取得了出色结果。DiT（Li 等，2022）通过在大规模文档数据上进行自监督预训练提升性能。VGT（Da 等，2023）引入基于网格的文本编码来提取文本特征。

#### 2.2　文档版面分析数据集

现有数据集在标注细致程度上各有限制。例如，IIT-CDIP（Lewis 等，2006）有 4,200 万张低分辨率无标注图像，其子集 RVL-CDIP（Harley 等，2015）将 40 万张图像分为 16 类。PubLayNet（Zhong 等，2019）包含来自 PubMed 期刊的 36 万页文档，显著扩大了版面分析数据规模。DocBank（Li 等，2020b）用弱监督标注了 50 万页 arXiv 文档；DocLayNet（Pfitzmann 等，2022）则收集了多种类型的 80,863 页文档。D4LA（Da 等，2023）对 RVL-CDIP 中的 11,092 张图像进行 27 类人工标注。M6Doc（Cheng 等，2023）包含 9,080 张多样化图像、74 类标注，因版权限制未开源。DEES200（Yang 等，2017）、CHN（Li 等，2020a）、Prima-LAD（Antonacopoulos 等，2009）和 ADOPD（Gu 等，2024）等数据集，有的未开源，有的主要适合微调。在文档生成方面（Zhang 等，2023b；Inoue 等，2023；Hui 等，2023；Jiang 等，2023；Kong 等，2022；Gupta 等，2021），大多数方法侧重学术论文。总体而言，现有数据集在多样性、数量及标注粒度上存在明显局限，影响了预训练模型的效果。

### 3　构建多样化的 DocSynth-300K 数据集

现有单模态预训练数据集高度同质化，主要由学术论文组成，严重限制了预训练模型的泛化能力。为了适应多种下游文档，需要构建类型更加丰富的预训练数据集。

预训练数据的多样性主要体现在两个维度。（1）元素多样性，包括不同字号的文本、不同形式的表格等。（2）版面多样性，包括但不限于单栏、双栏、多栏，以及学术论文、杂志和报纸特有的排版格式。我们提出 Mesh-candidate BestFit，同时利用元素和版面多样性，自动合成多样且组织有序的文档。所得 DocSynth-300K 显著提升了模型在多类真实文档上的表现。整体流程如图 2 所示，细节如下。

**图 2　Mesh-candidate BestFit 示意图。** 在（A）预处理阶段，从少量初始数据出发，按类别建立元素池。在（B）版面生成阶段，迭代寻找候选元素与网格的最佳匹配。

#### 3.1　预处理：保证元素多样性

为覆盖多种文档元素，我们选取 M6Doc 测试集（Cheng 等，2023）作为初始数据，其中约 2,800 页不同文档包含 74 类元素。我们将页面拆开，提取元素，并按细粒度类别建立元素池。为保持同一类别内部的多样性，还设计了增强流程，扩充元素数不足 100 个的稀有类别（附录 A.2.2）。

#### 3.2　版面生成：保证版面多样性

合成多样版面最直接的办法是随机排列，但这种方法得到的版面杂乱无章，严重限制模型在真实文档上的提升。基于扩散模型（Chen 等，2024；Inoue 等，2023）或 GAN（Jiang 等，2023；Gupta 等，2021）的现有方法则局限于学术论文等同质化版面，难以涵盖现实中的版面类型。

为兼顾多样性及与真实文档的一致性，我们借鉴二维装箱问题，将当前版面形成的可用网格视作大小不同的“箱子”，迭代寻找最佳匹配，以生成多样且合理的版面，在随机性与美观程度（如填充率、对齐程度）之间取得平衡。步骤如下。

1. **候选元素采样。** 对于每个空白页，按元素大小从元素池分层采样，得到候选集。从中随机抽取一个元素，置于页面上的某一位置。
2. **网格构建。** 根据当前版面构建网格，剔除与已插入元素重叠的无效网格。只有剩余网格才能参与后续候选匹配。
3. **搜索最佳适配对。** 对每个候选元素，遍历满足尺寸要求的全部网格，寻找填充率最高的网格–候选元素对。将最优元素从候选集中移除，并更新版面。
4. **迭代填充版面。** 重复步骤 2 和 3，直至找不到满足尺寸要求的有效组合。最后，分别以每个已填充元素的中心为基准，作随机缩放。

**图 3　合成文档数据示例。** 合成页面涵盖多种版面格式，并包含不同元素，体现出版面多样性和元素多样性。

通过上述过程，元素被不断填入最优位置，最终形成组织有序、美观的文档图像，如图 3 所示。生成文档的多样性使预训练模型能够有效适应多种真实文档。同时，定量分析表明，生成结果符合对齐和密度等人类设计原则（附录 A.3.1）。算法 1 给出了上述版面生成过程的详细步骤。

### 4　从全局到局部的模型架构

文档图像的元素尺度差异比自然图像更为突出，例如单行标题和整页表格。为应对尺度变化，我们提出分层架构 GL-CRM，包含可控感受野模块（Controllable Receptive Module，CRM）和从全局到局部的设计（Global-to-Local，GL）。CRM 灵活提取并整合多种尺度、粒度的特征；GL 采用分层感知过程，依次处理全局上下文（整页尺度）、子块区域（中等尺度）和局部语义信息。

**图 4　可控感受野模块（CRM）示意图。** 该模块提取并融合不同尺度和粒度的特征。

#### 4.1　可控感受野模块

如图 4 所示，对于各层特征 $X$，首先使用核大小为 $k$、权重共享的卷积层 $w$ 提取特征。为捕捉不同粒度的特征，使用多种膨胀率 $d=[d_1,d_2,\ldots,d_n]$，得到特征组 $F=[F_1,F_2,\ldots,F_n]$：

$$
F_i=\operatorname{GELU}\!\left(\operatorname{BN}\!\left(\operatorname{Conv}(X,w,d_i)\right)\right). \tag{1}
$$

提取不同粒度的特征后，将其整合，让网络自主学习如何融合不同分量：

$$
\hat F=\operatorname{Concat}([F_1,F_2,\ldots,F_n]). \tag{2}
$$

$$
M=\sigma\!\left(\operatorname{GELU}\!\left(\operatorname{BN}\!\left(\operatorname{Conv}_{\mathrm{gate}}(\hat F)\right)\right)\right). \tag{3}
$$

使用卷积核大小为 1、分组数为 $nC$ 的轻量卷积层 $\operatorname{Conv}_{\mathrm{gate}}$ 提取取值在 0 到 1 之间的掩码 $M$，其数值可视作不同特征的重要性权重。最后，将 $M$ 作用于融合特征 $\hat F$，再送入轻量输出投影层 $\operatorname{Conv}_{\mathrm{out}}$。通过捷径连接，将整合特征与初始特征 $X$ 合并：

$$
X_{\mathrm{CRM}}=X+\operatorname{GELU}\!\left(\operatorname{BN}\!\left(\operatorname{Conv}_{\mathrm{out}}(M\otimes\hat F)\right)\right). \tag{4}
$$

如图 4 所示，将 CRM 插入常规 CSP 瓶颈模块（Wang 等，2020），以提取并增强不同粒度的特征。CRM 的功能由 $k$ 和 $d$ 两个参数控制，二者调节所提取特征的粒度和尺度。

#### 4.2　从全局到局部的设计

**图 5　从全局到局部的设计示意图。**

**全局层级。** 浅层具有丰富的纹理细节，我们采用较大卷积核和不同膨胀率的 CRM（$k=5$，$d=1,2,3$）。大核有助于捕捉更多纹理细节，并保留整页尺度元素的局部模式。

**块层级。** 在中间阶段，特征图已下采样，纹理信息减少，我们使用较小卷积核的 CRM（$k=3$，$d=1,2,3$）。此时，利用膨胀率扩大感受野，已足以感知文档子块等中等尺度元素。

**局部层级。** 深层以语义信息为主，我们采用基础瓶颈作为轻量模块，聚焦局部语义信息。

### 5　实验

#### 5.1　评价指标与数据集

精度采用 COCO 风格的平均精度均值（mAP；Lin 等，2014），速度采用 FPS（每秒处理图像数）。实验在两个复杂的公开 DLA 数据集 D4LA（Da 等，2023）和 DocLayNet（Pfitzmann 等，2022）上进行。D4LA 包含来自 IIT-CDIP（Lewis 等，2006）的 11,092 张有噪声图像，覆盖 12 种文档类型，标注了 27 类元素。其中训练集 8,868 张，测试集 2,224 张。DocLayNet 涵盖 7 种文档类型，共 80,863 页，人工标注了 11 类元素。训练、验证和测试划分分别为 69,103、6,480 和 4,994 张，本研究使用验证集评价。

为定量评价不同文档类型上的表现，我们整理了内部数据集 DocStructBench，涵盖真实场景中的多种文档。按来源分为学术文档、教材、市场分析和金融文档四个子集（见图 6），涉及不同机构、出版社、网站和领域。DocStructBench 包含 7,310 张训练图像和 2,645 张测试图像。每张图像均按 10 类元素人工标注，包括标题、正文、弃用文本、图、图题、表、表题、表格脚注、独立公式和公式标号。实验混合四个子集进行训练，分别报告各子集的结果。其余细节见附录 A.1。

**图 6　DocStructBench 中具有不同格式和结构的复杂文档示例。** 从左到右为学术文档、教材、市场分析和金融文档。

#### 5.2　对比的 DLA 方法和数据集

我们将 DocLayout-YOLO 与多模态及单模态方法进行比较。多模态方法包括 LayoutLMv3（Huang 等，2022）、DiT-Cascade（Li 等，2022）和 VGT（Da 等，2023）。单模态对照采用性能较强的目标检测器 DINO-4scale-R50（Zhang 等，2023a）。对于 DLA 预训练数据，我们将 DocSynth-300K 与公开的 PubLayNet（Zhong 等，2019）和 DocBank（Li 等，2020b）比较。

#### 5.3　实现细节

在 DocSynth-300K 上预训练 DocLayout-YOLO 时，将图像长边缩放至 1,600，批量大小为 128，学习率为 0.02，共训练 30 轮。在 DocLayNet 上微调时，长边设为 1,120，学习率为 0.02；D4LA 上长边为 1,600，学习率为 0.04；DocStructBench 上长边为 1,280，学习率为 0.04。在 8 块 A100 GPU 上训练，早停耐心值为 100 轮。对照模型中，DINO 使用 MMDetection（Chen 等，2019），采用长边为 1,280 的多尺度训练及 AdamW 优化器，学习率为 $1.0\times10^{-4}$。LayoutLMv3 和 DiT 使用 Detectron2 的 Cascade R-CNN（Wu 等，2019），长边为 1,333，采用 SGD 优化器，学习率为 $2.0\times10^{-4}$，训练 60,000 次迭代。

**表 1　DocLayout-YOLO 采用不同优化策略的结果。** “预训练”指在 DocSynth-300K 上预训练。最终模型显著优于基线；↑Δ 表示相对 YOLO-v10 基线的提升。

| GL-CRM | 预训练 | D4LA mAP | D4LA AP50 | DocLayNet mAP | DocLayNet AP50 | 学术 mAP | 学术 AP50 | 教材 mAP | 教材 AP50 | 市场分析 mAP | 市场分析 AP50 | 金融 mAP | 金融 AP50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | 68.6 | 80.7 | 76.7 | 93.4 | 80.5 | 95.0 | 70.2 | 88.0 | 68.9 | 79.2 | 89.8 | 95.9 |
| ✓ | — | 69.8 | 81.7 | 77.7 | 93.0 | 81.4 | 95.4 | 71.5 | 88.8 | 70.2 | 80.0 | 90.0 | 95.8 |
| — | ✓ | 69.8 | 82.1 | 79.3 | 93.6 | 82.1 | 95.8 | 71.5 | 88.5 | 69.3 | 79.6 | 90.3 | 95.5 |
| ✓ | ✓ | 70.3 | 82.4 | 79.7 | 93.4 | 81.8 | 95.8 | 73.7 | 90.3 | 69.4 | 79.4 | 90.1 | 95.9 |
| ↑Δ | — | 1.7 | 1.7 | 3.0 | — | 1.3 | 0.8 | 3.5 | 2.3 | 0.5 | 0.2 | 0.3 | — |

**表 2　D4LA 和 DocLayNet 上的性能比较。** v10m++ 表示用所提 GL-CRM 瓶颈增强原始 v10m 瓶颈。表 2–4 中，粗体和斜体分别对应原表标出的最佳、次佳结果。

| 类型 | 方法 | 骨干 | 预训练数据集 | D4LA mAP | D4LA AP50 | DocLayNet mAP | DocLayNet AP50 |
|---|---|---|---|---|---|---|---|
| 单模态 | YOLO-v10 | v10m | — | 68.6 | *80.7* | 76.2 | 93.0 |
| 单模态 | DINO-4scale | R50 | ImageNet1K | 64.7 | 76.9 | *77.7* | **93.5** |
| 多模态 | VGT | ViT-B | IIT-CDIP，42M | *68.8* | — | — | — |
| 多模态 | LayoutLMv3-B | ViT-B | IIT-CDIP，42M | 60.0 | 72.6 | 75.4 | 92.1 |
| 多模态 | DiT-Cascade-B | ViT-B | IIT-CDIP，42M | 67.7 | 79.8 | 73.2 | 87.6 |
| 多模态 | DiT-Cascade-L | ViT-L | IIT-CDIP，42M | 68.2 | 80.1 | 72.6 | 84.9 |
| 本文方法 | DocLayout-YOLO | v10m++ | DocSynth，300K | **70.3** | **82.4** | **79.7** | *93.4* |

#### 5.4　主要结果

##### 5.4.1　所提优化策略的有效性

首先分析 DocLayout-YOLO 中不同改进策略的作用，结果见表 1。（1）DocSynth-300K 大幅提升了不同文档类型上的性能。在涵盖多种文档类型的 D4LA 和 DocLayNet 上，经 DocSynth-300K 预训练的模型分别提高 1.2 和 2.6 个点，在 DocStructBench 四个子集上也均有改善。（2）最终的 DocLayout-YOLO 取得显著提升。结合 CRM 与 DocSynth-300K 预训练，相较于基线 YOLO-v10，六项 mAP 分别提高 1.7、2.6、1.3、3.5、0.5 和 0.3 个点［原文如此，DocLayNet 的增幅在表 1 末行为 3.0］。

##### 5.4.2　与现有 DLA 方法比较

接着在多个数据集上与现有方法进行比较，D4LA、DocLayNet 的结果见表 2。（1）DocLayout-YOLO 优于性能较强的单模态 DLA 方法。例如，在 DocLayNet 上比排名第二的 DINO 高 2.0 个 mAP 点。（2）它也优于先进的多模态方法。例如，在 D4LA 上取得 70.3 mAP，超过第二名 VGT 的 68.8。表 3 给出了 DocStructBench 上的结果。DocLayout-YOLO 在四个子集中的三个上优于现有先进单模态方法 DINO 和多模态方法 DiT-Cascade-L。在市场分析子集上，DocLayout-YOLO 位居 DiT-Cascade-L 之后，排名第二。我们推测，对于最复杂的版面，DocSynth-300K 预训练仍不充分。

**表 3　DocStructBench 上的性能比较。** v10m++ 为 GL-CRM 增强的原始 v10m 瓶颈。FPS 使用同一台单卡 A100 机器测试。LayoutLMv3-Bᶜ 表示额外在中文文档数据上预训练。星号（*）、剑号（†）和双剑号（‡）分别表示在 Detectron2、Ultralytics（Jocher 等，2023）和 MMDetection 下测速。

| 类型 | 方法 | 骨干 | 学术 mAP | 学术 AP50 | 教材 mAP | 教材 AP50 | 市场分析 mAP | 市场分析 AP50 | 金融 mAP | 金融 AP50 | FPS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 单模态 | YOLO-v10 | v10m | 80.5 | 95.0 | 70.2 | 88.0 | 68.9 | 79.2 | *89.9* | *95.9* | **144.9**† |
| 单模态 | DINO-4scale | R50 | 80.5 | 95.4 | 70.5 | 85.6 | 68.6 | 79.2 | 89.1 | 95.6 | 26.7‡ |
| 多模态 | DiT-Cascade-B | ViT-B | 79.7 | 95.1 | 69.7 | 86.1 | 63.7 | 71.0 | 88.7 | 94.1 | 14.1∗ |
| 多模态 | DiT-Cascade-L | ViT-L | *81.0* | **96.0** | *70.8* | *86.8* | **70.8** | **80.8** | 89.3 | 94.5 | 6.0∗ |
| 多模态 | LayoutLMv3-B | ViT-B | 76.5 | 94.9 | 66.0 | 82.3 | 65.7 | 75.2 | 85.7 | 90.4 | 9.0∗ |
| 多模态 | LayoutLMv3-Bᶜ | ViT-B | 77.7 | 93.5 | 68.0 | 82.8 | 67.9 | 75.7 | 87.6 | 92.1 | 9.0∗ |
| 本文方法 | DocLayout-YOLO | v10m++ | **81.8** | *95.8* | **73.7** | **90.3** | *69.4* | *79.4* | **90.1** | **95.9** | *85.5*† |

**表 4　在不同文档数据集上预训练后的下游微调性能。** 使用基线 YOLO-v10m，“基线”一行表示从头训练。作者据此认为，相比其他公开与合成文档数据，DocSynth-300K 对各类文档具有更好的适应性。

| 数据类型 | 预训练数据集 | 规模 | 学术 mAP | 学术 AP50 | 教材 mAP | 教材 AP50 | 市场分析 mAP | 市场分析 AP50 | 金融 mAP | 金融 AP50 |
|---|---|---|---|---|---|---|---|---|---|---|
| 基线 | — | — | 80.5 | 95.0 | 70.2 | 88.0 | 68.9 | 79.2 | 89.9 | 95.9 |
| 公开 | M6Doc | 2K | 80.4 | 94.9 | 70.0 | 87.7 | 68.9 | 79.1 | 89.7 | 95.8 |
| 公开 | DocBank | 400K | *81.6* | *95.5* | 70.9 | **89.6** | 69.1 | *79.5* | *90.1* | **95.9** |
| 公开 | PubLayNet | 300K | 81.0 | 95.3 | 71.5 | 88.8 | *69.1* | 78.8 | 89.7 | 95.7 |
| 合成 | 随机排列 | 300K | 80.5 | 95.1 | 71.2 | 88.8 | 68.1 | 78.6 | 89.6 | 95.7 |
| 合成 | 扩散生成 | 300K | 80.7 | 95.2 | **71.9** | *89.4* | 68.9 | 79.3 | 89.3 | *95.8* |
| 合成 | DocSynth | 300K | **82.1** | **95.8** | *71.5* | 88.5 | **69.3** | **79.6** | **90.3** | 95.5 |

我们还仔细评估了各方法的推理 FPS。结果表明，（3）DocLayout-YOLO 比现有 DLA 方法更高效。尽管速度相较 YOLO-v10 基线有所下降，仍然具有明显优势。例如，其 FPS 是最强多模态方法 DiT-Cascade-L 的 14.3 倍，是最强单模态对照 DINO 的 3.2 倍。

#### 5.5　消融实验

##### 5.5.1　与不同文档合成方法比较

为评价合成数据质量，我们将 DocSynth-300K 与不同文档合成方法比较。不同方法使用相同的渲染元素生成文档，然后评价预训练模型在下游微调数据集上的表现。对照版面生成方法有随机排列和扩散生成两种。前者任意安排元素；后者用来自七个下游数据集的 100 万张文档图像训练先进的扩散版面生成模型 LACE（Chen 等，2024）来生成版面，训练数据见表 5。使用 YOLO-v10 基线进行实验，结果见表 4。

**表 5　LACE 使用的数据。**

| 数据 | 类型 | 规模 |
|---|---|---|
| DSSE200 | 学术 | 271 |
| CHN | 维基百科 | 10K |
| DocBank | 学术 | 400K |
| PubLayNet | 学术 | 300K |
| DocLayNet | 多类型 | 80K |
| D4LA | 多类型 | 9K |
| Prima-LAD | 多类型 | 478 |

结果表明：（1）随机版面不适合文档预训练。虽然某些指标有所提高，但随机版面与真实文档差距较大，效果不理想。（2）扩散版面的收益限于某些文档类型。它比随机版面预训练得更好，可能是生成结果更接近实际文档，但版面多样性有限，提升主要集中于学术文档、教材等类型。（3）DocSynth-300K 对多类文档表现出更好的泛化能力。相较于扩散和随机生成，以 DocSynth-300K 预训练的模型在四个子集上均取得改善，展现出更好的泛化性。定量结果与可视化（图 7）均表明，所提流程能够生成多样性更强、质量更高的文档。

**图 7　不同文档合成方法生成的文档图像可视化。** 图中并列展示随机、扩散和本文方法所生成的版面及渲染结果。

##### 5.5.2　与公开文档预训练数据集比较

表 4 给出了与公开预训练集的对比。结果表明，DocSynth-300K 是更有效的文档预训练数据集。首先，作为合成元素来源的 M6Doc 测试集规模较小，存在严重过拟合。其次，PubLayNet 和 DocBank 虽然数据量大，但元素类别不足 10 种，版面仅限学术论文，因此预训练模型学到的特征表示较为单一。即使有些方面已经提升，进一步改善仍受限制，无法在所有下游数据集上一致增强泛化能力。相比之下，DocSynth-300K 预训练模型在多方面得到改善，在多数下游数据集上优于 PubLayNet 和 DocBank，表明其能够更有效地改善多种下游文档的检测。

##### 5.5.3　GL-CRM 作用的消融实验

**表 6　GL-CRM 的消融实验（D4LA）。** 括号内为相对基线的增量；APs、APm 和 APl 分别对应小、中、大目标。

| 全局层级 | 块层级 | mAP | AP50 | APs | APm | APl |
|---|---|---|---|---|---|---|
| — | — | 68.6 | 80.7 | 47.0 | 53.2 | 68.8 |
| ✓ | — | 69.2（↑0.6） | 81.2（↑0.5） | 47.1（↑0.1） | 53.9（↑0.7） | 69.6（**↑0.8**） |
| — | ✓ | 69.3（↑0.7） | 81.5（↑0.8） | 47.2（↑0.2） | 55.0（**↑1.8**） | 69.4（↑0.6） |
| ✓ | ✓ | 69.8（↑1.2） | 81.7（↑1.0） | 47.2（↑0.2） | 55.3（↑2.1） | 70.2（↑1.4） |

最后，我们对 GL-CRM 进行消融，结果见表 6。引入全局层级，明显提高了中、大目标的检测精度。引入块层级，对应文档子块的中等目标获得了最明显的改善。实验验证了 GL-CRM 从全局到局部设计的有效性。

### 6　结论

我们提出的 DocLayout-YOLO 在速度和精度上均表现出色。它从预训练和模型优化两方面作出改进：在预训练方面，提出 Mesh-candidate BestFit，合成高质量、多样化的 DLA 预训练集 DocSynth-300K；在模型优化方面，引入 GL-CRM，从全局、块到局部逐级增强网络对文档图像的感知。在众多下游数据集上的实验表明，DocLayout-YOLO 在速度和精度两方面均显著优于现有 DLA 方法。

### 参考文献

原文按作者排列。ICDAR 为国际文档分析与识别会议，ECCV 为欧洲计算机视觉会议，CVPR 为计算机视觉与模式识别会议，ICCV 为国际计算机视觉大会，ICLR 为国际学习表征会议，ACM Multimedia 为 ACM 国际多媒体会议，SIGIR 为国际信息检索研究与发展大会，NIPS 为神经信息处理系统大会，COLING 为国际计算语言学大会，KDD 为知识发现与数据挖掘大会，ACL 为计算语言学协会年会。IEEE Trans. Vis. Comput. Graph. 为《IEEE 可视化与计算机图形学汇刊》，Transactions of the Association for Computational Linguistics 为《计算语言学协会汇刊》，arXiv 为预印本平台。

- **用于文档版面分析性能评价的真实数据集**。Apostolos Antonacopoulos, David Bridson, Christos Papadopoulos, and Stefan Pletschacher. A realistic dataset for performance evaluation of document layout analysis. In ICDAR, 2009.

- **基于 Transformer 的端到端目标检测**。Nicolas Carion, Francisco Massa, Gabriel Synnaeve, Nicolas Usunier, Alexander Kirillov, and Sergey Zagoruyko. End-to-end object detection with transformers. In ECCV, 2020.

- **通过带美学约束的扩散模型生成对齐版面**。Jian Chen, Ruiyi Zhang, Yufan Zhou, and Changyou Chen. Towards aligned layout generation via diffusion model with aesthetic constraints. arXiv preprint arXiv:2402.04754, 2024.

- **MMDetection：OpenMMLab 检测工具箱与基准**。Kai Chen, Jiaqi Wang, Jiangmiao Pang, Yuhang Cao, Yu Xiong, Xiaoxiao Li, Shuyang Sun, Wansen Feng, Ziwei Liu, Jiarui Xu, Zheng Zhang, Dazhi Cheng, Chenchen Zhu, Tianheng Cheng, Qijie Zhao, Buyu Li, Xin Lu, Rui Zhu, Yue Wu, Jifeng Dai, Jingdong Wang, Jianping Shi, Wanli Ouyang, Chen Change Loy, and Dahua Lin. MMDetection: Open mmlab detection toolbox and benchmark. arXiv, 2019.

- **M6Doc：面向现代文档版面分析的大规模多格式、多类型、多版式、多语言、多标注类别数据集**。Hiuyi Cheng, Peirong Zhang, Sihang Wu, Jiaxin Zhang, Qiyuan Zhu, Zecheng Xie, Jing Li, Kai Ding, and Lianwen Jin. M6doc: A large-scale multi-format, multi-type, multi-layout, multi-language, multi-annotation category dataset for modern document layout analysis. In CVPR, 2023.

- **用于文档版面分析的视觉网格 Transformer**。Cheng Da, Chuwei Luo, Qi Zheng, and Cong Yao. Vision grid transformer for document layout analysis. In ICCV, 2023.

- **从局部到全局：用于面向查询的摘要生成的图检索增强生成方法**。Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, and Jonathan Larson. From local to global: A graph rag approach to query-focused summarization. arXiv preprint arXiv:2404.16130, 2024.

- **ADoPD：大规模文档页面分解数据集**。Jiuxiang Gu, Xiangxi Shi, Jason Kuen, Lu Qi, Ruiyi Zhang, Anqi Liu, Ani Nenkova, and Tong Sun. ADoPD: A large-scale document page decomposition dataset. In ICLR, 2024.

- **LayoutTransformer：利用自注意力生成和补全版面**。Kamal Gupta, Justin Lazarow, Alessandro Achille, Larry Davis, Vijay Mahadevan, and Abhinav Shrivastava. Layouttransformer: Layout generation and completion with self-attention. In ICCV, 2021.

- **用于文档图像分类与检索的深度卷积网络评估**。Adam W. Harley, Alex Ufkes, and Konstantinos G. Derpanis. Evaluation of deep convolutional nets for document image classification and retrieval. In ICDAR, 2015.

- **LayoutLMv3：采用统一图文掩码的文档智能预训练**。Yupan Huang, Tengchao Lv, Lei Cui, Yutong Lu, and Furu Wei. Layoutlmv3: Pre-training for document AI with unified text and image masking. In ACM Multimedia, 2022.

- **利用解耦扩散模型统一版面生成**。Mude Hui, Zhizheng Zhang, Xiaoyi Zhang, Wenxuan Xie, Yuwang Wang, and Yan Lu. Unifying layout generation with a decoupled diffusion model. In CVPR, 2023.

- **LayoutDM：用于可控版面生成的离散扩散模型**。Naoto Inoue, Kotaro Kikuchi, Edgar Simo-Serra, Mayu Otani, and Kota Yamaguchi. Layoutdm: Discrete diffusion model for controllable layout generation. In CVPR, 2023.

- **LayoutFormer++：通过约束序列化及解码空间限制实现条件图形版面生成**。Zhaoyun Jiang, Jiaqi Guo, Shizhao Sun, Huayu Deng, Zhongkai Wu, Vuksan Mijovic, Zijiang James Yang, Jian-Guang Lou, and Dongmei Zhang. Layoutformer++: Conditional graphic layout generation via constraint serialization and decoding space restriction. In CVPR, 2023.

- **Ultralytics YOLO**。Glenn Jocher, Ayush Chaurasia, and Jing Qiu. Ultralytics YOLO, 2023. URL https://github.com/ultralytics/ultralytics.

- **通过潜在空间优化实现受约束的图形版面生成**。Kotaro Kikuchi, Edgar Simo-Serra, Mayu Otani, and Kota Yamaguchi. Constrained graphic layout generation via latent optimization. In ACM Multimedia, 2021.

- **BLT：用于可控版面生成的双向版面 Transformer**。Xiang Kong, Lu Jiang, Huiwen Chang, Han Zhang, Yuan Hao, Haifeng Gong, and Irfan Essa. BLT: bidirectional layout transformer for controllable layout generation. In ECCV, 2022.

- **构建用于复杂文档信息处理的测试集**。David D. Lewis, Gady Agam, Shlomo Argamon, Ophir Frieder, David A. Grossman, and Jefferson Heard. Building a test collection for complex document information processing. In SIGIR, 2006.

- **面向知识密集型自然语言处理任务的检索增强生成**。Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, et al. Retrieval-augmented generation for knowledge-intensive nlp tasks. In NIPS, 2020.

- **用于自动平面设计的属性条件版面 GAN**。Jianan Li, Jimei Yang, Jianming Zhang, Chang Liu, Christina Wang, and Tingfa Xu. Attribute-conditioned layout GAN for automatic graphic design. IEEE Trans. Vis. Comput. Graph., 2021.

- **DiT：文档图像 Transformer 的自监督预训练**。Junlong Li, Yiheng Xu, Tengchao Lv, Lei Cui, Cha Zhang, and Furu Wei. Dit: Self-supervised pre-training for document image transformer. In ACM Multimedia, 2022.

- **跨域文档目标检测：基准套件与方法**。Kai Li, Curtis Wigington, Chris Tensmeyer, Handong Zhao, Nikolaos Barmpalios, Vlad I. Morariu, Varun Manjunatha, Tong Sun, and Yun Fu. Cross-domain document object detection: Benchmark suite and method. In CVPR, 2020a.

- **DocBank：文档版面分析基准数据集**。Minghao Li, Yiheng Xu, Lei Cui, Shaohan Huang, Furu Wei, Zhoujun Li, and Ming Zhou. Docbank: A benchmark dataset for document layout analysis. In COLING, 2020b.

- **Microsoft COCO：上下文中的常见物体**。Tsung-Yi Lin, Michael Maire, Serge Belongie, and et al. Microsoft coco: Common objects in context. In ECCV, 2014.

- **DocLayNet：用于文档版面分割的大规模人工标注数据集**。Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter W. J. Staar. Doclaynet: A large human-annotated dataset for document-layout segmentation. In KDD, 2022.

- **上下文检索增强语言模型**。Ori Ram, Yoav Levine, Itay Dalmedigos, Dor Muhlgay, Amnon Shashua, Kevin Leyton-Brown, and Yoav Shoham. In-context retrieval-augmented language models. Transactions of the Association for Computational Linguistics, 11:1316–1331, 2023.

- **Faster R-CNN：利用区域建议网络实现实时目标检测**。Shaoqing Ren, Kaiming He, Ross Girshick, and Jian Sun. Faster r-cnn: Towards real-time object detection with region proposal networks. NIPS, 2015.

- **YOLOv10：实时端到端目标检测**。Ao Wang, Hui Chen, Lihao Liu, Kai Chen, Zijia Lin, Jungong Han, and Guiguang Ding. Yolov10: Real-time end-to-end object detection. arXiv, 2024a.

- **MinerU：精确提取文档内容的开源方案**。Bin Wang, Chao Xu, Xiaomeng Zhao, Linke Ouyang, Fan Wu, Zhiyuan Zhao, Rui Xu, Kaiwen Liu, Yuan Qu, Fukai Shang, Bo Zhang, Liqun Wei, Zhihao Sui, Wei Li, Botian Shi, Yu Qiao, Dahua Lin, and Conghui He. Mineru: An open-source solution for precise document content extraction, 2024b. URL https://arxiv.org/abs/2409.18839.

- **CSPNet：可增强卷积神经网络学习能力的新型骨干网络**。Chien-Yao Wang, Hong-Yuan Mark Liao, Yueh-Hua Wu, Ping-Yang Chen, Jun-Wei Hsieh, and I-Hau Yeh. Cspnet: A new backbone that can enhance learning capability of CNN. In CVPR Workshops, 2020.

- **Detectron2**。Yuxin Wu, Alexander Kirillov, Francisco Massa, Wan-Yen Lo, and Ross Girshick. Detectron2. https://github.com/facebookresearch/detectron2, 2019.

- **LayoutLMv2：面向视觉丰富文档理解的多模态预训练**。Yang Xu, Yiheng Xu, Tengchao Lv, Lei Cui, Furu Wei, Guoxin Wang, Yijuan Lu, Dinei A. F. Florêncio, Cha Zhang, Wanxiang Che, Min Zhang, and Lidong Zhou. Layoutlmv2: Multi-modal pre-training for visually-rich document understanding. In ACL, 2021.

- **LayoutLM：面向文档图像理解的文本与版面预训练**。Yiheng Xu, Minghao Li, Lei Cui, Shaohan Huang, Furu Wei, and Ming Zhou. Layoutlm: Pre-training of text and layout for document image understanding. In KDD, 2020.

- **学习利用多模态全卷积神经网络提取文档语义结构**。Xiao Yang, Ersin Yumer, Paul Asente, Mike Kraley, Daniel Kifer, and C Lee Giles. Learning to extract semantic structure from documents using multimodal fully convolutional neural networks. In CVPR, 2017.

- **DINO：使用改进的去噪锚框进行端到端目标检测的 DETR**。Hao Zhang, Feng Li, Shilong Liu, Lei Zhang, Hang Su, Jun Zhu, Lionel M. Ni, and Heung-Yeung Shum. DINO: DETR with improved denoising anchor boxes for end-to-end object detection. In ICLR, 2023a.

- **LayoutDiffusion：用离散扩散概率模型改进图形版面生成**。Junyi Zhang, Jiaqi Guo, Shizhao Sun, Jian-Guang Lou, and Dongmei Zhang. Layoutdiffusion: Improving graphic layout generation by discrete diffusion probabilistic models. In ICCV, 2023b.

- **PubLayNet：迄今最大的文档版面分析数据集**。Xu Zhong, Jianbin Tang, and Antonio Jimeno-Yepes. Publaynet: Largest dataset ever for document layout analysis. In ICDAR, 2019.

### A　附录

附录先详述自建评估集 DocStructBench（A.1），再介绍 Mesh-candidate BestFit 的细节及更多生成文档的可视化示例（A.2）。随后，从设计原则的角度定量评价 DocSynth-300K（A.3.1），并对预训练数据量开展消融研究（A.3.2）。最后，展示 DocLayout-YOLO 在多类真实文档上的检测示例（A.4）。

#### A.1　DocStructBench 细节

DocStructBench 是一个多样、复杂的文档结构数据集，包含 9,082 张训练图像和 2,232 张测试图像，分为学术文档、教材、市场分析和金融文档四个子集。表 7 列出了各子集的分布与来源，表 8 给出了各类文档组件的实例数。

**表 7　DocStructBench 的文档来源与训练/测试划分。**

| 类型 | 来源 | 训练图像 | 测试图像 |
|---|---|---|---|
| 学术 | 学术论文 | 1,605 | 402 |
| 教材 | 教材和试卷 | 2,345 | 587 |
| 分析报告 | 行业与市场分析报告 | 2,660 | 651 |
| 金融 | 金融业务文书 | 2,472 | 592 |

**表 8　DocStructBench 标注的细粒度类别及实例数。**

| 类别 | 释义 | 训练实例 | 测试实例 |
|---|---|---|---|
| 标题 | 包括多级标题，单独成行、加粗，并使用区别于正文的字体。 | 11,384 | 2,943 |
| 正文 | 文档的主体文字。 | 45,243 | 12,455 |
| 弃用文本 | 包括页眉、页脚、页码、页面脚注与边注。 | 16,640 | 4,379 |
| 图 | 文档中独立浮动的图。 | 5,164 | 1,296 |
| 图题 | 对相应图片作出解释的文字。 | 2,660 | 715 |
| 表 | 文档中独立浮动的表格。 | 1,389 | 407 |
| 表题 | 对相应表格作出解释的文字。 | 911 | 271 |
| 表格脚注 | 表格的脚注，通常对表格作补充解释与澄清。 | 1,490 | 370 |
| 独立公式 | 独立成块的方程，不含嵌在文本中的公式。 | 795 | 221 |
| 公式标号 | 公式的说明标记，通常指其标签或编号。 | 385 | 86 |

#### A.2　Mesh-candidate BestFit

##### A.2.1　版面生成算法

算法 1 详列了版面生成步骤。该算法迭代搜索各候选元素与所有网格（箱子）之间的最优匹配。找到最佳组合后，将该元素插入文档，继续迭代寻找最佳匹配，直到元素数达到阈值 $N$（经验设为 15）。匹配阈值 $fr_{\mathrm{thr}}$ 取 $10^{-4}$。

**算法 1　网格–候选元素最佳适配算法。** 输入为元素池 $P$、从 $P$ 采样所得的候选集 $C_{\mathrm{set}}=\{e_1,e_2,\ldots,e_N\}$、匹配阈值 $fr_{\mathrm{thr}}$；输出为生成的版面 $L$。伪代码保留原文的变量命名。

~~~text
 1  从 C_set 采样 e*，插入 L
 2  当 |L| < N 时：
 3      M_g = MeshEngine(L)
 4      对于 C_set 中的每个候选元素 e_i：
 5          对于 M_set 中的每个网格 g_j：
 6              fr = match(e_i, g_j)
 7              若 fr > fr_max：
 8                  fr_max ← fr，C_best ← e_i，M_best ← g_j
 9              结束条件判断
10          结束网格循环
11      结束候选元素循环
12      若 fr_max < fr_thr：
13          跳出循环
14      否则：
15          从 C_set 移除 C_best，并将 C_best 插入 L
16      结束条件判断
17  结束循环
18  返回 L
~~~

##### A.2.2　数据增强流程

预处理时，我们专门为元素池中样例较少的稀有类别设计了一套增强流程，具体如下。

1. **随机翻转。** 考虑到不同文档中文字方向可能不同，以 0.5 的概率对原始数据进行水平和垂直方向的随机翻转。
2. **随机亮度与对比度。** 以 0.5 的概率随机改变元素亮度和对比度，模拟现实环境中的多种光照条件和亮度水平。
3. **随机裁剪。** 为引导模型更关注局部特征，以 0.7 的概率对元素作随机裁剪，裁剪面积比例范围为 0.5 至 0.9。
4. **边缘提取。** 以 0.2 的概率使用 Sobel 滤波器进行边缘检测，提取元素内部的轮廓信息，丰富特征。
5. **弹性变换与添加高斯噪声。** 用轻微的弹性变换和高斯噪声使原始数据发生扭曲、模糊，以模拟现实中的抖动或分辨率造成的失真。

##### A.2.3　其他细节

在版面生成阶段，算法迭代寻找填充率最高的候选元素–网格对，直到再无满足尺寸要求的有效组合。我们设置了额外约束：小元素数量不得超过 $\mathrm{Mini}_{\mathrm{num}}$，过多小元素会使版面偏离常规审美标准。具体取值为 5。

##### A.2.4　更多可视化示例

图 8 给出了更丰富的生成样本。S、M、L 分别表示小、中、大元素，指出页面上相对较多的元素尺度。生成结果类别丰富、多样性强，既能得到含许多小元素的密集版面，也能生成只含少量大元素的稀疏版面，后者类似扩散模型生成的版面。

**图 8　多样化生成版面及其渲染页面的可视化。** S、M、L 分别表示小、中、大元素，标记页面上相对较多的组件尺度。

#### A.3　更多评价实验

##### A.3.1　从设计原则角度评价合成文档

本节定量评价合成文档是否符合人类设计原则。采用对齐（Align）和密度（Density）两个指标，分别从文档对齐和疏密程度衡量版面美学质量。对于 Align，我们采用 LayoutGAN++（Kikuchi 等，2021；Li 等，2021）衡量元素对齐程度的指标：

$$
L_{\mathrm{alg}}=\sum_{i=1}^{N}\min\!\left(
\begin{array}{ccc}
g(\Delta x_i^L),&g(\Delta x_i^C),&g(\Delta x_i^R),\\
g(\Delta y_i^T),&g(\Delta y_i^C),&g(\Delta y_i^B)
\end{array}\right). \tag{5}
$$

其中，$x_i^*$（$*=L,C,R$）表示第 $i$ 个元素左端、中心、右端的横坐标；$y_i^*$（$*=T,C,B$）表示其顶端、中心、底端的纵坐标。函数 $g(x)=-\log(1-x)$，而 $\Delta x_i^*$ 的计算方式为：

$$
\Delta x_i^*=\min_{\forall j\ne i}\left|x_i^*-x_j^*\right|. \tag{6}
$$

$\Delta y_i^*$（$*=T,C,B$）以同样方式计算。对于 Density，我们计算版面中已填充区域的占比：

$$
L_{\mathrm{dst}}=\frac{\sum_{i=1}^{N}|e_i|}{|L|}. \tag{7}
$$

$|e_i|$ 表示元素 $e_i$ 在版面 $L$ 中所占的面积，$|L|$ 表示整页版面面积。Align 越低，文档对齐越好；Density 越高，版面越紧凑、越密集。表 9 表明，Mesh-candidate BestFit 在对齐和密度上均显著优于扩散及随机方法。可视化结果进一步表明，它生成的版面更符合人类审美和设计标准。

**表 9　不同版面生成方法的定量比较。**

| 版面生成方法 | Align ↓ | Density ↑ |
|---|---|---|
| 随机排列 | 0.0171 | 0.259 |
| 扩散（LACE） | 0.0032 | 0.476 |
| Mesh-candidate BestFit（本文） | **0.0009** | **0.645** |

##### A.3.2　预训练数据量消融

我们用 Mesh-candidate BestFit 生成 0 至 50 万张预训练图像，预训练基础 YOLO-v10，随后在 D4LA 上微调，结果见图 9。实验显示，预训练数据量与模型表现有明显关联。具体来说，数据量低于 10 万张时，随着数据增加，性能持续提升；达到 20 万张时，性能出现明显波动；增加到 30 万张时达到最高水平。

**图 9　预训练数据量消融。** 横轴为预训练样本量，纵轴为 mAP。

#### A.4　检测示例

图 10 和图 11 展示了以 DocStructBench 微调 DocLayout-YOLO 后，在多种真实下游文档上的检测示例。示例表明，该模型能够有效适应多种文档，具有较强的实用性和覆盖面。

**图 10　DocLayout-YOLO 在学术文档与教材子集上的检测结果。**

**图 11　DocLayout-YOLO 在市场分析与金融文档子集上的检测结果。**
