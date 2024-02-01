# -*- coding: utf-8 -*-
"""mc_pred.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vCphml0r5-YGuwHwyqMYsVNfw29DxmCk
"""

import os
# os.chdir('/content/drive/MyDrive/adl-hw2')

os.chdir('./multiple-choice')
os.system('pip install -r requirements.txt')
os.system('pip install transformers')

import argparse
import json
import logging
import math
import os
import random
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Optional, Union

import datasets
import torch
import pandas as pd
from datasets import load_dataset
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

import evaluate
import transformers
from accelerate import Accelerator
from accelerate.logging import get_logger
from accelerate.utils import set_seed
from huggingface_hub import Repository
from transformers import (
    CONFIG_MAPPING,
    MODEL_MAPPING,
    AutoConfig,
    AutoModelForMultipleChoice,
    AutoTokenizer,
    PreTrainedTokenizerBase,
    SchedulerType,
    default_data_collator,
    get_scheduler,
)

from transformers.utils import PaddingStrategy, check_min_version, get_full_repo_name, send_example_telemetry
from pathlib import Path
from datasets import Dataset
import datasets

# Will error if the minimal version of Transformers is not installed. Remove at your own risks.
# check_min_version("4.24.0.dev0")

logger = get_logger(__name__)
# You should update this to your particular problem to have better documentation of `model_type`
MODEL_CONFIG_CLASSES = list(MODEL_MAPPING.keys())
MODEL_TYPES = tuple(conf.model_type for conf in MODEL_CONFIG_CLASSES)

def parse_args():
    parser = argparse.ArgumentParser(description="Finetune a transformers model on a multiple choice task")
    parser.add_argument(
        "--model_name_or_path",
        type=str,
        help="Path to pretrained model or model identifier from huggingface.co/models.",
        required=False,
        default='../cache/test-mc-no-trainer/' # bert-base-uncased
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
        help="The name of the dataset to use (via the datasets library).",
        default='swag',
    )
    parser.add_argument(
        "--output_dir", 
        type=str, 
        help="Where to store the final model.",
        default='../cache/test-mc-no-trainer', 
        )    
    parser.add_argument(
        "--pad_to_max_length",
        action="store_true",
        help="If passed, pad all samples to `max_length`. Otherwise, dynamic padding is used.",
    )

    #=======================================================================

    parser.add_argument(
        "--dataset_config_name",
        type=str,
        default=None,
        help="The configuration name of the dataset to use (via the datasets library).",
    )
    parser.add_argument(
        "--train_file", type=str, default=None, help="A csv or a json file containing the training data."
    )
    parser.add_argument(
        "--validation_file", type=str, default=None, help="A csv or a json file containing the validation data."
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=512,
        help=(
            "The maximum total input sequence length after tokenization. Sequences longer than this will be truncated,"
            " sequences shorter will be padded if `--pad_to_max_lengh` is passed."
        ),
    )
    parser.add_argument(
        "--config_name",
        type=str,
        default=None,
        help="Pretrained config name or path if not the same as model_name",
    )
    parser.add_argument(
        "--tokenizer_name",
        type=str,
        default=None,
        help="Pretrained tokenizer name or path if not the same as model_name",
    )
    parser.add_argument(
        "--use_slow_tokenizer",
        action="store_true",
        help="If passed, will use a slow tokenizer (not backed by the 🤗 Tokenizers library).",
    )
    parser.add_argument(
        "--per_device_train_batch_size",
        type=int,
        default=1,
        help="Batch size (per device) for the training dataloader.",
    )
    parser.add_argument(
        "--per_device_eval_batch_size",
        type=int,
        default=1,
        help="Batch size (per device) for the evaluation dataloader.",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=3e-5,
        help="Initial learning rate (after the potential warmup period) to use.",
    )
    parser.add_argument("--weight_decay", type=float, default=0.0, help="Weight decay to use.")
    parser.add_argument("--num_train_epochs", type=int, default=5, help="Total number of training epochs to perform.")
    parser.add_argument(
        "--max_train_steps",
        type=int,
        default=None,
        help="Total number of training steps to perform. If provided, overrides num_train_epochs.",
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=2,
        help="Number of updates steps to accumulate before performing a backward/update pass.",
    )
    parser.add_argument(
        "--lr_scheduler_type",
        type=SchedulerType,
        default="linear",
        help="The scheduler type to use.",
        choices=["linear", "cosine", "cosine_with_restarts", "polynomial", "constant", "constant_with_warmup"],
    )
    parser.add_argument(
        "--num_warmup_steps", type=int, default=0, help="Number of steps for the warmup in the lr scheduler."
    )
    
    parser.add_argument("--seed", type=int, default=None, help="A seed for reproducible training.")
    parser.add_argument(
        "--model_type",
        type=str,
        default=None,
        help="Model type to use if training from scratch.",
        choices=MODEL_TYPES,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activate debug mode and run training only with a subset of data.",
        default=True,
    )
    parser.add_argument("--push_to_hub", action="store_true", help="Whether or not to push the model to the Hub.")
    parser.add_argument(
        "--hub_model_id", type=str, help="The name of the repository to keep in sync with the local `output_dir`."
    )
    parser.add_argument("--hub_token", type=str, help="The token to use to push to the Model Hub.")
    parser.add_argument(
        "--checkpointing_steps",
        type=str,
        default=None,
        help="Whether the various states should be saved at the end of every n steps, or 'epoch' for each epoch.",
    )
    parser.add_argument(
        "--resume_from_checkpoint",
        type=str,
        default=None,
        help="If the training should continue from a checkpoint folder.",
    )
    parser.add_argument(
        "--with_tracking",
        action="store_true",
        help="Whether to enable experiment trackers for logging.",
    )
    parser.add_argument(
        "--report_to",
        type=str,
        default="all",
        help=(
            'The integration to report the results and logs to. Supported platforms are `"tensorboard"`,'
            ' `"wandb"` and `"comet_ml"`. Use `"all"` (default) to report to all integrations.'
            "Only applicable when `--with_tracking` is passed."
        ),
    )
    # args = parser.parse_args()
    args, unknown = parser.parse_known_args()

    if args.push_to_hub:
        assert args.output_dir is not None, "Need an `output_dir` to create a repo when `--push_to_hub` is passed."

    return args

