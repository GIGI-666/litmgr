# Real5-OmniDocBench：面向真实场景鲁棒文档解析的全规模物理重建基准

Real5-OmniDocBench: A Full-Scale Physical Reconstruction Benchmark for Robust Document Parsing in the Wild

## 论文正文

作者：Cheng Cui¹、Changda Zhou¹、Ziyue Gao¹˒²、Xueqing Wang¹、Tingquan Gao¹、Jing Tang²、Yi Liu¹

¹ 百度公司飞桨团队（PaddlePaddle Team, Baidu Inc.）

² 香港科技大学（广州）（The Hong Kong University of Science and Technology (Guangzhou)）

联系邮箱：paddleocr@baidu.com

arXiv:2603.04205v2 [cs.CV]，2026 年 6 月 22 日。

### 摘要

尽管视觉语言模型（Vision-Language Models，VLMs）在 OmniDocBench 等数字文档基准上取得了接近满分的成绩，但由于缺乏可控且真实的评估，它们在不可预测的物理世界中的表现仍然鲜为人知。我们提出 Real5-OmniDocBench，这是首个在扫描（Scanning）、翘曲（Warping）、屏幕翻拍（Screen-Photography）、光照（Illumination）和倾斜（Skew）这五种关键真实场景下，对整个 OmniDocBench v1.5（1,355 张图像）进行全规模、一对一物理重建的基准。以往基准要么缺少与数字文档的对应关系，要么只对部分样本采样；与之不同，我们完整的真值映射首次支持对性能退化进行严格的逐因素归因，使我们能够准确判断失败究竟源于几何畸变、光学伪影，还是模型本身的局限。该基准为社区建立了一个具有挑战性的新标准，表明文档解析中的“现实差距”远未弥合，并提供了一种诊断工具，以指导真正具有韧性的文档智能的发展。

### 1 引言

文档解析是将非结构化文档图像转换为 Markdown、LaTeX 等结构化格式的任务，已成为评估 VLM 细粒度视觉推理能力的一项关键基准。近期进展在很大程度上由 OmniDocBench [1] 等高质量基准推动；这些基准为多种文档类型提供精确标注，并支持标准化评估。然而，这些基准主要依赖在理想、无畸变条件下获取的“原生数字”文档。一个令人不安的事实是，如今在 OmniDocBench 上得分极高的模型，在面对真实文档时可能会出现灾难性失败，例如被书脊弯曲的页面、在台灯下拍摄的收据，或受到摩尔纹干扰的屏幕截图。

数据集已公开发布于：https://huggingface.co/datasets/PaddlePaddle/Real5-OmniDocBench

在实际部署中，文档图像不可避免地受到复杂物理扰动：装订引起的非刚性翘曲、手持拍摄带来的透视畸变、环境光导致的不均匀照明，以及二次屏幕翻拍产生的光学伪影。尽管已有零散证据表明模型存在这些脆弱性，但社区仍缺乏对模型在这些条件下如何失败、为何失败的系统认识。以往评估工作可分为两类，但都不够充分：不受控的真实场景数据集（如 WildDoc [2]）捕获了真实退化，却缺少数字真值对应关系，无法精确衡量真实环境干扰对模型推理的影响；部分物理模拟（如 DocPTBench [3]）具有可控性，却采用粗粒度采样，既无法覆盖真实畸变的完整范围，也无法支持严格的逐因素诊断。当前缺少的是一种将物理采集的真实性与可控的一对一数字映射精度结合起来的基准：它不仅能够告诉我们模型失败了，还能准确指出是哪种畸变导致了失败。

我们提出 Real5-OmniDocBench，以填补这一关键空白。其核心创新简单而有力：在扫描、翘曲、屏幕翻拍、光照和倾斜这五种精心设计的物理场景中，对包含 1,355 页的完整 OmniDocBench v1.5 测试集进行全规模、一对一物理重建。对于每张数字源图像，我们采用专业级打印和异构移动拍摄设备生成五个物理变体，同时继承原始图像的全部真值标注。这一设计将物理畸变从不受控的混杂因素转化为可控的独立变量。因此，研究人员首次能够对理想条件与真实物理场景之间的领域差距开展因果分析，在完全可比的设置下，精确评估不同场景中的性能变化。这实现了此前无法达到的可比性水平。

我们的贡献包括三个方面：

- **首个用于因果鲁棒性分析的全规模物理基准。** 我们提出 Real5-OmniDocBench，这是首个提供完整 1,355 张图像物理重建、并与数字图像严格一一对应的基准。与部分采样或不受控的数据集不同，我们的设计支持将性能退化严格归因到具体物理因素，为社区提供一种诊断工具，而不仅仅是另一个排行榜。
- **全面的多场景物理建模。** 我们系统构建了扫描、翘曲、屏幕翻拍、光照和倾斜这五种正交物理场景，每种场景均包含多个不同子条件，例如翘曲中的折叠、圆柱弯曲、揉皱、角部折弯和书本弯曲。该场景级设计支持精确诊断模型鲁棒性，例如揭示某个对扫描伪影具有韧性的模型，在手持拍摄的翘曲条件下会严重退化。
- **揭示反直觉见解的大规模实证研究。** 通过对 17 个最先进模型进行全面基准评估，我们发现了一项挑战当前主流规模扩展范式的结果：紧凑的领域专用 VLM，例如参数量为 0.9B 的 PaddleOCR-VL-1.6，在物理扰动下持续优于规模大得多的通用模型。这表明，对真实畸变的鲁棒性并非参数数量的简单函数，而需要领域特定的归纳偏置；这一认识对未来模型设计至关重要。

通过公开发布 Real5-OmniDocBench，我们为社区提供了文档智能领域亟需的压力测试。我们的结果建立了一个要求严格的基线，揭示了数字条件下的完美表现与真实世界可靠性之间的显著差距。我们希望该基准能够推动相关研究，使模型真正理解文档，无论文档来自保存完好的档案，还是杂乱、不可预测的物理世界。

### 2 相关工作

**文档解析基准的演进。** 文档理解基准已从早期的单任务光学字符识别（Optical Character Recognition，OCR）评估，发展到复杂的端到端结构化解析；前者如聚焦文本检测与识别的 ICDAR 系列 [4]。在这一过程中，OmniDocBench [1] 凭借九种文档类型的定义和三级评估框架，即整页级、模块级和属性级，成为评估 VLM（如 Qwen3-VL [5]、Gemini 3 Pro [6]）文档解析能力的核心基准。尽管 OmniDocBench 提供高精度标注，但其主要依赖“原生数字”图像，忽视了真实物理部署中固有的质量退化。

