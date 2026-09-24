# -*- coding: utf-8 -*-
import base64
import random
import time

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from vocab_data import VOCAB_DATA, LEVEL_NAMES, get_vocab_by_level, get_vocab_by_id
from sound_data import CORRECT_SOUND_B64, WRONG_SOUND_B64, BGM_LOOP_B64
import db

CORRECT_SOUND_BYTES = base64.b64decode(CORRECT_SOUND_B64)
WRONG_SOUND_BYTES = base64.b64decode(WRONG_SOUND_B64)

STARTING_LIVES = 2
STARTING_TIME_LIMIT = 7.0
MIN_TIME_LIMIT = 3.0
TIME_LIMIT_STEP = 0.2       # 1問正解するごとに制限時間が縮む秒数
QUESTIONS_PER_DIFFICULTY = 5  # このスコア数ごとに、出題する単語のレベルが1つ上がる
ALL_LEVELS = [1, 2, 3, 4, 5]

st.set_page_config(page_title="日本語チャレンジ", page_icon="🇯🇵", layout="centered")
db.init_db()

# ---------------- フレンドリーな丸ゴシック系フォント ----------------
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
                        st.session_state.auth_user = result.user
                        st.rerun()
                    else:
                        st.success("登録しました。確認メールが届いていればリンクをクリックしてから、「ログイン」タブでログインしてください。")
                except Exception as e:
                    st.error(f"登録に失敗しました。({e})")

        st.caption("ログインすると学習履歴が保存されます。")
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

    st.divider()

    # レベル別の習得率は答えるたびに更新すれば十分。
    # 毎回(自動更新のたびに)Supabaseに問い合わせるとクリックの反応が
    # 遅くなるため、st.session_stateにキャッシュしておく。
    if "level_summary" not in st.session_state:
        vocab_by_level = {lv: [v["id"] for v in get_vocab_by_level(lv)] for lv in ALL_LEVELS}
        st.session_state.level_summary = db.get_all_level_summary(user_id, vocab_by_level)
    summary = st.session_state.level_summary

    st.markdown(f"**{db.get_rank_title(summary['total_correct'])}**(通算正解 {summary['total_correct']})")
    for lv in ALL_LEVELS:
        lv_stat = summary["levels"][lv]
        st.progress(
            lv_stat["percent"] / 100,
            text=f"Lv{lv} {lv_stat['percent']}%({lv_stat['learned']}/{lv_stat['total']}語)",
        )

# ---------------- セッション初期化 ----------------
if "challenge_active" not in st.session_state:
    st.session_state.challenge_active = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "celebrated_levels" not in st.session_state:
    st.session_state.celebrated_levels = set()


