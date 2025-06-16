import os
import asyncio

from dotenv import load_dotenv
from langfuse import Langfuse
from loguru import logger
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas import metrics

from dify_eval.client import DifyClient
from dify_eval.dataset import QACDataset
from dify_eval.evaluator import RAGEvaluator

# 读取 .env 环境变量
load_dotenv()

# 设置变量
RUN_NAME = "abc-123"
DATASET_NAME = "qac_test"
OUTPUT_PATH = "qac_test_output.csv"
BATCH_SIZE = 10
METRICS_TYPE = [
    metrics.answer_correctness,
    metrics.answer_relevancy,
    metrics.answer_similarity,
    metrics.faithfulness,
    metrics.context_precision,
    metrics.context_recall,
]

if __name__ == '__main__':
    # 初始化 Langfuse 客户端
    langfuse = Langfuse()
    auth_result = langfuse.auth_check()
    if auth_result:
        logger.success("Langfuse Authentication Successful.")
        # 第一步：将 JSONL 文件转换为 Langfuse 数据集
        try:
            # 创建 QACDataset 实例
            qac_dataset = QACDataset(
                langfuse=langfuse,
                file_path="qac_test.jsonl"
            )
            # 创建 Langfuse 数据集
            qac_dataset.create_langfuse_dataset(dataset_name=DATASET_NAME, always_add=False)
        except Exception as e:
            logger.exception(f"Failed to create Langfuse dataset: {e}")
            raise

        # 第二步：将 Langfuse 数据集提交到 Dify 中并获取结果
        try:
            logger.info("Creating the Dify Client")
            # 创建 Client 用于连接 Dify
            dify_client = DifyClient(
                api_key=os.getenv("DIFY_API_KEY"),
                base_url=os.getenv("DIFY_API_BASE"),
                user=RUN_NAME
            )

            # 如果不存在 output_path 目录，则执行
            if not os.path.exists(OUTPUT_PATH):
                # 提交任务到 Dify
                logger.info(f"Creating the asyncio loop for Dify client")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.debug(f"Starting Dify client run experiment with dataset {DATASET_NAME}")
                results = loop.run_until_complete(
                    dify_client.run_dify_experiment(
                    langfuse=langfuse,
                    dataset_name=DATASET_NAME,
                    run_name=RUN_NAME,
                    output_path=OUTPUT_PATH
                ))
                logger.success("Dify experiment completed successfully.")

                # 关闭 session
                loop.run_until_complete(dify_client.close())
            else:
                logger.info(f"Output path {OUTPUT_PATH} already exists. Skipping Dify experiment.")
        except Exception as e:
            logger.exception(f"Failed to run Dify experiment: {e}")
            raise

        # 第三步：使用 RAGAS 评估 Dify 的生成结果
        try:
            logger.info("Creating the LLM and Embeddings.")
            # 创建 LLM 和 Embeddings 模型
            llm = LangchainLLMWrapper(
                ChatOpenAI(
                    model=os.getenv("LLM_MODEL_NAME"),
                    api_key=os.getenv("LLM_API_KEY"),
                    base_url=os.getenv("LLM_BASE_URL"),
                    temperature=0,
                    max_tokens=None,
                    timeout=None,
                    max_retries=2,
                )
            )
            logger.success("LLM successfully created.")
            embeddings = LangchainEmbeddingsWrapper(
                OpenAIEmbeddings(
                    model=os.getenv("EMBEDDING_MODEL_NAME"),
                    base_url=os.getenv("EMBEDDING_BASE_URL"),
                    api_key=os.getenv("LLM_API_KEY"),
                )
            )
            logger.success("Embeddings successfully created.")
        except Exception as e:
            logger.exception(f"Failed to initialize LLM or Embeddings: {e}")
            raise

        try:
            logger.info("Starting RAG evaluation.")
            # 创建 RAG 评估器
            rag_evaluator = RAGEvaluator(
                langfuse=langfuse,
                llm=llm,
                embeddings=embeddings
            )
            # 测试 Dify 生成结果
            rag_evaluator.run_evaluate_dataset(
                metrics=METRICS_TYPE,
                run_name=RUN_NAME,
                dataset_name=DATASET_NAME,
                batch_size=BATCH_SIZE
            )
        except Exception as e:
            logger.exception(f"Failed to evaluate RAG: {e}")
            raise

    else:
        logger.error("Langfuse Authentication Failed")