**VLM 评估集现状。** 为进一步探索 VLM 的解析极限，近期出现了若干专用基准。OlmOCR-Bench [7] 引入由单元测试驱动的验证机制，检验公式和表格的结构等价性，但缺少物理场景多样性。OceanOCR-Bench [8] 关注复杂多模态版面中的图文关联和跨模态对齐。对于真实场景，WildDoc [2] 从自然环境中收集大量文档，以极端光照和复杂背景挑战模型。然而，WildDoc 等数据集缺少与完好数字原件的一对一对应关系，无法精确对比模型在理想条件与真实环境中的表现。此外，尽管 DocPTBench [3] 尝试了物理拍摄，但部分采样和缺少干扰因素细粒度分解，限制了它作为标准化诊断工具的实用性。

**Real5-OmniDocBench 的独特性。** Real5-OmniDocBench 填补了上述空白。与关注预处理与恢复的工作（如 DocRes [9]）不同，我们强调端到端解析性能。相比仍主要基于数字图像的 OCRBench-v2 [10] 等 VLM 评估，我们通过对 OmniDocBench 语料进行完整物理重建，实现了数字域与物理域之间的“全量对齐”。该设计支持对扫描、翘曲、屏幕翻拍、光照和倾斜这五种物理因素进行系统分解，为 VLM 在实际部署中的可靠性提供严格的诊断评估标准。

### 3 Real5-OmniDocBench 基准

#### 3.1 设计原则与总体架构

Real5-OmniDocBench 基于 OmniDocBench v1.5 [1] 构建，后者包含九种文档类型的 1,355 页文档，包括学术论文、书籍、笔记、财务报告、杂志等。我们遵循一对一映射原则：每个原始样本对应五个真实场景变体，总计 6,775 个测试样本。真值（ground truth，GT）继承策略确保零修改复用 OmniDocBench 的 JSON 标注，涵盖版面、表格、公式、文本和阅读顺序；这是保证评估严格可比的核心设计。图 1 展示了数据集中的代表性样本，体现了所覆盖文档类型和真实退化的多样性。

**图 1：** Real5-OmniDocBench 的样本。

#### 3.2 物理数据采集与标准化

#### 3.3 物理数据采集与标准化

为保证 Real5-OmniDocBench 的科学严谨性与可复现性，我们实施了严格的物理数据采集流程。所有物理样本均使用专业级 Canon C5840 多功能打印机复现，彩色打印与扫描均配置为 1200 dpi。这种高分辨率复现保证后续解析退化严格归因于环境扰动，而非源质量损失。

为保持原始数字语料的结构保真度，我们采用尺度感知打印策略：打印前，根据文档原生数字尺寸，将文档划分为 A3 和 A4 格式。该方法保留了原始字号比例与版面密度，而这些因素对精确的结构解析评估至关重要。对于四种手持拍摄场景，即翘曲、屏幕翻拍、光照和倾斜，我们采用由 Apple、Xiaomi 和 OPPO 主流移动设备组成的异构硬件矩阵。多样化设备的选择有助于捕获广泛的图像信号处理（Image Signal Processing，ISP）特征、传感器噪声模式和镜头畸变，从而反映不同硬件生态系统中真实用户行为的实际变化。

**扫描。** 扫描场景在可控的高分辨率条件下评估解析性能，同时引入真实纸张纹理与数字化噪声。如图 2 所示，我们实施五种代表性配置：（a）标准（Standard），用于理想且对齐良好的采集；（b）低质量（Low-quality），通过反复打印与扫描循环，模拟入门级硬件带来的分辨率损失；（c）斜放（Slanted），捕获手工平板扫描进纸中常见的非正交对齐；（d）夹订（Stapled），呈现角部夹子造成的局部阴影与遮挡；（e）装订（Bound），模拟具有典型边缘弯曲的书本式扫描。这些设置覆盖了档案和办公环境中的一系列数字化伪影。

图 2 子图：（a）标准；（b）低质量；（c）斜放；（d）夹订；（e）装订。

**图 2：** 扫描场景中的代表性配置。

**翘曲。** 翘曲场景模拟文档处理过程中遇到的非刚性物理变形。我们在图 3 中定义五种典型变形模式：（a）折叠（Folding），沿中心线形成折痕；（b）圆柱弯曲（Cylinder），产生卷曲后的残余曲率；（c）揉皱（Crumpling），引入密集、随机的局部折痕；（d）角部折弯（Corner），模拟边缘折角或页面卷曲；（e）书本弯曲（Book），复现装订书脊处的自然弧度。这组多样化几何畸变为模型的空间鲁棒性提供严格测试。

图 3 子图：（a）折叠；（b）圆柱弯曲；（c）揉皱；（d）角部折弯；（e）书本弯曲。

**图 3：** 翘曲场景中的代表性变形类型。

**屏幕翻拍。** 该场景复现对数字终端上显示的文档进行二次拍摄。我们将显示设备分为图 4 所示的五种不同终端：（a）办公显示器（Office Monitor），代表标准液晶显示器（LCD）；（b）专业显示器（Professional Display），具有高像素密度；（c）笔记本电脑（Laptop），采用集成式高分辨率面板；（d）平板电脑（Tablet），模拟便携式触摸屏设备；（e）手机（Mobile），代表小尺寸、高亮度的有机发光二极管（OLED）屏幕。这一选择确保对不同像素结构与摩尔纹进行系统评估。

图 4 子图：（a）办公显示器；（b）专业显示器；（c）笔记本电脑；（d）平板电脑；（e）手机。

**图 4：** 屏幕翻拍场景中显示终端的选择。

**光照。** 光照场景考察不均匀照明下的解析韧性。我们在图 5 中构建五种复杂视觉环境：（a）低光照（Low-light），模拟亮度不足；（b）阴影（Shadow），形成局部遮挡；（c）偏色（Color-cast），引入色彩偏移；（d）手电筒照射（Flashlight），产生集中式过曝；（e）折射（Refraction），模拟透过透明介质产生的视觉畸变。该设计探究模型在显著对比度扰动下保持语义一致性的能力。

图 5 子图：（a）低光照；（b）阴影；（c）偏色；（d）手电筒照射；（e）折射。

**图 5：** 光照场景中的系统性照明变化。

**倾斜。** 倾斜场景对手持拍摄中固有的三维透视畸变进行建模。我们在图 6 中设计五种姿态配置：（a）俯仰（Pitch），造成垂直方向的透视缩短；（b）滚转（Roll），产生水平方向的梯形畸变；（c）偏航（Yaw），导致平面旋转；（d）复合（Compound），结合多轴旋转；（e）极端（Extreme），采用剧烈倾斜角度并产生严重边缘畸变。这些变化反映了真实移动端文档采集中面临的几何挑战。

#### 3.4 质量审核与改进

为保证 Real5-OmniDocBench 的可靠性，我们实施了将自动异常检测与专家人工核验结合的多阶段质量控制流程。

图 6 子图：（a）俯仰；（b）滚转；（c）偏航；（d）复合；（e）极端。

**图 6：** 倾斜场景中的系统性三维姿态变化。

**机器辅助异常检测。** 我们采用一组最先进（state-of-the-art，SOTA）的 VLM，对所有采集图像进行初始推理。对于在整组模型上均出现灾难性性能下降的样本，例如零分离群点，将其标记为潜在异常。该阶段能够高效定位遭受严重硬件诱发失败的样本，例如极端运动模糊、硬件级过曝或意外取景偏移。

