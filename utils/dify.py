import uuid
import json
import pathlib
import requests

from abc import ABCMeta, abstractmethod
from enum import Enum
from codecs import encode


class ResponseMode(Enum):
    STREAMING = "streaming"
    BLOCKING = "blocking"


class BaseClient(metaclass=ABCMeta):
    def __init__(self, api_key=None, base_url=None, user=None):
        self.api_key = api_key
        self.base_url = base_url
        self.user = user
    
    @abstractmethod
    def request(self, *args, **kwargs):
        """抽象方法，必须由子类实现具体的请求逻辑"""
        pass
    
    # 公共的getter方法
    def get_api_key(self):
        """获取当前配置的API密钥"""
        return self.api_key
    
    def get_base_url(self):
        """获取当前配置的基础URL"""
        return self.base_url
    
    def get_user(self):
        """获取当前配置的用户标识"""
        return self.user
    
    # 公共的setter方法
    def set_api_key(self, api_key):
        """设置当前配置的API密钥"""
        self.api_key = api_key
    
    def set_base_url(self, base_url):
        """设置当前配置的基础URL"""
        self.base_url = base_url
    
    def set_user(self, user):
        """设置当前配置的用户标识"""
        self.user = user
        

class FileUploadClient(BaseClient):
    def __init__(self, api_key=None, base_url=None, user=None):
        super().__init__(api_key, base_url, user)
    
    def request(self, file_path: str):
        # 判断 file_path 是存在的
        if not pathlib.Path(file_path).exists():
            print(f"File not found: {file_path}")
            return None
        
        # 获取文件类型
        fileType = 'application/octet-stream'
                
        # 生成boundary
        boundary = uuid.uuid4().hex

        # 构造请求参数
        headers = {
            "Authorization": f'Bearer {self.api_key}',
            'Content-type': f'multipart/form-data; boundary={boundary}'
        }
        
        dataList = []
        dataList.append(encode('--' + boundary))

        dataList.append(encode(
            f'Content-Disposition: form-data; name=file; filename={pathlib.Path(file_path).name}'
        ))

        dataList.append(encode('Content-Type: {}'.format(fileType)))
        dataList.append(encode(''))

        with open(file_path, 'rb') as f:
            dataList.append(f.read())

        dataList.append(encode('--' + boundary))

        dataList.append(encode('Content-Disposition: form-data; user=user;'))
        dataList.append(encode('Content-Type: {}'.format('text/plain')))
        dataList.append(encode(''))

        dataList.append(encode(self.user))
        dataList.append(encode('--'+boundary+'--'))
        dataList.append(encode(''))

        body = b'\r\n'.join(dataList)

        # 发送请求
        response = requests.request("POST", self.base_url, headers=headers, data=body)
        
        # 返回响应结果
        return response.json()
    
    
class WorkFlowRunClient(BaseClient):
    def __init__(self, api_key=None, base_url=None, user=None):
        super().__init__(api_key, base_url, user)
    
    def request(self, param_name: str, upload_file_id: str, response_mode: ResponseMode = ResponseMode.BLOCKING): 
        # 构造请求参数
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        # 构造请求体
        data = json.dumps({
            "inputs": {
                param_name: {
                    "type": "document",
                    "transfer_method": "local_file",
                    "upload_file_id": upload_file_id
                }
            },
            "response_mode": response_mode.value,
            "user": self.user
        })
        
        # 发送请求
        response = requests.request("POST", self.base_url, headers=headers, data=data)
        res = response.json()

        return res


class ChatMessageClient(BaseClient):
    def __init__(self, api_key=None, base_url=None, user=None):
        super().__init__(api_key, base_url, user)
        
    def request(self, message: str):
        # 构造请求参数
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        # 构造请求体
        data = json.dumps({
            "inputs": {},
            "query": message,
            "conversation_id": "",
            "response_mode": ResponseMode.BLOCKING.value,
            "user": self.user,
            "files": []
        })
        
        # 发送请求
        response = requests.request("POST", self.base_url, headers=headers, data=data)
        data = json.loads(response.text)
        
        return data

        

