import os # path.isfile
import csv # reader
import numpy # array, argmin, abs
from moviepy.editor import *
from moviepy.video.fx.resize import resize

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
  second_src = int(second_src)
  second = second_src % SECOND_PER_MINUTE
  second_src = int((second_src - second) / SECOND_PER_MINUTE)
  minute = second_src % MINUTE_PER_HOUR
  second_src = int((second_src - minute) / MINUTE_PER_HOUR)
  hour = second_src
  return str(hour) + ":" + str(minute).zfill(2) + ":" + str(second).zfill(2)

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
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット数, [n][5]: コメント数, [n][6]: 金額, [n][7]: タイトル
  dict_count_comment = {}
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if len(row) <= 0:
        continue
      is_comment = row[4] == "0:00:00" # 終了時刻が0ならコメントと判定
      id = subStrBegin(row[0], "youtu.be/", "?")
      if is_comment:
        dict_count_comment[id] = int(row[1])
      if row[0][:4] != "http": # 行頭に変更がなければ除外
        count_chat = 0
        if not is_comment:
          count_chat = int(row[1])
        date = row[5]
        title = ""
        if id in dict_date_title:
          date = dict_date_title[id][0]
          title = dict_date_title[id][1]
        results.append([id, date, timeToSecond(row[3]), timeToSecond(row[4]), count_chat, 0, int(row[2]), title])
  for result in results: # コメント数をすべてに反映
    if result[0] in dict_count_comment:
      result[5] = dict_count_comment[result[0]]
  return results

def displayText(date, count_chat, count_comment, yen): # 切り抜き動画中に表示する文字
  DISPLAY_DATE = True # 投稿日の表示オプション
  DISPLAY_COUNT = True # 該当チャット数の表示オプション
  DISPLAY_YEN = True # スーパーチャット金額(円)の表示オプション
  NEWLINE = "\n" # 改行文字
  display_text = ""
  if DISPLAY_DATE:
    display_text += date[:4] + "/" + date[4:6] + "/" + date[6:] + NEWLINE
  if DISPLAY_COUNT and count_chat > 0:
    display_text += "関連チャット数: " + str(count_chat) + NEWLINE
  if DISPLAY_COUNT and count_comment > 0:
    display_text += "関連コメント数: " + str(count_comment) + NEWLINE
  if DISPLAY_YEN and yen > 0:
    display_text += "スパチャ総額: ¥" + str(yen) + NEWLINE
  if len(display_text) > 0:
    display_text = display_text[:- len(NEWLINE)]
  return display_text

def getResolution(results, dir): # 全切り抜きのうち、該当数が最も多い解像度を取得
  LIST_HEIGHT_16_9 = [144, 360, 480, 720, 1080, 1440, 2160, 4320] # 一般的な16:9の解像度(の高さ)一覧
  list_count = [0] * len(LIST_HEIGHT_16_9)
  list_resolution = []
  for (id, date, sec_begin, sec_end, _, _, _, _) in results:
    str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
    str_sec_end = str(int(sec_end * 1000)).zfill(8)
    path = dir + date + "[" + id + "]_" + str_sec_begin + "-" + str_sec_end + ".mp4"
    video = VideoFileClip(path)
    index_nearest = numpy.argmin(numpy.abs(numpy.array(LIST_HEIGHT_16_9) - video.h))
    list_count[index_nearest] += 1
    list_resolution.append((video.h, video.w))
  height = LIST_HEIGHT_16_9[list_count.index(max(list_count))]
  width = int(height * 16 / 9)
  list_target_resolution = []
  for (height_original, width_original) in list_resolution:
    height_target = height_original
    width_target = width_original
    if height_target > height or width_target > width or (height_target != height and width_target != width): # 共通解像度に一致するようサイズ変更
      height_target = min(height, int(width * height_original / width_original))
      width_target = min(width, int(height * width_original / height_original))
    list_target_resolution.append((height_target, width_target))
  return (width, height), list_target_resolution # sizeは(x, y), target_resolutionは(y, x)。不満はmoviepy開発陣へ

