# 基于 Transformer 的端到端目标检测（End-to-End Object Detection with Transformers）

Nicolas Carion$^{1,2}$ [0000-0002-2308-9680]，Francisco Massa$^2$ [0000-0003-0697-6664]，Gabriel Synnaeve$^2$ [0000-0003-1715-3356]，Nicolas Usunier$^2$ [0000-0002-9324-1457]，Alexander Kirillov$^2$ [0000-0003-3169-3199]，Sergey Zagoruyko$^2$ [0000-0001-9684-5240]

$^1$ 巴黎多芬大学（Paris Dauphine University）  
$^2$ Facebook AI

{alcinos, fmassa, gab, usunier, akirillov, szagoruyko}@fb.com

## 摘要

我们提出了一种将目标检测（Object Detection）视为直接集合预测（direct set prediction）问题的新方法。我们的方法简化了检测流程，有效消除了对许多人工设计组件的需求，例如非极大值抑制（Non-Maximum Suppression，NMS）过程或锚框生成（anchor generation），这些组件显式编码了我们对于该任务的先验知识。这个新框架称为 DEtection TRansformer（DETR），其主要组成部分包括：一种基于集合的全局损失，通过二分图匹配（bipartite matching）强制实现唯一预测；以及一种 Transformer 编码器—解码器（encoder-decoder）架构。给定一个固定的小规模可学习目标查询（object queries）集合，DETR 对目标之间的关系以及全局图像上下文进行推理，从而直接并行输出最终的预测集合。与许多其他现代检测器不同，这一新模型在概念上十分简单，并且不需要专门的程序库。在具有挑战性的 COCO 目标检测数据集上，DETR 展现出了与成熟且经过高度优化的 Faster R-CNN 基线相当的准确率和运行时性能。此外，DETR 还可以很容易地以统一方式推广到全景分割（Panoptic Segmentation）任务。我们表明，它显著优于具有竞争力的基线方法。训练代码和预训练模型可在以下地址获取：

https://github.com/facebookresearch/detr

# 1 引言

目标检测的目标是为每一个感兴趣的目标预测一组边界框（bounding boxes）和类别标签。现代检测器以一种间接的方式处理这一集合预测任务，即在大量候选框（proposals）[36, 5]、锚框（anchors）[22] 或窗口中心（window centers）[52, 45] 上定义替代性的回归和分类问题。这些方法的性能会受到多个因素的显著影响，包括：用于合并近似重复预测的后处理步骤、锚框集合的设计，以及将目标边界框分配给锚框的启发式规则 [51]。为了简化这些流程，我们提出了一种直接集合预测方法，从而绕过这些替代任务。这样的端到端思想已经在机器翻译和语音识别等复杂结构化预测任务中带来了显著进展，但在目标检测领域尚未取得同样的成果：此前的尝试 [42, 15, 4, 38] 要么加入了其他形式的先验知识，要么尚未证明其在具有挑战性的基准测试上能够与强基线方法竞争。本文旨在弥合这一差距。

> **图 1.** DETR 将常规卷积神经网络（Convolutional Neural Network，CNN）与 Transformer 架构相结合，直接并行预测最终的检测结果集合。在训练过程中，二分图匹配将预测结果唯一地分配给真实边界框。没有匹配到真实目标的预测应输出“无目标”（no object，$\varnothing$）类别。

我们通过将目标检测视为一个直接集合预测问题来简化训练流程。我们采用了一种基于 Transformer [46] 的编码器—解码器架构，Transformer 是一种广泛用于序列预测的架构。Transformer 的自注意力（self-attention）机制能够显式建模序列中所有元素之间的两两交互，因此，这类架构特别适合处理集合预测中的特定约束，例如消除重复预测。

我们的 DEtection TRansformer（DETR，见图 1）能够一次性预测所有目标，并通过一种集合损失函数进行端到端训练，该损失函数在预测目标与真实目标之间执行二分图匹配。DETR 去除了多个用于编码先验知识的人工设计组件，例如空间锚框（spatial anchors）和非极大值抑制，从而简化了检测流程。与大多数现有检测方法不同，DETR 不需要任何定制层，因此，只要一个框架中包含标准的 ResNet [14] 和 Transformer [46] 类，就可以轻松复现 DETR。

与此前大多数直接集合预测工作相比，DETR 的主要特征是将二分图匹配损失与采用（非自回归）并行解码 [28, 11, 9, 7] 的 Transformer 相结合。相比之下，此前的工作主要关注基于循环神经网络（Recurrent Neural Network，RNN）的自回归解码 [42, 40, 29, 35, 41]。我们的匹配损失函数会将每个预测唯一地分配给一个真实目标，而且对于预测目标的排列具有不变性，因此我们能够并行输出这些预测。

我们在最流行的目标检测数据集之一 COCO [23] 上评估 DETR，并与一个非常具有竞争力的 Faster R-CNN 基线 [36] 进行比较。自 Faster R-CNN 最初发表以来，其设计经历了多次迭代，性能也获得了显著提升。我们的实验表明，新模型能够达到与其相当的性能。更具体地说，DETR 在大型目标上表现明显更好，这一结果可能得益于 Transformer 的非局部计算。然而，它在小型目标上的性能较低。我们预计，未来的工作能够改善这一问题，就像特征金字塔网络（Feature Pyramid Network，FPN）[21] 的发展改善了 Faster R-CNN 一样。

DETR 的训练设置在多个方面不同于标准目标检测器。新模型需要额外长的训练计划，并且能够从 Transformer 中的辅助解码损失中获益。我们对哪些组件对于实现所展示的性能至关重要进行了全面研究。

DETR 的设计理念也可以很容易地扩展到更加复杂的任务。在实验中，我们表明，在预训练 DETR 上训练一个简单的分割头，就能够在全景分割 [18] 上优于具有竞争力的基线方法。全景分割是一项具有挑战性的像素级识别任务，近年来受到了越来越多的关注。

# 2 相关工作

我们的工作建立在多个领域的已有研究之上，包括：用于集合预测的二分图匹配损失、基于 Transformer 的编码器—解码器架构、并行解码，以及目标检测方法。

## 2.1 集合预测（Set Prediction）

目前并不存在一种用于直接预测集合的标准深度学习模型。最基本的集合预测任务是多标签分类（multilabel classification；关于计算机视觉领域中的相关文献，例如参见 [39, 32]）。对于这类任务，常用的一对其余（one-vs-rest）基线方法并不适用于检测等问题，因为这些问题中的元素之间存在潜在结构，例如近乎相同的边界框。

此类任务面临的第一个困难是避免出现近似重复项。当前大多数检测器使用非极大值抑制等后处理方法来解决这一问题，但直接集合预测不采用后处理。它们需要能够对所有预测元素之间的交互进行建模的全局推理机制，以避免冗余。对于固定大小的集合预测，稠密全连接网络 [8] 已经足够，但其计算代价很高。一种通用方法是采用循环神经网络 [47] 等自回归序列模型。

无论采用哪种方法，损失函数都应当对预测结果的排列保持不变。通常的解决方案是设计一种基于匈牙利算法（Hungarian algorithm）[19] 的损失，以寻找真实目标与预测结果之间的二分图匹配。这能够保证排列不变性，并确保每一个目标元素都有唯一的匹配。我们采用了这种二分图匹配损失方法。不过，与此前大多数工作不同，我们不再采用自回归模型，而是使用具有并行解码能力的 Transformer，具体将在下文介绍。

## 2.2 Transformer 与并行解码（Transformers and Parallel Decoding）

Transformer 最初由 Vaswani 等人 [46] 提出，作为一种用于机器翻译的新型基于注意力（attention）的基础模块。注意力机制 [2] 是一种能够从整个输入序列中聚合信息的神经网络层。Transformer 引入了自注意力层，与非局部神经网络（Non-Local Neural Networks）[48] 类似，自注意力会遍历序列中的每一个元素，并通过聚合来自整个序列的信息来更新该元素。

基于注意力的模型的主要优势之一，在于其全局计算能力以及完整的记忆能力，这使得它们在处理长序列时比 RNN 更加合适。目前，在自然语言处理、语音处理和计算机视觉等诸多问题中，Transformer 正在逐步取代 RNN [7, 26, 44, 33, 30]。

Transformer 最初被应用于自回归模型，并沿用了早期序列到序列（sequence-to-sequence）模型 [43] 的方式，即逐个生成输出 token。然而，其高昂的推理成本——与输出长度成正比，并且难以进行批处理——推动了并行序列生成的发展，这一方向已经被应用于音频 [28]、机器翻译 [11, 9]、词表示学习 [7]，以及最近的语音识别 [6]。我们同样将 Transformer 与并行解码相结合，因为这种组合能够在计算成本与执行集合预测所需的全局计算能力之间取得良好的权衡。

## 2.3 目标检测（Object Detection）

大多数现代目标检测方法都相对于某种初始猜测进行预测。两阶段检测器（two-stage detectors）[36, 5] 相对于候选框进行边界框预测，而单阶段方法则相对于锚框 [22] 或潜在目标中心的网格 [52, 45] 进行预测。近期工作 [51] 表明，这些初始猜测具体如何设置会对这些系统的最终性能产生很大影响。在我们的模型中，我们能够去除这一人工设计过程，并直接相对于输入图像预测绝对边界框，而不是相对于某个锚框进行预测，从而简化检测过程。

**基于集合的损失（Set-based loss）。** 一些目标检测器 [8, 24, 34] 曾使用二分图匹配损失。不过，在这些早期的深度学习模型中，不同预测之间的关系仅使用卷积层或全连接层进行建模，而人工设计的 NMS 后处理能够进一步提高它们的性能。较新的检测器 [36, 22, 52] 则采用真实目标与预测之间的非唯一分配规则，并结合 NMS。

可学习 NMS（Learnable NMS）方法 [15, 4] 和关系网络（relation networks）[16] 使用注意力显式建模不同预测之间的关系。由于采用直接集合损失，它们不需要任何后处理步骤。然而，为了高效建模检测结果之间的关系，这些方法使用了额外的人工设计上下文特征，例如候选框坐标；而我们寻求的是减少模型中所编码先验知识的解决方案。

**循环检测器（Recurrent detectors）。** 与我们的方法最接近的是用于目标检测 [42] 和实例分割 [40, 29, 35, 41] 的端到端集合预测方法。与我们类似，它们使用二分图匹配损失，并采用基于 CNN 激活的编码器—解码器架构，直接生成一组边界框。然而，这些方法只在小规模数据集上进行了评估，而且没有与现代基线方法进行比较。特别是，这些方法基于自回归模型——更准确地说，是基于 RNN——因此并未利用最近出现的具有并行解码能力的 Transformer。

# 3 DETR 模型

