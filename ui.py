"""Identidade visual: estilos, ícones e blocos de HTML do Amigo Secreto Conectado."""
import base64
import html
import json
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components

RED = "#C62828"
GREEN = "#0E7C59"
GOLD = "#D4A017"
CREAM = "#FFF8E6"
NAVY = "#1F2937"

_ICON_PATHS = {
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "crown": '<path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"/><path d="M5 21h14"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "shuffle": '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22"/><path d="m18 2 4 4-4 4"/><path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2"/><path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"/><path d="m18 14 4 4-4 4"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "door": '<path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h3"/><path d="M13 20h9"/><path d="M10 12v.01"/><path d="M13 4.562v16.157a1 1 0 0 1-1.242.97L5 20V5.562a2 2 0 0 1 1.515-1.94l4-1A2 2 0 0 1 13 4.561Z"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
}

LOGO_SVG = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="{RED}"/>
  <path d="M10 43 Q32 62 54 43" stroke="#FFE7A3" stroke-width="2" fill="none"/>
  <circle cx="10" cy="43" r="4.2" fill="{CREAM}" stroke="#FFE7A3" stroke-width="1.5"/>
  <circle cx="54" cy="43" r="4.2" fill="{CREAM}" stroke="#FFE7A3" stroke-width="1.5"/>
  <circle cx="32" cy="54" r="4.2" fill="{CREAM}" stroke="#FFE7A3" stroke-width="1.5"/>
  <rect x="18" y="26" width="28" height="21" rx="3" fill="{CREAM}"/>
  <rect x="15" y="20" width="34" height="8" rx="2" fill="#FFFFFF"/>
  <rect x="30" y="20" width="4" height="27" fill="{GOLD}"/>
  <path d="M32 20 C26 11 18 13 23 19 Z" fill="{GOLD}"/>
  <path d="M32 20 C38 11 46 13 41 19 Z" fill="{GOLD}"/>
  <rect x="26.5" y="34" width="11" height="8.5" rx="1.8" fill="{RED}"/>
  <path d="M29 34 v-2.6 a3 3 0 0 1 6 0 V34" stroke="{RED}" stroke-width="1.9" fill="none"/>
  <circle cx="32" cy="38" r="1.3" fill="{CREAM}"/>
  <path d="M48 9 l1.2 2.8 2.8 1.2 -2.8 1.2 -1.2 2.8 -1.2 -2.8 -2.8 -1.2 2.8 -1.2z" fill="#FFE7A3"/>
</svg>
"""

CSS = f"""
<style>
.stApp {{
  background:
    radial-gradient(circle at 12% 18%, rgba(255,255,255,.9) 0 2px, transparent 3px),
    radial-gradient(circle at 78% 8%, rgba(255,255,255,.9) 0 2px, transparent 3px),
    radial-gradient(circle at 92% 46%, rgba(255,255,255,.9) 0 2px, transparent 3px),
    radial-gradient(circle at 4% 72%, rgba(255,255,255,.9) 0 2px, transparent 3px),
    linear-gradient(180deg, #FFF3DC 0%, {CREAM} 40%, #FFFBF1 100%);
  background-attachment: fixed;
}}
.stApp::before {{
  content: ""; position: fixed; top: 0; left: 0; right: 0; height: 6px; z-index: 1000;
  background: repeating-linear-gradient(90deg, {RED} 0 40px, {GOLD} 40px 52px, {GREEN} 52px 92px, {GOLD} 92px 104px);
}}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1120px; padding-top: 3.5rem; padding-bottom: 3rem; }}
[data-testid="stForm"] {{ border: none; padding: 0; }}

/* Cabeçalho */
.asc-hero {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 8px; }}
.asc-brand {{ display: flex; align-items: center; gap: 18px; }}
.asc-logo {{ width: 88px; height: 88px; flex: none; filter: drop-shadow(0 8px 16px rgba(198,40,40,.25)); }}
.asc-title {{ font-size: 2.6rem; font-weight: 900; line-height: 1; color: {NAVY}; letter-spacing: -0.02em; margin: 0; }}
.asc-pill {{ display: inline-block; margin-top: 8px; background: {RED}; color: #fff; font-weight: 900; font-size: 1.7rem;
  padding: 4px 20px 6px; border-radius: 999px; transform: rotate(-2deg); box-shadow: 0 6px 14px rgba(198,40,40,.3), inset 0 -3px 0 rgba(0,0,0,.12); }}
