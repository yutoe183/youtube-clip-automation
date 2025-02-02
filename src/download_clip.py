import sys # argv
import os # remove, path.isfile, path.dirname
import operator # itemgetter
import csv # reader
import glob # glob, escape
import yt_dlp # YoutubeDL
from moviepy import *

#from moviepy.config import change_settings
#change_settings({"FFMPEG_BINARY":"ffmpeg"}) # moviepyでnvencを呼び出せない問題の対応

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

def secondToTime(second_src): # 秒数(float)から時間表示(str)に変換
  SECOND_PER_MINUTE = 60
  MINUTE_PER_HOUR = 60
  second_src = round(second_src) # 小数点以下は四捨五入
  second = second_src % SECOND_PER_MINUTE
  second_src = int((second_src - second) / SECOND_PER_MINUTE)
  minute = second_src % MINUTE_PER_HOUR
  second_src = int((second_src - minute) / MINUTE_PER_HOUR)
  hour = second_src
  return str(hour) + ":" + str(minute).zfill(2) + ":" + str(second).zfill(2)

def getVideoPath(filename): # 拡張子も含めた動画のパスを取得
  list_extension = ("mp4", "webm", "mkv")
  for extension in list_extension:
    path = filename + "." + extension
    if os.path.isfile(path):
      return path
  print("file not found: " + filename)
  return ""

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
  count_clip = 0
  count_memo = 0
  comment_out = False
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if len(row) > 0 and row[0] == "//":
        continue
      if len(row) > 0 and "<!--" in row[0]:
        comment_out = True
      if len(row) > 0 and "-->" in row[0]:
        comment_out = False
      if comment_out: # コメントアウト中はすべて無視
        continue
      if len(row) < 6:
        continue
      if (row[0][:4] != "http" or "," in row[3]) and "http" in row[0]: # 未編集行は除外
        id = subStrBegin(row[0], "youtu.be/", "?")
        date = row[5]
        if id in dict_date_title:
          date = dict_date_title[id][0]
        time_str = row[3] + "," # 開始時刻とカウント時刻
        sec_begin = timeToSecond(time_str[:time_str.find(",")])
        results.append((id, date, sec_begin, timeToSecond(row[4])))
        time_list = [sec_begin]
        time_str = time_str[time_str.find(",") + 1:]
        if "," in time_str:
          while len(time_str) > 1:
            time_float = float(time_str[:time_str.find(",")])
            time_hour = time_float // 10000
            time_float = time_float - time_hour * 10000
            time_minute = time_float // 100
            time_float = time_float - time_minute * 100
            time_second = time_float
            is_hour_zero = False
            is_minute_zero = False
            if time_hour == 0:
              time_hour = time_list[-1] // 3600
              is_hour_zero = True
              if time_minute == 0:
                is_minute_zero = True
                time_minute = (time_list[-1] - time_hour * 3600) // 60
            time_total_second = time_hour * 3600 + time_minute * 60 + time_second
            if time_total_second < time_list[-1]:
              if is_minute_zero:
                time_minute += 1
              elif is_hour_zero:
                time_hour += 1
              else:
                print("Incorrect time: " + date + "[" + id + "]: " + time_list)
              time_total_second = time_hour * 3600 + time_minute * 60 + time_second
            time_list.append(time_total_second)
            time_str = time_str[time_str.find(",") + 1:]
        if timeToSecond(row[4]) <= time_list[-1]:
          print("Incorrect time: " + date + "[" + id + "]")
        time_list = [a - b for a, b in zip(time_list, [sec_begin] * len(time_list))]
        head = row[0][:row[0].find("http")] # 行頭のメモ
        head_count = -1
        if head.isdecimal():
          head_count = int(head)
        count_clip += 1
        if head_count >= 0: # 行頭のメモカウント機能
          count_memo += head_count
        else:
          count_memo += len(time_list) - 1
  print("count clip: " + str(count_clip))
  if count_memo > 0:
    print("count memo: " + str(count_memo))
  return results

