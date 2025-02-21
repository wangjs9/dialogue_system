# This file is based on the LlamaFactory `eval/template.py` file.
# It includes the templates / prompts for model training or generation.

from dataclasses import dataclass
from typing import Dict, List, Sequence, Any, Union
from llamafactory.data import Role
from utils.config_utils import ROLE_MAP


@dataclass
class InferTemplate:
    system: str
    context: str
    response: str

    def _parse_example(self, example: List[Dict[str, str]]) -> str:
        r"""
        input: a dict with keys {"conversation"}
        output: a prompt
        """
        conversation = self.context.format(
            conversation='\n'.join(
                [f"{ROLE_MAP[turn['role']]}: {turn['content']}" for turn in example])
        )
        return conversation + self.response

    def format_example(self, target_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Converts dataset examples to messages.
        """
        messages = []
        prompt = self._parse_example(target_data)
        messages.append({'role': Role.USER.value, 'content': prompt})
        messages.append({'role': Role.ASSISTANT.value, 'content': ''})
        messages[0]['content'] = self.system + messages[0]['content']
        return messages


@dataclass
class UserTemplate:
    system: str
    context: str
    response: str

    def _parse_conversation(self, example: List[Dict[str, str]]) -> str:
        r"""
        input: a dict with keys {"conversation"}
        output: a prompt
        """
        if len(example) == 0:
            return ''
        conversation = '\n\t'.join(
            [f"{ROLE_MAP[turn['role']]}: {turn['content']}" for turn in example])

        return conversation

    def format_example(self, target_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Converts dataset examples to messages.
        """
        messages = []
        description = target_data.get('description', '')
        conversation = self._parse_conversation(target_data.get('conversation', []))
        if conversation:
            messages.append({
                'role': Role.USER.value,
                'content': self.system + self.context.format(description=description, conversation=conversation)
            })
        else:
            messages.append({
                'role': Role.USER.value,
                'content': self.system + f'【来访者自我描述】：{description}\n\n请输出来访者的开场对话。\n'
            })
        messages.append({'role': Role.ASSISTANT.value, 'content': ''})
        return messages


@dataclass
class EmpatheticLLM:
    system: str
    context: str
    response: str

    def _parse_conversation(self, example: List[Dict[str, str]]) -> str:
        r"""
        input: a dict with keys {"conversation"}
        output: a prompt
        """
        conversation = '\n\t'.join(
            [f"{ROLE_MAP[turn['role']]}: {turn['content']}" for turn in example])

        return conversation

    def format_example(self, target_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Converts dataset examples to messages.
        """
        messages = []
        conversation = self._parse_conversation(target_data.get('conversation'))
        messages.append(
            {'role': Role.USER.value, 'content': self.system + self.context.format(conversation=conversation)})
        messages.append({'role': Role.ASSISTANT.value, 'content': ''})
        return messages


@dataclass
class COTTemplate:
    system: str
    context: str
    response: str

    def _parse_example(self, example: Dict[str, Union[List[dict], str]], contrast: bool = False) -> str:
        r"""
        input: a dict with keys {"conversation"}
        output: a prompt
        """
        context = '\n'.join([f"{ROLE_MAP[turn['role']]}: {turn['content']}" for turn in example['conversation']])
        if contrast:
            conversation = self.context.format(
                conversation=context, response=example['response'], contrast=example['contrast']
            )
            response = self.response.format(response=example['response'], contrast=example['contrast'])
        else:
            conversation = self.context.format(
                conversation=context, response=example['response'], user_state=example['user_state'])
            conversation = conversation.replace(f'我对来访者有如下判断：\n{None}\n', '')
            response = self.response.format(response=example['response'])

        return conversation + response

    def format_example(
            self,
            target_data: Dict[str, str],
            support_set: Sequence[Dict[str, str]] = None,
            contrast: bool = False,
            use_gpt: bool = False
    ) -> List[Dict[str, str]]:
        r"""
        Converts dataset examples to messages.
        """
        messages = []
        if support_set:
            for k in range(len(support_set)):
                prompt = self._parse_example(support_set[k])
                messages.append({'role': Role.USER.value, 'content': prompt})

        prompt = self._parse_example(target_data, contrast)
        messages.append({'role': Role.USER.value, 'content': prompt})
        messages.append({'role': Role.ASSISTANT.value, 'content': ''})
        if not use_gpt:
            messages[0]['content'] = self.system + messages[0]['content']
        return messages


templates: Dict[str, Union["COTTemplate", "InferTemplate", "UserTemplate", "EmpatheticLLM"]] = {}


def _register_template(name: str, system: str, context: str, condition: str = None, response: str = None) -> None:
    if '_cot' in name:
        templates[name] = COTTemplate(system=system, context=context, response=response)
    elif '_infer' in name:
        templates[name] = InferTemplate(system=system, context=context, response=response)
    elif 'user_' in name:
        templates[name] = UserTemplate(system=system, context=context, response=response)
    elif '_llm' in name:
        templates[name] = EmpatheticLLM(system=system, context=context, response=response)


def get_template(name: str) -> Union["COTTemplate", "InferTemplate", "UserTemplate", "EmpatheticLLM"]:
    template = templates.get(name, None)
    # assert template is not None, f'Eval template {name} not found.'
    return template


_register_template(
    name='qwen_infer',
    system='扮演一个精通非暴力沟通的倾听者，通过同理回复帮助来访者舒缓他们的情绪问题。\n\n',
    context='来访者和倾听者的对话历史如下：\n{conversation}\n\n',
    response='根据当前的对话历史和来访者的状态，倾听者应该回复：'
)

_register_template(
    name='generate_cot',
    system='任务：\n扮演一位与来访者对话的倾听者，描述倾听者在与来访者指定回复的思考过程，最终补充完整的思维链（……部分）。\n思维链内容包括：\n1. 倾听者对来访者状态的关注点（观察、情绪、需求或者请求），这个关注点直接影响倾听者的后续回复；\n2. 倾听者回复的策略（例如：建议、教育、安慰、回忆、否定、同情、询问等）和意图。\n\n要求：\n1. 视角：以倾听者的视角与口吻展开分析；\n2. 描述：详细说明倾听者回复背后的思维链；\n3. 思维过程：\n - 基于与来访者的对话历史作出推导；\n - 在推导过程中，倾听者不应预知或者提及后续回复的具体内容；\n - 通过思维链能够自然推导得出后续回复。\n\n',
    context='【历史对话】：\n{conversation}\n\t-----------------------------\n根据以上对话，【倾听者思维链】为：\n我对来访者有如下判断：\n{user_state}\n在接下来的回复中，我将重点关注于......\n相对应，我将采取......\n\t-----------------------------\n因此【倾听者回复】为：\n{response}\n\n',
    response='问题：补充【倾听者思维链】（......部分），使得【倾听者回复】为{response}？\n\n回答：完整的【倾听者思维链】为'
)

_register_template(
    name='user_simulator',
    system='【任务】：根据历史对话和来访者自我描述，推理对话过程中来访者的观测事实、感受、需求和请求（状态信息）。并请扮演来访者和倾听者进行对话，在对话过程中倾诉自己的烦恼。\n',
    context='【来访者自我描述】：{description}\n\n【历史对话】：\n\t{conversation}\n\n请输出来访者接下来来访者的状态信息（如有）和回复。\n'
)

_register_template(
    name='empathetic_llm',
    system='【任务】：请根据倾听者和来访者的历史对话，生成倾听者的思维链和相应的倾听者回复。\n\n',
    context='【历史对话】：\n\t{conversation}\n\n请判断倾听者思维链，并做出对来访者的回复。\n',
)
