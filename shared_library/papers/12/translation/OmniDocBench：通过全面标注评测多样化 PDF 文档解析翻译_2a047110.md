# OmniDocBench：通过全面标注评测多样化 PDF 文档解析

OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations

## 论文正文

作者：Linke Ouyang¹*、Yuan Qu¹*、Hongbin Zhou¹*、Jiawei Zhu¹*、Rui Zhang¹*、Qunshu Lin²*、Bin Wang¹*†、Zhiyuan Zhao¹、Man Jiang¹、Xiaomeng Zhao¹、Jin Shi¹、Fan Wu¹、Pei Chu¹、Minghao Liu³、Zhenxiang Li¹、Chao Xu¹、Bo Zhang¹、Botian Shi¹、Zhongying Tu¹、Conghui He¹‡。

机构：¹上海人工智能实验室（Shanghai AI Laboratory）；²Abaka AI；³2077AI。

*这些作者贡献相同。†项目负责人。‡通讯作者（heconghui@pjlab.org.cn）。

本 CVPR 论文是由计算机视觉基金会（Computer Vision Foundation）提供的开放获取版本。除本水印外，它与录用版本相同；会议论文集最终发表版本可在 IEEE Xplore 获取。

### 摘要

文档内容提取是计算机视觉中的一项关键任务，为大语言模型（Large Language Models，LLMs）和检索增强生成（Retrieval-Augmented Generation，RAG）系统提供基础数据支持。尽管近期取得了进展，但由于现有基准覆盖的文档类型有限，且评测流程过于简化、脱离现实，当前文档解析方法尚未得到公平、全面的评测。为弥补这些不足，我们提出 OmniDocBench：一个新颖的基准，提供来自九类文档来源的高质量标注，既包括学术论文、教科书，也包括手写笔记和排版密集的报纸等更具挑战性的情况。OmniDocBench 利用 19 个版面类别和 15 个属性标签，支持灵活的多层次评测，覆盖端到端评估、任务专项评估和基于属性的分析。我们全面评测了基于流水线的方法和端到端视觉语言模型，揭示它们在不同文档类型上的优势与不足。OmniDocBench 为文档解析中公平、多样化、细粒度的评测确立了新标准。数据集与代码见 https://github.com/opendatalab/OmniDocBench。

**图 1.** OmniDocBench 上覆盖 9 种 PDF 页面类型的端到端文本识别结果。

### 1. 引言

随着大语言模型 [1, 28, 39, 44] 日益依赖高质量、富含知识的数据，准确解析文档的重要性显著提升。文档解析是计算机视觉和文档智能的核心任务，旨在从 PDF 等非结构化文档中提取结构化、机器可读的内容。这项任务对于将学术论文、技术报告、教科书以及其他内容丰富的文本来源输入大语言模型尤其重要，能够提高模型的事实准确性和知识依据 [19, 42, 45, 47, 52]。此外，检索增强生成系统 [12, 22] 通过检索外部文档并以其为条件生成答案，其兴起进一步加剧了对精准文档理解的需求。

为解决这一具有挑战性的任务，形成了两种主要范式：1）基于流水线的方法，将任务分解为版面分析、光学字符识别（Optical Character Recognition，OCR）、公式／表格识别以及阅读顺序估计 [34, 42]；2）端到端视觉语言模型（Vision-Language Models，VLMs），直接输出结构化表示，例如 Markdown [3, 7, 8, 29, 45, 46, 48]。虽然这两类方法都展现了有希望的结果，但缺少全面、统一的评测基准，仍使广泛比较其有效性面临困难。

如表 1 所示，对于基于流水线的文档解析系统，已有专门基准 [10, 26, 54] 针对特定子任务开展评测。对于端到端评测，Nougat [7] 和 GOT-OCR [45] 等工作提供规模相对较小的验证集，并使用编辑距离（Edit Distance）[21] 等页面级指标评估预测结果。

**图 2. OmniDocBench 数据多样性概览。** 本基准包含 9 种不同的 PDF 文档类型，支持丰富的标注类型，包括版面标注（如标题、表格、图像）与识别标注（如文本片段、公式、表格）。每页标注 6 个页面级属性（如 PDF 类型、版面类型），同时提供 3 个细粒度文本属性（如语言）和 6 个表格属性（“特殊情况”下面的项目分别作为独立的是／否二元属性），支持细致、稳健的评测。

然而，这些基准存在几个关键局限：1）**文档多样性有限：**现有数据集主要聚焦学术论文，忽视了教科书、试卷、财务报告、报纸等其他真实世界的文档类型；2）**评测指标不一致：**当前基准高度依赖编辑距离 [21] 和 BLEU [33] 等通用文本相似度指标，无法公平评估 LaTeX 或 HTML 格式公式、表格的准确性，因为这些格式允许多种不同的语法表达；3）**缺少细粒度评测：**大部分评测仅报告总体得分，无法揭示具体弱点，例如元素级得分（文本与公式之间的差别）或不同文档类型的表现（如杂志或笔记）。

为解决这些局限，我们提出 OmniDocBench，一个旨在对流水线和端到端两种范式的文档解析模型开展严格、全面评测的新基准。概括而言，本基准的主要贡献如下：

- **高质量、多样化的评测集：**纳入从教科书到报纸等 9 种不同文档类型的页面，结合自动化工具、人工核验和专家审查完成标注。
- **灵活、多维度的评测：**支持端到端、单任务和基于属性三个层面的全面评测。端到端评测衡量整页解析结果的总体质量；单任务评测允许用户评估版面检测、OCR、表格识别或公式解析等独立组件；基于属性的评测则针对 9 种文档类型、6 个页面级属性和 9 个边界框级属性开展细粒度分析。
- **对最先进方法的全面基准评测：**系统评测一组具有代表性的文档解析系统，包括流水线工具和 VLM，提供最全面的比较，并识别不同文档类型与内容结构下的性能瓶颈。

### 2. 相关工作

#### 2.1. 基于流水线的文档内容提取

基于流水线的方法将文档内容提取视为多个独立模块的集合，如文档版面检测 [13, 17, 36, 53]、OCR [15, 23, 30, 38, 43]、公式识别 [6, 27, 40, 51] 和表格识别 [16, 18, 23]。因此，这类方法可以使用不同的专家模型解决每项具体任务。Marker [34] 集成开源模型，将文档解析为 Markdown、JSON 和 HTML 等结构化格式。为提高准确性，还可选用集成 LLM 的版本，以合并跨页表格、处理行内数学表达式等。类似地，MinerU [42] 首先使用版面检测模型将页面划分为不同区域，然后对相应区域应用任务专用模型，最后借助阅读顺序算法，以 Markdown 格式输出完整内容。通过轻量级模型与并行化操作，基于流水线的方法能够实现高效解析。

**表 1. OmniDocBench 与现有基准的比较。** BBox：边界框；文本：Unicode 文本；表格：LaTeX／HTML／Markdown 格式表格；公式：LaTeX 公式；属性：页面级和边界框级属性。OCR：光学字符识别；DLA：文档版面分析；TR：表格识别；MFR：数学公式识别；ROD：阅读顺序检测。✓ 表示支持，— 表示原表未勾选。

| 基准分组 | 基准 | 文档领域数 | BBox | 文本 | 表格 | 公式 | 属性 | 单任务 OCR | 单任务 DLA | 单任务 TR | 单任务 MFR | 端到端 OCR | 端到端 TR | 端到端 MFR | 端到端 ROD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 单任务评测 | Robust Reading [20] | 1 | ✓ | ✓ | — | — | — | ✓ | — | — | — | — | — | — | — |
| 单任务评测 | PubLayNet [49]、DocBank [26]、DocLayNet [35]、M6Doc [9] | 1、1、5、6 | ✓ | — | — | — | — | — | ✓ | — | — | — | — | — | — |
| 单任务评测 | PubTabNet [54]、TableX [11] | 1、1 | — | — | ✓ | — | — | — | — | ✓ | — | — | — | — | — |
| 单任务评测 | TableBank [25] | 1 | ✓ | — | ✓ | — | — | — | — | ✓ | — | — | — | — | — |
| 单任务评测 | Im2Latex-100K [10]、UniMER-Test [40] | 1 | — | — | — | ✓ | — | — | — | — | ✓ | — | — | — | — |
| 端到端评测 | Fox [29] | 2 | ✓ | ✓ | — | — | — | ✓ | — | — | — | ✓ | — | — | — |
| 端到端评测 | Nougat [7] | 1 | — | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ | — |
| 端到端评测 | GOT OCR 2.0 [45] | 2 | — | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | ✓ | — |
| 端到端评测 | OmniDocBench | 9 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

#### 2.2. 基于 VLM 的文档内容提取

文档理解和 OCR 是评估 VLM 感知能力的关键任务。在预训练阶段融入大规模 OCR 语料后，GPT4o [2] 和 Qwen2-VL [3] 等 VLM 在文档内容提取任务上表现出了相当的性能。与流水线方法不同，VLM 以端到端方式完成文档解析。此外，凭借泛化能力，这些模型无需专门的数据微调，便能处理多样化、甚至未见过的文档类型。

为结合轻量级模型的效率和 VLM 的泛化能力，许多工作 [7, 14, 29, 32, 45, 46] 着重训练用于文档解析的专用端到端专家模型。这些由 VLM 驱动的模型擅长理解视觉版面和文本内容，在准确性与效率之间取得权衡。

#### 2.3. 文档内容提取基准

文档内容提取需要理解文档版面并识别各类内容。然而，当前基准主要关注模块级识别性能，缺乏全面的页面级评测。PubLayNet [49] 与同时期基准 [9, 26, 35] 专注于评估模型检测文档页面版面的能力。OCRBench [31] 提出五项与 OCR 相关的任务，更侧重评估模型的视觉理解与推理能力；对于文本识别和手写数学表达式识别（Handwritten Mathematical Expression Recognition，HMER），仅提供行级评测。类似地，单模块基准 [20, 26, 40, 54] 将任务拆分到不同维度，并仅关注特定部分。这一范式忽视了阅读顺序等结构和语义信息的重要性，无法评估模型将整页文档作为整体处理时的综合能力。

