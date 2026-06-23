from typing import Optional, Union, Dict, List, Any, Callable
from pathlib import Path
import time
from datetime import datetime
import os
import pandas as pd
# from dataflow.logger import get_logger
# logger = get_logger()
import logging
logger = logging.getLogger(__name__)

class TimeUtils:
    @staticmethod
    def get_current_time():
        now = datetime.now()
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def get_path_time(obj_path):
        """  
        参数：
            obj_path: 目录/文件目录。  
        函数作用：
            获取文件的修改时间'%Y-%m-%d %H:%M:%S'
        """
        try:
            modified_time = os.path.getmtime(obj_path) # 时间戳
            modified_time = datetime.fromtimestamp(modified_time) # 时间戳转日期
            # modified_time.strftime('%Y-%m-%d')
            modified_time = modified_time.strftime('%Y-%m-%d %H:%M:%S') # 日期转字符串格式
            return modified_time
        except Exception as e:
            print(e.args[0])
            return None
    
    @staticmethod
    def trans_timeStr2timeStamp(timeStr):
        """
        字符类型日期转时间戳
        eg：trans_timeStr2timeStamp("2015-09-01 00:00:00") = 1441036800
        """
        # step1: 字符类型转为时间类型
        time_fmt = datetime.fromisoformat(timeStr)
        # step2：转为时间数组
        timeArray = time_fmt.timetuple()
        # step3：转为时间戳
        timeStamp = int(time.mktime(timeArray))
        return timeStamp