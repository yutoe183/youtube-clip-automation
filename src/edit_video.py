import sys # argv
import os # remove, rename, path.isfile, path.dirname
import gc # collect
import csv # reader
import glob # glob, escape
import numpy # array, argmin, abs
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
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット数, [n][5]: コメント数, [n][6]: 金額, [n][7]: タイトル, [n][8]: 公開日(表示用文字列), [n][9]: カウンター関連情報, [n][10]: カテゴリ
  dict_count_comment = {}
  count_clip = 0
  count_memo = 0
  count_begin = 0 # 各切り抜きのカウンター開始値
  display_counter = False
  counter_title = ""
  comment_out = False
  category = ""
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
      if len(row) > 0 and "<counter" in row[0]:
        display_counter = True
        set_count_begin = subStrBegin(row[0], "<counter=", ">")
        if set_count_begin.isdecimal():
          count_begin = int(set_count_begin)
      elif len(row) > 0 and "</counter>" in row[0]:
        display_counter = False
      if len(row) > 0 and "<category" in row[0]:
        category = subStrBegin(row[0], "<category=", ">")
        if len(category) > 0 and category[-1] == "/":
          category = category[:-1]
        counter_title = category
      if len(row) < 6:
        continue
      is_comment = row[4] == "0:00:00" # 終了時刻が0ならコメントと判定
      id = subStrBegin(row[0], "youtu.be/", "?")
      if is_comment:
        dict_count_comment[id] = int(row[1])
      if (row[0][:4] != "http" or "," in row[3]) and "http" in row[0]: # 未編集行は除外
        count_chat = 0
        if not is_comment:
          count_chat = int(row[1])
        date = row[5]
        title = ""
        if id in dict_date_title:
          date = dict_date_title[id][0]
          title = dict_date_title[id][1]
        time_str = row[3] + "," # 開始時刻とカウント時刻
        sec_begin = timeToSecond(time_str[:time_str.find(",")])
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
        results.append([id, date, sec_begin, timeToSecond(row[4]), count_chat, 0, int(row[2]), title, row[5], (display_counter, count_begin, head_count, time_list, counter_title), category])
        count_clip += 1
        if head_count >= 0: # 行頭のメモカウント機能
          count_memo += head_count
          count_begin += head_count
        else:
          count_memo += len(time_list) - 1
          count_begin += len(time_list) - 1
  print("count clip: " + str(count_clip))
  if count_memo > 0:
    print("count memo: " + str(count_memo))
  for result in results: # コメント数をすべてに反映
    if result[0] in dict_count_comment:
      result[5] = dict_count_comment[result[0]]
  return results

def getResolution(results, dir): # 全切り抜きのうち、該当数が最も多い解像度を取得
  LIST_HEIGHT_16_9 = [144, 360, 480, 720, 1080, 1440, 2160, 4320] # 一般的な16:9の解像度(の高さ)一覧
  list_count = [0] * len(LIST_HEIGHT_16_9)
  list_resolution = []
  list_duration = []
  list_max_volume = []
  id_current = ""
  count_same_id = 0
  for (id, date, sec_begin, sec_end, _, _, _, _, _, _, _) in results:
    str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
    str_sec_end = str(int(sec_end * 1000)).zfill(8)
    path = getVideoPath(dir + date + "[" + id + "]_" + str_sec_begin + "-" + str_sec_end) # glob.glob(glob.escape(dir) + "*" + glob.escape("[" + id + "]_" + str_sec_begin + "-" + str_sec_end) + "*")[0]
    video = VideoFileClip(path)
    index_nearest = numpy.argmin(numpy.abs(numpy.array(LIST_HEIGHT_16_9) - video.h))
    list_count[index_nearest] += 1
    list_resolution.append((video.w, video.h))
    list_duration.append(video.duration)
    list_max_volume.append(video.audio.max_volume())
    if id == id_current:
      count_same_id += 1
      if list_max_volume[-1] < list_max_volume[-2]:
        list_max_volume[-1] = list_max_volume[-2]
      else:
        for i in range(- count_same_id, -1):
          list_max_volume[i] = list_max_volume[-1]
    else:
      id_current = id
      count_same_id = 1
  height = LIST_HEIGHT_16_9[list_count.index(max(list_count))]
  width = int(height * 16 / 9)
  list_target_resolution = []
  for (width_original, height_original) in list_resolution:
    height_target = height_original
    width_target = width_original
    if height_target > height or width_target > width or (height_target != height and width_target != width): # 共通解像度に一致するようサイズ変更
      height_target = min(height, int(width * height_original / width_original))
      width_target = min(width, int(height * width_original / height_original))
    list_target_resolution.append((width_target, height_target))
  return (width, height), list_target_resolution, list_duration, list_max_volume # MoviePy v1.Xまで、sizeは(x, y), target_resolutionは(y, x)だったが、v2.Xから(x, y)に統一

