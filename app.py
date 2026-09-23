# -*- coding: utf-8 -*-
import random
import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from vocab_data import VOCAB_DATA, LEVEL_NAMES, get_vocab_by_level, get_vocab_by_id
from sound_data import CORRECT_SOUND_B64
import db

TIME_LIMIT_SECONDS = 7
TEST_MODE_QUESTIONS = 10

st.set_page_config(page_title="日本語学習アプリ", page_icon="🇯🇵", layout="centered")
db.init_db()

# ---------------- ユーザー識別(簡易・ログイン機能は未実装) ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = "guest"

with st.sidebar:
    st.header("👤 プロフィール")
    nickname = st.text_input("ニックネーム", value=st.session_state.user_id)
    if nickname.strip():
        st.session_state.user_id = nickname.strip()
    user_id = st.session_state.user_id

    st.divider()
    st.header("📚 レベルを選ぶ")
    level = st.radio(
        "学習レベル",
        options=[1, 2, 3, 4, 5],
        format_func=lambda l: LEVEL_NAMES[l],
        key="selected_level",
    )

    st.divider()
    st.header("🎯 モード")
    mode = st.radio(
        "学習モード",
        options=["practice", "test"],
        format_func=lambda m: "通常モード(復習しながら練習)" if m == "practice" else f"テストモード({TEST_MODE_QUESTIONS}問一本勝負)",
        key="selected_mode",
    )

    st.divider()
    level_vocab = get_vocab_by_level(level)
    level_vocab_ids = [v["id"] for v in level_vocab]
    stats = db.get_level_stats(user_id, level_vocab_ids)
    st.header("📊 このレベルの状況")
    st.metric("未学習", stats["new"])
    st.metric("学習中", stats["learning"])
    st.metric("習得済み", stats["mastered"])

    st.divider()
    st.caption(f"各問題の制限時間は{TIME_LIMIT_SECONDS}秒です。すべての機能を無料でご利用いただけます(β版)")

# ---------------- モード/レベル切り替え時にリセット ----------------
reset_needed = (
    "current_vocab_id" not in st.session_state
    or st.session_state.get("current_level") != level
    or st.session_state.get("current_mode") != mode
)
if reset_needed:
    st.session_state.current_level = level
    st.session_state.current_mode = mode
    st.session_state.current_vocab_id = None
    st.session_state.choices = None
    st.session_state.answered = False
    st.session_state.selected_choice = None
    st.session_state.session_correct = 0
    st.session_state.session_total = 0
    st.session_state.question_start_time = None
    st.session_state.timed_out = False
    st.session_state.test_queue = []
    st.session_state.test_index = 0
    st.session_state.test_finished = False
    st.session_state.play_sound = False


def build_choices(vocab_item):
    other_items = [v for v in get_vocab_by_level(level) if v["id"] != vocab_item["id"]]
    distractors = random.sample(other_items, k=min(3, len(other_items)))
    choices = [vocab_item["vietnamese"]] + [d["vietnamese"] for d in distractors]
    random.shuffle(choices)
    return choices


def load_new_question():
    if mode == "test":
        if st.session_state.test_index >= len(st.session_state.test_queue):
            st.session_state.test_finished = True
            return
        vid = st.session_state.test_queue[st.session_state.test_index]
    else:
        vocab_ids = [v["id"] for v in get_vocab_by_level(level)]
        vid = db.pick_next_vocab_id(user_id, vocab_ids)

    vocab_item = get_vocab_by_id(vid)
    st.session_state.current_vocab_id = vid
    st.session_state.choices = build_choices(vocab_item)
    st.session_state.answered = False
    st.session_state.selected_choice = None
    st.session_state.question_start_time = time.time()
    st.session_state.timed_out = False
    st.session_state.play_sound = False


def start_test_mode():
    vocab_ids = [v["id"] for v in get_vocab_by_level(level)]
    queue = [db.pick_next_vocab_id(user_id, vocab_ids) for _ in range(TEST_MODE_QUESTIONS)]
    st.session_state.test_queue = queue
    st.session_state.test_index = 0
    st.session_state.test_finished = False
    st.session_state.session_correct = 0
    st.session_state.session_total = 0
    load_new_question()


def submit_answer(choice, timed_out=False):
    vocab_item = get_vocab_by_id(st.session_state.current_vocab_id)
    is_correct = (choice == vocab_item["vietnamese"]) and not timed_out
    db.update_progress(user_id, vocab_item["id"], is_correct)
    st.session_state.session_total += 1
    if is_correct:
        st.session_state.session_correct += 1
        st.session_state.play_sound = True
    st.session_state.answered = True
    st.session_state.selected_choice = choice
    st.session_state.timed_out = timed_out


