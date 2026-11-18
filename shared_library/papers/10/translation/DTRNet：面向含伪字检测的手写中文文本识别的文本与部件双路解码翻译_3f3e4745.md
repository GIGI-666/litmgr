# DTRNet：面向含伪字检测的手写中文文本识别的文本与部件双路解码

DTRNet: Dual Text-Radical Decoding for Handwritten Chinese Text Recognition with Faked Character Detection

## 论文正文

作者：Runrui Li（runruili@mail.bnu.edu.cn）、Lin Zhu（通讯作者，linzhu@bnu.edu.cn）、Hua Huang（huahuang@bnu.edu.cn）。

三位作者均来自中国北京的北京师范大学人工智能学院（School of Artificial Intelligence, Beijing Normal University）、北京市教育人工智能重点实验室（Beijing Key Laboratory of Artificial Intelligence for Education）及智能技术与教育应用工程研究中心（Engineering Research Center of Intelligent Technology and Educational Application）。

**图 1　伪字检测及 DTRNet 框架概览。**（a）真实的中小学教育案例。在中文写作评价与自动阅卷中，教师需要识别学生手写内容中的伪字，才能标出原始书写错误，避免遗漏。图中进一步给出了伪字检测的定义以及现有识别系统的典型失败案例。（b）DTRNet 将文本分支、表意文字描述序列（Ideographic Description Sequence，IDS）分支与 IDS 引导的置信度调整（IDS-Guided Confidence Adjustment，IGCA）结合，以改善能感知伪字的识别。

### 摘要

在中小学教育场景中，手写中文文本识别既要转写学生书写的内容，也要检测伪字。然而，现有识别模型通常局限于预定义的正常字符集，因而无法显式识别伪字。现有检测方法的局限各有不同：单字级方法可以提供可解释的结构证据，但效率偏低；行级方法效率较高，却严重依赖置信度分数，容易漏检，也缺少显式结构证据。因此，核心挑战在于保持行级处理效率，同时保留独立于上下文推断的字符结构证据。

为此，我们提出 DTRNet，一种用于行级伪字检测的文本与部件双路解码框架。DTRNet 将感知上下文的文本识别与逐字结构验证解耦。文本分支负责整行转写，部件分支预测符合语法的 IDS，再依据词典判断伪字。我们进一步引入 IGCA，在推理阶段利用结构证据细化文本预测。实验表明，DTRNet 能有效检测伪字，同时保持较强的识别性能，并提供可解释的部件级证据。代码、模型检查点及处理后的数据集公开于 https://github.com/BNU-ERC-ITEA/DTRNet 。

**CCS 概念：** 计算方法 → 计算机视觉。  
**关键词：** 光学字符识别、手写中文文本识别、伪字检测、中小学教育。

本作品采用知识共享署名 4.0 国际许可协议。MM ’26，巴西里约热内卢。© 2026，版权归所有者/作者。ACM ISBN 979-8-4007-2213-4/2026/11。DOI：https://doi.org/10.1145/3767308.3835569 。arXiv:2608.05848v1 [cs.CV]，2026 年 8 月 6 日。

**ACM 引用格式：** Runrui Li、Lin Zhu、Hua Huang，2026。《DTRNet：面向含伪字检测的手写中文文本识别的文本与部件双路解码》。载于第 34 届 ACM 国际多媒体会议论文集（MM ’26），2026 年 11 月 10–14 日，巴西里约热内卢。ACM，美国纽约，15 页。https://doi.org/10.1145/3767308.3835569 。

### 1　引言

近年来，手写中文文本识别（Handwritten Chinese Text Recognition，HCTR）取得了显著进展 [23, 46]，广泛应用于中小学教育，例如中文写作评价和自动阅卷 [19, 31, 35]。然而，这些场景中的手写文本并不总是由标准字典中的正常字符组成。书写失误、记忆偏差或部件混淆都可能使学生写出伪字 [21]，即在标准字典中找不到对应正常字符的不存在的字。这些字的外观往往接近正常字，因此现有模型容易将它们过度纠正为看似合理的正常字。这既掩盖了原始书写错误，也降低了反馈和转写的可靠性。因此，此类 HCTR 系统在准确转写正常文本的同时，还应能在文本行中检测伪字。

如图 1 所示，已有研究处理伪字的能力仍明显受限。现有 OCR 系统 [1, 2, 33] 容易在上下文先验的作用下将伪字过度纠正为合理的正常字。基于自然语言处理的中文拼写纠错（Chinese Spelling Correction，CSC）[43, 44] 以文本为输入，无法捕获手写图像中伪字的视觉结构。专门处理这类问题的方法主要有两种。单字级手写汉字纠错（Handwritten Chinese Character Error Correction，HCCEC）方法 [18, 20, 34] 利用部件等结构线索，可解释性好，但须先将文本行切分成独立字符，再逐字检测，处理整行时效率较低。行级方法 [21, 41] 先做整行识别，再按置信度筛出疑似异常字。它们效率较高，却常因依赖置信度而漏检，难以区分普通识别错误与伪字，也无法提供显式的结构证据。在通用文本识别中，行级识别已凭借效率和准确率优势成为主流。因此，要在保持整行处理效率的前提下提高伪字检测能力和可解释性，就需要将显式字符结构建模引入行级伪字检测。

为解决这一问题，我们提出用于 HCTR 与伪字检测的文本与部件双路解码框架 DTRNet。其核心是将上下文感知的文本识别与逐字结构验证显式解耦，使检测不再只由识别置信度决定。文本分支负责整行转写，以保持正常文本识别性能；部件分支在各字符位置提取局部结构表示，并将其转写为 IDS [47, 48]，提供独立于上下文推断的结构证据。在此基础上，模型对照预定义的字符–IDS 词典逐字验证结构并识别伪字。我们还引入 IGCA，将结构证据反馈给文本分支，校准受上下文驱动的预测。这样，DTRNet 在一个行级框架中统一了文本转写、结构验证和伪字检测。由于伪字天然属于开放集，其类别无法预先穷举，我们将 Visual-C3 [21] 重构为行级伪字检测的广义零样本 [7, 30] 基准。实验表明，DTRNet 在整行识别和伪字检测上均持续优于代表性行级基线，同时给出可解释的部件级证据。与 OCR 工具及多模态大语言模型（MLLM）的比较进一步验证了其检测效果。在公开 BCTR 基准 [8] 上的结果也表明，DTRNet 具备鲁棒性和泛化能力。

本文的贡献如下。

- 提出文本与部件双路解码框架 DTRNet，在 HCTR 中引入显式字符结构建模，实现准确且可解释的伪字检测。
- 为部件分支设计感知合法性的 IDS 解码机制，并提出 IGCA，共同提高结构验证的可靠性及文本识别的鲁棒性。
- 将 Visual-C3 重构为行级伪字检测的广义零样本基准。实验表明，DTRNet 在该任务上持续优于代表性基线、OCR 工具及 MLLM，并在公开 BCTR 基准上展现出较强的鲁棒性与泛化能力。

### 2　相关工作

本节回顾四个研究方向：HCTR、CSC、HCCEC 和行级中文伪字检测。本文所说的“伪字”，指书写错误造成的、在标准字典及编码系统中均不存在的无效字符。如图 2 所示，相关研究主要采取三种范式：纯文本 CSC、单字级 HCCEC 和行级阈值检测。

**手写中文文本识别。** 手写文本识别已从基于 CNN/RNN 的模型发展为基于注意力的编码器–解码器框架 [39]。CRNN [33] 建立了统一的特征提取、序列建模与转写框架。NRTR [32] 用纯 Transformer 架构取代卷积和循环结构。ABINet [15] 加入显式语言建模，以更好利用上下文。SVTR [13] 则仅通过增强视觉建模来改善识别。近来，多模态大语言模型 [1, 3, 4, 6, 36, 40] 和面向 OCR 的大模型 [2, 22, 29, 42] 已将 OCR 从文本识别扩展到更广泛的文档理解任务 [16, 25]。

尽管识别能力很强，这些方法旨在恢复可读文本，并未专门设计显式伪字检测。引入更强的语言先验后，模型容易将异常输入过度纠正为看似合理的正常字，对转写有利，却抑制了伪字检测。因此，现有 HCTR 方法缺少可用于识别伪字的显式、可解释证据。

**中文拼写纠错。** CSC 是检测并纠正文本中错误字符的经典自然语言处理任务。代表性方法已从启发式设计发展到预训练语言模型框架。Soft-Masked BERT [49] 通过软掩码将显式错误检测与纠错连接起来。SpellGCN [10] 通过图卷积将语音及视觉混淆关系引入语言模型。PLOME [24] 在面向任务的预训练中进一步融入拼音和结构信息。

如图 2(a) 所示，CSC 本质上仅处理文本。SIGHAN13/14/15 [37, 43, 45] 等基准仅用文本表示错误，只能覆盖标准编码系统中定义的字符。因此，CSC 可以处理合法字符之间的误写，却无法建模手写图像中实际写出的伪字。

**图 2　现有研究处理伪字的代表性范式。**（a）基于自然语言处理的 CSC 只接收文本输入，无法建模实际书写的伪字。（b）单字级 HCCEC 利用部件等结构线索检测伪字，但须单独处理各字。（c）行级方法识别整行后，通过低置信度过滤检测可疑字符，缺少显式结构证据。

