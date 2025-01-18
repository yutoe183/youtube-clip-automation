import sys # argv
import os # remove, path.isfile, path.dirname
import glob # glob, escape
import yt_dlp # YoutubeDL

def getListURL(path): # ファイルからURLのリストを取得
  list_url = []
  with open(path) as f:
    for line in f:
      if len(line) > 11:
        list_url.append(line[:-1])
  return list_url

def downloadChat(dir_dst, list_url, dateafter, datebefore, cookiefile): # チャットのダウンロード
  MAX_RETRY_DOWNLOAD = 3 # ダウンロードに失敗した際の最大再試行回数
  option = {
    "outtmpl": dir_dst + "%(upload_date)s[%(id)s]", # 出力形式 投稿日[動画ID]
    "skip_download": True, # 動画のダウンロードをスキップ
    "writeinfojson": True, # infoファイルを出力
    "getcomments": True, # コメントをinfoファイルに出力
    "writesubtitles": True, # チャットを出力
    "daterange": yt_dlp.utils.DateRange(dateafter, datebefore), # ダウンロード対象期間
    "ignoreerrors": True, # エラーを無視して続行
    "cookiefile": cookiefile,
  }
  count = 0
  with yt_dlp.YoutubeDL(option) as ydl:
    for url in list_url:
      count += 1
      print("download: " + str(count) + " / " + str(len(list_url)))
      id = url[-11:]
      if len(glob.glob(glob.escape(dir_dst) + "*" + glob.escape(id) + "*")) == 0: # 出力先ファイルが既に存在する場合はダウンロードしない
        ydl.download([url])
      retry_download = MAX_RETRY_DOWNLOAD
      while retry_download > 0: # ダウンロード失敗時は再試行
        list_partfile = glob.glob(glob.escape(dir_dst) + "*" + glob.escape(id) + "*.part*")
        if len(list_partfile) <= 0:
          break
        for partfile in list_partfile: # ダウンロード途中のpartファイルを削除してから再ダウンロード
          if os.path.isfile(partfile):
            print("remove: " + partfile)
            os.remove(partfile)
        retry_download -= 1
        ydl.download([url])

def execute(dir_dst, path_list_url, dateafter, datebefore, cookiefile):
  list_url = getListURL(path_list_url)
  downloadChat(dir_dst, list_url, dateafter, datebefore, cookiefile)

def main():
  dateafter = "" # ダウンロード期間の最初の日付 YYYYMMDD
  datebefore = "" # ダウンロード期間の最後の日付 YYYYMMDD
  for arg in sys.argv[1:]:
    if len(arg) == 8 and arg.isdecimal():
      if dateafter == "":
        dateafter = arg
      elif datebefore == "":
        datebefore = arg
  if dateafter == "":
    dateafter = "00010101"
  if datebefore == "":
    datebefore = "99991231"
  execute("live_chat/", "extract/list_url.txt", dateafter, datebefore, os.path.dirname(__file__) + "/auth/cookies.txt")

if __name__ == "__main__":
  main()
