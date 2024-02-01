# Homework 2 ADL NTU

# reproduce
```shell
# 下載model, tokenizer, data
bash download.sh
# 會執行依序執行mc_pred, qa_pred生成最終預測結果 qa_pred.csv
# 可以傳入pred_qa希望儲存的位置，或者defalut會存在跟qa_pted.py同一個根目錄下面
bash ./run.sh path/to/pred_qa.csv
```

# train model
```shell
# 需要網路環境download model, tokenizer, 從hugging face 下載 pretrain model
# multiple choice 生成./data/mc.csv
# question answering接著讀取/mc.csv，生成pred_qa.csv
python ./multiple-choice/mc.py 
python ./question-answering/qa.py 
```