**手写汉字纠错。** HCCEC 是近期出现的、专门处理真实可见书写错误的任务。伪字类别开放，传统闭集分类不足以应对。TAN [20] 将 HCCEC 建模为广义零样本学习（GZSL）问题 [30]，通过树结构解码显式建模字符内部布局。CDC [18] 进一步减少自回归 IDS 分解的偏差，增强对未见伪字的泛化能力。近期，多模态方法 [34] 通过图像与 IDS 对齐推进了该任务。这些方法说明，结构线索对开放类别识别至关重要。

然而，现有 HCCEC 方法均以单字为单位，如图 2(b) 所示。尽管能够给出可解释的结构证据，它们需要显式切字并逐字处理，限制了行级场景中的效率。

**行级中文伪字检测。** 行级检测将任务从孤立字符扩展到连续手写文本。Visual-C3 [21] 推出了首个含有真实手写伪字的中文文本行图像数据集。VisCGEC [41] 进一步研究直接从手写句子图像进行视觉中文语法纠错，涵盖伪字、别字和更广泛的语法错误。这些工作为研究真实可见的书写错误提供了宝贵的数据资源与任务设定。

现有行级方法仍有明显局限。如图 2(c) 所示，Visual-C3 主要在整行识别后通过低置信度过滤检测可疑字符。这一策略虽有效率，却依赖后验置信度，缺少显式字符结构，难以区分一般识别错误与真正的伪字，也无法提供可解释的结构证据。此外，其随机划分方式可能让某些伪字在训练中出现，削弱了对未见样例泛化能力的评估。因此，目前仍缺少兼顾效率与显式字符结构建模的行级框架。

总的来看，已有研究表明，有效的伪字检测同时需要行级效率与显式结构证据。这促使我们在文本行框架内显式建模字符结构，以改善检测及可解释性。

### 3 所提方法

#### 3.1 动机与任务定义

现有手写中文文本识别（HCTR）模型主要从文本行图像中识别正常字符序列，解码时借助上下文语言先验提高准确率。这种语义依赖会引起过度纠正：模型倾向于把伪字强行识别成合乎语境的正常字，掩盖中小学学生实际书写的错误。因此，行级伪字检测既需要识别出的文本序列，也需要独立于上下文推断的字内结构证据。

手写汉字错误纠正（HCCEC）研究表明，伪字类别实际上无穷无尽。由此，我们把行级检测表述为广义零样本学习（GZSL）问题：训练只使用完全由正常字组成的文本行，推理既要准确转写正常字，也要明确拒识从未见过的伪字。相比孤立单字，文本行多了一层困难：上下文有助于辨认潦草的字，却也会使模型把伪字认作正常字。

基于这些观察，我们提出用于 HCTR 和伪字检测的文本与部件双路解码框架 DTRNet（图 3）。模型通过匹配表意文字描述序列（IDS）检测伪字，并在推理时通过 IDS 引导的置信度调整（IGCA）改善识别。

#### 3.2 编码器架构

为同时保留细粒度字内结构和行级上下文，我们采用 SVTR 编码器 [13] 作为视觉骨干。局部混合块捕捉笔画和部件模式，全局混合块建模长距离依赖，得到同时适用于文本转写和结构验证的视觉特征。

**图 3　DTRNet 框架。** 视觉编码器（3.2 节）从输入行图像提取特征图 $F$，并送入两个解耦的分支。文本分支执行上下文感知转写以识别正常文本（3.3 节）。部件分支通过字符定位、IDS 转写和合法性约束，得到独立于上下文推断的字符结构表示（3.4 节）。训练时联合优化两个分支，并对 IDS 施加额外的合法性监督。推理时，将预测 IDS 与预定义的字符–IDS 词典匹配以识别伪字，用 IGCA（3.5 节）校准文本预测。这样，同一框架可以识别文本、验证结构并检测伪字。图中的示例把本应为“讶”的误写分解为“⿰忄牙”，据此标记为 X。

对于输入图像 $X\in\mathbb R^{H\times W\times3}$，图像块嵌入将其变换为尺寸为 $\frac H4\times\frac W4\times C_0$ 的序列。骨干分为三个特征提取阶段，每阶段有六个局部或全局混合块。第二阶段之后进行下采样，高度减半、通道数增加、宽度保持不变。最终特征图为 $F\in\mathbb R^{\frac H8\times\frac W4\times C}$。

#### 3.3 文本解码器

文本分支基于 Transformer 解码器，将共享视觉特征图 $F$ 转写为目标文本序列 $Y_{\rm text}$。如图 3 左侧所示，先将其展平为长度 $N=\frac H8\times\frac W4$ 的视觉序列。为减少对同一区域的反复关注，我们采用交叉覆盖注意力（CCA）[38, 50, 51] 建模历史对齐。

设 $\alpha_t^i\in\mathbb R^N$ 为第 $i$ 层解码器在时刻 $t$ 的交叉注意力分布，$E_t^i\in\mathbb R^N$ 为对应的原始注意力分数。我们汇总此前各步的注意力，并结合上一层的注意力，构造覆盖项：

$$
C_t^i=\operatorname{Flat}\!\left(\operatorname{Conv2D}\!\left(\operatorname{Reshape}\!\left(\sum_{\tau=1}^{t-1}[\alpha_\tau^i;\alpha_\tau^{i-1}]\right)\right)\right). \tag{1}
$$

其中 $[\cdot;\cdot]$ 表示沿通道拼接，Reshape 将一维注意力序列恢复为二维空间图，Conv2D 汇聚局部邻域信息，Flat 再将它展平成向量。修正后的注意力为

$$
\widehat{\alpha}_t^i=\operatorname{Softmax}(E_t^i-C_t^i). \tag{2}
$$

该机制随时间累积已访问区域，并将覆盖范围延伸至相邻位置，帮助解码器把注意力移向尚未探索的区域，减少对同一字符的重复关注，从而提高转写准确率。

#### 3.4 部件解码器

如图 3 右侧所示，部件分支向行级伪字检测提供独立于语言上下文的字符结构证据。字符定位、IDS 转写两个模块从行特征中建立部件层面的结构表示，合法性感知解码进一步约束 IDS 预测，提高验证证据的可靠性。这样既保留单字的局部结构，也兼顾行级处理效率。

**字符定位模块（CLM）。** 首先将编码器输出 $F$ 展平为特征序列。为获得字符级特征，引入一组可学习查询 $Q=\{q_1,q_2,\ldots,q_L\}$，其中 $L$ 为最大文本长度。基于轻量 Transformer 解码器的 CLM 在 $Q$ 与 $F$ 之间执行交叉注意力：

$$
F^{\mathrm{char}}=\mathcal D_{\mathrm{loc}}(Q,F)\in\mathbb R^{L\times C}. \tag{3}
$$

$F_i^{\mathrm{char}}\in\mathbb R^C$ 表示第 $i$ 个字符的特征。短行只占用部分查询，因此增设查询有效性预测头，用二值标签将前 $T$ 个位置标为有效。推理时将预测转化为单调前缀掩码，以推断实际查询数。在 IDS 转写之前丢弃无效查询，避免混入冗余特征。定位不依赖文本解码状态，因而降低上下文偏差，为结构建模提供清晰的输入。

**图 4　表意文字描述序列（IDS）。**（a）空间结构符号及其所需子节点数。十类二元结构为左右（们）、上下（它）、全包围（因）、上包围（闪）、下包围（义）、左包围（匹）、左上包围（床）、右上包围（包）、左下包围（迷）、重叠（曲）。两类三元结构为左中右（斑）、上中下（享）。（b）“想”（xiang）的分层结构树及展平后的一维 IDS 符号序列“⿱⿰木⿴囗二心”。

**IDS 转写模块（ITM）。** 汉字内部结构可由 IDS 表示。其中结构符号描述部件之间的组合关系，部件符号对应基本构字单元。我们把每个有效字符特征转写成 IDS 符号序列，从而显式建模字内结构。给定字符特征 $f_i\in\mathbb R^C$，先将它扩展为 $K$ 个局部帧：

$$
U_i=\mathcal E_{\mathrm{frame}}(f_i)\in\mathbb R^{K\times C}. \tag{4}
$$

每个字符的帧数 $K$ 固定。通过 Transformer 对 $U_i$ 编码，再投影为各帧上的 IDS 符号分布。我们采用连接时序分类（CTC）[17]。它逐帧预测，不依赖先前输出，比自回归解码更适合忠实转写，能够保留伪字中异常却符合视觉观察的结构，为检测提供证据。

**合法性约束模块（LCM）。** 基于 IDS 的验证面临一个困难：视觉上似乎合理的预测，其结构未必合法。我们在解码中显式引入 IDS 文法。以往方法采用树解码或栈式解析，我们采用轻量的“待填节点计数器”，记录生成期间尚待补齐的子节点数，便于在训练和推理中控制合法性。

令 $z_k$ 为第 $k$ 个预测符号，$n_k$ 为当前待填节点数。初始化 $n_1=1$，表示需要一个根节点，此后按下式更新：

$$
n_{k+1}=n_k+\operatorname{arity}(z_k)-1. \tag{5}
$$

