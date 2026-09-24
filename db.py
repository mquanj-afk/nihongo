# -*- coding: utf-8 -*-
"""
学習履歴の保存(Supabase)と、ライトナー式復習スケジューリングを管理するモジュール。
- box (1〜6): 数字が大きいほど「よく覚えている」
- box が上がるほど次の復習までの間隔(日数)が長くなる
- 間違えると box は 1 に戻り、出題頻度が高くなる

事前準備:
  Supabaseでプロジェクトを作成し、SQL Editorで以下のテーブルを作成しておくこと。

    create table if not exists progress (
        user_id text not null,
        vocab_id text not null,
        box integer not null default 1,
        next_review date not null,
        wrong_count integer not null default 0,
        correct_count integer not null default 0,
        last_seen date,
        primary key (user_id, vocab_id)
    );

  さらに .streamlit/secrets.toml (または Streamlit Cloud の Secrets 設定) に
  以下を設定しておくこと。

    SUPABASE_URL = "https://xxxxxxxx.supabase.co"
    SUPABASE_KEY = "xxxxxxxxxxxxxxxxxxxxxxxx"
"""

import random
from datetime import datetime, timedelta

import streamlit as st
from supabase import create_client, Client

TABLE_NAME = "progress"

# box番号 -> 次回復習までの日数
BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14, 6: 30}
MAX_BOX = 6


def get_client() -> Client:
    """
    Supabaseクライアントをブラウザのセッションごとに1つ作る。
    st.cache_resourceで全ユーザー共有にしてしまうと、ログイン状態まで
    共有されてしまう(Aさんのログインセッションが他の人にも影響する)ため、
    st.session_stateでユーザーごとに分離する。
    """
    if "supabase_client" not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.session_state.supabase_client = create_client(url, key)
    return st.session_state.supabase_client


# ---------------- 認証(アカウント登録・ログイン) ----------------

def _apply_session_token(client: Client, result):
    """
    ログイン/サインアップ直後に、その場でPostgREST(テーブル操作)側にも
    認証トークンを明示的にセットする。
    ライブラリのバージョンによっては、client.auth側のログイン状態が
    テーブル操作(client.table(...))に自動反映されないことがあり、
    それが原因でRLS(本人のみアクセス可)に弾かれることがあるため、
    ここで確実に橋渡しする。
    """
    session = getattr(result, "session", None)
    if session and getattr(session, "access_token", None):
        client.postgrest.auth(session.access_token)
        return True
    return False


def sign_up(email, password):
    client = get_client()
    result = client.auth.sign_up({"email": email, "password": password})
    # メール確認が不要な設定の場合、サインアップ直後にセッションが発行されるので
    # そのままログイン済み状態にする
    _apply_session_token(client, result)
    return result


def sign_in(email, password):
    client = get_client()
    result = client.auth.sign_in_with_password({"email": email, "password": password})
    _apply_session_token(client, result)
    return result


def sign_out():
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass


# ---------------- プロフィール・ランキング ----------------

def upsert_profile(user_id, display_name):
    """ランキングに表示する名前を保存する(本人の行のみ書き込み可)"""
    client = get_client()
    client.table("profiles").upsert(
        {"user_id": user_id, "display_name": display_name},
        on_conflict="user_id",
    ).execute()


def get_leaderboard(limit=10):
    """全ユーザーの通算正解数ランキングを返す(多い順)"""
    client = get_client()

    profiles_res = client.table("profiles").select("user_id, display_name").execute()
    names = {row["user_id"]: row["display_name"] for row in profiles_res.data}

    progress_res = client.table(TABLE_NAME).select("user_id, correct_count").execute()
    totals = {}
    for row in progress_res.data:
        uid = row["user_id"]
        totals[uid] = totals.get(uid, 0) + row["correct_count"]

    ranking = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        {"user_id": uid, "name": names.get(uid, "名無しさん"), "total_correct": total}
        for uid, total in ranking
    ]


def init_db():
    """テーブルはSupabase側のSQL Editorで事前に作成しておくため、ここでは何もしない。
    接続確認のためだけに軽く呼び出しておく。"""
    try:
        get_client()
    except Exception as e:
        st.error(
            "Supabaseへの接続に失敗しました。secrets.tomlのSUPABASE_URL / "
            f"SUPABASE_KEYを確認してください。詳細: {e}"
        )
        st.stop()


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def get_all_progress(user_id):
    """指定ユーザーの全進捗を {vocab_id: row(dict)} の形で返す"""
    client = get_client()
    res = client.table(TABLE_NAME).select("*").eq("user_id", user_id).execute()
    return {row["vocab_id"]: row for row in res.data}