一些近期由 VLM 驱动的专家模型 [7, 29, 45] 同时提出了页面级基准。然而，数据规模、语言、文档类型和标注方面的限制削弱了这些基准的稳健性。例如，Nougat [7] 只使用从 arXiv 收集的印刷体英文文档评估模型，而 GOT-OCR [45] 引入的页面级基准总共只有 90 页中英文文档。手写笔记、报纸和试卷等常见文档类型也被忽略。由于缺少详细标注，这些基准只能在真实标注（Ground Truth，GT）与预测结果之间进行简单的整页比较，未对不同输出格式进行专门处理，也未针对不同内容类型使用专门指标。有限的文档领域、不统一的输出格式和不匹配的指标可能严重偏置模型性能评估。因此，迫切需要一个标注更细致、更加多样化、更加合理的页面级文档内容提取基准。

### 3. OmniDocBench 数据集

构建具有精确标注、多样化且全面的文档解析基准是一项重大挑战。如图 3 所示，我们为 OmniDocBench 设计了系统、专业的标注框架，涵盖数据获取、智能预标注和人工精修。这确保了 OmniDocBench 具备以下关键属性：

- **页面多样性。**从不同来源获取文档页面，确保覆盖广泛的文档类型。
- **全面标注。**细致标注页面上的所有元素，包括边界框、具体内容以及各种潜在属性。
- **标注准确性。**结合半自动标注流程、标注员修正和专家质量检查，确保所有标注的可靠性。

下文详细介绍数据获取过程、标注方法，以及最终标注数据集的统计分析。

**图 3.** OmniDocBench 数据集构建概览。

#### 3.1. 数据获取

在数据获取阶段，我们从不同来源收集文档页面，利用聚类算法初步选择具有视觉多样性的页面，再通过人工标注页面属性，最终确定 OmniDocBench 的页面。具体而言，我们从 Common Crawl、Google、百度搜索引擎及内部数据中收集了超过 200,000 份初始 PDF 文档。随后使用 ResNet-50 提取页面视觉特征，以 Faiss¹ 进行聚类，从 10 个聚类中心抽样得到 6,000 个具有视觉多样性的页面。最后，标注员提供页面类型、版面类型和语言类型等页面级属性标注，并进一步平衡筛选，得到最终数据集的 981 个样本。OmniDocBench 数据集包含九种不同类型的页面、多种版面类别及各种属性标注，覆盖广泛的真实场景。

¹ https://github.com/facebookresearch/faiss

#### 3.2. 数据标注

为确保 OmniDocBench 标注的全面性，我们针对版面检测和内容识别开展了详细标注。

##### 3.2.1. 标注类型

**版面检测标注：**不同于典型的版面检测任务，OmniDocBench 包含四种全面的标注：（1）**版面边界框标注：**标题、文本段落、表格、图像等 19 个不同区域类别的位置信息。（2）**版面属性标注：**为检测框提供详细属性标注，包括 3 类文本框属性和 6 类表格属性，共 9 个边界框级属性标签。（3）**阅读顺序标注：**标注检测框的阅读序列。（4）**从属关系标注：**为图像、表格、公式和代码块标注图注／表注及标题，以区别于正文。同样，对跨页段落标注其从属关系。

**内容识别标注：**根据每个区域中的内容类型，开展三类标注：（1）**文本标注：**对标题、文本段落及其他纯文本内容进行纯文本标注。（2）**公式标注：**对行内公式、独立显示公式及下标进行 LaTeX 格式标注。（3）**表格标注：**同时提供表格数据的 HTML 和 LaTeX 标注。

##### 3.2.2. 标注流程

针对多样化页面中的这些标注任务，我们设计了标准化流程以确保质量和效率，包括智能自动标注、标注员修正和专家质量检查。

**自动标注。**人工标注整篇文档耗时且成本高。为提高效率，我们采用最先进的检测和识别模型，进行版面检测和内容识别的预标注。具体而言，使用经过微调的 LayoutLMv3 [17] 进行版面检测标注，并分别使用 PaddleOCR [23]、UniMERNet [40] 和 GPT-4o [2] 完成文本、公式和表格标注。

**标注员修正。**在版面检测阶段之后，标注员精修检测框，并补充阅读顺序和从属关系细节。内容识别中逐字符核验以确保准确性。对于需使用 LaTeX 和 HTML 格式的复杂表格、公式标注，标注员借助 Tables Generator² 和 latexlive³ 等工具进行核验和修正。

² https://www.tablesgenerator.com/

³ https://www.latexlive.com/

**专家质量检查。**即使经过全面的标注员修正，公式与表格的复杂性仍可能留下问题。为此，我们采用 CDM 的渲染技术 [41] 识别无法渲染的元素，再由三名研究人员审查并修正这些元素，以确保最终标注准确。

#### 3.3. 数据集统计

**页面多样性。**OmniDocBench 共包含 981 个 PDF 页面，覆盖 9 种不同类型。每页均标注全局属性，包括文本语言、分栏版面类型，以及是否存在扫描模糊、水印和彩色背景的标记。

**标注多样性：**OmniDocBench 包含超过 100,000 条用于页面检测和识别的标注：（1）15 个类别的块级标注超过 20,000 条，其中包括超过 15,979 个文本段落、989 个图像框、428 个表格框等。除页眉、页脚和页注外，所有文档组件均标注阅读顺序信息，共超过 16,000 条标注。（2）数据集还包含 4 个类别的超过 70,000 条片段级标注，其中 4,009 个行内公式和 357 个脚注标记以 LaTeX 格式表示，其余标注为文本格式。

**标注属性多样性：**（1）**文本属性：**除表格和图像外，所有块级标注都包含文本属性标签。除常规中英文文本外，还有超过 2,000 个具有复杂背景的文本块，以及 493 个带旋转文本的文本块。（2）**表格属性：**除常规中英文表格外，还包括 142 个具有复杂背景的表格、81 个含公式的表格、150 个具有合并单元格的表格，以及 7 个竖向表格。

### 4. OmniDocBench 评测方法

为公平、全面地评估各种模型，我们提出由提取、匹配算法、指标计算等多个模块组成的端到端评测流水线，如图 4 所示。该流水线确保 OmniDocBench 自动对文档解析进行统一评测，从而产生可靠、有效的结果。

**图 4.** OmniDocBench 评测流水线。

#### 4.1. 提取

**预处理。**需要对模型生成的 Markdown 文本进行预处理，包括移除图像、删除文档开头的 Markdown 标记，以及规范重复字符的数量。

**元素提取。**提取主要通过正则表达式匹配完成。为确保各类元素的提取互不干扰，必须遵循特定顺序：LaTeX 表格、HTML 表格、独立显示公式、Markdown 表格（随后转为 HTML 格式），最后是代码块。

**纯文本提取。**提取特殊组件后，剩余内容视为纯文本。以双换行分隔段落，使其参与后续匹配，与 GT 中的阅读顺序标注单元保持一致。若不存在双换行，则以单换行分隔段落。此外，先前提取的代码块会合并到文本类别中处理。

**行内公式格式转换。**我们将段落内的行内公式统一转换为 Unicode 格式。这是必要的，因为不同模型对行内公式的输出并不一致。对于原本以 Unicode 表示的公式，很难使用正则表达式提取。因此，为确保公平比较，我们不提取行内公式进行独立评测，而是将其以 Unicode 格式与文本段落一起评估。

**阅读顺序提取。**提取完成后，记录各提取内容在原始 Markdown 中的起止位置，用于后续阅读顺序计算。

#### 4.2. 匹配算法

**邻接搜索匹配（Adjacency Search Match）。**为避免段落划分对最终结果的影响，我们提出邻接搜索匹配，对 GT 和预测结果（Pred）中的段落进行合并与拆分，以获得尽可能好的匹配。具体策略如下：i）计算 GT 与 Pred 之间的归一化编辑距离矩阵。相似度超过特定阈值的 Pred–GT 对视为匹配成功。ii）对于剩余部分，使用模糊匹配判断一个字符串是否为另一个字符串的子集。如果是，则进一步使用合并算法，尝试合并相邻段落。该过程持续合并更多段落，直到归一化编辑距离开始下降为止[原文如此]。经过这一过程，便可找到 GT 与 Pred 的最佳匹配。

**忽略处理。**对 PDF 页面内容中的某些组件，我们采用忽略逻辑，即它们参与匹配，但不参与指标计算。主要原因是各模型输出规范不一致，这种不一致不应影响验证结果。为保证公平性，我们忽略：（1）不同模型处理方式不一致的页眉、页脚、页码和页面脚注；（2）图、表和脚注的说明文字，其位置通常不确定，增加了阅读顺序的复杂性。此外，部分模型将表格标题嵌入 HTML 或 LaTeX 表格，另一些模型则将其作为纯文本处理。

#### 4.3. 指标计算

**纯文本。**计算归一化编辑距离 [21]，在样本级取平均以得到最终得分。

**表格。**所有表格先转换为 HTML 格式，再计算基于树编辑距离的相似度（Tree-Edit-Distance-based Similarity，TEDS）[54] 与归一化编辑距离。

**公式。**当前使用字符检测匹配（Character Detection Matching，CDM）指标 [41]、归一化编辑距离及 BLEU [33] 评估公式。

**阅读顺序。**使用归一化编辑距离评估阅读顺序，仅涉及文本组件，表格、图像和被忽略组件均不参与最终的阅读顺序计算。

⁴ https://mathpix.com/

⁵ https://github.com/tesseract-ocr/tesseract

⁶ https://github.com/VikParuchuri/surya

⁷ https://github.com/lukas-blecher/LaTeX-OCR

**表 2. OmniDocBench 上文档解析算法的综合评测：**文本、公式、表格及阅读顺序提取的性能指标，以及通过与真实标注比较得到的总体得分。Edit 为编辑距离（↓）；CDM 和 TEDS 越大越好（↑）。EN／ZH 分别为英文／中文；粗体保留原表突出显示的结果。

