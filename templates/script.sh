#!/bin/bash

FILE_NAME="$(basename "$INPUT_FILE_PATH" | cut -f 1 -d '.')"

if [[ $FILE_NAME == aisprint-* ]]
then
	OUTPUT_FILE="$TMP_OUTPUT_DIR/$FILE_NAME"
    UUID="${FILE_NAME:9:36}"
else
    UUID=$(uuidgen) 
	OUTPUT_FILE="$TMP_OUTPUT_DIR/aisprint-$UUID"
fi

echo "SCRIPT: Processing file '$INPUT_FILE_PATH', saving the output in '$OUTPUT_FILE'"
echo "UUID: $UUID"
# In case of partitions
# python main.py -i "$INPUT_FILE_PATH" -o "$TMP_OUTPUT_DIR" -x "$INTERMEDIATE"
python main.py -i "$INPUT_FILE_PATH" -o "$OUTPUT_FILE"