def update_progress(user_id, vocab_id, correct: bool):
    """回答結果を反映してbox・次回復習日を更新する(なければ新規作成)"""
    client = get_client()
    existing = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("user_id", user_id)
        .eq("vocab_id", vocab_id)
        .execute()
    )

    if existing.data:
        row = existing.data[0]
        box = row["box"]
        wrong_count = row["wrong_count"]
        correct_count = row["correct_count"]
    else:
        box = 1
        wrong_count = 0
        correct_count = 0

    if correct:
        box = min(box + 1, MAX_BOX)
        correct_count += 1
    else:
        box = 1
        wrong_count += 1

    next_review_date = (datetime.now() + timedelta(days=BOX_INTERVALS[box])).strftime("%Y-%m-%d")
    today = _today_str()

    client.table(TABLE_NAME).upsert(
        {
            "user_id": user_id,
            "vocab_id": vocab_id,
            "box": box,
            "next_review": next_review_date,
            "wrong_count": wrong_count,
            "correct_count": correct_count,
            "last_seen": today,
        },
        on_conflict="user_id,vocab_id",
    ).execute()


def get_all_level_summary(user_id, vocab_by_level):
    """
    vocab_by_level: {level: [vocab_id, ...]} 全レベル分をまとめて渡す。
    Supabaseへの問い合わせ1回で、レベルごとの習得率(%)と、
    ゲーミフィケーション表示用の合計正解数をまとめて返す。

    percentは「一度でも正解したことがある単語の割合」。
    正解するたびにその場で%が動くので、進捗が反映されないと感じにくい。
    """
    progress = get_all_progress(user_id)
    levels = {}
    total_correct = 0
    total_learned = 0
    total_words = 0

    for level, vocab_ids in vocab_by_level.items():
        learned = 0
        for vid in vocab_ids:
            row = progress.get(vid)
            if row:
                total_correct += row["correct_count"]
                if row["correct_count"] > 0:
                    learned += 1
                    total_learned += 1
        total = len(vocab_ids)
        total_words += total
        percent = round(learned / total * 100) if total else 0
        levels[level] = {"learned": learned, "total": total, "percent": percent}

    return {
        "levels": levels,
        "total_correct": total_correct,
        "total_learned": total_learned,
        "total_words": total_words,
    }


RANK_THRESHOLDS = [
    (0, "🌱 ひよこ級"),
    (10, "🌿 見習い"),
    (30, "🔥 がんばり屋"),
    (60, "⭐ エキスパート"),
    (100, "👑 マスター"),
    (200, "🏆 レジェンド"),
]


def get_rank_title(total_correct):
    """累計正解数に応じたゲーミフィケーション用の称号を返す"""
    title = RANK_THRESHOLDS[0][1]
    for threshold, name in RANK_THRESHOLDS:
        if total_correct >= threshold:
            title = name
        else:
            break
    return title


MAX_WEIGHT_BONUS = 3  # 間違いによる重みの上限(これ以上は増やさない)


def pick_next_vocab_id(user_id, vocab_ids, exclude_id=None):
    """
    出題する語彙を1つ選ぶ。
    優先順位: ① 復習期限が来ているもの(box優先度=間違いが多いほど優先。ただし上限あり)
             ② まだ一度も学習していない新規のもの
             ③ それ以外(復習期限前だが選択肢として残っているもの)
    exclude_idを指定すると、選択肢が他にもある限りその語彙は避ける
    (直前と同じ問題が連続して出るのを防ぐため)。
    """
    progress = get_all_progress(user_id)
    today = _today_str()

    pool = [v for v in vocab_ids if v != exclude_id] or list(vocab_ids)

    due_items = []
    new_items = []
    other_items = []

    for vid in pool:
        row = progress.get(vid)
        if row is None:
            new_items.append(vid)
        elif row["next_review"] <= today:
            # 間違いが多いほど優先はするが、青天井にはしない(上限あり)
            weight = 1 + min(row["wrong_count"], MAX_WEIGHT_BONUS)
            due_items.append((vid, weight))
        else:
            other_items.append(vid)

    if due_items:
        ids = [x[0] for x in due_items]
        weights = [x[1] for x in due_items]
        return random.choices(ids, weights=weights, k=1)[0]
    if new_items:
        return random.choice(new_items)
    if other_items:
        return random.choice(other_items)
    return random.choice(pool)


def build_test_queue(vocab_ids, num_questions):
    """
    テストモード用の出題リストを作る。
    語彙数が問題数以上なら、シャッフルして重複なしで選ぶ。
    語彙数が問題数より少ない場合だけ、足りない分を重複ありで補う。
    """
    ids = list(vocab_ids)
    random.shuffle(ids)
    if len(ids) >= num_questions:
        return ids[:num_questions]
    queue = list(ids)
    while len(queue) < num_questions:
        queue.append(random.choice(ids))
    return queue
