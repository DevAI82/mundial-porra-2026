"""
BOT DE TELEGRAM - PORRA MUNDIAL 2026
=====================================
Bot con interacción por VOZ y texto usando:
  - python-telegram-bot (v20+) para Telegram
  - Gemini Flash para entender comandos de voz/texto
  - Gemini 3.1 Flash TTS para responder por voz en español

INSTALACIÓN:
  pip install python-telegram-bot google-genai python-dotenv pydub

USO:
  python telegram_bot_porra.py

COMANDOS:
  /start            → Bienvenida
  /clasificacion    → Top 10 de la porra
  /partido J13      → Info del partido J13
  /pronosticos J13  → Pronósticos del partido
  /ayuda            → Lista de comandos
  Voz/Texto libre   → "¿Cómo va la clasificación?" etc.
"""

import os, json, wave, io, asyncio, urllib.request, urllib.error, tempfile, logging
from pathlib import Path
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
SUPABASE_KEY   = os.getenv('SUPABASE_KEY',   'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN5eXFvb2Jvanp1bnRhdWV2eXR4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDU1MTU0MiwiZXhwIjoyMDk2MTI3NTQyfQ.InprSiPRrbSQ80BiQ6C8ymkLbNntSbDkPK0RUjvVd3o')
ROOM_CODE      = os.getenv('ROOM_CODE',      'MGPX')

# Usuario(s) autorizados para actualizar resultados (pon tu user ID de Telegram)
# Déjalo vacío [] para permitir a todos, o pon tu ID: [123456789]
ADMIN_USER_IDS = [6058336566]

# Voz de Gemini TTS para respuestas en español
TTS_VOICE = 'Aoede'   # Breezy/Natural — muy buena en español

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZAR GEMINI
# ─────────────────────────────────────────────────────────────────────────────
gemini = genai.Client(api_key=GEMINI_API_KEY)

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
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            return json.loads(body) if body.strip() else []
    except Exception as e:
        log.error(f"Supabase error {path}: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# PARTIDOS (misma lista que auto_post_match.py)
# ─────────────────────────────────────────────────────────────────────────────
PARTIDOS = {
    "J01":["México","Sudáfrica"],      "J02":["Corea del Sur","Chequia"],
    "J03":["Canadá","Bosnia-Herzegovina"],"J04":["Estados Unidos","Paraguay"],
    "J05":["Catar","Suiza"],           "J06":["Brasil","Marruecos"],
    "J07":["Haití","Escocia"],         "J08":["Australia","Turquía"],
    "J09":["Alemania","Curazao"],      "J10":["Países Bajos","Japón"],
    "J11":["Costa de Marfil","Ecuador"],"J12":["Suecia","Túnez"],
    "J13":["España","Cabo Verde"],     "J14":["Bélgica","Egipto"],
    "J15":["Arabia Saudita","Uruguay"],"J16":["Irán","Nueva Zelanda"],
    "J17":["Francia","Senegal"],       "J18":["Irak","Noruega"],
    "J19":["Argentina","Argelia"],     "J20":["Austria","Jordania"],
    "J21":["Portugal","RD Congo"],     "J22":["Inglaterra","Croacia"],
    "J23":["Ghana","Panamá"],          "J24":["Uzbekistán","Colombia"],
    "J25":["Chequia","Sudáfrica"],     "J26":["Suiza","Bosnia-Herzegovina"],
    "J27":["Canadá","Catar"],          "J28":["México","Corea del Sur"],
    "J29":["Estados Unidos","Australia"],"J30":["Escocia","Marruecos"],
    "J31":["Brasil","Haití"],          "J32":["Turquía","Paraguay"],
    "J33":["Países Bajos","Suecia"],   "J34":["Alemania","Costa de Marfil"],
    "J35":["Ecuador","Curazao"],       "J36":["Túnez","Japón"],
    "J37":["España","Arabia Saudita"], "J38":["Bélgica","Irán"],
    "J39":["Uruguay","Cabo Verde"],    "J40":["Nueva Zelanda","Egipto"],
    "J41":["Argentina","Austria"],     "J42":["Francia","Irak"],
    "J43":["Noruega","Senegal"],       "J44":["Jordania","Argelia"],
    "J45":["Portugal","Uzbekistán"],   "J46":["Inglaterra","Ghana"],
    "J47":["Panamá","Croacia"],        "J48":["Colombia","RD Congo"],
    "J49":["Suiza","Canadá"],          "J50":["Bosnia-Herzegovina","Catar"],
    "J51":["Escocia","Brasil"],        "J52":["Marruecos","Haití"],
    "J53":["Chequia","México"],        "J54":["Sudáfrica","Corea del Sur"],
    "J55":["Ecuador","Alemania"],      "J56":["Curazao","Costa de Marfil"],
    "J57":["Túnez","Países Bajos"],    "J58":["Japón","Suecia"],
    "J59":["Turquía","Estados Unidos"],"J60":["Paraguay","Australia"],
    "J61":["Noruega","Francia"],       "J62":["Senegal","Irak"],
    "J63":["Uruguay","España"],        "J64":["Cabo Verde","Arabia Saudita"],
    "J65":["Nueva Zelanda","Bélgica"], "J66":["Egipto","Irán"],
    "J67":["Argelia","Argentina"],     "J68":["Jordania","Austria"],
    "J69":["RD Congo","Portugal"],     "J70":["Croacia","Inglaterra"],
    "J71":["Panamá","Ghana"],          "J72":["Colombia","Uzbekistán"],
}

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
    "Estados Unidos":"🇺🇸","México":"🇲🇽",
}

