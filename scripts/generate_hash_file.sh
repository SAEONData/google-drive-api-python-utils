if [ ! $# -eq 2 ]
  then
    echo "Insufficient arguments supplied. USAGE: bash generate_hash_file.sh <INPUT_FILE> <OUTPUT_DIR>"
    exit
fi

INFILE=$1
OUTDIR=$2

if [ ! -f "$INFILE" ]; then
    echo "$INFILE doesn't exist"
    exit
fi

if [ ! -d "$OUTDIR" ]; then
    echo "$OUTDIR doesn't exist"
    exit
fi

#./check_google_file_upload.py
MD5_SUM=$(md5sum $INFILE | cut -d ' ' -f1)
echo $MD5_SUM

BASENAME=$(basename $INFILE)
HASH_OUTPUT_FILE="$BASENAME.$MD5_SUM"
#echo $OUTDIR/$HASH_OUTPUT_FILE
touch $OUTDIR/$HASH_OUTPUT_FILE
