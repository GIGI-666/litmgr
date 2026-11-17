# HG-Bench：面向自动作业评估的多页手写答案区域定位基准

HG-Bench: A Benchmark for Multi-Page Handwritten Answer-Region Grounding in Automated Homework Assessment

## 论文正文

作者：Chuangxin Zhao¹、Boyan Shi³、Yanling Wang⁴、Yijian Lu²、Canran Xiao⁵、Jiali Chen⁶、Jun Xia¹、Yan Wang²、Ji Qi²˒\*、Juanzi Li²˒\*

¹ 香港科技大学（广州）（The Hong Kong University of Science and Technology (Guangzhou)）

² 清华大学（Tsinghua University）

³ 北京交通大学（Beijing Jiaotong University）

⁴ 独立研究者（Independent Researcher）

⁵ 中山大学深圳校区（Shenzhen Campus of Sun Yat-sen University）

⁶ 香港理工大学（The Hong Kong Polytechnic University）

通讯联系：Ji Qi（qiji@tsinghua.edu.cn）和 Juanzi Li（lijuanzi@tsinghua.edu.cn）

项目主页：https://hg-bench.github.io

载于 Proceedings of the 2026 Conference on Empirical Methods in Natural Language Processing（2026 年自然语言处理实证方法会议论文集），第 54888–54904 页。2026 年 10 月 24–29 日，©2026 Association for Computational Linguistics（计算语言学协会）。

### 摘要

自动作业评估不仅需要识别学生答案，还需要在带噪声的多页手写作业中，准确定位完整答案和中间推理步骤。我们针对当前缺失的评估设置——具备页面感知能力的两级答案区域定位（page-aware, two-level answer-region grounding）——展开研究：给定作业页面图像，模型必须定位完整答案区域及其有序的步骤级子区域。我们提出 HG-Bench，它包含从 1,489,278 张图像的源池中筛选出的 500 个人工标注的 K–12 作业样本，并提供按层级关联的题目级和步骤级边界框。其页面感知协议分别衡量完整答案定位（$\mathcal{F}_A$）和步骤级分解（$\mathcal{F}_S^{\mu}$），将结构化空间定位与可见文本解析区分开来。在前沿闭源和开放权重视觉语言模型（vision–language models，VLMs）中，没有任何零样本系统的 $\mathcal{F}_A$ 超过 55.22%，或 $\mathcal{F}_S^{\mu}$ 超过 48.22%；而在约 10k 个领域内示例上微调的 GLM-4.6V 9B 参考模型达到 74.97/72.26。这些结果揭示出步骤级手写区域定位这一具体能力缺口，并为未来自动作业评估研究提供可复现的基准、评估协议和经过训练的参考系统。

### 1 引言

自动作业评估正越来越多地部署于教育场景，以减轻教师工作量并提高评分一致性。每个此类流程的第一阶段都是空间定位：系统必须识别每张扫描页面上学生书写各个答案的位置；对于多步骤题目，还要识别推导中每个组成步骤的位置。下游光学字符识别、评分和反馈模块以这些区域为输入，因此最终评分准确率的上限受上游定位准确率制约。

**图 1：HG-Bench 概览。** HG-Bench 以多页手写作业图像序列为输入，要求模型输出具备页面感知能力的两级定位结果：每道题的完整答案区域，以及多步骤解答中有序的步骤级边界框。这一设置检验 VLM 能否定位学生推理的空间结构，而不仅仅是识别最终答案。

**研究空白。** 尽管自然图像中的指代表达定位（referring-expression grounding）（Kazemzadeh et al., 2014; Plummer et al., 2015）和文档理解（Mathew et al., 2021; Masry et al., 2022; Mathew et al., 2022）取得了快速进展，但目前没有公开基准衡量真实学生手写作业上的区域定位。自然图像基准在编辑选用的照片中，为每个查询评估一个指代对象；文档 AI 基准恢复文本内容，却不要求空间上正确、层级结构化的区域输出。MathVista（Lu et al., 2024）和 MathVerse（Zhang et al., 2024）等教育 AI 基准，在假定相关内容已经被识别的情况下评估解题能力。与实际评估流程最相关的能力——在带噪声的多页手写扫描件上进行有序、两级、页面感知的定位——仍未得到衡量。

**核心挑战。** 真实作业扫描件在四个方面同时显著难于以往所有定位基准的输入：（i）具有页面感知坐标语义的多页样本；（ii）行间距不规则、存在手部阴影和透视倾斜、且笔画风格因学生而异的手写内容；（iii）两级结构，既要求每题答案区域，也要求满足层级包含关系的有序步骤子区域；（iv）跨学科的长尾版面异质性，例如数学中的分式推导和矩阵，与语言学科中的密集段落。若基准未体现其中任何一个方面，就会高估当前 VLM 对作业评估部署的准备程度。

**我们的方法。** 我们通过两项协同成果填补这一空白。第一项是 HG-Bench：一个经筛选、分层、人工标注的测试集，包含覆盖上述四类挑战的 500 个多页样本，并配备将题目级定位（$\mathcal{F}_A$）与步骤级分解（$\mathcal{F}_S^{\mu}$）解耦的页面感知评估协议。第二项是轻量级参考微调系统：在约 10k 个领域内示例上，对一个开放权重的 9B VLM 进行单阶段监督微调（supervised fine-tuning，SFT）。它作为经过训练的参考点，而非最先进（state-of-the-art，SOTA）参评系统，用于验证该基准具有可学习性，并量化专用流程性能的一个下界。

**关键实证发现。** 我们观察到不同范式间显著的排名反转（表 2）：闭源模型的最佳 $\mathcal{F}_A$ 为 55.22%（Doubao-Seed-2.0-Pro，评估日期为 2026-04-01），最佳 $\mathcal{F}_S^{\mu}$ 为 48.22%（Gemini-3-Pro-Preview）。参考 SFT 系统达到 74.97/72.26。最显著的差距出现在 $\mathcal{F}_S^{\mu}$ 上，绝对提升为 24.04，证实步骤级结构化定位，而非粗粒度答案区域检测，是 HG-Bench 所衡量的核心能力。关键在于，扩大规模不能弥合这一差距：参数量为 397B 的 Qwen3.5-397B-A17B（Qwen Team, 2026）仅取得 42.71/18.15，低于若干更小的闭源 API。

**贡献。**

- HG-Bench 是首个面向多页手写 K–12 作业、进行两级页面感知答案区域定位的基准，包含从约 1.49M 张图像的源池中筛选出的 500 个人工标注样本。
- 页面感知评估协议将题目级宏观指标 $\mathcal{F}_A$，与仅在含步骤页面上计算的步骤级微观指标 $\mathcal{F}_S^{\mu}$ 解耦，校正不同样本之间多步骤题目的结构性不平衡。
- 对九个前沿视觉语言系统进行系统评估，包括闭源 API（GPT-5.4、Claude-Sonnet-4.6、Doubao-Seed-2.0-Pro、Gemini-3-Pro-Preview）和开放权重模型（Qwen3.5-397B-A17B、GLM-5V-Turbo、Kimi-K2.5、GLM-4.6V 9B）（OpenAI, 2026; Anthropic, 2026; ByteDance Seed Team, 2026; Google, 2025; Qwen Team, 2026; GLM-V Team, 2026; Kimi Team, 2026; GLM-V Team, 2025），确立了步骤级定位是主要能力缺口，单靠参数量无法解决它。
- 在约 10k 个领域内示例上，对 GLM-4.6V 9B 进行单阶段 SFT 得到参考微调系统，无需强化学习阶段即可超过所有受评闭源基线。我们发布该检查点，作为未来 HG-Bench 提交结果的性能下界参考。

### 2 相关工作

**视觉定位。** 指代表达定位使用自然图像数据集进行基准评估，包括 RefCOCO（Kazemzadeh et al., 2014; Yu et al., 2016; Mao et al., 2016）、Flickr30K Entities（Plummer et al., 2015）和 Visual Genome（Krishna et al., 2017）。这些基准主要将每个查询与自然图像中的单个指代对象配对。GLIP（Li et al., 2022a）和 Grounding-DINO（Liu et al., 2024a）等检测导向系统提升了定位能力，而 Shikra（Chen et al., 2023）和 Ferret（You et al., 2024）将指代融入多模态对话。相关任务拓展了查询和输出空间：TOIST 将动作可供性映射为实例掩码（Li et al., 2022b），Touch-Line Transformer 将语言与手势几何结合（Li et al., 2023a），图形用户界面（GUI）研究则将元素定位与下游动作联系起来（Li et al., 2026）。密集预测涵盖语言引导的表述方式（Yao et al., 2026a）和显著性感知的开放词汇分割（Yao et al., 2026b）。扩展研究还将定位与跨视频流程（Ye et al., 2026）、证据锚定注意力（Hu et al., 2026）、偏好优化的空间推理（Shen et al., 2025）及组合式三维理解（Yu et al., 2025a）相结合。机制分析研究 VLM 的定位与幻觉回路（Liu et al., 2026a），以及共享的解码时决策子空间（Shao et al., 2026）；结构感知分割（Zhang et al., 2026a）和与人类判断对齐的版面评估（Lu et al., 2025）则强调空间组织。HG-Bench 的不同之处在于，它要求在手写扫描件上输出具备页面感知能力、具有层级关系的题目区域与有序步骤区域。