def flag(t): return FLAGS.get(t, "🏳️")

# ─────────────────────────────────────────────────────────────────────────────
# DATOS DESDE SUPABASE
# ─────────────────────────────────────────────────────────────────────────────
def sign(x): return 1 if x > 0 else (-1 if x < 0 else 0)

def calcular_scores() -> dict:
    """Calcula puntuaciones desde predictions + match_adjustments (igual que auto_post_match.py)."""
    results_raw = supa('/results?limit=200')
    results = {r['match_id']: r for r in results_raw}

    preds_raw = supa(f'/predictions?room_code=eq.{ROOM_CODE}'
                     f'&select=player_name,match_key,loc,vis&limit=5000')
    adj_raw = supa(f'/match_adjustments?room_code=eq.{ROOM_CODE}'
                   f'&select=player_name,match_id,adjustment&limit=2000')

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
        scores[player] = scores.get(player, 0) + (adj.get('adjustment') or 0)

    return scores

def get_clasificacion(top_n=10) -> str:
    scores = calcular_scores()
    if not scores:
        return "No hay datos de clasificación disponibles."
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    lines = [f"🏆 *TOP {top_n} CLASIFICACION PORRA MUNDIAL 2026*\n"]
    medals = ["🥇","🥈","🥉"]
    for i, (player, pts) in enumerate(sorted_scores[:top_n]):
        pos = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{pos} {player} — *{pts} pts*")
    return "\n".join(lines)

def get_resultado_partido(jid: str) -> str:
    jid = jid.upper()
    if jid not in PARTIDOS:
        return f"No conozco el partido {jid}."
    h, a = PARTIDOS[jid]
    rows = supa(f'/results?match_id=eq.{jid}&limit=1')
    if not rows:
        return f"{flag(h)} {h} vs {flag(a)} {a} — resultado aun no registrado."
    r = rows[0]
    gh, ga = r.get('home_goals'), r.get('away_goals')
    if gh is None:
        return f"{flag(h)} {h} vs {flag(a)} {a} — resultado aun no registrado."
    scorers = r.get('scorers') or []
    gol_txt = ""
    if scorers:
        if isinstance(scorers, str):
            import json as _json
            try: scorers = _json.loads(scorers)
            except: scorers = []
        if scorers:
            gol_txt = "\n⚽ Goleadores: " + ", ".join(
                s.get('name', s) if isinstance(s, dict) else str(s) for s in scorers)
    return f"*{jid}: {flag(h)} {h} {gh} - {ga} {flag(a)} {a}*{gol_txt}"

def get_pronosticos_partido(jid: str, is_admin: bool = False) -> str:
    jid = jid.upper()
    if jid not in PARTIDOS:
        return f"No conozco el partido {jid}."
    h, a = PARTIDOS[jid]
    res = supa(f'/results?match_id=eq.{jid}&limit=1')
    tiene_resultado = bool(res and res[0].get('home_goals') is not None)
    if not tiene_resultado and not is_admin:
        return f"Los pronosticos de {h} vs {a} se mostraran cuando el partido tenga resultado."
    aviso = " _(partido sin resultado aun — solo visible para admin)_\n" if not tiene_resultado else "\n"
    mk = f"{h}|{a}"
    rows = supa(f'/predictions?room_code=eq.{ROOM_CODE}'
                f'&match_key=ilike.{mk}*&select=player_name,loc,vis,goleador&limit=200')
    if not rows:
        return f"No hay pronosticos registrados para {h} vs {a}."
    lines = [f"📋 *Pronosticos {jid}: {flag(h)} {h} vs {flag(a)} {a}*{aviso}"]
    for r in sorted(rows, key=lambda x: x.get('player_name','')):
        gol = f" — {r['goleador']}" if r.get('goleador') else ""
        lines.append(f"• {r['player_name']}: {r.get('loc','-')}-{r.get('vis','-')}{gol}")
    return "\n".join(lines)