args = parse_args()
# Sending telemetry. Tracking the example usage helps us better allocate resources to maintain them. The
# information sent is the one passed as arguments along with your Python/PyTorch versions.
send_example_telemetry("run_swag_no_trainer", args)

# Initialize the accelerator. We will let the accelerator handle device placement for us in this example.
# If we're using tracking, we also need to initialize it here and it will by default pick up all supported trackers
# in the environment
accelerator_log_kwargs = {}

if args.with_tracking:
    accelerator_log_kwargs["log_with"] = args.report_to
    accelerator_log_kwargs["logging_dir"] = args.output_dir

accelerator = Accelerator(gradient_accumulation_steps=args.gradient_accumulation_steps, **accelerator_log_kwargs)

# Make one log on every process with the configuration for debugging.
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger.info(accelerator.state, main_process_only=False)
if accelerator.is_local_main_process:
    datasets.utils.logging.set_verbosity_warning()
    transformers.utils.logging.set_verbosity_info()
else:
    datasets.utils.logging.set_verbosity_error()
    transformers.utils.logging.set_verbosity_error()

# If passed along, set the training seed now.
if args.seed is not None:
    set_seed(args.seed)

@dataclass
class DataCollatorForMultipleChoice:
    """
    Data collator that will dynamically pad the inputs for multiple choice received.

    Args:
        tokenizer ([`PreTrainedTokenizer`] or [`PreTrainedTokenizerFast`]):
            The tokenizer used for encoding the data.
        padding (`bool`, `str` or [`~utils.PaddingStrategy`], *optional*, defaults to `True`):
            Select a strategy to pad the returned sequences (according to the model's padding side and padding index)
            among:

            - `True` or `'longest'`: Pad to the longest sequence in the batch (or no padding if only a single sequence
              if provided).
            - `'max_length'`: Pad to a maximum length specified with the argument `max_length` or to the maximum
              acceptable input length for the model if that argument is not provided.
            - `False` or `'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of different
              lengths).
        max_length (`int`, *optional*):
            Maximum length of the returned list and optionally padding length (see above).
        pad_to_multiple_of (`int`, *optional*):
            If set will pad the sequence to a multiple of the provided value.

            This is especially useful to enable the use of Tensor Cores on NVIDIA hardware with compute capability >=
            7.5 (Volta).
    """

    tokenizer: PreTrainedTokenizerBase
    padding: Union[bool, str, PaddingStrategy] = True
    max_length: Optional[int] = None
    pad_to_multiple_of: Optional[int] = None

    def __call__(self, features):
        label_name = "label" if "label" in features[0].keys() else "labels"
        id_name = 'ids'

        if label_name in features[0].keys():
          labels = [feature.pop(label_name) for feature in features]

        ids = [feature.pop(id_name) for feature in features]

        batch_size = len(features)
        num_choices = len(features[0]["input_ids"])
        flattened_features = [
            [{k: v[i] for k, v in feature.items()} for i in range(num_choices)] for feature in features
        ]
        flattened_features = list(chain(*flattened_features))

        batch = self.tokenizer.pad(
            flattened_features,
            padding=self.padding,
            max_length=self.max_length,
            pad_to_multiple_of=self.pad_to_multiple_of,
            return_tensors="pt",
        )

        # Un-flatten
        batch = {k: v.view(batch_size, num_choices, -1) for k, v in batch.items()}
        # Add back labels
        # if labels:
        if 'labels' in locals():
          batch["labels"] = torch.tensor(labels, dtype=torch.int64)        
        batch["ids"] = ids
        return batch