**近期 VLM 的定位能力。** GPT-4V/4o（OpenAI, 2023）、Gemini（Gemini Team et al., 2023）、Claude（Anthropic, 2024）、Doubao（ByteDance Seed Team, 2025）和 Kimi（Kimi Team, 2026）等闭源 VLM 支持生成边界框；开放权重模型家族也支持这一能力，包括 Qwen-VL/Qwen2.5-VL（Wang et al., 2024a; Bai et al., 2025）、InternVL/InternVL2.5（Chen et al., 2024a,b）、CogVLM2（Wang et al., 2024b）、MiniCPM-V（Yao et al., 2024）、Florence-2（Xiao et al., 2024）、LLaVA-NeXT（Liu et al., 2024b）、DeepSeek-VL2（Wu et al., 2024）、Phi-3-Vision（Abdin et al., 2024）和 GLM-V（GLM-V Team, 2025）。这些系统从 CLIP（Radford et al., 2021）和 ALIGN（Jia et al., 2021）等骨干网络继承视觉语言先验；混合专家（Mixture-of-Experts，MoE）稀疏性进一步扩展了开放权重模型的容量（Shazeer et al., 2017; Fedus et al., 2022; Jiang et al., 2024; Dai et al., 2024），但其本身并不能确保细粒度定位。相邻的视觉语言动作研究考察信息性帧选择、通才与专家适应（Yu et al., 2026a,b），以及面向长时程交互、具备进度感知能力的可供性推理（Liu et al., 2026b）。跨模态异步融合则将模态特定表征学习与语义交互分离（Zhang et al., 2026b）。尽管取得了这些进展，但上述系统尚未在手写 K–12 作业的页面感知、层级定位上接受系统评估，也没有系统解决 HG-Bench。

**教育 AI 基准与基准方法论。** 数学与科学基准——MathVista（Lu et al., 2024）、MathVerse（Zhang et al., 2024）、We-Math（Qiao et al., 2024）、MATH-Vision（Wang et al., 2024c）、MathSpatial（Lu et al., 2026）和 OlympiadBench（He et al., 2024）——在相关视觉内容已被识别后衡量推理能力。MMBench（Liu et al., 2024c）、SEED-Bench（Li et al., 2023b）、MMMU（Yue et al., 2024）、Video-MME-Logical（Kwan et al., 2026）、HELM（Liang et al., 2023）和 BIG-Bench（Srivastava et al., 2023）等更广泛的评测套件旨在覆盖通用能力，而带引用的检索增强生成（cited-RAG）诊断则检验检索证据是否足以支持某项主张（Qian et al., 2026）。这两类评测都不衡量手写答案的区域级定位；此外，这一领域也很少报告使用 Cohen’s $\kappa$（Cohen, 1960）或 Fleiss’ $\kappa$（Fleiss, 1971）衡量的标注者间一致性。

### 3 任务形式化

**问题定义。** 该任务旨在评估模型准确定位学生手写答案的能力，同时覆盖题目级与步骤级；这对多页手写作业的自动评分和推理轨迹分析至关重要。

**输入与输出。** 系统输入是有序作业页面图像序列 $\{\mathbf{I}_p\}_{p=1}^{P}$，以及指定每页像素尺寸的元数据。期望输出为 JSON 数组 $\{q_i\}_{i=1}^{N}$，其中每个元素 $q_i$ 对应一道题，并包含：

- 固定的类型字段 `complete_answer_box`；
- 页面索引 $p_i\in\{1,\ldots,P\}$；
- 题目级边界框 $\mathbf{b}_i\in[0,1000]^4$，采用 `xyxy` 格式，包围该题完整的手写答案；
- 可选的有序步骤框列表 $\{s_{i,j}\}_{j=1}^{K_i}$，每个步骤包含 `step_id`，按学生书写顺序从 1 开始编号，并具有自己的边界框 $\mathbf{b}_{i,j}$。

所有题目框与步骤框必须按照学生作答顺序输出。

**两级边界框语义。** 题目级边界框在标注工具中有时称为“标题框”，用于定位每题完整的手写答案区域，支持逐题评分和部分分值归因。步骤级边界框进一步将多步骤解答和多空填答分解为有序子区域，支持步骤级评分和推理轨迹分析。每个 $\mathbf{b}_{i,j}$ 必须完全包含于其父框 $\mathbf{b}_i$ 内，从而强制维持层级一致性。当某个区域部分缺失或含糊不清时，模型应预测最佳适配的边界框，同时保留这一包含规则。

**坐标约定。** 默认将坐标归一化为 $[0,1000]$ 的 `xyxy` 格式，并可使用逐页元数据将其反归一化为像素值。协议也可通过配置支持 `yxyx` 和像素坐标变体。对于输出多边形的模型，使用其最小外包轴对齐矩形进行评估。所有坐标必须紧密包围学生手写内容，排除印刷文字和教师批注。

**图 2：HG-Bench 数据引擎。** 该流程包含四个阶段。**（I）采集。** 从两个互补渠道收集 1,489,278 张匿名化作业图像：企业 B2B 答题纸扫描件，以及面向公众的消费级作业拍照应用中的用户照片，从而同时覆盖受控采集与真实场景分布。**（II）过滤。** 按可用性（损坏、空白、无法辨认）、是否不存在教师批改标记，以及是否包含学生答案内容来过滤图像；多阶段自动检查后进行人工核验。**（III）分层标注。** 使用两级画框协议（题目级＋有序步骤级）标注 10,420 个样本，严格遵守层级包含关系；标注者使用支持键盘快捷键画框的定制工具。**（IV）核验与分层划分。** 每个样本至少审核一次；存在歧义的条目交由主标注者处理。按学科、年级、页数与答案类型对标注池进行分层，得到 500 个样本的测试划分（HG-Bench）和 9,920 个样本的训练池（HG-SFT），后者由第 6.2 节的参考系统使用。

### 4 HG-Bench

#### 4.1 源池

HG-Bench 来源于一个大型匿名化学生作业图像池，包含 1,489,278 张图像，涵盖真实在线作业扫描件和墨水屏采集图像，跨越多个学科与年级。我们从该原始池中筛选出由 10,420 个有效样本构成的高质量标注集，来源于两个具有代表性的采集渠道：

- **企业渠道（6,765 个样本）**：来自正式答题纸和标准化考试阅卷，以多页样本及较高比例的多步骤题目为特征；
- **消费渠道（3,655 个样本）**：来自面向公众的消费级作业拍照应用中普通用户上传的作业照片，通常为单页图像，题型分布更均衡，具有真实场景的拍摄变化。

随后将标注池划分为 500 个样本的保留测试集（HG-Bench）和 9,920 个样本的训练池（HG-SFT），每个渠道各保留 250 个样本。测试池与训练池在构建时即互不重叠；我们还使用感知哈希额外验证二者的不相交性（第 6.2 节）。所有能够识别个人身份的信息，在样本纳入任一数据池之前均已移除。

#### 4.2 采样策略

为保证该基准能够代表真实作业，我们沿四个维度进行分层采样：学科、年级、每个样本的页数，以及答案类型。该过程产生 500 个基准样本，旨在捕获实际中遇到的长尾版面与题目复杂性。各层的详细数量见表 1 和图 3。

#### 4.3 标注协议

标注协议明确了应跳过哪些页面，并规定绘制两级边界框的流程。

**跳过规则。** 当满足以下任一条件时，跳过该页：（i）图像不可用，存在损坏、空白或无法辨认的情况；（ii）存在教师批改标记，例如 ✓、×、书写分数等；（iii）全部学生答案均为非常规内容，例如绘画、涂鸦或偏离任务的内容。含有与评分无关的红笔标记的页面予以保留，并正常标注。

**画框。** 每个学生手写区域由一个轴对齐边界框包围。单答案题目获得一个题目级框。多步骤解答和多空填答另外获得一组有序步骤级框，每个框紧密包围一个步骤的手写内容，且绝不将同一行手写内容拆分到多个框内。不为非正式草稿画框。

**标签。** 每个框携带局部题号与父级题号层次，使用“/”分隔。题型从固定集合中选取：选择（choice）、填空（fill）、判断（judgment）、解答（solve，含计算）、绘图（drawing）、简答（short-answer）、写作（writing）。步骤 ID 是按学生书写顺序分配的整数。标签中的所有标点均遵循中文排版规范。

#### 4.4 标注工作流程

标注遵循两阶段协议。12 名受训标注者使用基于快捷键的定制工具绘制题目框和步骤框，5 名高级审核者独立决定接受每条标注，或退回修改；存在歧义的情况交由主标注者处理。我们在质检修订前，对从测试集中随机抽取的 50 个样本进行标注者间一致性（inter-annotator agreement，IAA）测量，每个样本由两名独立标注者标注。在定位方面，标注的平均交并比（Intersection-over-Union，IoU）为 0.86，85% 的边界框在 $\mathrm{IoU}=0.5$ 时能够匹配，二元框匹配一致性的 Cohen’s $\kappa=0.83$。对于离散标注，即题型、步骤包含关系和步骤顺序，Fleiss’ $\kappa$ 为 0.81。这些结果表明一致性较强（Cohen, 1960; Fleiss, 1971），支持 HG-Bench 的可靠性。

