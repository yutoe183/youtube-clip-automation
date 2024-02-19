# youtube-clip-automation
YouTube切り抜き動画の自動生成ツール

## 概要
YouTubeのライブ配信アーカイブの切り抜き動画を自動生成します。具体的には、以下の手順を自動化します。

- ライブ配信のアーカイブからチャットとコメントを取得
- 特定のキーワードに該当するチャットとコメントを抽出
- 該当の動画をダウンロード
- 動画編集(切り抜き、結合)

### パッケージ
以下のPythonパッケージを利用しています。

- yt-dlp
- moviepy

## 使い方
### 対応環境
Linux, Python3

#### 動作確認環境
OS: Ubuntu22.04LTS / WSL2
Python: 3.10.12, 3.12.1

### 環境構築
```source setup.sh```

Pythonのバージョンを指定する場合
```source setup.sh 3.12```

### 使用手順
#### 1. チャットの取得、抽出、クラスタリング
```source src/chat.sh 作成するディレクトリ名 YouTubeのチャンネルID 検索文字列 取得開始日(YYYYMMDD) 取得終了日(YYYYMMDD)```

- 必須引数(3個): 作成するディレクトリ名 YouTubeのチャンネルID 検索文字列
- 任意引数(2個): 取得開始日(YYYYMMDD) 取得終了日(YYYYMMDD)

作成するディレクトリ名は任意です。

検索文字列は正規表現で記述可能です。
この文字列は、候補の絞り込みに使われます。

取得開始日から取得終了日までに投稿された動画のデータを取得します。

切り抜き箇所の候補は `data/作成したディレクトリ名/extract/results.txt` に出力されます。

なお、クラスタリング前の `grep` コマンドによる検索結果は `data/作成したディレクトリ名/extract/search.txt` に出力されます。

#### 2. 実際にYouTubeで確認、results.txtを編集
`results.txt` 内の候補のうち、切り抜きに使用する動画について以下の編集をします。

1. 開始時刻と終了時刻を切り抜き部分に一致するように修正
1. 行の先頭に一文字追記 (例えば `-` など)
1. (任意) 並び順を変更

以降の手順で、 `results.txt` 内の該当動画が上から順に結合されます。動画順序の変更はここで実施します。(デフォルトは投稿日順)

#### 3. 動画ダウンロード、動画編集 (+ スパチャ額集計)
```source src/video.sh 作成したディレクトリ名 検索文字列```

- 必須引数(1個): 作成したディレクトリ名
- 任意引数(1個): 検索文字列

検索文字列は正規表現で記述可能です。
この文字列は、スーパーチャットやチャットの集計に使われます。

ダウンロードされた動画及び各切り抜きは、 `data/作成したディレクトリ名/clip/` 内に保存されます。

完成動画は `data/作成したディレクトリ名/dst/clip.mp4` に出力されます。

タイムスタンプは `data/作成したディレクトリ名/dst/timestamp.txt` に出力されます。

なお、切り抜き作成後に元動画を削除したい場合、 `download_clip.py` 内の定数 `REMOVE_ORIGINAL` を `True` に変更します。ダウンロード、切り抜き作成、元動画削除という一連の流れが各動画ごとに実行されます。

##### 切り抜き箇所の修正
切り抜きのタイミングをずらしたい場合、以下の手順で修正できます。

1. `results.txt` の開始時刻と終了時刻を修正
1. `data/作成したディレクトリ名/clip/` 内の該当切り抜き動画 (例: `data/example/clip/20240220[AAAAAAAAAAA]_clip0.mp4`) を削除
1. 手順3のコマンドを再度実行 `source src/video.sh 作成したディレクトリ名 検索文字列`

## 使用例、コード解説
詳細は以下の記事に記載しています。
https://diary-039.com/entry/2024/02/20/youtube-clip-automation