| 方法类型 | 方法 | 文本 Edit EN | 文本 Edit ZH | 公式 Edit EN | 公式 Edit ZH | 公式 CDM EN | 公式 CDM ZH | 表格 TEDS EN | 表格 TEDS ZH | 表格 Edit EN | 表格 Edit ZH | 阅读顺序 Edit EN | 阅读顺序 Edit ZH | 总体 Edit EN | 总体 Edit ZH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 流水线工具 | MinerU [42] | **0.061** | **0.215** | **0.278** | 0.577 | 57.3 | 42.9 | **78.6** | 62.1 | **0.18** | 0.344 | **0.079** | 0.292 | **0.15** | 0.357 |
| 流水线工具 | Marker [34] | 0.08 | 0.315 | 0.53 | 0.883 | 17.6 | 11.7 | 67.6 | 49.2 | 0.619 | 0.685 | 0.114 | 0.34 | 0.336 | 0.556 |
| 流水线工具 | Mathpix⁴ | 0.105 | 0.384 | 0.306 | **0.454** | 62.7 | **62.1** | 77.0 | 67.1 | 0.243 | **0.32** | 0.108 | 0.304 | 0.191 | 0.365 |
| 专家 VLM | GOT-OCR [45] | 0.189 | 0.315 | 0.360 | 0.528 | 74.3 | 45.3 | 53.2 | 47.2 | 0.459 | 0.52 | 0.141 | 0.28 | 0.287 | 0.411 |
| 专家 VLM | Nougat [7] | 0.365 | 0.998 | 0.488 | 0.941 | 15.1 | 16.8 | 39.9 | 0.0 | 0.572 | 1.000 | 0.382 | 0.954 | 0.452 | 0.973 |
| 通用 VLM | GPT4o [2] | 0.144 | 0.409 | 0.425 | 0.606 | 72.8 | 42.8 | 72.0 | 62.9 | 0.234 | 0.329 | 0.128 | 0.251 | 0.233 | 0.399 |
| 通用 VLM | Qwen2-VL-72B [44] | 0.096 | 0.218 | 0.404 | 0.487 | **82.2** | 61.2 | 76.8 | **76.4** | 0.387 | 0.408 | 0.119 | **0.193** | 0.252 | **0.327** |
| 通用 VLM | InternVL2-76B [8] | 0.353 | 0.290 | 0.543 | 0.701 | 67.4 | 44.1 | 63.0 | 60.2 | 0.547 | 0.555 | 0.317 | 0.228 | 0.44 | 0.443 |

**表 3. OmniDocBench 上的端到端文本识别性能：**使用编辑距离评估 9 种 PDF 页面类型。

| 模型类型 | 模型 | 书籍 | 幻灯片 | 财务报告 | 教科书 | 试卷 | 杂志 | 学术论文 | 笔记 | 报纸 | 总体 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 流水线工具 | MinerU [42] | **0.055** | 0.124 | **0.033** | **0.102** | **0.159** | 0.072 | **0.025** | 0.984 | **0.171** | 0.206 |
| 流水线工具 | Marker [34] | 0.074 | 0.34 | 0.089 | 0.319 | 0.452 | 0.153 | 0.059 | 0.651 | 0.192 | 0.274 |
| 流水线工具 | Mathpix⁴ | 0.131 | 0.22 | 0.202 | 0.216 | 0.278 | 0.147 | 0.091 | 0.634 | 0.69 | 0.3 |
| 专家 VLM | GOT-OCR [45] | 0.111 | 0.222 | 0.067 | 0.132 | 0.204 | 0.198 | 0.179 | 0.388 | 0.771 | 0.267 |
| 专家 VLM | Nougat [7] | 0.734 | 0.958 | 1.000 | 0.820 | 0.930 | 0.83 | 0.214 | 0.991 | 0.871 | 0.806 |
| 通用 VLM | GPT4o [2] | 0.157 | 0.163 | 0.348 | 0.187 | 0.281 | 0.173 | 0.146 | 0.607 | 0.751 | 0.316 |
| 通用 VLM | Qwen2-VL-72B [44] | 0.096 | **0.061** | 0.047 | 0.149 | 0.195 | **0.071** | 0.085 | **0.168** | 0.676 | **0.179** |
| 通用 VLM | InternVL2-76B [8] | 0.216 | 0.098 | 0.162 | 0.184 | 0.247 | 0.150 | 0.419 | 0.226 | 0.903 | 0.3 |

**表 4. OmniDocBench 上的端到端文本识别：**在各种页面属性下使用编辑距离评测。数值为该属性组得分的均值／方差。各列分别表示模糊扫描、水印、彩色背景以及无特殊问题。

| 模型 | 模糊扫描 | 水印 | 彩色背景 | 无特殊问题 |
|---|---|---|---|---|
| MinerU [42] | 0.15/0.048 | **0.151/0.031** | 0.107/0.052 | 0.079/0.035 |
| Marker [34] | 0.333/0.092 | 0.484/0.126 | 0.319/0.127 | **0.062/0.125** |
| Mathpix⁴ | 0.294/0.064 | 0.290/0.059 | 0.216/0.09 | 0.135/0.043 |
| GOT-OCR [45] | 0.175/0.05 | 0.190/0.056 | 0.186/0.097 | 0.177/0.081 |
| Nougat [7] | 0.934/0.051 | 0.915/0.071 | 0.873/0.096 | 0.615/0.208 |
| GPT4o [2] | 0.263/0.078 | 0.195/0.057 | 0.184/0.078 | 0.186/0.072 |
| Qwen2-VL-72B [44] | **0.082/0.01** | 0.172/0.078 | **0.104/0.05** | 0.084/0.042 |
| InternVL2-76B [8] | 0.120/0.013 | 0.197/0.042 | 0.155/0.059 | 0.261/0.082 |

**表 5. OmniDocBench 上的端到端阅读顺序评测：**使用归一化编辑距离，报告不同分栏版面类型上的结果。数值为该属性组得分的均值／方差。

| 模型 | 单栏 | 双栏 | 三栏 | 复杂版面 |
|---|---|---|---|---|
| MinerU [42] | 0.311/0.187 | **0.101/0.013** | **0.117/0.046** | 0.385/0.057 |
| Marker [34] | 0.299/0.143 | 0.299/0.299 | 0.149/0.063 | **0.363/0.086** |
| Mathpix⁴ | 0.207/0.123 | 0.188/0.07 | 0.225/0.029 | 0.452/0.177 |
| GOT-OCR [45] | 0.163/0.106 | 0.145/0.059 | 0.257/0.072 | 0.468/0.185 |
| Nougat [7] | 0.852/0.084 | 0.601/0.224 | 0.662/0.093 | 0.873/0.09 |
| GPT4o [2] | 0.109/0.112 | 0.204/0.076 | 0.254/0.046 | 0.426/0.188 |
| Qwen2-VL-72B [44] | **0.066/0.048** | 0.145/0.049 | 0.204/0.055 | 0.394/0.203 |
| InternVL2-76B [8] | 0.082/0.052 | 0.312/0.069 | 0.682/0.098 | 0.444/0.174 |

### 5. 基准评测

依据算法的不同特点，我们将文档内容提取方法划分为三大类：

- **流水线工具：**将版面检测和 OCR、表格识别、公式识别等内容识别任务集成到文档解析流水线中完成内容提取。典型例子包括 MinerU [42]（v0.9.3）、Marker [34]（v1.2.3）和 Mathpix⁴。
- **专家 VLM：**专门为文档解析任务训练的大型多模态模型，代表模型包括 GOT-OCR2.0 [45] 和 Nougat [7]。
- **通用 VLM：**自身具备文档解析能力的通用大型多模态模型，代表模型包括 GPT-4o [2]、Qwen2-VL-72B [44] 和 InternVL2-76B [8]。

#### 5.1. 端到端评测结果

**总体评测结果。**如表 2 所示，MinerU 和 Mathpix 等流水线工具在文本识别、公式识别、表格识别等子任务上展现出优越性能。此外，通用 VLM Qwen2-VL 和 GPT4o 也展现出有竞争力的表现。几乎所有算法在英文页面上的得分都优于中文页面。

**不同页面类型上的表现。**为深入了解模型在不同文档类型上的性能，我们针对不同页面类型评估文本识别任务。如表 3 所示，一个有意思的现象是，流水线工具在学术论文、财务报告等常用数据上表现良好；对于幻灯片、手写笔记等更特殊的数据，通用 VLM 则展现出更强的泛化能力。值得注意的是，大多数 VLM 在处理报纸时识别失败，而流水线工具表现明显更好。

**存在视觉退化的页面上的表现。**表 4 进一步分析了常见文档问题下的表现，包括模糊扫描、水印和彩色背景。尽管存在视觉噪声，InternVL2 和 Qwen2-VL 等 VLM 在这些场景中仍表现出更高的稳健性。流水线工具中，MinerU 凭借强大的版面分割和预处理能力，仍然具有竞争力。

**不同版面类型上的表现。**页面版面是文档理解中的关键因素，尤其影响阅读顺序任务。OmniDocBench 标注单栏、多栏和复杂自定义格式等版面属性。我们观察到，所有模型在多栏和复杂版面上的准确性均明显下降。MinerU 的阅读顺序预测最为稳定，但在手写单栏页面上，其性能会受到识别噪声影响而下降。

**端到端结果讨论。**1）通用 VLM 在学术论文等标准文档上往往落后于专门的流水线和专家模型，但对笔记等非常规格式有更好的泛化能力，在模糊扫描等退化条件下也更加稳健。这主要得益于更广泛的训练数据，相较于在狭窄领域训练的模型，它们能更好地处理长尾场景。2）然而，VLM 受输入分辨率和 token 长度限制，难以处理报纸等高密度文档。相比之下，流水线工具利用基于版面的分割，逐个处理组件，能在复杂版面中保持准确性。通过版面感知设计和领域专用微调增强 VLM，是值得探索的方向。OmniDocBench 提供版面、文本、公式和表格的详细标注，为多样化文档解析任务的全面基准评测与模块化工具开发提供支持。

#### 5.2. 单任务评测结果

**版面检测结果。**版面检测是流水线工具文档解析的第一步。稳健的版面检测算法应在多种文档类型上表现良好。表 6 评估了主流版面检测模型。DocLayout-YOLO 在多样化合成文档数据上预训练，显著优于其他方法。这一优势是 MinerU 集成 DocLayout-YOLO 的关键因素，并促成其出色的总体表现。其他方法在书籍和学术文献上表现良好，但受训练数据有限的影响，在更丰富的格式上表现不佳。