def generateTimestamp(results, list_duration): # タイムスタンプ用の文字列を生成 各切り抜きの開始時刻、投稿日、URL
  NEWLINE = "\n" # 改行文字
  SEC_CLUSTERING = 60 * 12 # 間隔が指定秒未満の場合、同じ事象に対する切り抜きだと判定。その場合、それらのタイムスタンプのカウントを同じにする (例: 1. 2-1. 2-2. 3. 4. ...)
  timestamp = ""
  timestamp1 = ""
  timestamp_day = ""
  timestamp_month = ""
  timestamp_year = ""
  sec_sum = 0
  count_num = 0
  count_sequence = 0
  current_id = ""
  current_sec_end = 0
  current_category = ""
  current_day = "0000/00/00"
  current_month = "0000/00"
  current_year = "0000"
  for i in range(len(results)):
    (id, date, sec_begin, sec_end, _, _, _, _, release_date, _, category) = results[i]
    release_date = release_date.replace("\\n", " ").replace("\\s", " ") # 特殊文字を除去
    url = "https://youtu.be/" + id + "?t=" + str(int(sec_begin)) + "s"
    if category != current_category:
      current_category = category
      count_num = 0
      current_id = ""
    if id == current_id and sec_begin < current_sec_end + SEC_CLUSTERING:
      count_sequence += 1
      timestamp += secondToTime(sec_sum) + " " + category + str(count_num) + "-" + str(count_sequence) + ". " + release_date + " "
    else:
      count_num += 1
      count_sequence = 1
      current_id = id
      timestamp += secondToTime(sec_sum) + " " + category + str(count_num) + ". " + release_date + " "
      timestamp1 += secondToTime(sec_sum) + " " + category + str(count_num) + ". " + release_date + " "
      timestamp1 += url + NEWLINE
      if release_date != current_day:
        current_day = release_date
        timestamp_day += secondToTime(sec_sum) + " " + category + str(count_num) + ". " + current_day + " "
        timestamp_day += url + NEWLINE
        if release_date[:7] != current_month:
          current_month = release_date[:7]
          timestamp_month += secondToTime(sec_sum) + " " + category + str(count_num) + ". " + current_month + " "
          timestamp_month += url + NEWLINE
          if release_date[:4] != current_year:
            current_year = release_date[:4]
            timestamp_year += secondToTime(sec_sum) + " " + category + str(count_num) + ". " + current_year + " "
            timestamp_year += url + NEWLINE
    current_sec_end = sec_end
    timestamp += url + NEWLINE
    sec_sum += list_duration[i] # 実際の動画の duration と sec_end - sec_begin では誤差(前者が最大+0.05s程度)が発生し、累積すると数秒単位の誤差になってしまう。これを防ぐため、実際の動画の duration を使う
  return timestamp, timestamp1, timestamp_day, timestamp_month, timestamp_year

def writeTimestamp(results, list_duration, path_dst_timestamp): # タイムスタンプをファイル出力
  timestamp, timestamp1, timestamp_day, timestamp_month, timestamp_year = generateTimestamp(results, list_duration)
  with open(path_dst_timestamp, "w") as f:
    f.write(timestamp)
  with open(path_dst_timestamp[:path_dst_timestamp.rfind(".")] + "1" + path_dst_timestamp[path_dst_timestamp.rfind("."):], "w") as f:
    f.write(timestamp1)
  with open(path_dst_timestamp[:path_dst_timestamp.rfind(".")] + "_day" + path_dst_timestamp[path_dst_timestamp.rfind("."):], "w") as f:
    f.write(timestamp_day)
  with open(path_dst_timestamp[:path_dst_timestamp.rfind(".")] + "_month" + path_dst_timestamp[path_dst_timestamp.rfind("."):], "w") as f:
    f.write(timestamp_month)
  with open(path_dst_timestamp[:path_dst_timestamp.rfind(".")] + "_year" + path_dst_timestamp[path_dst_timestamp.rfind("."):], "w") as f:
    f.write(timestamp_year)