**专家人工核验与重新采集。** 所有被标记样本都经过严格的人工审核。我们对完整数据集开展三轮检查，以确保：（1）语义对应：每张图像都正确映射到 OmniDocBench v1.5 中对应的原始数字图像；（2）结构完整：没有因不当取景或遮挡而丢失重要内容；（3）几何正交性：标准化图像方向，纠正任何非预期的 90/180 度旋转。对于确认存在不可恢复伪影的样本，例如严重失焦导致文本无法阅读，通过重新采集与替换的循环处理，直到达到质量阈值。

**保真度与真实退化。** 我们严格区分非预期的拍摄错误与具有代表性的真实退化。虽然 1200 dpi 打印确保了源文档保真度，但手持拍摄相较数字原件必然会引入分辨率差距。我们有意保留一般性的清晰度退化，因为它反映了移动端文档解析的客观约束。审核协议只过滤“不可用”样本，例如严重模糊导致无法辨认的样本，同时保留摩尔纹和轻微噪声等真实伪影。这保证基准评估的是模型对实际部署条件的鲁棒性，而非对意外拍摄错误的容忍度。

**数据集完整性。** 通过持续改进，我们在全部五种场景中维持了对原始 1,355 个 OmniDocBench 样本的 100% 覆盖。Real5-OmniDocBench 最终版本实现了物理真实性与评估可靠性的最佳结合，为下一代 VLM 的基准评估提供了稳定基础。

### 4 评估方法与指标

Real5-OmniDocBench 被设计为与 OmniDocBench [1] 的评估生态完全兼容，支持对完好数字原件及其对应物理退化进行严格的跨域诊断分析。

**核心指标与科学逻辑。** 我们采用 OmniDocBench 的多维评分框架，将版面、内容与结构逻辑解耦。指标定义如下：

- **文本与阅读顺序：** 我们使用归一化编辑距离（Normalized Edit Distance，NED）：

$$
NED=1-\frac{Lev(s_1,s_2)}{\max(|s_1|,|s_2|)}
$$

其中，$Lev$ 表示 Levenshtein 距离。该指标用于全文 OCR 和阅读顺序，衡量字符级精确程度与拓扑一致性。

- **公式解析（CDM）：** 该框架的一个关键特征是字符检测匹配（character detection matching，CDM）[11] 指标。与基于字符串的指标不同，CDM 将公式转换为计算图来评估结构等价性，从而保证即使物理噪声引起轻微语法变化，也能客观评价数学逻辑。
- **表格结构与内容（TEDS）：** 我们采用基于树编辑距离的相似度（Tree Edit Distance-based Similarity，TEDS）[12]：

$$
TEDS(G_a,G_p)=1-\frac{EditDist(G_a,G_p)}{\max(|G_a|,|G_p|)}
$$

其中，$G$ 表示表格的树结构。我们同时报告 TEDS（整体）和 TEDS-Struct，以判断失败发生在内容识别还是结构重建环节。

- **总体指标：** 总体性能量化如下：

$$
\mathrm{Overall}=\frac{(1-\text{Text NED})\times100+\text{Table TEDS}+\text{Formula CDM}}{3}
$$

**模型阵列与对齐协议。** 为确保基准的可信度，我们根据测试对象与官方记录的对齐情况进行分类：

- **与官方对齐的基线：** 我们优先采用已在原始 OmniDocBench 报告中验证的模型，包括 Qwen3-VL-235B、Qwen2.5-VL-72B、Gemini-2.5 Pro、MinerU-1.8.2 和 PP-StructureV3。我们的评估原则遵循严格的“对齐优先”协议：首先在官方数字测试集上执行推理；只有成功复现官方指标的模型，才会继续在 Real5-OmniDocBench 上评估。对于当前无法对齐官方数字指标的模型，我们暂不公布其 Real5-OmniDocBench 分数，以保持评估严谨性。
- **补充前沿评估：** 我们还纳入最新的最先进模型，例如 Gemini-3 Pro、GPT-5.2、GLM-OCR、DeepSeek-OCR 2 和 PaddleOCR-VL-1.6，并使用相同配置，以反映 VLM 鲁棒性的最新进展。

### 5 实验与分析

#### 5.1 主要结果概览

表 1 对多种模型在 Real5-OmniDocBench 基准上的性能进行了全面分析。结果表明，遭遇物理退化时，不同模型架构表现出不同的鲁棒性特征。值得注意的是，专用模型 PaddleOCR-VL-1.6 的总体得分达到 93.19，以 0.9B 的参数规模，相较 Qwen3-VL-235B（88.90）和 Gemini-3 Pro（89.24）等规模显著更大的模型，展现出很强的竞争效率。在全部五种评估场景中，这一紧凑模型均保持稳定表现，指标范围从翘曲场景的 91.25% 到扫描场景的 94.74% [原文如此]。在不同物理条件下的这种稳定性表明，对于真实文档解析，领域特定的架构优化以及训练时接触多种伪影，可能比单纯扩大参数规模更重要；后者主要有利于语义先验，而非几何与光学不变性。

**表 1：Real5-OmniDocBench 上的综合评估。** S：扫描；W：翘曲；SP：屏幕翻拍；I：光照；SK：倾斜。最佳结果用粗体，次佳结果用下划线。

