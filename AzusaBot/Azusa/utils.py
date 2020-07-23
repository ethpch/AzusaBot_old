# 定义常用工具集。
import time
import os
import base64
import csv
import ujson as json

# simple time counter
class Timer:
    def __init__(self, func=time.perf_counter):
        self.elapsed = 0.0
        self.run = False
        self._func = func
        self._start = None

    def start(self):
        if self._start is not None:
            raise RuntimeError('Already started')
        self._start = self._func()
        self.run = True

    def stop(self):
        if self._start is None:
            raise RuntimeError('Not started')
        end = self._func()
        self.elapsed += end - self._start
        self._start = None

    def reset(self):
        self.elapsed = 0.0

    @property
    def running(self):
        return self._start is not None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

# data save and load
class storage:

    __storageObjs = {}

    def __init__(self, name: str):
        if not os.path.exists(os.path.join(os.path.dirname(__file__), 'data')):
            os.mkdir(os.path.join(os.path.dirname(__file__), 'data'))
        self.__path = os.path.join(os.path.dirname(__file__), 'data', name)
        if not os.path.exists(self.__path):
            os.mkdir(self.__path)

    # 使用该方法获取模块级别的storage对象
    @classmethod
    def getStorageObj(cls, submodule: str):
        """获取模块级别的storage对象"""
        if submodule not in cls.__storageObjs:
            cls.__storageObjs[submodule] = storage(submodule)
        return cls.__storageObjs[submodule]

    @staticmethod
    def __save(filename: str, data: dict):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii = False, indent = 4)

    @staticmethod
    def __load(filename: str) -> dict:
        if os.path.exists(filename):
            if os.path.getsize(filename) > 0:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
        return {}

    # 保存为json文件
    def save(self, filename: str='data', data: dict={}) -> str:
        """将字典保存为json文件。
        参数：
            filename：文件名，如后缀不为“.json”则会自动添加
            data：要保存的字典
        返回值：
            返回一个字符串，值为全部文件名
        """
        if not filename.endswith('.json'):
            filename = os.path.join(self.__path, f'{filename}.json')
        else:
            filename = os.path.join(self.__path, filename)
        self.__save(filename, self.load(filename, data))
        return os.path.split(filename)[1]

    # 从json文件读取数据
    def load(self, filename: str='data', data: dict = {}) -> dict:
        """从json文件读取数据并转换为python字典。
        参数：
            filename：文件名，如后缀不为“.json”则会自动添加
            data：要合并的字典
        返回值：
            返回一个字典，值为读取的数据与传入data的合并字典
        """
        if not filename.endswith('.json'):
            filename = os.path.join(self.__path, f'{filename}.json')
        else:
            filename = os.path.join(self.__path, filename)
        loaded = self.__load(filename)
        loaded.update(data)
        return loaded

    # 将矩阵列表保存为csv文件，需要处理好矩阵列表数据
    def save_to_csv(self, filename: str='data', data: list=[]) -> str:
        """将二维列表保存为csv文件。
        参数：
            filename：文件名，如后缀不为“.csv”则会自动添加
            data：要保存的二维列表
        返回值：
            返回一个字符串，值为全部文件名
        """
        if not filename.endswith('.csv'):
            filename = os.path.join(self.__path, f'{filename}.csv')
        else:
            filename = os.path.join(self.__path, filename)
        with open(filename, 'w', encoding = 'gbk', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter = ',', quoting = csv.QUOTE_ALL)
            writer.writerows(data)
        return os.path.split(filename)[1]

# convert file to base64 string
def convert_to_b64(filename: str) -> str:
    """ 将文件转为base64编码 """
    if os.path.exists(filename) and os.path.isfile(filename):
        with open(filename, 'rb') as f:
            b64str = base64.b64encode(f.read()).decode()
        return 'base64://' + b64str
    else:
        return ''