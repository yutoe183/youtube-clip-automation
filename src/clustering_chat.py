import sys # argv
import os # listdir
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
  return re.search(query, text) != None

def getCommentList(line, query): # 生データから該当コメントを抽出してリスト化
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

def clusteringChat(dir, list_query): # チャットを1事象ごとにクラスタリング
  SEC_CLUSTERING = 90 # チャット間隔が90秒未満の場合、同じ事象に対するコメントだと判定(初期値)
  SEC_PRE = 15 # lv0チャット1個目の何秒前からチャット数を数えるか
  MAX_EXAMPLE_CHAT = 24 # 参考例として出力する該当チャット数の最大値
  MAX_EXAMPLE_COMMENT = 24 # 参考例として出力する該当コメント数の最大値
  results = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: 開始秒数, [n][3]: 終了秒数, [n][4]: チャット/コメント数, [n][5][m]: チャット/コメント例 (m <= 12), [n][6]: 投げ銭金額
  list_date_title = [] # [n][0]: VideoID, [n][1]: 投稿日, [n][2]: タイトル

  query_lv = [""] * 3 # 検索条件厳しい順
  for i in range(len(list_query)):
    query_lv[i] = list_query[i]
  for i in range(len(list_query), len(query_lv) - 1):
    query_lv[i] = query_lv[len(list_query) - 1]
  
  list_file = os.listdir(dir)
  list_file.sort() # 日付順に並び替え 日付が同じ場合はID順
  BUF_SIZE = 1000 # 下記リングバッファのサイズ
  for filename in list_file:
    buf_lv1_count = [(0, 0)] * BUF_SIZE # query_lv[1] に該当するチャットの秒数と金額を保持するリングバッファ
    buf_lv1_itr = 0 # 上記リングバッファのイテレータ
    sec_end_same = 0 # 同じ事象だと判定される期限
    with open(dir + filename) as f:
    # 入力データは、1チャットにつき1行。コメントは全データが1行
      id = getId(filename)
      date = getDate(filename)
      if isInfo(filename): # コメントの場合、開始終了秒数を0として追加
        for line in f:
          list_date_title.append((id, date, getTitle(line)))
          if query_lv[0] != "":
            list_comment = getCommentList(line, query_lv[0])
            if len(list_comment) > 0: # コメントに検索文字列が含まれていない場合は除外
              results.append([id, date, 0, 0, len(list_comment), list_comment[0:MAX_EXAMPLE_COMMENT], 0])
      else: # チャットの場合
        for line in f:
          if not isValidChat(line): # チャットが既存データと重複する場合は除外
            continue
          chat_text = getText(line)
          yen = getYenSuperchat(line)
          contain_lv1 = query_lv[0] != "" and containStr(chat_text, query_lv[1])
          if not contain_lv1 and yen <= 0: # チャットに検索文字列が含まれていない場合は除外
            continue
          chat_second = getSecond(line)
          is_same = len(results) > 0 and results[-1][0] == id and results[-1][3] > 0 and chat_second <= sec_end_same
          contain_lv0 = query_lv[0] != "" and containStr(chat_text, query_lv[0])
          if contain_lv0 and not is_same:
          # チャット間隔が SEC_CLUSTERING 秒未満の場合、同じ事象に対するコメントだと判定
            count_pre = 0 # 最初のlv0チャット以前のlv1チャット数 (SEC_PRE 秒前まで)
            yen_pre = 0
            for itr in range(buf_lv1_itr - 1, buf_lv1_itr - 1 - BUF_SIZE, -1):
              if buf_lv1_count[itr][0] <= max(0, chat_second - SEC_PRE):
                break
              count_pre += 1
              yen_pre += buf_lv1_count[itr][1]
            results.append([id, date, chat_second, chat_second, count_pre, [], yen_pre])
            sec_end_same = 0
            is_same = True
          if is_same:
            results[-1][3] = max(chat_second, results[-1][3])
            results[-1][4] += 1
            results[-1][6] += yen
            if len(results[-1][5]) < MAX_EXAMPLE_CHAT and contain_lv0: # チャット例を MAX_EXAMPLE_CHAT 個まで保持
              results[-1][5].append(chat_text)
            sec_end_same += (chat_second + SEC_CLUSTERING - sec_end_same) * SEC_CLUSTERING / (SEC_CLUSTERING + (chat_second - results[-1][2]) * 4) # 期限の加算時間を徐々に小さくする
          else:
            buf_lv1_count[buf_lv1_itr] = (chat_second, yen)
            buf_lv1_itr = (buf_lv1_itr + 1) % BUF_SIZE

  return results, list_date_title

def writeResults(results, path): # 結果を出力: URL チャット/コメント数 金額 開始秒数 終了秒数 投稿日 チャット例
  DELIMITER = " " # 出力時の区切り文字
  NEWLINE = "\n" # 改行文字
  SEC_BUFFER = 30 # チャット1個目の何秒前から動画を確認するか
  with open(path, "w") as f:
    for (id, date, sec_begin, sec_end, count, list_text, yen) in results:
      second = max(sec_begin - SEC_BUFFER, 0)
      f.write("https://youtu.be/" + id + "?t=" + str(second) + "s" + DELIMITER)
      f.write(str(count) + DELIMITER)
      f.write(str(int(yen)) + DELIMITER)
      f.write(secondToTime(sec_begin) + DELIMITER)
      f.write(secondToTime(sec_end) + DELIMITER)
      f.write(date + DELIMITER)
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

def execute(dir_src, path_results, path_list_date_title, list_query):
  results, list_date_title = clusteringChat(dir_src, list_query)
  writeResults(results, path_results)
  writeListDateTitle(list_date_title, path_list_date_title)

def main():
  execute("../live_chat/", "results.txt", "list_date_title.txt", sys.argv[1:])

if __name__ == "__main__":
  main()