$\operatorname{arity}(z_k)$ 为该符号需要的子节点数。合法 IDS 在解码各步均应满足 $n_k>0$，终止时应有 $n_{K+1}=0$。训练时对违反合法性的情况施加惩罚，推理时屏蔽非法候选，从而提高 IDS 预测的可靠性和稳定性。

#### 3.5 部件分支的结构反馈

部件分支既能为伪字检测提供证据，也能修正受上下文驱动的文本预测。为此我们提出 IGCA，在推理阶段将结构证据反馈给文本分支，用于缓解过度纠正。

设 $o_t\in\mathbb R^{|V|}$ 为文本分支在时刻 $t$ 的原始输出分数，调整后的输出为

$$
\widetilde o_t=o_t+b_t. \tag{6}
$$

其中 $b_t\in\mathbb R^{|V|}$ 为根据部件分支结果构造的加分向量。只有在预测 IDS 完整且结构合法时才启用 IGCA。若完全匹配预定义字符–IDS 词典中的某一项，给对应字符类别加上精确匹配分；否则，根据归一化编辑距离，给最相似词条加上软匹配分。与通过低置信度间接判断异常的阈值启发式方法相比，IGCA 利用显式结构证据校准文本预测，保留文本分支的识别能力，并提高对上下文过度纠正的鲁棒性。

#### 3.6 训练与推理

我们端到端联合训练文本和部件分支。对于样本 $(X,Y_{\mathrm{text}},Y_{\mathrm{ids}})$，总目标为

$$
\mathcal L=\lambda_{\mathrm{text}}\mathcal L_{\mathrm{CE}}^{\mathrm{text}}
+\lambda_{\mathrm{ids}}\mathcal L_{\mathrm{CTC}}^{\mathrm{ids}}
+\lambda_{\mathrm{valid}}\mathcal L_{\mathrm{BCE}}^{\mathrm{valid}}
+\lambda_{\mathrm{illegal}}\mathcal L_{\mathrm{LP}}. \tag{7}
$$

四项依次是文本分支的交叉熵损失、部件分支的逐字符 CTC 损失、查询有效性预测头的二分类损失和 IDS 合法性惩罚。

推理时两条分支并行。部件分支先判断哪些字符查询有效，再在合法性约束下把相应特征解码成 IDS。预测 IDS 结构合法且命中词典时，该字判为正常字，否则视为伪字。沿用 Visual-C3，我们用特殊符号 X 标记伪字。随后，IGCA 利用结构证据校准文本分支的预测，在一次推理中完成文本识别、结构验证和伪字检测。

### 4 实验

#### 4.1 数据集构建

伪字构成开放集问题，Visual-C3 最初采用随机划分，不适于评价对未见伪字的零样本泛化能力。因此，我们重新构建行级 GZSL 基准。训练集只含正常行，测试集同时包含正常行和带有未见伪字的文本行。从公开训练集和验证集的 8,058 个样本出发，将多行图像裁成单行，得到 49,337 个训练样本、5,482 个正常测试样本（test_correct）和 4,370 个含伪字测试样本（test_faked）。全部 5,119 个伪字都留在含伪字测试集中，用于零样本评价。

我们进一步构建字符–IDS 词典，包含 3,020 个字符、323 个部件符号和 12 个结构符号。推理时，预测 IDS 不在词典中即标记为伪字。另外，我们在公开 BCTR 基准的四个领域上报告跨域结果，仅用于评价标准文本识别的泛化能力。

#### 4.2 实验方案

**实现细节。** 模型在重构的 Visual-C3 上训练和评价。图像缩放至 $32\times256$，文本和 IDS 最大长度分别为 15 和 25。文本词表对应 3,020 个字符；部件分支使用上述 323 个部件和 12 个结构符号。使用 AdamW [27] 训练 100 轮，学习率 $6.5\times10^{-4}$，权重衰减 0.05。采用 PARSeqAug 数据增强及 OneCycleLR 调度器（预热 5 轮）[26]，每块 GPU 批量大小为 256。联合目标中，文本交叉熵、IDS CTC 和查询有效性损失的权重均为 1.0，合法性惩罚权重为 0.1。推理先通过带约束的束搜索得到 IDS，再与词典匹配以标记伪字 X，然后通过 IGCA 校准文本预测。实验使用两块 NVIDIA A800 GPU，以混合精度运行。

**评价指标。** 第一，基础文本识别在两个子集上都报告整行准确率（ACC）和 1 减归一化编辑距离（1-NED）[28]，评价前统一标点。第二，伪字检测是以 X 为目标的字符级二分类。为处理预测与标注的长度差异，用编辑距离进行全局序列对齐，并报告字符级精确率（P）、召回率（R）和 F1 [21]。第三，为衡量开放词表环境中的结构稳定性，引入 IDS 序列合法率。设 $N_{\rm seq}$ 是预测的文本行 IDS 序列总数，$N_{\rm legal}$ 是其中结构合法的行数，则

$$
\text{IDS 序列合法率}=\frac{N_{\rm legal}}{N_{\rm seq}}. \tag{8}
$$

一行中所有有效字符的 IDS 均合法，该行才计为合法。该指标反映核验所依据的结构输出是否可靠，检测准确性另行评价。

**基线如何适配伪字检测。** 我们选取 CRNN [33]、NRTR [32]、ABINet [15]、SVTR [13]、PARSeq [5]、LISTER [9]、SMTR [11]、CPPD [12] 和 SVTRv2 [14] 九种文本识别方法。这些模型原本转写正常字，没有专门的伪字检测机制。遵循 Visual-C3 的设置，在推理后统一对逐字预测进行置信度拒识：低于 0.2 的字符替换为 X。该适配只增加统一的后处理规则。

**表 1　重构的行级检测基准。** 两个子集报告 ACC 与 1-NED，伪字检测报告 P、R、F1。IDS 合法率为合法预测行占比。除参数量（百万）外，数值均为百分数，发表信息沿用原表。

| 方法 | 正常行 ACC | 正常行 1-NED | 含伪字行 ACC | 含伪字行 1-NED | 伪字 P | 伪字 R | 伪字 F1 | IDS 合法率 | 参数量（M） |
|---|---|---|---|---|---|---|---|---|---|
| CRNN（TPAMI 2016） | 76.76 | 93.52 | 1.69 | 73.75 | 45.51 | 4.06 | 7.46 | – | 17.69 |
| NRTR（ICDAR 2019） | 60.32 | 86.57 | 7.20 | 66.39 | 23.39 | 44.13 | 30.57 | – | 47.25 |
| ABINet（CVPR 2021） | 83.21 | 95.70 | 0.50 | 75.15 | 53.19 | 0.97 | 1.91 | – | 42.86 |
| SVTR（IJCAI 2021） | 83.16 | 95.74 | 0.13 | 74.80 | 48.57 | 0.33 | 0.66 | – | 18.87 |
| PARSeq（ECCV 2022） | 82.72 | 95.76 | 0.18 | 74.21 | 38.46 | 0.58 | 1.15 | – | 19.26 |
| LISTER（ICCV 2023） | 82.36 | 95.59 | 0.11 | 74.54 | 52.94 | 0.35 | 0.69 | – | 21.57 |
| SMTR（AAAI 2025） | 84.27 | 96.20 | 0.80 | 74.99 | 56.49 | 1.70 | 3.30 | – | 18.06 |
| CPPD（TPAMI 2025） | 81.24 | 95.27 | 11.48 | 77.47 | 45.59 | 22.25 | 29.90 | – | 29.27 |
| SVTRv2（ICCV 2025） | 84.02 | 96.09 | 0.04 | 74.94 | 66.67 | 0.15 | 0.31 | – | 20.94 |
| DTRNet | 86.81 | 96.76 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 | 27.59 |

**图 5　正常行与含伪字行代表样本的定性比较。** 绿色为正确输出，红色为错误。DTRNet 保持正常文本的识别能力，同时以 X 标记伪字，并提供逐字 IDS。图中对照 CRNN、NRTR、SMTR、CPPD、SVTRv2、DTRNet 及真值，例如在“打雪仗（X），滑雪”中，部件分支识别到“⿰扌丈”。

#### 4.3 定量和定性结果

表 1 采用 Visual-C3 的默认阈值 0.2。基线即使在正常行上表现良好，到了含伪字行也明显退化，说明它们容易把伪字纠正成合乎语境的正常字。在此设置下，DTRNet 综合表现最好：正常行 ACC 为 86.81%，含伪字行 ACC 为 20.29%、1-NED 为 80.25%，字符检测 F1 为 39.10%。

相对 CPPD 的检测收益主要来自召回率，DTRNet 为 34.53%，高出 12.28 个百分点。SVTRv2 的精确率有 66.67%，但召回率仅 0.15%，可见单凭高精确率不足以完成检测。DTRNet 的 IDS 合法率为 87.03%。图 5 呈现相同趋势：基线常把伪字规整为正常字，DTRNet 可以给出 IDS 证据并将其拒识为 X。这些结果说明，在该行级手写任务中，显式结构核验优于默认置信度筛选。

#### 4.4 消融实验

**表 2　DTRNet 消融。** 从纯文本基线起，依次考察部件分支、查询有效性、合法性约束及 IGCA。在两个测试集上报告 ACC 和 1-NED，另报告字符级检测指标及 IDS 合法率（%）。