def get_puntos_jugador(nombre: str) -> str:
    scores = calcular_scores()
    if not scores:
        return "No hay datos disponibles."
    # Ranking completo ordenado
    ranking = sorted(scores.items(), key=lambda x: -x[1])
    nombre_n = nombre.lower()
    lines = []
    for pos, (player, pts) in enumerate(ranking, 1):
        if nombre_n in player.lower():
            medals = {1:"🥇", 2:"🥈", 3:"🥉"}
            pos_str = medals.get(pos, f"{pos}º")
            total = len(scores)
            lines.append(f"👤 *{player}*\n{pos_str} puesto de {total} — *{pts} pts*")
    if not lines:
        return f"No encontre a ningun jugador con el nombre '{nombre}'."
    return "\n".join(lines)

def get_proximos_partidos(n=5) -> str:
    rows = supa('/results?limit=200')
    con_resultado = {r['match_id'] for r in rows if r.get('home_goals') is not None}
    sin_resultado = [(jid, teams) for jid, teams in PARTIDOS.items()
                     if jid not in con_resultado]
    if not sin_resultado:
        return "Todos los partidos ya tienen resultado registrado!"
    lines = [f"📅 *Proximos {n} partidos sin resultado:*\n"]
    for jid, (h, a) in sin_resultado[:n]:
        lines.append(f"• {jid}: {flag(h)} {h} vs {flag(a)} {a}")
    return "\n".join(lines)

def get_goleadores_porra(top_n=10) -> str:
    adj_raw = supa(f'/match_adjustments?room_code=eq.{ROOM_CODE}'
                   f'&match_id=like.*GOL*&select=player_name,adjustment&limit=2000')
    if not adj_raw:
        # Fallback: top jugadores por puntos de ajuste GOL
        adj_raw = supa(f'/match_adjustments?room_code=eq.{ROOM_CODE}'
                       f'&select=player_name,match_id,adjustment&limit=2000')
        adj_raw = [a for a in adj_raw if 'FAV' not in str(a.get('match_id',''))]
    gol_pts = {}
    for adj in adj_raw:
        p = adj['player_name']
        gol_pts[p] = gol_pts.get(p, 0) + (adj.get('adjustment') or 0)
    if not gol_pts:
        return "Aun no hay puntos de goleadores."
    sorted_gol = sorted(gol_pts.items(), key=lambda x: -x[1])
    lines = [f"⚽ *TOP {top_n} BONUS GOLEADORES*\n"]
    for i, (player, pts) in enumerate(sorted_gol[:top_n], 1):
        if pts <= 0:
            break
        lines.append(f"{i}. {player} — {pts} pts")
    return "\n".join(lines) if len(lines) > 1 else "Aun no hay puntos de goleadores."

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI: TRANSCRIBIR VOZ
# ─────────────────────────────────────────────────────────────────────────────
async def transcribe_voice(ogg_path: str) -> str:
    """Transcribe un archivo de voz OGG usando Gemini Flash (datos inline)."""
    try:
        import base64
        with open(ogg_path, 'rb') as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode()
        response = gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type='audio/ogg'),
                "Transcribe exactamente lo que dice este audio en español. "
                "Devuelve solo el texto transcrito, sin comentarios adicionales."
            ]
        )
        return response.text.strip()
    except Exception as e:
        log.error(f"Error transcribiendo voz: {e}")
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI: ENTENDER INTENCIÓN
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres el asistente del bot de la Porra del Mundial 2026.
Analiza el mensaje del usuario y devuelve UN JSON con esta estructura:
{
  "intent": "clasificacion|partido|pronosticos|puntos|proximos|goleadores|actualizar|desconocido",
  "jid": "J13 (si aplica, null si no)",
  "nombre": "nombre del jugador (si aplica, null si no)",
  "score": "2-1 (si es actualización, null si no)",
  "scorers": "Morata 45, Williams 78 (si se mencionan goleadores, null si no)"
}

