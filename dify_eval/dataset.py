from datetime import datetime
from typing import Any
from langfuse import Langfuse
from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import List
from loguru import logger

import pandas as pd


class QACDataItem(BaseModel):
    input: str | dict
    expected_output: str | None
    metadata: Any


class QACDataset:
    def __init__(
        self,
        langfuse: Langfuse,
        file_path: str,
        input_column: str = "question",
        output_column: str = "answer",
        metadata_column: str = "context",
        encoding: str = 'utf-8',
        file_type: str = 'jsonl'
    ):
        self.langfuse = langfuse
        self.datas = ExtractorBuilder(
            file_path=file_path,
            input_column=input_column,
            output_column=output_column,
            metadata_column=metadata_column,
            encoding=encoding,
        ).build(file_type=file_type).extract()

    def create_langfuse_dataset_item(self, dataset_name):
        try:
            for data in self.datas:
                self.langfuse.create_dataset_item(
                    dataset_name=dataset_name,
                    input=data.input,
                    expected_output=data.expected_output,
                    metadata=data.metadata
                )
        except Exception as e:
            raise RuntimeError(f"Failed to create dataset item: {e}")

    def create_langfuse_dataset(self, dataset_name: str, always_add: bool = False):
        # 判断是否存在 Dataset
        is_dataset_exist = False
        try:
            # Check if the dataset already exists
            self.langfuse.get_dataset(dataset_name)
            # 如果没有异常，说明数据集存在
            is_dataset_exist = True
            logger.info(f"Dataset {dataset_name} already exists. Skipping creation.")

            if always_add:
                self.create_langfuse_dataset_item(dataset_name)
                logger.info(f"Inserted dataset {dataset_name} into langfuse dataset. Total: {len(self.datas)}")
        finally:
            # 无论是否存在数据集，都执行这个代码块
            if not is_dataset_exist:
                logger.info(f"Dataset {dataset_name} is not exist. Creating...")
                self.langfuse.create_dataset(
                    name=dataset_name,
                    description="QA dataset",
                    metadata={
                        "author": "kimariyb",
                        "date": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        "type": "benchmark"
                    }
                )
                self.create_langfuse_dataset_item(dataset_name)
                logger.success(f"Created dataset {dataset_name} successfully. Total: {len(self.datas)}")

    def __len__(self):
        return len(self.datas)

    def __getitem__(self, idx):
        return self.datas[idx]

    def __iter__(self):
        for data in self.datas:
            yield data


class BaseExtractor(ABC):
    def __init__(
        self,
        file_path: str,
        input_column: str = "question",
        output_column: str = "answer",
        metadata_column: str = "context",
        encoding: str = "utf-8",
    ):
        self.file_path = file_path
        self.input_column = input_column
        self.output_column = output_column
        self.metadata_column = metadata_column
        self.encoding = encoding

    @abstractmethod
    def extract(self) -> List[QACDataItem]:
        raise NotImplementedError
    
    
class JSONLinesExtractor(BaseExtractor):
    def __init__(self, file_path: str, input_column: str = "question", output_column: str = "answer",
                 metadata_column: str = "context"):
        super().__init__(file_path, input_column, output_column, metadata_column)

        # read the JSONL file
        self.df = pd.read_json(self.file_path, encoding=self.encoding, lines=True)

    def extract(self) -> List[QACDataItem]:
        dataset_items = []
        for idx, row in self.df.iterrows():
            dataset_items.append(
                QACDataItem(
                    input=row.get(self.input_column),
                    expected_output=row.get(self.output_column),
                    metadata=row.get(self.metadata_column),
                )
            )

        return dataset_items


class ExtractorBuilder:
    def __init__(
        self,
        file_path: str,
        input_column: str = "question",
        output_column: str = "answer",
        metadata_column: str = "context",
        encoding: str = "utf-8"
    ):
        self.file_path = file_path
        self.input_column = input_column
        self.output_column = output_column
        self.metadata_column = metadata_column
        self.encoding = encoding

    def build(self, file_type: str) -> BaseExtractor:
        if file_type == "jsonl":
            return JSONLinesExtractor(self.file_path, self.input_column, self.output_column, self.metadata_column)
        else:
            raise ValueError("Unsupported file type")