| 方法 | 正常行 ACC | 正常行 1-NED | 含伪字行 ACC | 含伪字行 1-NED | 伪字 P | 伪字 R | 伪字 F1 | IDS 合法率 |
|---|---|---|---|---|---|---|---|---|
| 基线：仅文本 | 84.58 | 96.10 | 0.34 | 74.79 | 54.32 | 0.86 | 1.69 | – |
| ＋部件分支 | 84.98 | 96.20 | 19.61 | 80.11 | 44.24 | 34.87 | 39.04 | 77.56 |
| ＋查询有效性预测头 | 85.37 | 96.41 | 20.04 | 80.26 | 44.31 | 35.61 | 39.52 | 77.81 |
| 合法性：＋训练惩罚 | 85.60 | 96.43 | 19.97 | 80.36 | 44.31 | 35.16 | 39.21 | 77.73 |
| 合法性：＋推理约束 | 85.82 | 96.46 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 |
| IGCA：仅软匹配加分 | 85.91 | 96.47 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 |
| IGCA：仅精确匹配加分 | 86.70 | 96.74 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 |
| 完整 DTRNet | 86.81 | 96.76 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 |

**结构解耦。** 纯文本基线在含伪字行上的 ACC 仅 0.34%，检测 F1 仅 1.69%。加上部件分支后，F1 升至 39.04%；加入查询有效性预测头后达到 39.52%。显式结构验证与稳定的字符定位都很重要。

**合法性约束。** 合法性建模主要改善 IDS 可靠性。单加训练惩罚收益有限，推理时施加约束则使合法率从查询有效性基线的 77.81% 提高到 87.03%，识别也略有改善。在行级设置下，直接在推理时执行文法约束更有效。

**IDS 引导的置信度调整。** IGCA 主要改善正常文本识别。仅用软匹配或仅用精确匹配加分，伪字检测指标均未变化；仅精确匹配就使正常行 ACC 从 85.82% 升至 86.70%。完整模型综合表现最好：部件分支负责检测，合法性约束稳定 IDS 预测，IGCA 改善文本识别。

#### 4.5 伪字的可视化分析

**图 6　含伪字测试集中一行文字的视觉分析。** 左侧为逐字定位的注意力图，显示结构分支关注的位置；右侧显示每个字符的预测 IDS 部件。

为理解部件分支如何处理伪字，我们可视化了一行含一个伪字的逐符号注意力图。由粗到细的模式十分清楚：结构符号先关注整个字符，后续部件符号再逐步聚焦于较小的局部。对于正常字，这一过程稳定，与图像一致，解码序列能映射回词典中的有效条目。

伪字的注意力也能稳定地落在目标区域，问题出现在分解之后：局部部件可以分别定位和解码，但其组合无法对应词典中的有效字符结构。这表明，检测需要检验分解后各部件组合的一致性，单靠区域层面的识别不足以解决问题。

#### 4.6 与多模态大语言模型和 OCR 工具的比较

**表 3　含伪字子集上与 OCR 工具和多模态大语言模型的比较。** 数值均为百分数，各列最佳值加粗。

| 方法 | ACC | 1-NED | P | R | F1 |
|---|---|---|---|---|---|
| GPT-5.4 | 6.10 | 56.22 | 48.17 | 28.87 | 36.10 |
| qwen-vl-ocr | 0.10 | 73.33 | 50.00 | 0.16 | 0.36 |
| deepseek-v3.2 | 0.00 | 10.04 | 3.04 | 7.47 | 6.54 |
| kimi-latest | 3.10 | 67.82 | 52.39 | 15.65 | 24.10 |
| PPOCRv5 | 1.30 | 73.25 | **69.38** | 2.86 | 5.49 |
| RapidOCR | 0.30 | 72.81 | 61.90 | 1.09 | 2.15 |
| DTRNet | **20.29** | **80.25** | 45.05 | **34.53** | **39.10** |

通用 OCR 和多模态大模型在该任务上仍有困难。DTRNet 的含伪字行 ACC、1-NED 和检测 F1 分别为 20.29%、80.25%、39.10%；最强的大模型 GPT-5.4 的 F1 为 36.10%。OCR 工具较保守，精确率较高而召回率极低。多模态大模型的召回率稍好，但语义先验仍使它们倾向于将伪字规整成正常字。差距表明，行级伪字检测依赖显式的字内结构核验，通用 OCR 和多模态大模型在这一场景中没有专门建模此过程。

#### 4.7 标准文本识别性能

我们另外在中文文本识别基准 BCTR [8] 上检验泛化，涵盖街景、网页、文档和手写四个域。这是标准文本识别基准，因此只报告整行准确率以衡量跨域鲁棒性。

**表 4　BCTR 上的识别准确率（%）。** 各列最佳值加粗。

| 方法 | 街景 | 网页 | 文档 | 手写 | 平均 |
|---|---|---|---|---|---|
| CRNN | 62.50 | 68.42 | 94.66 | 43.04 | 67.16 |
| NRTR | 75.91 | 77.23 | 96.91 | 53.40 | 75.86 |
| ABINet | 77.30 | 77.30 | 98.61 | 55.87 | 77.27 |
| LISTER | 78.03 | 79.13 | 98.95 | 55.48 | 77.90 |
| CPPD | 80.26 | 80.63 | 98.86 | 56.92 | 79.17 |
| SVTRv2 | 80.35 | 80.53 | 99.02 | 60.98 | 80.22 |
| DTRNet | **82.66** | **82.43** | **99.19** | **64.32** | **82.15** |

我们的方法平均准确率最高，为 82.15%。文档域中多数方法已接近饱和，增益较小；在更困难的子集上增益更明显。相较于 SVTRv2，街景、网页和手写分别提高 2.31、1.90 和 3.34 个百分点。结果说明，面对较大的外观和领域变化，该设计仍有效。

#### 4.8 置信度阈值分析

表 1 沿用 Visual-C3 的阈值 0.2，但识别器的置信度校准有所不同。我们分别调整 CRNN、NRTR、CPPD 和 SVTRv2 的阈值，将低于阈值的字符改写为 X，同时观察含伪字行上的字符 F1 和正常行上的整行 ACC，兼顾伪字拒识和正常字误拒。

**图 7　代表性行级基线的置信度阈值分析。** 横轴为置信度阈值，纵轴为 F1 或正常行 ACC（%）。实线表示含伪字行的字符 F1，虚线表示正常行 ACC，星号为各模型 F1 最优时的工作点。

最优阈值因模型而异：CRNN 为 0.8，NRTR 为 0.3。提高阈值通常能改善检测直至各自最优点，同时会降低正常行识别率。CPPD 最佳 F1 为 39.21%，此时正常行 ACC 降至 63.01%。DTRNet 的 F1 为 39.10%，同时保留 86.81% 的正常行 ACC。调阈值可提高基线 F1，但常会误拒许多正常字；基于 IDS 的显式结构验证在二者之间取得了更好的平衡。

#### 4.9 局限性

行级伪字检测仍很困难，尤其是书写形态复杂或伪字高度模糊时，检测准确性仍有很大提升空间。其次，当前纠正阶段主要依赖 IGCA 这一轻量推理校准策略，尚未充分利用文本识别与结构验证间更深层的交互。值得继续探索更强的结构感知细化或联合纠正机制。

### 5 结论

本文将行级手写中文伪字检测表述为广义零样本问题，提出 DTRNet 文本与部件双路解码框架，将上下文感知文本识别与逐字结构验证相结合。引入 IDS 结构证据和 IGCA 后，模型能够检测未见伪字，同时保持较强的文本识别能力。在重构的 Visual-C3 上，相比代表性行级基线、OCR 系统和多模态大语言模型取得了明显改善；BCTR 实验进一步验证了该框架的鲁棒性。

### 致谢

本研究获得国家自然科学基金项目（编号 62437001）和中央高校基本科研业务费的部分资助。

### 参考文献

保留原文编号与书目信息，每项附中文题名。

[1] **GPT-4 技术报告**。Josh Achiam, Steven Adler, Sandhini Agarwal, Lama Ahmad, Ilge Akkaya, Florencia Leoni Aleman, Diogo Almeida, Janko Altenschmidt, Sam Altman, Shyamal Anadkat, et al. 2023. Gpt-4 technical report. arXiv preprint arXiv:2303.08774 (2023).（来源：arXiv 预印本。）

[2] **PaddleOCR：基于飞桨的多语言 OCR 工具包**。PaddlePaddle Authors. 2020. PaddleOCR, Awesome multilingual OCR toolkits based on PaddlePaddle. https://github.com/PaddlePaddle/PaddleOCR.（来源：飞桨项目仓库。）

[3] **Qwen-VL：支持理解、定位、文本读取等任务的通用视觉语言模型**。Jinze Bai, Shuai Bai, Shusheng Yang, Shijie Wang, Sinan Tan, Peng Wang, Junyang Lin, Chang Zhou, and Jingren Zhou. 2023. Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond. arXiv preprint arXiv:2308.12966 (2023).（来源：arXiv 预印本。）