def play_correct_sound():
    # 再生のたびに一意なタグにして、同じ音でも確実に再生させる
    unique = int(time.time() * 1000)
    st.markdown(
        f"""
        <audio autoplay="true" id="sound-{unique}">
            <source src="data:audio/wav;base64,{CORRECT_SOUND_B64}" type="audio/wav">
        </audio>
        """,
        unsafe_allow_html=True,
    )


# ---------------- テストモード開始処理 ----------------
if mode == "test" and not st.session_state.test_queue and not st.session_state.test_finished:
    start_test_mode()
elif mode == "practice" and st.session_state.current_vocab_id is None:
    load_new_question()

# ---------------- テストモード終了画面 ----------------
if mode == "test" and st.session_state.test_finished:
    st.title("🇯🇵 日本語学習アプリ")
    st.header("🏁 テスト結果")
    correct = st.session_state.session_correct
    total = st.session_state.session_total
    pct = round(correct / total * 100) if total else 0
    st.metric("正解数", f"{correct} / {total}", f"{pct}%")
    if pct >= 80:
        st.success("素晴らしい!よく身についています 🎉")
    elif pct >= 50:
        st.info("あと少し!間違えた単語を復習しましょう。")
    else:
        st.warning("この調子で通常モードで復習を重ねましょう。")

    if st.button("もう一度テストする", type="primary", use_container_width=True):
        start_test_mode()
        st.rerun()
    st.stop()

if st.session_state.current_vocab_id is None:
    st.stop()

vocab_item = get_vocab_by_id(st.session_state.current_vocab_id)

# ---------------- メイン画面 ----------------
st.title("🇯🇵 日本語学習アプリ")
if mode == "test":
    st.caption(f"テストモード:第 {st.session_state.test_index + 1} / {TEST_MODE_QUESTIONS} 問")
else:
    st.caption("正しいベトナム語の意味を選んでください")

col1, col2 = st.columns(2)
col1.metric("正解数", st.session_state.session_correct)
col2.metric("回答数", st.session_state.session_total)

st.divider()

# ---------------- タイマー処理 ----------------
if not st.session_state.answered:
    st_autorefresh(interval=500, key=f"timer_{st.session_state.current_vocab_id}")
    elapsed = time.time() - st.session_state.question_start_time
    remaining = max(0.0, TIME_LIMIT_SECONDS - elapsed)

    st.progress(remaining / TIME_LIMIT_SECONDS, text=f"⏱ 残り {remaining:0.1f} 秒")

    if remaining <= 0:
        submit_answer(None, timed_out=True)
        st.rerun()

st.markdown(f"### {vocab_item['japanese']}")
if vocab_item["reading"] != vocab_item["japanese"]:
    st.caption(f"読み方: {vocab_item['reading']}")

if not st.session_state.answered:
    for choice in st.session_state.choices:
        if st.button(choice, use_container_width=True, key=f"choice_{choice}"):
            submit_answer(choice)
            st.rerun()
else:
    if st.session_state.play_sound:
        play_correct_sound()

    if st.session_state.timed_out:
        st.error(f"⏰ 時間切れです。正しい答えは「{vocab_item['vietnamese']}」でした。")
    elif st.session_state.selected_choice == vocab_item["vietnamese"]:
        st.success(f"✅ 正解です!「{vocab_item['japanese']}」= {vocab_item['vietnamese']}")
    else:
        st.error(
            f"❌ 不正解です。正しい答えは「{vocab_item['vietnamese']}」でした。"
            f"(あなたの回答: {st.session_state.selected_choice})"
        )

    button_label = "次の問題 →"
    if mode == "test":
        is_last = st.session_state.test_index + 1 >= TEST_MODE_QUESTIONS
        button_label = "結果を見る →" if is_last else "次の問題 →"

    if st.button(button_label, use_container_width=True, type="primary"):
        if mode == "test":
            st.session_state.test_index += 1
        load_new_question()
        st.rerun()

st.divider()
if mode == "practice":
    st.caption(
        "間違えた単語は間隔を空けて自動的に再出題されます。"
        "何度も間違える単語ほど出題頻度が高くなります。"
    )
else:
    st.caption(f"{TEST_MODE_QUESTIONS}問終わると結果画面が表示されます。制限時間は各問{TIME_LIMIT_SECONDS}秒です。")
