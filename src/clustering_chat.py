import sys # argv
import re # search
import operator # itemgetter

def subStrBegin(str, str_begin, str_end): # 該当範囲の文字列を切り出し(開始文字列から検索)
  begin = str.find(str_begin) + len(str_begin)
  if begin < len(str_begin):
    return ""
  end = str[begin:].find(str_end) + begin
  return str[begin:end]

def subStrEnd(str, str_begin, str_end): # 該当範囲の文字列を切り出し(終了文字列から検索)
  end = str.find(str_end)
  if end < 0:
    return ""
  begin = str[:end].rfind(str_begin) + len(str_begin)
  return str[begin:end]

def getId(line): # 生データからVideoIDを抽出
  return subStrBegin(line, "[", "]")

def getDate(line): # 生データから投稿日を抽出
  return subStrEnd(line, "/", "[")

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

def isChat(line): # チャットならTrue、コメントならFalseを返す
  return subStrBegin(line, "].", ".") == "live_chat"

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

def secondToTime(second_src): # 秒数(int)から時間表示(str)に変換
  SECOND_PER_MINUTE = 60
  MINUTE_PER_HOUR = 60
  second = second_src % SECOND_PER_MINUTE
  second_src = int((second_src - second) / SECOND_PER_MINUTE)
  minute = second_src % MINUTE_PER_HOUR
  second_src = int((second_src - minute) / MINUTE_PER_HOUR)
  hour = second_src
  return str(hour) + ":" + str(minute).zfill(2) + ":" + str(second).zfill(2)

def clusteringChat(path, str=""): # チャットを1事象ごとにクラスタリング
  SEC_CLUSTERING = 60 # チャット間隔が60秒未満の場合、同じ事象に対するコメントだと判定
  MAX_EXAMPLE_CHAT = 12 # 参考例として出力する該当チャット数の最大値
  MAX_EXAMPLE_COMMENT = 12 # 参考例として出力する該当コメント数の最大値
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット数, [n][5][m]: チャット例 (m <= 5)
  with open(path) as f:
  # 入力データは、1チャットにつき1行
    for line in f:
      video_id = getId(line)
      video_date = getDate(line)
      if not isChat(line): # コメントの場合、開始終了秒数を0として追加
        if str == "":
          list_comment = []
        else:
          list_comment = getCommentList(line, str)
          if len(list_comment) == 0: # コメントに検索文字列が含まれていない場合は除外
            continue
        results.append([video_id, video_date, 0, 0, len(list_comment), list_comment[0:MAX_EXAMPLE_COMMENT]])
        continue
      if not isValidChat(line): # チャットが既存データと重複する場合は除外
        continue
      chat_second = getSecond(line)
      chat_text = getText(line)
      if str != "" and not containStr(chat_text, str): # チャットに検索文字列が含まれていない場合は除外
        continue
      if len(results) > 0 and results[-1][0] == video_id and results[-1][3] > 0 and chat_second - results[-1][3] < SEC_CLUSTERING:
      # チャット間隔が SEC_CLUSTERING 秒未満の場合、同じ事象に対するコメントだと判定
        results[-1][3] = max(chat_second, results[-1][3])
        results[-1][4] += 1
        if results[-1][4] <= MAX_EXAMPLE_CHAT: # チャット例を MAX_EXAMPLE_CHAT 個まで保持
          results[-1][5].append(chat_text)
      else:
        results.append([video_id, video_date, chat_second, chat_second, 1, [chat_text]])
  return results

def writeResults(results, path): # 結果を出力: URL 暫定チャット数 開始秒数 終了秒数 投稿日 チャット例(最大5個)
  DELIMITER = " " # 出力時の区切り文字
  NEWLINE = "\n" # 改行文字
  SEC_BUFFER = 30 # チャット1個目の何秒前から動画を確認するか
  with open(path, "w") as f:
    for (id, date, sec_begin, sec_end, count, list_text) in results:
      second = max(sec_begin - SEC_BUFFER, 0)
      f.write("https://www.youtube.com/watch?v=" + id + "&t=" + str(second) + "s" + DELIMITER)
      f.write(str(count) + DELIMITER)
      f.write(secondToTime(sec_begin) + DELIMITER)
      f.write(secondToTime(sec_end) + DELIMITER)
      f.write(date + DELIMITER)
      for text in list_text:
        f.write(text + DELIMITER)
      f.write(NEWLINE)

def execute(dir, file_src, file_dst, str=""):
  results = clusteringChat(dir + file_src, str)
  results_sorted = sorted(results, key=operator.itemgetter(1, 0)) # 日付順に並び替え 日付が同じ場合はID順
  writeResults(results_sorted, dir + file_dst)

def main():
  str = ""
  if len(sys.argv) > 1:
    str = sys.argv[1]
  execute("./", "search.txt", "results.txt", str)

if __name__ == "__main__":
  main()
