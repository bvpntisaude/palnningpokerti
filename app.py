import streamlit as st
import time
import statistics
import os
import base64
from database import (
    init_db, create_room, get_room, update_room_status, update_room_story,
    reset_round, add_player, get_players, heartbeat, remove_inactive_players,
    cast_vote, get_votes,
)

st.set_page_config(
    page_title="Planning Poker · Ti.Saúde",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

CARDS = ["0", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89", "?", "☕"]

# ── session state ──────────────────────────────────────────────────────────────
def ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default

ss("room_id", None)
ss("player_id", None)
ss("player_name", None)
ss("is_moderator", False)
ss("selected_card", None)
ss("home_tab", "criar")
ss("theme", "dark")

# ── tema ───────────────────────────────────────────────────────────────────────
DARK = {
    "bg":       "#0f1117",
    "card":     "#1e2130",
    "surface":  "#161925",
    "text":     "#f0f2f6",
    "muted":    "#889",
    "border":   "rgba(43,191,170,.2)",
    "radio_bg": "rgba(255,255,255,.04)",
    "input_bg": "#1e2130",
}
LIGHT = {
    "bg":       "#f0f4f8",
    "card":     "#ffffff",
    "surface":  "#ffffff",
    "text":     "#1a1a2e",
    "muted":    "#667",
    "border":   "rgba(43,191,170,.35)",
    "radio_bg": "rgba(0,0,0,.05)",
    "input_bg": "#f8f9fb",
}
T = LIGHT if st.session_state.theme == "light" else DARK

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

:root {{
    --teal:   #2BBFAA;
    --purple: #7B3FA0;
    --bg:     {T['bg']};
    --card:   {T['card']};
    --surface:{T['surface']};
    --text:   {T['text']};
    --muted:  {T['muted']};
    --border: {T['border']};
}}

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main {{
    background: var(--bg) !important;
    font-family: 'Poppins', sans-serif !important;
    color: var(--text) !important;
}}
[data-testid="stHeader"]      {{ background: transparent !important; }}
[data-testid="stSidebar"]     {{ background: var(--surface) !important; }}
#MainMenu, footer, header     {{ visibility: hidden; }}

/* ── image center ── */
[data-testid="stImage"] {{
    display: flex !important;
    justify-content: center !important;
}}
[data-testid="stImage"] img {{
    display: block !important;
    margin: 0 auto !important;
}}

/* ── container card (border=True) ── */
[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 2rem 2.2rem !important;
    box-shadow: 0 20px 50px rgba(0,0,0,.35) !important;
    width: 100% !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}}

/* neutraliza margens negativas das colunas dentro do card */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {{
    margin-left: 0 !important;
    margin-right: 0 !important;
    gap: 8px !important;
}}

/* ── radio pill switch ── */
div[data-testid="stRadio"] > label {{ display: none !important; }}

div[data-testid="stRadio"] {{
    width: 100% !important;
    box-sizing: border-box !important;
}}

div[role="radiogroup"] {{
    display: flex !important;
    width: 100% !important;
    box-sizing: border-box !important;
    background: {T['radio_bg']} !important;
    border-radius: 12px !important;
    padding: 4px !important;
    border: 1px solid rgba(128,128,128,.2) !important;
    gap: 0 !important;
}}

label[data-baseweb="radio"] {{
    flex: 1 !important;
    justify-content: center !important;
    border-radius: 9px !important;
    padding: .52rem .2rem !important;
    margin: 0 !important;
    font-weight: 700 !important;
    font-size: .85rem !important;
    transition: all .2s !important;
    color: {T['muted']} !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    text-align: center !important;
    min-width: 0 !important;
}}
label[data-baseweb="radio"]:has(input:checked) {{
    background: linear-gradient(135deg, var(--teal), var(--purple)) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(43,191,170,.3) !important;
}}
/* oculta o círculo do radio (primeiro div dentro do label) */
label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
label[data-baseweb="radio"] input[type="radio"]  {{ display: none !important; }}

/* ── inputs ── */
div[data-baseweb="input"] input, div[data-baseweb="base-input"] input,
input[type="text"] {{
    background: {T['input_bg']} !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    font-family: 'Poppins', sans-serif !important;
}}
div[data-baseweb="input"] {{ background: {T['input_bg']} !important; border-radius: 10px !important; }}

/* ── labels ── */
label[data-testid="stWidgetLabel"] p {{ color: var(--text) !important; font-weight: 600 !important; }}

/* ── botões de ação (primary) — gradiente ── */
button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, var(--teal), var(--purple)) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
    font-family: 'Poppins', sans-serif !important;
    transition: opacity .2s !important;
}}
button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{ opacity: .85 !important; }}

