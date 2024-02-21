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

def secondToTime(second_src): # 秒数(int)から時間表示(str)に変換
  SECOND_PER_MINUTE = 60
  MINUTE_PER_HOUR = 60
  second = second_src % SECOND_PER_MINUTE
  second_src = int((second_src - second) / SECOND_PER_MINUTE)
  minute = second_src % MINUTE_PER_HOUR
  second_src = int((second_src - minute) / MINUTE_PER_HOUR)
  hour = second_src
  return str(hour) + ":" + str(minute).zfill(2) + ":" + str(second).zfill(2)

def getResults(path): # ファイルから結果を取得
  DELIMITER = " " # 区切り文字
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット数, [n][5]: 金額, [n][6]: URL
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if row[0][:4] != "http": # 行頭に変更がなければ除外
        results.append([subStrBegin(row[0], "=", "&"), row[4], timeToSecond(row[2]), timeToSecond(row[3]), row[1], 0, row[0][row[0].find("http"):row[0].find("&")]])
  return results

def getYenChatList(path): # ファイルからスーパーチャットの合計金額、チャット数を取得
  DELIMITER = " " # 区切り文字
  if not os.path.isfile(path):
    return []
  list_yen_chat = []
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      list_yen_chat.append((int(row[0]), int(row[1])))
  return list_yen_chat

def updateYenChat(results, path): # 結果のうち、スーパーチャットの合計金額、チャット数を正確な値に更新
  list_yen_chat = getYenChatList(path)
  len_list = len(list_yen_chat)
  for i in range(len_list):
    results[i][4] = list_yen_chat[i][1]
    results[i][5] = list_yen_chat[i][0]

def displayText(date, count, yen): # 切り抜き動画中に表示する文字
  DISPLAY_DATE = True # 投稿日の表示オプション
  DISPLAY_COUNT = True # 該当チャット数の表示オプション
  DISPLAY_YEN = True # スーパーチャット金額(円)の表示オプション
  NEWLINE = "\n" # 改行文字
  display_text = ""
  if DISPLAY_DATE:
    display_text += date[:4] + "/" + date[4:6] + "/" + date[6:] + NEWLINE
  if DISPLAY_COUNT and count > 0:
    display_text += "関連チャット数: " + str(count) + NEWLINE
  if DISPLAY_YEN and yen > 0:
    display_text += "スパチャ総額: ¥" + str(yen) + NEWLINE
  if len(display_text) > 0:
    display_text = display_text[:- len(NEWLINE)]
  return display_text

def getResolution(results, dir): # 全切り抜きのうち、該当数が最も多い解像度を取得
  LIST_HEIGHT_16_9 = [144, 360, 480, 720, 1080, 1440, 2160, 4320] # 一般的な16:9の解像度(の高さ)一覧
  list_count = [0] * len(LIST_HEIGHT_16_9)
  for (id, date, _, _, _, _, _) in results:
    path = dir + date + "[" + id + "]_clip0.mp4"
    video = VideoFileClip(path)
    index_nearest = numpy.argmin(numpy.abs(numpy.array(LIST_HEIGHT_16_9) - video.h))
    list_count[index_nearest] += 1
  height = LIST_HEIGHT_16_9[list_count.index(max(list_count))]
  width = int(height * 16 / 9)
  return (height, width)

def subClip(resolution, text, path, path_font=""): # 各切り抜きのサイズを合わせ、文字とフェード効果を付与
  SEC_FADEIN = 1 # フェードイン秒数
  SEC_FADEOUT = 1 # フェードアウト秒数
  (height, width) = resolution
  videoclip = VideoFileClip(path, target_resolution=resolution) # 指定の解像度で動画読み込み。改良の余地はあるが、現状moviepyのバグで対応不可
  fontsize = int(height / 20)
  if path_font == "":
    textclip = TextClip(txt=text, fontsize=fontsize, color="#ffffff", bg_color="#000000c0").set_position((16, 16)).set_duration(videoclip.duration)
  else:
    textclip = TextClip(txt=text, font=path_font, fontsize=fontsize, color="#ffffff", bg_color="#000000c0").set_position((16, 16)).set_duration(videoclip.duration)
  return CompositeVideoClip(clips=[videoclip, textclip]).fadein(SEC_FADEIN).fadeout(SEC_FADEOUT)

def mergeClip(results, dir, path_font): # 全切り抜きを結合
  list_video = []
  resolution = getResolution(results, dir)
  len_results = len(results)
  count_same_id = 0
  for i in range(len_results):
    (id, date, sec_begin, sec_end, count, yen, url) = results[i]
    path = dir + date + "[" + id + "]_clip" + str(count_same_id) + ".mp4"
    text = displayText(date, count, yen)
    list_video.append(subClip(resolution, text, path, path_font))
    count_same_id += 1
    id_next = ""
    if i < len_results - 1:
      id_next = results[i + 1][0]
    if id != id_next:
      count_same_id = 0
  return concatenate_videoclips(list_video)

def generateTimestamp(results): # タイムスタンプ用の文字列を生成 各切り抜きの開始時刻、投稿日、URL
  NEWLINE = "\n" # 改行文字
  timestamp = ""
  len_results = len(results)
  sec_sum = 0
  for i in range(len_results):
    (id, date, sec_begin, sec_end, chat, yen, url) = results[i]
    timestamp += secondToTime(sec_sum) + " " + str(i + 1) + ". " + date[:4] + "/" + date[4:6] + "/" + date[6:] + " "
    timestamp += url + "&t=" + str(sec_begin) + "s" + NEWLINE
    sec_sum += sec_end - sec_begin
  return timestamp

def execute(path_results, dir_video, path_dst_video, path_dst_timestamp, path_superchat="", path_font=""):
  results = getResults(path_results)
  updateYenChat(results, path_superchat)
  video = mergeClip(results, dir_video, path_font)
  video.write_videofile(path_dst_video, codec="mpeg4", bitrate="1000000000")
  timestamp = generateTimestamp(results)
  with open(path_dst_timestamp, "w") as f:
    f.write(timestamp)

def main():
  execute("../extract/results.txt", "../clip/", "clip.mp4", "timestamp.txt", "../extract/superchat.txt", "../../../src/font/MPLUSRounded1c-Regular.ttf")

if __name__ == "__main__":
  main()