[4] **Qwen2.5-VL 技术报告**。Shuai Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, Sibo Song, Kai Dang, Peng Wang, Shijie Wang, Jun Tang, Humen Zhong, Yuanzhi Zhu, Mingkun Yang, Zhaohai Li, Jianqiang Wan, Pengfei Wang, Wei Ding, Zheren Fu, Yiheng Xu, Jiabo Ye, Xi Zhang, Tianbao Xie, Zesen Cheng, Hang Zhang, Zhibo Yang, Haiyang Xu, and Junyang Lin. 2025. Qwen2.5-VL Technical Report. arXiv preprint arXiv:2502.13923 (2025).（来源：arXiv 预印本。）

[5] **基于置换自回归序列模型的场景文本识别**。Darwin Bautista and Rowel Atienza. 2022. Scene text recognition with permuted autoregressive sequence models. In European conference on computer vision. Springer, 178–196.（来源：欧洲计算机视觉会议。）

[6] **豆包大模型系列**。ByteDance. 2024. Doubao large model family. Technology Launch, Volcano Engine Blog. https://seed.bytedance.com/en/research（来源：火山引擎技术发布。）

[7] **自然场景物体识别中广义零样本学习的实证研究与分析**。Wei-Lun Chao, Soravit Changpinyo, Boqing Gong, and Fei Sha. 2016. An empirical study and analysis of generalized zero-shot learning for object recognition in the wild. In European conference on computer vision. Springer, 52–68.（来源：欧洲计算机视觉会议。）

[8] **中文文本识别基准：数据集、基线及实证研究**。Jingye Chen, Haiyang Yu, Jianqi Ma, Mengnan Guan, Xixi Xu, Xiaocong Wang, Shaobo Qu, Bin Li, and Xiangyang Xue. 2021. Benchmarking Chinese Text Recognition: Datasets, Baselines, and an Empirical Study. arXiv preprint arXiv:2112.15093 (2021).（来源：arXiv 预印本。）

[9] **LISTER：面向长度不敏感场景文本识别的邻接解码**。Changxu Cheng, Peng Wang, Cheng Da, Qi Zheng, and Cong Yao. 2023. LISTER: Neighbor Decoding for Length-Insensitive Scene Text Recognition. 2023 IEEE/CVF International Conference on Computer Vision (ICCV) (2023).（来源：国际计算机视觉大会。）

[10] **SpellGCN：将语音和视觉相似性融入中文拼写检查语言模型**。Xingyi Cheng, Weidi Xu, Kunlong Chen, Shaohua Jiang, Feng Wang, Taifeng Wang, Wei Chu, and Yuan Qi. 2020. Spellgcn: Incorporating phonological and visual similarities into language models for chinese spelling check. In Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics. 871–881.（来源：计算语言学协会年会。）

[11] **通过子串匹配识别超长文本**。Yongkun Du, Zhineng Chen, Caiyan Jia, Xieping Gao, and Yu-Gang Jiang. 2025. Out of Length Text Recognition with Sub-String Matching. Proceedings of the AAAI Conference on Artificial Intelligence 39, 3 (Apr. 2025), 2798–2806. doi:10.1609/aaai.v39i3.32285（来源：美国人工智能协会年会。）

[12] **用于场景文本识别的上下文感知并行解码器**。Yongkun Du, Zhineng Chen, Caiyan Jia, Xiaoting Yin, Chenxia Li, Yuning Du, and Yu-Gang Jiang. 2025. Context Perception Parallel Decoder for Scene Text Recognition. IEEE Transactions on Pattern Analysis and Machine Intelligence 47, 6 (2025), 4668–4683. doi:10.1109/TPAMI.2025.3545453（来源：IEEE 模式分析与机器智能汇刊。）

[13] **SVTR：基于单一视觉模型的场景文本识别**。Yongkun Du, Zhineng Chen, Caiyan Jia, Xiaoting Yin, Tianlun Zheng, Chenxia Li, Yuning Du, and Yu-Gang Jiang. 2022. Svtr: Scene text recognition with a single visual model. arXiv preprint arXiv:2205.00159 (2022).（来源：arXiv 预印本。）

[14] **SVTRv2：CTC 在场景文本识别中超越编码器–解码器模型**。Yongkun Du, Zhineng Chen, Hongtao Xie, Caiyan Jia, and Yu-Gang Jiang. 2024. SVTRv2: CTC Beats Encoder-Decoder Models in Scene Text Recognition. CoRR abs/2411.15858 (2024). https://arxiv.org/abs/2411.15858（来源：计算研究资料库（CoRR）。）

[15] **像人一样阅读：用于场景文本识别的自主、双向、迭代语言建模**。Shancheng Fang, Hongtao Xie, Yuxin Wang, Zhendong Mao, and Yongdong Zhang. 2021. Read Like Humans: Autonomous, Bidirectional and Iterative Language Modeling for Scene Text Recognition. In 2021 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR). doi:10.1109/cvpr46437.2021.00702（来源：计算机视觉与模式识别会议。）

[16] **OCRBench v2：评价大型多模态模型视觉文本定位与推理能力的改进基准**。Ling Fu, Biao Yang, Zhebin Kuang, Jiajun Song, Yuzhe Li, Linghao Zhu, Qidi Luo, Xinyu Wang, Hao Lu, Mingxin Huang, Zhang Li, Guozhi Tang, Bin Shan, Chunhui Lin, Qi Liu, Binghong Wu, Hao Feng, Hao Liu, Can Huang, Jingqun Tang, Wei Chen, Lianwen Jin, Yuliang Liu, and Xiang Bai. 2024. OCRBench v2: An Improved Benchmark for Evaluating Large Multimodal Models on Visual Text Localization and Reasoning. arXiv:2501.00321 [cs.CV] https://arxiv.org/abs/2501.00321（来源：arXiv 预印本。）

[17] **连接时序分类：使用循环神经网络标注未分割序列数据**。Alex Graves, Santiago Fernandez, Faustino Gomez, and Jurgen Schmidhuber. 2006. Connectionist temporal classification: labelling unsegmented sequence data with recurrent neural networks. In ICML ’06 Proceedings of the 23rd international conference on Machine learning. 369–376.（来源：国际机器学习大会。）

[18] **计数、分解与纠正：手写汉字错误纠正新方法**。Pengfei Hu, Jiefeng Ma, Zhenrong Zhang, Jun Du, and Jianshu Zhang. 2025. Count, decompose and correct: A new approach to handwritten Chinese character error correction. Pattern Recognition 160 (2025), 111110.（来源：《模式识别》。）

[19] **看得见符号，遗漏了结构：大模型真实手写数学表达式识别基准**。Sheng Jiang, Lin Zhu, Runrui Li, Mei Wang, Qiannan Zhu, Yaoyao Zhong, and Hua Huang. [n. d.]. Seeing Symbols, Missing Structure: A Real-World Handwritten Mathematical Expression Recognition Benchmark for Large Models. In Fortythird International Conference on Machine Learning.（来源：国际机器学习大会。）

[20] **面向手写汉字错误纠正的树结构分析网络**。Yunqing Li, Jun Du, Jianshu Zhang, and Changjie Wu. 2022. A tree-structure analysis network on handwritten chinese character error correction. IEEE Transactions on Multimedia 25 (2022), 3615–3627.（来源：IEEE 多媒体汇刊。）

[21] **迈向真实写作辅助：含伪字和别字的汉字检查基准**。Yinghui Li, Zishan Xu, Shaoshen Chen, Haojing Huang, Yangning Li, Shirong Ma, Yong Jiang, Zhongli Li, Qingyu Zhou, Hai-Tao Zheng, et al. 2024. Towards real-world writing assistance: A chinese character checking benchmark with faked and misspelled characters. In Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers). 8656–8668.（来源：计算语言学协会年会。）

[22] **MonkeyOCR：基于结构、识别、关系三元范式的文档解析**。Zhang Li, Yuliang Liu, Qiang Liu, Zhiyin Ma, Ziyang Zhang, Shuo Zhang, Zidun Guo, Jiarui Zhang, Xinyu Wang, and Xiang Bai. 2025. MonkeyOCR: Document Parsing with a Structure-Recognition-Relation Triplet Paradigm. arXiv:2506.05218 [cs.CV] https://arxiv.org/abs/2506.05218（来源：arXiv 预印本。）

[23] **联机与脱机手写汉字识别：基于新数据库的基准评测**。Cheng-Lin Liu, Fei Yin, Da-Han Wang, and Qiu-Feng Wang. 2013. Online and offline handwritten Chinese character recognition: Benchmarking on new databases. Pattern Recognition (Jan 2013), 155–162. doi:10.1016/j.patcog.2012.06.021（来源：《模式识别》。）

[24] **PLOME：利用错拼知识预训练进行中文拼写纠正**。Shulin Liu, Tao Yang, Tianchi Yue, Feng Zhang, and Di Wang. 2021. PLOME: Pre-training with misspelled knowledge for Chinese spelling correction. In Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics and the 11th International Joint Conference on Natural Language Processing (Volume 1: Long Papers). 2991–3000.（来源：计算语言学协会年会暨国际自然语言处理联合会议。）