**图 3：HG-Bench 的组成。** （a）企业和消费渠道中，每个样本的答案数均呈长尾分布。（b）企业渠道的多步骤题目占比更高，与正式考试场景一致。（c）每个样本的页数：企业样本主要为多页，消费样本主要为单页。（d）题型组成：企业渠道以填空题为主，消费渠道则在选择、填空、解答和简答题之间分布更均衡。500 个样本的基准沿这四个维度分层，以保持对两个渠道的代表性。

**表 1：HG-Bench 汇总统计。**

| 统计项 | 数值 |
|---|---:|
| 样本数 | 500 |
| 学科数 | 5 |
| 每个样本平均页数 | 1.8 |
| 每页平均题目框数 | 5.2 |
| 每题平均步骤框数（存在步骤时） | 2.9 |
| 含步骤页面比例 | 0.34 |

#### 4.5 数据集统计

图 3 和表 1 汇总了标注池与 HG-Bench 测试集。数据反映了真实作业场景：两个渠道的答案数量均呈长尾分布，而企业样本包含更多多步骤题目、多页提交和填空题。消费样本主要为单页，选择、填空、解答和简答题之间更均衡。500 个 HG-Bench 样本通过分层保留这些模式，使基准在题目级与步骤级定位方面都兼具代表性和挑战性。

### 5 评估协议

#### 5.1 页面感知边界框匹配

不同于将整份文档中的所有边界框展平处理的标准定位任务，我们的评估严格在页面级进行，以保留多页版面结构。

在每页内部，我们在 IoU 约束下，对真值框 $\mathcal{G}$ 和预测框 $\mathcal{P}$ 进行贪心一对一匹配。具体而言，过滤所有满足 $\mathrm{IoU}(g,p)<0.5$ 的候选框对 $(g,p)\in\mathcal{G}\times\mathcal{P}$。将剩余框对按 IoU 降序排序，再进行贪心分配，使每个框最多参与一次匹配。该局部匹配产生每页的真阳性（true-positive，TP）、假阳性（false-positive，FP）与假阴性（false-negative，FN）数量。

#### 5.2 报告指标

在页面级匹配后，将性能聚合为两个主要的数据集级定位指标；我们另外报告附录 D 中定义的四个补充指标，用于描述步骤分解鲁棒性（$\mathcal{F}_S^M$）与解析时可靠性（$\mathrm{Succ}\%$、$\bar{\mathcal{S}}$、$\mathrm{Rep}\%$）。

- **答案区域 $F_1$（$\mathcal{F}_A$）。** 该指标评估题目级答案区域的定位质量。根据每页局部的 TP、FP 和 FN 数量计算标准 $F_1$ 分数，在每个多页样本内部取平均，并报告所有成功评估样本上的宏平均：

$$
\mathcal{F}_A=\frac{1}{|\mathcal{S}_{\mathrm{succ}}|}\sum_{s\in\mathcal{S}_{\mathrm{succ}}}\left(\frac{1}{|\mathcal{M}_s|}\sum_{m\in\mathcal{M}_s}F_1(s,m)\right)\times100. \tag{1}
$$

其中，$\mathcal{S}_{\mathrm{succ}}$ 是成功评估样本集合，$\mathcal{M}_s$ 是样本 $s$ 的页面集合，$F_1(s,m)$ 是样本 $s$ 第 $m$ 页的框级 $F_1$。

- **步骤级微平均 $F_1$（$\mathcal{F}_S^{\mu}$）。** 与每页都存在的题目级答案区域不同，步骤级框呈现高度稀疏且不平衡的分布：许多页面完全不包含步骤。为消除这种不平衡造成的评估偏差，$\mathcal{F}_S^{\mu}$ 通过仅限于含步骤页面的微聚合来计算。我们在真值至少包含一个步骤框的所有页面上，全局累计步骤级 TP、FP 和 FN 数量，计算单一、统一的 $F_1$ 分数。

### 6 基准评估与实验分析

所有基线 VLM 使用相同的提示词模板（附录 C），固定 JSON 模式、归一化的 $[0,1000]$ 坐标，以及具备页面感知、保留序列顺序的输出格式。我们使用格式容错的 JSON 解析器解析输出，并在结构性失败后发出一次格式提醒以重试；持续失败的输出标记为 `FAIL_STR`（`success = False`）。由于模型的坐标约定不同，我们在评估前，使用一小部分独立保留的校准数据，自动检测每个模型的框坐标轴顺序。

#### 6.1 受评基线

我们评估两组前沿视觉语言系统：

- **闭源前沿 API。** GPT-5.4（OpenAI, 2026）、Claude-Sonnet-4.6（Anthropic, 2026）、Doubao-Seed-2.0-Pro（ByteDance Seed Team, 2026）（官方 260215 发布版，以及 2026-04-01 的一次后续评估）和 Gemini-3-Pro-Preview（Google, 2025），均通过各自官方端点、采用默认解码设置调用。
- **开放权重基线。** Qwen3.5-397B-A17B（Qwen Team, 2026）（每个 token 激活 17B 参数的 MoE 模型）、GLM-5V-Turbo（GLM-V Team, 2026）、Kimi K2.5（Kimi Team, 2026）以及 GLM-4.6V 9B 基座（GLM-V Team, 2025）。

我们另外报告 GLM-4.6V-9B + HG-SFT，这是在 HG-SFT 池上训练的参考微调系统。该模型作为经过训练的参考点，而非零样本基线，使我们能够检验 HG-Bench 是否可以通过适量领域内监督来学习。

#### 6.2 参考 SFT 系统

为验证可学习性，并提供可复现的性能下界参考，我们使用单阶段 SFT，在包含 9,920 个样本的 HG-SFT 训练池上微调 GLM-4.6V 9B。结构化智能体蒸馏通过分离推理段与动作段，在更小模型中保留结构化智能体行为（Liu et al., 2026c）。在另一个结构化预测领域，反向蒸馏微调将分解后的推理轨迹内化，以实现可解释的 Text-to-SQL（Guan et al., 2026）；我们的参考系统则直接监督具有层级关系的题目级和步骤级区域，不包含教师–学生蒸馏阶段。训练不使用强化学习、合成持续预训练或领域外数据混合，因此相较零样本基线的改进可归因于有针对性的领域内监督，而非更强的基础模型或额外训练阶段。基座检查点、训练–测试去重、数据组成和优化方案的完整细节见附录 B。

**表 2：HG-Bench 上的主要结果。** 每个模型均评估 $N=500$ 个样本。$\mathcal{F}_A$：跨样本和页面取平均的答案区域宏平均 $F_1$；$\mathcal{F}_S^{\mu}$：在含步骤页面上聚合的步骤级微平均 $F_1$；$\mathcal{F}_S^M$：在含步骤样本上取平均的步骤级宏平均 $F_1$（附录 D）。$\mathrm{Succ}\%$：解析成功率。$\bar{\mathcal{S}}$：在全部 500 个样本上平均的统一综合分，解析失败记为 0。$\mathrm{Rep}\%$：包含重复内容的输出比例，越低越好。最佳结果用粗体，次佳结果用下划线。

| 类别 | 模型 | $\mathcal{F}_A$ | $\mathcal{F}_S^{\mu}$ | $\mathcal{F}_S^M$ | Succ% | $\bar{\mathcal{S}}$ | Rep% |
|---|---|---:|---:|---:|---:|---:|---:|
| 闭源前沿 API | GPT-5.4 | 14.91 | 1.55 | 1.38 | 100.0 | 8.12 | 0.4 |
| 闭源前沿 API | Claude-Sonnet-4.6 | 16.83 | 1.63 | 1.21 | 99.2 | 8.76 | 2.8 |
| 闭源前沿 API | Doubao-Seed-2.0-Pro（260215） | 52.65 | 44.78 | <u>42.59</u> | 49.4 | 21.22 | 0.0 |
| 闭源前沿 API | Doubao-Seed-2.0-Pro（评估于 2026-04-01） | <u>55.22</u> | 40.11 | 34.88 | 99.8 | <u>42.70</u> | 0.2 |
| 闭源前沿 API | Gemini-3-Pro-Preview | 50.90 | <u>48.22</u> | 37.58 | 100.0 | 42.33 | 6.0 |
| 开放权重基线 | Qwen3.5-397B-A17B | 42.71 | 18.15 | 17.73 | 94.2 | 32.73 | 4.0 |
| 开放权重基线 | GLM-5V-Turbo | 46.69 | 26.29 | 23.78 | 100.0 | 40.10 | 0.4 |
| 开放权重基线 | Kimi K2.5 | 31.21 | 7.42 | 7.21 | 79.4 | 20.18 | 1.0 |
| 开放权重基线 | GLM-4.6V 9B（基座） | 34.15 | 7.65 | 4.60 | 100.0 | 29.46 | 3.8 |
| 参考 SFT 系统 | **GLM-4.6V-9B + HG-SFT** | **74.97** | **72.26** | **48.25** | 100.0 | **71.53** | 0.8 |
| 相对此前最佳结果的差值 | | ↑19.75 | ↑24.04 | ↑5.66 | - | ↑28.83 | - |

#### 6.3 主要结果

表 2 报告了所有基线及参考 SFT 系统的结果。

**前沿 VLM 的性能远低于训练后的参考系统，单靠规模无法弥合差距。** 没有零样本基线的 $\mathcal{F}_A$ 超过 55.22，或 $\mathcal{F}_S^{\mu}$ 超过 48.22；而使用约 10k 个示例的参考系统达到 74.97/72.26，提升分别为 19.75/24.04 个点。尽管拥有 397B 参数，Qwen3.5-397B-A17B 仅取得 42.71/18.15，在 $\mathcal{F}_A$ 上落后于更小的闭源 API，在 $\mathcal{F}_S^{\mu}$ 上落后于 GLM-5V-Turbo。因此，单靠规模无法解决细粒度有序定位，HG-Bench 远未饱和。

