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


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


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


def get_level_stats(user_id, vocab_ids):
    """指定した語彙IDリストについて、新規/学習中/習得済みの件数を返す"""
    progress = get_all_progress(user_id)
    new_count = 0
    learning_count = 0
    mastered_count = 0
    for vid in vocab_ids:
        row = progress.get(vid)
        if row is None:
            new_count += 1
        elif row["box"] >= MAX_BOX:
            mastered_count += 1
        else:
            learning_count += 1
    return {"new": new_count, "learning": learning_count, "mastered": mastered_count}


def pick_next_vocab_id(user_id, vocab_ids):
    """
    出題する語彙を1つ選ぶ。
    優先順位: ① 復習期限が来ているもの(box優先度=間違いが多いほど優先)
             ② まだ一度も学習していない新規のもの
             ③ それ以外(復習期限前だが選択肢として残っているもの)
    """
    progress = get_all_progress(user_id)
    today = _today_str()

    due_items = []
    new_items = []
    other_items = []

    for vid in vocab_ids:
        row = progress.get(vid)
        if row is None:
            new_items.append(vid)
        elif row["next_review"] <= today:
            weight = 1 + row["wrong_count"] * 2
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
    return random.choice(vocab_ids)
