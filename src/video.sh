#!/bin/sh
# 作業用ルートディレクトリで実行 source src/video.sh arg1 [arg2, arg3]
# 引数(必須1個 + 任意2個): 作成したディレクトリ名, 検索文字列, -d (ダウンロードした元動画を削除する場合)

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
if [ $# -ge 3 ]
then
  python ../../../src/download_clip.py "$3"
else
  python ../../../src/download_clip.py
fi
cd ..
mkdir dst
cd dst
python ../../../src/edit_video.py
cd ../../..
deactivate
