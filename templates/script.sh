#!/bin/bash

FILE_NAME=`basename "$INPUT_FILE_PATH"`

echo "SCRIPT: Processing file '$INPUT_FILE_PATH', saving the output in '$TMP_OUTPUT_DIR'"
# In case of partitions
# python main.py -i "$INPUT_FILE_PATH" -o "$TMP_OUTPUT_DIR" -x "$INTERMEDIATE"
python main.py -i "$INPUT_FILE_PATH" -o "$TMP_OUTPUT_DIR"