检测任务中的直接集合预测需要两个关键组成部分：

1. 一种集合预测损失，用于强制预测边界框与真实边界框之间形成唯一匹配；
2. 一种能够在单次前向过程中预测一组目标并对目标之间关系进行建模的架构。

我们的架构在图 2 中进行了详细说明。

## 3.1 目标检测的集合预测损失（Object Detection Set Prediction Loss）

DETR 在一次通过解码器的过程中推断一个固定大小、包含 $N$ 个预测结果的集合，其中 $N$ 被设置为显著大于一幅图像中通常包含的目标数量。训练过程中一个主要困难在于，如何相对于真实标注对预测目标——包括类别、位置和尺寸——进行评分。我们的损失首先在预测目标与真实目标之间生成一个最优二分图匹配，然后优化与具体目标相关的边界框损失。

用 $y$ 表示真实目标集合，用

$\hat{y}=\{\hat{y}_i\}_{i=1}^{N}$

表示由 $N$ 个预测组成的集合。假设 $N$ 大于图像中的目标数量，我们同样将 $y$ 视为一个大小为 $N$ 的集合，并使用 $\varnothing$（无目标）进行填充。为了在这两个集合之间寻找二分图匹配，我们需要在 $N$ 个元素的所有排列 $\sigma\in\mathfrak{S}_N$ 中寻找具有最低代价的排列：

$$
\hat{\sigma}
=
\underset{\sigma\in\mathfrak{S}_N}{\arg\min}
\sum_{i}^{N}
\mathcal{L}_{\mathrm{match}}
\left(
y_i,
\hat{y}_{\sigma(i)}
\right)
\tag{1}
$$

其中，$\mathcal{L}_{\mathrm{match}}(y_i,\hat{y}_{\sigma(i)})$ 表示真实目标 $y_i$ 与索引为 $\sigma(i)$ 的预测之间的两两匹配代价（pair-wise matching cost）。按照此前的工作（例如 [42]），这一最优分配可以使用匈牙利算法高效计算。

匹配代价同时考虑类别预测以及预测边界框与真实边界框之间的相似程度。真实目标集合中的每一个元素 $i$ 都可以表示为 $y_i=(c_i,b_i)$，其中 $c_i$ 是目标类别标签（也可能为 $\varnothing$），而 $b_i\in[0,1]^4$ 是一个向量，用于定义真实边界框中心的坐标以及相对于图像尺寸归一化后的高度和宽度。

对于索引为 $\sigma(i)$ 的预测，我们将类别为 $c_i$ 的概率记为 $\hat{p}_{\sigma(i)}(c_i)$，并将预测边界框记为 $\hat{b}_{\sigma(i)}$。采用上述记号，我们将 $\mathcal{L}_{\mathrm{match}}(y_i,\hat{y}_{\sigma(i)})$ 定义为：

$$
\mathcal{L}_{\mathrm{match}}
\left(
y_i,\hat{y}_{\sigma(i)}
\right)
=
-\mathbb{1}_{\{c_i\neq\varnothing\}}
\hat{p}_{\sigma(i)}(c_i)
+
\mathbb{1}_{\{c_i\neq\varnothing\}}
\mathcal{L}_{\mathrm{box}}
\left(
b_i,\hat{b}_{\sigma(i)}
\right)
$$

这一寻找匹配的过程与现代检测器中用于将候选框 [36] 或锚框 [21] 与真实目标进行匹配的启发式分配规则起到了相同的作用。主要区别在于，对于不存在重复预测的直接集合预测，我们需要寻找一对一匹配。

第二步是计算损失函数，即针对前一步中得到的所有匹配对计算匈牙利损失（Hungarian loss）。我们以与常规目标检测器的损失类似的方式定义该损失，即将类别预测的负对数似然与稍后定义的边界框损失 $\mathcal{L}_{\mathrm{box}}(\cdot,\cdot)$ 进行线性组合：

$$
\mathcal{L}_{\mathrm{Hungarian}}
\left(
y,\hat{y}
\right)
=
\sum_{i=1}^{N}
\left[
-\log
\hat{p}_{\hat{\sigma}(i)}
(c_i)
+
\mathbb{1}_{\{c_i\neq\varnothing\}}
\mathcal{L}_{\mathrm{box}}
\left(
b_i,
\hat{b}_{\hat{\sigma}(i)}
\right)
\right]
\tag{2}
$$

其中，$\hat{\sigma}$ 是第一步公式（1）中计算得到的最优分配。在实践中，当 $c_i=\varnothing$ 时，我们将对数概率项的权重降低 10 倍，以处理类别不平衡问题。这与 Faster R-CNN 的训练过程通过下采样来平衡正、负候选框 [36] 的做法类似。

需要注意的是，一个目标与 $\varnothing$ 之间的匹配代价并不依赖于预测结果，这意味着在这种情况下，该代价是一个常数。在匹配代价中，我们使用概率 $\hat{p}_{\hat{\sigma}(i)}(c_i)$，而不是对数概率。这样能够使类别预测项与 $\mathcal{L}_{\mathrm{box}}(\cdot,\cdot)$ 具有可比较的量级，并且我们在实验中观察到了更好的性能。

> **图 2.** DETR 使用常规 CNN 骨干网络（backbone）学习输入图像的二维表示。模型首先将该表示展平，并加入位置编码（positional encoding），随后将其输入 Transformer 编码器。接下来，Transformer 解码器接收少量固定数量的可学习位置嵌入作为输入，我们将这些嵌入称为目标查询（object queries）；同时，解码器还会对编码器的输出进行注意力计算。我们将解码器的每一个输出嵌入传递给一个共享的前馈网络（Feed-Forward Network，FFN），该网络预测一个检测结果（类别和边界框）或“无目标”类别。

**边界框损失（Bounding box loss）。** 匹配代价以及匈牙利损失的第二部分是用于对边界框进行评分的 $\mathcal{L}_{\mathrm{box}}(\cdot)$。许多检测器相对于某些初始猜测预测边界框的偏移量 $\Delta$，与之不同，我们直接预测边界框。虽然这种方法简化了实现，但它会带来损失相对尺度方面的问题。

最常用的 $\ell_1$ 损失对于小边界框和大边界框会具有不同的尺度，即使二者的相对误差相似。为了缓解这一问题，我们使用 $\ell_1$ 损失与尺度不变的广义 IoU（Generalized Intersection over Union，GIoU）损失 [37] $\mathcal{L}_{\mathrm{iou}}(\cdot,\cdot)$ 的线性组合。

总体而言，我们的边界框损失 $\mathcal{L}_{\mathrm{box}}(b_i,\hat{b}_{\sigma(i)})$ 定义为：

$$
\mathcal{L}_{\mathrm{box}}
\left(
b_i,\hat{b}_{\sigma(i)}
\right)
=
\lambda_{\mathrm{iou}}
\mathcal{L}_{\mathrm{iou}}
\left(
b_i,\hat{b}_{\sigma(i)}
\right)
+
\lambda_{L1}
\left\|
b_i-\hat{b}_{\sigma(i)}
\right\|_1
$$

其中，$\lambda_{\mathrm{iou}},\lambda_{L1}\in\mathbb{R}$ 为超参数。这两个损失都使用一个批次中的目标数量进行归一化。

## 3.2 DETR 架构（DETR Architecture）

DETR 的整体架构出人意料地简单，如图 2 所示。它包含三个主要组成部分，下面将分别介绍：

1. 用于提取紧凑特征表示的 CNN 骨干网络；
2. 编码器—解码器 Transformer；
3. 用于生成最终检测预测的简单前馈网络（FFN）。

与许多现代检测器不同，只要深度学习框架提供常规 CNN 骨干网络和 Transformer 架构的实现，DETR 就可以用仅仅数百行代码实现。DETR 的推理代码使用 PyTorch [31] 可以在不到 50 行代码中实现。我们希望，我们方法的简洁性能够吸引新的研究人员加入目标检测研究领域。

### 骨干网络（Backbone）

从初始图像

$x_{\mathrm{img}}\in\mathbb{R}^{3\times H_0\times W_0}$

开始，其中包含 3 个颜色通道[^3]，一个常规 CNN 骨干网络会生成一个较低分辨率的激活图：

$f\in\mathbb{R}^{C\times H\times W}$。

我们通常使用的数值为：

$$
C=2048,
\qquad
H=\frac{H_0}{32},
\qquad
W=\frac{W_0}{32}.
$$

[^3]: 输入图像会组成批次，并根据需要应用零填充（0-padding），以保证它们都具有与该批次中最大图像相同的尺寸 $(H_0,W_0)$。

### Transformer 编码器（Transformer Encoder）

首先，一个 $1\times1$ 卷积将高层激活图 $f$ 的通道维度从 $C$ 降低到一个较小的维度 $d$，从而生成新的特征图：

$$
z_0\in\mathbb{R}^{d\times H\times W}.
$$

编码器要求输入为一个序列，因此我们将 $z_0$ 的两个空间维度折叠成一个维度，得到一个 $d\times HW$ 的特征图。

每一个编码器层都采用标准架构，由多头自注意力（multi-head self-attention）模块和前馈网络（FFN）组成。由于 Transformer 架构对于排列具有不变性，我们为其补充固定位置编码（fixed positional encodings）[30, 3]，并将这些位置编码加入每一个注意力层的输入中。关于该架构的详细定义，我们留到补充材料中介绍；其总体遵循 [46] 中描述的架构。

### Transformer 解码器（Transformer Decoder）

解码器遵循标准 Transformer 架构，使用多头自注意力以及编码器—解码器注意力机制，对 $N$ 个维度为 $d$ 的嵌入进行变换。

与原始 Transformer 的区别在于，我们的模型在每一个解码器层中并行解码这 $N$ 个目标，而 Vaswani 等人 [46] 使用的是自回归模型，即每次只预测输出序列中的一个元素。对于不熟悉这些概念的读者，我们建议参阅补充材料。

由于解码器同样具有排列不变性，因此，为了产生不同的结果，$N$ 个输入嵌入必须彼此不同。这些输入嵌入是可学习的位置编码，我们将其称为目标查询（object queries）；与编码器类似，我们将这些目标查询加入每一个注意力层的输入。

这 $N$ 个目标查询经过解码器后被转换成输出嵌入。随后，它们分别由前馈网络独立解码为边界框坐标和类别标签——该前馈网络将在下一小节中介绍——最终得到 $N$ 个预测结果。

通过对这些嵌入执行自注意力和编码器—解码器注意力，模型能够利用目标之间的两两关系，对所有目标进行联合的全局推理，同时还能够将整幅图像作为上下文。

### 预测前馈网络（Prediction Feed-Forward Networks，FFNs）

最终预测由一个三层感知机和一个线性投影层共同计算，其中三层感知机采用 ReLU 激活函数，隐藏维度为 $d$。

