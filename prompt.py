# -*- coding: UTF-8 -*-
import importlib
from typing import TYPE_CHECKING, Dict

from util.file_util import FileHandler
from util.various_util import name_mapper

if TYPE_CHECKING:
    from core.context import Scenario
    from core.data import Data
    from langchain.prompts import PromptTemplate


class Prompt:
    def __init__(self, scenario: "Scenario") -> None:
        self.scenario = scenario

        camel_step_name = self.__class__.__name__.replace("Prompt", "")
        under_score_step_name = name_mapper(camel_case=camel_step_name)

        self.step_name = camel_step_name

        version = FileHandler.version_control_load()["prompt_shell"][under_score_step_name]

        self.prompt_shell: "PromptTemplate" = getattr(
            getattr(
                importlib.import_module(f"res.prompt_shell.{under_score_step_name}.{version}"),
                camel_step_name
            ),
            under_score_step_name
        )

        self.data_units: Dict[str, "Data"] = {}  # variable: VariableDataUnit

        self._set_preset_data_units()


    def get_llm_understand_prompt(self) -> str:
        def replace_placeholders(prompt_template: "PromptTemplate", values):
            return prompt_template.format(**values)

        mapper = {}
        for variable in self.prompt_shell.input_variables:
            mapper[variable] = self.data_units[variable].get_llm_understand_format(self.step_name)

        return replace_placeholders(self.prompt_shell, mapper)


    def _set_preset_data_units(self) -> None:
        for variable in self.prompt_shell.input_variables:
            if variable.startswith("scenario_"):
                inst: "DataUnit" = getattr(
                    importlib.import_module(f"data_unit.{variable}_data_unit"),
                    name_mapper(under_score_case=variable) + "DataUnit"
                )(self.scenario)
                self.data_units[variable] = inst