**步骤级定位是主要能力缺口。** 每个零样本模型从 $\mathcal{F}_A$ 到 $\mathcal{F}_S^{\mu}$ 都有明显下降。Kimi K2.5 和 GLM-4.6V 9B 的步骤分数为个位数，GPT-5.4 与 Claude-Sonnet-4.6 仅取得 1.55 和 1.63，最强闭源 API 则从 55.22 降至 40.11。参考系统将这一差距缩小至 2.71 个点（74.97 对比 72.26），支持有针对性的监督，并推动将 $\mathcal{F}_S^{\mu}$ 作为首要排名指标。

**图 4：HG-SFT 数据规模扩展呈单调趋势，尚未饱和。** 实线使用三个训练轮次；虚线将所有实验固定为 930 个优化步骤。

**更多不同的领域内监督样本能够提升性能。** 图 4 汇总了按渠道、学科、页数与答案类型分层的嵌套子集。训练三个轮次时，将样本量从 1k 扩大至 9.92k，使 $\mathcal{F}_A$ 从 56.84 提升至 74.97，$\mathcal{F}_S^{\mu}$ 从 38.72 提升至 72.26；即使仅从 5k 增加到 9.92k，步骤级指标也提高了 8.79 个点。当训练固定为 930 步时，$\mathcal{F}_S^{\mu}$ 仍单调上升，依次为 45.18、60.14、67.02、72.26，证实增益由更多不同示例驱动，而非额外优化所致。

#### 6.4 学科与页数分解

**学科分解。** 在受评学科中，零样本基线在数学与科学上的得分最低。我们将其归因于 STEM 解答的非线性版面，如分式推导、矩阵和空间性草稿注记，这些布局违背了通用 VLM 训练中占主导的从左到右、从上到下先验。语言学科（语文、英语）遵循更规则的线性序列，使题目级画框（$\mathcal{F}_A$）更容易；即便如此，在段落密集交错的长篇答案中，细粒度步骤跟踪（$\mathcal{F}_S^{\mu}$）仍然退化，说明瓶颈在于版面密度，而非学科身份本身。

**页数扩展。** 我们按输入页数（1、2、3+）对测试集切片。零样本基线在单页输入上保持坐标格式，但随着页数增长，步骤级指标单调下降；从 1 页到 3 页及以上，基线的 $\mathcal{F}_S^{\mu}$ 平均下降超过 25%。不同模型家族的失败模式一致：页面边界幻觉，即框被归到错误页面，以及索引打乱，即跨页时步骤 ID 顺序错乱。参考 SFT 系统的下降显著较小，说明 SFT 中接触多页上下文有助于稳定跨页坐标映射。我们将多页坐标稳定性列为一个开放问题，当前跨模态注意力无法单凭规模解决它。

**图 5：HG-Bench 的任务概览与样本多样性。** 上方：共享评估提示词、带有预测题目级框（红色）与步骤级框（蓝色）的代表性双页手写输入，以及模型的文本定位轨迹。下方：三个额外样本，分别涵盖函数推导、计算和中文长篇写作，展示该基准在版面、手写密度与学科类型方面的多样性。其他针对具体失败的案例见附录 E。

### 7 分析

我们将模型失败分为五类：覆盖无手写内容区域的幻觉框；多步骤答案只获得题目级框的步骤遗漏；边界框被分配到错误页面的页面错位；一个步骤被拆开或多个步骤被合并的步骤过度/不足分割；以及无效 JSON、模式违规等格式失败。闭源前沿系统主要表现为步骤遗漏和分割不足，较弱的开放权重模型还经常遭遇格式错误。图 5 展示任务设置和有代表性的 HG-Bench 样本，详细失败案例见附录 E。

#### 7.1 模型间一致性

为衡量 HG-Bench 区分模型能力的程度，我们对每个测试样本统计九个零样本基线中有多少模型达到题目级 $F_1\ge T$，其中 $T=0.5$ 作为标准匹配阈值，$T=0.7$ 作为更严格的高质量门槛。

**HG-Bench 远未饱和。** 在 $T=0.5$ 时，仅有 3/500 个样本（0.6%）被全部九个基线解决，而 115 个样本（23.0%）被所有基线遗漏；其余 76% 的样本由一至八个模型解决，表明存在平滑的难度梯度。在 $T=0.7$ 时，全体均未解决的集合升至 44.6%，而全部通过的集合仍为 0.6%，证实当前前沿 VLM 仍有很大提升空间。

**困难样本并非主要由多页输入构成。** 在 $T=0.5$ 时所有模型都未解决的 115 个样本中，59 个（51%）来自企业渠道，56 个（49%）来自消费渠道，与平衡的测试集组成接近。因此，仅凭页数无法解释标题级失败；手写密度和步骤分解仍是主要的剩余挑战。

**有针对性的 SFT 能恢复真正困难的案例。** 对于 $T=0.5$ 时所有零样本基线均未解决的 115 个样本，参考 SFT 系统在其中 68 个样本（59.1%）上达到题目级 $F_1\ge0.5$。在更严格的 $T=0.7$ 下，它仍能恢复 223 个全体未解决样本中的 45.7%。这表明 HG-SFT 不只是改善简单案例，而是专门恢复前沿零样本系统能力范围之外的示例，支持第 6.3 节的可学习性主张。样本级视角十分重要，因为即使表面上已经收敛，整体 SFT 性能也可能掩盖始终未学会的子集（Xue et al., 2026b）。

### 8 结论

我们提出 HG-Bench，这是首个面向多页手写 K–12 作业中逐题和逐步骤答案区域定位的基准，并提供针对含步骤页面不平衡情况的页面感知协议。对前沿闭源和开放权重 VLM 的评估表明，$\mathcal{F}_A$ 在约 50～55 附近停滞，而步骤级定位（$\mathcal{F}_S^{\mu}$）仍是主要瓶颈，若干模型的分数低于 10。基于开放权重 9B 模型和约 10k 个领域内示例的简单 SFT 参考系统，无需强化学习即可超过所有受评闭源系统，凸显出有针对性的监督是实现结构化作业定位的实用途径。

### 局限性

HG-Bench 面向中国 K–12 作业；未衡量向其他语言和高等教育作业的迁移。基准包含 500 个样本，这限制了对更细粒度学科或年级结论的分辨率。评估使用单一 $\mathrm{IoU}=0.5$ 匹配阈值；本文未报告更严格或更宽松阈值下的性能。步骤分解存在无法完全消除的主观成分，尤其是较短的解答类答案；两阶段标注协议（第 4 节）能够缓解，但不能消除这一问题。标注者间一致性在随机抽取的 50 个样本子集上，由两名独立标注者进行报告（第 4 节）；将 IAA 扩展到更大子集，并报告逐类别以及题目/步骤的分解结果，是近期发布计划之一。

更多参考系统消融，包括渠道和监督目标消融，留待基于已发布 HG-SFT 语料的未来工作；参考 SFT 系统作为可学习性下界报告，而非方法贡献。最后，参考系统未经过强化学习阶段。近期研究使用模型内部不确定性触发更高效的生成式奖励建模（Xue et al., 2026a），而潜在状态评分可在多条推理轨迹中作选择（Yu et al., 2025b）；此类后训练能否进一步提升 HG-Bench 性能，仍是开放问题。

### 伦理声明

源作业图像在纳入基准或训练池前均已匿名化。两项资源均不含可识别学生个人身份的信息，也不向受评模型暴露任何学生个体属性。基于 HG-Bench 构建的系统，其预期下游用途是教师侧评分辅助，而非自动化学生评价、排名或招生决策。我们不发布学生个人作业；基准图像通过与第三方数据提供者的商业合作获得，使用条款允许教育研究，我们仅再分发派生的标注元数据及匿名标识。任何下游部署都应将这种数据最小化与基础设施级安全控制相结合。策略驱动的漏洞评估可聚合异构风险因素，以确定修复优先级（Shao, 2026a）；基于 SHAP 的异常检测集成，则为安全关键嵌入式场景中的网络流量监测提供可审计方法（Shao, 2026b）。

### 参考文献

Sahar Kazemzadeh, Vicente Ordonez, Mark Matten, and Tamara Berg. ReferItGame: Referring to objects in photographs of natural scenes（ReferItGame：指代自然场景照片中的物体）. 载于 EMNLP（自然语言处理实证方法会议）， 2014.

Licheng Yu, Patrick Poirson, Shan Yang, Alexander C. Berg, and Tamara L. Berg. Modeling context in referring expressions（指代表达中的上下文建模）. 载于 ECCV（欧洲计算机视觉会议）， 2016.

Junhua Mao, Jonathan Huang, Alexander Toshev, Oana Camburu, Alan Yuille, and Kevin Murphy. Generation and comprehension of unambiguous object descriptions（无歧义物体描述的生成与理解）. 载于 CVPR（计算机视觉与模式识别会议）， 2016.

