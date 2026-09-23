# -*- coding: utf-8 -*-
"""
語彙データベース
level: 1=日常単語, 2=日常会話, 3=学校生活, 4=日本での生活, 5=上級表現
"""

VOCAB_DATA = [
    # ---------------- Level 1: 日常単語 ----------------
    {"id": "L1-01", "level": 1, "japanese": "水", "reading": "みず", "vietnamese": "Nước"},
    {"id": "L1-02", "level": 1, "japanese": "火", "reading": "ひ", "vietnamese": "Lửa"},
    {"id": "L1-03", "level": 1, "japanese": "食べる", "reading": "たべる", "vietnamese": "Ăn"},
    {"id": "L1-04", "level": 1, "japanese": "飲む", "reading": "のむ", "vietnamese": "Uống"},
    {"id": "L1-05", "level": 1, "japanese": "学校", "reading": "がっこう", "vietnamese": "Trường học"},
    {"id": "L1-06", "level": 1, "japanese": "家", "reading": "いえ", "vietnamese": "Nhà"},
    {"id": "L1-07", "level": 1, "japanese": "車", "reading": "くるま", "vietnamese": "Xe hơi"},
    {"id": "L1-08", "level": 1, "japanese": "本", "reading": "ほん", "vietnamese": "Sách"},
    {"id": "L1-09", "level": 1, "japanese": "友達", "reading": "ともだち", "vietnamese": "Bạn bè"},
    {"id": "L1-10", "level": 1, "japanese": "先生", "reading": "せんせい", "vietnamese": "Giáo viên"},

    # ---------------- Level 2: 日常会話 ----------------
    {"id": "L2-01", "level": 2, "japanese": "おはようございます", "reading": "おはようございます", "vietnamese": "Chào buổi sáng"},
    {"id": "L2-02", "level": 2, "japanese": "ありがとうございます", "reading": "ありがとうございます", "vietnamese": "Cảm ơn"},
    {"id": "L2-03", "level": 2, "japanese": "すみません", "reading": "すみません", "vietnamese": "Xin lỗi / Xin phép"},
    {"id": "L2-04", "level": 2, "japanese": "お元気ですか", "reading": "おげんきですか", "vietnamese": "Bạn khỏe không?"},
    {"id": "L2-05", "level": 2, "japanese": "いただきます", "reading": "いただきます", "vietnamese": "Mời (trước khi ăn)"},
    {"id": "L2-06", "level": 2, "japanese": "ごちそうさまでした", "reading": "ごちそうさまでした", "vietnamese": "Cảm ơn vì bữa ăn"},
    {"id": "L2-07", "level": 2, "japanese": "お願いします", "reading": "おねがいします", "vietnamese": "Xin nhờ / Làm ơn"},
    {"id": "L2-08", "level": 2, "japanese": "いくらですか", "reading": "いくらですか", "vietnamese": "Bao nhiêu tiền?"},
    {"id": "L2-09", "level": 2, "japanese": "どこですか", "reading": "どこですか", "vietnamese": "Ở đâu?"},
    {"id": "L2-10", "level": 2, "japanese": "わかりました", "reading": "わかりました", "vietnamese": "Tôi hiểu rồi"},

    # ---------------- Level 3: 学校生活 ----------------
    {"id": "L3-01", "level": 3, "japanese": "授業", "reading": "じゅぎょう", "vietnamese": "Tiết học"},
    {"id": "L3-02", "level": 3, "japanese": "宿題", "reading": "しゅくだい", "vietnamese": "Bài tập về nhà"},
    {"id": "L3-03", "level": 3, "japanese": "試験", "reading": "しけん", "vietnamese": "Kỳ thi"},
    {"id": "L3-04", "level": 3, "japanese": "教科書", "reading": "きょうかしょ", "vietnamese": "Sách giáo khoa"},
    {"id": "L3-05", "level": 3, "japanese": "部活", "reading": "ぶかつ", "vietnamese": "Hoạt động câu lạc bộ"},
    {"id": "L3-06", "level": 3, "japanese": "出席", "reading": "しゅっせき", "vietnamese": "Có mặt / điểm danh"},
    {"id": "L3-07", "level": 3, "japanese": "遅刻", "reading": "ちこく", "vietnamese": "Đi trễ"},
    {"id": "L3-08", "level": 3, "japanese": "休み時間", "reading": "やすみじかん", "vietnamese": "Giờ nghỉ giải lao"},
    {"id": "L3-09", "level": 3, "japanese": "クラスメート", "reading": "くらすめーと", "vietnamese": "Bạn cùng lớp"},
    {"id": "L3-10", "level": 3, "japanese": "卒業", "reading": "そつぎょう", "vietnamese": "Tốt nghiệp"},

    # ---------------- Level 4: 日本での生活 ----------------
    {"id": "L4-01", "level": 4, "japanese": "役所", "reading": "やくしょ", "vietnamese": "Cơ quan hành chính"},
    {"id": "L4-02", "level": 4, "japanese": "保険証", "reading": "ほけんしょう", "vietnamese": "Thẻ bảo hiểm"},
    {"id": "L4-03", "level": 4, "japanese": "在留カード", "reading": "ざいりゅうかーど", "vietnamese": "Thẻ cư trú"},
    {"id": "L4-04", "level": 4, "japanese": "アルバイト", "reading": "あるばいと", "vietnamese": "Làm thêm"},
    {"id": "L4-05", "level": 4, "japanese": "家賃", "reading": "やちん", "vietnamese": "Tiền thuê nhà"},
    {"id": "L4-06", "level": 4, "japanese": "引っ越し", "reading": "ひっこし", "vietnamese": "Chuyển nhà"},
    {"id": "L4-07", "level": 4, "japanese": "ゴミの分別", "reading": "ごみのぶんべつ", "vietnamese": "Phân loại rác"},
    {"id": "L4-08", "level": 4, "japanese": "病院", "reading": "びょういん", "vietnamese": "Bệnh viện"},
    {"id": "L4-09", "level": 4, "japanese": "銀行口座", "reading": "ぎんこうこうざ", "vietnamese": "Tài khoản ngân hàng"},
    {"id": "L4-10", "level": 4, "japanese": "契約", "reading": "けいやく", "vietnamese": "Hợp đồng"},

    # ---------------- Level 5: 上級表現 ----------------
    {"id": "L5-01", "level": 5, "japanese": "手続き", "reading": "てつづき", "vietnamese": "Thủ tục"},
    {"id": "L5-02", "level": 5, "japanese": "申請する", "reading": "しんせいする", "vietnamese": "Nộp đơn / đăng ký"},
    {"id": "L5-03", "level": 5, "japanese": "承知いたしました", "reading": "しょうちいたしました", "vietnamese": "Tôi đã hiểu rõ (kính ngữ)"},
    {"id": "L5-04", "level": 5, "japanese": "お手数をおかけします", "reading": "おてすうをおかけします", "vietnamese": "Xin lỗi vì đã làm phiền"},
    {"id": "L5-05", "level": 5, "japanese": "恐れ入りますが", "reading": "おそれいりますが", "vietnamese": "Xin lỗi nhưng (lịch sự)"},
    {"id": "L5-06", "level": 5, "japanese": "大変申し訳ございません", "reading": "たいへんもうしわけございません", "vietnamese": "Tôi thành thật xin lỗi"},
    {"id": "L5-07", "level": 5, "japanese": "ご検討ください", "reading": "ごけんとうください", "vietnamese": "Xin vui lòng cân nhắc"},
    {"id": "L5-08", "level": 5, "japanese": "差し支えなければ", "reading": "さしつかえなければ", "vietnamese": "Nếu không phiền"},
    {"id": "L5-09", "level": 5, "japanese": "拝見する", "reading": "はいけんする", "vietnamese": "Xem (khiêm nhường ngữ)"},
    {"id": "L5-10", "level": 5, "japanese": "ご不明な点がございましたら", "reading": "ごふめいなてんがございましたら", "vietnamese": "Nếu có điều gì chưa rõ"},
]

LEVEL_NAMES = {
    1: "レベル1: 日常単語",
    2: "レベル2: 日常会話",
    3: "レベル3: 学校生活",
    4: "レベル4: 日本での生活",
    5: "レベル5: 上級表現",
}


def get_vocab_by_level(level):
    return [v for v in VOCAB_DATA if v["level"] == level]


def get_vocab_by_id(vocab_id):
    for v in VOCAB_DATA:
        if v["id"] == vocab_id:
            return v
    return None