def printDurationFromResults(results):
  duration_sum = 0
  print("[", end="")
  for (_, _, sec_begin, sec_end) in results:
    print(secondToTime(sec_end - sec_begin), end=", ")
    duration_sum += sec_end - sec_begin
  print("]")
  print("total: " + secondToTime(duration_sum))

def downloadAllAndClip(results, dir_download, dir_clip, remove_original, cookiefile): # 各動画のダウンロードと切り抜き
  option = {
    "outtmpl": dir_download + "%(upload_date)s[%(id)s].%(ext)s", # 出力形式 投稿日[動画ID].mp4
    #"format": "(bv*[vcodec~='^((he|a)vc|h26[45])']+ba) / (bv*+ba/b)", # Download the best video with either h264 or h265 codec, or the best video if there is no such video
    #"format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b", # Download the best mp4 video available, or the best video if no mp4 available
    "ignoreerrors": True, # エラーを無視して続行
    "cookiefile": cookiefile,
  }
  MAX_RETRY_DOWNLOAD = 6 # ダウンロードに失敗した際の最大再試行回数
  results.sort(key=operator.itemgetter(1, 0, 2, 3)) # 日付順で、動画ごとにすべての切り抜きを作成
  len_results = len(results)
  with yt_dlp.YoutubeDL(option) as ydl:
    for i in range(len_results):
      (id, date, sec_begin, sec_end) = results[i]
      url = "https://www.youtube.com/watch?v=" + id
      filename = date + "[" + id + "]"
      filename_download = dir_download + filename
      path_download = ""
      str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
      str_sec_end = str(int(sec_end * 1000)).zfill(8)
      path_clip = dir_clip + filename + "_" + str_sec_begin + "-" + str_sec_end + ".mp4"
      print(str(i) + "/" + str(len(results)) + ": " + path_clip)
      if not os.path.isfile(path_clip): # 出力先ファイルが既に存在する場合は動画生成しない
        retry_download = MAX_RETRY_DOWNLOAD
        while retry_download > 0:
          path_download = getVideoPath(filename_download)
          if path_download != "": # 存在しない場合のみダウンロード
            break
          retry_download -= 1
          ydl.download([url])
        if path_download != "": # ダウンロードに失敗した場合はスキップ
          if sec_begin < sec_end: # 時刻指定に誤りがある場合はスキップ
            videoclip = VideoFileClip(path_download).subclipped(sec_begin, sec_end)
            videoclip.write_videofile(path_clip, codec="mpeg4", bitrate="1000000000")
      if remove_original and (i == len_results - 1 or id != results[i + 1][0]): # 用済みになった動画は、オプションがTrueなら削除
        if os.path.isfile(path_download):
          os.remove(path_download)

