#!/bin/sh
# 作業用ルートディレクトリで実行 source setup.sh [arg1]
# 引数(任意1個): Pythonのバージョン(3.12等。デフォルト値は3)

python_version=${1:-3}

sudo apt update
sudo apt install "python${python_version}-venv"

mkdir -p {src,data,venv}
rm -fr venv/yt-dlp_moviepy

"python${python_version}" -m venv venv/yt-dlp_moviepy
source venv/yt-dlp_moviepy/bin/activate
pip install -U pip
pip install -U yt-dlp
pip install -U moviepy
deactivate
