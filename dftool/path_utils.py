from .time_utils import TimeUtils
from typing import Optional, Union, Dict, List, Any, Callable
from pathlib import Path
import os
import pandas as pd
import shutil

import logging
logger = logging.getLogger(__name__)


class PathUtils:
    @staticmethod
    def trans_abs_path(file_path:str):
        if file_path:
            pth = Path(file_path)
            if not pth.is_absolute():
                # 如果是相对路径，转换为绝对路径
                file_path = str(pth.resolve())
        return file_path
    
    @staticmethod
    def get_path_depth(path_str):
        # 实例化路径对象 + 标准化路径
        path_obj = Path(path_str).resolve()
        # parts 属性直接返回路径片段元组（自动过滤空值，无需额外处理）
        return len(path_obj.parts) - (1 if os.name == 'posix' else 0)
    
    @staticmethod
    def is_hidden(path: Union[str, Path]) -> bool:
        path = Path(path)
        
        # Linux / macOS：以 . 开头
        if os.name == 'posix':
            return path.name.startswith('.')

        # Windows：检查 FILE_ATTRIBUTE_HIDDEN
        elif os.name == 'nt':
            try:
                attrs = os.stat(path).st_file_attributes
                return bool(attrs & 0x2)
            except (AttributeError, FileNotFoundError):
                return False
        else:
            return False
    
    @staticmethod
    def setDir(dir_path, type=None):  
        '''
        函数作用：如果目录dir_path不存在，创建。
                 如果目录存在可以选择清空，也可以保留（不做任何操作）！
        
        参数：
            dir_path: 目录路径，默认目录不存在，创建之。
            type==1： 表示删除目录，重新创建。 
                  
        '''
        if not os.path.exists(dir_path):
            # 目录不存在，创建之
            os.makedirs(dir_path)
        else:
            if type == 1:
                confirm = input(f"你确定要清空这个文件夹{dir_path}, 然后重新创建吗？请输入Y/N确认: ").strip().lower()
                if confirm == 'y':
                    shutil.rmtree(dir_path)
                    os.makedirs(dir_path)
                    print("已清空并重新创建了该文件夹!")

    @staticmethod
    def get_dirinfo(target_dir='./', filter_file=1):
    
        # 转换为决定路径
        target_dir = PathUtils.trans_abs_path(target_dir)
        root_depth = PathUtils.get_path_depth(target_dir)
        
        # 存储遍历的文件信息
        file_info = []
        dir_info = []
        # 遍历 root 文件夹
        for parent_dir, children_dirs, children_files in os.walk(target_dir):
            # 当前父目录（parent_dir）的相对深度
            parent_relative_depth = PathUtils.get_path_depth(parent_dir)-root_depth
            
            # 遍历当前目录下的所有文件
            for file in children_files:
                file_path = os.path.join(parent_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = TimeUtils.get_path_time(file_path)
                file_info.append([parent_relative_depth+1, file_path, file_size, file_time, 'file', None, None])
            
            if filter_file==0:
                dir_info.append([parent_relative_depth,
                                parent_dir,
                                None,
                                TimeUtils.get_path_time(parent_dir),
                                "dir",
                                len(children_dirs), 
                                len(children_files)])

        # 整理遍历的结果
        columns = ["depth", "path", "size", "time", "type", "children_dirs_num", "children_files_num"]
        file_info_df = pd.DataFrame(file_info, columns=columns)
        if filter_file==1:
            return file_info_df[columns[:-2]]
        else:
            # 更新目录的大小
            size_index = columns.index('size')
            for j, item in enumerate(dir_info):
                # size 的索引: size_index
                item[size_index] = file_info_df[file_info_df['path'].str.contains(item[0])]['size'].sum()
                dir_info[j] = item
            dir_info_df = pd.DataFrame(dir_info, columns=columns)
            return pd.concat([file_info_df, dir_info_df], ignore_index=True)