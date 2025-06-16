from ragas.evaluation import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Metric as RagasMetric
from langfuse import Langfuse
from langfuse.client import ObservationsView, TraceWithDetails

from typing import List, Optional
from loguru import logger


class RAGEvaluator:
    def __init__(self, langfuse: Langfuse, llm: LangchainLLMWrapper, embeddings: LangchainEmbeddingsWrapper):
        self.langfuse = langfuse
        self.llm = llm
        self.embeddings = embeddings

    def _get_ground_truth_map(self, dataset_name: str) -> dict[str, dict]:
        """获取 Langfuse 数据集的 ground truth"""
        dataset = self.langfuse.get_dataset(dataset_name)

        ground_truth_map = {}
        for item in dataset.items:
            # 如果没有 input; expected_output; metadata 则跳过
            if not item.input or not item.expected_output or not item.metadata:
                logger.warning(f"Item {item.id} has no input, expected_output, or metadata. Skipping.")
                continue

            ground_truth_map[item.input] = {
                "expected_output": item.expected_output,
                "context": item.metadata,
            }

        return ground_truth_map

    def _fetch_traces(self, user_id: str, page: int = 1, limit: int = 10) -> List[TraceWithDetails]:
        """跟踪 Langfuse 中的 trace 结果"""
        return self.langfuse.fetch_traces(user_id=user_id, page=page, limit=limit).data

    def _fetch_observations(self, name: str, trace_id: str) -> List[ObservationsView]:
        """跟踪 Langfuse 中的 observations 结果"""
        return self.langfuse.fetch_observations(name=name, trace_id=trace_id).data

    def _run_evaluate(
        self,
        metrics: List[RagasMetric],
        page: int = 1,
        limit: int = 10,
        run_name: Optional[str] = None,
        ground_truth_map: dict = None,
    ):
        traces = self._fetch_traces(
            user_id=run_name,
            page=page,
            limit=limit,
        )

        logger.info(
            f"Page {page} of traces with limit {limit}. {len(traces)} traces found. Start evaluating."
        )

        for trace in traces:
            self._trace_evaluate_item(
                metrics=metrics,
                trace=trace,
                ground_truth_map=ground_truth_map,
            )

        return len(traces)

    def _trace_evaluate_item(
        self,
        trace: TraceWithDetails,
        metrics: list,
        ground_truth_map: dict,
    ):
        logger.info(f"Evaluating {trace.id}")

        # 首先拿到 name == llm 的 observations
        llm_observations = self._fetch_observations(name="llm", trace_id=trace.id)
        if not llm_observations:
            logger.warning(f"No llm observations found for trace {trace.id}")
            return

        # 然后拿到 name == dataset_retrieval 的 observations
        dataset_retrieval_observations = self._fetch_observations(name="dataset_retrieval", trace_id=trace.id)
        if not dataset_retrieval_observations:
            logger.warning(f"No dataset_retrieval observations found for trace {trace.id}")
            return

        # user_input: 用户输入的问题
        llm_input = llm_observations[0].input
        user_input = next((
            msg["content"] for msg in llm_input if msg["role"] == "user"
        ))
        # retrieved_contexts: AI 召回的相关文本
        dataset_retrieval_output = dataset_retrieval_observations[0].output
        retrieved_contexts = [
            doc["page_content"] for doc in dataset_retrieval_output["documents"]
        ]
        # reference_contexts: 人给出的正确召回片段
        reference_contexts = [ground_truth_map[user_input]["context"]]
        # response: AI 生成的回答
        llm_output = llm_observations[0].output
        response = next((
            msg["content"] for msg in llm_output if msg["role"] == "assistant"
        ))
        # reference: 人给出的正确答案
        reference = ground_truth_map[user_input]["expected_output"]

        # 创建一个 SingleTurnSample
        sample = SingleTurnSample(
            user_input=str(user_input),
            retrieved_contexts=retrieved_contexts,
            reference_contexts=reference_contexts,
            response=str(response),
            reference=str(reference),
        )

        logger.debug(
            f"Trace {trace.id}"
        )

        # 使用 ragas 评估结果
        ragas_metrics = [
            metric for metric in metrics
            if isinstance(metric, RagasMetric)
        ]

        if ragas_metrics:
            self._ragas_generation_evaluate(
                metrics=ragas_metrics,
                sample=sample,
                trace_id=trace.id,
            )


    def _ragas_generation_evaluate(
        self,
        metrics: List[RagasMetric],
        sample: SingleTurnSample,
        trace_id: Optional[str] = None
    ):
        """
        使用 RAGAS 评估生成结果

        Parameters
        ----------
        metrics : List[RagasMetric]
            评估指标
        sample : SingleTurnSample
            数据集样本
        trace_id : Optional[str]
            追踪 ID，可选，用于 Langfuse 追踪
        """
        # 获取 Dataset
        dataset = EvaluationDataset(samples=[sample])

        # 使用 ragas 测评
        result = evaluate(
            dataset,
            metrics=metrics,
            llm=self.llm,
            embeddings=self.embeddings
        )
        logger.info(f"Ragas evaluate result: {result}")

        if trace_id:
            for metric in result.scores:
                for metric_type, metric_value in metric.items():
                    self.langfuse.score(
                        trace_id=trace_id,
                        name=metric_type,
                        value=metric_value,
                    )

        return result

    def run_evaluate_dataset(self, metrics: list, run_name: str, dataset_name: str, batch_size: int):
        # 首先获取 langfuse 中的 Dataset ground truth list
        ground_truth_map = self._get_ground_truth_map(dataset_name)

        logger.debug(
            f"Evaluating {run_name} on {dataset_name} dataset. Get {len(ground_truth_map)} samples."
        )

        page = 1
        while True:
            # 每次获取 batch_size 条 trace
            count = self._run_evaluate(
                metrics=metrics,
                page=page,
                limit=batch_size,
                run_name=run_name,
                ground_truth_map=ground_truth_map,
            )

            page += 1
            if count < batch_size:
                break

            logger.success(f"Finished evaluating dataset: {dataset_name}.")