**表 6. OmniDocBench 版面子集上的组件级版面检测评测：**按 PDF 页面类型报告 mAP 结果。

| 模型 | 骨干网络 | 参数量 | 书籍 | 幻灯片 | 研究报告 | 教科书 | 试卷 | 杂志 | 学术文献 | 笔记 | 报纸 | 平均 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DiT-L [24] | ViT-L | 361.6M | 43.44 | 13.72 | 45.85 | 15.45 | 3.40 | 29.23 | **66.13** | 0.21 | 23.65 | 26.90 |
| LayoutLMv3 [17] | RoBERTa-B | 138.4M | 42.12 | 13.63 | 43.22 | 21.00 | 5.48 | 31.81 | 64.66 | 0.80 | 30.84 | 28.84 |
| DocLayout-YOLO [53] | v10m | 19.6M | **43.71** | **48.71** | **72.83** | **42.67** | **35.40** | 51.44 | 64.64 | 9.54 | **57.54** | **47.38** |
| SwinDocSegmenter [4] | Swin-L | 223M | 42.91 | 28.20 | 47.29 | 32.44 | 20.81 | **52.35** | 48.54 | **12.38** | 38.06 | 35.89 |
| GraphKD [5] | R101 | 44.5M | 39.03 | 16.18 | 39.92 | 22.82 | 14.31 | 37.61 | 44.43 | 5.71 | 23.86 | 27.10 |
| DOCX-Chain [50] | — | — | 30.86 | 11.71 | 39.62 | 19.23 | 10.67 | 23.00 | 41.60 | 1.80 | 16.96 | 21.27 |

**表格识别结果。**表 7 在 OmniDocBench 表格子集上从语言多样性、表格边框类型和特殊情况三个维度评测表格识别模型。在所有模型中，基于 OCR 的模型总体表现更好，其中 RapidTable 在语言多样性方面取得最高得分，并在不同边框类型上保持稳定性能。专家 VLM 在特定场景中表现出竞争力，StructEqTable [55] 尤其擅长无边框表格，并具有更好的旋转稳健性。通用 VLM（Qwen2-VL-7B 和 InternVL2-8B）的性能相对较低，但较为一致，说明虽然通用 VLM 在表格理解方面取得了进展，仍落后于专门的解决方案。

**表 7. OmniDocBench 表格子集上的组件级表格识别评测。**（+/−）表示存在／不存在相应特殊情况。

| 模型类型 | 模型 | 英文 | 中文 | 混合语言 | 全边框 | 省略线 | 三线表 | 无边框 | 合并单元格(+/−) | 公式(+/−) | 彩色背景(+/−) | 旋转(+/−) | 总体 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 基于 OCR | PaddleOCR [23] | 76.8 | 71.8 | 80.1 | 67.9 | 74.3 | 81.1 | 74.5 | 70.6/75.2 | 71.3/74.1 | 72.7/74.0 | 23.3/74.6 | 73.6 |
| 基于 OCR | RapidTable [37] | **80.0** | **83.2** | **91.2** | **83.0** | **79.7** | **83.4** | 78.4 | **77.1/85.4** | **76.7/83.9** | **77.6/84.9** | 25.2/83.7 | **82.5** |
| 专家 VLM | StructEqTable [55] | 72.8 | 75.9 | 83.4 | 72.9 | 76.2 | 76.9 | **88.0** | 64.5/81.0 | 69.2/76.6 | 72.8/76.4 | **30.5/76.2** | 75.8 |
| 专家 VLM | GOT-OCR [45] | 72.2 | 75.5 | 85.4 | 73.1 | 72.7 | 78.2 | 75.7 | 65.0/80.2 | 64.3/77.3 | 70.8/76.9 | 8.5/76.3 | 74.9 |
| 通用 VLM | Qwen2-VL-7B [44] | 70.2 | 70.7 | 82.4 | 70.2 | 62.8 | 74.5 | 80.3 | 60.8/76.5 | 63.8/72.6 | 71.4/70.8 | 20.0/72.1 | 71.0 |
| 通用 VLM | InternVL2-8B [8] | 70.9 | 71.5 | 77.4 | 69.5 | 69.2 | 74.8 | 75.8 | 58.7/78.4 | 62.4/73.6 | 68.2/73.1 | 20.4/72.6 | 71.5 |

**文本识别结果。**表 8 使用编辑距离，比较不同语言、背景和旋转条件下的 OCR 工具。PaddleOCR 优于所有竞争方法，其次是 GOT-OCR 和 Mathpix。通用 VLM 难以处理文本旋转或混合语言场景。

**表 8. OmniDocBench OCR 子集上的组件级评测：**使用编辑距离，按文本属性分组。背景分为白色、单色、多色；旋转属性包括正常、旋转 90°、旋转 270°和 Horizontal（横向）。

| 模型类型 | 模型 | 英文 | 中文 | 混合语言 | 白色背景 | 单色背景 | 多色背景 | 正常 | 旋转90° | 旋转270° | 横向 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 专家视觉模型 | PaddleOCR [23] | 0.071 | **0.055** | **0.118** | **0.060** | **0.038** | **0.085** | **0.060** | **0.015** | 0.285 | **0.021** |
| 专家视觉模型 | Tesseract OCR⁵ | 0.179 | 0.553 | 0.553 | 0.453 | 0.463 | 0.394 | 0.448 | 0.369 | 0.979 | 0.982 |
| 专家视觉模型 | Surya⁶ | 0.057 | 0.123 | 0.164 | 0.093 | 0.186 | 0.235 | 0.104 | 0.634 | 0.767 | 0.255 |
| 专家视觉模型 | GOT-OCR [45] | 0.041 | 0.112 | 0.135 | 0.092 | 0.052 | 0.155 | 0.091 | 0.562 | 0.966 | 0.097 |
| 专家视觉模型 | Mathpix⁴ | 0.033 | 0.240 | 0.261 | 0.185 | 0.121 | 0.166 | 0.180 | 0.038 | **0.185** | 0.638 |
| 视觉语言模型 | Qwen2-VL-72B [44] | 0.072 | 0.274 | 0.286 | 0.234 | 0.155 | 0.148 | 0.223 | 0.273 | 0.721 | 0.067 |
| 视觉语言模型 | InternVL2-76B [8] | 0.074 | 0.155 | 0.242 | 0.113 | 0.352 | 0.269 | 0.132 | 0.610 | 0.907 | 0.595 |
| 视觉语言模型 | GPT4o [2] | **0.020** | 0.224 | 0.125 | 0.167 | 0.140 | 0.220 | 0.168 | 0.115 | 0.718 | 0.132 |

**公式识别结果。**表 9 使用 CDM、BLEU 和归一化编辑距离报告公式解析结果。GPT-4o、Mathpix 和 UniMERNet 分别达到 86.8%、86.6% 和 85.0%。值得注意的是，在要求字符完全准确的严格条件下，GPT-4o 以 65.5% 的召回率表现突出。虽然 Mathpix 的字符级精度较高，但偶尔会漏掉逗号等标点，导致整体正确率较低。尽管如此，这三个模型都是公式识别任务的有力候选。

**表 9. OmniDocBench 公式子集上的组件级公式识别评测。**

| 模型 | CDM | ExpRate@CDM | BLEU | 归一化编辑距离 |
|---|---|---|---|---|
| GOT-OCR [45] | 74.1 | 28.0 | 55.07 | 0.290 |
| Mathpix⁴ | 86.6 | 2.8 | **66.56** | 0.322 |
| Pix2Tex⁷ | 73.9 | 39.5 | 46.00 | 0.337 |
| UniMERNet-B [40] | 85.0 | 60.2 | 60.84 | **0.238** |
| GPT4o [2] | **86.8** | **65.5** | 45.17 | 0.282 |
| InternVL2-76B [8] | 67.4 | 54.5 | 47.63 | 0.308 |
| Qwen2-VL-72B [44] | 83.8 | 55.4 | 53.71 | 0.285 |

### 6. 结论

本文针对文档解析研究中缺乏多样化、贴近现实的基准这一问题，提出 OmniDocBench：一个覆盖多种页面类型、具备全面标注的数据集，并配套灵活可靠的评测框架。OmniDocBench 支持系统、公平地评估文档解析方法，为推动该领域发展提供重要见解。其任务专项和属性级评测支持有针对性的模型优化，促进更稳健、有效的解析方案。

### 7. 致谢

本项目得到国家重点研发计划（编号：2022ZD0160102）和上海人工智能实验室的支持。

### 参考文献

条目末尾数字为原文保留的文内引用页码。

[1] Josh Achiam, Steven Adler, Sandhini Agarwal, Lama Ahmad, Ilge Akkaya, Florencia Leoni Aleman, Diogo Almeida, Janko Altenschmidt, Sam Altman, Shyamal Anadkat, et al. Gpt-4 technical report. arXiv:2303.08774, 2023. 1

中文题名及出版信息说明：GPT-4 技术报告。

[2] Open AI. Hello gpt 4o, 2024. Accessed July 24, 2024. 3, 4, 6, 7, 8

中文题名及出版信息说明：你好，GPT-4o。访问日期：2024 年 7 月 24 日。

[3] Jinze Bai, Shuai Bai, Shusheng Yang, Shijie Wang, Sinan Tan, Peng Wang, Junyang Lin, Chang Zhou, and Jingren Zhou. Qwen-vl: A versatile vision-language model for understanding, localization, text reading, and beyond. arXiv:2308.12966, 2024. 1, 3

中文题名及出版信息说明：Qwen-VL：用于理解、定位、文本阅读及更多任务的通用视觉语言模型。

[4] Ayan Banerjee, Sanket Biswas, Josep Llad ́os, and Umapada Pal. Swindocsegmenter: An end-to-end unified domain adaptive transformer for document instance segmentation. In ICDAR, 2023. 7

中文题名及出版信息说明：SwinDocSegmenter：面向文档实例分割的端到端统一域自适应 Transformer。ICDAR：国际文档分析与识别大会。

[5] Ayan Banerjee, Sanket Biswas, Josep Llad ́os, and Umapada Pal. Graphkd: Exploring knowledge distillation towards document object detection with structured graph creation. In ICDAR, 2024. 7