| 模型类型 | 方法 | 参数量 | Overall↑ | S↑ | W↑ | SP↑ | I↑ | SK↑ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 流水线工具 | Marker-1.8.2 [13] | - | 60.10 | 70.27 | 58.98 | 63.65 | 66.31 | 41.27 |
| 流水线工具 | PP-StructureV3 [14] | - | 64.45 | 84.68 | 59.34 | 66.89 | 73.38 | 37.98 |
| 通用 VLM | GPT-5.2 [15] | - | 78.66 | 84.43 | 76.26 | 76.75 | 80.88 | 75.00 |
| 通用 VLM | Qwen2.5-VL-72B [16] | 72B | 86.92 | 86.19 | 87.77 | 86.48 | 87.25 | 86.90 |
| 通用 VLM | Gemini-2.5 Pro [17] | - | 88.21 | 89.25 | 87.63 | 87.11 | 87.97 | 89.07 |
| 通用 VLM | Qwen3-VL-235B [18] | 235B | 88.90 | 89.43 | 89.99 | 89.27 | 89.27 | 86.56 |
| 通用 VLM | Kimi K2.5 [19] | 1T | 89.09 | 89.67 | 88.86 | 88.39 | 89.66 | 88.86 |
| 通用 VLM | Gemini-3 Pro [6] | - | 89.24 | 89.47 | 88.90 | 88.86 | 89.53 | 89.45 |
| 专用 VLM | Deepseek-OCR 2 [20] | 3B | 73.01 | 89.59 | 66.53 | 71.65 | 76.02 | 61.28 |
| 专用 VLM | Deepseek-OCR [21] | 3B | 73.99 | 86.17 | 67.20 | 75.31 | 78.10 | 63.01 |
| 专用 VLM | MinerU2-VLM [22] | 0.9B | 76.95 | 83.60 | 73.73 | 78.77 | 80.51 | 68.16 |
| 专用 VLM | MonkeyOCR-pro-3B [23] | 3.7B | 79.49 | 86.94 | 78.90 | 82.44 | 84.71 | 64.47 |
| 专用 VLM | Nanonets-OCR-s [24] | 3B | 84.19 | 85.52 | 83.56 | 84.86 | 85.01 | 81.98 |
| 专用 VLM | dots.ocr [25] | 3B | 86.38 | 86.87 | 86.01 | 87.18 | 87.57 | 84.27 |
| 专用 VLM | PaddleOCR-VL [26] | 0.9B | 85.54 | 92.11 | 85.97 | 82.54 | 89.61 | 77.47 |
| 专用 VLM | MinerU2.5 [27] | 1.2B | 85.61 | 90.06 | 83.76 | 89.41 | 89.57 | 75.24 |
| 专用 VLM | MinerU2.5-Pro [28] | 1.2B | 88.96 | 92.11 | 88.72 | <u>92.29</u> | 91.42 | 81.26 |
| 专用 VLM | GLM-OCR [29] | 0.9B | 90.32 | 92.67 | 90.68 | 91.75 | 91.12 | 85.39 |
| 专用 VLM | PaddleOCR-VL-1.5 [30] | 0.9B | <u>92.05</u> | <u>93.43</u> | <u>91.25</u> | 91.76 | <u>92.16</u> | <u>91.66</u> |
| 专用 VLM | PaddleOCR-VL-1.6 [31] | 0.9B | **93.19** | **94.74** | **92.48** | **92.78** | **93.28** | **92.66** |

在通用 VLM 类别中，Gemini-3 Pro 在保持语义连贯性方面表现稳定。尽管 Qwen3-VL-235B 在翘曲场景中表现出特定优势（89.99%），但其在屏幕翻拍（89.27%）和倾斜（86.56%）任务中的表现存在波动。这些波动表明，增加参数规模主要提升字符识别准确率，但未必能从根本上解决三维透视变换带来的几何歧义。相比之下，传统流水线工具对环境变化更加敏感。例如，与扫描结果相比，PP-StructureV3 和 Marker-1.8.2 在倾斜场景中均出现明显下降，主要原因是基于启发式的版面分析通常难以应对大角度透视畸变。

#### 5.2 场景级诊断分析

为细粒度量化模型鲁棒性，我们将评估分解为四个关键子任务：全文 OCR（$\mathrm{Text}^{E}$）、公式识别（$\mathrm{Formula}^{\mathrm{CDM}}$）、表格重建（$\mathrm{Table}^{\mathrm{TEDS}}$）以及阅读顺序一致性（$\mathrm{RO}^{E}$）。这一多维分析有助于识别模型在不同物理伪影下的具体失败机制，超越简单的准确率指标，理解结构与语义保真度。

**扫描与翘曲：几何变形对结构的影响。** 扫描场景（表 2）反映了文档平整、照明均匀时的理想性能上界。专用 VLM 的字符级精确程度与原生数字基准几乎相同。然而，在翘曲场景（表 3）中，非刚性变形引入复杂的曲线畸变，干扰基于坐标的解析。我们的分析表明，虽然通用 VLM 保持较高识别率，但其结构保真度（TEDS）的下降通常比 PaddleOCR-VL-1.6 更明显。这说明纸张曲率会改变文本行之间的空间关系，而经过几何鲁棒性增强的模型，能够在畸变视觉输入中更好地锚定单元格边界和公式组成部分。

**表 2：子任务：扫描。**

| 方法 | Overall↑ | $\mathrm{Text}^{E}$↓ | CDM↑ | TEDS↑ | $\mathrm{RO}^{E}$↓ |
|---|---:|---:|---:|---:|---:|
| PP-StructureV3 [14] | 84.68 | 0.094 | 84.34 | 79.06 | 0.092 |
| Marker-1.8.2 [13] | 70.27 | 0.223 | 77.03 | 56.05 | 0.238 |
| Qwen3-VL-235B [18] | 89.43 | 0.059 | 89.01 | 85.19 | 0.066 |
| Gemini-3 Pro [6] | 89.47 | 0.071 | 88.16 | 87.37 | 0.078 |
| MinerU2.5-Pro [28] | 92.11 | <u>0.040</u> | 89.77 | 90.57 | **0.043** |
| GLM-OCR [29] | <u>92.67</u> | 0.054 | <u>91.10</u> | <u>92.28</u> | <u>0.061</u> |
| PaddleOCR-VL-1.6 [31] | **94.74** | **0.036** | **93.65** | **94.12** | **0.043** |

**表 3：子任务：翘曲。**

| 方法 | Overall↑ | $\mathrm{Text}^{E}$↓ | CDM↑ | TEDS↑ | $\mathrm{RO}^{E}$↓ |
|---|---:|---:|---:|---:|---:|
| PP-StructureV3 [14] | 59.34 | 0.376 | 68.22 | 47.40 | 0.261 |
| Marker-1.8.2 [13] | 58.98 | 0.349 | 72.71 | 39.08 | 0.390 |
| Qwen3-VL-235B [18] | 89.99 | <u>0.051</u> | 89.06 | 85.95 | <u>0.064</u> |
| Gemini-3 Pro [6] | 88.90 | 0.086 | 88.10 | 87.20 | 0.087 |
| MinerU2.5-Pro [28] | 88.72 | 0.100 | 87.81 | 88.36 | 0.076 |
| GLM-OCR [29] | <u>90.68</u> | 0.071 | <u>90.30</u> | <u>88.78</u> | 0.100 |
| PaddleOCR-VL-1.6 [31] | **92.48** | **0.049** | **91.63** | **90.66** | **0.061** |

**屏幕翻拍与光照：光学伪影与一致性。** 光学干扰仍然是真实世界文档智能的重要瓶颈。屏幕翻拍中的摩尔纹（表 4）和光照场景中的局部过曝（表 5），经常在传统系统中触发“版面碎片化”。我们的实验表明，基于流水线的工具经常将反光误认为结构边界，导致阅读顺序（$\mathrm{RO}^{E}$）得分急剧下降。相比之下，PaddleOCR-VL-1.6 展现出更强的视觉一致性。通过在多任务训练中整合多样化的光照增强数据，模型学会利用全局上下文线索，即使局部视觉对比度受损，也能保持解析精度。

**表 4：子任务：屏幕翻拍。**