Ejemplos:
- "¿Cómo va la clasificación?" → {"intent":"clasificacion","jid":null,"nombre":null,"score":null,"scorers":null}
- "¿Qué resultado hubo en el J13?" → {"intent":"partido","jid":"J13","nombre":null,"score":null,"scorers":null}
- "dime los pronósticos del partido J5" → {"intent":"pronosticos","jid":"J05","nombre":null,"score":null,"scorers":null}
- "¿cuántos puntos tiene Jose?" → {"intent":"puntos","jid":null,"nombre":"Jose","score":null,"scorers":null}
- "actualiza el J13 con resultado 2-1" → {"intent":"actualizar","jid":"J13","nombre":null,"score":"2-1","scorers":null}
- "¿cuándo es el próximo partido?" → {"intent":"proximos","jid":null,"nombre":null,"score":null,"scorers":null}
- "top goleadores de la porra" → {"intent":"goleadores","jid":null,"nombre":null,"score":null,"scorers":null}

Normaliza el JID con cero si es necesario: "partido 5" → "J05", "jornada 13" → "J13".
Responde SOLO con el JSON, sin explicaciones."""

def normalize(s: str) -> str:
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ü','u'),('ñ','n')]:
        s = s.lower().replace(a, b)
    return s

def find_jid_by_text(text: str) -> str | None:
    """Busca el JID mirando si el texto menciona nombres de equipos."""
    import re
    # Primero buscar código explícito tipo J13
    m = re.search(r'\bj(\d{1,2})\b', text.lower())
    if m:
        return f"J{int(m.group(1)):02d}"
    # Buscar por nombres de equipo (normalizado sin acentos)
    t = normalize(text)
    best_jid, best_count = None, 0
    for jid, (h, a) in PARTIDOS.items():
        count = 0
        if normalize(h) in t: count += 1
        if normalize(a) in t: count += 1
        if count > best_count:
            best_count, best_jid = count, jid
    return best_jid if best_count >= 1 else None

def parse_intent_keywords(text: str) -> dict | None:
    """Reconocimiento rápido por palabras clave como respaldo."""
    t = text.lower()
    jid = find_jid_by_text(text)

    # Extraer nombre propio del texto (palabras con mayúscula que no sean equipos)
    import re as _re
    team_names_norm = {normalize(team) for teams in PARTIDOS.values() for team in teams}
    nombre_detectado = None
    for word in _re.findall(r'[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)*', text):
        if normalize(word) not in team_names_norm and len(word) > 2:
            nombre_detectado = word
            break

    # Puntos de un jugador concreto — ANTES que clasificación general
    if any(w in t for w in ['punto','puntos','puntuacion','lleva','puesto','posicion','posición']) and nombre_detectado:
        return {"intent":"puntos","jid":None,"nombre":nombre_detectado,"score":None,"scorers":None}
    if any(w in t for w in ['clasificacion','clasificación','ranking','tabla','top','lider','líder']):
        return {"intent":"clasificacion","jid":None,"nombre":None,"score":None,"scorers":None}
    if any(w in t for w in ['pronostico','pronóstico','pronosticos','pronósticos','apuesta']):
        return {"intent":"pronosticos","jid":jid,"nombre":None,"score":None,"scorers":None}
    if any(w in t for w in ['resultado','marcador','como quedo','cómo quedó','termino','terminó']) and jid:
        return {"intent":"partido","jid":jid,"nombre":None,"score":None,"scorers":None}
    if any(w in t for w in ['proximo','próximo','siguiente','cuando','cuándo','pendiente']):
        return {"intent":"proximos","jid":None,"nombre":None,"score":None,"scorers":None}
    if any(w in t for w in ['goleador','gol bonus','bonus gol']):
        return {"intent":"goleadores","jid":None,"nombre":None,"score":None,"scorers":None}
    if any(w in t for w in ['punto','puntuacion','puntuación','cuantos puntos','cuántos puntos']):
        return {"intent":"puntos","jid":None,"nombre":nombre_detectado,"score":None,"scorers":None}
    return None

async def parse_intent(text: str) -> dict:
    """Usa Gemini para entender la intención del usuario."""
    # Primero intentar palabras clave (rápido y sin coste)
    kw = parse_intent_keywords(text)
    if kw and kw["intent"] != "desconocido":
        return kw
    # Si no, usar Gemini
    try:
        resp = gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{SYSTEM_PROMPT}\n\nMensaje: {text}",
        )
        raw = resp.text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Error parseando intención: {e}")
        return kw or {"intent": "desconocido", "jid": None, "nombre": None, "score": None, "scorers": None}

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI TTS: GENERAR AUDIO
# ─────────────────────────────────────────────────────────────────────────────
def wav_bytes(pcm: bytes, channels=1, rate=24000, sample_width=2) -> bytes:
    """Envuelve PCM raw en un WAV válido."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()