中文题名及出版信息说明：GraphKD：通过结构化图构建探索面向文档目标检测的知识蒸馏。ICDAR：国际文档分析与识别大会。

[6] Lukas Blecher. pix2tex - latex ocr. https://github.com/lukas-blecher/LaTeX-OCR, 2022. Accessed: 2024-2-29. 2

中文题名及出版信息说明：pix2tex：LaTeX 光学字符识别。访问日期：2024-2-29。

[7] Lukas Blecher, Guillem Cucurull, Thomas Scialom, and Robert Stojnic. Nougat: Neural optical understanding for academic documents. arXiv:2308.13418, 2024. 1, 2, 3, 6, 7

中文题名及出版信息说明：Nougat：面向学术文档的神经光学理解。

[8] Zhe Chen, Jiannan Wu, Wenhai Wang, Weijie Su, Guo Chen, Sen Xing, Muyan Zhong, Qinglong Zhang, Xizhou Zhu, Lewei Lu, Bin Li, Ping Luo, Tong Lu, Yu Qiao, and Jifeng Dai. Internvl: Scaling up vision foundation models and aligning for generic visual-linguistic tasks. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 24185–24198, 2024. 1, 6, 7, 8

中文题名及出版信息说明：InternVL：扩展视觉基础模型并对齐通用视觉语言任务。IEEE/CVF Conference on Computer Vision and Pattern Recognition（CVPR）：IEEE/CVF 计算机视觉与模式识别会议。

[9] Hiuyi Cheng, Peirong Zhang, Sihang Wu, Jiaxin Zhang, Qiyuan Zhu, Zecheng Xie, Jing Li, Kai Ding, and Lianwen Jin. M6doc: A large-scale multi-format, multi-type, multi-layout, multi-language, multi-annotation category dataset for modern document layout analysis. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 15138–15147, 2023. 3

中文题名及出版信息说明：M6Doc：面向现代文档版面分析的大规模多格式、多类型、多版面、多语言、多标注类别数据集。CVPR：IEEE/CVF 计算机视觉与模式识别会议。

[10] Yuntian Deng, Anssi Kanervisto, Jeffrey Ling, and Alexander M Rush. Image-to-markup generation with coarse-to-fine attention. In International Conference on Machine Learning, pages 980–989. PMLR, 2017. 1, 3

中文题名及出版信息说明：通过由粗到细的注意力进行图像到标记语言生成。International Conference on Machine Learning：国际机器学习大会。

[11] Harsh Desai, Pratik Kayal, and Mayank Singh. Tablex: a benchmark dataset for structure and content information extraction from scientific tables. In Document Analysis and Recognition–ICDAR 2021: 16th International Conference, pages 554–569, 2021. 3

中文题名及出版信息说明：TableX：用于从科学表格中提取结构与内容信息的基准数据集。Document Analysis and Recognition–ICDAR 2021: 16th International Conference：第 16 届国际文档分析与识别大会。

[12] Yunfan Gao, Yun Xiong, Xinyu Gao, Kangxiang Jia, Jinliu Pan, Yuxi Bi, Yi Dai, Jiawei Sun, Meng Wang, and Haofen Wang. Retrieval-augmented generation for large language models: A survey. arXiv:2312.10997, 2023. 1

中文题名及出版信息说明：大语言模型的检索增强生成：综述。

[13] Jiuxiang Gu, Jason Kuen, Vlad I Morariu, Handong Zhao, Rajiv Jain, Nikolaos Barmpalios, Ani Nenkova, and Tong Sun. Unidoc: Unified pretraining framework for document understanding. Advances in Neural Information Processing Systems, 34:39–50, 2021. 2

中文题名及出版信息说明：UniDoc：用于文档理解的统一预训练框架。Advances in Neural Information Processing Systems：神经信息处理系统进展。

[14] Anwen Hu, Haiyang Xu, Liang Zhang, Jiabo Ye, Ming Yan, Ji Zhang, Qin Jin, Fei Huang, and Jingren Zhou. mplug-docowl2: High-resolution compressing for ocr-free multi-page document understanding. arXiv preprint arXiv:2409.03420, 2024. 3

中文题名及出版信息说明：mPLUG-DocOwl2：通过高分辨率压缩实现无需 OCR 的多页文档理解。

[15] Mingxin Huang, Yuliang Liu, Zhenghao Peng, Chongyu Liu, Dahua Lin, Shenggao Zhu, Nicholas Yuan, Kai Ding, and Lianwen Jin. Swintextspotter: Scene text spotting via better synergy between text detection and text recognition. In proceedings of the IEEE/CVF conference on computer vision and pattern recognition, pages 4593–4603, 2022. 2

中文题名及出版信息说明：SwinTextSpotter：通过文本检测与文本识别更好的协同实现自然场景文本定位与识别。CVPR：IEEE/CVF 计算机视觉与模式识别会议。

[16] Xin Huang, Ashish Khetan, Milan Cvitkovic, and Zohar Karnin. Tabtransformer: Tabular data modeling using contextual embeddings. arxiv 2020. arXiv preprint arXiv:2012.06678, 2012. 2

中文题名及出版信息说明：TabTransformer：利用上下文嵌入进行表格数据建模。arxiv 2020；条目年份写为 2012[原文如此]。

[17] Yupan Huang, Tengchao Lv, Lei Cui, Yutong Lu, and Furu Wei. Layoutlmv3: Pre-training for document ai with unified text and image masking, 2022. 2, 4, 7

中文题名及出版信息说明：LayoutLMv3：采用统一文本和图像掩码的文档 AI 预训练。

[18] Yongshuai Huang, Ning Lu, Dapeng Chen, Yibo Li, Zecheng Xie, Shenggao Zhu, Liangcai Gao, and Wei Peng. Improving table structure recognition with visual-alignment sequential coordinate modeling. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition, pages 11134–11143, 2023. 2

中文题名及出版信息说明：通过视觉对齐的序列坐标建模改进表格结构识别。CVPR：IEEE/CVF 计算机视觉与模式识别会议。

[19] Wonseok Hwang, Jinyeong Yim, Seunghyun Park, Sohee Yang, and Minjoon Seo. Spatial dependency parsing for semi-structured document information extraction. In Findings of the Association for Computational Linguistics: ACL-IJCNLP, pages 330–343. Association for Computational Linguistics (ACL), 2021. 1

中文题名及出版信息说明：面向半结构化文档信息提取的空间依存解析。Findings of the Association for Computational Linguistics: ACL-IJCNLP：计算语言学协会研究成果集；Association for Computational Linguistics（ACL）：计算语言学协会。

[20] Dimosthenis Karatzas, Lluis Gomez-Bigorda, Anguelos Nicolaou, Suman Ghosh, Andrew Bagdanov, Masakazu Iwamura, Jiri Matas, Lukas Neumann, Vijay Ramaseshan Chandrasekhar, Shijian Lu, Faisal Shafait, Seiichi Uchida, and Ernest Valveny. Icdar 2015 competition on robust reading. In 2015 13th International Conference on Document Analysis and Recognition, pages 1156–1160, 2015. 3

中文题名及出版信息说明：ICDAR 2015 鲁棒阅读竞赛。2015 13th International Conference on Document Analysis and Recognition：2015 年第 13 届国际文档分析与识别大会。

[21] Vladimir I Levenshtein et al. Binary codes capable of correcting deletions, insertions, and reversals. In Doklady Physics, pages 707–710. Soviet Union, 1966. 2, 6

中文题名及出版信息说明：能够纠正删除、插入和反转的二进制编码。Doklady Physics：物理学报告；Soviet Union：苏联。

[22] Patrick Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Naman Goyal, Heinrich K ̈uttler, Mike Lewis, Wen-tau Yih, Tim Rockt ̈aschel, et al. Retrieval-augmented generation for knowledge-intensive nlp tasks. Advances in Neural Information Processing Systems, 33:9459–9474, 2020. 1

中文题名及出版信息说明：面向知识密集型自然语言处理任务的检索增强生成。Advances in Neural Information Processing Systems：神经信息处理系统进展。

[23] Chenxia Li, Weiwei Liu, Ruoyu Guo, Xiaoting Yin, Kaitao Jiang, Yongkun Du, Yuning Du, Lingfeng Zhu, Baohua Lai, Xiaoguang Hu, Dianhai Yu, and Yanjun Ma. Pp-ocrv3: More attempts for the improvement of ultra lightweight ocr system, 2022. 2, 4, 7, 8

中文题名及出版信息说明：PP-OCRv3：对超轻量 OCR 系统改进的更多尝试。

[24] Junlong Li, Yiheng Xu, Tengchao Lv, Lei Cui, Cha Zhang, and Furu Wei. Dit: Self-supervised pre-training for document image transformer. In ACMMM, 2022. 7

中文题名及出版信息说明：DiT：文档图像 Transformer 的自监督预训练。ACMMM：ACM 国际多媒体会议。

[25] Minghao Li, Lei Cui, Shaohan Huang, Furu Wei, Ming Zhou, and Zhoujun Li. Tablebank: Table benchmark for image-based table detection and recognition. In Proceedings of the Twelfth Language Resources and Evaluation Conference, pages 1918–1925, 2020. 3

中文题名及出版信息说明：TableBank：面向基于图像的表格检测和识别的表格基准。Twelfth Language Resources and Evaluation Conference：第十二届语言资源与评测会议。

[26] Minghao Li, Yiheng Xu, Lei Cui, Shaohan Huang, Furu Wei, Zhoujun Li, and Ming Zhou. Docbank: A benchmark dataset for document layout analysis. arXiv:2006.01038, 2020. 1, 3

中文题名及出版信息说明：DocBank：文档版面分析基准数据集。

[27] Zhe Li, Lianwen Jin, Songxuan Lai, and Yecheng Zhu. Improving attention-based handwritten mathematical expression recognition with scale augmentation and drop attention. In 2020 17th International Conference on Frontiers in Handwriting Recognition (ICFHR), pages 175–180. IEEE, 2020. 2

中文题名及出版信息说明：通过尺度增强与注意力丢弃改进基于注意力的手写数学表达式识别。2020 17th International Conference on Frontiers in Handwriting Recognition（ICFHR）：2020 年第 17 届手写识别前沿国际会议。