Bryan A. Plummer, Liwei Wang, Chris M. Cervantes, Juan C. Caicedo, Julia Hockenmaier, and Svetlana Lazebnik. Flickr30K Entities: Collecting region-to-phrase correspondences for richer image-to-sentence models（Flickr30K Entities：收集区域–短语对应关系，以构建更丰富的图像到句子模型）. 载于 ICCV（国际计算机视觉会议）， 2015.

Ranjay Krishna, Yuke Zhu, Oliver Groth, Justin Johnson, Kenji Hata, et al. Visual Genome: Connecting language and vision using crowdsourced dense image annotations（Visual Genome：使用众包密集图像标注连接语言与视觉）. IJCV（《国际计算机视觉期刊》）， 123(1):32–73, 2017.

Liunian Harold Li, Pengchuan Zhang, Haotian Zhang, Jianwei Yang, Chunyuan Li, Yiwu Zhong, Lijuan Wang, Lu Yuan, Lei Zhang, Jenq-Neng Hwang, Kai-Wei Chang, and Jianfeng Gao. Grounded language–image pre-training（具有空间定位基础的语言–图像预训练）. 载于 CVPR（计算机视觉与模式识别会议）， 2022.

Shilong Liu, Zhaoyang Zeng, Tianhe Ren, Feng Li, Hao Zhang, Jie Yang, Chunyuan Li, Jianwei Yang, Hang Su, Jun Zhu, and Lei Zhang. Grounding DINO: Marrying DINO with grounded pre-training for open-set object detection（Grounding DINO：将 DINO 与定位预训练结合，用于开放集目标检测）. 载于 ECCV（欧洲计算机视觉会议）， 2024.

Keqin Chen, Zhao Zhang, Weili Zeng, Richong Zhang, Feng Zhu, and Rui Zhao. Shikra: Unleashing multimodal LLM’s referential dialogue magic（Shikra：释放多模态大语言模型的指代对话能力）. arXiv:2306.15195, 2023.

Haoxuan You, Haotian Zhang, Zhe Gan, Xianzhi Du, Bowen Zhang, Zirui Wang, Liangliang Cao, Shih-Fu Chang, and Yinfei Yang. Ferret: Refer and ground anything anywhere at any granularity（Ferret：在任意位置、以任意粒度指代与定位任何事物）. 载于 ICLR（国际学习表征会议）， 2024.

Pengfei Li, Beiwen Tian, Yongliang Shi, Xiaoxue Chen, Hao Zhao, Guyue Zhou, and Ya-Qin Zhang. TOIST: Task oriented instance segmentation transformer with noun–pronoun distillation（TOIST：采用名词–代词蒸馏的任务导向实例分割 Transformer）. 载于 NeurIPS（神经信息处理系统大会）， 35:17597–17611, 2022.

Yang Li, Xiaoxue Chen, Hao Zhao, Jiangtao Gong, Guyue Zhou, Federico Rossano, and Yixin Zhu. Understanding embodied reference with touch-line transformer（使用 Touch-Line Transformer 理解具身指代）. 载于 ICLR（国际学习表征会议）， 2023.

Songze Li, Xiaoke Guo, Tianqi Liu, Biao Yi, Zhaoyan Gong, Zhiqiang Liu, Huajun Chen, and Wen Zhang. What’s missing in screen-to-action? Towards a UI-in-the-loop paradigm for multimodal GUI reasoning（从屏幕到动作还缺少什么？迈向用于多模态 GUI 推理的界面在环范式）. 载于 Findings of ACL（ACL 研究发现论文集）， 第 17674–17690 页, 2026.

Shuo Lu, Yanyin Chen, Wei Feng, Jiahao Fan, Fengheng Li, Zheng Zhang, Jingjing Lv, Junjie Shen, Ching Law, and Jian Liang. Uni-Layout: Integrating human feedback in unified layout generation and evaluation（Uni-Layout：将人类反馈融入统一版面生成与评估）. 载于 ACM Multimedia（ACM 国际多媒体会议）， 第 7709–7718 页, 2025.

Zhentong Ye, Lei Zhang, Sijia Zhou, Yingda Yu, Yuehan Shi, Jiaqi Xuan, Shuaiwu Dong, Guanchao Tong, Meimei Zhang, and Bin Li. OSEF: One-step evidence fusion for cross-video scene procedure planning（OSEF：用于跨视频场景流程规划的单步证据融合）. arXiv 预印本 arXiv:2607.29401, 2026.

Ruina Hu, Chen Wang, Lai Wei, et al. Attend to evidence: Evidence-anchored spatial attention supervision for multimodal RLVR（关注证据：用于多模态 RLVR 的证据锚定空间注意力监督）. arXiv 预印本 arXiv:2605.30912, 2026.

Yifan Shen, Yuanzhe Liu, Jingyuan Zhu, Xu Cao, Xiaofeng Zhang, Yixiao He, Wenming Ye, James M. Rehg, and Ismini Lourentzou. Fine-grained preference optimization improves spatial reasoning in VLMs（细粒度偏好优化改善 VLM 的空间推理）. 载于 NeurIPS（神经信息处理系统大会）， 38:17929–17960, 2025.

Tianjiao Yu, Xinzhuo Li, Yifan Shen, Yuanzhe Liu, and Ismini Lourentzou. CoRe3D: Collaborative reasoning as a foundation for 3D intelligence（CoRe3D：以协作推理作为三维智能的基础）. arXiv 预印本 arXiv:2512.12768, 2025.

Jiaxin Liu, Ding Zhong, Yue Wang, et al. Dual-pathway circuits of object hallucination in vision-language models（视觉语言模型中物体幻觉的双通路回路）. arXiv 预印本 arXiv:2605.13156, 2026.

Zishan Shao, Lixun Zhang, Kangning Cui, Yixiao Wang, Ting Jiang, Hancheng Ye, Qinsi Wang, Zhixu Du, Yuzhe Fu, Fan Yang, Danyang Zhuo, Yiran Chen, and Hai Helen Li. DecodeShare: Tracing the shared subspace of LLM decode-time decisions（DecodeShare：追踪大语言模型解码时决策的共享子空间）. arXiv 预印本 arXiv:2607.20469, 2026.

Fan Zhang, Zhiwei Gu, and Hua Wang. Decoding with structured awareness: Integrating directional, frequency-spatial, and structural attention for medical image segmentation（结构感知解码：融合方向、频率–空间和结构注意力以进行医学图像分割）. 载于 AAAI（AAAI 人工智能会议）， 40(15):12421–12429, 2026.

Zhen Yao, Bo Lang, Zhihao Zheng, Haoyan Xu, Zhengtao Yao, Zhikang Dong, and Mooi Choo Chuah. From semantic to reasoing: A survey of language-guided segmentation in the multimodal era（从语义到推理：多模态时代语言引导分割综述）. TechRxiv, 2026.

Zhen Yao, Xin Li, Taotao Jing, Shuai Zhang, and Mooi Choo Chuah. DiSa: Saliency-aware foreground-background disentangled framework for open-vocabulary semantic segmentation（DiSa：用于开放词汇语义分割的显著性感知前景–背景解耦框架）. arXiv 预印本 arXiv:2601.20064, 2026.

Minesh Mathew, Dimosthenis Karatzas, and C.V. Jawahar. DocVQA: A dataset for VQA on document images（DocVQA：用于文档图像视觉问答的数据集）. 载于 WACV（计算机视觉应用冬季会议）， 2021.

Ahmed Masry, Do Xuan Long, Jia Qing Tan, Shafiq Joty, and Enamul Hoque. ChartQA: A benchmark for question answering about charts with visual and logical reasoning（ChartQA：结合视觉与逻辑推理的图表问答基准）. 载于 Findings of ACL（ACL 研究发现论文集）， 2022.

Minesh Mathew, Viraj Bagal, Rubèn Tito, Dimosthenis Karatzas, Ernest Valveny, and C.V. Jawahar. InfographicVQA（InfographicVQA：信息图视觉问答）. 载于 WACV（计算机视觉应用冬季会议）， 2022.

OpenAI. GPT-4V(ision) system card（GPT-4V(ision) 系统卡）. 技术报告, 2023. https://openai.com/index/gpt-4v-system-card/.

OpenAI. GPT-5.4 model（GPT-5.4 模型）. OpenAI API 文档, 2026. https://developers.openai.com/api/docs/models/gpt-5.4.

Gemini Team, Rohan Anil, Sebastian Borgeaud, et al. Gemini: A family of highly capable multimodal models（Gemini：高能力多模态模型家族）. arXiv 预印本 arXiv:2312.11805, 2023.

Google. Gemini 3 Pro preview（Gemini 3 Pro 预览版）. Gemini API 文档, 2025. https://ai.google.dev/gemini-api/docs/models/gemini-3-pro-preview.

Anthropic. The Claude 3 model family: Opus, Sonnet, Haiku（Claude 3 模型家族：Opus、Sonnet、Haiku）. 技术报告, 2024.

Anthropic. System card: Claude Sonnet 4.6（系统卡：Claude Sonnet 4.6）. 技术报告, Anthropic, 2026 年 2 月 17 日. https://www.anthropic.com/claude-sonnet-4-6-system-card.

ByteDance Seed Team. Seed1.5-VL technical report（Seed1.5-VL 技术报告）. arXiv 预印本 arXiv:2505.07062, 2025.

ByteDance Seed Team. Seed2.0 model card: Towards intelligence frontier for real-world complexity（Seed2.0 模型卡：迈向应对真实世界复杂性的智能前沿）. arXiv 预印本 arXiv:2607.00248, 2026.

