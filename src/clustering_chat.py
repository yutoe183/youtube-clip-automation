import sys # argv
import os # listdir, path.isfile
import re # search
import unicodedata # normalize

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

def getId(filename): # ファイル名からVideoIDを抽出
  return subStrEnd(filename, "[", "]")

def getDate(filename): # ファイル名から投稿日を抽出
  return subStrEnd(filename, "/", "[")

def getTitle(line): # 生データからタイトルを抽出
  return subStrBegin(line, '"title": "', '"')

def getReleaseDate(line): # 生データから公開日を抽出
  return subStrBegin(line, '"release_date": "', '"')

def getSecond(line): # 生データから時刻を抽出
  str = subStrBegin(line, '"videoOffsetTimeMsec": "', '"')[:-3] # mili sec で記載されているため下3文字削る
  if str == "":
    return 0
  return int(str)

def getText(line): # 生データからチャットを抽出
  text = ""
  list_str_begin_end = (('"text": "', '"'), ('"shortcuts": ["', '"'))
  str_end = ''
  while True: # チャットがいくつかに分割される場合があるためすべて抽出して結合
    begin = len(line)
    for str_begin_end in list_str_begin_end:
      (str_begin, str_end_current) = str_begin_end
      begin_current = line.find(str_begin) + len(str_begin)
      if begin_current >= len(str_begin) and begin_current < begin:
        begin = begin_current
        str_end = str_end_current
    if begin >= len(line):
      break
    end = line[begin:].find(str_end) + begin
    text += line[begin:end]
    line = line[end + len(str_end):]
  return text

def exchangeToYen(amount): # 円に両替した場合の金額
  YEN_PER = {"¥": 1, "$": 150, "€": 160, "₩": 0.1, "£": 190, "₱": 2.5, "₹": 1.8, "₫": 0.006, "₪": 41, "MYR": 32, "CA$": 110, "NT$": 4.7, "THB": 4, "HK$": 19, "A$": 97, "ARS": 0.17, "PLN": 37, "MX$": 8.7, "CLP": 0.15, "IDR": 0.01, "SGD": 110, "R$": 30, "ZAR": 7.9, "RON": 32, "NOK": 14, "NZ$": 90, "RUB": 1.6, "DKK": 22, "SEK": 14, "CHF": 170, "PEN": 40, "CRC": 0.3, "RSD": 1.4, "UYU": 3.8, "DOP": 2.5, "ISK": 1.1, "SAR": 40, "HUF": 40, "CZK": 6.4, "BGN": 82, "BYN": 45, "GTQ": 19, "BOB": 21, "PYG": 0.02, "TRY": 4.6, "COP": 0.038, "HRK": 20, "AED": 40, "KES": 1, "NIO": 4, "ден": 2.6}
  # 為替レートは2024/03/10時点、有効数字2桁程度。未記載の通貨は0円で換算
  amount_normalized = unicodedata.normalize("NFKC", amount).replace(" ", "").replace(",", "")
  if amount_normalized == "":
    return 0
  for symbol in YEN_PER:
    if amount_normalized[:len(symbol)] == symbol:
      return float(amount_normalized[len(symbol):]) * YEN_PER[symbol]
  return 0

def getYenSuperchat(line): # 生データからスーパーチャット金額を抽出
  return exchangeToYen(subStrBegin(line, '"purchaseAmountText": {"simpleText": "', '"'))

def isInfo(filename): # コメントならTrue, チャットならFalseを返す
  return subStrBegin(filename, "].", ".") == "info"

def isValidChat(line): # データが重複していないか確認
  if line.find("addChatItemAction") < 0:
    return False
  return True

def containStr(text, query): # 文字列が含まれるか判定
  if query == "":
    return False
  return re.search(query, text) != None

def getCommentList(line, query): # 生データから該当コメントを抽出してリスト化
  if query == "":
    return []
  list_comment = []
  str_begin = '"text": "'
  str_end = '"'
  while True: # 全コメントを抽出
    begin = line.find(str_begin) + len(str_begin)
    if begin < len(str_begin):
      break
    end = line[begin:].find(str_end) + begin
    comment = line[begin:end]
    if containStr(comment, query):
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

