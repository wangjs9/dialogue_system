import random
import yaml
from pathlib import Path
from fire import Fire
from typing import Optional, Dict, Any, List
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from llamafactory.hparams import get_eval_args
from llamafactory.model import load_model, load_tokenizer
from llamafactory.data import get_template_and_fix_tokenizer
from utils.message_utils import Message
from utils.config_utils import *
from utils.template_utils import get_template

logging.getLogger().setLevel(logging.INFO)


class UserSimulator:
    def __init__(self, args: Optional[Dict[str, Any]] = None) -> None:
        self.model_args, self.data_args, self.eval_args, fine_tuning_args = get_eval_args(args)
        self.tokenizer = load_tokenizer(self.model_args)["tokenizer"]
        self.tokenizer.padding_side = "right"
        self.template = get_template_and_fix_tokenizer(self.tokenizer, self.data_args)
        self.model = load_model(self.tokenizer, self.model_args, fine_tuning_args)
        self.user_template = get_template('user_simulator')
        self.description_list = self.__init_desc__()

    def __init_desc__(self):
        dataset_path = os.path.join(self.data_args.dataset_dir, f"{self.data_args.dataset_name}.json")
        raw_data = json.load(open(dataset_path, 'r', encoding='utf-8'))
        description_list = [line['description'] for line in raw_data]
        return description_list

    @torch.inference_mode()
    def __respond__(self, input_message: List[Dict[str, str]]) -> str:
        input_ids = self.template.encode_oneturn(tokenizer=self.tokenizer, messages=input_message)[0]
        input_ids = torch.tensor(input_ids).unsqueeze(0).to(self.model.device)
        output_ids = self.model.generate(
            input_ids=input_ids,
            attention_mask=torch.ones_like(input_ids),
            max_new_tokens=256,  # Maximum length of the generated text
            num_return_sequences=1,  # Number of sequences per input
            temperature=1.0,  # Sampling temperature
            top_k=50,  # Top-k sampling
            top_p=0.95,  # Top-p (nucleus sampling)
            do_sample=True,  # Enable sampling
        )[0]
        input_length = (input_ids != self.tokenizer.pad_token_id).sum(dim=1)  # Shape: [batch_size]
        new_tokens = output_ids[input_length:].tolist()

        # Decode the newly generated tokens
        generated_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        print(generated_text.split('【来访者对话】：')[0])
        generated_text = generated_text.split('【来访者对话】：')[-1]
        return generated_text

    def interact(self) -> None:
        user_description = random.choice(self.description_list)
        conversation = []

        while True:
            input_dict = {'description': user_description, 'conversation': conversation}
            input_text = self.user_template.format_example(input_dict)
            user_response = self.__respond__(input_text)
            print(user_response)
            therapist = input('倾听者：')
            conversation.append({'role': 'user', 'content': user_response})
            conversation.append({'role': 'assistant', 'content': therapist})

    def __save__(self, message: Message) -> None:
        pass


class EmpatheticLLM:
    def __init__(self, args: Optional[Dict[str, Any]] = None) -> None:
        self.model_args, self.data_args, self.eval_args, fine_tuning_args = get_eval_args(args)
        self.tokenizer = load_tokenizer(self.model_args)["tokenizer"]
        self.tokenizer.padding_side = "right"
        self.template = get_template_and_fix_tokenizer(self.tokenizer, self.data_args)
        self.model = load_model(self.tokenizer, self.model_args, fine_tuning_args)
        self.llm_template = get_template('empathetic_llm')

    @torch.inference_mode()
    def __respond__(self, input_message: List[Dict[str, str]]) -> str:
        input_message = self.llm_template.format_example({'conversation': input_message})
        input_ids = self.template.encode_oneturn(tokenizer=self.tokenizer, messages=input_message)[0]
        input_ids = torch.tensor(input_ids).unsqueeze(0).to(self.model.device)
        while True:
            output_ids = self.model.generate(
                input_ids=input_ids,
                attention_mask=torch.ones_like(input_ids),
                max_new_tokens=512,  # Maximum length of the generated text
                num_return_sequences=1,  # Number of sequences per input
                temperature=1.0,  # Sampling temperature
                top_k=50,  # Top-k sampling
                top_p=0.95,  # Top-p (nucleus sampling)
                do_sample=True,  # Enable sampling
            )[0]
            input_length = (input_ids != self.tokenizer.pad_token_id).sum(dim=1)  # Shape: [batch_size]
            new_tokens = output_ids[input_length:].tolist()

            # Decode the newly generated tokens
            generated_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            # print(generated_text.split('【倾听者回复】：')[0])
            try:
                generated_text = generated_text.split('【倾听者回复】：')[-1]
                break
            except IndexError:
                continue
        return generated_text

    def interact(self) -> None:
        conversation = []
        while True:
            user_response = input('用户：')
            conversation.append({'role': 'user', 'content': user_response})
            input_dict = {'conversation': conversation}
            input_text = self.llm_template.format_example(input_dict)
            therapist = self.__respond__(input_text)
            output_text = therapist.split('【倾听者回复】：')[-1]
            print('咨询师：', therapist)
            conversation.append({'role': 'assistant', 'content': output_text})


def chat(model, tok, ques, history=[], **kw):
    iids = tok.apply_chat_template(
        history + [{'role': 'user', 'content': ques}],
        add_generation_prompt=1,
    )
    oids = model.generate(
        inputs=torch.tensor([iids]).to(model.device),
        **kw,
    )
    oids = oids[0][len(iids):].tolist()
    if oids[-1] == tok.eos_token_id:
        oids = oids[:-1]
    ans = tok.decode(oids)

    return ans


def soulchat():
    # GPU设置
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # 加载模型与tokenizer
    model_name_or_path = '/home/v-jiaswang/models/SoulChat2.0-Qwen2-7B'
    model = AutoModelForCausalLM.from_pretrained(model_name_or_path, trust_remote_code=True).half()
    model.to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)

    history = []
    while True:
        user_input = input("用户：")
        history.append({'role': 'user', 'content': user_input})
        # 拼接对话历史
        response = chat(model, tokenizer, user_input, history=history, max_length=2048, num_beams=1,
                        do_sample=True, top_p=0.75, temperature=0.95, logits_processor=None)
        print("心理咨询师：", response)
        history.append({'role': 'assistant', 'content': response})


def main(yaml_path: str = 'interactive_models/user_simulator.yaml') -> None:
    # load configuration
    # soulchat()
    args = yaml.safe_load(Path(yaml_path).read_text())

    # start inference
    # interact = UserSimulator(args)
    interact = EmpatheticLLM(args)
    interact.interact()


if __name__ == '__main__':
    Fire(main)
