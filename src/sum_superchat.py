import sys # argv
import os # path.isfile
import re # search
import csv # reader

def subStrBegin(str, str_begin, str_end): # 該当範囲の文字列を切り出し(開始文字列から検索)
  begin = str.find(str_begin) + len(str_begin)
  if begin < len(str_begin):
    return ""
  end = str[begin:].find(str_end) + begin
  return str[begin:end]

def getSecond(line): # 生データから時刻を抽出
  str = subStrBegin(line, '"videoOffsetTimeMsec": "', '"')[:-3] # mili sec で記載されているため下3文字削る
  if str == "":
    return 0
  return int(str)

def getText(line): # 生データからチャットを抽出
  text = ""
  str_begin = '"text": "'
  str_end = '"'
  while True: # チャットがいくつかに分割される場合があるためすべて抽出して結合
    begin = line.find(str_begin) + len(str_begin)
    if begin < len(str_begin):
      break
    end = line[begin:].find(str_end) + begin
    text += line[begin:end]
    line = line[end + len(str_end):]
  return text

def getYen(line): # 生データからスーパーチャット金額を抽出
  YEN_PER = {"¥": 1, "$": 150, "€": 160} # 円, ドル, ユーロ に対応 (為替レートは2024/02/13時点)
  str = subStrBegin(line, '"purchaseAmountText": {"simpleText": "', '"')
  if str == "":
    return 0
  if str[0] not in YEN_PER:
    return 0
  return float(str[1:].replace(",", "")) * YEN_PER[str[0]]

def isValidChat(line): # データが重複していないか確認
  if line.find("addChatItemAction") < 0:
    return False
  return True

def containStr(text, str): # 文字列が含まれるか判定
  return re.search(str, text) != None

def getCommentList(line, str): # 生データから該当コメントを抽出してリスト化
  list_comment = []
  str_begin = '"text": "'
  str_end = '"'
  while True: # 全コメントを抽出
    begin = line.find(str_begin) + len(str_begin)
    if begin < len(str_begin):
      break
    end = line[begin:].find(str_end) + begin
    comment = line[begin:end]
    if containStr(comment, str):
      list_comment.append(comment)
    line = line[end + len(str_end):]
  return list_comment

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

def getResults(path): # ファイルから結果を取得
  DELIMITER = " " # 区切り文字
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数
  with open(path) as f:
    reader = csv.reader(f, delimiter=DELIMITER)
    for row in reader:
      if row[0][:4] != "http": # 行頭に変更がなければ除外
        results.append((subStrBegin(row[0], "=", "&"), row[4], timeToSecond(row[2]), timeToSecond(row[3])))
  return results

def sumSuperchat(sec_begin, sec_end, str, path_chat, path_comment): # スーパーチャットの合計金額、チャット数を取得
  SEC_CLUSTERING = 90 # スーパーチャットかチャットの間隔が60秒未満の場合、同じ事象に対するコメントだと判定
  sum_yen = 0
  count_chat = 0
  if os.path.isfile(path_chat):
    with open(path_chat) as f:
      for line in f:
        if not isValidChat(line):
          continue
        second = getSecond(line)
        text = getText(line)
        yen = getYen(line)
        contain_str = str != "" and containStr(text, str)
        if second >= sec_begin:
          if second < sec_end + SEC_CLUSTERING:
            if yen > 0 or contain_str:
              sum_yen += yen
              count_chat += 1
              if second > sec_end:
                sec_end = second
          else:
            break
  count_comment = 0
  if os.path.isfile(path_comment):
    with open(path_comment) as f:
      for line in f:
        if str != "":
          count_comment += len(getCommentList(line, str))
  return int(sum_yen), count_chat, count_comment

def sumSuperchatList(results, str, dir): # 全候補に対するスーパーチャットの合計金額、チャット数を返す
  list_sum = []
  for (id, date, sec_begin, sec_end) in results:
    path_chat = dir + date + "[" + id + "].live_chat.json"
    path_comment = dir + date + "[" + id + "].info.json"
    list_sum.append(sumSuperchat(sec_begin, sec_end, str, path_chat, path_comment))
  return list_sum

def writeSumSuperchat(list_sum, path): # 結果を出力
  DELIMITER = " " # 出力時の区切り文字
  NEWLINE = "\n" # 改行文字
  with open(path, "w") as f:
    for sum_superchat in list_sum:
      f.write(str(sum_superchat[0]) + DELIMITER + str(sum_superchat[1]) + DELIMITER + str(sum_superchat[2]) + NEWLINE)

def execute(str_search, path_src, dir, path_dst):
  results = getResults(path_src)
  list_sum = sumSuperchatList(results, str_search, dir)
  writeSumSuperchat(list_sum, path_dst)

def main():
  str = ""
  if len(sys.argv) > 1:
    str = sys.argv[1]
  execute(str, "results.txt", "../live_chat/", "superchat.txt")

if __name__ == "__main__":
  main()
