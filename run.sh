# "${1}" is one argument passed to the script, the output_dir
python3 ./multiple-choice/mc_pred.py
python3 ./question-answering/qa_pred.py --pred_file "${1}"