def displayText(release_date, count_chat, count_comment, yen): # 切り抜き動画中に表示する文字
  DISPLAY_DATE = True # 公開日の表示オプション
  DISPLAY_COUNT = True # 該当チャット数の表示オプション
  DISPLAY_YEN = True # スーパーチャット金額(円)の表示オプション
  JP_CHATS = "関連チャット数: "
  JP_COMMENTS = "関連コメント数: "
  JP_TIPPING = "スパチャ総額: ¥"
  EN_CHATS = "Chats: "
  EN_COMMENTS = "Comments: "
  EN_TIPPING = "Tipping: ¥"
  NEWLINE = "\n" # 改行文字
  display_date = ""
  if DISPLAY_DATE:
    display_date += release_date.replace("\\n", "\n").replace("\\s", " ") # 改行を\nで、空白を\sで表現可能にする
  display_text = ""
  if DISPLAY_COUNT and count_chat > 0:
    display_text += JP_CHATS + str(count_chat) + NEWLINE
  if DISPLAY_COUNT and count_comment > 0:
    display_text += JP_COMMENTS + str(count_comment) + NEWLINE
  if DISPLAY_YEN and yen > 0:
    display_text += JP_TIPPING + str(yen) + NEWLINE
  if len(display_text) > 0:
    display_text = display_text[:- len(NEWLINE)]
  return display_date, display_text

def subClip(resolution, target_resolution, max_volume, title, display_date, display_text, counter, path, path_font="Courier"): # 各切り抜きのサイズを合わせ、文字とフェード効果を付与
  SEC_FADEIN = 0.75 # フェードイン秒数
  SEC_FADEOUT = 0.75 # フェードアウト秒数
  SEC_AUDIO_FADEIN = 0.1 # 音のフェードイン秒数
  SEC_AUDIO_FADEOUT = 0.1 # 音のフェードアウト秒数
  COLOR_FONT = "#ffffff" # フォント色
  COLOR_BACKGROUND = "#000000c0" # テキストの背景色
  TEXT_MARGIN = (12, 12, 12, 12) # テキストの周りの余白 (left, top, right, bottom)
  TEXT_X = 16 # テキストの左端座標(= 右端座標)
  TEXT_Y = 8 # テキストの上端座標
  (width, height) = resolution
  (width_target, height_target) = target_resolution
  videoclip = VideoFileClip(path, target_resolution=target_resolution).with_position((int((width - width_target) / 2), int((height - height_target) / 2))) # 指定の解像度で動画読み込み
  fontsize = int(height / 15)
  titlesize = int(fontsize * 3 / 8)
  textsize = int(fontsize * 3 / 4)
  countersize = int(fontsize * 3 / 2)
  duration = videoclip.duration
  if max_volume == 0:
    max_volume = 1
  list_clip = [videoclip.with_audio(videoclip.audio.subclipped(0, -0.05)).with_effects([afx.MultiplyVolume(1 / max_volume), afx.AudioFadeIn(SEC_AUDIO_FADEIN), afx.AudioFadeOut(SEC_AUDIO_FADEOUT)])] # 動画末尾の音声ノイズ対策(0, -0.05), 音量正規化(1 / max_volume)
  current_x = TEXT_X
  current_y = TEXT_Y
  if len(title) > 0:
    titleclip = TextClip(text=title, font=path_font, font_size=titlesize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND, margin=TEXT_MARGIN).with_position((current_x, current_y)).with_duration(duration)
    current_y += titleclip.h
    list_clip.append(titleclip)
  if len(display_date) > 0:
    dateclip = TextClip(text=display_date, font=path_font, font_size=fontsize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND, margin=TEXT_MARGIN, text_align="center").with_position((current_x, current_y)).with_duration(duration)
    current_y += dateclip.h
    list_clip.append(dateclip)
  if len(display_text) > 0:
    textclip = TextClip(text=display_text, font=path_font, font_size=textsize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND, margin=TEXT_MARGIN, text_align="left").with_position((current_x, current_y)).with_duration(duration)
    current_y += textclip.h
    list_clip.append(textclip)
  current_x = width - TEXT_X
  current_y = TEXT_Y
  (display_counter, count_begin, _, time_list, counter_title) = counter
  if counter_title != "":
    counterheadclip = TextClip(text=counter_title, font=path_font, font_size=fontsize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND, margin=TEXT_MARGIN).with_duration(duration)
    counterheadclip = counterheadclip.with_position((current_x - counterheadclip.w, current_y))
    current_y += counterheadclip.h
    list_clip.append(counterheadclip)
  if display_counter:
    time_list.append(duration)
    count_current = count_begin
    for i in range(len(time_list) - 1):
      counterbodyclip = TextClip(text=(str(count_current)), font=path_font, font_size=countersize, size=(None, countersize), color=COLOR_FONT, bg_color=COLOR_BACKGROUND, margin=TEXT_MARGIN).with_duration(time_list[i + 1] - time_list[i]).with_start(time_list[i]) # .with_end(time_list[i + 1])
      counterbodyclip = counterbodyclip.with_position((current_x - counterbodyclip.w, current_y))
      list_clip.append(counterbodyclip)
      count_current += 1
  return CompositeVideoClip(clips=list_clip, size=resolution).with_effects([vfx.FadeIn(SEC_FADEIN), vfx.FadeOut(SEC_FADEOUT)])

