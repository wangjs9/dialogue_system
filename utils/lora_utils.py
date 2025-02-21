from fire import Fire
from llamafactory.train.tuner import export_model


def main(
        model_name_or_path: str = '/home/v-jiaswang/models/Qwen2.5-7B-Instruct',
        adapter_name_or_path: str = '/home/v-jiaswang/checkpoint/EmpatheticLLMs/EmpatheticLLM_cot',
        template: str = 'qwen2.5',
        finetuning_type: str = 'lora',
        trust_remote_code: bool = True,
        export_dir: str = '/home/v-jiaswang/models/EmpatheticLLM_v1_lora',
        export_size: int = 5,
        export_device: str = "auto",
        export_legacy_format: bool = False
):
    args = {
        'model_name_or_path': model_name_or_path,
        'adapter_name_or_path': adapter_name_or_path,
        'template': template,
        'finetuning_type': finetuning_type,
        'trust_remote_code': trust_remote_code,
        'export_dir': export_dir,
        'export_size': export_size,
        'export_device': export_device,
        'export_legacy_format': export_legacy_format,
    }
    export_model(args)


if __name__ == "__main__":
    Fire(main)
