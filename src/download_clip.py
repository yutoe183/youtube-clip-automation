import sys # argv
import os # remove, path.isfile
import operator # itemgetter
import csv # reader
import yt_dlp # YoutubeDL
from moviepy.editor import *

def subStrBegin(str, str_begin, str_end): # 該当範囲の文字列を切り出し(開始文字列から検索)
  begin = str.find(str_begin) + len(str_begin)
  if begin < len(str_begin):
    return ""
  end = str[begin:].find(str_end) + begin
  return str[begin:end]

def timeToSecond(str): # 時間表示(str)から秒数(float)に変換
  SECOND_PER_MINUTE = 60
  MINUTE_PER_HOUR = 60
  DELIMITER = ":" # 時間表示の区切り文字
  index_delimiter = str.find(DELIMITER)
  hour = int(str[:index_delimiter])
  str = str[index_delimiter + len(DELIMITER):]
  index_delimiter = str.find(DELIMITER)
  minute = int(str[:index_delimiter])
  str = str[index_delimiter + len(DELIMITER):]
  second = float(str)
  return (hour * MINUTE_PER_HOUR + minute) * SECOND_PER_MINUTE + second

def getDictDateTitle(path): # ファイルから日付とタイトルの辞書を取得
  if not os.path.isfile(path):
    return {}
  dict_date_title = {}
  with open(path) as f:
    for line in f:
      dict_date_title[line[:11]] = (line[12:20], line[21:-1])
  return dict_date_title

def getResults(path, dict_date_title): # ファイルから結果を取得
  DELIMITER = " " # 区切り文字
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if len(row) <= 0:
        continue
      if row[0][:4] != "http": # 行頭に変更がなければ除外
        id = subStrBegin(row[0], "youtu.be/", "?")
        date = row[5]
        if id in dict_date_title:
          date = dict_date_title[id][0]
        results.append((id, date, timeToSecond(row[3]), timeToSecond(row[4])))
  return results

def downloadClip(results, dir_download, dir_clip, remove_original): # 各動画のダウンロードと切り抜き
  option = {
    "outtmpl": dir_download + "%(upload_date)s[%(id)s].%(ext)s", # 出力形式 投稿日[動画ID].mp4
    "ignoreerrors": True, # エラーを無視して続行
  }
  MAX_RETRY_DOWNLOAD = 6 # ダウンロードに失敗した際の最大再試行回数
  results.sort(key=operator.itemgetter(1, 2, 3)) # 並び順に関わらず、動画ごとにすべての切り抜きを作成
  len_results = len(results)
  with yt_dlp.YoutubeDL(option) as ydl:
    for i in range(len_results):
      (id, date, sec_begin, sec_end) = results[i]
      url = "https://www.youtube.com/watch?v=" + id
      filename = date + "[" + id + "]"
      path_download = dir_download + filename + ".mp4"
      str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
      str_sec_end = str(int(sec_end * 1000)).zfill(8)
      path_clip = dir_clip + filename + "_" + str_sec_begin + "-" + str_sec_end + ".mp4"
      if not os.path.isfile(path_clip): # 出力先ファイルが既に存在する場合は動画生成しない
        retry_download = MAX_RETRY_DOWNLOAD
        while not os.path.isfile(path_download) and retry_download > 0: # 存在しない場合のみダウンロード
          retry_download -= 1
          ydl.download([url])
        if os.path.isfile(path_download): # ダウンロードに失敗した場合はスキップ
          if sec_begin < sec_end: # 時刻指定に誤りがある場合はスキップ
            videoclip = VideoFileClip(path_download).subclip(sec_begin, sec_end)
            videoclip.write_videofile(path_clip, codec="mpeg4", bitrate="1000000000")
      id_next = ""
      if i < len_results - 1:
        id_next = results[i + 1][0]
      if (id != id_next):
        if remove_original: # 用済みになった動画は、オプションがTrueなら削除
          if os.path.isfile(path_download):
            os.remove(path_download)

def execute(path_results, path_list_date_title, dir_download, dir_clip, remove_original):
  dict_date_title = getDictDateTitle(path_list_date_title)
  results = getResults(path_results, dict_date_title)
  downloadClip(results, dir_download, dir_clip, remove_original)

def main():
  remove_original = len(sys.argv) > 1 and (sys.argv[1] == "-d" or sys.argv[1] == "-D") # ダウンロードした元動画を削除するか
  execute("extract/results.txt", "extract/list_date_title.txt", "download/", "clip/", remove_original)

if __name__ == "__main__":
  main()