def current_difficulty_level(score):
    """スコアに応じて出題する単語のレベル(1〜5)を上げていく"""
    return min(5, 1 + score // QUESTIONS_PER_DIFFICULTY)


def current_time_limit(score):
    """スコアが増えるほど制限時間を短くして難しくする"""
    return max(MIN_TIME_LIMIT, STARTING_TIME_LIMIT - score * TIME_LIMIT_STEP)


def build_choices(vocab_item, pool_level):
    other_items = [v for v in get_vocab_by_level(pool_level) if v["id"] != vocab_item["id"]]
    distractors = random.sample(other_items, k=min(3, len(other_items)))
    choices = [vocab_item["vietnamese"]] + [d["vietnamese"] for d in distractors]
    random.shuffle(choices)
    return choices


def load_new_question():
    difficulty = current_difficulty_level(st.session_state.score)
    pool = [v["id"] for v in get_vocab_by_level(difficulty)]
    prev = st.session_state.get("current_vocab_id")
    candidates = [v for v in pool if v != prev] or pool
    vid = random.choice(candidates)

    vocab_item = get_vocab_by_id(vid)
    st.session_state.current_vocab_id = vid
    st.session_state.current_difficulty = difficulty
    st.session_state.choices = build_choices(vocab_item, difficulty)
    st.session_state.answered = False
    st.session_state.selected_choice = None
    st.session_state.question_time_limit = current_time_limit(st.session_state.score)
    st.session_state.question_start_time = time.time()
    st.session_state.timed_out = False
    st.session_state.play_correct_sound = False
    st.session_state.play_wrong_sound = False


def start_challenge():
    st.session_state.challenge_active = True
    st.session_state.game_over = False
    st.session_state.lives = STARTING_LIVES
    st.session_state.score = 0
    st.session_state.last_spoken_vocab_id = None
    load_new_question()


def submit_answer(choice, timed_out=False):
    vocab_item = get_vocab_by_id(st.session_state.current_vocab_id)
    is_correct = (choice == vocab_item["vietnamese"]) and not timed_out
    db.update_progress(user_id, vocab_item["id"], is_correct)

    st.session_state.trigger_balloons = False
    st.session_state.play_correct_sound = False
    st.session_state.play_wrong_sound = False

    # 進捗が変わったので、キャッシュしていたレベル別習得率を更新する
    vocab_by_level = {lv: [v["id"] for v in get_vocab_by_level(lv)] for lv in ALL_LEVELS}
    st.session_state.level_summary = db.get_all_level_summary(user_id, vocab_by_level)

    if is_correct:
        st.session_state.score += 1
        st.session_state.play_correct_sound = True
        if st.session_state.score % 5 == 0:
            st.session_state.trigger_balloons = True

        difficulty = st.session_state.current_difficulty
        level_percent = st.session_state.level_summary["levels"][difficulty]["percent"]
        if level_percent == 100 and difficulty not in st.session_state.celebrated_levels:
            st.session_state.celebrated_levels.add(difficulty)
            st.session_state.trigger_balloons = True
    else:
        st.session_state.lives -= 1
        st.session_state.play_wrong_sound = True
        if st.session_state.lives <= 0:
            st.session_state.game_over = True
            st.session_state.challenge_active = False

    st.session_state.answered = True
    st.session_state.selected_choice = choice
    st.session_state.timed_out = timed_out


def play_correct_sound():
    st.audio(CORRECT_SOUND_BYTES, format="audio/wav", autoplay=True)


def play_wrong_sound():
    st.audio(WRONG_SOUND_BYTES, format="audio/wav", autoplay=True)


def play_bgm():
    """
    チャレンジ中はずっと同じ内容のコンポーネントを描画し続けることで、
    自動更新(1秒ごとの再実行)のたびにBGMが最初から再生し直されるのを防ぎ、
    ループがシームレスに鳴り続けるようにする。
    """
    components.html(
        f"""
        <audio autoplay loop>
            <source src="data:audio/wav;base64,{BGM_LOOP_B64}" type="audio/wav">
        </audio>
        """,
        height=0,
    )


def speak_japanese(text):
    """ブラウザ内蔵の音声読み上げ(Web Speech API)で単語を発音する。
    st.markdownで<script>を入れてもブラウザは実行しない(innerHTML経由のscriptは
    セキュリティ上無視される)ため、components.htmlでiframeとして描画する。"""
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
    components.html(
        f"""
        <script>
        try {{
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance("{safe_text}");
            utter.lang = "ja-JP";
            utter.rate = 0.9;
            window.speechSynthesis.speak(utter);
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


# ==================== スタート画面 ====================
if not st.session_state.challenge_active and not st.session_state.game_over:
    st.title("🇯🇵 日本語チャレンジ")
    st.markdown(
        f"""
        - ❤️ ライフは **{STARTING_LIVES}つ**。間違えるかタイムアウトすると1つ減ります
        - ライフが0になったら **ゲームオーバー**
        - 正解を重ねるほど、単語のレベルも制限時間もどんどん難しくなります
        """
    )
    if st.button("▶ チャレンジスタート", type="primary", use_container_width=True):
        start_challenge()
        st.rerun()
    st.stop()

# ==================== ゲームオーバー画面 ====================
if st.session_state.game_over:
    st.title("🇯🇵 日本語チャレンジ")
    st.header("💀 ゲームオーバー")
    st.metric("最終スコア", f"{st.session_state.score} 問正解")
    reached = current_difficulty_level(st.session_state.score)
    st.caption(f"到達レベル: {LEVEL_NAMES[reached]}")

    if not st.session_state.get("game_over_celebrated"):
        if st.session_state.score >= 10:
            st.balloons()
        st.session_state.game_over_celebrated = True

    if st.button("🔁 もう一度挑戦する", type="primary", use_container_width=True):
        st.session_state.game_over_celebrated = False
        start_challenge()
        st.rerun()
    st.stop()

# ==================== チャレンジ本編 ====================
vocab_item = get_vocab_by_id(st.session_state.current_vocab_id)

play_bgm()

if st.session_state.get("trigger_balloons"):
    st.balloons()
    st.session_state.trigger_balloons = False

st.title("🇯🇵 日本語チャレンジ")

hearts = "❤️" * st.session_state.lives + "🖤" * (STARTING_LIVES - st.session_state.lives)
st.markdown(f"### {hearts}")
st.caption(f"スコア: {st.session_state.score} 問正解 ・ 出題レベル: {LEVEL_NAMES[st.session_state.current_difficulty]}")

# ---------------- タイマー処理 ----------------
if not st.session_state.answered:
    st_autorefresh(
        interval=1000,
        limit=int(st.session_state.question_time_limit) + 3,
        debounce=True,
        key=f"timer_{st.session_state.current_vocab_id}_{st.session_state.score}",
    )
    limit = st.session_state.question_time_limit
    elapsed = time.time() - st.session_state.question_start_time
    remaining = max(0.0, limit - elapsed)

    st.progress(remaining / limit, text=f"⏱ 残り {remaining:0.1f} 秒")

    if remaining <= 0:
        submit_answer(None, timed_out=True)
        st.rerun()

st.markdown(f"## {vocab_item['japanese']}")
if vocab_item["reading"] != vocab_item["japanese"]:
    st.caption(f"読み方: {vocab_item['reading']}")

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
        st.error(f"⏰ 時間切れ!正しい答えは「{vocab_item['vietnamese']}」でした。")
    elif st.session_state.selected_choice == vocab_item["vietnamese"]:
        st.success(f"✅ 正解!「{vocab_item['japanese']}」= {vocab_item['vietnamese']}")
    else:
        st.error(
            f"❌ 不正解。正しい答えは「{vocab_item['vietnamese']}」でした。"
            f"(あなたの回答: {st.session_state.selected_choice})"
        )

    if st.session_state.game_over:
        if st.button("結果を見る →", use_container_width=True, type="primary"):
            st.rerun()
    else:
        if st.button("次の問題 →", use_container_width=True, type="primary"):
            load_new_question()
            st.rerun()