def tts_to_wav(text: str) -> bytes | None:
    """Genera audio WAV desde texto usando Gemini TTS."""
    # Limitar a ~500 chars para TTS (sin emojis ni markdown)
    clean = text.replace('*','').replace('_','').replace('`','')
    # Quitar emojis básicos para TTS más limpio
    import re
    clean = re.sub(r'[^\w\s\.,;:!?¿¡\-\(\)áéíóúüñÁÉÍÓÚÜÑ]', '', clean)
    clean = clean[:600]

    try:
        resp = gemini.models.generate_content(
            model='gemini-3.1-flash-tts-preview',
            contents=f"[natural, informativo, español] {clean}",
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=TTS_VOICE
                        )
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
# EJECUTAR INTENCIÓN
# ─────────────────────────────────────────────────────────────────────────────
def execute_intent(intent_data: dict, user_id: int) -> str:
    """Ejecuta la acción correspondiente y devuelve texto de respuesta."""
    intent = intent_data.get('intent', 'desconocido')
    jid    = intent_data.get('jid')
    nombre = intent_data.get('nombre')
    score  = intent_data.get('score')

    if intent == 'clasificacion':
        return get_clasificacion(10)

    elif intent == 'partido':
        if not jid:
            return "¿De qué partido quieres el resultado? Dime los equipos, por ejemplo: *resultado España Brasil*"
        return get_resultado_partido(jid)

    elif intent == 'pronosticos':
        if not jid:
            return "¿De qué partido quieres los pronósticos? Dime los equipos, por ejemplo: *pronósticos Escocia Brasil*"
        is_admin = not ADMIN_USER_IDS or user_id in ADMIN_USER_IDS
        return get_pronosticos_partido(jid, is_admin=is_admin)

    elif intent == 'puntos':
        if not nombre:
            return "¿De qué jugador quieres ver los puntos?"
        return get_puntos_jugador(nombre)

    elif intent == 'proximos':
        return get_proximos_partidos(5)

    elif intent == 'goleadores':
        return get_goleadores_porra(10)

    elif intent == 'actualizar':
        if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
            return "❌ Solo el administrador puede actualizar resultados."
        if not jid or not score:
            return ("Para actualizar un resultado necesito el partido y el marcador.\n"
                    "Ejemplo: *Actualiza el J13 con resultado 2-1*")
        # Llamar al script existente como subproceso
        import subprocess
        script = Path(__file__).parent / 'auto_post_match.py'
        cmd = ['python', str(script), jid, f'--manual-score', score]
        scorers = intent_data.get('scorers')
        if scorers:
            cmd += ['--manual-scorers', scorers]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                    cwd=str(Path(__file__).parent))
            if result.returncode == 0:
                return (f"✅ *{jid}* actualizado con resultado *{score}*.\n"
                        f"Deploy realizado. ¡La clasificación ya está actualizada!")
            else:
                return f"⚠️ Error al actualizar:\n```{result.stderr[-500:]}```"
        except subprocess.TimeoutExpired:
            return "⏱️ El proceso tardó demasiado. Revisa los logs."
        except Exception as e:
            return f"❌ Error: {e}"

    else:
        return ("No entendí tu solicitud. Puedes pedirme:\n"
                "• 📊 *Clasificación* — top 10\n"
                "• 🏟 *Resultado* del partido J13\n"
                "• 📋 *Pronósticos* del J13\n"
                "• 👤 *Puntos* de Jose\n"
                "• 📅 *Próximos* partidos\n"
                "• ⚽ *Goleadores* de la porra\n"
                "• ✏️ *Actualiza J13 con 2-1* (solo admin)")

# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS DE TELEGRAM
# ─────────────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ *¡Bienvenido al Bot de la Porra Mundial 2026!*\n\n"
        "Puedes hablarme por *voz* o por *texto*. Te responderé con voz y texto.\n\n"
        "Prueba a decir:\n"
        "🎙 _\"¿Cómo va la clasificación?\"_\n"
        "🎙 _\"¿Qué resultado tuvo el partido J13?\"_\n"
        "🎙 _\"¿Cuántos puntos tiene Jose?\"_\n\n"
        "O usa /ayuda para ver todos los comandos.",
        parse_mode='Markdown'
    )

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comandos disponibles:*\n\n"
        "• /clasificacion — Top 10 de la porra\n"
        "• /partido J13 — Resultado de un partido\n"
        "• /pronosticos J13 — Pronósticos del partido\n"
        "• /proximos — Próximos partidos sin resultado\n"
        "• /goleadores — Top bonus goleadores\n\n"
        "O simplemente escríbeme o mándame un *audio* con lo que quieras saber 🎙",
        parse_mode='Markdown'
    )

async def cmd_clasificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    texto = get_clasificacion()
    await send_response(update, texto)

async def cmd_partido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jid = ' '.join(context.args).upper() if context.args else None
    if not jid:
        await update.message.reply_text("Indica el partido: /partido J13")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    texto = get_resultado_partido(jid)
    await send_response(update, texto)

async def cmd_pronosticos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jid = ' '.join(context.args).upper() if context.args else None
    if not jid:
        await update.message.reply_text("Indica el partido: /pronosticos J13")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    texto = get_pronosticos_partido(jid)
    await send_response(update, texto)

async def cmd_proximos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    texto = get_proximos_partidos()
    await send_response(update, texto)

async def cmd_goleadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    texto = get_goleadores_porra()
    await send_response(update, texto)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe un mensaje de voz, lo transcribe y procesa."""
    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await update.message.reply_text("🎙 Escuchando...")

    # Descargar el archivo de voz
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        await voice_file.download_to_drive(tmp.name)
        ogg_path = tmp.name

    try:
        # Transcribir
        transcripcion = await transcribe_voice(ogg_path)
        if not transcripcion:
            await msg.edit_text("❌ No pude entender el audio. Inténtalo de nuevo.")
            return

        await msg.edit_text(f"🎙 _\"{transcripcion}\"_\n⏳ Procesando...", parse_mode='Markdown')

        # Procesar intención y responder
        intent_data = await parse_intent(transcripcion)
        texto = execute_intent(intent_data, update.effective_user.id)
        await msg.delete()
        await send_response(update, texto, prefijo=f"🎙 _{transcripcion}_\n\n")

    finally:
        os.unlink(ogg_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa mensajes de texto libre con Gemini."""
    await update.message.chat.send_action(ChatAction.TYPING)
    texto_usuario = update.message.text.strip()

    intent_data = await parse_intent(texto_usuario)
    texto = execute_intent(intent_data, update.effective_user.id)
    await send_response(update, texto)

# ─────────────────────────────────────────────────────────────────────────────
# ENVIAR RESPUESTA (TEXTO + VOZ)
# ─────────────────────────────────────────────────────────────────────────────
async def send_response(update: Update, texto: str, prefijo: str = ""):
    """Envía respuesta de texto y, si es posible, también como nota de voz."""
    # Texto
    await update.message.reply_text(prefijo + texto, parse_mode='Markdown')

    # Voz — generar de forma asíncrona en el executor
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    loop = asyncio.get_event_loop()
    wav_data = await loop.run_in_executor(None, tts_to_wav, texto)
    if wav_data:
        await update.message.reply_voice(voice=io.BytesIO(wav_data))

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: Falta TELEGRAM_BOT_TOKEN en el archivo .env")
        return
    if not GEMINI_API_KEY:
        print("❌ ERROR: Falta GEMINI_API_KEY en el archivo .env")
        return

    print("🤖 Iniciando Bot de la Porra Mundial 2026...")
    print(f"   Supabase: {SUPABASE_URL}")
    print(f"   Room:     {ROOM_CODE}")
    print(f"   Voz TTS:  {TTS_VOICE}")
    print("   Bot listo. Escuchando mensajes... (Ctrl+C para parar)\n")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('ayuda', cmd_ayuda))
    app.add_handler(CommandHandler('help', cmd_ayuda))
    app.add_handler(CommandHandler('clasificacion', cmd_clasificacion))
    app.add_handler(CommandHandler('partido', cmd_partido))
    app.add_handler(CommandHandler('pronosticos', cmd_pronosticos))
    app.add_handler(CommandHandler('proximos', cmd_proximos))
    app.add_handler(CommandHandler('goleadores', cmd_goleadores))

    # Mensajes libres
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
