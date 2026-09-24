# -*- coding: utf-8 -*-
import base64
import random
import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from vocab_data import VOCAB_DATA, LEVEL_NAMES, get_vocab_by_level, get_vocab_by_id
from sound_data import CORRECT_SOUND_B64, WRONG_SOUND_B64
import db

CORRECT_SOUND_BYTES = base64.b64decode(CORRECT_SOUND_B64)
WRONG_SOUND_BYTES = base64.b64decode(WRONG_SOUND_B64)

TIME_LIMIT_SECONDS = 7
TEST_MODE_QUESTIONS = 10

st.set_page_config(page_title="日本語学習アプリ", page_icon="🇯🇵", layout="centered")
db.init_db()

# ---------------- フレンドリーな丸ゴシック系フォント ----------------
# 日本語はM PLUS Rounded 1c、ベトナム語の声調記号などはNunitoが担当する
# (1つのフォントでカバーしきれない文字は、次のフォントに自動で引き継がれる)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700&family=Nunito:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', 'Nunito', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- アカウント(ログイン・新規登録) ----------------
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

with st.sidebar:
    st.header("👤 アカウント")

    if st.session_state.auth_user is None:
        tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])

        with tab_login:
            login_email = st.text_input("メールアドレス", key="login_email")
            login_password = st.text_input("パスワード", type="password", key="login_password")
            if st.button("ログイン", use_container_width=True, type="primary"):
                try:
                    result = db.sign_in(login_email, login_password)
                    st.session_state.auth_user = result.user
                    st.rerun()
                except Exception as e:
                    st.error(f"ログインに失敗しました。メールアドレスとパスワードを確認してください。({e})")

        with tab_signup:
            signup_email = st.text_input("メールアドレス", key="signup_email")
            signup_password = st.text_input("パスワード(6文字以上)", type="password", key="signup_password")
            if st.button("アカウントを作成", use_container_width=True):
                try:
                    result = db.sign_up(signup_email, signup_password)
                    if result.session is not None:
                        # メール確認が不要な設定の場合は、そのままログイン済みにする
                        st.session_state.auth_user = result.user
                        st.rerun()
                    else:
                        st.success("登録しました。確認メールが届いていればリンクをクリックしてから、「ログイン」タブでログインしてください。")
                except Exception as e:
                    st.error(f"登録に失敗しました。({e})")

        st.caption("ログインすると学習履歴が保存され、次に来たときも続きから復習できます。")
        st.stop()

    else:
        st.success(f"ログイン中: {st.session_state.auth_user.email}")
        if st.button("ログアウト", use_container_width=True):
            db.sign_out()
            st.session_state.auth_user = None
            st.session_state.pop("supabase_client", None)
            st.session_state.pop("level_summary", None)
            st.rerun()
        user_id = st.session_state.auth_user.id

    level = st.radio(
        "📚 レベル",
        options=[1, 2, 3, 4, 5],
        format_func=lambda l: LEVEL_NAMES[l],
        key="selected_level",
    )

    mode = st.radio(
        "🎯 モード",
        options=["practice", "test"],
        format_func=lambda m: "通常モード" if m == "practice" else f"テストモード({TEST_MODE_QUESTIONS}問)",
        key="selected_mode",
    )

    st.divider()

    # レベル別の習得率は、答えるたびに更新すれば十分。
    # 毎回(1秒ごとのタイマー更新も含む)Supabaseに問い合わせるとクリックの
    # 反応が遅くなるため、st.session_stateにキャッシュしておく。
    if "level_summary" not in st.session_state:
        vocab_by_level = {lv: [v["id"] for v in get_vocab_by_level(lv)] for lv in [1, 2, 3, 4, 5]}
        st.session_state.level_summary = db.get_all_level_summary(user_id, vocab_by_level)
    summary = st.session_state.level_summary

    st.markdown(f"**{db.get_rank_title(summary['total_correct'])}**(通算正解 {summary['total_correct']})")
    for lv in [1, 2, 3, 4, 5]:
        lv_stat = summary["levels"][lv]
        st.progress(
            lv_stat["percent"] / 100,
            text=f"Lv{lv} {lv_stat['percent']}%({lv_stat['mastered']}/{lv_stat['total']})",
        )

    level_vocab = get_vocab_by_level(level)
    level_vocab_ids = [v["id"] for v in level_vocab]

