echo "= = = = = = = = = = = = = ="
echo "The project is running..."
currentDate=`date`
echo $currentDate
start=`date +%s`
echo "= = = = = = = = = = = = = ="

python train.py \
    --len_input 'topic' \
    --len_output 'no' \
    --output_dir ./output/2 \
    --train_file ./data/macdial_flatten/train.json \
    --validation_file ./data/macdial_flatten/val.json \
    --test_file ./data/macdial_flatten/test.json \
    --text_column dialogue \
    --summary_column summary \
    --model_name_or_path facebook/bart-large \
    --model_type bart \
    --max_source_length 1024 \
    --min_target_length 1 \
    --max_target_length 400 \
    --num_beams 4 \
    --learning_rate 3e-5 \
    --weight_decay 1e-3 \
    --label_smoothing 0.1 \
    --length_penalty 1.0 \
    --num_train_epochs 1 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 32 \
    --per_device_eval_batch_size 8 \
    --per_device_test_batch_size 8 \
    --num_warmup_steps 300 \
    --cache_dir ./output/cache \
    --overwrite_cache True \
    --seed 42 \

echo "= = = = = = = = = = = = = ="
echo "The project is Finished..."
end=`date +%s`
runtime=$((end-start))
echo "The program takes '$((runtime / 60))' minutes."
echo "= = = = = = = = = = = = = ="