# Handle the repository creation
if accelerator.is_main_process:
    if args.push_to_hub:
        if args.hub_model_id is None:
            repo_name = get_full_repo_name(Path(args.output_dir).name, token=args.hub_token)
        else:
            repo_name = args.hub_model_id
        repo = Repository(args.output_dir, clone_from=repo_name)

        with open(os.path.join(args.output_dir, ".gitignore"), "w+") as gitignore:
            if "step_*" not in gitignore:
                gitignore.write("step_*\n")
            if "epoch_*" not in gitignore:
                gitignore.write("epoch_*\n")
    elif args.output_dir is not None:
        os.makedirs(args.output_dir, exist_ok=True)
accelerator.wait_for_everyone()

# load model, tokenizer and config
config = AutoConfig.from_pretrained(args.model_name_or_path)
tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=True)
model = AutoModelForMultipleChoice.from_pretrained(args.model_name_or_path, config=config)
# padding
padding = "max_length" if args.pad_to_max_length else False

# Use the device given by the `accelerator` object.
device = accelerator.device
model.to(device)

# 設定資料欄位
# column_names
# ['video-id', 'fold-ind', 'startphrase', 'sent1', 'sent2', 'gold-source', 'ending0', 'ending1', 'ending2', 'ending3', 'label']

ending_names = [f"ending{i}" for i in range(4)]
context_name = "sent1"
question_id_name = "id"
question_header_name = "sent2"
label_column_name = "label"

# 轉換資料格式
def trans_format(ori_data, data_type='train_data'):
  new_data_json = []
  for old_data in ori_data:
    new_data = {}
    paragraphs = old_data['paragraphs']
    
    new_data['id'] = old_data['id']
    new_data['sent1'] = old_data['question']
    new_data['sent2'] = ''
    new_data['ending0'] = content_data[paragraphs[0]]
    new_data['ending1'] = content_data[paragraphs[1]]
    new_data['ending2'] = content_data[paragraphs[2]]
    new_data['ending3'] = content_data[paragraphs[3]]
    if data_type == 'train_data':
      new_data['label'] = paragraphs.index(old_data['relevant'])
    new_data_json.append(new_data)
  return new_data_json