[28] Aixin Liu, Bei Feng, Bing Xue, Bingxuan Wang, Bochao Wu, Chengda Lu, Chenggang Zhao, Chengqi Deng, Chenyu Zhang, Chong Ruan, et al. Deepseek-v3 technical report. arXiv preprint arXiv:2412.19437, 2024. 1

中文题名及出版信息说明：DeepSeek-V3 技术报告。

[29] Chenglong Liu, Haoran Wei, Jinyue Chen, Lingyu Kong, Zheng Ge, Zining Zhu, Liang Zhao, Jianjian Sun, Chunrui Han, and Xiangyu Zhang. Focus anywhere for fine-grained multi-page document understanding. arXiv:2405.14295, 2024. 1, 3

中文题名及出版信息说明：随处聚焦，实现细粒度多页文档理解。

[30] Yuliang Liu, Hao Chen, Chunhua Shen, Tong He, Lianwen Jin, and Liangwei Wang. Abcnet: Real-time scene text spotting with adaptive bezier-curve network. In proceedings of the IEEE/CVF conference on computer vision and pattern recognition, pages 9809–9818, 2020. 2

中文题名及出版信息说明：ABCNet：基于自适应贝塞尔曲线网络的实时自然场景文本定位与识别。CVPR：IEEE/CVF 计算机视觉与模式识别会议。

[31] Yuliang Liu, Zhang Li, Mingxin Huang, Biao Yang, Wenwen Yu, Chunyuan Li, Xu-Cheng Yin, Cheng-Lin Liu, Lianwen Jin, and Xiang Bai. Ocrbench: on the hidden mystery of ocr in large multimodal models. Science China Information Sciences, 67(12), 2024. 3

中文题名及出版信息说明：OCRBench：大型多模态模型中 OCR 的隐秘奥秘。Science China Information Sciences：中国科学：信息科学。

[32] Tengchao Lv, Yupan Huang, Jingye Chen, Yuzhong Zhao, Yilin Jia, Lei Cui, Shuming Ma, Yaoyao Chang, Shaohan Huang, Wenhui Wang, Li Dong, Weiyao Luo, Shaoxiang Wu, Guoxin Wang, Cha Zhang, and Furu Wei. Kosmos-2.5: A multimodal literate model, 2024. 3

中文题名及出版信息说明：Kosmos-2.5：一个具备读写能力的多模态模型。

[33] Kishore Papineni, Salim Roukos, Todd Ward, and Wei-Jing Zhu. Bleu: a method for automatic evaluation of machine translation. pages 311–318, 2002. 2, 6

中文题名及出版信息说明：BLEU：一种机器翻译自动评测方法。

[34] Vik Paruchuri. Marker, 2024. 1, 3, 6, 7

中文题名及出版信息说明：Marker。

[35] Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S Nassar, and Peter Staar. Doclaynet: A large human-annotated dataset for document-layout segmentation. In Proceedings of the 28th ACM SIGKDD conference on knowledge discovery and data mining, pages 3743–3751, 2022. 3

中文题名及出版信息说明：DocLayNet：一个用于文档版面分割的大规模人工标注数据集。28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining：第 28 届 ACM SIGKDD 知识发现与数据挖掘会议。

[36] Subhojeet Pramanik, Shashank Mujumdar, and Hima Patel. Towards a multi-modal, multi-task learning based pretraining framework for document representation learning. arXiv preprint arXiv:2009.14457, 2020. 2

中文题名及出版信息说明：迈向基于多模态、多任务学习的文档表示学习预训练框架。

[37] RapidAI. Rapidtable. https://github.com/RapidAI/RapidTable, 2023. 7

中文题名及出版信息说明：RapidTable。

[38] Ray Smith, Daria Antonova, and Dar-Shyang Lee. Adapting the tesseract open source ocr engine for multilingual ocr. In Proceedings of the International Workshop on Multilingual OCR, 2009. 2

中文题名及出版信息说明：使 Tesseract 开源 OCR 引擎适应多语言 OCR。International Workshop on Multilingual OCR：多语言 OCR 国际研讨会。

[39] Hugo Touvron, Thibaut Lavril, Gautier Izacard, Xavier Martinet, Marie-Anne Lachaux, Timoth ́ee Lacroix, Baptiste Rozière, Naman Goyal, Eric Hambro, Faisal Azhar, et al. Llama: Open and efficient foundation language models. arXiv preprint arXiv:2302.13971, 2023. 1

中文题名及出版信息说明：LLaMA：开放且高效的基础语言模型。

[40] Bin Wang, Zhuangcheng Gu, Guang Liang, Chao Xu, Bo Zhang, Botian Shi, and Conghui He. Unimernet: A universal network for real-world mathematical expression recognition, 2024. 2, 3, 4, 8

中文题名及出版信息说明：UniMERNet：用于真实世界数学表达式识别的通用网络。

[41] Bin Wang, Fan Wu, Linke Ouyang, Zhuangcheng Gu, Rui Zhang, Renqiu Xia, Bo Zhang, and Conghui He. Cdm: A reliable metric for fair and accurate formula recognition evaluation. arXiv:2409.03643, 2024. 5, 6

中文题名及出版信息说明：CDM：用于公平、准确的公式识别评测的可靠指标。

[42] Bin Wang, Chao Xu, Xiaomeng Zhao, Linke Ouyang, Fan Wu, Zhiyuan Zhao, Rui Xu, Kaiwen Liu, Yuan Qu, Fukai Shang, Bo Zhang, Liqun Wei, Zhihao Sui, Wei Li, Botian Shi, Yu Qiao, Dahua Lin, and Conghui He. Mineru: An open-source solution for precise document content extraction. arXiv:2409.18839, 2024. 1, 3, 6, 7

中文题名及出版信息说明：MinerU：用于精确文档内容提取的开源解决方案。

[43] Pengfei Wang, Chengquan Zhang, Fei Qi, Shanshan Liu, Xiaoqiang Zhang, Pengyuan Lyu, Junyu Han, Jingtuo Liu, Errui Ding, and Guangming Shi. Pgnet: Real-time arbitrarily-shaped text spotting with point gathering network. In Proceedings of the AAAI Conference on Artificial Intelligence, pages 2782–2790, 2021. 2

中文题名及出版信息说明：PGNet：基于点聚合网络的实时任意形状文本定位与识别。AAAI Conference on Artificial Intelligence：AAAI 人工智能会议。

[44] Peng Wang, Shuai Bai, Sinan Tan, Shijie Wang, Zhihao Fan, Jinze Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, et al. Qwen2-vl: Enhancing vision-language model’s perception of the world at any resolution. arXiv preprint arXiv:2409.12191, 2024. 1, 6, 7, 8

中文题名及出版信息说明：Qwen2-VL：增强视觉语言模型在任意分辨率下感知世界的能力。

[45] Haoran Wei, Chenglong Liu, Jinyue Chen, Jia Wang, Lingyu Kong, Yanming Xu, Zheng Ge, Liang Zhao, Jianjian Sun, Yuang Peng, et al. General ocr theory: Towards ocr-2.0 via a unified end-to-end model. arXiv:2409.01704, 2024. 1, 2, 3, 6, 7, 8

中文题名及出版信息说明：通用 OCR 理论：通过统一端到端模型迈向 OCR-2.0。

[46] Haoran Wei, Lingyu Kong, Jinyue Chen, Liang Zhao, Zheng Ge, Jinrong Yang, Jianjian Sun, Chunrui Han, and Xiangyu Zhang. Vary: Scaling up the vision vocabulary for large vision-language model. In European Conference on Computer Vision, pages 408–424. Springer, 2025. 1, 3

中文题名及出版信息说明：Vary：扩展大型视觉语言模型的视觉词汇表。European Conference on Computer Vision：欧洲计算机视觉会议；Springer：施普林格。

[47] Renqiu Xia, Song Mao, Xiangchao Yan, Hongbin Zhou, Bo Zhang, Haoyang Peng, Jiahao Pi, Daocheng Fu, Wenjie Wu, Hancheng Ye, et al. Docgenome: An open large-scale scientific document benchmark for training and testing multi-modal large language models. arXiv preprint arXiv:2406.11633, 2024. 1

中文题名及出版信息说明：DocGenome：面向多模态大语言模型训练与测试的开放大规模科学文档基准。

[48] Renqiu Xia, Bo Zhang, Hancheng Ye, Xiangchao Yan, Qi Liu, Hongbin Zhou, Zijun Chen, Min Dou, Botian Shi, Junchi Yan, et al. Chartx & chartvlm: A versatile benchmark and foundation model for complicated chart reasoning. arXiv preprint arXiv:2402.12185, 2024. 1

中文题名及出版信息说明：ChartX 与 ChartVLM：用于复杂图表推理的通用基准和基础模型。

[49] Zhong Xu, Jianbin Tang, and Antonio Jimeno Yepes. Publaynet: largest dataset ever for document layout analysis. In 2019 International conference on document analysis and recognition, pages 1015–1022, 2019. 3

中文题名及出版信息说明：PubLayNet：迄今最大的文档版面分析数据集。2019 International Conference on Document Analysis and Recognition：2019 年国际文档分析与识别大会。

[50] Cong Yao. DocXChain: A Powerful Open-Source Toolchain for Document Parsing and Beyond. ArXiv, 2023. 7

中文题名及出版信息说明：DocXChain：用于文档解析及更多任务的强大开源工具链。

[51] Jianshu Zhang, Jun Du, and Lirong Dai. Multi-scale attention with dense encoder for handwritten mathematical expression recognition. In 2018 24th international conference on pattern recognition (ICPR), pages 2245–2250. IEEE, 2018. 2

中文题名及出版信息说明：采用密集编码器和多尺度注意力的手写数学表达式识别。2018 24th International Conference on Pattern Recognition（ICPR）：2018 年第 24 届国际模式识别大会。

[52] Qintong Zhang, Victor Shea-Jay Huang, Bin Wang, Junyuan Zhang, Zhengren Wang, Hao Liang, Shawn Wang, Matthieu Lin, Wentao Zhang, and Conghui He. Document parsing unveiled: Techniques, challenges, and prospects for structured information extraction. arXiv preprint arXiv:2410.21169, 2024. 1

