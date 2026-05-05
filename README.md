# 🧠 Para-QA: Parahydrogen Hyperpolarization Intelligent QA Assistant

**Para-QA** 是一个面向仲氢超极化（PHIP / SABRE）领域的智能问答系统，结合大语言模型（LLMs）与检索增强生成（RAG），用于支持跨学科研究者快速理解复杂文献与实验机制。

## 📌 项目背景

仲氢超极化（Parahydrogen-Induced Polarization, PHIP）及其扩展方法（如 SABRE）涉及：

- 有机化学
- 催化化学
- 核磁共振（NMR）
- 量子物理

其文献高度碎片化、跨学科壁垒明显，对初学者和跨领域研究者不友好。

**Para-QA 的目标**是构建一个：

> 可解释、可追溯、基于文献的智能问答系统用于降低学习门槛并提升科研效率。

## 🧩 系统架构

```
User Query
    ↓
Query Processing
    ↓
Retriever (Top-k passages)
    ↓
Context Construction
    ↓
LLM Generator
    ↓
Answer + Evidence
```

核心模块：

- **Retriever**：基于向量数据库的语义检索
- **Generator**：大语言模型（支持 GPT / Qwen / LLaMA 等）
- **Knowledge Base**：PHIP/SABRE 专业文献语料
- **Evaluation Module**：QAC benchmark 自动评估

## 🚀 功能特点

### 1. 📚 文献驱动问答（Literature-grounded QA）

- 所有回答基于真实文献
- 支持引用证据（context grounding）

### 2. 🔍 检索增强生成（RAG）

- Top-k 相关段落检索
- 降低 hallucination 风险

### 3. 🧪 专业领域适配

支持问题类型包括：

- PHIP / SABRE 机制
- 催化剂作用（如 Ir 配合物）
- NMR 增强原理
- 实验参数解释
- 对比不同超极化方法

### 4. 📊 QAC 评估框架

构建 **Question–Answer–Context (QAC)** 数据集用于：

- 检索质量评估
- 生成答案准确性评估
- 系统对比实验

## 🧠 技术栈

- **LLMs**: DeepSeek-R1
- **Embedding**: bge-m3-embedding
- **Reranker**: bge-reranker-v2-m3
- **Vector DB**: Milvus
- **Framework**: Dify / RAGAS
- **Pipeline**: RAG (Retrieval-Augmented Generation)

## 📈 未来工作

-  多模态支持（NMR谱图 + 文本）
-  专家级推理（Chain-of-Thought for chemistry）
-  自动文献更新（持续学习）
-  实验设计辅助（AI-assisted PHIP optimization）

## 📄 引用

如果你在研究中使用了 Para-QA，请引用：

未发表

