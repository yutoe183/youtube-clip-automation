#!/bin/sh
# 作業用ルートディレクトリで実行 source src/chat.sh arg1 arg2 [arg3, arg4]
# 引数(必須3個 + 任意2個): 作成するディレクトリ名, YouTubeのChannel ID, 検索文字列, 取得開始日(YYYYMMDD), 取得終了日(YYYYMMDD)

source venv/yt-dlp_moviepy/bin/activate
mkdir -p data/"$1"/live_chat
cd data/"$1"/live_chat
if [ $# -ge 5 ]
then
  yt-dlp --skip-download --write-subs --write-comments --dateafter $4 --datebefore $5 -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
elif [ $# == 4 ]
then
  yt-dlp --skip-download --write-subs --write-comments --dateafter $4 -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
else
  yt-dlp --skip-download --write-subs --write-comments -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
fi
cd ..
mkdir extract
cd extract
grep -E "$3" ../live_chat/* > search.txt
python ../../../src/clustering_chat.py "$3"
cd ../../..
deactivate