# ---------------- モード/レベル切り替え時にリセット ----------------
reset_needed = (
    "current_vocab_id" not in st.session_state
    or st.session_state.get("current_level") != level
    or st.session_state.get("current_mode") != mode
)
if "streak" not in st.session_state:
    st.session_state.streak = 0  # 連続正解数(ゲーミフィケーション用、レベル切り替えでは消さない)
if "celebrated_levels" not in st.session_state:
    st.session_state.celebrated_levels = set()  # 100%お祝い済みのレベル(セッション中は再表示しない)

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
    st.session_state.play_correct_sound = False
    st.session_state.play_wrong_sound = False
    st.session_state.test_result_celebrated = False


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
        # exclude_idで直前と同じ問題を避け、連続で同じ単語が出るのを防ぐ
        vid = db.pick_next_vocab_id(user_id, vocab_ids, exclude_id=st.session_state.current_vocab_id)

    vocab_item = get_vocab_by_id(vid)
    st.session_state.current_vocab_id = vid
    st.session_state.choices = build_choices(vocab_item)
    st.session_state.answered = False
    st.session_state.selected_choice = None
    st.session_state.question_start_time = time.time()
    st.session_state.timed_out = False
    st.session_state.play_correct_sound = False
    st.session_state.play_wrong_sound = False


def start_test_mode():
    vocab_ids = [v["id"] for v in get_vocab_by_level(level)]
    # 語彙数が問題数以上あれば重複なしでシャッフル、足りない時だけ重複ありで補う
    queue = db.build_test_queue(vocab_ids, TEST_MODE_QUESTIONS)
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

    st.session_state.trigger_balloons = False
    st.session_state.play_correct_sound = False
    st.session_state.play_wrong_sound = False

    # 進捗が変わったので、キャッシュしていたレベル別習得率を更新する
    # (正解・不正解どちらでもboxが変わるため、必ず更新する。
    #  これは回答した時だけ行い、タイマーの自動更新のたびには行わない)
    vocab_by_level = {lv: [v["id"] for v in get_vocab_by_level(lv)] for lv in [1, 2, 3, 4, 5]}
    st.session_state.level_summary = db.get_all_level_summary(user_id, vocab_by_level)

    if is_correct:
        st.session_state.session_correct += 1
        st.session_state.play_correct_sound = True
        st.session_state.streak += 1
        # 連続正解5問ごとにちょっとした演出
        if st.session_state.streak % 5 == 0:
            st.session_state.trigger_balloons = True

        # そのレベルを100%習得したら、初回だけお祝いする
        level_percent = st.session_state.level_summary["levels"][level]["percent"]
        if level_percent == 100 and level not in st.session_state.celebrated_levels:
            st.session_state.celebrated_levels.add(level)
            st.session_state.trigger_balloons = True
    else:
        st.session_state.streak = 0
        st.session_state.play_wrong_sound = True

    st.session_state.answered = True
    st.session_state.selected_choice = choice
    st.session_state.timed_out = timed_out


def play_correct_sound():
    # Streamlit公式のst.audio(autoplay対応)を使うことで、
    # 手書きHTMLよりブラウザの自動再生制限を受けにくくする
    st.audio(CORRECT_SOUND_BYTES, format="audio/wav", autoplay=True)


def play_wrong_sound():
    st.audio(WRONG_SOUND_BYTES, format="audio/wav", autoplay=True)