/* ── cartas (secondary) — estilo poker — só dentro do .poker-zone ── */
.poker-zone + [data-testid="stHorizontalBlock"] button[kind="secondary"],
.poker-zone + [data-testid="stHorizontalBlock"] button[data-testid="baseButton-secondary"] {{
    background: var(--card) !important;
    color: var(--text) !important;
    border: 2px solid rgba(43,191,170,.35) !important;
    border-radius: 12px !important;
    font-size: 1.3rem !important; font-weight: 800 !important;
    font-family: 'Poppins', sans-serif !important;
    min-height: 80px !important;
    transition: all .22s ease !important;
    box-shadow: 0 3px 10px rgba(0,0,0,.25) !important;
    padding: 0 !important;
}}
.poker-zone + [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    border-color: var(--teal) !important;
    background: rgba(43,191,170,.08) !important;
    transform: translateY(-6px) scale(1.06) !important;
    box-shadow: 0 10px 22px rgba(43,191,170,.3) !important;
    color: var(--teal) !important;
}}

/* ── tab switch dentro do card home ── */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button[kind="primary"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    min-height: 40px !important;
    max-height: 40px !important;
    height: 40px !important;
    font-size: .85rem !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    padding: 0 .8rem !important;
    box-shadow: none !important;
    transform: none !important;
    line-height: 1 !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button[kind="secondary"] {{
    border: 1.5px solid rgba(128,128,128,.3) !important;
    background: transparent !important;
    color: {T['muted']} !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
    background: rgba(43,191,170,.08) !important;
    border-color: var(--teal) !important;
    color: var(--teal) !important;
}}

/* ── room code ── */
.room-code {{
    display: inline-block;
    background: linear-gradient(135deg, var(--teal), var(--purple));
    color: #fff; font-size: 1.8rem; font-weight: 800;
    letter-spacing: .3rem; padding: .35rem 1.6rem;
    border-radius: 12px; margin: .4rem 0;
}}

/* ── story box ── */
.story-box {{
    background: linear-gradient(135deg,rgba(43,191,170,.12),rgba(123,63,160,.12));
    border: 1px solid rgba(43,191,170,.3);
    border-radius: 12px; padding: 1rem 1.4rem;
    font-size: 1.1rem; font-weight: 600;
    text-align: center; margin-bottom: 1.2rem;
    color: var(--text);
}}

/* ── poker cards ── */
.poker-card {{
    width: 68px; height: 100px;
    background: var(--card);
    border: 2px solid rgba(43,191,170,.3);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; font-weight: 800; color: var(--text);
    cursor: pointer; transition: all .2s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
    user-select: none;
}}
.poker-card:hover {{
    border-color: var(--teal);
    transform: translateY(-8px) scale(1.06);
    box-shadow: 0 10px 24px rgba(43,191,170,.35);
}}
.poker-card.selected {{
    background: linear-gradient(135deg, var(--teal), var(--purple));
    border-color: transparent;
    transform: translateY(-10px) scale(1.08);
    box-shadow: 0 12px 28px rgba(43,191,170,.5);
    color: #fff;
}}

/* ── player row ── */
.player-row {{
    display: flex; align-items: center; gap: .7rem;
    background: var(--card);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 12px; padding: .6rem .9rem; margin-bottom: .45rem;
    color: var(--text);
}}
.avatar {{
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, var(--teal), var(--purple));
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: .85rem; color: #fff; flex-shrink: 0;
}}
.voted-badge {{
    background: rgba(43,191,170,.15); border: 1px solid var(--teal);
    color: var(--teal); border-radius: 8px;
    padding: .1rem .5rem; font-size: .75rem; font-weight: 600;
}}
.waiting-badge {{
    background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.12);
    color: #777; border-radius: 8px;
    padding: .1rem .5rem; font-size: .75rem;
}}