.asc-tagline {{ max-width: 430px; }}
.asc-steps {{ display: inline-block; border: 2px solid rgba(198,40,40,.25); background: #fff; color: {RED}; font-weight: 800;
  border-radius: 999px; padding: 6px 18px; font-size: 1rem; }}
.asc-tagline p {{ margin: 10px 4px 0; color: #4B5563; font-size: 1.05rem; }}
.asc-hero.compact .asc-logo {{ width: 56px; height: 56px; }}
.asc-hero.compact .asc-title {{ font-size: 1.6rem; }}
.asc-hero.compact .asc-pill {{ font-size: 1.05rem; padding: 2px 14px 4px; margin-top: 4px; }}

/* Cartões */
[class*="st-key-card_"] {{
  background: #FFFFFF; border: 1px solid #F1E3C4; border-radius: 20px; padding: 1.4rem 1.4rem 1.2rem;
  box-shadow: 0 10px 28px rgba(120, 72, 0, .08); border-top: 5px solid {RED};
}}
.st-key-card_join, .st-key-card_guest, .st-key-card_invite {{ border-top-color: {GREEN}; background: linear-gradient(180deg, #F3FBF6 0, #fff 120px); }}
.st-key-card_admin, .st-key-card_panel {{ border-top-color: {GOLD}; background: linear-gradient(180deg, #FFF9E8 0, #fff 120px); }}
.st-key-card_create {{ background: linear-gradient(180deg, #FFF4F2 0, #fff 120px); }}
.asc-card-head {{ display: flex; gap: 14px; align-items: center; margin-bottom: 4px; }}
.asc-icon {{ width: 46px; height: 46px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex: none; }}
.asc-icon img {{ width: 24px; height: 24px; }}
.asc-icon.red {{ background: #FDECEA; color: {RED}; }}
.asc-icon.green {{ background: #E3F4EC; color: {GREEN}; }}
.asc-icon.gold {{ background: #FBF0D2; color: #A57C0B; }}
.asc-card-head h3 {{ margin: 0; padding: 0; font-size: 1.35rem; font-weight: 800; color: {NAVY}; }}
.asc-card-head p {{ margin: 2px 0 0; color: #6B7280; font-size: .92rem; }}

/* Botão verde de participar */
.st-key-card_guest button[kind^="primary"], .st-key-card_join button[kind^="primary"] {{
  background: {GREEN}; border-color: {GREEN};
}}
.st-key-card_guest button[kind^="primary"]:hover, .st-key-card_join button[kind^="primary"]:hover {{
  background: #0B6649; border-color: #0B6649; color: #fff;
}}

/* Indicadores do painel */
.asc-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 14px 0 6px; }}
.asc-stat {{ border-radius: 16px; padding: 14px 10px; text-align: center; border: 1px solid rgba(0,0,0,.04); }}
.asc-stat img {{ width: 24px; height: 24px; }}
.asc-stat .v {{ font-size: 1.35rem; font-weight: 900; color: {NAVY}; margin-top: 4px; line-height: 1.2; }}
.asc-stat .l {{ font-size: .85rem; color: #6B7280; }}
.asc-stat.green {{ background: #EEF8F2; color: {GREEN}; }}
.asc-stat.gold {{ background: #FFF6DF; color: #A57C0B; }}
.asc-stat.red {{ background: #FDEFEC; color: {RED}; }}

/* Convite */
.asc-share {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 6px 0 14px; }}
.asc-share a {{ display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 999px; font-weight: 800;
  text-decoration: none !important; color: #fff !important; font-size: .95rem; box-shadow: 0 4px 10px rgba(0,0,0,.1); transition: transform .15s; }}
.asc-share a:hover {{ transform: translateY(-2px); }}
.asc-share .wa {{ background: {GREEN}; }}
.asc-share .fb {{ background: #1F4E9C; }}
.asc-share .tw {{ background: {NAVY}; }}
.asc-share .tg {{ background: #1A8AC4; }}

/* Participantes */
.asc-people {{ display: flex; flex-direction: column; gap: 8px; margin: 8px 0; }}
.asc-person {{ display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 14px; background: {CREAM}; }}
.asc-avatar {{ width: 34px; height: 34px; border-radius: 50%; background: {RED}; color: #fff; font-weight: 800; display: flex; align-items: center; justify-content: center; flex: none; }}
.asc-person:nth-child(3n+2) .asc-avatar {{ background: {GREEN}; }}
.asc-person:nth-child(3n) .asc-avatar {{ background: {GOLD}; }}
.asc-person > div:last-child {{ min-width: 0; display: flex; flex-direction: column; }}
.asc-person b {{ color: {NAVY}; overflow-wrap: anywhere; }}
.asc-person span {{ color: #6B7280; font-size: .85rem; overflow-wrap: anywhere; }}

/* Avisos */
.asc-note {{ border-radius: 18px; padding: 22px; text-align: center; }}
.asc-note h3 {{ margin: 0 0 6px; font-weight: 900; padding: 0; }}
.asc-note p {{ margin: 0; color: #4B5563; }}
.asc-note.success {{ background: #EEF8F2; border: 1px solid #BFE5D1; }}
.asc-note.success h3 {{ color: {GREEN}; }}
.asc-note.closed {{ background: #FDEFEC; border: 1px solid #F5C6C0; }}
.asc-note.closed h3 {{ color: {RED}; }}
.asc-note.declined {{ background: #FFF6DF; border: 1px solid #F1DFA6; }}
.asc-note.declined h3 {{ color: #8A6608; }}

/* Convite */
.asc-invite {{ text-align: center; padding: 6px 4px 2px; }}
.asc-invite-logo {{ width: 72px; height: 72px; filter: drop-shadow(0 8px 16px rgba(198,40,40,.25)); }}
.asc-invite-kicker {{ margin: 12px 0 0; color: #6B7280; font-size: 1rem; }}
.asc-invite h2 {{ margin: 2px 0 8px; padding: 0; font-size: 1.8rem; font-weight: 900; color: {RED}; line-height: 1.15; }}
.asc-invite-date {{ display: inline-block; background: #EEF8F2; color: {GREEN}; font-weight: 800; border-radius: 999px; padding: 4px 14px; font-size: .92rem; }}
.asc-invite-ask {{ margin: 18px 0 4px; font-weight: 800; color: {NAVY}; font-size: 1.1rem; }}
.asc-invite-owner {{ margin: 8px 0 0; color: #6B7280; font-size: .92rem; }}
.asc-invite-owner b {{ color: {NAVY}; }}
.st-key-selfjoin {{ background: #EEF8F2; border: 2px solid {GREEN}; border-radius: 16px; padding: 14px 16px 10px; margin: 6px 0 4px; }}
.st-key-selfjoin label p {{ font-size: 1.15rem !important; font-weight: 900; color: {GREEN}; }}
.st-key-selfjoin [data-testid="stCaptionContainer"] {{ margin-top: -4px; }}
.st-key-decline_btn button {{ border-color: #F5C6C0; color: {RED}; background: #fff; }}
.st-key-decline_btn button:hover {{ border-color: {RED}; color: {RED}; background: #FDEFEC; }}
.asc-declined {{ margin-top: 14px; padding-top: 12px; border-top: 1px dashed #EADBB8; }}
.asc-declined p {{ margin: 0 0 8px; font-weight: 800; color: #6B7280; font-size: .9rem; }}
.asc-declined-item {{ padding: 8px 14px; border-radius: 12px; background: #FAF7F2; margin-bottom: 6px; }}
.asc-declined-item b {{ color: #6B7280; font-weight: 700; }}
.asc-declined-item span {{ display: block; color: #6B7280; font-size: .85rem; font-style: italic; overflow-wrap: anywhere; }}

.st-key-adminkey {{ border: 2px dashed {GOLD}; background: #FFF9E8; border-radius: 18px; padding: 16px 20px; }}
.asc-key h4 {{ margin: 0; padding: 0; color: #8A6608; font-weight: 900; }}
.asc-key p {{ margin: 4px 0 0; color: #4B5563; font-size: .92rem; }}

.asc-footer {{ text-align: center; color: #6B7280; font-size: .85rem; margin-top: 28px; }}
.asc-footer a {{ color: {RED}; font-weight: 700; }}
.st-key-card_privacy h4 {{ font-size: 1.05rem; font-weight: 800; color: {NAVY}; margin-top: 1rem; }}

/* Recursos */
.asc-features-title {{ font-size: 1.5rem; font-weight: 900; color: {NAVY}; margin: 28px 0 12px; }}
.asc-features {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; }}
.asc-feature {{ flex: 1 1 0; min-width: 0; display: flex; gap: 12px; align-items: flex-start; background: rgba(255,255,255,.75); border: 1px solid #F1E3C4; border-radius: 16px; padding: 14px; }}
.asc-feature .asc-icon {{ width: 36px; height: 36px; border-radius: 11px; }}
.asc-feature .asc-icon img {{ width: 20px; height: 20px; }}
.asc-feature b {{ display: block; color: {RED}; font-weight: 900; }}
.asc-feature span {{ color: #4B5563; font-size: .88rem; }}

/* Tablet: cartões da tela inicial um embaixo do outro, convidado centralizado */
@media (max-width: 960px) {{
  .st-key-home_cards > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
  .st-key-home_cards > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important; }}
  .st-key-guest_cols > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:nth-child(2)) {{ display: none; }}
  .st-key-guest_cols > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {{ flex: 1 1 100% !important; width: 100% !important; max-width: 560px; margin: 0 auto; }}
  .asc-feature {{ flex: 0 1 calc(33.333% - 8px); }}
}}

/* Celular */
@media (max-width: 640px) {{
  .block-container {{ padding-top: 3rem; }}
  .asc-title {{ font-size: 2rem; }}
  .asc-pill {{ font-size: 1.3rem; }}
  .asc-logo {{ width: 64px; height: 64px; }}
  [class*="st-key-card_"] {{ padding: 1.1rem 1rem 1rem; border-radius: 18px; }}
  .asc-stats {{ grid-template-columns: repeat(3, 1fr); gap: 8px; }}
  .asc-stat {{ padding: 10px 4px; border-radius: 12px; }}
  .asc-stat img {{ width: 20px; height: 20px; }}
  .asc-stat .v {{ font-size: 1rem; }}
  .asc-stat .l {{ font-size: .75rem; }}
  .asc-feature {{ flex: 0 1 calc(50% - 6px); }}
  .asc-share a {{ flex: 1 1 calc(50% - 5px); justify-content: center; padding: 10px 8px; }}
}}
@media (max-width: 400px) {{
  .asc-feature {{ flex: 1 1 100%; }}
}}
</style>
"""


ICON_COLORS = {"red": RED, "green": GREEN, "gold": "#A57C0B"}


def _svg_img(svg, css_class=""):
    # st.html remove <svg> inline, então os desenhos vão como imagem data URI
    data = base64.b64encode(svg.encode()).decode()
    return f'<img class="{css_class}" src="data:image/svg+xml;base64,{data}" alt="">'


def icon(name, color):
    return _svg_img(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{ICON_COLORS[color]}" '
                    f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_ICON_PATHS[name]}</svg>')


def inject_styles():
    st.html(CSS)


def hero(compact=False):
    tagline = "" if compact else """
      <div class="asc-tagline">
        <span class="asc-steps">Crie a sala • Convide • Sorteie • Envie</span>
        <p>A forma simples, segura e divertida de organizar o seu Amigo Secreto online.</p>
      </div>"""
    st.html(f"""
    <div class="asc-hero{' compact' if compact else ''}">
      <div class="asc-brand">
        {_svg_img(LOGO_SVG, "asc-logo")}
        <div><p class="asc-title">Amigo Secreto</p><span class="asc-pill">Conectado</span></div>
      </div>
      {tagline}
    </div>""")


def card_header(icon_name, color, title, subtitle):
    st.html(f"""
    <div class="asc-card-head">
      <div class="asc-icon {color}">{icon(icon_name, color)}</div>
      <div><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>
    </div>""")


def stats(items):
    """items: lista de (ícone, cor, valor, rótulo)."""
    tiles = "".join(
        f'<div class="asc-stat {color}">{icon(i, color)}<div class="v">{html.escape(str(v))}</div><div class="l">{html.escape(l)}</div></div>'
        for i, color, v, l in items
    )
    st.html(f'<div class="asc-stats">{tiles}</div>')


def share_buttons(whatsapp, twitter, telegram, url):
    """Cada rede recebe o texto no formato que entende. O Facebook só aceita o link."""
    q = urllib.parse.quote
    st.html(f"""
    <div class="asc-share">
      <a class="wa" href="https://api.whatsapp.com/send?text={q(whatsapp)}" target="_blank">📱 WhatsApp</a>
      <a class="fb" href="https://www.facebook.com/sharer/sharer.php?u={q(url)}" target="_blank">📘 Facebook</a>
      <a class="tw" href="https://twitter.com/intent/tweet?text={q(twitter)}" target="_blank">✖️ X / Twitter</a>
      <a class="tg" href="https://t.me/share/url?url={q(url)}&text={q(telegram)}" target="_blank">✈️ Telegram</a>
    </div>""")


def native_share_button(title, text, url):
    """Abre a folha de compartilhar do celular (contatos recentes e todos os apps).
    Onde o navegador não oferece isso, o botão vira "Copiar convite"."""
    payload = json.dumps({"title": title, "text": text, "url": url}).replace("</", "<\\/")
    components.html(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@800&display=swap" rel="stylesheet">
    <style>
      body {{ margin: 0; font-family: Nunito, sans-serif; }}
      button {{ width: 100%; height: 48px; border: 0; border-radius: 999px; cursor: pointer; font: 800 16px Nunito, sans-serif;
        color: #fff; background: {RED}; box-shadow: 0 6px 14px rgba(198,40,40,.25); }}
      button:active {{ transform: scale(.98); }}
      small {{ display: block; text-align: center; color: #6B7280; font-size: 13px; margin-top: 4px; min-height: 16px; }}
    </style>
    <button id="b">📤 Compartilhar convite</button><small id="m"></small>
    <script>
      const data = {payload};
      const b = document.getElementById("b"), m = document.getElementById("m");
      // O componente roda num iframe sem permissão de compartilhar; a página do app (mesma origem) tem.
      const nav = (() => {{ try {{ return window.top.navigator.share ? window.top.navigator : navigator; }} catch (e) {{ return navigator; }} }})();
      const canShare = !!nav.share;
      if (!canShare) b.textContent = "📋 Copiar convite";
      const copy = async () => {{
        const full = data.text + "\\n" + data.url;
        let ok = false;
        try {{ await navigator.clipboard.writeText(full); ok = true; }} catch (e) {{
          const t = document.createElement("textarea");
          t.value = full; document.body.appendChild(t); t.select();
          try {{ ok = document.execCommand("copy"); }} catch (e2) {{}}
          t.remove();
        }}
        m.textContent = ok ? "Convite copiado! É só colar onde quiser." : "Copie o texto do convite mais abaixo.";
      }};
      b.onclick = async () => {{
        if (!canShare) return copy();
        try {{ await nav.share(data); }} catch (e) {{ if (e.name !== "AbortError") await copy(); }}
      }};
    </script>""", height=74)


def people_list(people):
    """people: lista de (nome, e-mail mascarado)."""
    rows = "".join(
        f'<div class="asc-person"><div class="asc-avatar">{html.escape(name[:1].upper())}</div>'
        f'<div><b>{html.escape(name)}</b><span>{html.escape(email)}</span></div></div>'
        for name, email in people
    )
    st.html(f'<div class="asc-people">{rows}</div>')


def note(kind, title, text):
    st.html(f'<div class="asc-note {kind}"><h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div>')


def invite_intro(room_name, date_label, owner_name="", ask=True):
    """ask=False tira a pergunta "Vai participar?" (sala já sorteada)."""
    date_html = f'<span class="asc-invite-date">📅 Troca de presentes: {html.escape(date_label)}</span>' if date_label else ""
    if owner_name:
        date_html += f'<p class="asc-invite-owner">Organizado por <b>{html.escape(owner_name)}</b></p>'
    st.html(f"""
    <div class="asc-invite">
      {_svg_img(LOGO_SVG, "asc-invite-logo")}
      <p class="asc-invite-kicker">Você foi convidado(a) para o</p>
      <h2>{html.escape(room_name)}</h2>
      {date_html}
      {'<p class="asc-invite-ask">Vai participar do sorteio?</p>' if ask else ''}
    </div>""")


def declined_list(declines):
    """declines: lista de (nome, recado)."""
    rows = "".join(
        f'<div class="asc-declined-item"><b>❌ {html.escape(name)}</b>'
        + (f'<span>“{html.escape(message)}”</span>' if message else "")
        + "</div>"
        for name, message in declines
    )
    st.html(f'<div class="asc-declined"><p>Não vão participar</p>{rows}</div>')


def admin_key_notice(code, emailed_to=""):
    """emailed_to: e-mail (mascarado) que recebeu a chave, ou vazio se o envio falhou."""
    if emailed_to:
        where = (f"Também enviamos o código e a chave para <b>{html.escape(emailed_to)}</b> "
                 "(se não achar, olhe o spam).")
    else:
        where = "<b>Não conseguimos enviar a chave para o seu e-mail</b>, então anote-a agora: ela não será mostrada de novo."
    st.html(f"""
    <div class="asc-key">
      <h4>🔑 Sua chave do organizador</h4>
      <p>Para voltar a este painel você vai precisar do código <b>{html.escape(code)}</b> e da chave abaixo. {where}</p>
    </div>""")


def footer():
    st.html('<div class="asc-footer">🎁 Amigo Secreto Conectado · '
            '<a href="?pagina=privacidade" target="_self">Política de Privacidade</a></div>')


def privacy_policy(contact_email):
    with st.container(key="card_privacy"):
        card_header("lock", "green", "Política de Privacidade", "Última atualização: novembro de 2026")
        st.markdown(f"""
O **Amigo Secreto Conectado** organiza sorteios de amigo secreto. Esta página explica quais dados usamos e por quê.

#### Dados que coletamos
- **Organizador:** nome e e-mail informados ao criar a sala.
- **Participantes:** nome e e-mail informados ao confirmar presença, ou cadastrados pelo organizador.
- **Quem recusa o convite:** nome e, se a pessoa quiser, um recado para o organizador.
- **Sala:** nome, data da troca de presentes e o resultado do sorteio.

#### Como usamos
Só para fazer o amigo secreto funcionar: mostrar os participantes ao organizador, realizar o sorteio e
enviar por e-mail a cada participante quem ele tirou, além de enviar ao organizador o código e a chave da sala.
Não usamos os dados para publicidade e **não vendemos nem compartilhamos** com terceiros.

#### Onde ficam guardados
Em uma planilha privada do Google. Nomes, e-mails, recados e o resultado do sorteio são guardados
**criptografados**. A chave do organizador é guardada apenas de forma irreversível (hash).

#### Acesso à conta de e-mail do app
Os e-mails são enviados pela conta do próprio app ({contact_email}), usando a API do Gmail.
O app só **envia** os e-mails do sorteio, do convite e da chave e depois **move para a lixeira** essas mesmas
mensagens da pasta Enviados dessa conta, para que o resultado continue secreto.
Ele não lê, não guarda e não acessa nenhum outro e-mail, e não acessa o e-mail de participantes.
O uso das informações recebidas das APIs do Google segue a
[Política de Dados do Usuário dos Serviços de API do Google](https://developers.google.com/terms/api-services-user-data-policy),
incluindo os requisitos de Uso Limitado.

#### Por quanto tempo e como excluir
Os dados ficam guardados enquanto a sala existir. Para pedir a exclusão dos seus dados ou tirar dúvidas,
escreva para **{contact_email}**.
""")


def features():
    items = [
        ("door", "red", "Sala", "Crie uma sala para o seu grupo."),
        ("link", "green", "Convite", "Envie o link e convide os participantes."),
        ("shuffle", "gold", "Sorteio", "Sorteie de forma justa e automática."),
        ("mail", "red", "E-mail", "Cada participante recebe por e-mail quem tirou."),
        ("lock", "green", "Privacidade", "Dados criptografados e sorteio confidencial."),
    ]
    cards = "".join(
        f'<div class="asc-feature"><div class="asc-icon {c}">{icon(i, c)}</div><div><b>{t}</b><span>{d}</span></div></div>'
        for i, c, t, d in items
    )
    st.html(f'<div class="asc-features-title">Principais recursos</div><div class="asc-features">{cards}</div>')