Kimi Team. Kimi K2.5: Visual agentic intelligence（Kimi K2.5：视觉智能体智能）. arXiv 预印本 arXiv:2602.02276, 2026.

Peng Wang, Shuai Bai, Sinan Tan, Shijie Wang, Zhihao Fan, Jinze Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, Yang Fan, Kai Dang, Mengfei Du, Xuancheng Ren, Rui Men, Dayiheng Liu, Chang Zhou, Jingren Zhou, and Junyang Lin. Qwen2-VL: Enhancing vision–language model’s perception of the world at any resolution（Qwen2-VL：增强视觉语言模型在任意分辨率下对世界的感知）. 技术报告, 2024.

Shuai Bai, Keqin Chen, Xuejing Liu, et al. Qwen2.5-VL technical report（Qwen2.5-VL 技术报告）. 技术报告, 2025.

Qwen Team. Qwen3.5: Towards native multimodal agents（Qwen3.5：迈向原生多模态智能体）. 技术报告, 2026. https://qwen.ai/blog?id=qwen3.5.

Zhe Chen, Jiannan Wu, Wenhai Wang, Weijie Su, Guo Chen, Sen Xing, Muyan Zhong, Qinglong Zhang, Xizhou Zhu, Lewei Lu, Bin Li, Ping Luo, Tong Lu, Yu Qiao, and Jifeng Dai. InternVL: Scaling up vision foundation models and aligning for generic visual–linguistic tasks（InternVL：扩展视觉基础模型并针对通用视觉语言任务进行对齐）. 载于 CVPR（计算机视觉与模式识别会议）， 2024.

Zhe Chen, Weiyun Wang, Yue Cao, et al. Expanding performance boundaries of open-source multimodal models with model, data, and test-time scaling（通过模型、数据与测试时扩展拓展开源多模态模型的性能边界）. arXiv 预印本 arXiv:2412.05271, 2024.

Weihan Wang, Wenyi Hong, Yean Cheng, et al. CogVLM2: Visual language models for image and video understanding（CogVLM2：用于图像与视频理解的视觉语言模型）. 技术报告, 2024.

Yuan Yao, Tianyu Yu, Ao Zhang, Chongyi Wang, Junbo Cui, Hongji Zhu, et al. MiniCPM-V: A GPT-4V level MLLM on your phone（MiniCPM-V：手机上的 GPT-4V 水平多模态大语言模型）. 技术报告, 2024.

Bin Xiao, Haiping Wu, Weijian Xu, Xiyang Dai, Houdong Hu, Yumao Lu, Michael Zeng, Ce Liu, and Lu Yuan. Florence-2: Advancing a unified representation for a variety of vision tasks（Florence-2：推进适用于多种视觉任务的统一表征）. 载于 CVPR（计算机视觉与模式识别会议）， 2024.

Haotian Liu, Chunyuan Li, Yuheng Li, Bo Li, Yuanhan Zhang, Sheng Shen, and Yong Jae Lee. LLaVA-NeXT: Improved reasoning, OCR, and world knowledge（LLaVA-NeXT：改进推理、OCR 与世界知识）. 技术报告, 2024.

Zhiyu Wu, Xiaokang Chen, Zizheng Pan, et al. DeepSeek-VL2: Mixture-of-experts vision–language models for advanced multimodal understanding（DeepSeek-VL2：用于高级多模态理解的混合专家视觉语言模型）. 技术报告, 2024.

Marah Abdin, Sam Ade Jacobs, Ammar Ahmad Awan, et al. Phi-3 technical report: A highly capable language model locally on your phone（Phi-3 技术报告：在手机本地运行的高能力语言模型）. 技术报告, 2024.

GLM-V Team. GLM-4.5V and GLM-4.1V-Thinking: Towards versatile multimodal reasoning with scalable reinforcement learning（GLM-4.5V 与 GLM-4.1V-Thinking：通过可扩展强化学习迈向多功能多模态推理）. arXiv 预印本 arXiv:2507.01006, 2025.

GLM-V Team. GLM-5V-Turbo: Toward a native foundation model for multimodal agents（GLM-5V-Turbo：迈向面向多模态智能体的原生基础模型）. arXiv 预印本 arXiv:2604.26752, 2026.

Yuanzhe Liu, Jingyuan Zhu, Yuchen Mo, Gen Li, Xu Cao, Jin Jin, Yifan Shen, Zhengyuan Li, Tianjiao Yu, Wenzhen Yuan, Fangqiang Ding, and Ismini Lourentzou. PALM: Progress-aware policy learning via affordance reasoning for long-horizon robotic manipulation（PALM：通过可供性推理进行面向长时程机器人操作的进度感知策略学习）. arXiv 预印本 arXiv:2601.07060, 2026.

Bin Yu, Shijie Lian, Xiaopeng Lin, et al. FrameSkip: Learning from fewer but more informative frames in VLA training（FrameSkip：在 VLA 训练中从更少但信息更丰富的帧学习）. arXiv 预印本 arXiv:2605.13757, 2026.

Bin Yu, Shijie Lian, Xiaopeng Lin, et al. TwinBrainVLA: Unleashing the potential of generalist VLMs for embodied tasks via asymmetric mixture-of-transformers（TwinBrainVLA：通过非对称 Transformer 混合释放通用 VLM 在具身任务中的潜力）. arXiv 预印本 arXiv:2601.14133, 2026.

Fan Zhang, Shiming Fan, and Hua Wang. TimeSAF: Towards LLM-guided semantic asynchronous fusion for time series forecasting（TimeSAF：迈向用于时间序列预测的大语言模型引导语义异步融合）. 载于 ACL（计算语言学协会年会）， 第 26267–26284 页, 2026.

Chao Xue, Yao Wang, Mengqiao Liu, et al. Reason only when needed: Efficient generative reward modeling via model-internal uncertainty（仅在需要时推理：通过模型内部不确定性实现高效生成式奖励建模）. 载于 Findings of ACL（ACL 研究发现论文集）， 第 23302–23319 页, 2026.

Chao Xue, Yao Wang, Mengqiao Liu, et al. Why supervised fine-tuning fails to learn: A systematic study of incomplete learning in large language models（监督微调为何未能学会：对大语言模型不完全学习的系统研究）. 载于 ACL（计算语言学协会年会）， 第 30186–30213 页, 2026.

Jun Liu, Zhenglun Kong, Peiyan Dong, Changdi Yang, Tianqin Li, Yanyue Xie, Yifan Gong, Xuan Shen, Pu Zhao, Hao Tang, Geng Yuan, Wei Niu, Wenbin Zhang, Xue Lin, Dong Huang, and Yanzhi Wang. Structured agent distillation for large language model agents（面向大语言模型智能体的结构化智能体蒸馏）. 载于 Proceedings of the 25th International Conference on Autonomous Agents and Multiagent Systems（第 25 届自主智能体与多智能体系统国际会议论文集）， 第 3676–3685 页, 2026.

Shixing Guan, Xuan Hua, Jiahao Lin, and Luyan Zhang. Internalizing decomposed reasoning: Reverse-distilled fine-tuning for interpretable and robust Text-to-SQL（内化分解推理：面向可解释、鲁棒 Text-to-SQL 的反向蒸馏微调）. 载于 International Conference on Intelligent Computing（国际智能计算会议）， 第 534–544 页. Springer, 2026.

Bin Yu, Xinming Wang, Shijie Lian, et al. TrajSelector: Harnessing latent representations for efficient and effective best-of-N in large reasoning model（TrajSelector：利用潜在表征在大型推理模型中实现高效、有效的 N 选优）. arXiv 预印本 arXiv:2510.16449, 2025.

Alec Radford, Jong Wook Kim, Chris Hallacy, Aditya Ramesh, Gabriel Goh, Sandhini Agarwal, et al. Learning transferable visual models from natural language supervision（从自然语言监督中学习可迁移视觉模型）. 载于 ICML（国际机器学习会议）， 2021.

Chao Jia, Yinfei Yang, Ye Xia, Yi-Ting Chen, Zarana Parekh, Hieu Pham, Quoc V. Le, Yunhsuan Sung, Zhen Li, and Tom Duerig. Scaling up visual and vision-language representation learning with noisy text supervision（通过带噪声文本监督扩展视觉及视觉语言表征学习）. 载于 ICML（国际机器学习会议）， 2021.

Noam Shazeer, Azalia Mirhoseini, Krzysztof Maziarz, Andy Davis, Quoc Le, Geoffrey Hinton, and Jeff Dean. Outrageously large neural networks: The sparsely-gated mixture-of-experts layer（超大规模神经网络：稀疏门控混合专家层）. 载于 ICLR（国际学习表征会议）， 2017.

William Fedus, Barret Zoph, and Noam Shazeer. Switch transformers: Scaling to trillion parameter models with simple and efficient sparsity（Switch Transformers：通过简单高效的稀疏性扩展至万亿参数模型）. JMLR（《机器学习研究期刊》）， 23(120):1–39, 2022.

Albert Q. Jiang, Alexandre Sablayrolles, Antoine Roux, et al. Mixtral of Experts（Mixtral 专家混合）. 技术报告, 2024.

Damai Dai, Chengqi Deng, Chenggang Zhao, R.X. Xu, Huazuo Gao, Deli Chen, et al. DeepSeekMoE: Towards ultimate expert specialization in mixture-of-experts language models（DeepSeekMoE：迈向混合专家语言模型中的极致专家专门化）. 载于 ACL（计算语言学协会年会）， 2024.