FFN 预测相对于输入图像归一化后的边界框中心坐标、高度和宽度；线性层则使用 softmax 函数预测类别标签。

由于我们预测的是一个固定大小、包含 $N$ 个边界框的集合，而 $N$ 通常远大于一幅图像中真正感兴趣目标的数量，因此我们引入了额外的特殊类别标签 $\varnothing$，用于表示某一个预测槽（slot）中没有检测到目标。该类别发挥的作用类似于标准目标检测方法中的“背景”（background）类别。

### 辅助解码损失（Auxiliary Decoding Losses）

我们发现，在训练过程中对解码器使用辅助损失 [1] 是有帮助的，尤其有助于模型输出每个类别正确数量的目标。

每一个解码器层的输出首先使用共享的层归一化（Layer Normalization，LayerNorm）进行归一化，然后输入共享的预测头——即分类预测头和边界框预测头。随后，我们按照通常的方式应用匈牙利损失进行监督。

# 4 实验（Experiments）

我们首先通过 COCO 上的定量评估表明，DETR 相较于 Faster R-CNN [36] 和 RetinaNet [22] 能够取得具有竞争力的结果。随后，我们对模型架构和损失函数进行了详细的消融研究，并给出了相应的分析与定性结果。最后，为了说明 DETR 是一种具有通用性的模型，我们展示了其在全景分割（Panoptic Segmentation）上的结果，其中仅在固定的 DETR 模型上训练了一个小型扩展模块。

**数据集（Dataset）。** 我们在 COCO 2017 目标检测和全景分割数据集 [23, 17] 上进行实验，该数据集包含 11.8 万张训练图像和 5000 张验证图像。每张图像都带有边界框和全景分割标注。平均每张图像包含 7 个实例，在训练集中单张图像最多包含 63 个实例，并且同一幅图像中可能同时存在从小目标到大目标的不同尺度实例。若无特别说明，我们报告的 AP 指的是边界框 AP（bbox AP），即对多个阈值进行积分得到的综合指标。与其他模型比较时，我们报告训练最后一个 epoch 的验证集 AP；在消融实验中，我们报告最后 10 个 epoch 的中位数。

**技术细节（Technical details）。** 我们使用 AdamW [25] 训练 DETR，将 Transformer 的初始学习率设置为 $10^{-4}$，骨干网络的学习率设置为 $10^{-5}$，权重衰减设置为 $10^{-4}$。

所有 Transformer 权重均使用 Xavier 初始化 [10]。骨干网络采用 torchvision 中经过 ImageNet 预训练的 ResNet 模型 [14]，其中批归一化（Batch Normalization）层被冻结。我们分别使用两种不同的骨干网络：ResNet-50 和 ResNet-101。对应模型分别称为 DETR 和 DETR-R101。

按照 [20]，我们还通过在骨干网络最后一个阶段中加入空洞卷积（dilation），并移除该阶段第一个卷积的一个步幅（stride），来提高特征分辨率。对应模型分别称为 DETR-DC5 和 DETR-DC5-R101，其中 DC5 表示采用空洞卷积的 C5 阶段（dilated C5 stage）。这一修改将特征分辨率提高了 2 倍，因此改善了小目标的性能，但代价是编码器自注意力的计算成本提高 16 倍，从而使整体计算成本约增加 2 倍。DETR、Faster R-CNN 和 RetinaNet 各模型的 FLOPs 完整比较见表 1。

我们使用尺度增强（scale augmentation），将输入图像缩放，使其短边至少为 480 像素、至多为 800 像素，同时长边不超过 1333 像素 [49]。

为了帮助模型通过编码器中的自注意力学习全局关系，我们在训练过程中还使用了随机裁剪增强，这能够将性能提高约 1 AP。具体而言，我们以 0.5 的概率将训练图像随机裁剪为一个矩形区域，然后再次将其缩放至 800–1333 的尺寸范围。

Transformer 使用默认的 0.1 dropout 进行训练。在推理阶段，一部分预测槽会预测为空类别。为了针对 AP 进行优化，我们使用这些预测槽中得分第二高的类别来替换空类别预测，并使用其对应的置信度。与直接过滤掉空预测槽相比，这一方法能够提高 2 个 AP。

其他训练超参数可见附录。在消融实验中，我们使用 300 个 epoch 的训练计划，并在第 200 个 epoch 后将学习率降低 10 倍；其中，一个 epoch 表示完整遍历所有训练图像一次。使用 16 块 V100 GPU 训练基线模型 300 个 epoch 需要 3 天，每块 GPU 使用 4 张图像，因此总批大小（batch size）为 64。

为了与 Faster R-CNN 进行比较，我们采用更长的训练计划，共训练 500 个 epoch，并在第 400 个 epoch 后降低学习率，这能够进一步提高 1.5 AP。

> **表 1.** 在 COCO 验证集上，使用 ResNet-50 和 ResNet-101 骨干网络的 RetinaNet、Faster R-CNN 与 DETR 的比较。表格上半部分给出了 Detectron2 [49] 中模型的结果；中间部分给出了加入 GIoU [37]、训练阶段随机裁剪增强以及较长的 9× 训练计划后的模型结果。DETR 模型能够取得与经过大量调优的 Faster R-CNN 基线相当的结果，其 $AP_S$ 较低，但 $AP_L$ 显著提高。我们使用 TorchScript 模型测量 FLOPs 和 FPS。名称中不包含 R101 的模型均使用 ResNet-50。

| 模型 | GFLOPs / FPS | 参数量 | AP | $AP_{50}$ | $AP_{75}$ | $AP_S$ | $AP_M$ | $AP_L$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RetinaNet | 205 / 18 | 38M | 38.7 | 58.0 | 41.5 | 23.3 | 42.3 | 50.3 |
| Faster RCNN-DC5 | 320 / 16 | 166M | 39.0 | 60.5 | 42.3 | 21.4 | 43.5 | 52.5 |
| Faster RCNN-FPN | 180 / 26 | 42M | 40.2 | 61.0 | 43.8 | 24.2 | 43.5 | 52.0 |
| Faster RCNN-R101-FPN | 246 / 20 | 60M | 42.0 | 62.5 | 45.9 | 25.2 | 45.6 | 54.6 |
| RetinaNet+ | 205 / 18 | 38M | 41.1 | 60.4 | 43.7 | 25.6 | 44.8 | 53.6 |
| Faster RCNN-DC5+ | 320 / 16 | 166M | 41.1 | 61.4 | 44.3 | 22.9 | 45.9 | 55.0 |
| Faster RCNN-FPN+ | 180 / 26 | 42M | 42.0 | 62.1 | 45.5 | 26.6 | 45.4 | 53.4 |
| Faster RCNN-R101-FPN+ | 246 / 20 | 60M | 44.0 | 63.9 | 47.8 | 27.2 | 48.1 | 56.0 |
| DETR | 86 / 28 | 41M | 42.0 | 62.4 | 44.2 | 20.5 | 45.8 | 61.1 |
| DETR-DC5 | 187 / 12 | 41M | 43.3 | 63.1 | 45.9 | 22.5 | 47.3 | 61.1 |
| DETR-R101 | 152 / 20 | 60M | 43.5 | 63.8 | 46.4 | 21.9 | 48.0 | 61.8 |
| DETR-DC5-R101 | 253 / 10 | 60M | 44.9 | 64.7 | 47.7 | 23.7 | 49.5 | 62.3 |

## 4.1 与 Faster R-CNN 和 RetinaNet 的比较（Comparison with Faster R-CNN and RetinaNet）

Transformer 通常使用 Adam 或 Adagrad 优化器，并结合非常长的训练计划和 dropout 进行训练，DETR 也是如此。然而，Faster R-CNN 通常使用随机梯度下降（Stochastic Gradient Descent，SGD）训练，只采用极少量的数据增强，而且据我们所知，尚不存在成功使用 Adam 或 dropout 的 Faster R-CNN 实例。

尽管存在这些差异，我们仍尝试增强基线模型。为了使其与 DETR 更加一致，我们在边界框损失中加入广义 IoU（Generalized IoU，GIoU）[37]，使用相同的随机裁剪增强，并采用已知能够改善结果的长训练方案 [12]。结果见表 1。

表 1 的上半部分给出了 Detectron2 Model Zoo [49] 中采用 3× 训练计划训练的模型结果。中间部分给出了相同模型采用 9× 训练计划（109 个 epoch）以及上述改进后的结果，并以“+”标记；这些改进总共带来了 1–2 AP 的提升。

表 1 的最后一部分给出了多种 DETR 模型的结果。为了保证参数量可比，我们选用一个具有 6 个 Transformer 编码器层和 6 个解码器层、宽度为 256、使用 8 个注意力头的模型。与采用 FPN 的 Faster R-CNN 类似，该模型拥有 41.3M 个参数，其中 ResNet-50 占 23.5M，Transformer 占 17.8M。

尽管 Faster R-CNN 和 DETR 都很可能通过更长时间的训练进一步获得提升，但我们可以得出结论：在参数量相同的情况下，DETR 能够与 Faster R-CNN 相竞争，并在 COCO 验证集上达到 42 AP。

DETR 达到这一结果的主要方式是显著提高了 $AP_L$（+7.8），但需要注意的是，在 $AP_S$ 上仍落后 5.5 个点。参数量相同且 FLOPs 数量相近的 DETR-DC5 能够获得更高的 AP，但在 $AP_S$ 上同样明显落后。使用 ResNet-101 骨干网络时，结果也具有类似趋势。

> **图 3.** 一组参考点对应的编码器自注意力。编码器能够区分不同的独立实例。预测结果由基线 DETR 在一张验证集图像上生成。

## 4.2 消融实验（Ablations）

Transformer 解码器中的注意力机制是对不同检测结果的特征表示之间关系进行建模的关键组成部分。在消融分析中，我们研究了架构和损失函数中的其他组件如何影响最终性能。

在该研究中，我们选用基于 ResNet-50 的 DETR 模型，该模型具有 6 个编码器层、6 个解码器层，宽度为 256。模型包含 41.3M 个参数，在短训练计划和长训练计划下分别达到 40.6 AP 和 42.0 AP，并能够以 28 FPS 运行，与使用相同骨干网络的 Faster R-CNN-FPN 类似。

### 编码器层数（Number of Encoder Layers）

我们通过改变编码器层数来评估图像级全局自注意力的重要性。

当完全不使用编码器层时，总体 AP 下降 3.9 个点，其中大型目标上的 AP 下降更为显著，达到 6.0 个点。我们推测，编码器通过使用全局场景推理，对于将不同目标彼此解耦具有重要作用。相关结果见附录。

