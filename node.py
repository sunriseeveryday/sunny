# -*- coding: UTF-8 -*-
from functools import wraps
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict

from api.niogpt_api import LLM
from prompt import CheckIntentPrompt
from core.context import StateCode, IntentType
from interrupt import UnsupportedIntentInterrupt
from res.template.msg_template import MsgTemplate
from core.data_unit import StrDataUnit, EnumDataUnit
from core.record import insert_record, update_record
from core.state import load_states, set_pass, store_states, restore_states

if TYPE_CHECKING:
    from core.context import Context
    from core.data_unit import DataUnit
    from core.interrupt_with_saving_states import InterruptWithSavingStates


def add_unsupported_intent_interrupt_handler(func):
    @wraps(func)
    def wrapper(self: "BaseStep", *args, **kwargs):
        if args:
            interrupt: InterruptWithSavingStates = args[0]
        elif "interrupt" in kwargs:
            interrupt: InterruptWithSavingStates = kwargs["interrupt"]

        if isinstance(interrupt, UnsupportedIntentInterrupt):
            return MsgTemplate.unsupported_intent_msg.format(
                interrupt_msg = interrupt.interrupt_msg,
                user_intent=self.user_intent[1].get()
            )
        else:
            return func(self, *args, **kwargs)
    return wrapper


class Node:
    def __init__(self, context: "Context", need_internal_model: bool=False) -> None:
        self.context = context
        self.need_internal_model = need_internal_model
        self.prompt = ""
        self.answer = ""
        self.record_id = -1
        self.states_mapper: Dict[str, "DataUnit"] = {}
        self.chaos = {}

        # 状态相关参数
        self.state_code = StateCode.NoData
        self.states = {}
        self.user_intent = []  # [intent_type, context.user_intent: DataUnit]


    def _restore_states(self) -> None:
        for variable_name, variable_value in self.states_mapper.items():
            variable_value.init(self.states["states"][variable_name])
            setattr(self, variable_name, variable_value)


    def _store_states(self) -> None:
        for variable_name in self.states_mapper:
            data_unit: "DataUnit" = getattr(self, variable_name)
            self.states["states"][variable_name] = data_unit.state
            self.chaos[variable_name] = data_unit.state


    @restore_states
    @load_states
    def check_exist(self) -> None:
        if self.states:
            if self.states["state_code"] == StateCode.HasError:
                self.state_code = StateCode.HasError
            elif self.states["state_code"] == StateCode.NoError:
                self.state_code = StateCode.NoError
        else:
            self.state_code = StateCode.NoData


    @insert_record
    def prechat(self) -> None:
        self._prechat()


    def _chat(self) -> None:
        if self.prompt:
            self.answer = LLM().run(self.prompt, need_internal_model=self.need_internal_model)
            for variable_name, variable_value in self.states_mapper.items():
                variable_value.init(self.answer)
                setattr(self, variable_name, variable_value)


    @store_states
    def chat(self) -> None:
        self._chat()


    @set_pass
    @update_record
    def postchat(self) -> Any:
        return self._postchat()


    def check_intent(self) -> None:
        fast_intent_check = ("确认", "确定", "继续", "好的")

        user_intent = StrDataUnit(raw=self.context.user_intent)
        intent_to_user = StrDataUnit(raw=self.states["intent_to_user"])

        if self.context.user_intent in fast_intent_check:
            intent_type = "comfirm"
        else:
            prompt = CheckIntentPrompt(self.context.scenario, user_intent, intent_to_user).get_llm_understand_prompt()
            intent_type = LLM().run(prompt)

        self.user_intent = [
            EnumDataUnit(raw=intent_type, enum_class=IntentType, default=IntentType.Other).get_enum(),
            user_intent
        ]
        if self.user_intent[0] == IntentType.Other:
            raise UnsupportedIntentInterrupt(MsgTemplate.unsupported_intent, self)


    @store_states
    def modify_states(self) -> None:
        self._modify_states()


    @add_unsupported_intent_interrupt_handler
    def generate_intent_to_user(self, interrupt: "InterruptWithSavingStates") -> str:
        return self._generate_intent_to_user(interrupt)


    def run(self) -> Any:
        print(f"Calling Step: {self.__class__.__name__}")

        self.check_exist()
        if self.state_code == StateCode.HasError:
            self.check_intent()
            if self.user_intent[0] != IntentType.Comfirm:
                self.modify_states()

        elif self.state_code == StateCode.NoData:
            self.prechat()
            self.chat()
        return self.postchat()


    def _prechat(self) -> None:
        pass


    def _modify_states(self) -> None:
        pass


    def _generate_intent_to_user(self, interrupt: "InterruptWithSavingStates") -> str:
        return interrupt.interrupt_msg


    # =========================ABSTRACTMETHOD=========================

    @abstractmethod
    def _postchat(self) -> Any:
        ...