def downloadAllAudioAndClip(results, dir_download, dir_clip, remove_original, cookiefile): # すべての音声と切り抜き部分のみの映像をダウンロード
  MAX_RETRY_DOWNLOAD = 6 # ダウンロードに失敗した際の最大再試行回数
  SEC_INTERVAL_BEGIN_DOWNLOAD = 12 # 切り抜き前に指定秒数を追加した部分をダウンロード
  SEC_INTERVAL_END_DOWNLOAD = 4 # 切り抜き後に指定秒数を追加した部分をダウンロード
  SEC_INTERVAL_BEGIN_CLIP = 4 # 前に指定秒数以上が存在するダウンロード動画から切り抜きを作成
  SEC_INTERVAL_END_CLIP = 0.1 # 後に指定秒数以上が存在するダウンロード動画から切り抜きを作成
  results.sort(key=operator.itemgetter(1, 0, 2, 3)) # 日付順にダウンロード
  len_results = len(results)
  for i in range(len_results):
    (id, date, sec_begin, sec_end) = results[i]
    if sec_begin >= sec_end: # 時刻指定に誤りがある場合はスキップ
      continue
    url = "https://www.youtube.com/watch?v=" + id
    filename = date + "[" + id + "]"
    filename_download_pre = dir_download + filename
    path_download_video = ""
    path_download_audio = ""
    str_sec_begin = str(round(sec_begin * 1000)).zfill(8)
    str_sec_end = str(round(sec_end * 1000)).zfill(8)
    path_clip = dir_clip + filename + "_" + str_sec_begin + "-" + str_sec_end + ".mp4"
    print(str(i + 1) + "/" + str(len(results)) + ": " + path_clip)
    if not os.path.isfile(path_clip): # 出力先ファイルが既に存在する場合は動画生成しない
      retry_download = MAX_RETRY_DOWNLOAD
      sec_begin_download = 0
      sec_end_download = 0
      while retry_download > 0:
        for downloaded in glob.glob(glob.escape(filename_download_pre) + "*"):
          index_extension = downloaded.rfind(".")
          index_id_end = downloaded[:index_extension].rfind("]")
          if index_id_end + 1 == index_extension: # 動画が開始から終了まですべてダウンロードされている場合
            sec_begin_download = 0
            sec_end_download = 0
            path_download_video = downloaded
            path_download_audio = downloaded
            break
          elif "audio." in downloaded: # 音声が開始から終了まですべてダウンロードされている場合
            path_download_audio = downloaded
            if path_download_video != "" and path_download_audio != "":
              break
          else: # 切り抜き付近のみがダウンロードされている場合
            index_sec_end = downloaded[:index_extension].rfind("-")
            index_sec_begin = downloaded[:index_sec_end].rfind("_")
            if downloaded[index_sec_end + 1:index_extension].isdecimal(): # partファイルの場合は無視
              sec_begin_download_current = int(downloaded[index_sec_begin + 1:index_sec_end]) / 1000
              sec_end_download_current = int(downloaded[index_sec_end + 1:index_extension]) / 1000
              if (sec_begin_download_current <= sec_begin - SEC_INTERVAL_BEGIN_CLIP or sec_begin_download_current == 0) and sec_end_download_current >= sec_end + SEC_INTERVAL_END_CLIP: # 適するダウンロード動画が存在する場合
                path_download_video = downloaded
                sec_begin_download = sec_begin_download_current
                sec_end_download = sec_end_download_current
                if path_download_video != "" and path_download_audio != "":
                  break
        if path_download_video != "" and path_download_audio != "":
          break
        retry_download -= 1
        if path_download_video == "":
          sec_begin_download = round(sec_begin - SEC_INTERVAL_BEGIN_DOWNLOAD)
          if sec_begin_download < 0:
            sec_begin_download = 0
          sec_end_download = round(sec_end + SEC_INTERVAL_END_DOWNLOAD)
          str_sec_begin_download = str(round(sec_begin_download * 1000)).zfill(8)
          str_sec_end_download = str(round(sec_end_download * 1000)).zfill(8)
          filename_download = dir_download + filename + "_" + str_sec_begin_download + "-" + str_sec_end_download
          option = {
            "outtmpl": filename_download + ".%(ext)s", # 出力形式 投稿日[動画ID]_開始ミリ秒-終了ミリ秒.mp4
            #"format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b", # Download the best mp4 video available, or the best video if no mp4 available
            "ignoreerrors": True, # エラーを無視して続行
            "download_ranges": lambda info_dict, ydl: [{"start_time": sec_begin_download, "end_time": sec_end_download}],
            "cookiefile": cookiefile
          }
          with yt_dlp.YoutubeDL(option) as ydl:
            ydl.download([url])
        if path_download_audio == "":
          filename_download = dir_download + filename + "audio"
          option = {
            "outtmpl": filename_download + ".%(ext)s", # 出力形式 投稿日[動画ID]_開始ミリ秒-終了ミリ秒.mp4
            "format": "ba", # 音声のみ
            "ignoreerrors": True, # エラーを無視して続行
            "cookiefile": cookiefile
          }
          with yt_dlp.YoutubeDL(option) as ydl:
            ydl.download([url])
      if path_download_video != "" and path_download_audio != "":
        videoclip = VideoFileClip(path_download_video) # ダウンロードの開始終了秒数をyt-dlpが厳守しない(少し長めになる)ので、切り抜き位置を調整する。現在は、終了秒数が一致している想定で調整している
        audioclip = AudioFileClip(path_download_audio).subclipped(sec_begin, sec_end)
        if sec_end_download <= 0:
          sec_end_download = videoclip.duration
        sec_begin_clip = videoclip.duration - sec_end_download + sec_begin # = videoclip.duration - (sec_end_download - sec_begin_download) + (sec_begin - sec_begin_download)
        sec_end_clip = videoclip.duration - sec_end_download + sec_end
        subclip = videoclip.subclipped(sec_begin_clip, sec_end_clip).with_audio(audioclip) # 映像と音声を結合
        subclip.write_videofile(path_clip, codec="mpeg4", bitrate="1000000000")
    if remove_original and (i == len_results - 1 or id != results[i + 1][0]): # 用済みになった動画は、オプションがTrueなら削除
      for downloaded in glob.glob(glob.escape(filename_download_pre) + "*"):
        os.remove(downloaded)