[25] **OCRBench：探索大型多模态模型的 OCR 能力**。Yuliang Liu, Zhang Li, Mingxin Huang, Biao Yang, Wenwen Yu, Chunyuan Li, Xu- Cheng Yin, Cheng-Lin Liu, Lianwen Jin, and Xiang Bai. 2024. OCRBench: on the hidden mystery of OCR in large multimodal models. Science China Information Sciences 67, 12 (Dec. 2024). doi:10.1007/s11432-024-4235-6（来源：《中国科学：信息科学》。）

[26] **SGDR：带热重启的随机梯度下降**。Ilya Loshchilov and Frank Hutter. 2016. Sgdr: Stochastic gradient descent with warm restarts. arXiv preprint arXiv:1608.03983 (2016).（来源：arXiv 预印本。）

[27] **解耦权重衰减正则化**。Ilya Loshchilov and Frank Hutter. 2017. Decoupled weight decay regularization. arXiv preprint arXiv:1711.05101 (2017).（来源：arXiv 预印本。）

[28] **归一化编辑距离的计算与应用**。A. Marzal and E. Vidal. 1993. Computation of normalized edit distance and applications. IEEE Transactions on Pattern Analysis and Machine Intelligence 15, 9 (1993), 926–932. doi:10.1109/34.232078（来源：IEEE 模式分析与机器智能汇刊。）

[29] **Mistral OCR**。Mistral. 2025. Mistral OCR. Technology Launch, Volcano Engine Blog. https://mistral.ai/news/mistral-ocr（来源：Mistral 技术发布。）

[30] **广义零样本学习方法综述**。Farhad Pourpanah, Moloud Abdar, Yuxuan Luo, Xinlei Zhou, Ran Wang, Chee Peng Lim, Xi-Zhao Wang, and QM Jonathan Wu. 2022. A review of generalized zero-shot learning methods. IEEE transactions on pattern analysis and machine intelligence 45, 4 (2022), 4051–4070.（来源：IEEE 模式分析与机器智能汇刊。）

[31] **使用卷积神经网络自动批改手写答题纸**。Eman Shaikh, Iman Mohiuddin, Ayisha Manzoor, Ghazanfar Latif, and Nazeeruddin Mohammad. 2019. Automated Grading for Handwritten Answer Sheets using Convolutional Neural Networks. In 2019 2nd International Conference on new Trends in Computing Sciences (ICTCS). 1–6. doi:10.1109/ICTCS.2019.8923092（来源：计算科学新趋势国际会议。）

[32] **NRTR：用于场景文本识别的无循环序列到序列模型**。Fenfen Sheng, Zhineng Chen, and Bo Xu. 2019. NRTR: A No-Recurrence Sequenceto-Sequence Model For Scene Text Recognition. In 2019 International Conference on Document Analysis and Recognition (ICDAR). doi:10.1109/icdar.2019.00130（来源：国际文档分析与识别会议。）

[33] **面向图像序列识别的端到端可训练神经网络及其在场景文本识别中的应用**。Baoguang Shi, Xiang Bai, and Cong Yao. 2017. An End-to-End Trainable Neural Network for Image-based Sequence Recognition and Its Application to Scene Text Recognition. IEEE Transactions on Pattern Analysis and Machine Intelligence (Nov 2017), 2298–2304. doi:10.1109/tpami.2016.2646371（来源：IEEE 模式分析与机器智能汇刊。）

[34] **面向手写汉字错误纠正的多模态网络**。Haizhao Sun, Yu Ning, Xu Ji, Chuang Zhang, and Ming Wu. 2024. A Multimodal Network on Handwritten Chinese Character Error Correction.. In BMVC.（来源：英国机器视觉会议。）

[35] **自动作文考试评分系统：系统性文献综述**。Meilia Nur Indah Susanti, Arief Ramadhan, and Harco Leslie Hendric Spit Warnars. 2023. Automatic essay exam scoring system: A systematic literature review. Procedia Computer Science 216 (2023), 531–538.（来源：《计算机科学会议录》。）

[36] **Kimi K2.5：视觉智能体能力**。Kimi Team, Tongtong Bai, Yifan Bai, Yiping Bao, SH Cai, Yuan Cao, Y Charles, HS Che, Cheng Chen, Guanduo Chen, et al. 2026. Kimi K2. 5: Visual Agentic Intelligence. arXiv preprint arXiv:2602.02276 (2026).（来源：arXiv 预印本。）

[37] **SIGHAN 2015 中文拼写检查评测介绍**。Yuen-Hsien Tseng, Lung-Hao Lee, Li-Ping Chang, and Hsin-Hsi Chen. 2015. Introduction to SIGHAN 2015 bake-off for Chinese spelling check. In Proceedings of the Eighth SIGHAN Workshop on Chinese Language Processing. 32–37.（来源：SIGHAN 中文语言处理研讨会。）

[38] **神经机器翻译中的覆盖建模**。Zhaopeng Tu, Zhengdong Lu, Yang Liu, Xiaohua Liu, and Hang Li. 2016. Modeling coverage for neural machine translation. In Proceedings of the 54th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers). 76–85.（来源：计算语言学协会年会。）

[39] **注意力就是你所需要的一切**。Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez, Łukasz Kaiser, and Illia Polosukhin. 2017. Attention is all you need. Advances in neural information processing systems 30 (2017).（来源：神经信息处理系统大会。）

[40] **Qwen2-VL：增强视觉语言模型在任意分辨率下的世界感知能力**。Peng Wang, Shuai Bai, Sinan Tan, Shijie Wang, Zhihao Fan, Jinze Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, Yang Fan, Kai Dang, Mengfei Du, Xuancheng Ren, Rui Men, Dayiheng Liu, Chang Zhou, Jingren Zhou, and Junyang Lin. 2024. Qwen2-VL: Enhancing Vision-Language Model’s Perception of the World at Any Resolution. arXiv preprint arXiv:2409.12191 (2024).（来源：arXiv 预印本。）

[41] **VisCGEC：视觉中文语法纠错基准**。Xiaoman Wang, Dan Yuan, Xin Liu, Yike Zhao, Xiaoxiao Zhang, Xizhi Chen, and Yunshi Lan. 2025. VisCGEC: Benchmarking the visual Chinese grammatical error correction. In Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers). 5054–5068.（来源：计算语言学协会美洲分会会议。）

[42] **通用 OCR 理论：通过统一端到端模型迈向 OCR 2.0**。Haoran Wei, Chenglong Liu, Jinyue Chen, Jia Wang, Lingyu Kong, Yanming Xu, Zheng Ge, Liang Zhao, Jianjian Sun, Yuang Peng, et al. 2024. General OCR Theory: Towards OCR-2.0 via a Unified End-to-end Model. arXiv preprint arXiv:2409.01704 (2024).（来源：arXiv 预印本。）

[43] **SIGHAN 2013 中文拼写检查评测**。Shih-Hung Wu, Chao-Lin Liu, and Lung-Hao Lee. 2013. Chinese spelling check evaluation at SIGHAN bake-off 2013. In Proceedings of the seventh SIGHAN workshop on Chinese language processing. 35–42.（来源：SIGHAN 中文语言处理研讨会。）

[44] **基于语言模型、读音和字形的中文拼写错误检测与纠正**。Junjie Yu and Zhenghua Li. 2014. Chinese spelling error detection and correction based on language model, pronunciation, and shape. In Proceedings of The Third CIPS-SIGHAN Joint Conference on Chinese Language Processing. 220–223.（来源：CIPS–SIGHAN 中文语言处理联合会议。）

[45] **SIGHAN 2014 中文拼写检查评测概述**。Liang-Chih Yu, Lung-Hao Lee, Yuen-Hsien Tseng, and Hsin-Hsi Chen. 2014. Overview of SIGHAN 2014 bake-off for Chinese spelling check. In Proceedings of The Third CIPS-SIGHAN Joint Conference on Chinese Language Processing. 126–132.（来源：CIPS–SIGHAN 中文语言处理联合会议。）

[46] **SCUT-HCCDoc：非受控相机采集文档中的手写中文文本基准数据集**。Hesuo Zhang, Lingyu Liang, and Lianwen Jin. 2020. SCUT-HCCDoc: A New Benchmark Dataset of Handwritten Chinese Text in Unconstrained Camera-captured Documents. Pattern Recognition (2020), 107559.（来源：《模式识别》。）

[47] **学习汉字层级结构的部件分析网络**。Jianshu Zhang, Jun Du, and Lirong Dai. 2020. Radical analysis network for learning hierarchies of Chinese characters. Pattern Recognition 103 (2020), 107305.（来源：《模式识别》。）

[48] **面向印刷汉字零样本识别的部件分析网络**。Jianshu Zhang, Yixing Zhu, Jun Du, and Lirong Dai. 2018. Radical analysis network for zero-shot learning in printed Chinese character recognition. In 2018 IEEE International Conference on Multimedia and Expo (ICME). IEEE, 1–6.（来源：IEEE 国际多媒体与博览会。）

[49] **基于软掩码 BERT 的拼写错误纠正**。Shaohua Zhang, Haoran Huang, Jicong Liu, and Hang Li. 2020. Spelling error correction with soft-masked BERT. In Proceedings of the 58th annual meeting of the association for computational linguistics. 882–890.（来源：计算语言学协会年会。）

