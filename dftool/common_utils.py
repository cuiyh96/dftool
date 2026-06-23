from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Union, Dict

import sys
import json
import logging
import numpy as np
import jsonlines
import yaml
import uuid
import random

logger = logging.getLogger(__name__)


# ============================================================
# Strategy Interface
# ============================================================

class FileStrategy(ABC):
    """Abstract file read/write strategy."""

    @abstractmethod
    def read(self, path: Path, **kwargs) -> Any:
        ...

    @abstractmethod
    def write(self, path: Path, data: Any, **kwargs) -> None:
        ...


# ============================================================
# Concrete Strategies
# ============================================================

class JsonStrategy(FileStrategy):
    def read(self, path: Path, **kwargs) -> Any:
        encoding = kwargs.get("encoding", "utf-8")
        with path.open("r", encoding=encoding) as f:
            return json.load(f)

    def write(self, path: Path, data: Any, **kwargs) -> None:
        encoding = kwargs.get("encoding", "utf-8")
        with path.open("w", encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


class JsonlStrategy(FileStrategy):
    def read(self, path: Path, **kwargs) -> list[dict]:
        data = []
        with jsonlines.open(path, "r") as reader:
            for item in reader.iter(type=dict, skip_invalid=True):
                data.append(item)
        return data

    def write(self, path: Path, data: Any, **kwargs) -> None:
        with jsonlines.open(path, "w") as writer:
            if isinstance(data, dict):
                writer.write(data)
            elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
                for item in data:
                    if not isinstance(item, dict):
                        raise TypeError("Each jsonl item must be dict")
                    writer.write(item)
            else:
                raise TypeError("jsonl data must be dict or Iterable[dict]")


class YamlStrategy(FileStrategy):
    def read(self, path: Path, **kwargs) -> Any:
        encoding = kwargs.get("encoding", "utf-8")
        with path.open("r", encoding=encoding) as f:
            return yaml.safe_load(f)

    def write(self, path: Path, data: Any, **kwargs) -> None:
        encoding = kwargs.get("encoding", "utf-8")
        with path.open("w", encoding=encoding) as f:
            yaml.safe_dump(data, f, allow_unicode=True)


class NumpyStrategy(FileStrategy):
    def read(self, path: Path, **kwargs) -> Any:
        return np.load(path)

    def write(self, path: Path, data: Any, **kwargs) -> None:
        raise NotImplementedError("Writing .npy/.npz is not supported")


class TextStrategy(FileStrategy):
    def read(self, path: Path, **kwargs) -> Union[str, list[str]]:
        encoding = kwargs.get("encoding", "utf-8")
        lines = kwargs.get("lines", True)

        with path.open("r", encoding=encoding) as f:
            text = f.read()

        return text.splitlines() if lines else text.strip()

    def write(self, path: Path, data: Any, **kwargs) -> None:
        encoding = kwargs.get("encoding", "utf-8")

        with path.open("w", encoding=encoding) as f:
            if isinstance(data, str):
                f.write(data)
            elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
                for line in data:
                    f.write(f"{line}\n")
            else:
                raise TypeError("text data must be str or Iterable[str]")


# ============================================================
# Strategy Registry
# ============================================================

STRATEGY_MAP: Dict[str, FileStrategy] = {
    ".json": JsonStrategy(),
    ".jsonl": JsonlStrategy(),
    ".yaml": YamlStrategy(),
    ".yml": YamlStrategy(),
    ".npy": NumpyStrategy(),
    ".npz": NumpyStrategy(),
    ".txt": TextStrategy(),
    ".md": TextStrategy(),
    ".html": TextStrategy(),
}


# ============================================================
# Common Utils (Facade)
# ============================================================

class CommonUtils:
    @staticmethod
    def get_logger() -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        return logging.getLogger(__name__)

    @staticmethod
    def seq_truncate_or_pad(
        sequence: Iterable[Any],
        target_length: int,
        fill_value: Any = None,
    ) -> list[Any]:
        seq = list(sequence)
        result = seq[:target_length]

        padding = target_length - len(result)
        if padding > 0:
            result.extend([fill_value] * padding)

        return result

    @staticmethod
    def _get_strategy(path: Path) -> FileStrategy:
        suffix = path.suffix.lower()
        strategy = STRATEGY_MAP.get(suffix)
        if not strategy:
            raise ValueError(f"Unsupported file type: {suffix}")
        return strategy

    @staticmethod
    def read_file(
        file_path: Union[str, Path],
        **kwargs,
    ) -> Any:
        """
        file_path: 文件路径
        :return kwargs: 其他参数
        :return: 读取到的数据
        """
        
        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(f"{path} is not a valid file, please check the path.")

        strategy = CommonUtils._get_strategy(path)
        return strategy.read(path, **kwargs)

    @staticmethod
    def write_file(
        file_path: Union[str, Path],
        data: Any,
        **kwargs,
    ) -> None:
        path = Path(file_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        strategy = CommonUtils._get_strategy(path)
        strategy.write(path, data, **kwargs)

    @staticmethod
    def get_hashcode(text: str, digit_num=10, n_special_diginum=None, seed=42):
        """
        函数作用： 根据指定的 text文本生成固定的编码id。可用于生成指定位数的密码。
        :param text: 基于输入的文本生成编码id
        :param digit_num: 预设的 id 编码的字符数
        :param n_special_diginum: 其中特殊字符的个数，首位不能为特殊符号。
        :param seed: 随机种子，默认为42
        :return:
        """
        # type==1
        array_list = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                      "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s",
                      "t", "u", "v", "w", "x", "y", "z",
                      "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
                      "T",
                      "U", "V", "W", "X", "Y", "Z"
                      ]
        # type==2
        special_list = ["!", "@", "#", "$", "%", "^", "&", "*", "-", "+", "_", "|", "~", "?"]
        len_array_list = len(array_list)
        len_special_list = len(special_list)

        random.seed(seed)
        # 生成基础 code 编码
        id_ = uuid.uuid5(uuid.NAMESPACE_DNS, text).hex + uuid.uuid3(uuid.NAMESPACE_DNS, text).hex  # 32位+32位=共64位
        id_base = id_ + id_[:3]
        sample_index = random.sample(range(len(id_)), digit_num)
        sample_index_type = {i: 1 for i in sample_index}
        if n_special_diginum:
            special_sample_index = random.sample(sample_index[1:], n_special_diginum)
            for i in special_sample_index:
                sample_index_type[i] = 2

        buffer = []
        for i, type_ in sample_index_type.items():
            # 截取子串，得到一个“十六进制字符串”
            val = id_base[i: i + 4]
            # 将十六进制字符串转换为整数
            val_int = int(val, 16)
            # 根据type获取单个字符
            if type_ == 1:
                buffer.append(array_list[val_int % len_array_list])
            if type_ == 2:
                buffer.append(special_list[val_int % len_special_list])
        return ''.join(buffer)
    