/* ── reveal card ── */
.reveal-card {{
    background: linear-gradient(135deg, var(--teal), var(--purple));
    border-radius: 14px; padding: 1.1rem .7rem;
    text-align: center;
    box-shadow: 0 6px 20px rgba(43,191,170,.3);
    margin-bottom: .5rem;
}}
.reveal-card .rv {{ font-size: 1.9rem; font-weight: 800; color: #fff; }}
.reveal-card .rn {{ font-size: .75rem; color: rgba(255,255,255,.8); margin-top: .2rem; }}

/* ── stat box ── */
.stat-box {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 1.1rem;
    text-align: center; color: var(--text);
}}
.stat-val {{
    font-size: 2rem; font-weight: 800;
    background: linear-gradient(90deg, var(--teal), var(--purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.stat-lbl {{ font-size: .78rem; color: var(--muted); margin-top: .15rem; }}
</style>
""", unsafe_allow_html=True)


# ── helpers ────────────────────────────────────────────────────────────────────
def numeric_votes(votes):
    nums = []
    for v in votes:
        try:
            nums.append(float(v["vote"]))
        except (ValueError, TypeError):
            pass
    return nums


def show_logo(width=140):
    for name in ["Logo_Ti.Saude_Vertical.png", "logo.png", "Logo.png"]:
        if os.path.exists(name):
            st.image(name, width=width)
            return


def logo_b64():
    for name in ["Logo_Ti.Saude_Vertical.png", "logo.png", "Logo.png"]:
        if os.path.exists(name):
            with open(name, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


# ── home page ──────────────────────────────────────────────────────────────────
def page_home():
    # ── tema toggle ────────────────────────────────────────────────────────────
    _, col_btn = st.columns([9, 1])
    with col_btn:
        icon  = "☀️" if st.session_state.theme == "dark" else "🌙"
        label = f"{icon} {'Claro' if st.session_state.theme == 'dark' else 'Escuro'}"
        if st.button(label, key="theme_toggle", use_container_width=True, type="primary"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()

    # ── card centralizado (SEM colunas internas) ───────────────────────────────
    _, center, _ = st.columns([1, 1.6, 1])
    with center:
        with st.container(border=True):

            # logo — base64 embed para controle total de centralização
            _b64 = logo_b64()
            if _b64:
                st.markdown(
                    f"<div style='text-align:center;margin-bottom:.6rem'>"
                    f"<img src='data:image/png;base64,{_b64}' style='width:120px;height:auto'>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # título e subtítulo
            st.markdown(
                "<div style='text-align:center;font-size:1.55rem;font-weight:800;"
                "margin:.5rem 0 .2rem;"
                "background:linear-gradient(90deg,#2BBFAA,#7B3FA0);"
                "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
                "Planning Poker</div>"
                "<div style='text-align:center;font-size:.83rem;margin-bottom:1.5rem;"
                f"color:{T['muted']};'>"
                "Estime histórias de forma colaborativa e divertida</div>",
                unsafe_allow_html=True,
            )

            # ── pill switch (dois botões lado a lado) ──────────────────────────
            t1, t2 = st.columns(2, gap="small")
            with t1:
                if st.button("🚀 Criar sala",
                             use_container_width=True,
                             key="tab_criar",
                             type="primary" if st.session_state.home_tab == "criar" else "secondary"):
                    st.session_state.home_tab = "criar"
                    st.rerun()
            with t2:
                if st.button("🔗 Entrar na sala",
                             use_container_width=True,
                             key="tab_entrar",
                             type="primary" if st.session_state.home_tab == "entrar" else "secondary"):
                    st.session_state.home_tab = "entrar"
                    st.rerun()

            st.markdown("<div style='margin-top:.4rem'></div>", unsafe_allow_html=True)

            # ── formulário criar ───────────────────────────────────────────────
            if st.session_state.home_tab == "criar":
                room_name = st.text_input("Nome da sala", placeholder="Sprint 42 – Ti.Saúde",
                                          key="new_room_name")
                mod_name  = st.text_input("Seu nome (moderador)", placeholder="João Silva",
                                          key="mod_name")
                if st.button("Criar e entrar →", use_container_width=True,
                             key="btn_criar", type="primary"):
                    if room_name.strip() and mod_name.strip():
                        room_id   = create_room(room_name.strip())
                        player_id = add_player(room_id, mod_name.strip(), is_moderator=True)
                        st.session_state.room_id       = room_id
                        st.session_state.player_id     = player_id
                        st.session_state.player_name   = mod_name.strip()
                        st.session_state.is_moderator  = True
                        st.session_state.selected_card = None
                        st.rerun()
                    else:
                        st.warning("Preencha o nome da sala e o seu nome.")

            # ── formulário entrar ──────────────────────────────────────────────
            else:
                join_code = st.text_input("Código da sala", placeholder="ABC12345",
                                          key="join_code", max_chars=8).upper()
                join_name = st.text_input("Seu nome", placeholder="Maria Costa",
                                          key="join_name")
                if st.button("Entrar na sala →", use_container_width=True,
                             key="btn_entrar", type="primary"):
                    if join_code.strip() and join_name.strip():
                        room = get_room(join_code.strip())
                        if room:
                            player_id = add_player(join_code.strip(), join_name.strip())
                            st.session_state.room_id       = join_code.strip()
                            st.session_state.player_id     = player_id
                            st.session_state.player_name   = join_name.strip()
                            st.session_state.is_moderator  = False
                            st.session_state.selected_card = None
                            st.rerun()
                        else:
                            st.error("Sala não encontrada. Verifique o código.")
                    else:
                        st.warning("Preencha o código e o seu nome.")


# ── room page ──────────────────────────────────────────────────────────────────
def page_room():
    room_id   = st.session_state.room_id
    player_id = st.session_state.player_id
    is_mod    = st.session_state.is_moderator

    heartbeat(player_id)
    remove_inactive_players(room_id)

    room      = get_room(room_id)
    players   = get_players(room_id)
    votes     = get_votes(room_id)
    voted_ids = {v["player_id"] for v in votes}
    my_vote   = next((v["vote"] for v in votes if v["player_id"] == player_id), None)

    if my_vote:
        st.session_state.selected_card = my_vote

    # ── header ─────────────────────────────────────────────────────────────────
    h1, h2, h3, h4 = st.columns([1, 4, 1, 1])
    with h1:
        show_logo(width=100)
    with h2:
        st.markdown(f"""
        <div style="padding:.5rem 0">
            <div style="font-size:.8rem;color:#aab">Sala</div>
            <span class="room-code">{room_id}</span>
            <span style="margin-left:.8rem;font-size:1rem;font-weight:600">{room['name']}</span>
        </div>
        """, unsafe_allow_html=True)
    with h3:
        icon = "☀️" if st.session_state.theme == "dark" else "🌙"
        if st.button(icon, key="theme_room", use_container_width=True):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
    with h4:
        if st.button("↩ Sair", key="btn_sair", use_container_width=True):
            for k in ["room_id", "player_id", "player_name", "selected_card"]:
                st.session_state[k] = None
            st.session_state.is_moderator = False
            st.rerun()

    st.divider()

    story = room.get("current_story", "") or ""
    if story:
        st.markdown(f'<div class="story-box">📋 {story}</div>', unsafe_allow_html=True)

    # ── moderador ──────────────────────────────────────────────────────────────
    if is_mod:
        with st.expander("⚙️ Controles do moderador", expanded=(room["status"] == "waiting")):
            new_story = st.text_input("História / tarefa", value=story,
                                       placeholder="Ex: Implementar tela de login", key="mod_story")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("▶️ Iniciar votação", use_container_width=True, type="primary"):
                    if new_story.strip():
                        update_room_story(room_id, new_story.strip())
                        st.session_state.selected_card = None
                        st.rerun()
                    else:
                        st.warning("Adicione uma história.")
            with c2:
                if st.button("👁️ Revelar cartas", use_container_width=True, type="primary"):
                    update_room_status(room_id, "revealed")
                    st.rerun()
            with c3:
                if st.button("🔄 Nova rodada", use_container_width=True, type="primary"):
                    reset_round(room_id)
                    st.session_state.selected_card = None
                    st.rerun()

    # ── colunas principais ─────────────────────────────────────────────────────
    col_cards, col_players = st.columns([3, 1], gap="large")

    with col_cards:
        if room["status"] in ("voting", "waiting"):
            st.markdown("### 🃏 Escolha sua carta")
            if not story:
                st.info("Aguardando o moderador iniciar a votação...")
            else:
                st.markdown('<div class="poker-zone"></div>', unsafe_allow_html=True)
                card_cols = st.columns(len(CARDS))
                for idx, card in enumerate(CARDS):
                    with card_cols[idx]:
                        selected = st.session_state.selected_card == card
                        if st.button(
                            "✓" if selected else card,
                            key=f"card_{card}",
                            use_container_width=True,
                            type="primary" if selected else "secondary",
                        ):
                            st.session_state.selected_card = card
                            cast_vote(room_id, player_id, card)
                            st.rerun()

                if st.session_state.selected_card:
                    st.markdown(f"""
                    <div style="text-align:center;margin-top:1.2rem">
                        <div style="display:inline-block;background:linear-gradient(135deg,#2BBFAA,#7B3FA0);
                            border-radius:16px;padding:1.2rem 2.2rem">
                            <div style="font-size:2.8rem;font-weight:800;color:#fff">
                                {st.session_state.selected_card}
                            </div>
                            <div style="color:rgba(255,255,255,.8);font-size:.85rem;margin-top:.2rem">
                                sua escolha ✓
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        elif room["status"] == "revealed":
            st.markdown("### 🎉 Resultado")
            if votes:
                cols = st.columns(min(len(votes), 5))
                for i, v in enumerate(votes):
                    with cols[i % min(len(votes), 5)]:
                        st.markdown(f"""
                        <div class="reveal-card">
                            <div class="rv">{v['vote'] or '?'}</div>
                            <div class="rn">{v['name']}</div>
                        </div>
                        """, unsafe_allow_html=True)

            nums = numeric_votes(votes)
            if nums:
                avg  = round(sum(nums) / len(nums), 1)
                med  = statistics.median(nums)
                mode = statistics.mode(nums) if len(nums) >= 2 else nums[0]
                cons = max(nums) - min(nums) <= 2

                st.markdown("<br>", unsafe_allow_html=True)
                s1, s2, s3, s4 = st.columns(4)
                for col, val, lbl in [
                    (s1, avg, "Média"), (s2, med, "Mediana"),
                    (s3, mode, "Moda"),  (s4, "✅" if cons else "⚠️", "Consenso" if cons else "Divergência"),
                ]:
                    with col:
                        st.markdown(f'<div class="stat-box"><div class="stat-val">{val}</div>'
                                    f'<div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                if cons:
                    st.success(f"🎉 Consenso! Estimativa: **{mode}** pontos.")
                else:
                    st.warning("Divergência nas estimativas. Discuta e vote novamente! 💬")

    with col_players:
        voted_count = len(voted_ids)
        total       = len(players)
        st.markdown(f"### 👥 Jogadores ({voted_count}/{total})")

        for p in players:
            did_vote = p["id"] in voted_ids
            badge    = '<span class="voted-badge">✓ votou</span>' if did_vote else '<span class="waiting-badge">aguardando</span>'
            initials = "".join(w[0].upper() for w in p["name"].split()[:2])
            mod_icon = " 👑" if p["is_moderator"] else ""
            st.markdown(f"""
            <div class="player-row">
                <div class="avatar">{initials}</div>
                <span style="flex:1;font-weight:600">{p['name']}{mod_icon}</span>
                {badge}
            </div>
            """, unsafe_allow_html=True)

        if total > 0:
            pct = int(voted_count / total * 100)
            st.markdown(f"""
            <div style="margin-top:.8rem;font-size:.78rem;color:#aab;margin-bottom:.3rem">
                Progresso: {pct}%
            </div>
            <div style="background:#1e2130;border-radius:8px;height:8px;overflow:hidden">
                <div style="width:{pct}%;height:100%;
                    background:linear-gradient(90deg,#2BBFAA,#7B3FA0);
                    border-radius:8px;transition:width .4s">
                </div>
            </div>
            """, unsafe_allow_html=True)

        if voted_count == total and total > 0 and room["status"] == "voting" and is_mod:
            st.markdown("<br>", unsafe_allow_html=True)
            st.success("Todos votaram! 🎉")
            if st.button("👁️ Revelar agora", use_container_width=True, key="reveal_all", type="primary"):
                update_room_status(room_id, "revealed")
                st.rerun()

    st.markdown('<div style="text-align:center;font-size:.72rem;color:#444;margin-top:1rem">⟳ atualiza a cada 3s</div>',
                unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()


# ── router ─────────────────────────────────────────────────────────────────────
if st.session_state.room_id and st.session_state.player_id:
    page_room()
else:
    page_home()