Pan Lu, Hritik Bansal, Tony Xia, Jiacheng Liu, Chunyuan Li, Hannaneh Hajishirzi, Hao Cheng, Kai-Wei Chang, Michel Galley, and Jianfeng Gao. MathVista: Evaluating mathematical reasoning of foundation models in visual contexts（MathVista：评估基础模型在视觉情境中的数学推理）. 载于 ICLR（国际学习表征会议）， 2024.

Renrui Zhang, Dongzhi Jiang, Yichi Zhang, Haokun Lin, Ziyu Guo, Pengshuo Qiu, Aojun Zhou, Pan Lu, Kai-Wei Chang, Peng Gao, and Hongsheng Li. MathVerse: Does your multi-modal LLM truly see the diagrams in visual math problems?（MathVerse：你的多模态大语言模型真的看到了视觉数学题中的图示吗？） 载于 ECCV（欧洲计算机视觉会议）， 2024.

Runqi Qiao, Qiuna Tan, Guanting Dong, et al. We-Math: Does your large multimodal model achieve human-like mathematical reasoning?（We-Math：你的大型多模态模型实现了类人数学推理吗？） 技术报告, 2024.

Ke Wang, Junting Pan, Weikang Shi, Zimu Lu, Mingjie Zhan, and Hongsheng Li. Measuring multimodal mathematical reasoning with MATH-Vision dataset（使用 MATH-Vision 数据集衡量多模态数学推理）. 载于 NeurIPS（神经信息处理系统大会）， 2024.

Shuo Lu, Jianjie Cheng, Yinuo Xu, Yongcan Yu, Lijun Sheng, Peijie Wang, Siru Jiang, Yongguan Hu, Run Ling, Yihua Shao, Ao Ma, Wei Feng, Lingxiao He, Meng Wang, Qianlong Xie, Xingxing Wang, Nicu Sebe, Ran He, and Jian Liang. Do MLLMs really understand space? A mathematical reasoning evaluation（多模态大语言模型真的理解空间吗？一项数学推理评估）. arXiv 预印本 arXiv:2602.11635, 2026.

Chaoqun He, Renjie Luo, Yuzhuo Bai, Shengding Hu, Zhen Leng Thai, Junhao Shen, Jinyi Hu, Xu Han, Yujie Huang, Yuxiang Zhang, Jie Liu, Lei Qi, Zhiyuan Liu, and Maosong Sun. OlympiadBench: A challenging benchmark for promoting AGI with olympiad-level bilingual multimodal scientific problems（OlympiadBench：利用奥林匹克竞赛级双语多模态科学题目推动 AGI 的挑战性基准）. 载于 ACL（计算语言学协会年会）， 2024.

Yuan Liu, Haodong Duan, Yuanhan Zhang, Bo Li, Songyang Zhang, Wangbo Zhao, Yike Yuan, Jiaqi Wang, Conghui He, Ziwei Liu, Kai Chen, and Dahua Lin. MMBench: Is your multi-modal model an all-around player?（MMBench：你的多模态模型是全能选手吗？） 载于 ECCV（欧洲计算机视觉会议）， 2024.

Bohao Li, Rui Wang, Guangzhi Wang, Yuying Ge, Yixiao Ge, and Ying Shan. SEED-Bench: Benchmarking multimodal LLMs with generative comprehension（SEED-Bench：通过生成式理解对多模态大语言模型进行基准评估）. 技术报告, 2023.

Xiang Yue, Yuansheng Ni, Kai Zhang, Tianyu Zheng, Ruoqi Liu, Ge Zhang, et al. MMMU: A massive multi-discipline multimodal understanding and reasoning benchmark for expert AGI（MMMU：面向专家级 AGI 的大规模多学科多模态理解与推理基准）. 载于 CVPR（计算机视觉与模式识别会议）， 2024.

Hohin Kwan, Hongyu Li, Ray Zhang, Manyuan Zhang, Xianghao Kong, Anyi Rao, Jiahao Xie, and Si Liu. Video-MME-Logical: A controlled diagnostic benchmark for video temporal-logical reasoning（Video-MME-Logical：用于视频时序逻辑推理的受控诊断基准）. arXiv:2606.27828, 2026.

Pin Qian, Su Wang, Xiaoyuan Wang, Yihang Chen, Wenxuan Xu, Qiaolin Yu, Shuhuai Lin, Sipeng Zhang, Junxian You, and Xinpeng Wei. Relevant is not warranted: Evidence-force calibration for cited RAG（相关不等于有据支持：带引用 RAG 的证据支持力校准）. arXiv 预印本 arXiv:2605.28044, 2026.

Percy Liang, Rishi Bommasani, Tony Lee, et al. Holistic evaluation of language models（语言模型的全面评估）. TMLR（《机器学习研究汇刊》）， 2023.

Aarohi Srivastava, Abhinav Rastogi, Abhishek Rao, et al. Beyond the imitation game: Quantifying and extrapolating the capabilities of language models（超越模仿游戏：量化与外推语言模型的能力）. TMLR（《机器学习研究汇刊》）， 2023.

Wanru Shao. Policy-driven vulnerability risk quantification framework for large-scale cloud infrastructure data security（面向大规模云基础设施数据安全的策略驱动漏洞风险量化框架）. arXiv 预印本 arXiv:2604.06252, 2026.

Wanru Shao. Interpretable Ensemble Learning for Network Traffic Anomaly Detection: A SHAP-based Explainable AI Framework for Embedded Systems Security（用于网络流量异常检测的可解释集成学习：面向嵌入式系统安全、基于 SHAP 的可解释 AI 框架）. 载于 2026 14th International Symposium on Digital Forensics and Security (ISDFS)（2026 年第 14 届数字取证与安全国际研讨会）， 第 1–4 页. IEEE, 2026.

Jacob Cohen. A coefficient of agreement for nominal scales（名义尺度的一致性系数）. Educational and Psychological Measurement（《教育与心理测量》）， 20(1):37–46, 1960.

Joseph L. Fleiss. Measuring nominal scale agreement among many raters（测量多名评分者之间的名义尺度一致性）. Psychological Bulletin（《心理学公报》）， 76(5):378–382, 1971.

### A 标注指南（节选）

本附录总结标注者团队使用的核心规则（第 4 节）。完整指南文档随基准一同发布。

**跳过规则。** 当出现以下任一情况时，跳过该页，不绘制任何框：（i）图像损坏、空白或无法辨认；（ii）页面任何位置出现教师批改标记，包括勾、叉、书写分数或记号笔批改；（iii）该页所有学生生成标记均为非常规内容，例如自由绘画、涂鸦或偏离任务的内容。明确属于学生自身答案一部分的红笔标记，如下划线或高亮，不视为评分标记，页面予以保留。

**两级画框。** 每个学生手写区域由轴对齐边界框包围。每道题恰好获得一个题目级 `complete_answer_box`，紧密包围归属于该题的全部学生手写内容。对于多步骤解答，如计算、推导和多空填答，另外使用一个有序 `step_box` 元素列表分解答案；每个步骤框必须完全包含在父级题目框内。同一行手写内容绝不能拆分到两个框中。非正式草稿，例如页边计算、划去的草稿，不予画框。

**选择与判断答案。** 当填涂区域与手写字母答案同时存在时，标注者为填涂区域画框。若只存在其中一种，则为存在的那种画框。

**标签。** 每个题目级框携带（i）父级大题号和（ii）小题号，以斜杠分隔。原始标签遵循中文排版约定，包括全角括号、带圈数字和 blank-N 标识符；发布的模式逐字保留原始字符串。步骤 ID 是按照学生书写步骤的顺序分配的整数，从 1 开始。

**层级包含关系。** 每个步骤框都包含在父级题目框内，这一包含属性在标注时强制执行，并由质检审核者再次核验。

### B 参考 SFT 系统细节

本附录提供第 6.2 节所报告参考 SFT 系统的完整配置。该系统旨在作为 HG-Bench 的可学习性探针和可复现的性能下界参考，而非最先进模型提交。

**基座检查点。** 我们从 GLM-4.6V 9B（GLM-V Team, 2025）初始化；它是 Z.ai 于 2025-09-30 发布的开放权重视觉语言模型。我们有意避免从任何更新的同家族检查点初始化，以保证相较表 2 基线的增益不能由更强或更新的基础模型来解释。

**训练数据。** 我们在 HG-SFT 上微调，该训练池包含 9,920 个样本，与 500 个样本的 HG-Bench 测试集来自同一标注工作。两个池在构建时即互不重叠。作为额外保障，每张训练图像都通过感知哈希（perceptual hashing，pHash，汉明距离 $\le5$），并结合用户 ID 与拍摄时间戳的精确元数据匹配，与 HG-Bench 测试池进行检查。去重前，原始候选训练池包含 14,264 个样本；基于 pHash 的过滤移除 4,344 个近重复样本，得到最终的 $N_{\mathrm{train}}=9,920$。HG-SFT 保留源池自然的企业/消费渠道组成（6,515/3,405），不在渠道之间重新加权。