在图 3 中，我们可视化了一个训练完成的模型最后一个编码器层的注意力图，并关注图像中的若干参考点。可以观察到，编码器似乎已经能够区分不同实例，这可能简化了解码器后续进行目标提取与定位的过程。

### 解码器层数（Number of Decoder Layers）

我们在每一个解码层后都施加辅助损失（见第 3.2 节），因此，在设计上，预测 FFN 会接受训练，使其能够根据任意一个解码器层的输出预测目标。

我们通过评估解码过程各个阶段能够得到的目标预测结果，分析每个解码器层的重要性（图 4）。随着解码层数增加，AP 和 $AP_{50}$ 均逐层提高。从第一层到最后一层，总计分别获得了显著的 +8.2 AP 和 +9.5 $AP_{50}$ 提升。

由于采用了基于集合的损失，DETR 从设计上并不需要 NMS。为了验证这一点，我们使用默认参数 [49]，对每一层解码器的输出应用标准 NMS。

NMS 能够改善第一层解码器的预测性能。原因可能是，Transformer 的单个解码层还无法计算输出元素之间的交叉关联，因此容易针对同一个目标生成多个预测。在第二层及后续解码层中，对激活进行自注意力计算使模型能够抑制重复预测。

随着解码器深度增加，我们观察到 NMS 所带来的性能增益逐渐减小。在最后几层中，NMS 反而降低 AP，因为它错误地移除了一部分真正例（True Positive，TP）预测。

> **图 4.** 长训练计划下的基线模型在每个解码器层之后的 AP 和 $AP_{50}$ 性能。DETR 从设计上不需要 NMS，这一点由该图得到了验证。在最后几层中，NMS 会移除真正例预测，因此降低 AP；但在前几层中，DETR 尚不具备消除重复预测的能力，因此 NMS 能够改善性能。

> **图 5.** 稀有类别上的分布外（out-of-distribution）泛化。尽管训练集中没有任何一张图像包含超过 13 只长颈鹿，DETR 仍可以轻松泛化至 24 个甚至更多实例。

与对编码器注意力进行可视化类似，我们在图 6 中可视化了解码器注意力，并使用不同颜色表示每一个预测目标对应的注意力图。

我们观察到，解码器的注意力相当局部，也就是说，它主要关注目标的边缘部位，例如头部或腿部。我们推测，在编码器通过全局注意力将不同实例分离之后，解码器只需要关注这些边缘部位，就可以提取目标类别和目标边界。

> **图 6.** 对每一个预测目标的解码器注意力进行可视化（图像来自 COCO 验证集）。预测结果由 DETR-DC5 模型生成。解码器通常关注目标的边缘部位，例如腿部和头部。

### FFN 的重要性（Importance of FFN）

Transformer 内部的 FFN 可以视为 $1\times1$ 卷积层，因此编码器与注意力增强卷积网络（attention augmented convolutional networks）[3] 具有一定相似性。

我们尝试完全移除 FFN，使 Transformer 层中仅保留注意力机制。这样做使网络参数量从 41.3M 降低至 28.7M，其中 Transformer 中仅剩 10.8M 个参数，但性能下降了 2.3 AP。因此，我们得出结论：FFN 对于取得良好性能十分重要。

### 位置编码的重要性（Importance of Positional Encodings）

我们的模型中存在两种位置编码：

1. 空间位置编码（spatial positional encodings）；
2. 输出位置编码（output positional encodings），即目标查询（object queries）。

我们对固定位置编码和可学习位置编码的多种组合进行了实验，结果见附录。

输出位置编码是必需的，无法完全移除，因此我们进行了两类实验：一种是在解码器输入处仅加入一次输出位置编码，另一种是在每一个解码器注意力层中将输出位置编码加入查询。

在第一个实验中，我们完全移除了空间位置编码，仅在输入处加入输出位置编码。值得注意的是，此时模型仍然能够取得超过 32 AP，仅比基线低 7.8 AP。

随后，我们像原始 Transformer [46] 那样，在输入处一次性加入固定的正弦空间位置编码和输出位置编码。与直接在注意力计算中加入位置编码相比，这种方式会导致 1.4 AP 的下降。

将可学习空间位置编码直接传入注意力模块能够取得相似结果。令人意外的是，在编码器中完全不加入任何空间位置编码仅导致 1.3 AP 的轻微下降。

当我们向注意力模块传递位置编码时，所有层共享同一套位置编码，而输出位置编码（目标查询）始终是可学习的。

根据这些消融实验，我们得出结论：Transformer 的多个组成部分——包括编码器中的全局自注意力、FFN、多层解码器以及位置编码——都会对最终的目标检测性能产生显著贡献。

### 对未见过的实例数量的泛化（Generalization to Unseen Numbers of Instances）

COCO 中的一些类别很少出现同一类别的大量实例。例如，在训练集中，没有任何一张图像包含超过 13 只长颈鹿。

我们构造了一张合成图像[^4]，以验证 DETR 的泛化能力（见图 5）。我们的模型能够找到图像中的全部 24 只长颈鹿，而这显然属于训练分布之外的数据。

这一实验验证了不同目标查询并不存在很强的类别专门化现象。

[^4]: 基础图片来源：https://www.piqsels.com/en/public-domain-photo-jzlwu

## 4.3 用于全景分割的 DETR（DETR for Panoptic Segmentation）

全景分割 [18] 近年来受到了计算机视觉社区的大量关注。

类似于 Faster R-CNN [36] 被扩展为 Mask R-CNN [13]，DETR 也可以通过在解码器输出之上增加一个掩码头（mask head）进行自然扩展。

在本节中，我们证明，可以使用这样的掩码头生成全景分割结果 [18]，并以统一方式处理 stuff 类别和 thing 类别。

我们在 COCO 数据集的全景标注上进行实验。除了 80 个 thing 类别之外，该数据集还包含 53 个 stuff 类别。

我们使用与目标检测相同的训练方案，在 COCO 上训练 DETR，使其同时预测 stuff 类别和 thing 类别周围的边界框。

训练过程中必须预测边界框，因为匈牙利匹配需要根据边界框之间的距离来计算。

此外，我们增加了一个掩码头，用于针对每一个预测边界框生成一个二值掩码，见图 7。

该掩码头以 Transformer 解码器针对每个目标的输出作为输入，并计算该嵌入在编码器输出上的多头注意力分数，其中包含 $M$ 个注意力头，从而为每个目标生成 $M$ 张低分辨率注意力热图。

为了生成最终预测并提高分辨率，我们采用了类似 FPN 的架构。更多细节见补充材料。

最终掩码的输出分辨率对应步幅 4，每一个掩码都使用 DICE/F-1 损失 [27] 和 Focal Loss [22] 独立进行监督。

> **图 7.** 全景分割头示意图。针对每个检测到的目标并行生成一个二值掩码，随后通过逐像素 argmax 将这些掩码进行合并。

掩码头既可以与 DETR 联合训练，也可以采用两阶段训练过程：首先仅针对边界框训练 DETR，然后冻结所有权重，仅训练掩码头 25 个 epoch。

实验表明，这两种方法能够获得相似结果。由于第二种方法的计算成本更低，我们报告的结果采用该方法。

为了生成最终的全景分割结果，我们只需要在每一个像素位置对掩码分数执行 argmax，并将对应类别分配给最终得到的掩码。

这一过程能够保证最终掩码之间不存在重叠，因此 DETR 不需要使用启发式方法 [18] 对不同掩码进行对齐。

### 训练细节（Training Details）

我们按照边界框检测的训练方案训练 DETR、DETR-DC5 和 DETR-R101，使这些模型在 COCO 数据集上同时预测 stuff 和 thing 类别周围的边界框。

新的掩码头训练 25 个 epoch，具体细节见补充材料。

在推理过程中，我们首先过滤掉置信度低于 85% 的检测结果，然后执行逐像素 argmax，以确定每一个像素属于哪个掩码。

随后，我们将同一 stuff 类别的不同掩码预测合并为一个掩码，并过滤掉空掩码，即面积小于 4 个像素的掩码。

### 主要结果（Main Results）

定性结果见图 8。

在表 2 中，我们将所提出的统一全景分割方法与若干成熟方法进行了比较，这些方法分别对 thing 和 stuff 类别进行处理。

我们报告全景质量（Panoptic Quality，PQ），以及其在 thing 类别上的结果 $PQ^{th}$ 和 stuff 类别上的结果 $PQ^{st}$。

我们还报告掩码 AP，该指标仅在 thing 类别上计算，并且是在执行任何全景后处理之前计算的；对于我们的方法而言，即在执行逐像素 argmax 之前。

结果表明，在 COCO-val 2017 上，DETR 优于已经发表的方法，同时也优于我们构建的强 PanopticFPN 基线。为了公平比较，该 PanopticFPN 基线采用与 DETR 相同的数据增强方式进行训练。

从分项结果可以看出，DETR 在 stuff 类别上的表现尤其突出。我们推测，编码器注意力所带来的全局推理能力是实现这一结果的关键因素。

对于 thing 类别，尽管在掩码 AP 指标上相比基线最多落后约 8 mAP，但 DETR 仍然能够获得具有竞争力的 $PQ^{th}$。

我们还在 COCO 测试集上评估了所提出的方法，最终取得 46 PQ。

我们希望，本方法能够推动未来对完全统一的全景分割模型进行进一步探索。

> **表 2.** 在 COCO 验证集上与当前先进方法 UPSNet [50] 和 Panoptic FPN [17] 的比较。为了公平比较，我们使用与 DETR 相同的数据增强方式，并采用 18× 训练计划重新训练了 PanopticFPN。UPSNet 使用 1× 训练计划，UPSNet-M 是采用多尺度测试时增强（multiscale test-time augmentations）的版本。

| 模型 | 骨干网络 | PQ | SQ | RQ | $PQ^{th}$ | $SQ^{th}$ | $RQ^{th}$ | $PQ^{st}$ | $SQ^{st}$ | $RQ^{st}$ | AP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PanopticFPN++ | R50 | 42.4 | 79.3 | 51.6 | 49.2 | 82.4 | 58.8 | 32.3 | 74.8 | 40.6 | 37.7 |
| UPSnet | R50 | 42.5 | 78.0 | 52.5 | 48.6 | 79.4 | 59.6 | 33.4 | 75.9 | 41.7 | 34.3 |
| UPSnet-M | R50 | 43.0 | 79.1 | 52.8 | 48.9 | 79.7 | 59.7 | 34.1 | 78.2 | 42.3 | 34.3 |
| PanopticFPN++ | R101 | 44.1 | 79.5 | 53.3 | 51.0 | 83.2 | 60.6 | 33.6 | 74.0 | 42.1 | 39.7 |
| DETR | R50 | 43.4 | 79.3 | 53.8 | 48.2 | 79.8 | 59.5 | 36.3 | 78.5 | 45.3 | 31.1 |
| DETR-DC5 | R50 | 44.6 | 79.8 | 55.0 | 49.4 | 80.5 | 60.6 | 37.3 | 78.7 | 46.5 | 31.9 |
| DETR | R101 | 45.1 | 79.9 | 55.5 | 50.5 | 80.9 | 61.7 | 37.0 | 78.5 | 46.0 | 33.0 |
| DETR-DC5 | R101 | 45.6 | 80.0 | 56.1 | 50.9 | 80.9 | 62.2 | 37.5 | 78.6 | 46.8 | 33.1 |

