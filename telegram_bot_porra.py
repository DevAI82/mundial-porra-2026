"""
BOT DE TELEGRAM - PORRA MUNDIAL 2026 (v2 - AI-First)
=====================================================
Arquitectura: Gemini es el cerebro. Se le pasa todo el contexto de
Supabase en tiempo real y responde libremente a cualquier pregunta.

Capacidades:
  - Clasificación de la porra
  - Resultados del Mundial
  - Pronósticos por partido (quién ha registrado / quién no)
  - Puntos de cualquier jugador con su posición
  - Clasificación de grupos reales del Mundial
  - Próximos partidos
  - Cualquier pregunta sobre datos de la porra
  - Respuesta por voz (Gemini TTS)
"""

import os, json, wave, io, asyncio, urllib.request, urllib.error, urllib.parse
import tempfile, logging, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

from google import genai
from google.genai import types

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / '.env')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
SUPABASE_URL   = os.getenv('SUPABASE_URL',   'https://syyqoobojzuntauevytx.supabase.co')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY',   '')
ROOM_CODE      = os.getenv('ROOM_CODE',      'MGPX')

ADMIN_USER_IDS = [6058336566]   # Jose's Telegram ID
TTS_VOICE      = 'Aoede'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

gemini = genai.Client(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# JUGADORES (los 34 de la sala MGPX)
# ─────────────────────────────────────────────────────────────────────────────
JUGADORES = [
    'Aitor','Alberto','Antonio Marco','Antoniox','Carlos V','Chechu',
    'Curazao','Enrique','Eu','F,c,Alcahud','Ferhepi','Fran Peralta',
    'Gonzalo','Ismael','Iñaki','J','J.Tarraga','JORGINHO',
    'JOSELITO EL MESSiAS','Javi Llor','Javier Valero','Jona jr',
    'Juanco','Kaiser','Lapeña F.C','Niklian','Pablo R','Pascual',
    'RL7','Shevchen','Sosi','Zaqui','javichu','Álex Magic'
]

# ─────────────────────────────────────────────────────────────────────────────
# PARTIDOS
# ─────────────────────────────────────────────────────────────────────────────
PARTIDOS = {
    # Calendario REAL sincronizado con auto_post_match.py — regenerado 03/07/2026
    "J01":["México","Sudáfrica"], "J02":["Corea del Sur","Chequia"],
    "J03":["Canadá","Bosnia-Herzegovina"], "J04":["Estados Unidos","Paraguay"],
    "J05":["Catar","Suiza"], "J06":["Brasil","Marruecos"],
    "J07":["Haití","Escocia"], "J08":["Australia","Turquía"],
    "J09":["Alemania","Curazao"], "J10":["Países Bajos","Japón"],
    "J11":["Costa de Marfil","Ecuador"], "J12":["Suecia","Túnez"],
    "J13":["España","Cabo Verde"], "J14":["Bélgica","Egipto"],
    "J15":["Arabia Saudita","Uruguay"], "J16":["Irán","Nueva Zelanda"],
    "J17":["Francia","Senegal"], "J18":["Irak","Noruega"],
    "J19":["Argentina","Argelia"], "J20":["Austria","Jordania"],
    "J21":["Portugal","RD Congo"], "J22":["Inglaterra","Croacia"],
    "J23":["Ghana","Panamá"], "J24":["Uzbekistán","Colombia"],
    "J25":["Chequia","Sudáfrica"], "J26":["Suiza","Bosnia-Herzegovina"],
    "J27":["Canadá","Catar"], "J28":["México","Corea del Sur"],
    "J29":["Estados Unidos","Australia"], "J30":["Escocia","Marruecos"],
    "J31":["Brasil","Haití"], "J32":["Turquía","Paraguay"],
    "J33":["Países Bajos","Suecia"], "J34":["Alemania","Costa de Marfil"],
    "J35":["Ecuador","Curazao"], "J36":["Túnez","Japón"],
    "J37":["España","Arabia Saudita"], "J38":["Bélgica","Irán"],
    "J39":["Uruguay","Cabo Verde"], "J40":["Nueva Zelanda","Egipto"],
    "J41":["Argentina","Austria"], "J42":["Francia","Irak"],
    "J43":["Noruega","Senegal"], "J44":["Jordania","Argelia"],
    "J45":["Portugal","Uzbekistán"], "J46":["Inglaterra","Ghana"],
    "J47":["Panamá","Croacia"], "J48":["Colombia","RD Congo"],
    "J49":["Suiza","Canadá"], "J50":["Bosnia-Herzegovina","Catar"],
    "J51":["Escocia","Brasil"], "J52":["Marruecos","Haití"],
    "J53":["Chequia","México"], "J54":["Sudáfrica","Corea del Sur"],
    "J55":["Ecuador","Alemania"], "J56":["Curazao","Costa de Marfil"],
    "J57":["Túnez","Países Bajos"], "J58":["Japón","Suecia"],
    "J59":["Turquía","Estados Unidos"], "J60":["Paraguay","Australia"],
    "J61":["Noruega","Francia"], "J62":["Senegal","Irak"],
    "J63":["Uruguay","España"], "J64":["Cabo Verde","Arabia Saudita"],
    "J65":["Nueva Zelanda","Bélgica"], "J66":["Egipto","Irán"],
    "J67":["Panamá","Inglaterra"], "J68":["Croacia","Ghana"],
    "J69":["Colombia","Portugal"], "J70":["RD Congo","Uzbekistán"],
    "J71":["Jordania","Argentina"], "J72":["Argelia","Austria"],
    "J73":["Sudáfrica","Canadá"], "J74":["Alemania","Paraguay"],
    "J75":["Países Bajos","Marruecos"], "J76":["Brasil","Japón"],
    "J77":["Francia","Suecia"], "J78":["Costa de Marfil","Noruega"],
    "J79":["México","Ecuador"], "J80":["Inglaterra","RD Congo"],
    "J81":["Estados Unidos","Bosnia-Herzegovina"], "J82":["Bélgica","Senegal"],
    "J83":["Portugal","Croacia"], "J84":["España","Austria"],
    "J85":["Suiza","Argelia"], "J86":["Argentina","Cabo Verde"],
    "J87":["Colombia","Ghana"], "J88":["Australia","Egipto"],
    # ── ELIMINATORIAS: OCTAVOS DE FINAL (4-7 Jul) ──
    "J89":["Canadá","Marruecos"],     "J90":["Paraguay","Francia"],
    "J91":["Brasil","Noruega"],        "J92":["México","Inglaterra"],
    "J93":["Portugal","España"],       "J94":["Estados Unidos","Bélgica"],
    "J95":["Argentina","Egipto"],      "J96":["Suiza","Colombia"],
    # ── ELIMINATORIAS: CUARTOS DE FINAL (9-12 Jul) ──
    "J97":["Marruecos","Francia"],     "J99":["Noruega","Inglaterra"],
}

# Grupos del Mundial 2026
GRUPOS = {
    'A': ['México','Sudáfrica','Corea del Sur','Chequia'],
    'B': ['Canadá','Bosnia-Herzegovina','Suiza','Catar'],
    'C': ['Estados Unidos','Paraguay','Australia','Turquía'],
    'D': ['Brasil','Marruecos','Haití','Escocia'],
    'E': ['Alemania','Curazao','Costa de Marfil','Ecuador'],
    'F': ['Países Bajos','Japón','Suecia','Túnez'],
    'G': ['España','Cabo Verde','Arabia Saudita','Uruguay'],
    'H': ['Bélgica','Egipto','Irán','Nueva Zelanda'],
    'I': ['Francia','Senegal','Irak','Noruega'],
    'J': ['Argentina','Argelia','Austria','Jordania'],
    'K': ['Portugal','RD Congo','Uzbekistán','Colombia'],
    'L': ['Inglaterra','Croacia','Ghana','Panamá'],
}
EQUIPO_GRUPO = {team: grp for grp, teams in GRUPOS.items() for team in teams}

FLAGS = {
    "España":"🇪🇸","Alemania":"🇩🇪","Francia":"🇫🇷","Inglaterra":"🇬🇧",
    "Marruecos":"🇲🇦","Brasil":"🇧🇷","Argentina":"🇦🇷","Portugal":"🇵🇹",
    "Países Bajos":"🇳🇱","Bélgica":"🇧🇪","Croacia":"🇭🇷","Uruguay":"🇺🇾",
    "Colombia":"🇨🇴","México":"🇲🇽","Japón":"🇯🇵","Suiza":"🇨🇭",
    "Senegal":"🇸🇳","Cabo Verde":"🇨🇻","Curazao":"🇨🇼","Ecuador":"🇪🇨",
    "Ghana":"🇬🇭","Australia":"🇦🇺","Turquía":"🇹🇷","Suecia":"🇸🇪",
    "Arabia Saudita":"🇸🇦","Canadá":"🇨🇦","Catar":"🇶🇦","Corea del Sur":"🇰🇷",
    "Costa de Marfil":"🇨🇮","Egipto":"🇪🇬","Noruega":"🇳🇴","Austria":"🇦🇹",
    "Irán":"🇮🇷","Irak":"🇮🇶","Argelia":"🇩🇿","Jordania":"🇯🇴",
    "Sudáfrica":"🇿🇦","Chequia":"🇨🇿","Bosnia-Herzegovina":"🇧🇦","Paraguay":"🇵🇾",
    "Haití":"🇭🇹","Escocia":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Túnez":"🇹🇳","Uzbekistán":"🇺🇿",
    "Panamá":"🇵🇦","Nueva Zelanda":"🇳🇿","RD Congo":"🇨🇩",
    "Estados Unidos":"🇺🇸",
}
def flag(t): return FLAGS.get(t, "🏳️")

def normalize(s: str) -> str:
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ü','u'),('ñ','n')]:
        s = s.lower().replace(a, b)
    return s

# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE HELPER
# ─────────────────────────────────────────────────────────────────────────────
def supa(path: str, payload=None, method='GET'):
    url = f'{SUPABASE_URL}/rest/v1{path}'
    data = json.dumps(payload).encode() if payload else None
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates',
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return json.loads(body) if body.strip() else []
    except Exception as e:
        log.error(f"Supabase error {path}: {e}")
        return []

def supa_paged(path: str, page: int = 1000) -> list:
    """GET paginado con cabecera Range — PostgREST corta en 1000 filas por peticion
    (FIX 03/07/2026: predictions ya supera las 1000 y el bot calculaba puntos incompletos)."""
    sep = '&' if '?' in path else '?'
    out, start = [], 0
    while True:
        url = f'{SUPABASE_URL}/rest/v1{path}'
        req = urllib.request.Request(url, headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Range-Unit': 'items',
            'Range': f'{start}-{start + page - 1}',
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                rows = json.loads(resp.read() or b'[]')
        except Exception as e:
            log.error(f"Supabase paged error {path}: {e}")
            return out
        out.extend(rows)
        if len(rows) < page:
            return out
        start += page

# ─────────────────────────────────────────────────────────────────────────────
# CALCULAR PUNTUACIONES
# ─────────────────────────────────────────────────────────────────────────────
def sign(x): return 1 if x > 0 else (-1 if x < 0 else 0)

def calcular_scores() -> dict:
    results_raw = supa('/results?limit=200')
    results = {r['match_id']: r for r in results_raw}
    preds_raw = supa_paged(f'/predictions?room_code=eq.{ROOM_CODE}'
                     f'&select=player_name,match_key,loc,vis&order=player_name.asc,match_key.asc')
    adj_raw = supa_paged(f'/match_adjustments?room_code=eq.{ROOM_CODE}'
                   f'&select=player_name,match_id,adjustment&order=player_name.asc,match_id.asc')
    scores = {}
    for pred in preds_raw:
        player = pred['player_name']
        mk = pred.get('match_key', '')
        parts = mk.split('|')
        if len(parts) < 2:
            continue
        home_team, away_team = parts[0], parts[1]
        match_jid = next((j for j, t in PARTIDOS.items()
                          if t[0] == home_team and t[1] == away_team), None)
        if not match_jid or match_jid not in results:
            continue
        r = results[match_jid]
        ph, pa = pred.get('loc'), pred.get('vis')
        if ph is None or pa is None:
            continue
        try:
            ph, pa = int(ph), int(pa)
        except (ValueError, TypeError):
            continue
        rh, ra = r.get('home_goals'), r.get('away_goals')
        if rh is None or ra is None:
            continue
        pts = 0
        if ph == rh and pa == ra:
            pts += 3
        if sign(ph - pa) == sign(rh - ra):
            pts += 1
        scores[player] = scores.get(player, 0) + pts
    for adj in adj_raw:
        player = adj['player_name']
        mid = adj.get('match_id') or ''
        # FIX 03/07/2026: mismo criterio que la web (calcFavTeamPoints/calcScoreBreakdown):
        # goleador = 'J##' plano; favorita/avance = contiene '_FAV' o '_ADV'.
        # Otros (p.ej. 'CLASIFICACION_GRUPOS' sin sufijo, duplicado historico) NO computan.
        es_goleador = mid.startswith('J') and mid[1:].isdigit()
        es_fav = ('_FAV' in mid) or ('_ADV' in mid)
        if not (es_goleador or es_fav):
            continue
        scores[player] = scores.get(player, 0) + (adj.get('adjustment') or 0)
    # Añadir jugadores con 0 pts
    for j in JUGADORES:
        if j not in scores:
            scores[j] = 0
    return scores

# ─────────────────────────────────────────────────────────────────────────────
# BUSCAR PARTIDO EN TEXTO LIBRE
# ─────────────────────────────────────────────────────────────────────────────
def find_jid_by_text(text: str) -> str | None:
    m = re.search(r'\bj(\d{1,2})\b', text.lower())
    if m:
        return f"J{int(m.group(1)):02d}"
    t = normalize(text)
    best_jid, best_count = None, 0
    for jid, (h, a) in PARTIDOS.items():
        count = (1 if normalize(h) in t else 0) + (1 if normalize(a) in t else 0)
        if count > best_count:
            best_count, best_jid = count, jid
    return best_jid if best_count >= 1 else None

# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUIR CONTEXTO COMPLETO DESDE SUPABASE
# ─────────────────────────────────────────────────────────────────────────────
def build_full_context(question: str = "", is_admin: bool = False) -> str:
    """Reúne TODOS los datos relevantes de Supabase para que Gemini los use."""

    # ── Resultados ──
    results_raw = supa('/results?limit=200')
    results = {r['match_id']: r for r in results_raw}

    # ── Fechas de partidos (extraídas de match_keys en predictions) ──
    all_preds = supa(f'/predictions?room_code=eq.{ROOM_CODE}&select=match_key&limit=5000')
    match_dates = {}
    for p in all_preds:
        mk = p.get('match_key', '')
        parts = mk.split('|')
        if len(parts) >= 3:
            h, a, fecha = parts[0], parts[1], parts[2]
            jid = next((j for j,(th,ta) in PARTIDOS.items() if th==h and ta==a), None)
            if jid:
                match_dates[jid] = fecha

    # ── Puntuaciones porra ──
    scores = calcular_scores()
    ranking = sorted(scores.items(), key=lambda x: -x[1])

    # ── Resultados del Mundial ──
    resultados_lines = []
    for jid in sorted(results.keys()):
        r = results[jid]
        if r.get('home_goals') is None or jid not in PARTIDOS:
            continue
        h, a = PARTIDOS[jid]
        gh, ga = r['home_goals'], r['away_goals']
        fecha = match_dates.get(jid, '')
        scorers = r.get('scorers') or []
        gol_str = ''
        if scorers:
            if isinstance(scorers, str):
                try: scorers = json.loads(scorers)
                except: scorers = []
            names = [s.get('name', str(s)) if isinstance(s, dict) else str(s) for s in scorers]
            if names:
                gol_str = f" ⚽ {', '.join(names)}"
        resultados_lines.append(f"  {jid} ({fecha}): {h} {gh}-{ga} {a}{gol_str}")

    # ── Próximos partidos sin resultado ──
    proximos_lines = []
    for jid, (h, a) in sorted(PARTIDOS.items()):
        if jid not in results or results[jid].get('home_goals') is None:
            fecha = match_dates.get(jid, 'sin fecha')
            proximos_lines.append(f"  {jid} ({fecha}): {h} vs {a}")

    # ── Clasificación de grupos del Mundial real ──
    group_lines = []
    for grp, equipos in sorted(GRUPOS.items()):
        st = {eq: {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0,'pts':0} for eq in equipos}
        for jid, (h, a) in PARTIDOS.items():
            if h not in equipos or a not in equipos or jid not in results:
                continue
            r = results[jid]
            gh, ga = r.get('home_goals'), r.get('away_goals')
            if gh is None:
                continue
            st[h]['pj']+=1; st[a]['pj']+=1
            st[h]['gf']+=gh; st[h]['gc']+=ga
            st[a]['gf']+=ga; st[a]['gc']+=gh
            if gh > ga:   st[h]['g']+=1; st[h]['pts']+=3; st[a]['p']+=1
            elif gh < ga: st[a]['g']+=1; st[a]['pts']+=3; st[h]['p']+=1
            else:         st[h]['e']+=1; st[h]['pts']+=1; st[a]['e']+=1; st[a]['pts']+=1
        sorted_st = sorted(st.items(), key=lambda x: (-x[1]['pts'],-(x[1]['gf']-x[1]['gc']),-x[1]['gf']))
        group_lines.append(
            f"  Grupo {grp}: " +
            " | ".join(f"{eq} {s['pts']}pts ({s['pj']}PJ {s['g']}G {s['e']}E {s['p']}P GF:{s['gf']} GC:{s['gc']})"
                       for eq, s in sorted_st)
        )

    # ── Pronósticos del partido mencionado en la pregunta ──
    pred_context = ""
    jid_q = find_jid_by_text(question) if question else None
    if jid_q and jid_q in PARTIDOS:
        h_q, a_q = PARTIDOS[jid_q]
        tiene_resultado = jid_q in results and results[jid_q].get('home_goals') is not None
        if tiene_resultado or is_admin:
            # Buscar por formato equipo1|equipo2|... (fase de grupos)
            mk_enc = urllib.parse.quote(f"{h_q}|{a_q}")
            preds_team = supa(f'/predictions?room_code=eq.{ROOM_CODE}'
                              f'&match_key=ilike.*{mk_enc}*'
                              f'&select=player_name,loc,vis,goleador,pos&limit=200')
            # Buscar por formato prox_Jid (eliminatorias)
            preds_prox = supa(f'/predictions?room_code=eq.{ROOM_CODE}'
                              f'&match_key=eq.prox_{jid_q}'
                              f'&select=player_name,loc,vis,goleador,pos&limit=200')
            # Unir y deduplicar (prioridad al formato team si existe)
            seen_players = set()
            match_preds = []
            for p in preds_team + preds_prox:
                if p['player_name'] not in seen_players:
                    seen_players.add(p['player_name'])
                    match_preds.append(p)
            if match_preds:
                registrados = sorted(match_preds, key=lambda x: x['player_name'])
                pred_lines = [
                    f"    {p['player_name']}: {p.get('loc','-')}-{p.get('vis','-')}"
                    + (f" (gol: {p['goleador']})" if p.get('goleador') else '')
                    for p in registrados
                ]
                sin_pred = sorted(set(JUGADORES) - {p['player_name'] for p in match_preds})
                pred_context = (
                    f"\nPRONÓSTICOS {jid_q} ({h_q} vs {a_q}) — {len(match_preds)}/34 registrados:\n"
                    + "\n".join(pred_lines)
                )
                if sin_pred:
                    pred_context += f"\n  Sin pronóstico ({len(sin_pred)}): {', '.join(sin_pred)}"
            else:
                pred_context = f"\nNadie ha registrado pronóstico para {jid_q} ({h_q} vs {a_q}) aún."
        elif not is_admin:
            pred_context = f"\nLos pronósticos de {h_q} vs {a_q} estarán disponibles cuando el partido tenga resultado (privacidad)."

    context = f"""=== DATOS EN TIEMPO REAL — PORRA MUNDIAL 2026 ===
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Sala: {ROOM_CODE} | {len(JUGADORES)} participantes: {', '.join(sorted(JUGADORES))}

CLASIFICACIÓN PORRA (puntos acumulados):
{chr(10).join(f'  {i+1}. {p} — {pts} pts' for i,(p,pts) in enumerate(ranking))}

RESULTADOS DEL MUNDIAL ({len(resultados_lines)} partidos jugados):
{chr(10).join(resultados_lines) if resultados_lines else '  Ninguno registrado aún'}

PRÓXIMOS PARTIDOS SIN RESULTADO ({len(proximos_lines)} restantes):
{chr(10).join(proximos_lines[:20]) if proximos_lines else '  Todos los partidos tienen resultado'}

CLASIFICACIÓN DE GRUPOS — MUNDIAL REAL:
{chr(10).join(group_lines)}
{pred_context}"""

    return context

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI: RESPUESTA LIBRE CON CONTEXTO
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres el asistente inteligente de la Porra del Mundial 2026.
Tienes acceso a todos los datos en tiempo real de la porra y del Mundial.

REGLAS:
- Responde en español, de forma natural y concisa
- Usa los datos del contexto para responder con precisión
- Si preguntan por puntos/clasificación de una SELECCIÓN (España, Brasil...) → usa la clasificación de grupos del Mundial real
- Si preguntan por puntos de un JUGADOR (Kaiser, Eu, Aitor...) → usa la clasificación de la porra
- Si preguntan quién ha registrado pronóstico para un partido → usa los datos de pronósticos del contexto
- Para partidos de eliminatorias (cuartos, octavos...) los pronósticos también son visibles si hay datos en el contexto
- El administrador puede ver pronósticos de partidos aún sin resultado
- Si no tienes el dato exacto, dilo honestamente
- Para preguntas de resultados de partidos concretos, da el marcador exacto y goleadores si los hay
- El sistema de puntuación de la porra: exacto=3pts, signo correcto=1pt, bonus goleador por posición (DEL=1pt, MED=2pts, DEF=3pts), equipo favorito gana=+2pts
- Cuando nombres listas largas, resume si son más de 10 elementos
- No menciones el JID (J01, J13...) si el usuario no lo ha usado; usa los nombres de los equipos"""

async def ask_gemini(question: str, context: str) -> str:
    """Usa Gemini para responder libremente basándose en el contexto completo."""
    prompt = f"""{SYSTEM_PROMPT}

{context}

PREGUNTA DEL USUARIO: {question}

Responde de forma directa y natural:"""
    try:
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
        )
        return resp.text.strip()
    except Exception as e:
        log.error(f"Error Gemini: {e}")
        return "Lo siento, tuve un problema al procesar tu pregunta. Inténtalo de nuevo."

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI: TRANSCRIBIR VOZ
# ─────────────────────────────────────────────────────────────────────────────
async def transcribe_voice(ogg_path: str) -> str:
    try:
        with open(ogg_path, 'rb') as f:
            audio_bytes = f.read()
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg'),
                    "Transcribe exactamente lo que dice este audio en español. "
                    "Devuelve solo el texto transcrito, sin comentarios."
                ]
            )
        )
        return response.text.strip()
    except Exception as e:
        log.error(f"Error transcribiendo voz: {e}")
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI TTS
# ─────────────────────────────────────────────────────────────────────────────
def wav_bytes(pcm: bytes, channels=1, rate=24000, sample_width=2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()

def tts_to_wav(text: str) -> bytes | None:
    clean = re.sub(r'[^\w\s\.,;:!?¿¡\-\(\)áéíóúüñÁÉÍÓÚÜÑ]', '', text.replace('*','').replace('_','').replace('`',''))
    clean = clean[:700]
    try:
        resp = gemini.models.generate_content(
            model='gemini-3.1-flash-tts-preview',
            contents=f"[natural, informativo, español] {clean}",
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
                    )
                ),
            )
        )
        pcm = resp.candidates[0].content.parts[0].inline_data.data
        return wav_bytes(pcm)
    except Exception as e:
        log.error(f"Error TTS: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# ENVIAR RESPUESTA
# ─────────────────────────────────────────────────────────────────────────────
async def send_response(update: Update, texto: str, prefijo: str = ""):
    # FIX 03/07/2026: si el Markdown viene roto (p.ej. '_' sin pareja en IDs tipo J84_FAV),
    # Telegram rechaza el mensaje con BadRequest y el usuario no recibe NADA.
    # Reintentamos como texto plano antes de rendirnos.
    try:
        await update.message.reply_text(prefijo + texto, parse_mode='Markdown')
    except Exception as _e:
        log.warning(f"Markdown rechazado ({_e}); reenviando como texto plano")
        await update.message.reply_text(prefijo + texto)
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    loop = asyncio.get_event_loop()
    wav_data = await loop.run_in_executor(None, tts_to_wav, texto)
    if wav_data:
        await update.message.reply_voice(voice=io.BytesIO(wav_data))

# ─────────────────────────────────────────────────────────────────────────────
# PROCESADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
async def process_question(question: str, user_id: int, update: Update):
    """Procesa cualquier pregunta obteniendo contexto completo y respondiendo con Gemini."""
    is_admin = bool(ADMIN_USER_IDS) and user_id in ADMIN_USER_IDS
    # Construir contexto en executor para no bloquear el event loop
    loop = asyncio.get_event_loop()
    context = await loop.run_in_executor(None, lambda: build_full_context(question, is_admin))
    respuesta = await ask_gemini(question, context)
    await send_response(update, respuesta)

# ─────────────────────────────────────────────────────────────────────────────
# COMANDOS RÁPIDOS (respuestas directas sin pasar por Gemini para mayor rapidez)
# ─────────────────────────────────────────────────────────────────────────────
def get_clasificacion_texto(top_n=15) -> str:
    scores = calcular_scores()
    ranking = sorted(scores.items(), key=lambda x: -x[1])
    medals = ["🥇","🥈","🥉"]
    lines = [f"🏆 *TOP {top_n} — PORRA MUNDIAL 2026*\n"]
    for i, (player, pts) in enumerate(ranking[:top_n]):
        pos = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{pos} {player} — *{pts} pts*")
    return "\n".join(lines)

def get_resultado_partido(jid: str) -> str:
    jid = jid.upper()
    if jid not in PARTIDOS:
        return f"No conozco el partido {jid}."
    h, a = PARTIDOS[jid]
    rows = supa(f'/results?match_id=eq.{jid}&limit=1')
    if not rows or rows[0].get('home_goals') is None:
        return f"{flag(h)} {h} vs {flag(a)} {a} — resultado aún no registrado."
    r = rows[0]
    gh, ga = r['home_goals'], r['away_goals']
    scorers = r.get('scorers') or []
    gol_txt = ""
    if scorers:
        if isinstance(scorers, str):
            try: scorers = json.loads(scorers)
            except: scorers = []
        names = [s.get('name', str(s)) if isinstance(s, dict) else str(s) for s in scorers]
        if names:
            gol_txt = "\n⚽ Goleadores: " + ", ".join(names)
    return f"*{jid}: {flag(h)} {h} {gh} - {ga} {flag(a)} {a}*{gol_txt}"

def get_proximos_texto(n=8) -> str:
    rows = supa('/results?limit=200')
    con_resultado = {r['match_id'] for r in rows if r.get('home_goals') is not None}
    # Fechas desde predictions
    preds = supa(f'/predictions?room_code=eq.{ROOM_CODE}&select=match_key&limit=5000')
    dates = {}
    for p in preds:
        mk = p.get('match_key','').split('|')
        if len(mk) >= 3:
            jid = next((j for j,(th,ta) in PARTIDOS.items() if th==mk[0] and ta==mk[1]), None)
            if jid: dates[jid] = mk[2]
    sin_resultado = [(jid, teams) for jid, teams in PARTIDOS.items() if jid not in con_resultado]
    if not sin_resultado:
        return "¡Todos los partidos ya tienen resultado registrado!"
    lines = [f"📅 *Próximos {n} partidos:*\n"]
    for jid, (h, a) in sin_resultado[:n]:
        fecha = dates.get(jid, '')
        fecha_str = f" ({fecha})" if fecha else ""
        lines.append(f"• {jid}{fecha_str}: {flag(h)} {h} vs {flag(a)} {a}")
    return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS DE TELEGRAM
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ *¡Bienvenido al Bot de la Porra Mundial 2026!*\n\n"
        "Puedo responder a *cualquier pregunta* sobre la porra y el Mundial.\n\n"
        "Prueba a preguntar por voz o texto:\n"
        "🎙 _\"¿Cómo va la clasificación?\"_\n"
        "🎙 _\"¿Cuántos puntos tiene España en el grupo?\"_\n"
        "🎙 _\"¿Quién ha registrado pronóstico para España-Arabia Saudita?\"_\n"
        "🎙 _\"¿Qué puntos lleva Kaiser?\"_\n"
        "🎙 _\"¿Cuál es el próximo partido de Brasil?\"_\n\n"
        "O usa /ayuda para ver los comandos rápidos.",
        parse_mode='Markdown'
    )

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comandos rápidos:*\n\n"
        "• /clasificacion — Top 15 de la porra\n"
        "• /partido J13 — Resultado de un partido\n"
        "• /proximos — Próximos partidos sin resultado\n\n"
        "O simplemente *escríbeme o mándame un audio* con cualquier pregunta 🎙\n\n"
        "Ejemplos de lo que puedes preguntar:\n"
        "• ¿Cuántos puntos tiene España en el grupo G?\n"
        "• ¿Quién ha puesto pronóstico para el partido Escocia-Brasil?\n"
        "• ¿Quién va líder en la porra?\n"
        "• ¿Qué resultado hubo en el J37?\n"
        "• ¿Cuántos puntos lleva Kaiser y en qué puesto está?\n"
        "• ¿Qué partidos quedan por jugar?",
        parse_mode='Markdown'
    )

async def cmd_clasificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    await send_response(update, get_clasificacion_texto())

async def cmd_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jid = ' '.join(context.args).upper() if context.args else None
    if not jid:
        await update.message.reply_text("Indica el partido: /partido J13")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    await send_response(update, get_resultado_partido(jid))

async def cmd_proximos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    await send_response(update, get_proximos_texto())

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await update.message.reply_text("🎙 Escuchando...")
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        ogg_path = tmp.name
    try:
        transcripcion = await transcribe_voice(ogg_path)
        if not transcripcion:
            await msg.edit_text("❌ No pude entender el audio. Inténtalo de nuevo.")
            return
        await msg.edit_text(f"🎙 _{transcripcion}_\n⏳ Consultando datos...", parse_mode='Markdown')
        await process_question(transcripcion, update.effective_user.id, update)
        await msg.delete()
    finally:
        os.unlink(ogg_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    pregunta = update.message.text.strip()
    await process_question(pregunta, update.effective_user.id, update)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        print("ERROR: Falta TELEGRAM_BOT_TOKEN")
        return
    if not GEMINI_API_KEY:
        print("ERROR: Falta GEMINI_API_KEY")
        return

    print("Bot de la Porra Mundial 2026 iniciando...")
    print(f"  Supabase: {SUPABASE_URL}")
    print(f"  Room: {ROOM_CODE} | Jugadores: {len(JUGADORES)}")
    print("  Bot listo. Escuchando...\n")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('ayuda', cmd_ayuda))
    app.add_handler(CommandHandler('help', cmd_ayuda))
    app.add_handler(CommandHandler('clasificacion', cmd_clasificacion))
    app.add_handler(CommandHandler('partido', cmd_partido))
    app.add_handler(CommandHandler('proximos', cmd_proximos))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
