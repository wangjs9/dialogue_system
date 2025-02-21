import json
import torch
import random
from transformers import AutoTokenizer
from llamafactory.hparams import DataArguments
from llamafactory.data import get_template_and_fix_tokenizer, Role
from typing import Dict, List
from vllm import LLM
from vllm import SamplingParams
from vllm.lora.request import LoRARequest
from utils.template_utils import get_template
import re

model_info = json.load(open("user_interface/model.json", "r"))

model_name_or_path = model_info["MODEL_PATH"]
sft_lora_path = model_info["SFT_LORA_PATH"]
dpo_lora_path = model_info["DPO_LORA_PATH"]

model = LLM(
    model=model_name_or_path,
    enable_lora=True,
    tensor_parallel_size=torch.cuda.device_count(),
    swap_space=1
)
tokenizer = AutoTokenizer.from_pretrained(
    model_name_or_path,
    use_fast=True,
    split_special_tokens=False,
    padding_side="right",
    trust_remote_code=True
)
data_args = DataArguments()
data_args.template = 'qwen2.5'
template = get_template_and_fix_tokenizer(tokenizer, data_args)
input_template = get_template("empathetic_llm")


@torch.inference_mode()
def infer_model(message_ids, lora_path: str = None):
    while True:
        generation_kwargs = {
            "max_tokens": 512,
            "top_k": 50,
            "top_p": 0.9,
            "temperature": 0.9
        }
        if lora_path:
            outputs = model.generate(
                prompt_token_ids=message_ids,
                sampling_params=SamplingParams(seed=random.randint(0, 4096), **generation_kwargs),
                lora_request=LoRARequest('default', 2, lora_path=lora_path)
            )
            generated = outputs[0].outputs[0].text
            if "【倾听者回复】：" in generated:
                generated = generated.split("【倾听者回复】：")[-1]
                return generated.replace("\n", "")
        else:
            outputs = model.generate(
                prompt_token_ids=message_ids,
                sampling_params=SamplingParams(seed=random.randint(0, 4096), **generation_kwargs)
            )
            generated = outputs[0].outputs[0].text
            return generated.replace("\n", "")


def translate(text, to_english=True):
    if to_english:
        message = [{'content': f'把以下的文字翻译成英文：\n\n{text}\n\n只输出英文即可。\n', 'role': 'user'},
                   {'content': '', 'role': 'assistant'}]
        message_id = [template.encode_oneturn(tokenizer=tokenizer, messages=message)[0]]
        output = infer_model(message_id)
        return output
    else:
        message = [{'content': f'把以下的文字翻译成中文：\n\n{text}\n\n只输出中文即可。\n', 'role': 'user'},
                   {'content': '', 'role': 'assistant'}]
        message_id = [template.encode_oneturn(tokenizer=tokenizer, messages=message)[0]]
        output = infer_model(message_id)
        return output


def get_model_response(conversations: List[Dict[str, str]]):
    is_english = not re.search(r'[\u4e00-\u9fff]', conversations[-1]['content'])
    if is_english:
        translated_content = translate(conversations[-1]['content'], to_english=False)
        conversations[-1]['translated_content'] = translated_content
        conversations = [
            {"content": turn["translated_content"] if idx % 2 == 0 else turn["content"], "role": turn["role"]}
            for idx, turn in enumerate(conversations)
        ]

    input_message = input_template.format_example({"conversation": conversations})
    message_ids = [template.encode_oneturn(tokenizer=tokenizer, messages=input_message)[0]]
    sft_output = infer_model(message_ids, sft_lora_path)
    dpo_output = infer_model(message_ids, dpo_lora_path)
    if is_english:
        sft = translate(sft_output, to_english=True)
        dpo = translate(dpo_output, to_english=True)
        return {
            "sft": sft, "dpo": dpo, "is_english": is_english,
            "chinese_sft": sft_output, "chinese_dpo": dpo_output,
            "translated_content": translated_content
        }
    else:
        return {"sft": sft_output, "dpo": dpo_output, "is_english": is_english}