> **图 8.** DETR-R101 生成的全景分割定性结果。DETR 以统一方式为 thing 和 stuff 类别生成彼此对齐的掩码预测。

# 5 结论（Conclusion）

我们提出了 DETR，这是一种新的目标检测系统设计，它基于 Transformer 和用于直接集合预测的二分图匹配损失。

在具有挑战性的 COCO 数据集上，该方法能够取得与经过优化的 Faster R-CNN 基线相当的结果。

DETR 易于实现，并具有灵活的架构，可以很容易地扩展到全景分割任务，同时能够取得具有竞争力的结果。

此外，DETR 在大型目标上的性能显著更好，这很可能得益于自注意力机制对全局信息的处理。

这种新的检测器设计也带来了一些新的挑战，尤其是在训练、优化以及小目标性能方面。

现有目标检测器花费了数年时间才逐渐解决类似问题，我们预计未来的工作也能够成功解决 DETR 所面临的这些问题。

# 参考文献（References）

[1] Al-Rfou, R., Choe, D., Constant, N., Guo, M., Jones, L.  
**Character-level language modeling with deeper self-attention.**  
**中文译名：** 使用更深层自注意力的字符级语言建模。  
In: AAAI Conference on Artificial Intelligence（AAAI 人工智能会议）, 2019.

[2] Bahdanau, D., Cho, K., Bengio, Y.  
**Neural machine translation by jointly learning to align and translate.**  
**中文译名：** 通过联合学习对齐与翻译实现神经机器翻译。  
In: ICLR（International Conference on Learning Representations，国际学习表征会议）, 2015.

[3] Bello, I., Zoph, B., Vaswani, A., Shlens, J., Le, Q.V.  
**Attention augmented convolutional networks.**  
**中文译名：** 注意力增强卷积网络。  
In: ICCV（IEEE/CVF International Conference on Computer Vision，国际计算机视觉会议）, 2019.

[4] Bodla, N., Singh, B., Chellappa, R., Davis, L.S.  
**Soft-NMS — improving object detection with one line of code.**  
**中文译名：** Soft-NMS——用一行代码改进目标检测。  
In: ICCV, 2017.

[5] Cai, Z., Vasconcelos, N.  
**Cascade R-CNN: High quality object detection and instance segmentation.**  
**中文译名：** Cascade R-CNN：高质量目标检测与实例分割。  
PAMI（IEEE Transactions on Pattern Analysis and Machine Intelligence，IEEE《模式分析与机器智能汇刊》）, 2019.

[6] Chan, W., Saharia, C., Hinton, G., Norouzi, M., Jaitly, N.  
**Imputer: Sequence modelling via imputation and dynamic programming.**  
**中文译名：** Imputer：通过插补与动态规划进行序列建模。  
arXiv:2002.08926, 2020.

[7] Devlin, J., Chang, M.W., Lee, K., Toutanova, K.  
**BERT: Pre-training of deep bidirectional transformers for language understanding.**  
**中文译名：** BERT：用于语言理解的深度双向 Transformer 预训练。  
In: NAACL-HLT, 2019.

[8] Erhan, D., Szegedy, C., Toshev, A., Anguelov, D.  
**Scalable object detection using deep neural networks.**  
**中文译名：** 使用深度神经网络的可扩展目标检测。  
In: CVPR（IEEE Conference on Computer Vision and Pattern Recognition，计算机视觉与模式识别会议）, 2014.

[9] Ghazvininejad, M., Levy, O., Liu, Y., Zettlemoyer, L.  
**Mask-predict: Parallel decoding of conditional masked language models.**  
**中文译名：** Mask-predict：条件掩码语言模型的并行解码。  
arXiv:1904.09324, 2019.

[10] Glorot, X., Bengio, Y.  
**Understanding the difficulty of training deep feedforward neural networks.**  
**中文译名：** 理解深度前馈神经网络训练的困难。  
In: AISTATS（International Conference on Artificial Intelligence and Statistics，人工智能与统计国际会议）, 2010.

[11] Gu, J., Bradbury, J., Xiong, C., Li, V.O., Socher, R.  
**Non-autoregressive neural machine translation.**  
**中文译名：** 非自回归神经机器翻译。  
In: ICLR, 2018.

[12] He, K., Girshick, R., Dollár, P.  
**Rethinking imagenet pre-training.**  
**中文译名：** 重新思考 ImageNet 预训练。  
In: ICCV, 2019.

[13] He, K., Gkioxari, G., Dollár, P., Girshick, R.B.  
**Mask R-CNN.**  
**中文译名：** Mask R-CNN。  
In: ICCV, 2017.

[14] He, K., Zhang, X., Ren, S., Sun, J.  
**Deep residual learning for image recognition.**  
**中文译名：** 用于图像识别的深度残差学习。  
In: CVPR, 2016.

[15] Hosang, J.H., Benenson, R., Schiele, B.  
**Learning non-maximum suppression.**  
**中文译名：** 学习非极大值抑制。  
In: CVPR, 2017.

[16] Hu, H., Gu, J., Zhang, Z., Dai, J., Wei, Y.  
**Relation networks for object detection.**  
**中文译名：** 用于目标检测的关系网络。  
In: CVPR, 2018.

[17] Kirillov, A., Girshick, R., He, K., Dollár, P.  
**Panoptic feature pyramid networks.**  
**中文译名：** 全景特征金字塔网络。  
In: CVPR, 2019.

[18] Kirillov, A., He, K., Girshick, R., Rother, C., Dollar, P.  
**Panoptic segmentation.**  
**中文译名：** 全景分割。  
In: CVPR, 2019.

[19] Kuhn, H.W.  
**The Hungarian method for the assignment problem.**  
**中文译名：** 用于指派问题的匈牙利方法。  
1955.

[20] Li, Y., Qi, H., Dai, J., Ji, X., Wei, Y.  
**Fully convolutional instance-aware semantic segmentation.**  
**中文译名：** 全卷积实例感知语义分割。  
In: CVPR, 2017.

[21] Lin, T.Y., Dollár, P., Girshick, R., He, K., Hariharan, B., Belongie, S.  
**Feature pyramid networks for object detection.**  
**中文译名：** 用于目标检测的特征金字塔网络。  
In: CVPR, 2017.

[22] Lin, T.Y., Goyal, P., Girshick, R.B., He, K., Dollár, P.  
**Focal loss for dense object detection.**  
**中文译名：** 用于稠密目标检测的 Focal Loss。  
In: ICCV, 2017.

[23] Lin, T.Y., Maire, M., Belongie, S., Hays, J., Perona, P., Ramanan, D., Dollár, P., Zitnick, C.L.  
**Microsoft COCO: Common objects in context.**  
**中文译名：** Microsoft COCO：上下文中的常见目标。  
In: ECCV（European Conference on Computer Vision，欧洲计算机视觉会议）, 2014.

[24] Liu, W., Anguelov, D., Erhan, D., Szegedy, C., Reed, S.E., Fu, C.Y., Berg, A.C.  
**SSD: Single shot multibox detector.**  
**中文译名：** SSD：单次多框目标检测器。  
In: ECCV, 2016.

[25] Loshchilov, I., Hutter, F.  
**Decoupled weight decay regularization.**  
**中文译名：** 解耦权重衰减正则化。  
In: ICLR, 2017.

[26] Lüscher, C., Beck, E., Irie, K., Kitza, M., Michel, W., Zeyer, A., Schlüter, R., Ney, H.  
**Rwth asr systems for librispeech: Hybrid vs attention - w/o data augmentation.**  
**中文译名：** 用于 LibriSpeech 的 RWTH ASR 系统：混合方法与注意力方法——不使用数据增强。  
arXiv:1905.03072, 2019.

[27] Milletari, F., Navab, N., Ahmadi, S.A.  
**V-net: Fully convolutional neural networks for volumetric medical image segmentation.**  
**中文译名：** V-Net：用于体积医学图像分割的全卷积神经网络。  
In: 3DV（International Conference on 3D Vision，国际三维视觉会议）, 2016.

[28] Oord, A.v.d., Li, Y., Babuschkin, I., Simonyan, K., Vinyals, O., Kavukcuoglu, K., Driessche, G.v.d., Lockhart, E., Cobo, L.C., Stimberg, F., et al.  
**Parallel WaveNet: Fast high-fidelity speech synthesis.**  
**中文译名：** Parallel WaveNet：快速高保真语音合成。  
arXiv:1711.10433, 2017.

[29] Park, E., Berg, A.C.  
**Learning to decompose for object detection and instance segmentation.**  
**中文译名：** 学习分解以进行目标检测与实例分割。  
arXiv:1511.06449, 2015.

[30] Parmar, N., Vaswani, A., Uszkoreit, J., Kaiser, L., Shazeer, N., Ku, A., Tran, D.  
**Image Transformer.**  
**中文译名：** Image Transformer：图像 Transformer。  
In: ICML（International Conference on Machine Learning，国际机器学习会议）, 2018.

[31] Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., Killeen, T., Lin, Z., Gimelshein, N., Antiga, L., Desmaison, A., Kopf, A., Yang, E., DeVito, Z., Raison, M., Tejani, A., Chilamkurthy, S., Steiner, B., Fang, L., Bai, J., Chintala, S.  
**PyTorch: An imperative style, high-performance deep learning library.**  
**中文译名：** PyTorch：一种命令式风格的高性能深度学习程序库。  
In: NeurIPS（Conference on Neural Information Processing Systems，神经信息处理系统大会）, 2019.

[32] Pineda, L., Salvador, A., Drozdzal, M., Romero, A.  
**Elucidating image-to-set prediction: An analysis of models, losses and datasets.**  
**中文译名：** 阐明图像到集合预测：对模型、损失和数据集的分析。  
arXiv:1904.05709, 2019.

[33] Radford, A., Wu, J., Child, R., Luan, D., Amodei, D., Sutskever, I.  
**Language models are unsupervised multitask learners.**  
**中文译名：** 语言模型是无监督多任务学习器。  
2019.

[34] Redmon, J., Divvala, S., Girshick, R., Farhadi, A.  
**You only look once: Unified, real-time object detection.**  
**中文译名：** You Only Look Once：统一的实时目标检测。  
In: CVPR, 2016.