def preprocess_function(examples):

    question_headers = examples[question_header_name]
    question_ids = examples[question_id_name]
    first_sentences = [[context] * 4 for context in examples[context_name]]
    second_sentences = [
        [f"{header} {examples[end][i]}" for end in ending_names] for i, header in enumerate(question_headers)
    ]
    
    if label_column_name in examples:
      labels = examples[label_column_name]

    # Flatten out
    first_sentences = list(chain(*first_sentences))
    second_sentences = list(chain(*second_sentences))

    # Tokenize
    tokenized_examples = tokenizer(
        first_sentences,
        second_sentences,
        max_length=args.max_length,
        padding=padding,
        truncation=True,
    )
    # Un-flatten
    tokenized_inputs = {k: [v[i : i + 4] for i in range(0, len(v), 4)] for k, v in tokenized_examples.items()}
    if label_column_name in examples:
      tokenized_inputs["labels"] = labels
    tokenized_inputs["ids"] = question_ids

    return tokenized_inputs

"""## load_data"""

# 讀入原始資料
train_data = json.loads(Path('../data/train.json').read_text())
val_data = json.loads(Path('../data/valid.json').read_text())
test_data = json.loads(Path('../data/test.json').read_text())
content_data = json.loads(Path('../data/context.json').read_text())

# 轉換資料格式
new_train_data = trans_format(train_data)
new_val_data = trans_format(val_data)
new_test_data = trans_format(test_data,'test_data')

new_train_data = Dataset.from_list(new_train_data)
new_val_data = Dataset.from_list(new_val_data)
new_test_data = Dataset.from_list(new_test_data)

new_raw_datasets = datasets.DatasetDict({"train":new_train_data,"validation":new_val_data })
test_raw_datasets = datasets.DatasetDict({"test":new_test_data})

# test data
with accelerator.main_process_first():
    processed_datasets_test = test_raw_datasets.map(
        preprocess_function, batched=True, remove_columns=test_raw_datasets["test"].column_names
    )

test_dataset = processed_datasets_test["test"]


# DataLoaders creation:
if args.pad_to_max_length:
    print("args.pad_to_max_length",args.pad_to_max_length)
    # If padding was already done ot max length, we use the default data collator that will just convert everything
    # to tensors.
    data_collator = default_data_collator
else:
    print("DataCollatorWithPadding")
    # Otherwise, `DataCollatorWithPadding` will apply dynamic padding for us (by padding to the maximum length of
    # the samples passed). When using mixed precision, we add `pad_to_multiple_of=8` to pad all tensors to multiple
    # of 8s, which will enable the use of Tensor Cores on NVIDIA hardware with compute capability >= 7.5 (Volta).
    data_collator = DataCollatorForMultipleChoice(
        tokenizer, pad_to_multiple_of=(8 if accelerator.use_fp16 else None)
    )

test_dataloader = DataLoader(test_dataset, collate_fn=data_collator, batch_size=args.per_device_eval_batch_size)

"""# do predict"""

def flat_list(l):
  return [item for sublist in l for item in sublist]
def trans_ind(row):
  return row['paragraphs'][row['result']]

# test
test_dataloader = accelerator.prepare(test_dataloader)
# Prepare everything with our `accelerator`.
model = accelerator.prepare(model)

id_list = []
result_list = []
model.eval()
for step, batch in enumerate(test_dataloader):
    with torch.no_grad():
        id_list.append(batch['ids'])
        batch.pop('ids', None)
        outputs = model(**batch)
    predictions = outputs.logits.argmax(dim=-1).tolist()
    result_list.append(predictions)

# 展開list
flat_id = flat_list(id_list)
flat_result = flat_list(result_list)
test_df = pd.DataFrame({'id': flat_id,'result': flat_result})
test_json_df = pd.DataFrame.from_dict(test_data)

# 合併
merge = test_df.merge(test_json_df[['id','paragraphs']], on='id')
merge['result_ind'] = merge.apply(lambda row : trans_ind(row), axis = 1)
merge = merge[['id','result_ind']]

# 儲存結果
pred_test_fname = f"../data/mc.csv"
merge.to_csv(pred_test_fname, encoding='utf-8', index=False)