import pandas as pd
from loguru import logger
from langfuse import Langfuse
from langfuse.client import DatasetItemClient
from datetime import datetime
from typing import Optional, Literal, List
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from tqdm.asyncio import tqdm

import aiohttp
import asyncio


class DifyClient:
    def __init__(self, api_key: str, base_url: str, user: str):
        self._api_key = api_key
        self._base_url = base_url
        self._user = user
        self._session = None

    @property
    async def session(self):
        """懒加载session，确保正确的事件循环"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """安全关闭session"""
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        stop=stop_after_attempt(5),  # 重试5次
        wait=wait_fixed(2),  # 每次重试等待2秒
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True  # 重试后仍失败则抛出原始异常
    )
    async def send_chat_message(
        self, query: str,
        response_mode: Literal["streaming", "blocking"] = "blocking"
    ):
        session = await self.session

        # 构造请求头
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # 构造请求体
        payload = {
            "inputs": {},
            "query": query,
            "conversation_id": "",
            "response_mode": response_mode,
            "user": self._user,
            "files": []
        }

        # 发送异步请求
        async with session.post(self._base_url, headers=headers, json=payload) as response:
            ret = await response.json()

            status = ret.get("status")
            message = ret.get("message")

            if status and message:
                logger.exception(
                    f"Request with query {query} failed with status {status} and message {message}"
                )
                raise RuntimeError(f"{status}: {message}")
            if ret.get("answer") == "":
                logger.exception(
                    f"Request with query {query} get empty answer"
                )
                raise RuntimeError(f"Empty answer. {status}: {message}")

            return ret

    async def run_dify_task(
        self, item: DatasetItemClient,
        run_name: Optional[str] = None,
        semaphore: asyncio.Semaphore | None = None
    ):
        async with semaphore:
            # 记录输出
            logger.info(f"Running dify task with item_id {item.id}")

            # 发送请求
            resp = await self.send_chat_message(item.input)

            # 追踪 Langfuse 中的测试结果
            item.link(
                trace_or_observation=None,
                run_name=run_name,
                trace_id=resp["message_id"],
                observation_id=None,
            )

            return resp

    async def run_dify_experiment(
        self,
        langfuse: Langfuse,
        dataset_name: str,
        run_name: str = None,
        output_path: Optional[str] = None,
        time_asc_submit: bool = True,
    ):
        """
        用于提交 Langfuse 数据集到 Dify 进行测试

        Parameters
        ----------
        langfuse : Langfuse
            Langfuse 客户端实例
        dataset_name : str
            Langfuse 数据集名称
        run_name : str, optional
            运行名称，默认为当前时间戳
        output_path : str, optional
            输出路径，默认为 None
        time_asc_submit : bool, optional
            是否按照时间升序提交，默认为 True

        Returns
        -------
        list
            包含所有测试结果的列表
        """
        if not dataset_name:
            raise ValueError("No dataset name provided")

        if not run_name:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        logger.info(f"Starting dataset {dataset_name} with run_name {run_name}")

        # 创建 langfuse dataset client
        try:
            dataset = langfuse.get_dataset(dataset_name)
            items = dataset.items
            logger.success(f"Submitting dataset {dataset_name} with run_name {run_name} to Dify. Total: {len(items)}")
        except Exception as e:
            logger.error(f"Failed to submit dataset {dataset_name} with run_name {run_name}: {e}")
            raise RuntimeError(f"Failed to get dataset {dataset_name} with run_name {run_name}: {e}")

        if time_asc_submit:
            items = list(reversed(items))
            logger.info(f"Sorting {len(items)} items by time ascending")

        # 创建异步任务
        semaphore = asyncio.Semaphore(5)
        tasks = []
        input_data = []

        for item in items:
            task = asyncio.create_task(
                self.run_dify_task(item, run_name, semaphore)
            )
            input_data.append(item.input)
            tasks.append(task)

        results = await tqdm.gather(*tasks, desc="Processing items", total=len(tasks))
        # 保存结果
        DifyClient.save_results(results, output_path, items)

        return results

    @staticmethod
    def save_results(results: List[dict], output_path: str, dataset_items: List[DatasetItemClient]):
        answers = []
        for result in results:
            answers.append(result["answer"].strip())

        questions = []
        for item in dataset_items or []:
            questions.append(item.input)

        if questions:
            df = pd.DataFrame({"question": questions, "answer": answers})
        else:
            df = pd.DataFrame(answers, columns=["answer"])

        if not output_path:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = f"{current_time}.csv"
        else:
            local_path = output_path

        df.to_csv(local_path, index=False)
        logger.success(f"Results saved to {local_path}")
