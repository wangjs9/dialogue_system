import json
import re
import os
import copy

abs_path = os.path.abspath(__file__)
abs_dir = '/'.join(abs_path.split('/')[:-1])
with open(f'{abs_dir}/config.json', 'r') as f:
    configs = json.load(f)
ROOT_DIR = os.environ.get('ROOT_DIR', configs['ROOT_DIR'])
MODEL_PATH = {model: path.format(ROOT_DIR=ROOT_DIR) if 'ROOT_DIR' in path else path for model, path in
              configs['model_path'].items()}
TRAIN_DATA_PATH = f'{ROOT_DIR}/datasets/PsyDTCorpus/PsyDTCorpus_train_mulit_turn_packing.json'
TEST_DATA_PATH = f'{ROOT_DIR}/datasets/PsyDTCorpus/PsyDTCorpus_test_single_turn_split.json'
USER_STATE_PATH = f'{ROOT_DIR}/datasets/PsyDTCorpus/PsyDTCorpus_train_user_state.jsonl'
ROLE_MAP = {'user': '来访者', 'assistant': '倾听者'}
END_POINTS = configs['end_points']


def is_json(myjson):
    """
    Checks whether a given string is a valid JSON.

    Parameters:
        myjson (str): The string to be checked.

    Returns:
        bool: True if the string is a valid JSON, False otherwise.
    """
    try:
        _ = json.loads(myjson)
    except ValueError:
        return False
    return True


def is_json_inside(text):
    """
    Checks whether a given string contains valid JSON(s).

    Parameters:
        text (str): The string to be checked.

    Returns:
        bool: True if the string contains valid JSON(s), False otherwise.
    """
    text = re.sub(r"\s+", " ", text)
    matches = re.findall(r"\{.*?\}", text)
    for match in matches:
        if is_json(match):
            return True
    return False


def extract_jsons(text):
    """
    Extracts all valid JSON objects from a given string.

    Parameters:
        text (str): The string from which JSON objects are to be extracted.

    Returns:
        List[Dict]: A list of all extracted JSON objects.
    """
    text = re.sub(r"\s+", " ", text)
    matches = re.findall(r"\{.*?\}", text)
    parsed_jsons = []
    for match in matches:
        try:
            json_object = json.loads(match)
            parsed_jsons.append(json_object)
        except ValueError:
            pass
    return parsed_jsons


def extract_code(text):
    """
    Extracts all code blocks encapsulated by '```' from a given string.

    Parameters:
        text (str): The string from which Python code blocks are to be extracted.

    Returns:
        List[str]: A list of all extracted Python code blocks.
    """
    text = re.sub("```python", "```", text)
    matches = re.findall(r"```(.*?)```", text, re.DOTALL)
    parsed_codes = []
    for match in matches:
        parsed_codes.append(match)
    return parsed_codes


class AttributedDict(dict):
    """
    A dictionary class whose keys are automatically set as attributes of the class.

    The dictionary is serializable to JSON.

    Inherits from:
        dict: Built-in dictionary class in Python.

    Note:
        This class provides attribute-style access to dictionary keys, meaning you can use dot notation
        (like `my_dict.my_key`) in addition to the traditional bracket notation (`my_dict['my_key']`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError

    def __delattr__(self, key):
        del self[key]

    # check whether the key is string when adding the key
    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise ValueError("The key must be a string")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value


class Config(AttributedDict):
    """
    Config class to manage the configuration of the games.

    The class has a few useful methods to load and save the config.
    """

    # convert dict to Config recursively
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = init_config(value)  # convert dict to Config recursively
            # convert list of dict to list of Config recursively
            elif isinstance(value, list) and len(value) > 0:
                self[key] = [init_config(item) if isinstance(item, dict) else item for item in value]

    def save(self, path: str):
        # save config to file
        with open(path, "w") as f:
            json.dump(self, f, indent=4)

    @classmethod
    def load(cls, path: str):
        # load config from file
        with open(path) as f:
            config = json.load(f)
        return cls(config)

    def deepcopy(self):
        # get the config class so that subclasses can be copied in the correct class
        config_class = self.__class__
        # make a deep copy of the config
        return config_class(copy.deepcopy(self))


# Initialize with different config class depending on whether the config is for environment or backend
def init_config(config: dict):
    if not isinstance(config, dict):
        raise ValueError("The config must be a dict")

    # check if the config is for environment or backend
    elif "backend_type" in config:
        return BackendConfig(config)
    elif "role_desc" in config:
        return AgentConfig(config)
    else:
        return Config(config)


class BackendConfig(Config):
    """BackendConfig contains a backend_type field to indicate the name of the backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # check if the backend_type field is specified
        if "backend_type" not in self:
            raise ValueError("The backend_type field is not specified")


class AgentConfig(Config):
    """AgentConfig contains role_desc and backend fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # check if the role_desc field is specified
        if "role_desc" not in self:
            raise ValueError("The role_desc field is not specified")
        # check if the backend field is specified
        if "backend" not in self:
            raise ValueError("The backend field is not specified")
        # Make sure the backend field is a BackendConfig
        if not isinstance(self["backend"], BackendConfig):
            raise ValueError("The backend field must be a BackendConfig")


class Configurable:
    """Configurable is an interface for classes that can be initialized with a config."""

    def __init__(self, **kwargs):
        self._config_dict = kwargs

    @classmethod
    def from_config(cls, config: Config):
        return cls(**config)

    def to_config(self) -> Config:
        # Convert the _config_dict to Config
        return Config(**self._config_dict)

    def save_config(self, path: str):
        self.to_config().save(path)
