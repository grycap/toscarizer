#!/bin/bash

FILE_NAME=`basename "$INPUT_FILE_PATH"`
OUTPUT_FILE="$TMP_OUTPUT_DIR/$FILE_NAME"

echo "SCRIPT: Processing file '$INPUT_FILE_PATH', saving the output in '$OUTPUT_FILE'"
python main.py -i "$INPUT_FILE_PATH" -o "$OUTPUT_FILE"