[35] Ren, M., Zemel, R.S.  
**End-to-end instance segmentation with recurrent attention.**  
**中文译名：** 使用循环注意力的端到端实例分割。  
In: CVPR, 2017.

[36] Ren, S., He, K., Girshick, R.B., Sun, J.  
**Faster R-CNN: Towards real-time object detection with region proposal networks.**  
**中文译名：** Faster R-CNN：利用区域候选网络实现实时目标检测。  
PAMI, 2015.

[37] Rezatofighi, H., Tsoi, N., Gwak, J., Sadeghian, A., Reid, I., Savarese, S.  
**Generalized intersection over union.**  
**中文译名：** 广义交并比。  
In: CVPR, 2019.

[38] Rezatofighi, S.H., Kaskman, R., Motlagh, F.T., Shi, Q., Cremers, D., Leal-Taixé, L., Reid, I.  
**Deep Perm-Set Net: Learn to predict sets with unknown permutation and cardinality using deep neural networks.**  
**中文译名：** Deep Perm-Set Net：使用深度神经网络学习预测具有未知排列和基数的集合。  
arXiv:1805.00613, 2018.

[39] Rezatofighi, S.H., Milan, A., Abbasnejad, E., Dick, A., Reid, I., Kaskman, R., Cremers, D., Leal-Taixé, L.  
**DeepSetNet: Predicting sets with deep neural networks.**  
**中文译名：** DeepSetNet：使用深度神经网络预测集合。  
In: ICCV, 2017.

[40] Romera-Paredes, B., Torr, P.H.S.  
**Recurrent instance segmentation.**  
**中文译名：** 循环实例分割。  
In: ECCV, 2015.

[41] Salvador, A., Bellver, M., Baradad, M., Marqués, F., Torres, J., Giró, X.  
**Recurrent neural networks for semantic instance segmentation.**  
**中文译名：** 用于语义实例分割的循环神经网络。  
arXiv:1712.00617, 2017.

[42] Stewart, R.J., Andriluka, M., Ng, A.Y.  
**End-to-end people detection in crowded scenes.**  
**中文译名：** 拥挤场景中的端到端行人检测。  
In: CVPR, 2015.

[43] Sutskever, I., Vinyals, O., Le, Q.V.  
**Sequence to sequence learning with neural networks.**  
**中文译名：** 使用神经网络的序列到序列学习。  
In: NeurIPS, 2014.

[44] Synnaeve, G., Xu, Q., Kahn, J., Grave, E., Likhomanenko, T., Pratap, V., Sriram, A., Liptchinsky, V., Collobert, R.  
**End-to-end ASR: from supervised to semi-supervised learning with modern architectures.**  
**中文译名：** 端到端自动语音识别：利用现代架构从监督学习走向半监督学习。  
arXiv:1911.08460, 2019.

[45] Tian, Z., Shen, C., Chen, H., He, T.  
**FCOS: Fully convolutional one-stage object detection.**  
**中文译名：** FCOS：全卷积单阶段目标检测。  
In: ICCV, 2019.

[46] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A.N., Kaiser, L., Polosukhin, I.  
**Attention is all you need.**  
**中文译名：** 注意力机制就是你所需要的一切。  
In: NeurIPS, 2017.

[47] Vinyals, O., Bengio, S., Kudlur, M.  
**Order matters: Sequence to sequence for sets.**  
**中文译名：** 顺序很重要：面向集合的序列到序列方法。  
In: ICLR, 2016.

[48] Wang, X., Girshick, R.B., Gupta, A., He, K.  
**Non-local neural networks.**  
**中文译名：** 非局部神经网络。  
In: CVPR, 2018.

[49] Wu, Y., Kirillov, A., Massa, F., Lo, W.Y., Girshick, R.  
**Detectron2.**  
**中文译名：** Detectron2。  
https://github.com/facebookresearch/detectron2, 2019.

[50] Xiong, Y., Liao, R., Zhao, H., Hu, R., Bai, M., Yumer, E., Urtasun, R.  
**UPSNet: A unified panoptic segmentation network.**  
**中文译名：** UPSNet：一种统一的全景分割网络。  
In: CVPR, 2019.

[51] Zhang, S., Chi, C., Yao, Y., Lei, Z., Li, S.Z.  
**Bridging the gap between anchor-based and anchor-free detection via adaptive training sample selection.**  
**中文译名：** 通过自适应训练样本选择弥合基于锚框与无锚框目标检测之间的差距。  
arXiv:1912.02424, 2019.

[52] Zhou, X., Wang, D., Krähenbühl, P.  
**Objects as points.**  
**中文译名：** 将目标表示为点。  
arXiv:1904.07850, 2019.
























——DETR 主论文翻译完毕。下一部分从补充材料《End-to-End Object Detection with Transformers: Supplementary material》开始——

























# 基于 Transformer 的端到端目标检测：补充材料（End-to-End Object Detection with Transformers: Supplementary Material）

# 目录（Table of Contents）

1. 附录  
   1.1 预备知识：多头注意力层  
   1.2 损失函数  
   1.3 详细架构  
   1.4 训练超参数  
   1.5 补充结果  
   1.6 PyTorch 推理代码  
   1.7 致谢  

# 1 附录（Appendix）

## 1.1 预备知识：多头注意力层（Preliminaries: Multi-head Attention Layers）

由于我们的模型基于 Transformer 架构，为了完整起见，我们在这里回顾本文所使用的注意力机制的一般形式。该注意力机制遵循 [8]，但位置编码的具体处理方式除外（见公式（6）），后者遵循 [1]。

**多头注意力（Multi-head）。** 具有 $M$ 个头、维度为 $d$ 的多头注意力（multi-head attention）的一般形式是一个具有如下形式的函数，其中使用

$$
d'=\frac{d}{M},
$$

并通过下方括号标注矩阵/张量的尺寸：