def mergeClip(results, resolution, list_target_resolution, list_max_volume, dir, path_dst_video, remove_original, path_font): # 全切り抜きを結合
  SEC_PER_PART = 60 * 30 # まとめて処理できる最大秒数。この秒数ごとの動画を生成し、最後に結合する
  COUNT_PER_PART = 48 # まとめて処理できる最大動画数。この個数ごとの動画を生成し、最後に結合する
  list_video = []
  path_dst_video_pre = path_dst_video[:path_dst_video.rfind(".")] # 拡張子より前
  path_dst_video_extension = path_dst_video[path_dst_video.rfind("."):]
  part_current = 0
  duration_current = 0
  duration_sum = 0
  count_current = 0
  list_video_current = []
  gc.collect()
  for i in range(len(results)):
    (id, date, sec_begin, sec_end, count_chat, count_comment, yen, title, release_date, counter, _) = results[i]
    str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
    str_sec_end = str(int(sec_end * 1000)).zfill(8)
    path = getVideoPath(dir + date + "[" + id + "]_" + str_sec_begin + "-" + str_sec_end) # glob.glob(glob.escape(dir) + "*" + glob.escape("[" + id + "]_" + str_sec_begin + "-" + str_sec_end) + "*")[0]
    display_date, display_text = displayText(release_date, count_chat, count_comment, yen)
    list_video.append(subClip(resolution, list_target_resolution[i], list_max_volume[i], title, display_date, display_text, counter, path, path_font))
    duration_current += list_video[-1].duration
    count_current += 1
    if duration_current >= SEC_PER_PART or count_current >= COUNT_PER_PART or i == len(results) - 1: # まとめて処理できる許容量を超えた場合、現在のリスト内の動画をすべて結合して出力
      print(secondToTime(duration_sum) + " -> " + secondToTime(duration_sum + duration_current))
      print("[", end="")
      for video in list_video:
        print(secondToTime(video.duration), end=", ")
      print("]")
      path_current = path_dst_video_pre + "_part" + str(part_current) + path_dst_video_extension
      if part_current >= 0: # ToDo: 変更を含むpartファイルのみ作成し直す。現状は、すべてのpartファイルが作成し直される
        concatenate_videoclips(list_video).write_videofile(path_current, codec="mpeg4", bitrate="1000000000")
      list_video.clear()
      part_current += 1
      duration_sum += duration_current
      duration_current = 0
      count_current = 0
      gc.collect() # 各動画出力ごとにメモリ解放を明示的に指定
  if part_current == 1: # 許容量に到達しなかった場合は結合処理が不要
    os.rename(path_dst_video_pre + "_part0" + path_dst_video_extension, path_dst_video)
  else:
    list_part = []
    for i in range(part_current):
      path_current = path_dst_video_pre + "_part" + str(i) + path_dst_video_extension
      videoclip = VideoFileClip(path_current)
      list_part.append(videoclip.with_audio(videoclip.audio.subclipped(0, -0.1)).with_effects([afx.AudioFadeIn(0.1), afx.AudioFadeOut(0.1)])) # 動画末尾の音声ノイズ対策(0, -0.1) 0.05では消えなかったので0.1とした
    concatenate_videoclips(list_part).write_videofile(path_dst_video, codec="mpeg4", bitrate="1000000000") # ToDo: codec="h264_nvenc", hevc_nvenc
    list_part.clear()
    if remove_original:
      for i in range(part_current): # 一時ファイルをすべて削除
        path_current = path_dst_video_pre + "_part" + str(i) + path_dst_video_extension
        os.remove(path_current)

def execute(path_results, path_list_date_title, dir_video, path_dst_video, path_dst_timestamp, remove_original, dir_font=""):
  path_font = ""
  if dir_font != "":
    path_font = glob.glob(glob.escape(dir_font) + "*")[0]
  dict_date_title = getDictDateTitle(path_list_date_title)
  results = getResults(path_results, dict_date_title)
  resolution, list_target_resolution, list_duration, list_max_volume = getResolution(results, dir_video)
  print("total: " + secondToTime(sum(list_duration)))
  print("resolution: " + str(resolution))
  writeTimestamp(results, list_duration, path_dst_timestamp)
  print("timestamp: " + path_dst_timestamp)
  mergeClip(results, resolution, list_target_resolution, list_max_volume, dir_video, path_dst_video, remove_original, path_font)
  print("video: " + path_dst_video)

def main():
  remove_original = False # 生成過程の動画を削除するか
  for arg in sys.argv[1:]:
    remove_original = remove_original or (arg == "-d" or arg == "-D" or arg == "--delete")
  execute("extract/results.txt", "extract/list_date_title.txt", "clip/", "dst/clip.mp4", "dst/timestamp.txt", remove_original, os.path.dirname(__file__) + "/font/")

if __name__ == "__main__":
  main()