| 方法 | Overall↑ | $\mathrm{Text}^{E}$↓ | CDM↑ | TEDS↑ | $\mathrm{RO}^{E}$↓ |
|---|---:|---:|---:|---:|---:|
| PP-StructureV3 [14] | 66.89 | 0.204 | 73.26 | 47.82 | 0.165 |
| Marker-1.8.2 [13] | 63.65 | 0.290 | 72.73 | 47.21 | 0.325 |
| Qwen3-VL-235B [18] | 89.27 | 0.068 | 88.72 | 85.85 | 0.071 |
| Gemini-3 Pro [6] | 88.86 | 0.084 | 87.33 | 87.65 | 0.087 |
| MinerU2.5-Pro [28] | 91.29 | <u>0.050</u> | 87.41 | 91.44 | **0.044** |
| GLM-OCR [29] | <u>91.75</u> | 0.063 | <u>89.83</u> | <u>91.66</u> | 0.071 |
| PaddleOCR-VL-1.6 [31] | **92.78** | **0.045** | **90.64** | **92.19** | <u>0.054</u> |

**表 5：子任务：光照。**

| 方法 | Overall↑ | $\mathrm{Text}^{E}$↓ | CDM↑ | TEDS↑ | $\mathrm{RO}^{E}$↓ |
|---|---:|---:|---:|---:|---:|
| PP-StructureV3 [14] | 73.38 | 0.158 | 77.75 | 58.19 | 0.126 |
| Marker-1.8.2 [13] | 66.31 | 0.259 | 74.80 | 50.03 | 0.337 |
| Qwen3-VL-235B [18] | 89.27 | 0.060 | 87.81 | 86.05 | 0.070 |
| Gemini-3 Pro [6] | 89.53 | 0.073 | 87.78 | 88.14 | 0.080 |
| MinerU2.5-Pro [28] | <u>91.31</u> | <u>0.050</u> | 88.15 | <u>90.76</u> | <u>0.053</u> |
| GLM-OCR [29] | 91.12 | 0.059 | <u>91.02</u> | 88.20 | 0.071 |
| PaddleOCR-VL-1.6 [31] | **93.28** | **0.042** | **92.61** | **91.48** | **0.051** |

**倾斜：透视校正与阅读顺序恢复。** 倾斜场景（表 6）是本基准中要求最严苛的任务之一，测试三维到二维投影恢复的极限。大角度透视倾斜会产生“行压缩”效应，使原本平行的文本行看起来汇聚或重叠。依赖轴对齐投影的传统系统容易产生严重的序列错误。实验数据表明，PaddleOCR-VL-1.6 保持了稳健的 0.058 的 $\mathrm{RO}^{E}$，优于若干大型通用模型。这一表现表明，模型已经内化了对透视线索的灵活映射，即使视觉版面严重倾斜，也能准确重建文档的逻辑流。

**表 6：倾斜场景下的详细性能分解。**

| 方法 | Overall↑ | $\mathrm{Text}^{E}$↓ | CDM↑ | TEDS↑ | $\mathrm{RO}^{E}$↓ |
|---|---:|---:|---:|---:|---:|
| PP-StructureV3 [14] | 37.98 | 0.557 | 44.37 | 25.27 | 0.417 |
| Marker-1.8.2 [13] | 41.27 | 0.536 | 60.16 | 17.23 | 0.543 |
| Qwen3-VL-235B [18] | 86.56 | <u>0.077</u> | 83.96 | 83.41 | <u>0.091</u> |
| Gemini-3 Pro [6] | <u>89.45</u> | 0.080 | <u>88.33</u> | <u>88.06</u> | 0.092 |
| MinerU2.5-Pro [28] | 81.26 | 0.212 | 83.92 | 81.07 | 0.107 |
| GLM-OCR [29] | 85.39 | 0.099 | 85.78 | 80.28 | 0.156 |
| PaddleOCR-VL-1.6 [31] | **92.66** | **0.045** | **91.44** | **91.04** | **0.058** |

### 6 讨论

**关于领域差距与鲁棒性的认识。** 对 Real5-Omni-DocBench 的系统评估表明，当模型从原生数字环境转向物理世界采集图像时，性能出现明显退化。结果显示，尽管大型通用 VLM 具有强大的语义先验，但其对非刚性几何变换（如翘曲）的零样本迁移能力与参数规模并不严格相关。这说明当前瓶颈与其说是语言建模，不如说是随机畸变下的视觉特征对齐。这一“现实差距”的持续存在，强调了评估鲁棒性的基准需要超越标准准确率，聚焦三维视觉与文档分析的交叉领域。

**专用架构与通用架构的有效性。** 我们的结果为架构选择提供了更细致的视角。尽管通用 VLM 在开放领域的连贯性方面表现出更强的适应能力，但针对多任务解析优化的专用模型，在资源受限条件下通常具有更高的结构保真度。紧凑架构的竞争性表现说明，在高质量增强数据上进行领域特定微调，可以有效弥补参数数量较少的不足。相反，传统流水线工具在倾斜和光照条件下的失败，凸显了启发式系统的局限，支持采用将光学校正与结构解析联合优化的统一端到端架构。

### 7 结论

本文提出 Real5-OmniDocBench，这是一个在五种真实场景中评估文档解析鲁棒性的综合基准。通过基于 OmniDocBench v1.5 语料重建 1,355 张高保真图像，我们提供了一个标准化平台，用于评估物理伪影如何影响模型性能。

我们的基准评估揭示了当前解析技术的显著脆弱性，尤其是在复杂三维畸变和局部光照变化方面。结果表明，尽管紧凑的专用模型能够实现较高效率，但距离普遍适用的鲁棒性仍有很大提升空间。我们希望 Real5-OmniDocBench 能够推动更具韧性的模型研究，使其能够处理实际应用固有的复杂性。

### 参考文献

[1] Linke Ouyang, Yuan Qu, Hongbin Zhou, Jiawei Zhu, Rui Zhang, Qunshu Lin, Bin Wang, Zhiyuan Zhao, Man Jiang, Xiaomeng Zhao, Jin Shi, Fan Wu, Pei Chu, Minghao Liu, Zhenxiang Li, Chao Xu, Bo Zhang, Botian Shi, Zhongying Tu, and Conghui He. Omnidocbench: Benchmarking diverse pdf document parsing with comprehensive annotations（OmniDocBench：通过全面标注对多样化 PDF 文档解析进行基准评估）, 2024. 网址：https://arxiv.org/abs/2412.07626.

[2] An-Lan Wang, Jingqun Tang, Liao Lei, Hao Feng, Qi Liu, Xiang Fei, Jinghui Lu, Han Wang, Weiwei Liu, Hao Liu, Yuliang Liu, Xiang Bai, and Can Huang. Wilddoc: How far are we from achieving comprehensive and robust document understanding in the wild?（WildDoc：距离实现全面、鲁棒的真实场景文档理解还有多远？）, 2025. 网址：https://arxiv.org/abs/2505.11015.

[3] Yongkun Du, Pinxuan Chen, Xuye Ying, and Zhineng Chen. Docptbench: Benchmarking end-to-end photographed document parsing and translation（DocPTBench：端到端拍摄文档解析与翻译的基准评估）, 2025. 网址：https://arxiv.org/abs/2511.18434.