**优化方案。** 我们进行三个轮次的单阶段 SFT，对应 930 个优化步骤，全局批大小为 32，序列长度为 32,768，使用 bfloat16 精度和 AdamW 优化。学习率采用余弦策略，预热 30 步，峰值学习率 $1\times10^{-6}$，最低学习率 $5\times10^{-7}$，权重衰减为 0.1，梯度裁剪为 1.0。训练在单个 $8\times\mathrm{H100}$-80GB 节点上运行，张量并行为 2，上下文并行为 2，并启用序列并行，包含 ViT 视觉塔。表 3 列出了完整超参数和系统配置。

**表 3：参考 SFT 系统的超参数与系统配置。**

| 项目 | 数值 |
|---|---|
| 基座检查点 | GLM-4.6V 9B（GLM-V Team, 2025） |
| 精度 | bfloat16 |
| 序列长度 | 32,768 |
| 每张图像的视觉 token 数 | 最多 10,000，形状可变，抖动范围 0.75～1.25 |
| 优化器 | AdamW，$(\beta_1,\beta_2)=(0.9,0.95)$，$\epsilon=10^{-8}$ |
| 权重衰减 | 0.1 |
| 梯度裁剪 | 1.0 |
| 学习率策略 | 余弦，预热 30 步 |
| 峰值/最低学习率 | $1\times10^{-6}$ / $5\times10^{-7}$ |
| 全局批大小 | 32，微批大小为 1 |
| 训练步数 | 930，即在 9,920 个示例上训练 3 个轮次 |
| Dropout | 0 |
| 硬件 | 1 个节点，$8\times\mathrm{H100}$-80GB |
| 张量并行 | 2 |
| 上下文并行 | 2 |
| 序列并行 | 启用，包含 ViT 视觉塔 |
| 流水线并行 | 1 |
| ZeRO / 分布式优化器 | 启用，梯度归约与计算重叠 |
| 激活重计算 | 完全重计算，逐块执行 |
| 激活卸载 | 启用，包含 ViT 卷积与投影 |
| 优化器状态卸载 | CPU，100%，具有精度感知的矩估计 |
| 实际运行时间 | 约 3 小时 |
| 总计算量 | 约 24 GPU 小时 |

### C 提示词模板

**评估提示词。** 所有基线 VLM 都使用统一提示词模板查询。下文是原论文所列英文译文的中文翻译；评估中实际使用的逐字中文版本随基准发布。

> 你是一名面向教育作业和试卷的高精度视觉标注专家。你的任务是识别所提供图像中每个学生的手写答案区域，并输出两种边界框，坐标采用归一化至 $[0,1000]$ 的 `[xmin, ymin, xmax, ymax]` 格式。
>
> **框类型。** （a）`complete_answer_box`：紧密包含学生对一道题的完整答案。对于选择题和判断题，若同时存在填涂区域与手写字母答案，优先选择填涂区域。（b）`step_box`：用于计算、推导和多空填空等多步骤答案。每个步骤或空格单独画框，并按学生书写顺序从 1 开始分配 `step_id`。每个步骤框必须嵌套于对应的 `complete_answer_box` 中。
>
> **标注规则。** 只为学生自己的标记画框，包括手写文字、修改、勾选、连线和绘图。不要框入印刷题目文字或教师批改。步骤框必须完整包含该步骤或该空格的手写内容。对于同一道多空题，每个空格按从左到右、从上到下顺序成为一个独立步骤框。
>
> **输出格式。** 输出 JSON 列表。每个元素是题目级对象，具有以下字段：`box_2d`（题目级框）、`type`（固定为 `complete_answer_box`），以及可选的 `steps` 列表；其各元素均携带自己的 `box_2d` 与整数 `step_id`。条目必须按学生作答顺序输出。坐标必须紧密包围手写内容，不能裁掉任何字符。

图 6 展示了预期 JSON 输出的示意示例。

**格式提醒重试提示词。** 当格式容错解析器无法从模型首次回复中恢复出有效 JSON 数组时，追加以下指令进行一次重试：

> 你之前的回复无法被解析为有效 JSON 数组。请只回复上述 JSON 数组，不要附带任何说明文字或 Markdown 代码围栏。

```json
[
  {
    "box_2d": [100, 200, 180, 300],
    "type": "complete_answer_box"
  },
  {
    "box_2d": [400, 220, 490, 320],
    "type": "complete_answer_box",
    "steps": [
      {"box_2d": [410, 230, 440, 320], "step_id": 1},
      {"box_2d": [450, 230, 480, 320], "step_id": 2}
    ]
  },
  {
    "box_2d": [500, 220, 580, 780],
    "type": "complete_answer_box",
    "steps": [
      {"box_2d": [510, 230, 540, 780], "step_id": 1},
      {"box_2d": [550, 230, 580, 780], "step_id": 2},
      {"box_2d": [590, 230, 620, 780], "step_id": 3}
    ]
  }
]
```

**图 6：** 展示两级边界框模式的 JSON 输出示例：一道无步骤的选择题，一道含两个有序空格的填空题，以及一道含三个有序推导步骤的解答题。

在此重试后仍持续失败的输出，通过哨兵值 `FAIL_STR` 记录为终止错误（`success = False`）。

### D 补充指标

除第 5 节报告的两个主要定位指标（$\mathcal{F}_A$ 与 $\mathcal{F}_S^{\mu}$）外，我们还在表 2 中记录四个补充指标，用于描述步骤分解的宏观表现及各 VLM 的解析时可靠性。

**步骤级宏平均 $F_1$（$\mathcal{F}_S^M$）。** 这是 $\mathcal{F}_S^{\mu}$ 的宏聚合补充。仅针对真值中至少包含一个步骤框的样本子集，我们计算每个样本的步骤 $F_1$，即在样本内部对逐页步骤 $F_1$ 取平均，然后对所有此类样本取不加权均值。相比会增加步骤结构更密集页面权重的 $\mathcal{F}_S^{\mu}$，$\mathcal{F}_S^M$ 平等对待每个含步骤样本，因此放大了短多步骤答案的贡献，例如单个推导和多空填答。若模型只在长推导上表现良好，却在短多步骤题目上失败，其 $\mathcal{F}_S^{\mu}$ 与 $\mathcal{F}_S^M$ 的差距就会更大。

**解析成功率（Succ%）。** 在 $N=500$ 个样本中，模型回复在最多一次格式提醒重试后，能够产生符合规定模式、结构有效的 JSON 数组的样本比例。回复无法解析的样本计为失败，并在下述统一分数 $\bar{\mathcal{S}}$ 中，对所有定位指标贡献 0。

**所有样本上的统一分数（$\bar{\mathcal{S}}$）。** 这是一个考虑可靠性的综合指标，在完整的 500 个样本测试集上结合 $\mathcal{F}_A$ 与 $\mathcal{F}_S^{\mu}$：解析失败的样本记为 0，而不是被排除。具体而言，$\bar{\mathcal{S}}$ 是逐样本综合分在全部 500 个样本上的平均值；逐样本综合分是题目级和步骤级页面 $F_1$ 的加权组合，与评估时使用的逐页奖励相同。将 $\bar{\mathcal{S}}$ 与 $\mathcal{F}_A$ 比较，可以揭示格式失败的实际代价：若某模型的 $\mathcal{F}_A$ 较高、但 Succ% 较低，其 $\bar{\mathcal{S}}$ 将大幅下降；在 Doubao-Seed-2.0-Pro 260215 发布版中最为明显，其 $\mathcal{F}_A=52.65$，而 $\bar{\mathcal{S}}=21.22$，因为近半数输出无法解析。

**重复率（Rep%）。** 在 500 个输出中，模型产生重复文本或结构模式的比例，包括连续重复边界框、循环 JSON 片段，或在原始模型回复上通过最长公共子串启发式检测到的重复内容块。越低越好。表 2 报告 Rep% 以提供透明性信号；被标为重复的样本仍按标准协议计分，不从 $\mathcal{F}_A$、$\mathcal{F}_S^{\mu}$、$\mathcal{F}_S^M$、Succ% 或 $\bar{\mathcal{S}}$ 中排除。

### E 更多定性案例

本附录用四个额外 HG-Bench 样本补充第 7 节（图 5）的定性比较，展示不同失败模式与难度维度。

**图 7：案例 1：所有基线均遗漏的样本（全体失败后的恢复）。** 这是 115 个没有任何零样本基线达到标题级 $F_1\ge0.5$ 的样本之一（第 7.1 节）。每个闭源前沿 API 和开放权重基线都产生高度碎片化或错误定位的边界框；参考 SFT 系统则同时恢复题目级答案区域与有序步骤分解。

**图 8：案例 2：多页企业样本。** 一份跨两页的企业答题纸，展示页面错位与索引打乱失败：若干基线将框归到错误页面索引，或在跨页时输出不符合书写顺序的步骤 ID（参见第 6.4 节）。参考 SFT 系统保留了正确的页面归属和跨页逐步骤顺序。

**图 9：案例 3：步骤框过度分割。** 若干基线将单个多步骤推导拆分为过多步骤框，例如每个“=”或算术运算符都有自己的框，导致步骤数量膨胀并干扰下游逐步骤评分。参考 SFT 系统生成的步骤框在数量与粒度上均与人工标注一致。

**图 10：案例 4：步骤框分割不足。** 这是与案例 3 互补的失败：若干不同推导步骤被合并为一个大框，即使整体题目级框大致正确，也会丢失逐步骤评分信号。闭源基线在密集多行解答上最常表现出这一模式。参考 SFT 系统保留了逐步骤边界。