中文题名及出版信息说明：揭开文档解析的面纱：结构化信息提取的技术、挑战与前景。

[53] Zhiyuan Zhao, Hengrui Kang, Bin Wang, and Conghui He. Doclayout-yolo: Enhancing document layout analysis through diverse synthetic data and global-to-local adaptive perception, 2024. 2, 7

中文题名及出版信息说明：DocLayout-YOLO：通过多样化合成数据和从全局到局部的自适应感知增强文档版面分析。

[54] Xu Zhong, Elaheh ShafieiBavani, and Antonio Jimeno Yepes. Image-based table recognition: data, model, and evaluation. In European conference on computer vision, pages 564–580, 2020. 1, 3, 6

中文题名及出版信息说明：基于图像的表格识别：数据、模型与评测。European Conference on Computer Vision：欧洲计算机视觉会议。

[55] Hongbin Zhou, Xiangchao Yan, and Bo Zhang. Structeqtable-deploy: A high-efficiency open-source toolkit for table-to-latex transformation. https://github.com/UniModal4Reasoning/StructEqTable-Deploy, 2024. 7, 8

中文题名及出版信息说明：StructEqTable-Deploy：用于表格到 LaTeX 转换的高效开源工具包。

## 补充材料

### OmniDocBench：通过全面标注评测多样化 PDF 文档解析——补充材料

### I. 更多端到端评测结果

表 S1 按表格属性分组，给出端到端表格评测结果。如表所示，多数模型在英文表格上的表现好于中文表格。多数模型在全边框与无边框表格上的表现相对较差。特殊情况会影响多数模型的准确性。合并单元格和公式主要检验模型可识别数据的广度，而彩色背景与表格旋转则检验其稳健性。结果表明，表格旋转显著影响所有模型的准确性。流水线工具的表现不会受到更具挑战性的表格（如合并单元格）的影响，但彩色背景会影响识别准确性。若干 VLM 在具有合并单元格的表格上表现更差，但彩色背景不会显著影响其表格识别准确性。

表 S2 按文本属性分组，展示端到端文本块评测结果。几乎所有模型的中文识别准确性均低于英文。部分模型，如 MinerU 和 Marker，在识别中英文混合内容时，准确性进一步降低。主要原因在于 MinerU 的文本识别模块使用 PaddleOCR。根据 PaddleOCR 在文本识别模块中的表现，混合语言会使其准确性下降。此外，复杂背景颜色会显著影响流水线工具的识别准确性，而对 VLM 准确性的影响很小。

**表 S1. 按表格属性分组的端到端表格 TEDS 结果。**EN／ZH／Mixed 分别为英文／中文／中英文混合；+/− 为有／无相应特殊情况。模型名 InterVL2-76B 保留原表拼写。