[4] Zheng Huang, Kai Chen, Jianhua He, Xiang Bai, Dimosthenis Karatzas, Shijian Lu, and CV Jawahar. Icdar2019 competition on scanned receipt ocr and information extraction（ICDAR2019 扫描收据 OCR 与信息提取竞赛）. 载于 2019 International Conference on Document Analysis and Recognition (ICDAR)（2019 年国际文档分析与识别会议），第 1516–1520 页. IEEE, 2019.

[5] Shuai Bai, Yuxuan Cai, Ruizhe Chen, Keqin Chen, Xionghui Chen, Zesen Cheng, Lianghao Deng, Wei Ding, Chang Gao, Chunjiang Ge, Wenbin Ge, Zhifang Guo, Qidong Huang, Jie Huang, Fei Huang, Binyuan Hui, Shutong Jiang, Zhaohai Li, Mingsheng Li, Mei Li, Kaixin Li, Zicheng Lin, Junyang Lin, Xuejing Liu, Jiawei Liu, Chenglong Liu, Yang Liu, Dayiheng Liu, Shixuan Liu, Dunjie Lu, Ruilin Luo, Chenxu Lv, Rui Men, Lingchen Meng, Xuancheng Ren, Xingzhang Ren, Sibo Song, Yuchong Sun, Jun Tang, Jianhong Tu, Jianqiang Wan, Peng Wang, Pengfei Wang, Qiuyue Wang, Yuxuan Wang, Tianbao Xie, Yiheng Xu, Haiyang Xu, Jin Xu, Zhibo Yang, Mingkun Yang, Jianxin Yang, An Yang, Bowen Yu, Fei Zhang, Hang Zhang, Xi Zhang, Bo Zheng, Humen Zhong, Jingren Zhou, Fan Zhou, Jing Zhou, Yuanzhi Zhu, and Ke Zhu. Qwen3-vl technical report（Qwen3-VL 技术报告）, 2025. 网址：https://arxiv.org/abs/2511.21631.

[6] Google DeepMind. Gemini 3.0（Gemini 3.0）. https://blog.google/products-and-platforms/products/gemini/gemini-3-collection/, 2025.

[7] Jake Poznanski, Jon Borchardt, Jason Dunkelberger, Regan Huff, Daniel Lin, Aman Rangapur, Christopher Wilhelm, Kyle Lo, and Luca Soldaini. olmOCR: Unlocking Trillions of Tokens in PDFs with Vision Language Models（olmOCR：利用视觉语言模型释放 PDF 中的万亿级 token）, 2025. 网址：https://arxiv.org/abs/2502.18443.

[8] Song Chen, Xinyu Guo, Yadong Li, Tao Zhang, Mingan Lin, Dongdong Kuang, Youwei Zhang, Lingfeng Ming, Fengyu Zhang, Yuran Wang, Jianhua Xu, Zenan Zhou, and Weipeng Chen. Ocean-ocr: Towards general ocr application via a vision-language model（Ocean-OCR：通过视觉语言模型迈向通用 OCR 应用）, 2025. 网址：https://arxiv.org/abs/2501.15558.

[9] Jiaxin Zhang, Dezhi Peng, Chongyu Liu, Peirong Zhang, and Lianwen Jin. Docres: A generalist model toward unifying document image restoration tasks（DocRes：面向统一文档图像恢复任务的通用模型）. 载于 Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition（IEEE/CVF 计算机视觉与模式识别会议论文集），第 15654–15664 页, 2024.

[10] Ling Fu, Zhebin Kuang, Jiajun Song, Mingxin Huang, Biao Yang, Yuzhe Li, Linghao Zhu, Qidi Luo, Xinyu Wang, Hao Lu, Zhang Li, Guozhi Tang, Bin Shan, Chunhui Lin, Qi Liu, Binghong Wu, Hao Feng, Hao Liu, Can Huang, Jingqun Tang, Wei Chen, Lianwen Jin, Yuliang Liu, and Xiang Bai. Ocrbench v2: An improved benchmark for evaluating large multimodal models on visual text localization and reasoning（OCRBench v2：用于评估大型多模态模型视觉文本定位与推理的改进基准）, 2025. 网址：https://arxiv.org/abs/2501.00321.

[11] Bin Wang, Fan Wu, Linke Ouyang, Zhuangcheng Gu, Rui Zhang, Renqiu Xia, Botian Shi, Bo Zhang, and Conghui He. Image over text: Transforming formula recognition evaluation with character detection matching（图像优于文本：利用字符检测匹配变革公式识别评估）. 载于 Proceedings of the Computer Vision and Pattern Recognition Conference（计算机视觉与模式识别会议论文集），第 19681–19690 页, 2025.

[12] Xu Zhong, Elaheh ShafieiBavani, and Antonio Jimeno Yepes. Image-based table recognition: data, model, and evaluation（基于图像的表格识别：数据、模型与评估）. 载于 European conference on computer vision（欧洲计算机视觉会议），第 564–580 页. Springer, 2020.

[13] Vik Paruchuri. Marker（Marker）. https://github.com/datalab-to/marker, 2025. 访问日期： 2025-09-25.

[14] Cheng Cui, Ting Sun, Manhui Lin, Tingquan Gao, Yubo Zhang, Jiaxuan Liu, Xueqing Wang, Zelun Zhang, Changda Zhou, Hongen Liu, Yue Zhang, Wenyu Lv, Kui Huang, Yichao Zhang, Jing Zhang, Jun Zhang, Yi Liu, Dianhai Yu, and Yanjun Ma. Paddleocr 3.0 technical report（PaddleOCR 3.0 技术报告）, 2025. 网址：https://arxiv.org/abs/2507.05595.

[15] OpenAI. Gpt-5.2 system card（GPT-5.2 系统卡）, 2025. 网址：https://cdn.openai.com/pdf/3a4153c8-c748-4b71-8e31-aecbde944f8d/oai_5_2_system-card.pdf.

[16] Shuai Bai, Keqin Chen, Xuejing Liu, Jialin Wang, Wenbin Ge, Sibo Song, Kai Dang, Peng Wang, Shijie Wang, Jun Tang, Humen Zhong, Yuanzhi Zhu, Mingkun Yang, Zhaohai Li, Jianqiang Wan, Pengfei Wang, Wei Ding, Zheren Fu, Yiheng Xu, Jiabo Ye, Xi Zhang, Tianbao Xie, Zesen Cheng, Hang Zhang, Zhibo Yang, Haiyang Xu, and Junyang Lin. Qwen2.5-vl technical report（Qwen2.5-VL 技术报告）, 2025. 网址：https://arxiv.org/abs/2502.13923.

[17] Google DeepMind. Gemini 2.5（Gemini 2.5）. https://blog.google/technology/google-deepmind/gemini-model-thinking-updates-march-2025/, 2025.