$$
\mathrm{mh\text{-}attn}:
\underbrace{X_q}_{d\times N_q},
\underbrace{X_{kv}}_{d\times N_{kv}},
\underbrace{T}_{M\times 3\times d'\times d},
\underbrace{L}_{d\times d}
\mapsto
\underbrace{\tilde{X}_q}_{d\times N_q}.
\tag{1}
$$

其中，$X_q$ 是长度为 $N_q$ 的查询序列（query sequence），$X_{kv}$ 是长度为 $N_{kv}$ 的键—值序列（key-value sequence）；为了简化说明，这两个序列具有相同的通道数 $d$。$T$ 是用于计算所谓查询（query）、键（key）和值（value）嵌入的权重张量，而 $L$ 是一个投影矩阵。输出与查询序列具有相同的尺寸。

在介绍细节之前，为了明确术语，多头自注意力（multi-head self-attention，mh-s-attn）是 $X_q=X_{kv}$ 时的特殊情况，即：

$$
\mathrm{mh\text{-}s\text{-}attn}(X,T,L)
=
\mathrm{mh\text{-}attn}(X,X,T,L).
\tag{2}
$$

多头注意力实际上就是将 $M$ 个单头注意力（single attention head）的输出进行拼接，然后通过 $L$ 进行投影。通常的做法 [8] 是使用残差连接（residual connection）、dropout 和层归一化（layer normalization）。

换言之，记

$$
\tilde{X}_q
=
\mathrm{mh\text{-}attn}(X_q,X_{kv},T,L),
$$

并令 $X'_q$ 表示所有注意力头输出的拼接，则有：

$$
X'_q
=
[
\mathrm{attn}(X_q,X_{kv},T_1);
\ldots;
\mathrm{attn}(X_q,X_{kv},T_M)
]
\tag{3}
$$

以及：

$$
\tilde{X}_q
=
\mathrm{layernorm}
\left(
X_q+
\mathrm{dropout}(LX'_q)
\right).
\tag{4}
$$

其中，$[\,;\,]$ 表示沿通道维度进行拼接。

**单头注意力（Single head）。** 一个权重张量为

$$
T'\in\mathbb{R}^{3\times d'\times d}
$$

的注意力头，记作

$$
\mathrm{attn}(X_q,X_{kv},T'),
$$

还依赖额外的位置编码：

$$
P_q\in\mathbb{R}^{d\times N_q}
$$

和

$$
P_{kv}\in\mathbb{R}^{d\times N_{kv}}.
$$

首先，在查询和键中加入位置编码 [1]，然后计算所谓的查询、键和值嵌入：

$$
[Q;K;V]
=
[
T'_1(X_q+P_q);
T'_2(X_{kv}+P_{kv});
T'_3X_{kv}
].
\tag{5}
$$

其中，$T'$ 是 $T'_1$、$T'_2$ 和 $T'_3$ 的拼接。

随后，根据查询与键之间点积的 softmax 计算注意力权重 $\alpha$，使查询序列中的每一个元素都能够关注键—值序列中的所有元素。这里，$i$ 表示查询索引，$j$ 表示键—值索引：

$$
\alpha_{i,j}
=
\frac{
e^{\frac{1}{\sqrt{d'}}Q_i^T K_j}
}{
Z_i
},
\qquad
Z_i
=
\sum_{j=1}^{N_{kv}}
e^{\frac{1}{\sqrt{d'}}Q_i^T K_j}.
\tag{6}
$$

在我们的方法中，位置编码既可以是可学习的，也可以是固定的；但对于给定的查询/键—值序列，它们会在所有注意力层之间共享，因此我们没有显式地将其写成注意力函数的参数。在描述编码器和解码器时，我们将进一步给出它们具体取值的详细信息。

最终输出是使用注意力权重对值进行加权聚合得到的。第 $i$ 个输出为：

$$
\mathrm{attn}_i(X_q,X_{kv},T')
=
\sum_{j=1}^{N_{kv}}
\alpha_{i,j}V_j.
$$

**前馈网络层（Feed-Forward Network，FFN layers）。** 原始 Transformer 在多头注意力层与所谓的 FFN 层 [8] 之间交替堆叠。FFN 实际上可以视为多层 $1\times1$ 卷积。

我们采用的 FFN 由两层 $1\times1$ 卷积组成，并使用 ReLU 激活函数。在这两层之后，还会像公式（4）一样使用残差连接、dropout 和层归一化。

## 1.2 损失函数（Losses）

为了完整起见，我们在这里详细介绍本文方法所使用的损失函数。所有损失均按照一个批次中的目标数量进行归一化。

在分布式训练中需要格外注意：由于每块 GPU 接收到一个子批次（sub-batch），仅使用本地批次中的目标数量进行归一化是不够的，因为不同 GPU 上的子批次通常并不平衡。相反，必须使用所有子批次中的目标总数进行归一化。

### 边界框损失（Box Loss）

与 [7, 5] 类似，我们在损失函数中使用交并比（Intersection over Union，IoU）的一个软版本，同时对 $\hat{b}$ 使用 $\ell_1$ 损失：

$$
\mathcal{L}_{\mathrm{box}}
\left(
b_{\sigma(i)},\hat{b}_i
\right)
=
\lambda_{\mathrm{iou}}
\mathcal{L}_{\mathrm{iou}}
\left(
b_{\sigma(i)},\hat{b}_i
\right)
+
\lambda_{L1}
\left\|
b_{\sigma(i)}-\hat{b}_i
\right\|_1,
\tag{7}
$$

其中，$\lambda_{\mathrm{iou}},\lambda_{L1}\in\mathbb{R}$ 为超参数，而 $\mathcal{L}_{\mathrm{iou}}(\cdot)$ 是广义 IoU（Generalized IoU，GIoU）[6]：

$$
\mathcal{L}_{\mathrm{iou}}
\left(
b_{\sigma(i)},\hat{b}_i
\right)
=
1-
\left(
\frac{
\left|
b_{\sigma(i)}\cap\hat{b}_i
\right|
}{
\left|
b_{\sigma(i)}\cup\hat{b}_i
\right|
}
-
\frac{
\left|
B(b_{\sigma(i)},\hat{b}_i)
\setminus
\left(
b_{\sigma(i)}\cup\hat{b}_i
\right)
\right|
}{
\left|
B(b_{\sigma(i)},\hat{b}_i)
\right|
}
\right).
\tag{8}
$$

$|\cdot|$ 表示“面积”，边界框坐标之间的并集和交集在这里被简写为边界框本身。并集或交集的面积通过对 $b_{\sigma(i)}$ 和 $\hat{b}_i$ 的线性函数执行 $\min/\max$ 运算得到，这使该损失函数对于随机梯度而言具有足够良好的性质。

$B(b_{\sigma(i)},\hat{b}_i)$ 表示能够同时包含 $b_{\sigma(i)}$ 和 $\hat{b}_i$ 的最小边界框；涉及 $B$ 的面积同样通过对边界框坐标的线性函数执行 $\min/\max$ 运算计算。

### DICE/F-1 损失（DICE/F-1 Loss）[3]

DICE 系数与交并比密切相关。记 $\hat{m}$ 为模型预测的原始掩码 logits，$m$ 为二值目标掩码，则损失定义为：

$$
\mathcal{L}_{\mathrm{DICE}}(m,\hat{m})
=
1-
\frac{
2m\sigma(\hat{m})+1
}{
\sigma(\hat{m})+m+1
}.
\tag{9}
$$

其中，$\sigma$ 为 sigmoid 函数。该损失按照目标数量进行归一化。

## 1.3 详细架构（Detailed Architecture）

DETR 所使用 Transformer 的详细结构如图 1 所示，其中位置编码会传入每一个注意力层。

来自 CNN 骨干网络的图像特征与空间位置编码一起输入 Transformer 编码器。在每一个多头自注意力层中，空间位置编码都会加入查询和键。

随后，解码器接收查询——其初始值设置为零——、输出位置编码（即目标查询，object queries）以及编码器记忆（encoder memory），并通过多个多头自注意力层以及解码器—编码器注意力层，最终生成预测类别标签和边界框的集合。

第一个解码器层中的第一层自注意力可以省略。

> **图 1.** DETR 的 Transformer 架构。详细信息请参见第 1.3 节。

### 计算复杂度（Computational Complexity）

编码器中的每一次自注意力计算复杂度均为：

$$
O\left(d^2HW+d(HW)^2\right).
$$

其中，计算单个查询/键/值嵌入的代价为：

$$
O(d'd),
$$

并且：

$$
Md'=d.
$$

而单个注意力头计算注意力权重的代价为：

$$
O\left(d'(HW)^2\right).
$$

其他计算的代价可以忽略不计。

在解码器中，每一次自注意力的复杂度为：

$$
O\left(d^2N+dN^2\right),
$$

编码器与解码器之间的交叉注意力（cross-attention）复杂度为：

$$
O\left(d^2(N+HW)+dNHW\right).
$$

这一计算量远低于编码器，因为在实践中：

$$
N\ll HW.
$$

### FLOPs 计算（FLOPS Computation）

由于 Faster R-CNN 的 FLOPs 取决于图像中的候选框数量，因此我们报告 COCO 2017 验证集中前 100 张图像的平均 FLOPs。

我们使用 Detectron2 [9] 中的 `flop_count_operators` 工具计算 FLOPs。对于 Detectron2 模型，我们直接使用该工具而不进行修改；对于 DETR 模型，我们对其进行了扩展，以将批量矩阵乘法（batch matrix multiply，`bmm`）计入其中。

## 1.4 训练超参数（Training Hyperparameters）

我们使用 AdamW [2] 训练 DETR。AdamW 改进了权重衰减的处理方式，我们将权重衰减设置为：

$$
10^{-4}.
$$

我们还使用梯度裁剪（gradient clipping），最大梯度范数设为：

$$
0.1.
$$

骨干网络和 Transformer 的处理方式略有不同，下面分别介绍二者的具体设置。

### 骨干网络（Backbone）

从 Torchvision 中导入经过 ImageNet 预训练的 ResNet-50 骨干网络，并移除最后的分类层。

按照目标检测领域广泛采用的做法，在训练期间冻结骨干网络中批归一化（Batch Normalization）的权重和统计量。

我们使用如下学习率对骨干网络进行微调：

$$
10^{-5}.
$$

我们观察到，将骨干网络的学习率设置为比网络其他部分大约低一个数量级，对于稳定训练十分重要，尤其是在训练的前几个 epoch 中。

> **表 1. 编码器规模的影响。** 每一行对应一个具有不同编码器层数、但解码器层数保持固定的模型。随着编码器层数增加，性能逐渐提升。

| 编码器层数 | GFLOPs / FPS | 参数量 | AP | $AP_{50}$ | $AP_S$ | $AP_M$ | $AP_L$ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 76 / 28 | 33.4M | 36.7 | 57.4 | 16.8 | 39.6 | 54.2 |
| 3 | 81 / 25 | 37.4M | 40.1 | 60.6 | 18.5 | 43.8 | 58.6 |
| 6 | 86 / 23 | 41.3M | 40.6 | 61.6 | 19.9 | 44.3 | 60.2 |
| 12 | 95 / 20 | 49.2M | 41.6 | 62.1 | 19.8 | 44.9 | 61.9 |

### Transformer

我们使用如下学习率训练 Transformer：

$$
10^{-4}.
$$

每一个多头注意力层和 FFN 之后、层归一化之前，都使用概率为 $0.1$ 的加性 dropout（additive dropout）。

权重使用 Xavier 初始化进行随机初始化。

### 损失函数（Losses）

对于边界框回归，我们使用 $\ell_1$ 损失和 GIoU 损失的线性组合，其权重分别为：

$$
\lambda_{L1}=5,
\qquad
\lambda_{\mathrm{iou}}=2.
$$

所有模型均使用：

$$
N=100
$$

个解码器查询槽（decoder query slots）进行训练。

### 基线（Baseline）

我们增强后的 Faster-RCNN+ 基线在边界框回归中使用 GIoU 损失 [6] 以及标准 $\ell_1$ 损失。

我们进行了网格搜索以寻找这些损失的最佳权重，最终模型仅使用 GIoU 损失，在边界框回归任务和候选框回归任务中的权重分别为 20 和 1。

对于基线模型，我们采用与 DETR 相同的数据增强，并使用 9× 训练计划——约为 109 个 epoch——进行训练。

其他所有设置均与 Detectron2 Model Zoo [9] 中的相同模型保持一致。

### 空间位置编码（Spatial Positional Encoding）

编码器激活与图像特征中相应的空间位置相关联。

在我们的模型中，我们使用固定绝对编码（fixed absolute encoding）来表示这些空间位置。我们采用了原始 Transformer [8] 位置编码在二维情况下的一种推广形式 [4]。

具体而言，对于每个嵌入的两个空间坐标，我们分别使用：

$$
\frac{d}{2}
$$

个具有不同频率的正弦和余弦函数。随后，将二者拼接，从而得到最终具有 $d$ 个通道的位置编码。

## 1.5 补充结果（Additional Results）

DETR-R101 模型用于全景预测的一些额外定性结果如图 2 所示。

### 损失消融实验（Loss Ablations）

为了评估匹配代价和损失函数中不同组成部分的重要性，我们通过启用或关闭不同损失项训练了多个模型。

损失中包含三个组成部分：

- 分类损失；
- $\ell_1$ 边界框距离损失；
- GIoU 损失 [6]。

分类损失对于训练而言是必需的，因此不能关闭。于是，我们训练了一个不使用边界框距离损失的模型，以及一个不使用 GIoU 损失的模型，并将二者与同时使用三种损失的基线模型进行比较。

结果见表 3。

仅使用 GIoU 损失已经能够获得模型的大部分性能，与使用组合损失的基线相比仅损失 0.7 AP。仅使用 $\ell_1$ 而不使用 GIoU 时，结果较差。

我们只研究了不同损失函数的简单消融方式——每一次均使用相同的损失权重——但采用其他损失组合方式可能会得到不同结果。

> **图 2. 全景分割预测结果比较。**
>
> **(a)** 目标发生重叠时的失败案例。PanopticFPN 完全漏掉了一架飞机，而 DETR 未能准确分割其中 3 架飞机。
>
> **(b)** thing 类别的掩码以完整分辨率进行预测，因此相比 PanopticFPN 能够得到更加清晰的边界。
>
> 从左到右依次为：真实标注（Ground truth）、使用 ResNet-101 的 PanopticFPN、使用 ResNet-101 的 DETR。

> **表 2.** 不同位置编码方案与基线模型（最后一行）的比较结果。基线模型在编码器和解码器中的每个注意力层均使用固定正弦位置编码。可学习嵌入在所有层之间共享。不使用空间位置编码会导致 AP 显著下降。值得注意的是，仅在解码器中传入空间位置编码只会导致较小的 AP 下降。所有这些模型均使用可学习的输出位置编码。

| 编码器空间位置编码 | 解码器空间位置编码 | 解码器输出位置编码 | AP | $\Delta$ | $AP_{50}$ | $\Delta$ |
|---|---|---|---:|---:|---:|---:|
| 无 | 无 | 输入处可学习 | 32.8 | -7.8 | 55.2 | -6.5 |
| 输入处正弦编码 | 输入处正弦编码 | 输入处可学习 | 39.2 | -1.4 | 60.0 | -1.6 |
| 注意力层可学习 | 注意力层可学习 | 注意力层可学习 | 39.6 | -1.0 | 60.7 | -0.9 |
| 无 | 注意力层正弦编码 | 注意力层可学习 | 39.3 | -1.3 | 60.3 | -1.4 |
| 注意力层正弦编码 | 注意力层正弦编码 | 注意力层可学习 | 40.6 | - | 61.6 | - |

> **表 3. 损失组成部分对 AP 的影响。** 我们分别训练了关闭 $\ell_1$ 损失以及关闭 GIoU 损失的两个模型。可以观察到，单独使用 $\ell_1$ 的结果较差，但将其与 GIoU 组合后可以提高 $AP_M$ 和 $AP_L$。我们的基线模型（最后一行）同时使用两种损失。

| 分类损失 | $\ell_1$ | GIoU | AP | $\Delta$ | $AP_{50}$ | $\Delta$ | $AP_S$ | $AP_M$ | $AP_L$ |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| ✓ | ✓ |  | 35.8 | -4.8 | 57.3 | -4.4 | 13.7 | 39.8 | 57.9 |
| ✓ |  | ✓ | 39.9 | -0.7 | 61.6 | 0 | 19.9 | 43.2 | 57.9 |
| ✓ | ✓ | ✓ | 40.6 | - | 61.6 | - | 19.9 | 44.3 | 60.2 |

### 解码器输出槽分析（Decoder Output Slot Analysis）

在图 3 中，我们对 COCO 2017 验证集中的所有图像进行预测，并可视化不同预测槽生成的边界框。

DETR 会为不同查询槽学习到不同的专门化模式。我们观察到，每一个预测槽都具有多种工作模式，会关注不同的区域和不同尺寸的边界框。

特别是，所有预测槽都具有预测覆盖整幅图像的大型边界框的模式，这在图中表现为排列在中部的红色点。我们推测，这与 COCO 中目标的分布有关。

> **图 3.** 对 COCO 2017 验证集所有图像中的边界框预测进行可视化。图中展示了 DETR 解码器总计 $N=100$ 个预测槽中的 20 个。每一个边界框预测都表示为一个点，该点的坐标对应边界框中心在根据每张图像尺寸归一化得到的 $1\times1$ 正方形中的位置。不同点通过颜色编码：绿色表示小边界框，红色表示大型水平边界框，蓝色表示大型垂直边界框。可以观察到，每一个预测槽都学会了针对特定区域和边界框尺寸进行专门化，并具有多种工作模式。我们注意到，几乎所有预测槽都具有预测大型、覆盖整幅图像的边界框的模式，而这类边界框在 COCO 数据集中较为常见。

### 增加实例数量（Increasing the Number of Instances）

从设计上看，DETR 无法预测超过其查询槽数量的目标，也就是说，在我们的实验中最多只能预测 100 个目标。

在本节中，我们分析 DETR 在目标数量逐渐逼近这一上限时的行为。

我们选取某个给定类别的一张标准正方形图像，将其重复排列成一个 $10\times10$ 的网格，并计算模型漏检实例所占的百分比。

为了在少于 100 个实例的情况下测试模型，我们随机遮蔽其中一部分网格单元。这样可以保证，无论当前可见多少目标，每个目标的绝对尺寸都保持一致。

为了消除随机遮蔽带来的随机性，我们使用不同的遮蔽方式重复实验 100 次。

结果如图 4 所示。

不同类别上的模型行为相似。当可见实例数量不超过 50 时，模型能够检测所有实例；随后，模型开始趋于饱和，并漏掉越来越多的实例。

值得注意的是，当图像中包含全部 100 个实例时，模型平均只能检测出其中 30 个。这一数量甚至低于图像中只包含 50 个实例时的结果——在后一种情况下，50 个实例全部都能被检测出来。

模型这一违反直觉的行为很可能是因为此时的图像和检测目标都明显偏离了训练数据分布。

> **图 4.** 分析图像中存在不同数量目标时，DETR 对不同类别实例的漏检情况。我们报告均值和标准差。随着实例数量逐渐接近 100，DETR 开始趋于饱和，并漏掉越来越多的目标。

需要注意的是，从设计上说，这一测试本身就是一个分布外泛化（out-of-distribution generalization）实验，因为训练数据中几乎没有包含大量同一类别实例的图像。

从该实验中很难将以下两种分布外泛化因素彼此区分：

- 图像本身的分布外性质；
- 每个类别中目标数量的分布外性质。

但是，由于 COCO 中几乎不存在只包含大量同一类别目标的图像，这种实验已经是我们用于理解目标查询是否对数据集的类别与位置分布发生过拟合的最佳尝试。

总体而言，实验表明，模型并没有在这些分布上发生明显过拟合，因为当目标数量不超过 50 时，它仍然能够获得近乎完美的检测结果。

## 1.6 PyTorch 推理代码（PyTorch Inference Code）

为了展示本方法的简洁性，我们在代码清单 1 中给出了基于 PyTorch 和 Torchvision 库的推理代码。

该代码可运行于：

- Python 3.6+
- PyTorch 1.4
- Torchvision 0.5

需要注意的是，该代码不支持批处理，因此仅适用于推理，或者在每块 GPU 仅使用一张图像的情况下，通过 `DistributedDataParallel` 进行训练。

还需要注意的是，为了提高代码的清晰度，这段代码在编码器中使用可学习位置编码，而不是固定位置编码；同时，位置编码只在输入处添加一次，而不是在 Transformer 的每一层中添加。

如果要实现这些修改，就需要超出 PyTorch 自带 Transformer 实现的范围，这会降低代码的可读性。

用于复现实验的完整代码将在会议召开前公开。

```python
import torch
from torch import nn
from torchvision.models import resnet50


class DETR(nn.Module):

    def __init__(self, num_classes, hidden_dim, nheads,
                 num_encoder_layers, num_decoder_layers):
        super().__init__()
        # 我们仅使用 ResNet-50 模型中的卷积层
        self.backbone = nn.Sequential(
            *list(resnet50(pretrained=True).children())[:-2]
        )
        self.conv = nn.Conv2d(2048, hidden_dim, 1)
        self.transformer = nn.Transformer(
            hidden_dim,
            nheads,
            num_encoder_layers,
            num_decoder_layers
        )
        self.linear_class = nn.Linear(hidden_dim, num_classes + 1)
        self.linear_bbox = nn.Linear(hidden_dim, 4)
        self.query_pos = nn.Parameter(torch.rand(100, hidden_dim))
        self.row_embed = nn.Parameter(torch.rand(50, hidden_dim // 2))
        self.col_embed = nn.Parameter(torch.rand(50, hidden_dim // 2))

    def forward(self, inputs):
        x = self.backbone(inputs)
        h = self.conv(x)
        H, W = h.shape[-2:]
        pos = torch.cat([
            self.col_embed[:W].unsqueeze(0).repeat(H, 1, 1),
            self.row_embed[:H].unsqueeze(1).repeat(1, W, 1),
        ], dim=-1).flatten(0, 1).unsqueeze(1)
        h = self.transformer(
            pos + h.flatten(2).permute(2, 0, 1),
            self.query_pos.unsqueeze(1)
        )
        return self.linear_class(h), self.linear_bbox(h).sigmoid()


detr = DETR(
    num_classes=91,
    hidden_dim=256,
    nheads=8,
    num_encoder_layers=6,
    num_decoder_layers=6
)
detr.eval()
inputs = torch.randn(1, 3, 800, 1200)
logits, bboxes = detr(inputs)
```

> **代码清单 1. DETR 的 PyTorch 推理代码。** 为了提高可读性，该代码在编码器中使用可学习位置编码，而不是固定位置编码，并且仅在输入处加入位置编码，而不是在 Transformer 的每一层中加入。如果实现论文实验中使用的这些差异，就需要超出 PyTorch 自带 Transformer 实现的范围，这会降低代码的可读性。用于复现实验的完整代码将在会议召开前公开。

## 1.7 致谢（Acknowledgements）

我们感谢 Sainbayar Sukhbaatar、Piotr Bojanowski、Natalia Neverova、David Lopez-Paz、Guillaume Lample、Danielle Rothermel、Kaiming He、Ross Girshick、Xinlei Chen、Aishwarya Kamath，以及 Facebook AI Research Paris 的全体团队成员所进行的讨论并提出的建议；如果没有他们，本项工作将不可能完成。

# 参考文献（References）

[1] Cordonnier, J.B., Loukas, A., Jaggi, M.  
**On the relationship between self-attention and convolutional layers.**  
**中文译名：** 论自注意力与卷积层之间的关系。  
In: ICLR（International Conference on Learning Representations，国际学习表征会议）, 2020.

[2] Loshchilov, I., Hutter, F.  
**Decoupled weight decay regularization.**  
**中文译名：** 解耦权重衰减正则化。  
In: ICLR（International Conference on Learning Representations，国际学习表征会议）, 2017.

[3] Milletari, F., Navab, N., Ahmadi, S.A.  
**V-Net: Fully convolutional neural networks for volumetric medical image segmentation.**  
**中文译名：** V-Net：用于体积医学图像分割的全卷积神经网络。  
In: 3DV（International Conference on 3D Vision，国际三维视觉会议）, 2016.

[4] Parmar, N., Vaswani, A., Uszkoreit, J., Kaiser, L., Shazeer, N., Ku, A., Tran, D.  
**Image Transformer.**  
**中文译名：** Image Transformer：图像 Transformer。  
In: ICML（International Conference on Machine Learning，国际机器学习会议）, 2018.

[5] Ren, M., Zemel, R.S.  
**End-to-end instance segmentation with recurrent attention.**  
**中文译名：** 使用循环注意力的端到端实例分割。  
In: CVPR（IEEE Conference on Computer Vision and Pattern Recognition，计算机视觉与模式识别会议）, 2017.

[6] Rezatofighi, H., Tsoi, N., Gwak, J., Sadeghian, A., Reid, I., Savarese, S.  
**Generalized intersection over union.**  
**中文译名：** 广义交并比。  
In: CVPR（IEEE Conference on Computer Vision and Pattern Recognition，计算机视觉与模式识别会议）, 2019.

[7] Romera-Paredes, B., Torr, P.H.S.  
**Recurrent instance segmentation.**  
**中文译名：** 循环实例分割。  
In: ECCV（European Conference on Computer Vision，欧洲计算机视觉会议）, 2015.

[8] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A.N., Kaiser, L., Polosukhin, I.  
**Attention is all you need.**  
**中文译名：** 注意力机制就是你所需要的一切。  
In: NeurIPS（Conference on Neural Information Processing Systems，神经信息处理系统大会）, 2017.

[9] Wu, Y., Kirillov, A., Massa, F., Lo, W.Y., Girshick, R.  
**Detectron2.**  
**中文译名：** Detectron2。  
https://github.com/facebookresearch/detectron2, 2019.