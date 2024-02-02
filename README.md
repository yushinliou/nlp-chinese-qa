# Chinese Question Answering
This work combines multiple choice and question answering models to select appropriate texts from multiple options and answer specified questions based on the texts.


### Reproduce
Execute the following code in the terminal
```shell
# Download model, tokenizer, data
bash download.sh
# Sequentially executes mc_pred, qa_pred to generate the final prediction result qa_pred.csv
# You can specify a location to save pred_qa, or by default, it will be saved in the same root directory as qa_pred.py
bash ./run.sh path/to/pred_qa.csv
```
### Train model
```shell
# Internet connection required to download model, tokenizer from Hugging Face to download pretrain model
# Multiple choice generates ./data/mc.csv
# Question answering then reads /mc.csv, generating pred_qa.csv
python ./multiple-choice/mc.py 
python ./question-answering/qa.py
```
Please see `report.pdf` for more detailed information, including model structure, perofrmance and the model config.
___
這隻程式碼混合了多重選擇，以及問答兩種模型以完成在多個文本當中選擇合適的文本，並根據文本回答指定問題
## Chinese version
### Reproduce
在終端機執行以下程式碼
```shell
# 下載model, tokenizer, data
bash download.sh
# 會執行依序執行mc_pred, qa_pred生成最終預測結果 qa_pred.csv
# 可以傳入pred_qa希望儲存的位置，或者defalut會存在跟qa_pted.py同一個根目錄下面
bash ./run.sh path/to/pred_qa.csv
```

### Train model
在終端機執行以下程式碼
```shell
# 需要網路環境download model, tokenizer, 從hugging face 下載 pretrain model
# multiple choice 生成./data/mc.csv
# question answering接著讀取/mc.csv，生成pred_qa.csv
python ./multiple-choice/mc.py 
python ./question-answering/qa.py 
```