[50] **CoMER：基于 Transformer 的手写数学表达式识别中的覆盖建模**。Wenqi Zhao and Liangcai Gao. 2022. Comer: Modeling coverage for transformer-based handwritten mathematical expression recognition. In European conference on computer vision. Springer, 392–408.（来源：欧洲计算机视觉会议。）

[51] **TAMER：面向手写数学表达式识别的树感知 Transformer**。Jianhua Zhu, Wenqi Zhao, Yu Li, Xingjian Hu, and Liangcai Gao. 2025. TAMER: tree-aware transformer for handwritten mathematical expression recognition. In Proceedings of the AAAI Conference on Artificial Intelligence, Vol. 39. 10950–10958.（来源：美国人工智能协会年会。）

## 补充材料　DTRNet：面向含伪字检测的手写中文文本识别的文本与部件双路解码

Runrui Li、Lin Zhu（通讯作者）、Hua Huang。作者均来自北京师范大学人工智能学院、北京市教育人工智能重点实验室、智能技术与教育应用工程研究中心（中国北京）。电子邮箱分别为 runruili@mail.bnu.edu.cn、linzhu@bnu.edu.cn、huahuang@bnu.edu.cn。

本补充材料的 A 节给出任务、重构的 Visual-C3 基准、字符–IDS 词典与评价指标的细节。B 节给出额外定量结果，包括部件分支 CTC 与自回归（AR）解码的比较、设计分析及复杂度与效率。C 节给出更多伪字案例、与 OCR 工具和多模态大语言模型的定性对比，以及 BCTR 上的定性结果。D 节讨论任务设置、当前框架的局限和未来方向。

### A　任务、基准与评价细节

#### A.1　任务设置和重构的 Visual-C3 基准

我们聚焦于行级伪字检测。Visual-C3 共有 10,072 个样本，公开的带标注训练集和验证集合计 8,058 个。数据同时包含伪字与别字，字符级标注为 $(x,y,w,h,\mathrm{char})$。本研究只保留与伪字有关的样本，忽略别字问题：写错位置的别字仍是字表中的正常字符，更接近纯文本中文拼写纠错；伪字无法用纯文本直接表示，需要图像和结构信息。

中小学场景中的伪字难以预先穷举，这项任务天然具有开放集特征。我们将 Visual-C3 重构为行级广义零样本基准，把多行图像裁成单行，再拆成较短的行片段。正常片段用于训练，测试集分为 test_correct 和 test_faked。重构使 8,058 个样本扩展为 59,189 个片段，其中训练 49,337 个、正常测试 5,482 个、含伪字测试 4,370 个。全部 5,119 个伪字均置于 test_faked，训练中不出现。流程见图 S1。本基准在文本行上评价，与使用真实单字裁剪区域的 HCCEC 评测互补，分别覆盖连续行与孤立字场景。

**图 S1　将原始 Visual-C3 重构为行级伪字基准的流程。** 标签中红色标记伪字、绿色标记别字。仅保留与伪字有关的样本，以原始文本及纠正文本作为配对标签。多行切为单行，再切成短片段。正常片段构成训练集和 test_correct，含伪字片段全部进入 test_faked，以评价广义零样本性能。图中给出的配对例子为“含着这颗宝石，能听X”与“含着这颗宝石，能听懂”。

#### A.2　字符–IDS 词典细节

我们直接针对重构基准建立完整覆盖的词典。数据集包含 3,020 个目标字符，文本分支采用同一词表。常见汉字分解资源未覆盖数据中全部符号，尤其是英文字母、数字与标点，因而针对基准构建词典更合适。

3,020 个目标字符中，2,843 个具有标准 IDS 映射。其余无标准分解的符号保留为原子符号，并映射到自身，主要是英文字符、数字、中英文标点。这样词典可完全覆盖基准，不引入词表外符号。部件分支共使用 323 个部件或原子符号，以及 12 个表示 IDS 结构运算的结构符号。原始 Visual-C3 标注无字符 X，所以本文的大写 X 专指伪字，与实际字符类别没有冲突。

已有 IDS 感知识别方法多以提高正常字识别为目标，DTRNet 用预测 IDS 作为结构验证证据。此处 3,020 项词典服务于当前基准；其他应用若将罕见字或异体字视作合法字符，可添加其 IDS 或原子映射并按需扩展识别词表。

#### A.3　评价细节

本节补充正文省略的指标公式。两个测试子集均计算整行 ACC 与 1-NED。伪字检测将 X 作为正例，计算字符级精确率、召回率与 F1。另报告 IDS 序列合法率衡量结构有效性。评价前统一标点。设 $\hat y_i$ 与 $y_i$ 分别为第 $i$ 个样本的预测和真实序列，$N$ 为样本数，则

$$
\mathrm{ACC}=\frac{\sum_{i=1}^N\mathbf1(\hat y_i=y_i)}{N},\qquad
\mathrm{1\!-\!NED}=1-\frac{1}{N}\sum_{i=1}^N\frac{\operatorname{EditDist}(\hat y_i,y_i)}{\max(|y_i|,1)}. \tag{S1}
$$

对于伪字检测，先按编辑距离对预测与真值进行全局对齐，再在特殊符号 X 上计算真阳性（TP）、假阳性（FP）和假阴性（FN）。定义为

$$
P=\frac{\mathrm{TP}}{\mathrm{TP}+\mathrm{FP}},\quad
R=\frac{\mathrm{TP}}{\mathrm{TP}+\mathrm{FN}},\quad
F1=\frac{2\mathrm{TP}}{2\mathrm{TP}+\mathrm{FP}+\mathrm{FN}}. \tag{S2}
$$

设 $N_{\mathrm{seq}}$ 为预测的文本行 IDS 序列总数，$N_{\mathrm{legal}}$ 为结构合法的行数，定义

$$
\text{IDS 序列合法率}=\frac{N_{\mathrm{legal}}}{N_{\mathrm{seq}}}. \tag{S3}
$$

仅当一行中所有有效字符位置的 IDS 预测均合法时，该样本才计为合法。

### B　额外定量结果

#### B.1　部件分支中的 CTC 与 AR

为分析解码策略的作用，我们将部件分支中的 CTC 替换为自回归解码器。表 S1 比较不使用 IGCA 的 AR、启用 IGCA 的 AR 和完整 DTRNet。两种 AR 在含伪字行上的表现几乎一致，ACC 仅 1.44%，1-NED 为 75.29%，F1 为 3.61%。采用 CTC 的 DTRNet 分别达到 20.29%、80.25% 和 39.10%，在伪字检测中明显更有效。带 IGCA 的 AR 在正常行上的识别稍好，说明自回归解码对正常字识别可能仍有益。

两种 AR 的 IDS 合法率高达 99.84%，远高于 DTRNet 的 87.03%，但检测召回率只有 1.85%。这表明 AR 倾向于输出结构合法且偏向常见正常字的 IDS，因而把异常结构规整化，失去了拒识依据。CTC 的逐帧独立转写更可能保留异常，使预测难以与正常字词典条目匹配。这与我们优先忠实转写结构、避免依据上下文补全结构的设计相符。

**表 S1　部件分支的 CTC 与自回归解码。** 两个测试子集均报告 ACC 与 1-NED，另列字符级检测精确率、召回率、F1 和满足约束的 IDS 合法率（%）。

| 方法 | 正常行 ACC | 正常行 1-NED | 含伪字行 ACC | 含伪字行 1-NED | P | R | F1 | IDS 合法率 |
|---|---|---|---|---|---|---|---|---|
| AR，无 IGCA | 86.10 | 96.59 | 1.44 | 75.29 | 68.34 | 1.85 | 3.61 | 99.84 |
| AR | 86.93 | 96.94 | 1.44 | 75.29 | 68.34 | 1.85 | 3.61 | 99.84 |
| DTRNet（完整） | 86.81 | 96.76 | 20.29 | 80.25 | 45.05 | 34.53 | 39.10 | 87.03 |

#### B.2　设计的进一步分析

正文表 1 中，许多基线在正常行上有较高识别率，在含伪字行上则显著退化。擅长识别正常文本，并不能自然获得有效检测伪字的能力。依赖上下文先验或置信度拒识的方法尤其容易把伪字规整为看似合理的正常字。与 CPPD 相比，DTRNet 的优势主要来自召回率，达到 34.53%，高出 12.28 个百分点。SVTRv2 的精确率虽达 66.67%，召回率却只有 0.15%。模型除提高识别准确率外，还必须保留并利用异常字的结构证据。

正文表 2 阐明各部分的作用。部件分支是伪字检测能力的主要来源，使纯文本基线的 F1 从 1.69% 提高到 39.04%。查询有效性预测头进一步改善结果，说明稳定定位有利于结构验证。合法性建模主要改善 IDS 输出的可靠性，推理约束比训练惩罚更有效，使合法率从 77.81% 提高至 87.03%。IGCA 主要改善正常样本识别，对检测指标影响很小。部件分支承担检测，合法性约束稳定结构预测，IGCA 细化文本输出。

正文表 3 也呈现相同趋势。OCR 工具通常具有较高精确率和极低的召回率；多模态大模型的召回率稍好，但语义先验仍会使伪字被规整为正常字。GPT-5.4 在外部模型中最强，F1 达 36.10%，仍低于 DTRNet 的 39.10%。行级检测的困难既在于转写整行，也在于判断单字结构的有效性，通用 OCR 和多模态大模型没有显式建模后者。