def subClip(resolution, target_resolution, title, text, path, path_font=""): # 各切り抜きのサイズを合わせ、文字とフェード効果を付与
  SEC_FADEIN = 1 # フェードイン秒数
  SEC_FADEOUT = 1 # フェードアウト秒数
  SEC_AUDIO_FADEIN = 0.1 # 音のフェードイン秒数
  SEC_AUDIO_FADEOUT = 0.1 # 音のフェードアウト秒数
  COLOR_FONT = "#ffffff" # フォント色
  COLOR_BACKGROUND = "#000000c0" # テキストの背景色
  (width, height) = resolution
  (height_target, width_target) = target_resolution
  videoclip = VideoFileClip(path, target_resolution=target_resolution).set_position((int((width - width_target) / 2), int((height - height_target) / 2))) # 指定の解像度で動画読み込み
  fontsize = int(height / 20)
  titlesize = int(fontsize / 2)
  position_title = (16, 8)
  position_text = (16, 16 + titlesize + 1)
  duration = videoclip.duration
  if path_font == "":
    titleclip = TextClip(txt=title, fontsize=titlesize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND).set_position(position_title).set_duration(duration)
    textclip = TextClip(txt=text, fontsize=fontsize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND).set_position(position_text).set_duration(duration)
  else:
    titleclip = TextClip(txt=title, font=path_font, fontsize=titlesize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND).set_position(position_title).set_duration(duration)
    textclip = TextClip(txt=text, font=path_font, fontsize=fontsize, color=COLOR_FONT, bg_color=COLOR_BACKGROUND).set_position(position_text).set_duration(duration)
  return CompositeVideoClip(clips=[videoclip, titleclip, textclip], size=resolution).fadein(SEC_FADEIN).fadeout(SEC_FADEOUT).audio_fadein(SEC_AUDIO_FADEIN).audio_fadeout(SEC_AUDIO_FADEOUT)

def mergeClip(results, dir, path_font): # 全切り抜きを結合
  list_video = []
  resolution, list_target_resolution = getResolution(results, dir)
  len_results = len(results)
  for i in range(len_results):
    (id, date, sec_begin, sec_end, count_chat, count_comment, yen, title) = results[i]
    str_sec_begin = str(int(sec_begin * 1000)).zfill(8)
    str_sec_end = str(int(sec_end * 1000)).zfill(8)
    path = dir + date + "[" + id + "]_" + str_sec_begin + "-" + str_sec_end + ".mp4"
    text = displayText(date, count_chat, count_comment, yen)
    list_video.append(subClip(resolution, list_target_resolution[i], title, text, path, path_font))
    id_next = ""
    if i < len_results - 1:
      id_next = results[i + 1][0]
  return concatenate_videoclips(list_video)

def generateTimestamp(results): # タイムスタンプ用の文字列を生成 各切り抜きの開始時刻、投稿日、URL
  NEWLINE = "\n" # 改行文字
  timestamp = ""
  len_results = len(results)
  sec_sum = 0
  for i in range(len_results):
    (id, date, sec_begin, sec_end, _, _, _, _) = results[i]
    url = "https://youtu.be/" + id + "?t=" + str(int(sec_begin)) + "s"
    timestamp += secondToTime(sec_sum) + " " + str(i + 1) + ". " + date[:4] + "/" + date[4:6] + "/" + date[6:] + " "
    timestamp += url + NEWLINE
    sec_sum += sec_end - sec_begin
  return timestamp

def execute(path_results, path_list_date_title, dir_video, path_dst_video, path_dst_timestamp, path_font=""):
  dict_date_title = getDictDateTitle(path_list_date_title)
  results = getResults(path_results, dict_date_title)
  video = mergeClip(results, dir_video, path_font)
  video.write_videofile(path_dst_video, codec="mpeg4", bitrate="1000000000")
  timestamp = generateTimestamp(results)
  with open(path_dst_timestamp, "w") as f:
    f.write(timestamp)

def main():
  execute("../extract/results.txt", "../extract/list_date_title.txt", "../clip/", "clip.mp4", "timestamp.txt", "../../../src/font/MPLUSRounded1c-Regular.ttf")

if __name__ == "__main__":
  main()
