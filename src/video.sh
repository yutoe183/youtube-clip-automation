#!/bin/sh
# 作業用ルートディレクトリで実行 source src/video.sh arg1 [arg2]
# 引数(必須1個 + 任意1個): 作成したディレクトリ名, 検索文字列

source venv/yt-dlp_moviepy/bin/activate
cd data/"$1"/extract
if [ $# -ge 2 ]
then
  python ../../../src/sum_superchat.py "$2"
else
  python ../../../src/sum_superchat.py
fi
cd ..
mkdir clip
cd clip
python ../../../src/download_clip.py
cd ..
mkdir dst
cd dst
python ../../../src/edit_video.py
cd ../../..
deactivate
