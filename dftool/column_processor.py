from .common_utils import CommonUtils
from .json_utils import JsonUtils
from typing import Optional, List, Callable, Sequence, Union
import pandas as pd
import numpy as np

import json
import re

import logging
logger = logging.getLogger(__name__)


class ColumnProcessor:
    # ===================================================================== #
    #                                                                       #
    #                       一般函数（非列处理函数）                          #
    #                                                                       #
    # ===================================================================== #
    @staticmethod
    def check_columns_exist(df:pd.DataFrame, check_cols: Union[str, list[str]]):
        """检查多个列是否存在于DataFrame中"""
        if isinstance(check_cols, str):
            check_cols = [check_cols]
        
        missing_cols = [col for col in check_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"以下列不存在于 DataFrame 中: {missing_cols}\n"
            )
        return True
    
    # ===================================================================== #
    #                                                                       #
    #                         1. （转换）dataframe 列处理函数                 #
    #                                                                       #
    # ===================================================================== #
    @staticmethod
    def df_select_columns(
        select_cols: list,
        drop_duplicates: bool=False
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        功能：对 df 筛选列，实现 select cols / select distinct cols
        
        Args:
            select_cols: 要保留的列名列表，即sub_df[行数不变，列数变小]
            drop_duplicates: sub_df是否去重，默认不去重
            
        Returns:
            一个函数，该函数接受DataFrame并返回只包含指定列的新DataFrame
            
        Example:
            >>> keep_name_age = df_select_columns(['name', 'age'])
            >>> result_df = keep_name_age(original_df)
        """
        def _df_select_columns(df: pd.DataFrame)->pd.DataFrame:
            # 筛查列：输出的需要保留的列 select_cols
            if not select_cols:
                raise ValueError("select_cols 不能为空！")
            else:
                missing_cols = set(select_cols) - set(df.columns)
                if missing_cols:
                    logger.warning(f"指定需要输出的列：{select_cols}, 有些不在 dataframe 中: {missing_cols}")
                available_cols = [k for k in select_cols if k in df.columns]
                df_keep = df[available_cols]
                
            # 是否去重，默认不去重
            if not drop_duplicates:
                return df_keep
            else:
                # 将不可哈希的列转为 JSON 字符串
                temp_cols = {}
                for col in df_keep.columns:
                    if df_keep[col].apply(lambda x: isinstance(x, (dict, list))).any():
                        temp_cols[col] = df_keep[col].apply(lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False) if isinstance(x, (dict, list)) else x)

                if temp_cols:
                    df_temp = df_keep.copy()
                    for col, series in temp_cols.items():
                        df_temp[col] = series
                    df_temp = df_temp.drop_duplicates()
                    # 恢复原始类型
                    for col in temp_cols.keys():
                        df_temp[col] = df_temp[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
                    return df_temp
                else:
                    return df_keep.drop_duplicates()
        
        return _df_select_columns
    
    @staticmethod
    def df_rename_columns(
        rename_mapping: dict = None
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        # 处理None情况
        if rename_mapping is None:
            rename_mapping = {}
        
        def _rename_columns(df: pd.DataFrame):
            if not rename_mapping:
                logger.warning("重名字典rename_mapping为空，列重命名操作未执行！")
                return df
            
            df_keys = set(df.columns)
            rename_keys = set(rename_mapping.keys())
            
            # 计算交集
            inner_keys = rename_keys & df_keys
            
            # 1. 无任何匹配的键
            if not inner_keys:
                logger.warning(
                    "列重命名校验：重名字典rename_mapping的所有键均未匹配到DataFrame列名"
                )
            # 2. 部分键不匹配
            else:
                # 计算差集
                unmatched_keys = rename_keys - df_keys
                if unmatched_keys:
                    logger.warning(
                        f"列重命名校验：重名字典rename_mapping存在未匹配的列名 | "
                        f"未匹配键列表：{sorted(unmatched_keys)} | "
                        f"已匹配键列表：{sorted(inner_keys)}"
                    )
            
            return df.rename(columns=rename_mapping)
        
        return _rename_columns
    
    @staticmethod
    def df_fillna_column(
        select_cols: Union[str, List[str]],
        fill_values: Union[str, List[str], int, float, List[Union[str, int, float]]],
        output_cols: Union[str, List[str], None] = None,
        replace: bool = True
    ):
        """
        用指定值填充DataFrame中的缺失值
        
        Parameters:
        -----------
        select_cols : str or list of str
            要处理的列名或列名列表
        fill_values : scalar or list
            用于填充缺失值的值，如果为列表，长度需与select_cols相同
        output_cols : str or list of str, optional
            输出列名，仅在replace=False时使用。如果为None且replace=False，
            则自动生成输出列名
        replace : bool, default True
            是否替换原始列。如果为False，则创建新列
            
        Returns:
        --------
        Callable: 接受DataFrame并返回处理后的DataFrame的函数
        """
        # 归一化入参：统一为列表，避免对标量/字符串求长度或逐字符迭代
        if isinstance(select_cols, str):
            select_cols = [select_cols]
        if isinstance(fill_values, (list, tuple)):
            fill_values = list(fill_values)
        else:
            fill_values = [fill_values] * len(select_cols)
        if output_cols is not None and isinstance(output_cols, str):
            output_cols = [output_cols]

        # 验证select_cols和fill_values长度匹配
        if len(select_cols) != len(fill_values):
            raise ValueError(
                f"select_cols和fill_values长度必须相同。"
                f"select_cols长度: {len(select_cols)}, "
                f"fill_values长度: {len(fill_values)}"
            )
        
        # 处理output_cols参数
        if not replace:
            if output_cols is None:
                # 自动生成输出列名：在原列名后添加'_filled'
                output_cols = [f"{col}_filled" for col in select_cols]
            elif len(output_cols) != len(select_cols):
                # 验证用户传入的output_cols长度匹配
                raise ValueError(
                    f"当replace=False时，output_cols长度必须与select_cols相同。"
                    f"select_cols长度: {len(select_cols)}, "
                    f"output_cols长度: {len(output_cols)}"
                )        
        def _df_fillna_column(df: pd.DataFrame) -> pd.DataFrame:
            
            # check: select_col列是否在df中
            ColumnProcessor.check_columns_exist(df, select_cols)
            
            df_copy = df.copy()
            
            if replace:
                for col, value in zip(select_cols, fill_values):
                    df_copy[col] = df_copy[col].fillna(value)
            else:
                for col, value, output_col in zip(select_cols, fill_values, output_cols):
                    df_copy[output_col] = df_copy[col].fillna(value)
            
            return df_copy
        
        return _df_fillna_column
    # ===================================================================== #
    #                                                                       #
    #                 2. 自定义 dataframe 列处理函数                         #
    #                                                                       #
    # ===================================================================== #
    @staticmethod
    def explode_dict_column_to_kv_columns(
        select_col: str,
        output_cols: list = ['key', 'value']
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        综合函数：
            调用已定义的2个函数实现：将一个字典列，拆分为2列：key、value
        
        Args:
            select_col: 需要处理的字典列
            output_cols: 包含两个字符串的序列，分别代表新列的名称
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数
            
        Example:
            >>> split_col = ColumnProcessor.explode_dict_column_to_kv_columns(select_col='dict_data', output_cols=['dict_key', 'dict_value'])
            >>> result_df = split_col(input_df)
        """
        if len(output_cols)!=2:
            raise ValueError("output_cols 应为长度为2的列表，代表输出结果的列名！")
        
        def _explode_dict_column_to_kv_columns(df:pd.DataFrame):
            
            # step1: 拆分指定字典列的k-v对（含纵向展开操作）, 结果保存在列'_kv_pairs'= (k1, v1)、(k2, v2)、 (k3, v3), ...
            fn_step1 = ColumnProcessor.explode_dict_column_to_kv_tuples(select_col=select_col, output_col='_kv_pairs')
            df = fn_step1(df)
            
            # step2:  ki-vi 单独成列
            fn_step2 = ColumnProcessor.expand_nlen_sequence_column_to_n_columns(select_col='_kv_pairs', output_cols=output_cols)
            df = fn_step2(df)
            
            return df
        return _explode_dict_column_to_kv_columns
        
    @staticmethod
    def expand_dict_column_to_columns(
        select_col: str, 
        keep_keys: Optional[List] = None,
        drop_select_col: bool = True,
        conflict_suffix: str = "_2nd"
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        用于展开字典列的转换函数
        
        将包含字典的列展开为多个独立的列，自动处理列名冲突。
        
        Args:
            select_col: 需要展开的列名，该列应包含字典数据
            keep_keys: 可选，指定要保留的 select_col 中 keys 列表，如为None则保留所有键。
            drop_select_col: 是否在结果中删除原始的字典列，默认为True
            conflict_suffix: 冲突列名的后缀，默认为"_2nd"。注意只有有列名冲突的时候才起作用。
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数
            
        Example:
            >>> transformer = ColumnProcessor.expand_dict_column_to_columns(select_col='json_data', keep_keys=['name', 'age'])
            >>> result_df = transformer(input_df)
        """
        
        def _explode_dataframe(df: pd.DataFrame) -> pd.DataFrame:
            """
            展开指定列，将其字典内容转换为独立的列
            
            Args:
                df: 输入的DataFrame，df[select_col]的每一行应为字典
                
            Returns:
                处理后的DataFrame
                
            Raises:
                ValueError: 当指定列不存在或数据格式不符合预期时
            """
            df_copy = df.reset_index(drop=True)
            
            # 输入验证
            if select_col not in df.columns:
                raise ValueError(f"列 '{select_col}' 不存在于DataFrame中")
            
            if df_copy.empty:
                return df_copy.copy()
            
            # 验证数据格式
            sample_value = df_copy[select_col].iloc[0]
            if not isinstance(sample_value, dict):
                raise ValueError(f"列 '{select_col}' 应包含字典数据(Dict)，但实际类型为 {type(sample_value).__name__}")
            
            # 展开字典列
            df_filter = df_copy[df_copy[select_col].notna()]
            
            expanded_df = pd.DataFrame(df_filter[select_col].tolist(), index=df_filter.index)
            
            # 过滤需要保留的键
            if keep_keys:
                fn_select_cols = ColumnProcessor.df_select_columns(select_cols=keep_keys)
                expanded_df = fn_select_cols(expanded_df)
            
            # 处理列名冲突
            if drop_select_col:
                original_columns = set(df_copy.columns) - {select_col}
            else:
                original_columns = set(df_copy.columns)
            expanded_columns = set(expanded_df.columns)
            conflicting_columns = original_columns & expanded_columns
            
            if conflicting_columns:
                logger.warning(
                    f"列 '{select_col}' 展开后包含与原DataFrame冲突的列: {conflicting_columns}，"
                    f"这些列将添加后缀 '{conflict_suffix}'"
                )
                rename_mapping = {col: f"{col}{conflict_suffix}" for col in conflicting_columns}
                expanded_df = expanded_df.rename(columns=rename_mapping)
            
            # 合并数据框
            if drop_select_col:
                result_df = pd.concat([
                    df_copy.drop(columns=[select_col]), 
                    expanded_df
                ], axis=1)
            else:
                result_df = pd.concat([df_copy, expanded_df], axis=1)
            return result_df
        
        return _explode_dataframe

    @staticmethod
    def get_column_element_lengths(
        select_col: str,
        output_key: str = "_element_len"
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        创建计算列长度的转换函数
        
        Args:
            select_col: 需要计算长度的列名
            output_key: 输出结果列名，默认为"_element_len"
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数

        Example:
            >>> get_col_len = ColumnProcessor.get_column_element_lengths(select_col='col_1', output_key='_element_len')
            >>> result_df = get_col_len(input_df)    
        """
        
        def _get_column_element_lengths(df: pd.DataFrame) -> pd.DataFrame:
            """安全计算长度的函数"""
            def safe_length(x):
                if pd.isna(x):  # 检查是否为 NaN/None
                    return None
                elif isinstance(x, (str, list, dict, tuple, set)):
                    return len(x) if x else None  # 空字符串/列表/字典返回 None
                else:
                    # 对于其他类型，尝试转换为字符串计算长度
                    try:
                        return len(str(x)) if x is not None else None
                    except Exception:
                        return None
            
            df_copy = df.copy()
            df_copy[output_key] = df_copy[select_col].apply(safe_length)
            return df_copy
        
        return _get_column_element_lengths
    
    @staticmethod
    def explode_dict_column_to_kv_tuples(
        select_col: str,
        output_col: str='_kv_pairs'
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        创建将字典列转换为键值对形式的转换函数
        
        将DataFrame中字典类型的列转换为键值对形式, 并展开（纵向）
        
        Args:
            select_col: 要处理的字典列名，其值的单元素为：{k1：v1, k2:v2, k3:v3, ...}
            output_col: 拆分后的字段列名，其值的单元素为：(k1,v1)，下一个元素为(k2,v2), ...
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数

        Example:
            >>> fn1 = ColumnProcessor.explode_dict_column_to_kv_tuples(select_col='col_1', output_key='_kv_pairs')
            >>> result_df = fn1(input_df)       
        """
        
        def _explode_dict_column_to_kv_tuples(df: pd.DataFrame) -> pd.DataFrame:
            
            # check: select_col列是否在df中
            ColumnProcessor.check_columns_exist(df, select_col)
            
            # df 行数不变：列 kv_pairs 是list[(k1,v1), (k2,v2), (k3,v3), ......]
            df = df.assign(
                **{
                f"{output_col}":df[select_col].apply(lambda x: list(x.items()) if isinstance(x, dict) else [])
            }
            )
            
            # 展开（纵向）
            df_new = df.explode(output_col)
            return df_new
        
        return _explode_dict_column_to_kv_tuples

    @staticmethod
    def expand_nlen_sequence_column_to_n_columns(
            select_col: str, 
            output_cols: Sequence[str]
            ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        将（长度为 n 的序列）列（横向）展开成 n 列
        
        Args:
            select_col: 需要处理的列，每个元素都是长度为固定长度 n 的序列
            output_cols: 长度为n的列表，代表展开后的n列列名。
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数

        Example:
            >>> fn = ColumnProcessor.expand_nlen_sequence_column_to_n_columns(select_col='len2_seq_col', output_key=['key', 'value'])
            >>> result_df = fn(input_df)      
        """
        
        def _expand_nlen_sequence_column_to_n_columns(df: pd.DataFrame) -> pd.DataFrame:
            
            n = len(output_cols) # 计算需要输出几列
            """check: seq长度是否存在大于n的情况，会被截断"""
            get_column_element_lengths_func = ColumnProcessor.get_column_element_lengths(select_col=select_col, output_key="_element_len")
            df = get_column_element_lengths_func(df)
            check_ = df["_element_len"] > n
            if sum(check_) > 0:
                logger.warning(f"dataframe 中给定列{select_col}, 存在长度大于{n}的元素，可能有字段信息损失，请核查！")
            
            # 遍历给定列的元素，通过 CommonUtils.seq_truncate_or_pad() 使其长度一致
            nested_list = []
            for seq in df[select_col]:
                seq_new = CommonUtils.seq_truncate_or_pad(seq,n)
                nested_list.append(seq_new)
            
            # 删除 select_col 和 _element_len
            df_copy = df.drop(columns=[select_col, "_element_len"])
            
            # （expand）增加新列
            nested_array = np.array(nested_list)
            for i, col_name in enumerate(output_cols):
                df_copy[col_name] = nested_array[:, i]
            return df_copy
        
        return _expand_nlen_sequence_column_to_n_columns

    @staticmethod
    def assign_column(
        **assignments: Union[str, Callable]
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        创建列赋值转换函数
        
        Args:
            **assignments: 列名和赋值表达式的映射
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数
        """
        def _assign_column(df: pd.DataFrame) -> pd.DataFrame:
            return df.assign(**assignments)
        return _assign_column

    @staticmethod
    def map_column(
        column: str,
        mapping_func: Callable,
        output_column: Optional[str] = None
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        创建列映射转换函数
        
        Args:
            column: 要映射的列名
            mapping_func: 映射函数
            output_column: 输出列名，如为None则覆盖原列
            
        Returns:
            接收DataFrame并返回处理后的DataFrame的函数
        """
        def _map_column(df: pd.DataFrame) -> pd.DataFrame:
            target_column = output_column if output_column else column
            df = df.copy()
            df[target_column] = df[column].map(mapping_func)
            return df
        return _map_column

    @staticmethod
    def extract_json_from_column(select_col: str, output_json_col: str="extract_json") -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        创建 JSON 提取器函数
        
        Args:
            select_col: 需要处理的文本列名
            output_json_col: 抽取的 JSON 结果，保存的列名
            
        Returns:
            接收 DataFrame 并返回处理后的 DataFrame 的函数
        """
        def _json_extractor(df: pd.DataFrame) -> pd.DataFrame:
            # check: select_col列是否在df中
            ColumnProcessor.check_columns_exist(df, select_col)

            df_copy = df.copy()
            df_copy[output_json_col] = df_copy[select_col].apply(
                lambda x: JsonUtils.extract_json_from_text(x) if pd.notna(x) else None
            )

            return df_copy
        
        return _json_extractor
    
    @staticmethod
    def str_column_to_json_column(
        select_col: str, 
        output_col: Optional[str] = None
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        使用 JsonUtils.safe_json_loads 解析 JSON，兼容更多非标准格式
        
        Args:
            select_col: 要转换的列名
            output_col: 输出列名，如果为 None 则使用 f"{select_col}_json"
        """
        
        def _json_convert(df: pd.DataFrame) -> pd.DataFrame:
            
            # check: select_col列是否在df中
            ColumnProcessor.check_columns_exist(df, select_col)
            
            
            df_copy = df.copy()
            result_json = []
            for text in df_copy[select_col]:
                result_json.append(JsonUtils.safe_json_loads(text))

            final_json_col = output_col if output_col is not None else f"{select_col}_json"
            df_copy[final_json_col] = result_json
            
            return df_copy
        
        return _json_convert
    
    @staticmethod
    def extract_pattern_from_column(
        select_col: str, 
        output_col: Union[str, list[str]],
        pattern: str,
        extract_all: bool = False 
    ) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        从文本中提取用户指定模式的内容
        
        Args:
            select_col: 被选择的操作列
            output_col: 输出提取结果的列名
            pattern: 抽取模式的正则表示式
            extract_all: 是否提取全部匹配。
                - 默认值为 False, 即只提取第一个匹配，返回值为 str;
                - True, 即提取所有匹配，返回值为 list[str].
        Returns:
            处理DataFrame的函数
        """
        # eg: pattern = r"\*\*用户请求\*\*：(.*)"
        PATTERN =  re.compile(pattern, re.DOTALL)
        def _extract_df(df: pd.DataFrame) -> pd.DataFrame:
            """处理整个DataFrame"""
            # check: select_col列是否在df中
            ColumnProcessor.check_columns_exist(df, select_col)
                
            # 使用向量化操作替代apply以提高性能
            df_copy = df.copy()
            if extract_all:
                # 提取所有匹配，返回结果 list[str]
                df_copy[output_col] = df_copy[select_col].str.findall(PATTERN)
            else:
                # 提取第一个匹配, 返回结果 str
                df_copy[output_col] = df_copy[select_col].str.extract(PATTERN)
            return df_copy
        
        return _extract_df

    @staticmethod
    def check_missing_elements_between_columns(check_col: str, 
                                                target_col: str,
                                                output_col: str = None
                                                ):
        """
        检查check_col列中的每个元素（列表）是否都出现在target_col列中
        
        Args:
            check_col: 包含列表的列名，每个元素是待检查的字符串列表
            target_col: 要搜索的目标文本列名
            output_col: 输出结果的列名，如果为None则自动生成
        
        Returns:
            一个函数，该函数接受DataFrame并返回处理后的DataFrame
            返回True表示有缺失元素，False表示所有元素都出现在target_col中
        """
        def check_missing_elements(check_list, text):
            """辅助函数：检查列表中是否有元素不在文本中"""
            if not isinstance(check_list, list) or not text:
                return None
            # 检查 check_list 中的每个元素是否出现在text中
            for element in check_list:
                if str(element) not in str(text):
                    return True
            return False
        
        def _has_missing(df: pd.DataFrame) -> pd.DataFrame:
            # 检查列是否存在
            ColumnProcessor.check_columns_exist(df, [check_col, target_col])
            
            # 设置输出列名
            if output_col is None:
                result_col = f"{check_col}_missing_in_{target_col}"
            else:
                result_col = output_col
            
            df_copy = df.copy()
            # 应用检查函数
            df_copy.loc[:, result_col] = df_copy.apply(
                lambda row: check_missing_elements(row[check_col], row[target_col]), 
                axis=1
            )
            
            return df_copy
        
        return _has_missing
    
    @staticmethod
    def df_explode_column(
            col_name: str,
        ) -> Callable[[pd.DataFrame], pd.DataFrame]:
            """
            高阶函数：生成对指定列进行 explode（炸裂）的函数
            风格与 df_rename_columns 完全一致
            """
            def _explode_column(df: pd.DataFrame):
                # 检查列是否存在
                if col_name not in df.columns:
                    logger.warning(f"列名 {col_name} 不存在于 DataFrame 中，炸裂操作未执行！")
                    return df
                
                # 执行炸裂
                df_exploded = df.explode(col_name, ignore_index=True)
                logger.info(f"成功对列 {col_name} 执行炸裂操作！")
                return df_exploded
            return _explode_column