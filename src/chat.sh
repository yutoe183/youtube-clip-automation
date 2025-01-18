#!/bin/sh
# 作業用ルートディレクトリで実行 source src/chat.sh arg1 arg2 [arg3 arg4 arg5 arg6 arg7]
# 引数(必須2個 + 任意5個 + オプション): 作成するディレクトリのパス, YouTubeのChannel ID, 検索文字列(厳しめ), 検索文字列(緩め), 検索文字列(カウント用), 取得開始日(YYYYMMDD), 取得終了日(YYYYMMDD), オプション(-f: results.txtを強制上書きする場合)

current_dir=`pwd`
source venv/yt-dlp_moviepy/bin/activate
mkdir "$1"
cd "$1"
mkdir live_chat extract
rm -f extract/list_url.txt
yt-dlp --flat-playlist --print-to-file "%(webpage_url)s" extract/list_url.txt "https://www.youtube.com/channel/$2"
python "${current_dir}"/src/download_chat.py "${@:3}"
python "${current_dir}"/src/clustering_chat.py "${@:3}"
cd "${current_dir}"
deactivate
