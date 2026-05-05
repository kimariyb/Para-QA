import json
import os
import pandas as pd
import re

from typing import Any


def contains_chinese_deep(data: Any, chinese_pattern: re.Pattern) -> bool:
    """
    深度递归检查任何数据结构中是否包含中文字符

    参数:
        data: 任意数据类型（dict, list, str等）
        chinese_pattern: 预编译的中文字符正则

    返回:
        是否包含中文字符
    """
    # 字符串类型：直接检测
    if isinstance(data, str):
        # 检查Unicode编码中文和原生中文
        return chinese_pattern.search(data) is not None

    # 字典类型：递归检查所有值
    if isinstance(data, dict):
        return any(contains_chinese_deep(value, chinese_pattern) for value in data.values())

    # 列表/元组类型：递归检查所有元素
    if isinstance(data, (list, tuple)):
        return any(contains_chinese_deep(item, chinese_pattern) for item in data)

    # 其他类型：不需要检查
    return False


def get_jsonl_data(file_path):
    data = []
    # 编译全面的中文检测正则
    chinese_pattern = re.compile(
        r'['  # 开始字符集
        r'\u4e00-\u9fff'       # 基本汉字
        r'\u3400-\u4dbf'       # 扩展A
        r'\U00020000-\U0002a6df'  # 扩展B
        r'\U0002a700-\U0002b73f'  # 扩展C
        r'\U0002b740-\U0002b81f'  # 扩展D
        r'\U0002b820-\U0002ceaf'  # 扩展E
        r'\uf900-\ufaff'        # 兼容汉字
        r']'
    )
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()

            if not stripped_line:
                continue

            try:
                json_obj = json.loads(stripped_line)
            except json.decoder.JSONDecodeError as e:
                print(f"JSON Decode Error: {stripped_line}. Error: {e}")
                continue

            if "NaN" in stripped_line:
                continue
            if "None" in stripped_line:
                continue

            # 深度检测中文（递归检查所有层级）
            if contains_chinese_deep(json_obj, chinese_pattern):
                continue

            data.append(json_obj)

    return data


def merge_jsonl_data(file_paths) -> list[dict]:
    data = []
    for file_path in file_paths:
        data += get_jsonl_data(file_path)
    print(f"Merging {len(file_paths)} jsonl files...")
    return data
    

if __name__ == '__main__':
    # 如果当前目录存在 qac.jsonl 则跳过这部分代码
    if os.path.exists('qac.jsonl'):
        print("qac.jsonl already exists, skipping...")

        # 随机在 qac.jsonl 中选择

    else:
        print("qac.jsonl does not exist, creating...")
        files = [
            os.path.join('./qac_jsonls', file)
            for file in os.listdir('./qac_jsonls')
        ]

        # get the data from the jsonl files
        jsonl_datas = merge_jsonl_data(files)
        print(f"The total number of jsonl data is {len(jsonl_datas)}")
        # convert the data to a pandas dataframe
        df = pd.DataFrame(jsonl_datas)
        # save the dataframe to a jsonl file
        df.to_json(os.path.join('qac.jsonl'), orient='records', lines=True, force_ascii=False)