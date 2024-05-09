#!/bin/sh
# 作業用ルートディレクトリで実行 source src/video.sh arg1 [arg2]
# 引数(必須1個 + 任意1個): 作成したディレクトリのパス, -d (ダウンロードした元動画を削除する場合)

current_dir=`pwd`
source venv/yt-dlp_moviepy/bin/activate
cd "$1"
mkdir download clip
if [ $# -ge 2 ]
then
  python "${current_dir}"/src/download_clip.py "$2"
else
  python "${current_dir}"/src/download_clip.py
fi
mkdir dst
cd dst
python "${current_dir}"/src/edit_video.py
cd "${current_dir}"
deactivate
