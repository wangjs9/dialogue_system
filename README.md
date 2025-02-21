# A Dialogue System

## Prepare the environment
The environment configurations are stored in the ``coach.yaml``

## Set the Model Paths
The configurations can be set in the ``user_interface/model.json``.

- "SFT_LORA_PATH": "/home/v-jiaswang/checkpoint/EmpatheticLLMs/empathetic_sft_v1.0",
- "DPO_LORA_PATH": "/home/v-jiaswang/checkpoint/EmpatheticLLMs/empathetic_dpo_v2.0"

These two paths are kaitaosong/coach/checkpoint/EmpatheticLLMs/xxx
## Start the Program
```python -m user_interface.main_app```