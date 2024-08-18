#!/bin/sh
# 作業用ルートディレクトリで実行 source src/chat.sh arg1 arg2 [arg3 arg4 arg5 arg6]
# 引数(必須2個 + 任意4個): 作成するディレクトリのパス, YouTubeのChannel ID, 検索文字列(厳しめ), 検索文字列(緩め), 取得開始日(YYYYMMDD), 取得終了日(YYYYMMDD)

current_dir=`pwd`
source venv/yt-dlp_moviepy/bin/activate
if [ ! -d "$1"/live_chat ]
then
  mkdir -p "$1"/live_chat
  cd "$1"/live_chat
  if [ $# -ge 6 ]
  then
    yt-dlp --skip-download --write-subs --write-comments --cookies "${current_dir}"/src/auth/cookies.txt --dateafter $5 --datebefore $6 -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
  elif [ $# == 5 ]
  then
    yt-dlp --skip-download --write-subs --write-comments --cookies "${current_dir}"/src/auth/cookies.txt --dateafter $5 -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
  else
    yt-dlp --skip-download --write-subs --write-comments --cookies "${current_dir}"/src/auth/cookies.txt -o "%(upload_date)s[%(id)s]" "https://www.youtube.com/channel/$2"
  fi
  cd "${current_dir}"
fi
if [ $# -ge 3 ] && [ ! -e "$1"/extract/results.txt ]
then
  mkdir -p "$1"/extract
  cd "$1"
  if [ $# -ge 4 ]
  then
    python "${current_dir}"/src/clustering_chat.py "$3" "$4"
  else
    python "${current_dir}"/src/clustering_chat.py "$3"
  fi
  cd "${current_dir}"
fi
deactivate