def timeToDisplayTime(str): # 時間を表示用に変換(yyyyMMdd -> yyyy/MM/dd)
  return str[0:4] + "/" + str[4:6] + "/" + str[6:8]

def clusteringChat(dir, list_query): # チャットを1事象ごとにクラスタリング
  SEC_CLUSTERING = 90 # チャット間隔が90秒未満の場合、同じ事象に対するコメントだと判定(初期値)
  SEC_PRE = 60 # lv0チャット1個目の何秒前からチャット数を数えるか
  MAX_EXAMPLE_CHAT = 24 # 参考例として出力する該当チャット数の最大値
  MAX_EXAMPLE_LV = 2 # 参考例として出力する該当チャットLvの種類数
  MAX_EXAMPLE_COMMENT = 24 # 参考例として出力する該当コメント数の最大値
  EVAL_LV = (1, 0.25) # 各クエリlvに該当するチャット1つあたりの影響度。SEC_PRE秒間に加算値が1以上の場合、該当箇所と判定

  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット/コメント数, [n][5][m]: チャット/コメント例 (m <= 12), [n][6]: 投げ銭金額, [n][7]: 公開日
  list_date_title = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: タイトル

  NUM_QUERY_LV = 3 # クエリの種類数
  query_lv = [""] * NUM_QUERY_LV # 検索条件厳しい順
  for i in range(min(len(list_query), NUM_QUERY_LV)):
    query_lv[i] = list_query[i]
  for i in range(min(len(list_query), NUM_QUERY_LV), len(query_lv) - 1):
    query_lv[i] = query_lv[len(list_query) - 1]

  list_file = os.listdir(dir)
  list_file.sort() # 日付順に並び替え 日付が同じ場合はID順
  BUF_SIZE = 1000 # 下記リングバッファのサイズ
  count_progress = 0 # 進捗表示用カウンタ
  for filename in list_file:
    count_progress += 1
    print("\r" + "clustering: " + str(count_progress) + " / " + str(len(list_file)), end="")
    buf_lv_count = [(0, 0, 0)] * BUF_SIZE # 該当チャットの秒数とクエリlvと金額を保持するリングバッファ
    buf_lv_itr = 0 # 上記リングバッファのイテレータ
    sec_end_same = 0 # 同じ事象だと判定される期限
    release_date = "00000000"
    with open(dir + filename) as f:
    # 入力データは、1チャットにつき1行。コメントは全データが1行
      id = getId(filename)
      date = getDate(filename)
      if date.isdecimal() and int(release_date) < int(date): # 投稿日 < 公開日 が成り立つように。ただし、infoファイルから読み込まれるはずなので、このif文の有無で結果は変わらないはず
        release_date = date
      if isInfo(filename): # コメントの場合、開始終了秒数を0として追加
        for line in f:
          list_date_title.append((id, date, getTitle(line)))
          if getReleaseDate(line) != "":
            release_date = getReleaseDate(line)
          list_comment = getCommentList(line, query_lv[0])
          if len(list_comment) > 0: # コメントに検索文字列が含まれていない場合は除外
            results.append([id, date, 0, 0, len(list_comment), [list_comment[0:MAX_EXAMPLE_COMMENT]], 0, release_date])
      else: # チャットの場合
        for line in f:
          if not isValidChat(line): # チャットが既存データと重複する場合は除外
            continue
          chat_text = getText(line)
          yen = getYenSuperchat(line)
          query_lv_current = NUM_QUERY_LV
          for i in range(NUM_QUERY_LV):
            if containStr(chat_text, query_lv[i]):
              query_lv_current = i
              break
          if query_lv_current >= NUM_QUERY_LV and yen <= 0: # チャットに検索文字列が含まれていない場合は除外
            continue
          chat_second = getSecond(line)
          is_same = len(results) > 0 and results[-1][0] == id and results[-1][3] > 0 and chat_second <= sec_end_same
          # チャット間隔が SEC_CLUSTERING 秒未満の場合、同じ事象に対するコメントだと判定
          if not is_same:
            buf_lv_count[buf_lv_itr] = (chat_second, query_lv_current, yen) # バッファに現在のチャットを追加
            buf_lv_itr = (buf_lv_itr + 1) % BUF_SIZE
            count_pre = 0
            yen_pre = 0
            eval_pre = 0 # 該当チャット判定用評価値。1以上なら該当
            for itr in range(buf_lv_itr - 1, buf_lv_itr - 1 - BUF_SIZE, -1): # 最新のチャットから遡る
              if buf_lv_count[itr][0] <= max(0, chat_second - SEC_PRE):
                break
              count_pre += 1
              yen_pre += buf_lv_count[itr][2]
              if buf_lv_count[itr][1] < len(EVAL_LV):
                eval_pre += EVAL_LV[buf_lv_count[itr][1]]
            if eval_pre >= 1: # 該当チャットである場合
              results.append([id, date, chat_second, chat_second, count_pre, [[] for i in range(MAX_EXAMPLE_LV)], yen_pre, release_date])
              sec_end_same = 0
              is_same = True
          if is_same:
            results[-1][3] = max(chat_second, results[-1][3])
            results[-1][4] += 1
            results[-1][6] += yen
            if len(results[-1][5]) < MAX_EXAMPLE_CHAT and query_lv_current < MAX_EXAMPLE_LV: # チャット例を MAX_EXAMPLE_CHAT 個まで保持
              results[-1][5][query_lv_current].append(chat_text)
            sec_end_same += (chat_second + SEC_CLUSTERING - sec_end_same) * SEC_CLUSTERING / (SEC_CLUSTERING + (chat_second - results[-1][2]) * 4) # 期限の加算時間を徐々に小さくする
  return results, list_date_title