def speak_japanese(text):
    """ブラウザ内蔵の音声読み上げ(Web Speech API)で単語を発音する。
    追加のファイルや通信は不要で、ブラウザが持っている日本語音声を使う。"""
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    st.markdown(
        f"""
        <script>
        (function() {{
            try {{
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance("{safe_text}");
                utter.lang = "ja-JP";
                utter.rate = 0.9;
                window.speechSynthesis.speak(utter);
            }} catch (e) {{}}
        }})();
        </script>
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
        if not st.session_state.get("test_result_celebrated"):
            st.balloons()
            st.session_state.test_result_celebrated = True
    elif pct >= 50:
        st.info("あと少し!間違えた単語を復習しましょう。")
    else:
        st.warning("この調子で通常モードで復習を重ねましょう。")

    if st.button("もう一度テストする", type="primary", use_container_width=True):
        start_test_mode()
        st.session_state.test_result_celebrated = False
        st.rerun()
    st.stop()

if st.session_state.current_vocab_id is None:
    st.stop()

vocab_item = get_vocab_by_id(st.session_state.current_vocab_id)

# ---------------- ゲーミフィケーション演出(連続正解・レベル制覇) ----------------
if st.session_state.get("trigger_balloons"):
    st.balloons()
    st.session_state.trigger_balloons = False

# ---------------- メイン画面 ----------------
st.subheader("🇯🇵 日本語学習アプリ")
streak = st.session_state.streak
streak_display = f" 🔥×{streak}" if streak > 0 else ""
if mode == "test":
    st.caption(f"第 {st.session_state.test_index + 1}/{TEST_MODE_QUESTIONS} 問 ・ 正解 {st.session_state.session_correct}/{st.session_state.session_total}{streak_display}")
else:
    st.caption(f"正解 {st.session_state.session_correct}/{st.session_state.session_total}{streak_display}")

# ---------------- タイマー処理 ----------------
if not st.session_state.answered:
    # debounce=True にすることで、クリックなど他の操作が起きた直後は
    # 自動更新のタイマーをリセットする。これによりクリックと自動更新が
    # 衝突して反応が鈍くなる問題を防ぐ。
    st_autorefresh(
        interval=1000,
        limit=TIME_LIMIT_SECONDS + 3,
        debounce=True,
        key=f"timer_{st.session_state.current_vocab_id}",
    )
    elapsed = time.time() - st.session_state.question_start_time
    remaining = max(0.0, TIME_LIMIT_SECONDS - elapsed)

    st.progress(remaining / TIME_LIMIT_SECONDS, text=f"⏱ 残り {remaining:0.1f} 秒")

    if remaining <= 0:
        submit_answer(None, timed_out=True)
        st.rerun()

st.markdown(f"### {vocab_item['japanese']}")
if vocab_item["reading"] != vocab_item["japanese"]:
    st.caption(f"読み方: {vocab_item['reading']}")

# 新しい問題が表示された最初の1回だけ発音する
# (タイマーの自動更新のたびに再生されると煩わしいため、発音済みかどうかを記録する)
if st.session_state.get("last_spoken_vocab_id") != st.session_state.current_vocab_id:
    speak_japanese(vocab_item["reading"])
    st.session_state.last_spoken_vocab_id = st.session_state.current_vocab_id

if not st.session_state.answered:
    for choice in st.session_state.choices:
        if st.button(choice, use_container_width=True, key=f"choice_{choice}"):
            submit_answer(choice)
            st.rerun()
else:
    if st.session_state.play_correct_sound:
        play_correct_sound()
    elif st.session_state.play_wrong_sound:
        play_wrong_sound()

    if st.session_state.timed_out:
        st.error(f"⏰ 時間切れです。正しい答えは「{vocab_item['vietnamese']}」でした。")
    elif st.session_state.selected_choice == vocab_item["vietnamese"]:
        st.success(f"✅ 正解です!「{vocab_item['japanese']}」= {vocab_item['vietnamese']}")
        if st.session_state.streak > 0 and st.session_state.streak % 5 == 0:
            st.info(f"🔥 {st.session_state.streak}問連続正解中!すごい調子です!")
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