#### B.3　模型复杂度与效率分析

**表 S2　行级方法、OCR 工具和多模态大模型的复杂度及效率。** 行级模型采用批量大小 1 的纯模型延迟；OCR 工具和多模态大模型采用端到端的每行平均实际耗时。F1 为 test_faked 上的伪字检测结果。

| 类型 | 方法 | 参数量（百万） | 时间（毫秒/行，越低越好） | F1（%，越高越好） |
|---|---|---|---|---|
| 行级 | CRNN | 17.69 | 7.28 | 7.46 |
| 行级 | ABINet | 42.86 | 13.96 | 1.91 |
| 行级 | CPPD | 29.27 | 20.83 | 29.90 |
| 行级 | SVTRv2 | 20.94 | 17.73 | 0.31 |
| 行级 | 仅文本 | 22.48 | 19.86 | 1.69 |
| 行级 | DTRNet | 27.59 | 46.74 | 39.10 |
| OCR 工具 | PPOCRv5 | – | 646.4 | 5.49 |
| OCR 工具 | RapidOCR | – | 1474.9 | 2.15 |
| 多模态大模型 | GPT-5.4 | – | 1843.4 | 36.10 |
| 多模态大模型 | qwen-vl-ocr | – | 608.6 | 0.36 |
| 多模态大模型 | kimi-latest | – | 832.7 | 24.10 |
| 多模态大模型 | deepseek-v3.2 | – | 2470.7 | 6.54 |

与纯文本基线相比，DTRNet 增加 511 万个参数，每行耗时从 19.86 增至 46.74 毫秒，检测 F1 从 1.69% 升到 39.10%。额外开销主要来自字符定位、IDS 转写、受约束解码、词典匹配和 IGCA。所有行级模型均在同一块 NVIDIA A800 上以批量大小 1 计时。

按表中的计时口径，DTRNet 仍快于 OCR 工具与多模态大模型。后两类每行通常需要数百至数千毫秒，检测水平也不稳定。GPT-5.4 的 F1 最接近 DTRNet，但耗时明显更高。DTRNet 在行级方法中速度并非最快，却能以可接受的代价取得表中最高检测 F1，较好地兼顾效率与效果。

### C　额外定性结果

#### C.1　更多伪字案例

图 S2 进一步展示 DTRNet 的失败案例，左侧三例来自正常行，右侧三例来自含伪字行。除最终文本外，还列出逐字 IDS，以分析两个分支的交互问题。正常行上的失败主要是结构证据与文本先验不一致。有时结构分支的线索更接近目标字，却不足以推翻文本分支按语境给出的预测；有时正常字被误拒为 X，说明模糊书写或不清晰的局部结构可能导致预测 IDS 偏离合法词条。图中还包含 Visual-C3 本身标注有误的一例，表面上的识别错误源于数据标注。

在含伪字行上，失败主要表现为漏检和 IDS 解码不足。有些伪字在结构上仍很接近正常字，被归入合法字类。另一些虽被正确拒识为 X，预测 IDS 却不合法或与预期分解不同。开放集下，判断一个字符异常与准确复原其内部结构是两个层次的能力。

**图 S2　重构基准上的额外失败案例。** 左三例来自 test_correct，右三例来自 test_faked，绿、红分别为正确和错误预测，逐字 IDS 用于诊断。主要错误包括结构纠正不足、误拒、漏检和 IDS 解码不完善。例如标注为“爬（X）”的伪字被识别为正常“爬”；另一个被正确拒识的位置，预测“⿰氵方”仍与预期结构“⿰氵⿰方攵”不同。

#### C.2　与 OCR 工具和多模态大模型的定性比较

我们在含伪字子集上进一步比较各方法。所有涉及多模态大模型的实验均采用改编自 Visual-C3 设置的提示词，原文意译如下：

> 首先定义伪字：由于偏旁或部件组合错误而形成、在字典中不存在的字符。请识别所给手写图像，用 X 标记其中所有伪字。仅返回一个 JSON 对象，恰好含有两个字符串字段 {"src":"...","tgt":"..."}。“src”须保留阅读顺序，将每个伪字替换成一个大写 X。“tgt”也须保留阅读顺序，不含 X，在伪字位置写出本应使用的正常字。不要输出 Markdown、代码围栏、注释或任何额外键。

**图 S3　含伪字测试集上与 OCR 工具及多模态大模型的定性比较。** 比较 PPOCRv5、GPT-5.4、kimi-latest 和 DTRNet，绿色与红色分别表示正确与错误预测。

PPOCRv5 通常把伪字规整成合理的正常字，kimi-latest 有类似倾向。GPT-5.4 对异常更敏感，能正确将部分伪字标记为 X，但遇到困难样本时，也会改动周围正常字，反映出其预测仍严重依赖整行语义生成。在这些例子中，DTRNet 能稳定拒识伪字并保留其余正常字。这与定量结果一致，说明逐字 IDS 验证有助于减少过度纠正和对周围上下文的干扰。

#### C.3　BCTR 上的定性结果

我们在 BCTR 手写子集上选取六个有代表性的困难样本，对比 CRNN、NRTR、ABINet、CPPD、SVTRv2 和 DTRNet（图 S4）。困难主要有两类：一是涂改痕迹、格线或附加笔画叠加造成的强背景干扰；二是相邻字符间距极小，局部边界模糊。多数基线的错误集中在这些区域，常常无法完整解析字形，导致只认出部分字符、重复识别局部部件、漏掉整字或部分部件。DTRNet 在这六例上均输出正确，表明逐字结构建模有助于缓解复杂背景及紧密布局造成的困难。案例与正文 BCTR 定量结果相符，进一步体现了框架在标准手写文本识别中的鲁棒性与泛化能力。

**图 S4　BCTR 手写子集上的定性结果。** 比较代表性行级方法与 DTRNet，绿、红分别表示正确、错误预测。例子包括“张冠李戴”“挨家挨户”和“心理活动描写”等。

### D　讨论、局限与未来方向

#### D.1　任务设置讨论

本研究要求在转写手写文本的同时检测并标记行内伪字，动机来自真实的中小学教学。学生可能因书写失误、遗忘或部件混淆而写出不存在的字符。教师需要保留原始错误以便评分和反馈；若系统像常规 OCR 那样将其规整为看似合理的正常字，原始错误便会丢失。因此，明确识别伪字也是该场景的目标。

我们采用行级广义零样本设置。实际手写识别系统通常先检测行级文本区域，再直接识别各行，因此真实应用中的伪字检测也应在文本行上研究。相较于 TAN 等单字策略，行级处理避免显式分割和逐字反复计算，效率更高。伪字类别无法预先枚举，具有开放集性质。为更真实地评价行级泛化，我们重构 Visual-C3，只用正常行训练，在 test_correct 和 test_faked 两个子集上测试。

#### D.2　局限性

尽管 DTRNet 取得较好的结果，距离解决行级伪字检测仍有差距。如 C.1 节所示，除漏检外，还存在文本与部件分支不一致、正常字误拒、IDS 解码不稳定。当伪字结构接近正常字或笔迹本身模糊时，即使模型捕获了部分异常线索，也可能无法正确拒识。难点还涉及字符定位、结构转写、文字符号与结构交互之间的一致性。当前词典覆盖基准中的全部字符，但系统依赖具体应用中映射的完整性和正确性，缺失或有噪声的映射可能导致正常字被误拒，这一敏感性尚未得到系统评价。

其次，纠正机制仍较轻量。IGCA 在推理时使用部件分支的结构证据缓解上下文先验造成的过度纠正，主要起事后调整作用。部件分支更多提供证据和辅助修正，与文本分支的双向联合决策仍不紧密。两分支产生相互冲突的线索时，模型尚不能稳定地按结构纠正，这是分支不一致错误的重要原因。

最后，可用数据也构成限制。Visual-C3 为任务奠定了基础，但现有样本多为方格作文，字间分隔较好，行布局规整。真实考试的其他题型甚至其他学科同样会出现伪字，文字可能更密集，页面背景和版面干扰更复杂。当前基准更适合验证规整中文文本，尚未充分覆盖更广泛的中小学场景，需要更大、更多样、更真实的数据资源。

#### D.3　未来方向

在模型层面，可加强结构建模与跨分支融合。当前主要在部件层面建模，未来可探索更细的笔画级建模，或结合笔画与部件的多粒度表示，以捕捉伪字与正常字的微妙差异。文本与部件分支交互仍有限，如何更精确地对齐两分支并稳定输出，是值得研究的问题。

在任务层面，可从伪字检测扩展至更广泛的手写中文错误分析。真实教学中，教师还需标注别字、多字、漏字，乃至语法和语义错误。实际需求包括统一定位、识别并标注多种错误。将伪字检测与更广泛的错误检测、定位、纠正结合起来，更具应用价值。

在数据与评价层面，需要更大、更多样、更贴近真实中小学场景的数据。当前基准已支持行级开放集检测，但数据形态较有限。未来应覆盖复杂题型、布局和书写条件，并配套相应的开放集评测方案，以系统评价模型在真实教育场景中的泛化能力与诊断价值。