def writeResults(results, path): # 結果を出力: URL チャット/コメント数 金額 開始秒数 終了秒数 投稿日 チャット例
  DELIMITER = " " # 出力時の区切り文字
  NEWLINE = "\n" # 改行文字
  SEC_BUFFER = 15 # チャット1個目の何秒前から動画を確認するか
  with open(path, "w") as f:
    for (id, _, sec_begin, sec_end, count, list_list_text, yen, release_date) in results:
      second = max(sec_begin - SEC_BUFFER, 0)
      f.write("https://youtu.be/" + id + "?t=" + str(second) + "s" + DELIMITER)
      f.write(str(count) + DELIMITER)
      f.write(str(int(yen)) + DELIMITER)
      f.write(secondToTime(sec_begin) + DELIMITER)
      f.write(secondToTime(sec_end) + DELIMITER)
      f.write(timeToDisplayTime(release_date))
      for list_text in list_list_text:
        f.write(DELIMITER)
        for text in list_text:
          f.write(text + DELIMITER)
      f.write(NEWLINE)

def writeListDateTitle(list_date_title, path): # ID,日付,タイトルを出力
  DELIMITER = " " # 出力時の区切り文字
  NEWLINE = "\n" # 改行文字
  with open(path, "w") as f:
    for (id, date, title) in list_date_title:
      f.write(id + DELIMITER)
      f.write(date + DELIMITER)
      f.write(title + NEWLINE)

def execute(dir_src, path_results, path_list_date_title, list_query, force):
  if len(list_query) <= 0: # クエリ文字列がなければ終了
    return
  if os.path.isfile(path_results) and not force: # 既に出力先ファイルが存在し、オプションが指定されていないなら終了
    print(path_results + " already exists.")
    return
  results, list_date_title = clusteringChat(dir_src, list_query)
  writeResults(results, path_results)
  writeListDateTitle(list_date_title, path_list_date_title)
  print()
  print("results: " + path_results)
  print("list_date_title: " + path_list_date_title)

def main():
  force = False # results.txtを強制的に上書きするか
  list_query = []
  for i in range(1, len(sys.argv)):
    arg = sys.argv[i]
    if arg == "-f" or arg == "-F" or arg == "--force":
      force = True
    elif not (len(arg) == 8 and arg.isdecimal()):
      list_query.append(arg)
  execute("live_chat/", "extract/results.txt", "extract/list_date_title.txt", list_query, force)

if __name__ == "__main__":
  main()