[18] An Yang, Anfeng Li, Baosong Yang, Beichen Zhang, Binyuan Hui, Bo Zheng, Bowen Yu, Chang Gao, Chengen Huang, Chenxu Lv, Chujie Zheng, Dayiheng Liu, Fan Zhou, Fei Huang, Feng Hu, Hao Ge, Haoran Wei, Huan Lin, Jialong Tang, Jian Yang, Jianhong Tu, Jianwei Zhang, Jianxin Yang, Jiaxi Yang, Jing Zhou, Jingren Zhou, Junyang Lin, Kai Dang, Keqin Bao, Kexin Yang, Le Yu, Lianghao Deng, Mei Li, Mingfeng Xue, Mingze Li, Pei Zhang, Peng Wang, Qin Zhu, Rui Men, Ruize Gao, Shixuan Liu, Shuang Luo, Tianhao Li, Tianyi Tang, Wenbiao Yin, Xingzhang Ren, Xinyu Wang, Xinyu Zhang, Xuancheng Ren, Yang Fan, Yang Su, Yichang Zhang, Yinger Zhang, Yu Wan, Yuqiong Liu, Zekun Wang, Zeyu Cui, Zhenru Zhang, Zhipeng Zhou, and Zihan Qiu. Qwen3 technical report（Qwen3 技术报告）, 2025. 网址：https://arxiv.org/abs/2505.09388.

[19] Kimi Team, Tongtong Bai, Yifan Bai, Yiping Bao, S. H. Cai, Yuan Cao, Y. Charles, H. S. Che, Cheng Chen, Guanduo Chen, Huarong Chen, Jia Chen, Jiahao Chen, Jianlong Chen, Jun Chen, Kefan Chen, Liang Chen, Ruijue Chen, Xinhao Chen, Yanru Chen, Yanxu Chen, Yicun Chen, Yimin Chen, Yingjiang Chen, Yuankun Chen, Yujie Chen, Yutian Chen, Zhirong Chen, Ziwei Chen, Dazhi Cheng, Minghan Chu, Jialei Cui, Jiaqi Deng, Muxi Diao, Hao Ding, Mengfan Dong, Mengnan Dong, Yuxin Dong, Yuhao Dong, Angang Du, Chenzhuang Du, Dikang Du, Lingxiao Du, Yulun Du, Yu Fan, Shengjun Fang, Qiulin Feng, Yichen Feng, Garimugai Fu, Kelin Fu, Hongcheng Gao, Tong Gao, Yuyao Ge, Shangyi Geng, Chengyang Gong, Xiaochen Gong, Zhuoma Gongque, Qizheng Gu, Xinran Gu, Yicheng Gu, Longyu Guan, Yuanying Guo, Xiaoru Hao, Weiran He, Wenyang He, Yunjia He, Chao Hong, Hao Hu, Jiaxi Hu, Yangyang Hu, Zhenxing Hu, Ke Huang, Ruiyuan Huang, Weixiao Huang, Zhiqi Huang, Tao Jiang, Zhejun Jiang, Xinyi Jin, Yu Jing, Guokun Lai, Aidi Li, C. Li, Cheng Li, Fang Li, Guanghe Li, Guanyu Li, Haitao Li, Haoyang Li, Jia Li, Jingwei Li, Junxiong Li, Lincan Li, Mo Li, Weihong Li, Wentao Li, Xinhang Li, Xinhao Li, Yang Li, Yanhao Li, Yiwei Li, Yuxiao Li, Zhaowei Li, Zheming Li, Weilong Liao, Jiawei Lin, Xiaohan Lin, Zhishan Lin, Zichao Lin, Cheng Liu, Chenyu Liu, Hongzhang Liu, Liang Liu, Shaowei Liu, Shudong Liu, Shuran Liu, Tianwei Liu, Tianyu Liu, Weizhou Liu, Xiangyan Liu, Yangyang Liu, Yanming Liu, Yibo Liu, Yuanxin Liu, Yue Liu, Zhengying Liu, Zhongnuo Liu, Enzhe Lu, Haoyu Lu, Zhiyuan Lu, Junyu Luo, Tongxu Luo, Yashuo Luo, Long Ma, Yingwei Ma, Shaoguang Mao, Yuan Mei, Xin Men, Fanqing Meng, Zhiyong Meng, Yibo Miao, Minqing Ni, Kun Ouyang, Siyuan Pan, Bo Pang, Yuchao Qian, Ruoyu Qin, Zeyu Qin, Jiezhong Qiu, Bowen Qu, Zeyu Shang, Youbo Shao, Tianxiao Shen, Zhennan Shen, Juanfeng Shi, Lidong Shi, Shengyuan Shi, Feifan Song, Pengwei Song, Tianhui Song, Xiaoxi Song, Hongjin Su, Jianlin Su, Zhaochen Su, Lin Sui, Jinsong Sun, Junyao Sun, Tongyu Sun, Flood Sung, Yunpeng Tai, Chuning Tang, Heyi Tang, Xiaojuan Tang, Zhengyang Tang, Jiawen Tao, Shiyuan Teng, Chaoran Tian, Pengfei Tian, Ao Wang, Bowen Wang, Chensi Wang, Chuang Wang, Congcong Wang, Dingkun Wang, Dinglu Wang, Dongliang Wang, Feng Wang, Hailong Wang, Haiming Wang, Hengzhi Wang, Huaqing Wang, Hui Wang, Jiahao Wang, Jinhong Wang, Jiuzheng Wang, Kaixin Wang, Linian Wang, Qibin Wang, Shengjie Wang, Shuyi Wang, Si Wang, Wei Wang, Xiaochen Wang, Xinyuan Wang, Yao Wang, Yejie Wang, Yipu Wang, Yiqin Wang, Yucheng Wang, Yuzhi Wang, Zhaoji Wang, Zhaowei Wang, Zhengtao Wang, Zhexu Wang, Zihan Wang, Zizhe Wang, Chu Wei, Ming Wei, Chuan Wen, Zichen Wen, Chengjie Wu, Haoning Wu, Junyan Wu, Rucong Wu, Wenhao Wu, Yuefeng Wu, Yuhao Wu, Yuxin Wu, Zijian Wu, Chenjun Xiao, Jin Xie, Xiaotong Xie, Yuchong Xie, Yifei Xin, Bowei Xing, Boyu Xu, Jianfan Xu, Jing Xu, Jinjing Xu, L. H. Xu, Lin Xu, Suting Xu, Weixin Xu, Xinbo Xu, Xinran Xu, Yangchuan Xu, Yichang Xu, Yuemeng Xu, Zelai Xu, Ziyao Xu, Junjie Yan, Yuzi Yan, Guangyao Yang, Hao Yang, Junwei Yang, Kai Yang, Ningyuan Yang, Ruihan Yang, Xiaofei Yang, Xinlong Yang, Ying Yang, Yi Yang, Yi Yang, Zhen Yang, Zhilin Yang, Zonghan Yang, Haotian Yao, Dan Ye, Wenjie Ye, Zhuorui Ye, Bohong Yin, Chengzhen Yu, Longhui Yu, Tao Yu, Tianxiang Yu, Enming Yuan, Mengjie Yuan, Xiaokun Yuan, Yang Yue, Weihao Zeng, Dunyuan Zha, Haobing Zhan, Dehao Zhang, Hao Zhang, Jin Zhang, Puqi Zhang, Qiao Zhang, Rui Zhang, Xiaobin Zhang, Y. Zhang, Yadong Zhang, Yangkun Zhang, Yichi Zhang, Yizhi Zhang, Yongting Zhang, Yu Zhang, Yushun Zhang, Yutao Zhang, Yutong Zhang, Zheng Zhang, Chenguang Zhao, Feifan Zhao, Jinxiang Zhao, Shuai Zhao, Xiangyu Zhao, Yikai Zhao, Zijia Zhao, Huabin Zheng, Ruihan Zheng, Shaojie Zheng, Tengyang Zheng, Junfeng Zhong, Longguang Zhong, Weiming Zhong, M. Zhou, Runjie Zhou, Xinyu Zhou, Zaida Zhou, Jinguo Zhu, Liya Zhu, Xinhao Zhu, Yuxuan Zhu, Zhen Zhu, Jingze Zhuang, Weiyu Zhuang, Ying Zou, and Xinxing Zu. Kimi k2.5: Visual agentic intelligence（Kimi K2.5：视觉智能体智能）, 2026. 网址：https://arxiv.org/abs/2602.02276.