| 模型类型 | 模型 | 英文 | 中文 | 混合语言 | 全边框 | 省略线 | 三线表 | 无边框 | 合并单元格(+/−) | 公式(+/−) | 彩色背景(+/−) | 旋转(+/−) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 流水线工具 | MinerU | 75.1 | 59.3 | **79.1** | 59.4 | 71.6 | 69.7 | 60.0 | 63.6/65.3 | 66.0/64.4 | 59.2/67.5 | 3.0/65.8 |
| 流水线工具 | Marker | 64.9 | 47.3 | 49.8 | 44.5 | 61.8 | 59.0 | **63.6** | 52.6/52.7 | 53.2/52.5 | 48.0/54.9 | 35.5/52.9 |
| 流水线工具 | Mathpix | **75.4** | 63.2 | 71.3 | 67.4 | 77.3 | 66.3 | 25.5 | 70.3/65.4 | 68.7/66.7 | 59.7/70.8 | 19.2/67.9 |
| 专家视觉模型 | GOT-OCR | 51.7 | 46.2 | 49.0 | 45.5 | 48.3 | 51.3 | 46.2 | 46.0/48.9 | 45.7/48.4 | 39.8/51.9 | 0.0/48.7 |
| 专家视觉模型 | Nougat | 36.2 | 0.3 | 0.0 | 6.1 | 3.5 | 22.1 | 0.0 | 15.0/8.9 | 21/8.7 | 2.6/15.2 | 0.0/11.2 |
| 视觉语言模型 | GPT4o | 71.1 | 58.0 | 57.3 | 62.5 | 68.7 | 61.3 | 31.2 | 56.8/64.7 | 60.8/62.2 | 61.4/62.2 | 14.2/62.7 |
| 视觉语言模型 | Qwen2-VL-72B | 73.2 | **75.1** | 76.1 | **72.0** | **79.0** | **77.5** | 63.2 | 67.9/**78.1** | **71.6/75.3** | **77.9/72.9** | **42.7/75.1** |
| 视觉语言模型 | InterVL2-76B | 60.9 | 58.5 | 65.4 | 58.8 | 65.3 | 58.3 | 55.6 | 49.0/65.1 | 53.3/60.9 | 58.8/59.8 | 6.9/60.3 |

**表 S2. 按文本属性分组的端到端文本归一化编辑距离结果。**“Mixed”表示中英文混合；“Single”和“Multi”分别表示单色与多色。

| 模型类型 | 模型 | 英文 | 中文 | 混合语言 | 白色背景 | 单色背景 | 多色背景 |
|---|---|---|---|---|---|---|---|
| 流水线工具 | MinerU | **0.124** | **0.234** | 0.742 | **0.188** | **0.15** | 0.514 |
| 流水线工具 | Marker | 0.163 | 0.379 | 0.747 | 0.303 | 0.396 | 0.594 |
| 流水线工具 | Mathpix | 0.175 | 0.793 | 0.538 | 0.698 | 0.587 | 0.583 |
| 专家视觉模型 | GOT-OCR | 0.251 | 0.763 | 0.266 | 0.669 | 0.595 | 0.440 |
| 专家视觉模型 | Nougat | 0.587 | 0.991 | 0.983 | 0.874 | 0.935 | 0.972 |
| 视觉语言模型 | GPT4o | 0.170 | 0.647 | 0.322 | 0.536 | 0.423 | 0.406 |
| 视觉语言模型 | Qwen2-VL-72B | 0.128 | 0.582 | **0.209** | 0.494 | 0.388 | **0.217** |
| 视觉语言模型 | InternVL2-76B | 0.418 | 0.606 | 0.251 | 0.589 | 0.366 | 0.221 |

### II. 数据集统计与可视化

OmniDocBench 包含 981 个页面，涵盖 9 种 PDF 页面类型、4 种版面类型、3 种语言类型，以及水印等 3 种视觉退化特殊情况。表 S3 和图 S1 展示各页面属性对应的页面数量。图 S5 至图 S8 给出不同 PDF 类型、版面类型及特殊情况的页面示例。

表 S6 和图 S2 展示 OmniDocBench 包含的全部标注类别，均以边界框标注。块级标注共 15 类，片段级标注共 4 类，片段级标注嵌套在块级标注内。此外，还有 3 类标注被标记为页面干扰信息（编号 20–22），其边界框用于遮盖 PDF 页面中特定区域，以避免影响评测结果。除图像外，每个标注类别还提供识别标注。公式采用 LaTeX 格式，表格同时标注 HTML 和 LaTeX，其余采用纯文本。

此外，每个包含文本的块级类别还标注文本属性。可能影响 OCR 准确性的文本属性分为 3 类：语言、文本背景颜色和文本旋转。表 S5[原文如此]展示具有特定文本属性的标注统计。共有 23,010 条块级标注带有文本属性标签。

表格也具有表格属性标注。可能影响表格识别准确性的表格属性分为 6 类：语言、表格边框类型、合并单元格、彩色背景、包含公式以及旋转。表 S5 给出具有特定表格属性的标注数量。图 S9 和图 S10 展示不同边框和特殊情况下的表格示例。

**表 S3. OmniDocBench 页面属性统计。**

| 类别 | 属性名称 | 数量 |
|---|---|---|
| PDF 类型 | 书籍 | 104 |
| PDF 类型 | PPT 转 PDF | 133 |
| PDF 类型 | 研究报告 | 81 |
| PDF 类型 | 彩色教科书 | 96 |
| PDF 类型 | 试卷 | 114 |
| PDF 类型 | 杂志 | 97 |
| PDF 类型 | 学术文献 | 129 |
| PDF 类型 | 笔记 | 116 |
| PDF 类型 | 报纸 | 111 |
| 版面类型 | 单栏 | 477 |
| 版面类型 | 双栏 | 126 |
| 版面类型 | 三栏 | 45 |
| 版面类型 | 单栏与多栏混合 | 120 |
| 版面类型 | 复杂版面 | 213 |
| 语言 | 英文 | 290 |
| 语言 | 简体中文 | 612 |
| 语言 | 混合语言 | 79 |
| 特殊情况 | 模糊扫描 | 28 |
| 特殊情况 | 水印 | 65 |
| 特殊情况 | 彩色背景 | 246 |

**表 S4. OmniDocBench 文本属性统计。**

| 属性类别 | 类别名称 | 数量 |
|---|---|---|
| 语言 | 英文 | 5857 |
| 语言 | 简体中文 | 16073 |
| 语言 | 中英文混合 | 1080 |
| 文本背景 | 白色 | 19465 |
| 文本背景 | 单色 | 1116 |
| 文本背景 | 多色 | 2429 |
| 文本旋转 | 正常 | 22865 |
| 文本旋转 | 旋转90° | 14 |
| 文本旋转 | 旋转270° | 58 |
| 文本旋转 | 横向（Horizontal） | 421 |

**表 S5. OmniDocBench 表格属性统计。**

| 属性类别 | 类别名称 | 数量 |
|---|---|---|
| 语言 | 英文 | 128 |
| 语言 | 简体中文 | 285 |
| 语言 | 中英文混合 | 15 |
| 表格边框类型 | 全边框 | 205 |
| 表格边框类型 | 省略线 | 62 |
| 表格边框类型 | 三线表 | 147 |
| 表格边框类型 | 无边框 | 14 |
| 特殊情况 | 合并单元格 | 150 |
| 特殊情况 | 彩色背景 | 142 |
| 特殊情况 | 包含公式 | 81 |
| 特殊情况 | 旋转 | 7 |

**表 S6. 标注说明与统计。**

| 编号 | 类别名称 | 说明 | 总数 |
|---|---|---|---|
| 1 | 标题（Title） | 包括主标题、章节标题等。 | 2972 |
| 2 | 文本块（Text Block） | 文本段落，在 Markdown 中通常用双换行分隔。 | 15979 |
| 3 | 图像（Figure） | 包括图片、可视化图表等。 | 989 |
| 4 | 图注（Figure Caption） | 通常以“Figure”加编号开头，或仅为图像下方的描述性语言。 | 651 |
| 5 | 图像脚注（Figure Footnotes） | 图注之外的描述性语言，通常以星号（*）开头。 | 133 |
| 6 | 表格（Table） | 以表格形式组织的内容，通常具有边框或清晰的表格结构。 | 428 |
| 7 | 表注（Table Caption） | 通常以“Table”加编号开头，或仅为表格上方的描述性语言。 | 299 |
| 8 | 表格脚注（Table Footnotes） | 表注之外的描述性语言，通常以星号（*）开头。 | 132 |
| 9 | 页眉（Header） | 位于 PDF 页面顶部或侧边栏、与主体内容分离的信息，通常包括章节名称等细节。 | 1271 |
| 10 | 页脚（Footer） | 位于 PDF 页面底部、与主体内容分离的信息，通常包括出版者名称等细节。 | 541 |
| 11 | 页码（Page Number） | 通常以数字表示，可位于页面顶部、侧边栏或底部。 | 669 |
| 12 | 页面脚注（Page Footnote） | 进一步解释页面内容中标记的脚注，例如作者机构信息。 | 92 |
| 13 | 代码块（Code Block） | 在 Markdown 中，代码块通常以三个反引号定义。 | 13 |
| 14 | 代码块说明（Code Block Caption） | 位于代码块上方的描述性语言。 | / |
| 15 | 参考文献（Reference） | 通常只出现在学术文献中。 | 260 |
| 16 | 文本片段（Text Span） | 片段级文本框，包含可直接以 Markdown 格式书写的纯文本内容。 | 73143 |
| 17 | 行内公式（Equation Inline） | 需要用 LaTeX 格式表示并嵌入文本的公式。 | 4009 |
| 18 | 忽略公式（Equation Ignore） | 无需 LaTeX 格式也能正确显示的某些公式，例如 15 kg。 | 3685 |
| 19 | 脚注标记（Footnote Mark） | 通常以上标或下标形式嵌入文本，其编号通常与页面脚注对应。 | 357 |
| 20 | 其他舍弃类别（Other Abandoned Categories） | （遮盖）无法分类且与页面无关的信息，例如小图标等。 | 538 |
| 21 | 遮盖文本块（Masked Text Block） | （遮盖）难以识别且干扰文本流的信息，例如汉字上方的拼音注释。 | 34 |
| 22 | 有机化学式（Organic Chemical Formula） | （遮盖）难以用 Markdown 书写且易被识别为图像的有机化学式。 | 24 |

### III. 模型预测结果讨论

**结论。**综合各任务和子属性下分散的结果，可以得出：与 VLM 相比，流水线工具和专家模型在学术论文等常见数据，以及具有合并单元格的表格等困难情况中表现更好。然而，VLM 在幻灯片和试卷等不常见的 PDF 类型上表现出更强泛化能力，对模糊扫描等特殊页面情况也更加稳健。VLM 准确性低主要源于：1）密集页面中的内容缺失（图 S11）；2）难以识别的页面中的幻觉（图 S30）。流水线工具准确性低主要源于：1）对水印等特殊页面情况的稳健性较弱（图 S21）；2）对手写笔记等不常见 PDF 类型的泛化较弱（图 S16）。

图 S11 至图 S19 展示不同 PDF 类型下文档解析模型的良好与不佳输出示例。如图所示，不同模型在不同 PDF 类型上的表现不同。例如，MinerU 将全部手写笔记检测为图像，导致笔记识别准确性极低。Marker 和 InternVL2 存在漏检，导致得分较低。InternVL2 和 Qwen2-VL 在幻灯片、财务报告等特定 PDF 类型中，倾向于合并多栏文本。

图 S20 至图 S22 展示 PDF 页面存在特殊问题时模型输出的好坏示例。对于模糊扫描或带水印的 PDF 页面，Marker 容易生成错字，而 GOT-OCR 无法识别彩色背景页面上的内容。MinerU 在特殊情况下表现良好，而 Mathpix 偶尔产生错字。

图 S23 至图 S26 展示不同版面 PDF 页面上的模型输出好坏示例。MinerU 在单栏版面上的阅读顺序得分较低，主要因为大部分笔记都是单栏，而 MinerU 对笔记识别不佳，从而导致阅读顺序得分较低。InternVL2 在单栏版面上得分高，但在双栏、三栏版面上较差，主要原因是多栏页面中经常出现内容漏识别和阅读顺序判断错误。MinerU 在复杂版面中的阅读顺序与识别准确性下降，主要因为识别过程中错误地合并了多栏内容。

图 S29 和图 S30 展示特殊文本条件下的模型识别能力。面对复杂背景颜色的文本，Marker 可能出错或遗漏内容，而 Qwen2-VL 仍表现良好。文本旋转 270°时，多数模型无法识别。某些视觉语言模型会基于能够识别的内容生成幻觉信息。

图 S31 至图 S34 展示不同属性表格的良好与不佳模型结果。对于三线表，RapidTable 表现良好，能准确识别结构，而 PaddleOCR 的局限在于输出中遗漏了最后一列。有趣的是，在无边框表格中，PaddleOCR 能准确预测表格，表现良好，而 Qwen2-VL-7B 在最后两列出现错误。这说明边框的存在与否可能以不同方式显著影响各模型。旋转表格尤其困难，包括 GOT-OCR 在内的大多数模型都无法识别其结构。然而，StructEqTable 展现出有希望的结果，正确识别大部分表格内容，仅有少量细节错误。对于含公式的表格，Qwen2-VL-7B 的结构识别比 InternVL2-8B 更准确。

### IV. 模型设置

MinerU、Marker 和 Mathpix 等流水线工具使用默认设置评测。具体而言，MinerU 使用 0.9.3 版本⁸，Marker 评测 1.2.3 版本⁹。Nougat 使用 0.1.0-base 模型（350M）。GOT-OCR 采用 format OCR 模式输出结构化数据。

对于通用 VLM，使用 GPT4o、Qwen2-VL-72B 和 InternVL2-Llama3-76B，并设置 `do_sample=False` 以确保可复现性。测试不同 `max_token` 设置后，为各 VLM 选择最佳设置。具体而言，Qwen2-VL-72B 设为 `max_token=32000`，InternVL2-Llama3-76B 设为 `max_token=4096`，GPT-4o 使用默认设置。

⁸ https://github.com/opendatalab/MinerU/releases/tag/magic_pdf-0.9.3-released

⁹ https://github.com/VikParuchuri/marker/releases/tag/v1.2.3

### V. 方法的更多细节

**忽略处理。**此过程旨在避免文档解析算法输出规范不统一造成准确性波动。（1）部分算法，如 GPT-OCR[原文如此]、Qwen2-VL，倾向于移除页眉和页脚，而另一些算法，如 GPT4o，更倾向于保留它们（图 S3）。（2）此外，还考虑图注和脚注造成的阅读顺序不匹配。例如，Nougat 将图注放在页面内容末尾（图 S4），而其他方法倾向于按人类阅读顺序放置图注。

忽略处理旨在尽量减少文档解析规范差异对评测的影响。我们的评测数据集希望更加公平地评估各种算法的解析准确性，这些涉及规范的细枝末节不在我们的考虑范围之内。

**图 S1.** OmniDocBench 中各属性对应的页面数据比例。

**图 S2.** OmniDocBench 中各种标注的可视化。

**图 S3.** 解析页眉、页脚等内容时的不同规范。

**图 S4.** 解析图注时的不同规范。

**图 S5.** OmniDocBench 中学术论文、书籍、教科书、笔记与杂志的示例。

**图 S6.** OmniDocBench 中财务报告、报纸、示例试卷及幻灯片的示例。

**图 S7.** OmniDocBench 中不同版面类型的 PDF 页面示例。

**图 S8.** OmniDocBench 中存在特殊情况的 PDF 页面示例。

**图 S9.** OmniDocBench 中不同边框的表格示例。

**图 S10.** OmniDocBench 中存在特殊情况的表格示例。

**图 S11.** 学术论文上的良好模型结果与不佳模型结果。

**图 S12.** 书籍上的良好模型结果与不佳模型结果。

**图 S13.** 试卷上的良好模型结果与不佳模型结果。

**图 S14.** 杂志上的良好模型结果与不佳模型结果。

**图 S15.** 报纸上的良好模型结果与不佳模型结果。

**图 S16.** 手写笔记上的良好模型结果与不佳模型结果。

**图 S17.** 财务报告上的良好模型结果与不佳模型结果。

**图 S18.** 幻灯片上的良好模型结果与不佳模型结果。

**图 S19.** 教科书上的良好模型结果与不佳模型结果。

**图 S20.** 模糊扫描页面上的良好模型结果与不佳模型结果。

**图 S21.** 带水印页面上的良好模型结果与不佳模型结果。

**图 S22.** 彩色背景页面上的良好模型结果与不佳模型结果。

**图 S23.** 单栏页面上的良好模型结果与不佳模型结果。

**图 S24.** 双栏页面上的良好模型结果与不佳模型结果。

**图 S25.** 三栏页面上的良好模型结果与不佳模型结果。

**图 S26.** 复杂版面页面上的良好模型结果与不佳模型结果。

**图 S27.** 中文文本上的良好模型结果与不佳模型结果。

**图 S28.** 英文文本上的良好模型结果与不佳模型结果。

**图 S29.** 彩色背景文本上的良好模型结果与不佳模型结果。

**图 S30.** 旋转文本上的不佳模型结果。

**图 S31.** 三线表上的良好模型结果与不佳模型结果。

**图 S32.** 无边框表格上的良好模型结果与不佳模型结果。

**图 S33.** 旋转表格上的良好模型结果与不佳模型结果。

**图 S34.** 含公式表格上的良好模型结果与不佳模型结果。
