import os # remove, path.isfile
import csv # reader
import yt_dlp # YoutubeDL
from moviepy.editor import *

def subStrBegin(str, str_begin, str_end): # 該当範囲の文字列を切り出し(開始文字列から検索)
  begin = str.find(str_begin) + len(str_begin)
  if begin < len(str_begin):
    return ""
  end = str[begin:].find(str_end) + begin
  return str[begin:end]

def timeToSecond(str): # 時間表示(str)から秒数(int)に変換
  SECOND_PER_MINUTE = 60
  MINUTE_PER_HOUR = 60
  DELIMITER = ":" # 時間表示の区切り文字
  index_delimiter = str.find(DELIMITER)
  hour = int(str[:index_delimiter])
  str = str[index_delimiter + len(DELIMITER):]
  index_delimiter = str.find(DELIMITER)
  minute = int(str[:index_delimiter])
  str = str[index_delimiter + len(DELIMITER):]
  second = int(str)
  return (hour * MINUTE_PER_HOUR + minute) * SECOND_PER_MINUTE + second

def getResults(path): # ファイルから結果を取得
  DELIMITER = " " # 区切り文字
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: URL
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if row[0][:4] != "http": # 行頭に変更がなければ除外
        results.append((subStrBegin(row[0], "=", "&"), row[4], timeToSecond(row[2]), timeToSecond(row[3]), row[0][row[0].find("http"):row[0].find("&")]))
  return results

def downloadClip(results): # 各動画のダウンロードと切り抜き
  REMOVE_ORIGINAL = False # ダウンロードした元動画を削除するか
  OPTION = {"outtmpl": "%(upload_date)s[%(id)s].%(ext)s"}
  len_results = len(results)
  with yt_dlp.YoutubeDL(OPTION) as ydl:
    count_same_id = 0
    for i in range(len_results):
      (id, date, sec_begin, sec_end, url) = results[i]
      filename = date + "[" + id + "]"
      path_download = filename + ".mp4"
      path_clip = filename + "_clip" + str(count_same_id) + ".mp4"
      if not os.path.isfile(path_clip): # 出力先ファイルが既に存在する場合は動画生成しない
        if not os.path.isfile(path_download): # 存在しない場合のみダウンロード
          ydl.download([url])
        videoclip = VideoFileClip(path_download).subclip(sec_begin, sec_end)
        videoclip.write_videofile(path_clip, codec="mpeg4", bitrate="1000000000")
      count_same_id += 1
      id_next = ""
      if i < len_results - 1:
        id_next = results[i + 1][0]
      if (id != id_next):
        count_same_id = 0
        if REMOVE_ORIGINAL: # 用済みになった動画は、オプションがTrueなら削除
          os.remove(path_download)

def execute(path):
  results = getResults(path)
  downloadClip(results)

def main():
  execute("../extract/results.txt")

if __name__ == "__main__":
  main()