def downloadOnlyClip(results, dir_download, dir_clip, remove_original, cookiefile): # 切り抜き部分のみをダウンロード (ToDo: 現在は音声ずれが確率的に発生するため使用しない)
  MAX_RETRY_DOWNLOAD = 6 # ダウンロードに失敗した際の最大再試行回数
  SEC_INTERVAL_BEGIN_DOWNLOAD = 2 # 切り抜き前に指定秒数を追加した部分をダウンロード
  SEC_INTERVAL_END_DOWNLOAD = 2 # 切り抜き後に指定秒数を追加した部分をダウンロード
  SEC_INTERVAL_BEGIN_CLIP = 0 # 前に指定秒数以上が存在するダウンロード動画から切り抜きを作成
  SEC_INTERVAL_END_CLIP = 0 # 後に指定秒数以上が存在するダウンロード動画から切り抜きを作成
  results.sort(key=operator.itemgetter(1, 0, 2, 3)) # 日付順にダウンロード
  len_results = len(results)
  for i in range(len_results):
    (id, date, sec_begin, sec_end) = results[i]
    if sec_begin >= sec_end: # 時刻指定に誤りがある場合はスキップ
      continue
    url = "https://www.youtube.com/watch?v=" + id
    filename = date + "[" + id + "]"
    filename_download_pre = dir_download + filename
    path_download = ""
    str_sec_begin = str(round(sec_begin * 1000)).zfill(8)
    str_sec_end = str(round(sec_end * 1000)).zfill(8)
    path_clip = dir_clip + filename + "_" + str_sec_begin + "-" + str_sec_end + ".mp4"
    print(str(i) + "/" + str(len(results)) + ": " + path_clip)
    if not os.path.isfile(path_clip): # 出力先ファイルが既に存在する場合は動画生成しない
      retry_download = MAX_RETRY_DOWNLOAD
      sec_begin_download = 0
      sec_end_download = 0
      while retry_download > 0:
        for downloaded in glob.glob(glob.escape(filename_download_pre) + "*"):
          index_extension = downloaded.rfind(".")
          index_id_end = downloaded[:index_extension].rfind("]")
          if index_id_end + 1 == index_extension: # 動画が開始から終了まですべてダウンロードされている場合
            sec_begin_download = 0
            sec_end_download = 0
            path_download = downloaded
            break
          else: # 切り抜き付近のみがダウンロードされている場合
            index_sec_end = downloaded[:index_extension].rfind("-")
            index_sec_begin = downloaded[:index_sec_end].rfind("_")
            if downloaded[index_sec_end + 1:index_extension].isdecimal(): # partファイルの場合は無視
              sec_begin_download = int(downloaded[index_sec_begin + 1:index_sec_end]) / 1000
              sec_end_download = int(downloaded[index_sec_end + 1:index_extension]) / 1000
              if (sec_begin_download <= sec_begin - SEC_INTERVAL_BEGIN_CLIP or sec_begin_download == 0) and sec_end_download >= sec_end + SEC_INTERVAL_END_CLIP: # 適するダウンロード動画が存在する場合
                path_download = downloaded
                break
        if path_download != "":
          break
        sec_begin_download = round(sec_begin - SEC_INTERVAL_BEGIN_DOWNLOAD)
        if sec_begin_download < 0:
          sec_begin_download = 0
        sec_end_download = round(sec_end + SEC_INTERVAL_END_DOWNLOAD)
        str_sec_begin_download = str(round(sec_begin_download * 1000)).zfill(8)
        str_sec_end_download = str(round(sec_end_download * 1000)).zfill(8)
        filename_download = dir_download + filename + "_" + str_sec_begin_download + "-" + str_sec_end_download
        retry_download -= 1
        option = {
          "outtmpl": filename_download + ".%(ext)s", # 出力形式 投稿日[動画ID]_開始ミリ秒-終了ミリ秒.mp4
          #"format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b", # Download the best mp4 video available, or the best video if no mp4 available
          "ignoreerrors": True, # エラーを無視して続行
          "download_ranges": lambda info_dict, ydl: [{"start_time": sec_begin_download, "end_time": sec_end_download}],
          "cookiefile": cookiefile
        }
        with yt_dlp.YoutubeDL(option) as ydl:
          ydl.download([url])
      if path_download != "":
        videoclip = VideoFileClip(path_download) # ダウンロードの開始終了秒数をyt-dlpが厳守しない(少し長めになる)ので、切り抜き位置を調整する。現在は、終了秒数が一致している想定で調整している
        print(videoclip.duration, videoclip.audio.duration)
        if sec_end_download <= 0:
          sec_end_download = videoclip.duration
        sec_begin_clip = videoclip.duration - sec_end_download + sec_begin # = videoclip.duration - (sec_end_download - sec_begin_download) + (sec_begin - sec_begin_download)
        sec_end_clip = videoclip.duration - sec_end_download + sec_end
        subclip = videoclip.subclipped(sec_begin_clip, sec_end_clip)
        subclip.write_videofile(path_clip, codec="mpeg4", audio_codec="libvorbis", bitrate="1000000000")
    if remove_original and (i == len_results - 1 or id != results[i + 1][0]): # 用済みになった動画は、オプションがTrueなら削除
      for downloaded in glob.glob(glob.escape(filename_download_pre) + "*"):
        os.remove(downloaded)

def execute(path_results, path_list_date_title, dir_download, dir_clip, download_all, remove_original, cookiefile):
  dict_date_title = getDictDateTitle(path_list_date_title)
  results = getResults(path_results, dict_date_title)
  printDurationFromResults(results)
  if download_all:
    downloadAllAndClip(results, dir_download, dir_clip, remove_original, cookiefile)
  else:
    downloadAllAudioAndClip(results, dir_download, dir_clip, remove_original, cookiefile)

def main():
  download_all = False # 全編をダウンロードするか
  remove_original = False # ダウンロードした元動画を削除するか
  for arg in sys.argv[1:]:
    download_all = download_all or (arg == "-a" or arg == "-A" or arg == "--all")
    remove_original = remove_original or (arg == "-d" or arg == "-D" or arg == "--delete")
  execute("extract/results.txt", "extract/list_date_title.txt", "download/", "clip/", download_all, remove_original, os.path.dirname(__file__) + "/auth/cookies.txt")

if __name__ == "__main__":
  main()
