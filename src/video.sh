#!/bin/sh
# 作業用ルートディレクトリで実行 source src/video.sh arg1 [option]
# 引数(必須1個 + オプション): 作成したディレクトリのパス, オプション (-a: 動画全編をダウンロードする場合, -d: ダウンロードした元動画を削除する場合)

current_dir=`pwd`
source venv/yt-dlp_moviepy/bin/activate
cd "$1"
mkdir download clip
python "${current_dir}"/src/download_clip.py ${@:2}
mkdir dst
cd dst
python "${current_dir}"/src/edit_video.py
cd "${current_dir}"
deactivate
