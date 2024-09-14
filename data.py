import sys
sys.path.append("./")
import json
from enum import Enum
from abc import ABC, abstractmethod
from typing import Type, Union, Optional

from util.various_util import (
    leaf_to_dict,
    get_json_data,
    remove_md_label,
    check_and_format,
    get_enum_name_by_value
)


class Data(ABC):
    _raw: Optional[str] = None


    def __init__(self, raw: Optional[str]=None) -> None:
        if raw is not None:
            self.init(raw)


    def init(self, raw: str):
        self._raw = raw
        self._get_parsed_format()


    @property
    def state(self):
        ...


    @abstractmethod
    def _get_parsed_format(self):
        ...


    @abstractmethod
    def get_llm_understand_format(self, step_name: str=None) -> str:
        ...


class StrData(Data):
    def __init__(self, raw: Optional[str]=None, label=None) -> None:
        self.label = label
        super().__init__(raw)


    @property
    def state(self):
        return self._raw


    def _get_parsed_format(self):
        self._raw = remove_md_label(self._raw, self.label)


    def get_llm_understand_format(self, step_name: str=None) -> str:
        return self._raw


    def get(self):
        return self._raw


    def set(self, new_str: str):
        self._raw = new_str


class DictData(Data, dict):
    def __init__(self, empty_value, raw: Optional[Union[str, dict]]=None, empty_delete=True, label=None):
        self.empty_value = empty_value
        self.empty_delete = empty_delete
        self.label = label
        super().__init__(raw)


    @property
    def state(self):
        return self


    def _get_parsed_format(self):
        if isinstance(self._raw, str):
            dict_obj = json.loads(remove_md_label(self._raw, self.label))
        else:
            dict_obj = self._raw
        assert isinstance(dict_obj, dict), "text must be dict"
        dict_obj = check_and_format(dict_obj, self.empty_delete, self.empty_value)
        self.clear()
        self.update(dict_obj)


    def get_llm_understand_format(self, step_name: str=None) -> str:
        return get_json_data(self)


    def leaf_to_dict(self):
        temp = leaf_to_dict(self)
        self.clear()
        self.update(temp)


class ListData(Data, list):
    def __init__(self, raw: Optional[Union[str, list]]=None, label=None):
        self.label = label
        super().__init__(raw)


    @property
    def state(self):
        return self


    def _get_parsed_format(self):
        if isinstance(self._raw, str):
            list_obj = json.loads(remove_md_label(self._raw, self.label))
        else:
            list_obj = self._raw
        assert isinstance(list_obj, list), "raw must be list"
        self.clear()
        self.extend(list_obj)


    def get_llm_understand_format(self, step_name: str=None) -> str:
        return "\n".join(self)


    def remove_str_duplicates(self):
        seen = set()
        unique_items = []

        for item in self:
            if item not in seen:
                unique_items.append(item)
                seen.add(item)

        self.clear()
        self.extend(unique_items)


    def remove_list_duplicates(self):
        unique_items = []

        for item in self:
            is_match = False
            for unique_item in unique_items:
                is_inner_match = True
                for a, b in zip(item, unique_item):
                    if a != b:
                        is_inner_match = False
                if is_inner_match:
                    is_match = True

            if not is_match:
                unique_items.append(item)

        self.clear()
        self.extend(unique_items)


    def leaf_to_dict(self, empty_value):
        temp = leaf_to_dict(self)
        return DictDataUnit(empty_value=empty_value, empty_delete=False, raw=temp)


class EnumData(Data):
    def __init__(self, enum_class: Type[Enum], raw: Optional[str]=None, default: Enum=None, label=None):
        self.enum_class = enum_class
        self.default = default
        self.label = label
        super().__init__(raw)


    @property
    def state(self):
        return self.get_value()


    def _get_parsed_format(self):
        enum_obj = remove_md_label(self._raw, self.label)
        self._enum = get_enum_name_by_value(self.enum_class, enum_obj, self.default)


    def get_enum(self):
        return self._enum


    def get_value(self):
        return self._enum.value


if __name__ == "__main__":
    pass