[20] Haoran Wei, Yaofeng Sun, and Yukun Li. Deepseek-ocr 2: Visual causal flow（DeepSeek-OCR 2：视觉因果流）, 2026. 网址：https://arxiv.org/abs/2601.20552.

[21] Haoran Wei, Yaofeng Sun, and Yukun Li. Deepseek-ocr: Contexts optical compression（DeepSeek-OCR：上下文光学压缩）, 2025. 网址：https://arxiv.org/abs/2510.18234.

[22] opendatalab. Mineru2.0-2505-0.9b（MinerU2.0-2505-0.9B）. https://huggingface.co/opendatalab/MinerU2.0-2505-0.9B, 2025.

[23] Zhang Li, Yuliang Liu, Qiang Liu, Zhiyin Ma, Ziyang Zhang, Shuo Zhang, Biao Yang, Zidun Guo, Jiarui Zhang, Xinyu Wang, and Xiang Bai. Monkeyocr: Document parsing with a structure-recognition-relation triplet paradigm（MonkeyOCR：采用结构–识别–关系三元组范式的文档解析）, 2026. 网址：https://arxiv.org/abs/2506.05218.

[24] Souvik Mandal, Ashish Talewar, Paras Ahuja, and Prathamesh Juvatkar. Nanonets-ocr-s: A model for transforming documents into structured markdown with intelligent content recognition and semantic tagging（Nanonets-OCR-s：通过智能内容识别与语义标注将文档转换为结构化 Markdown 的模型）, 2025.

[25] Yumeng Li, Guang Yang, Hao Liu, Bowen Wang, and Colin Zhang. dots.ocr: Multilingual document layout parsing in a single vision-language model（dots.ocr：通过单一视觉语言模型实现多语言文档版面解析）, 2025. 网址：https://arxiv.org/abs/2512.02498.

[26] Cheng Cui, Ting Sun, Suyin Liang, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Xueqing Wang, Changda Zhou, Hongen Liu, Manhui Lin, Yue Zhang, Yubo Zhang, Handong Zheng, Jing Zhang, Jun Zhang, Yi Liu, Dianhai Yu, and Yanjun Ma. Paddleocr-vl: Boosting multilingual document parsing via a 0.9b ultra-compact vision-language model（PaddleOCR-VL：通过 0.9B 超紧凑视觉语言模型提升多语言文档解析）, 2025. 网址：https://arxiv.org/abs/2510.14528.

[27] Junbo Niu, Zheng Liu, Zhuangcheng Gu, Bin Wang, Linke Ouyang, Zhiyuan Zhao, Tao Chu, Tianyao He, Fan Wu, Qintong Zhang, Zhenjiang Jin, Guang Liang, Rui Zhang, Wenzheng Zhang, Yuan Qu, Zhifei Ren, Yuefeng Sun, Yuanhong Zheng, Dongsheng Ma, Zirui Tang, Boyu Niu, Ziyang Miao, Hejun Dong, Siyi Qian, Junyuan Zhang, Jingzhou Chen, Fangdong Wang, Xiaomeng Zhao, Liqun Wei, Wei Li, Shasha Wang, Ruiliang Xu, Yuanyuan Cao, Lu Chen, Qianqian Wu, Huaiyu Gu, Lindong Lu, Keming Wang, Dechen Lin, Guanlin Shen, Xuanhe Zhou, Linfeng Zhang, Yuhang Zang, Xiaoyi Dong, Jiaqi Wang, Bo Zhang, Lei Bai, Pei Chu, Weijia Li, Jiang Wu, Lijun Wu, Zhenxiang Li, Guangyu Wang, Zhongying Tu, Chao Xu, Kai Chen, Yu Qiao, Bowen Zhou, Dahua Lin, Wentao Zhang, and Conghui He. Mineru2.5: A decoupled vision-language model for efficient high-resolution document parsing（MinerU2.5：用于高效高分辨率文档解析的解耦视觉语言模型）, 2025. 网址：https://arxiv.org/abs/2509.22186.

[28] Bin Wang, Tianyao He, Linke Ouyang, Fan Wu, Zhiyuan Zhao, Tao Chu, Yuan Qu, Zhenjiang Jin, Weijun Zeng, Ziyang Miao, et al. Mineru2. 5-pro: Pushing the limits of data-centric document parsing at scale（MinerU2.5-Pro：突破大规模数据驱动文档解析的极限）. arXiv 预印本 arXiv:2604.04771, 2026.

[29] zai-org. Glm-ocr（GLM-OCR）. https://huggingface.co/zai-org/GLM-OCR, 2026.

[30] Cheng Cui, Ting Sun, Suyin Liang, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Xueqing Wang, Changda Zhou, Hongen Liu, Manhui Lin, Yue Zhang, Yubo Zhang, Yi Liu, Dianhai Yu, and Yanjun Ma. Paddleocr-vl-1.5: Towards a multi-task 0.9b vlm for robust in-the-wild document parsing（PaddleOCR-VL-1.5：迈向用于鲁棒真实场景文档解析的多任务 0.9B VLM）, 2026. 网址：https://arxiv.org/abs/2601.21957.

[31] Zelun Zhang, Hongen Liu, Suyin Liang, Yubo Zhang, Yiqing Xiang, Jiaxuan Liu, Ting Sun, Manhui Lin, Yue Zhang, Changda Zhou, Tingquan Gao, Cheng Cui, Yi Liu, Dianhai Yu, and Yanjun Ma. Paddleocr-vl-1.6: Expanding the frontier of document parsing with under-optimized region refinement and progressive post-training（PaddleOCR-VL-1.6：通过欠优化区域细化与渐进式后训练拓展文档解析前沿）, 2026. 网址：https://arxiv.org/abs/2606.03264.
