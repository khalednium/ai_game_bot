"""
╔═══════════════════════════════════════════════════════════════════════╗
║         RESIDENT EVIL 3: NEMESIS CLASSIC (PS1 1999)                   ║
║         LOCAL AI BOT — النسخة النهائية الشاملة 100%                   ║
║         DuckStation + Ollama (GPU/CPU) — بدون إنترنت أو API           ║
╠═══════════════════════════════════════════════════════════════════════╣
║  المعرفة المدمجة:                                                      ║
║  ✓ كل 10 Live Selections + الخيار الأمثل لـ 100%                      ║
║  ✓ كل 7 مكافآت نيميسيس بالترتيب (Hard Mode فقط)                      ║
║  ✓ نظام البارود الكامل (A/B/C + Enhanced بعد 8 مرات)                  ║
║  ✓ كل ألغاز الكلاسيك (برج الساعة، المحوّل، المستشفى، الصندوق)        ║
║  ✓ تكتيكات كل عدو (زومبي/كلاب/هانتر/Brain Sucker/Drain Deimos)       ║
║  ✓ تكتيكات نيميسيس المتخصصة (7 مواجهات)                               ║
║  ✓ تتبع الرتبة: الوقت + الحفظ + العلاج                                ║
║  ✓ الكشف السريع للشاشة (Live Selection، الصحة) بدون AI               ║
║  ✓ اكتشاف GPU تلقائي + اختيار أفضل نموذج                              ║
║  ✓ وضع كارلوس (مستشفى)                                                 ║
╚═══════════════════════════════════════════════════════════════════════╝
  للتشغيل:  python re3_final_bot.py
  المتطلبات: pip install mss Pillow keyboard requests pywin32
             + Ollama من https://ollama.com
"""

# ═══════════════════════════ الاستيرادات ═══════════════════════════════
import json, time, base64, threading, sys, os, random, subprocess
from io import BytesIO
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

for lib in ("mss", "PIL", "keyboard", "requests"):
    try:
        __import__(lib if lib != "PIL" else "PIL.Image")
    except ImportError:
        print(f"[!] مكتبة مفقودة: {lib}")
        print("[!] pip install mss Pillow keyboard requests pywin32")
        sys.exit(1)

import mss
from PIL import Image
import keyboard
import requests

# ════════════════════════ إعدادات ══════════════════════════════════════
CONFIG_FILE = "config.json"

def load_config() -> dict:
    """تحميل الإعدادات من ملف JSON"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

CONFIG = load_config()

OLLAMA_URL       = CONFIG.get("ollama_url", "http://localhost:11434")
DUCKSTATION_WIN  = CONFIG.get("duckstation_window", "DuckStation")
CAPTURE_SEC      = CONFIG.get("capture_sec", 0.25)
THINK_EXPLORE    = CONFIG.get("think_explore", 1.4)
THINK_COMBAT     = CONFIG.get("think_combat", 0.7)
THINK_NEMESIS    = CONFIG.get("think_nemesis", 0.35)
THINK_LIVE_SEL   = CONFIG.get("think_live_sel", 0.18)
LIVE_SEL_BRIGHT  = CONFIG.get("live_sel_bright", 0.55)
AUTO_LAUNCH     = CONFIG.get("auto_launch", True)
DUCKSTATION_PATH = CONFIG.get("duckstation_path", r"C:\AI game bot\000 duckstation\duckstation-qt-x64-ReleaseLTCG.exe")
GAME_ISO_PATH   = CONFIG.get("game_iso_path", r"C:\ps1\epsxe\isos\resident evil 3\resident evil 3.bin")

# ════════════════════════ النماذج المحلية ══════════════════════════════
MODELS = {
    "cpu":      "moondream",             # CPU أو VRAM < 4GB  → ~0.7ث
    "low_gpu":  "llava:7b",              # VRAM 4-7 GB        → ~0.5ث
    "mid_gpu":  "qwen2.5vl:7b",          # VRAM 6-8 GB        → ~0.5ث
    "high_gpu": "llama3.2-vision:11b",   # VRAM 8-12 GB       → ~0.7ث
    "pro_gpu":  "llava:34b",             # VRAM 24 GB+        → ~1.2ث
}

# ═══════════════════ معرفة اللعبة الكاملة ══════════════════════════════

# ── 7 مكافآت نيميسيس (Hard فقط، بالترتيب) ──────────────────────────
# المصدر: GameFAQs + residentevil.org
NEMESIS_DROPS = [
    {"n": 1, "item": "Eagle Parts A",      "tip": "لا تحتاج إطلاق نار كثير، اركض فوق جثة Brad فقط"},
    {"n": 2, "item": "Eagle Parts B",      "tip": "جمع A+B → Eagle 6.0 (أقوى مسدس)"},
    {"n": 3, "item": "First Aid Box",      "tip": "يحمل 3 بخاخات — قيّم جداً"},
    {"n": 4, "item": "M37 (Benelli) Parts A", "tip": "بندقية M37 أقوى من المسدس"},
    {"n": 5, "item": "M37 Parts B",        "tip": "جمع A+B → M37 Shotgun"},
    {"n": 6, "item": "First Aid Box",      "tip": "ثانية First Aid Box"},
    {"n": 7, "item": "Assault Rifle / ∞Ammo", "tip": "AR (أول لعبة) أو ذخيرة لانهائية (لعبة ثانية+)"},
]

# ── الـ 10 Live Selections — الخيار الأمثل لـ 100% ───────────────────
# المصدر: evilresource.com + pushsquare.com + residentevil.fandom.com
LIVE_SELECTIONS = [
    {
        "n":1, "pos":"أمام محطة الشرطة (Brad)",
        "choice_hard":"top",   "choice_easy":"bottom",
        "label_hard":"قاتل نيميسيس",
        "reason":"اركض فوق جثة Brad → STARS Card مبكراً + Eagle Parts A (أول قتل)",
        "reward":"Eagle Parts A + STARS Card",
    },
    {
        "n":2, "pos":"مطعم Grill 13 (مع كارلوس)",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"الاختباء في المطبخ",
        "reason":"جيل ترمي المصباح → نيميسيس يسقط → يسقط عنصراً على Hard",
        "reward":"عنصر من نيميسيس على Hard",
    },
    {
        "n":3, "pos":"مبنى Raccoon Press (كارلوس)",
        "choice_hard":"bottom","choice_easy":"bottom",
        "label_hard":"القفز من النافذة",
        "reason":"شارع خلفي → عشبتان حمراوتان + تجنب مواجهة نيميسيس",
        "reward":"2 أعشاب حمراء في الشارع الخلفي",
    },
    {
        "n":4, "pos":"محطة الكهرباء الفرعية",
        "choice_hard":"bottom","choice_easy":"bottom",
        "label_hard":"زيادة التيار الكهربائي",
        "reason":"يقتل كل الزومبيز عند البوابة → يوفر ذخيرة كثيرة",
        "reward":"ذخيرة محفوظة",
    },
    {
        "n":5, "pos":"كراج السيارات / حفرة",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"الصعود للأعلى",
        "reason":"أسرع + يتجنب شاشات تحميل إضافية",
        "reward":"توفير وقت",
    },
    {
        "n":6, "pos":"مطعم (إذا زرت المطبعة أولاً)",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"الاختباء في المطبخ",
        "reason":"نفس نتيجة Live Selection #2",
        "reward":"عنصر على Hard",
    },
    {
        "n":7, "pos":"شرفة برج الساعة",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"استخدام الضوء (Spotlight)",
        "reason":"يعمي نيميسيس → تدفعه من الشرفة → لا يظهر حتى Chronos Gear",
        "reward":"توفير وقت + ذخيرة",
    },
    {
        "n":8, "pos":"الجسر قبل Dead Factory",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"دفع نيميسيس",
        "reason":"تدخل Dead Factory من 2F مع Facility Key",
        "reward":"مسار أفضل",
    },
    {
        "n":9, "pos":"Dead Factory — نيقولاي + مروحية",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"التفاوض مع نيقولاي",
        "reason":"يُشتت نيقولاي → الصاروخ يظهر على الرادار",
        "reward":"مسار أفضل للنهاية",
    },
    {
        "n":10,"pos":"Dead Factory — نيميسيس الطافر النهائي",
        "choice_hard":"top",   "choice_easy":"top",
        "label_hard":"إبادة نيميسيس",
        "reason":"النهاية الكانونية + مشهد 'I'll give you STARS!'",
        "reward":"المشهد النهائي الأصلي",
    },
]

# ── تكتيكات الأعداء ────────────────────────────────────────────────────
ENEMY_TACTICS = {
    "zombie":       "رصاصة للرأس (headshot) = قتل فوري. أو تجاوز من الجانب وامش.",
    "zombie_dog":   "سريع! إزاحة جانبية (يسار أو يمين) + بندقية أو مسدس.",
    "hunter_alpha": "خطر: تقطع الرأس! ابتعد للخلف أثناء التصويب. لا تقترب أبداً.",
    "drain_deimos": "تسرق الأعشاب من حقيبتك! أطلق فور الاقتراب. مسدس كافٍ.",
    "brain_sucker": "مثل Drain Deimos تماماً. أطلق بسرعة قبل أن تقترب.",
    "grave_digger": "بوس! أطلق على الجزء الأمامي (الرأس) فقط. ابتعد عن الجزء الخلفي.",
    "nemesis":      "راجع NEMESIS_DROPS أعلاه. قاتله كل مرة على Hard للحصول على الغنائم.",
}

# ── ألغاز الكلاسيك PS1 ────────────────────────────────────────────────
PUZZLES = {
    "clock_tower": {
        "desc": "جواهر برج الساعة — الحل بحسب وقت الساعة المركزية",
        "solutions": {
            "23:00":["AMBER","OBSIDIAN","CRYSTAL"],
            "22:00":["AMBER","CRYSTAL","OBSIDIAN"],
            "21:00":["OBSIDIAN","AMBER","CRYSTAL"],
            "19:00":["OBSIDIAN","CRYSTAL","AMBER"],
            "18:00":["CRYSTAL","AMBER","OBSIDIAN"],
            "17:00":["CRYSTAL","OBSIDIAN","AMBER"],
        },
    },
    "electrical_transformer": {
        "desc": "محوّل الكهرباء",
        "solutions": {
            "20V":  ["RED","BLUE","BLUE","BLUE"],
            "120V": ["RED","RED","RED","BLUE"],
            "after_shock_blue": ["BLUE","BLUE","RED","BLUE"],
            "after_shock_red":  ["RED","RED","BLUE","RED"],
        },
    },
    "hospital_safe": {
        "desc": "خزنة المستشفى (Carlos) — 3 احتمالات",
        "solutions": ["SAFSPRIN (66%)", "ADRAVIL (22%)", "AQUACURE (11%)"],
    },
    "music_box": {
        "desc": "الصندوق الموسيقي v1.0",
        "solution": ["UP","DOWN","UP","UP","DOWN","UP"],
        "note_v11": "الإصدار 1.1 عشوائي — استمع للصوت",
    },
    "water_sample": {
        "desc": "لغز عينة الماء — طابق A B C D مع النموذج الملوّن",
        "note": "4 احتمالات عشوائية — انظر ألوان النموذج",
    },
}

# ── وصفات البارود الكاملة ──────────────────────────────────────────────
# C = A+B (مصنوع، غير موجود في العالم)
GUNPOWDER = {
    "A":   {"out":"handgun",        "qty":15},
    "AA":  {"out":"handgun",        "qty":35},
    "AAA": {"out":"handgun",        "qty":55},
    "BBA": {"out":"handgun",        "qty":60},  # أفضل للمسدس
    "B":   {"out":"shotgun",        "qty":7},
    "BB":  {"out":"shotgun",        "qty":18},
    "BBB": {"out":"shotgun",        "qty":30},
    "AAB": {"out":"shotgun",        "qty":20},
    "C":   {"out":"grenade_std",    "qty":10},   # C = A+B أولاً
    "AC":  {"out":"grenade_flame",  "qty":10},
    "BC":  {"out":"grenade_acid",   "qty":10},
    "CC":  {"out":"grenade_freeze", "qty":10},   # ★ الأفضل لنيميسيس ★
    "CCC": {"out":"magnum",         "qty":10},
    # بعد 8 مشاركات من نفس النوع → Enhanced Ammo (qty أعلى + ضرر أكبر)
}

# ════════════════════════ كشف GPU ══════════════════════════════════════
def detect_gpu() -> dict:
    info = {"ok":False, "name":"CPU", "vram":0}
    try:
        r = subprocess.run(
            ["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            n, mb = r.stdout.strip().split("\n")[0].split(", ")
            info = {"ok":True, "name":n.strip(), "vram":round(int(mb.strip())/1024,1)}
    except Exception:
        pass
    return info

def pick_model(gpu: dict) -> str:
    v = gpu["vram"]
    if not gpu["ok"] or v < 4:  return MODELS["cpu"]
    if v < 7:                   return MODELS["low_gpu"]
    if v < 9:                   return MODELS["mid_gpu"]
    if v < 20:                  return MODELS["high_gpu"]
    return MODELS["pro_gpu"]

# ════════════════════════ Ollama ════════════════════════════════════════
def ollama_running() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).status_code == 200
    except:
        return False

def installed_models() -> list:
    try:
        return [m["name"] for m in requests.get(f"{OLLAMA_URL}/api/tags",timeout=5).json().get("models",[])]
    except:
        return []

def pull_model(model: str) -> bool:
    print(f"\n  ↓ تحميل {model} (اول مرة فقط)...")
    try:
        return subprocess.run(["ollama","pull",model],timeout=900).returncode == 0
    except FileNotFoundError:
        print("  ✖ Ollama غير مثبت → https://ollama.com/download")
        return False

def is_duckstation_running() -> bool:
    """فحص إذا كان DuckStation يعمل"""
    try:
        import win32gui
        wins = []
        win32gui.EnumWindows(
            lambda h,r: r.append(h)
            if DUCKSTATION_WIN.lower() in win32gui.GetWindowText(h).lower() else None,
            wins)
        return len(wins) > 0
    except:
        return False

def launch_game():
    """تشغيل DuckStation واللعبة تلقائيا"""
    print("\n[0/4] تشغيل DuckStation...")
    
    # فحص إذا كان يعمل بالفعل
    if is_duckstation_running():
        print("  ✅ DuckStation يعمل بالفعل")
        time.sleep(2)
        return
    
    if os.path.exists(DUCKSTATION_PATH):
        subprocess.Popen([DUCKSTATION_PATH, GAME_ISO_PATH])
        print(f"  ✅DuckStation + RE3 Started")
        time.sleep(8)
    else:
        print(f"  ⚠️  المسار غير موجود: {DUCKSTATION_PATH}")
        print("  عرف المسار الصحيح في الإعدادات")

# ════════════════════════ حالة البوت ═══════════════════════════════════
class Mode(Enum):
    IDLE    = auto()
    EXPLORE = auto()
    COMBAT  = auto()
    FLEE    = auto()
    NEMESIS = auto()
    PUZZLE  = auto()
    CRAFT   = auto()
    HEAL    = auto()
    LIVESEL = auto()
    SAVE    = auto()
    CARLOS  = auto()
    MANUAL = auto()  # تحكم يدوي

@dataclass
class GameProgress:
    """يتتبع تقدم 100% في اللعبة"""
    nemesis_defeated:  int  = 0      # عدد مرات هزيمة نيميسيس (0-7)
    live_sel_next:     int  = 0      # الاختيار التالي (0-9)
    eagle_parts:       int  = 0      # 0→1→2 (يصبح Eagle 6.0)
    m37_parts:         int  = 0      # 0→1→2 (يصبح M37)
    has_first_aid_box: bool = False
    files_collected:   int  = 0      # ملفات القصة (لـ Jill's Diary)
    saves_used:        int  = 0      # للرتبة — أقل أفضل
    hp_items_used:     int  = 0      # للرتبة — أقل أفضل
    start_time:        float = field(default_factory=time.time)

    @property
    def elapsed_min(self) -> float:
        return (time.time() - self.start_time) / 60

    @property
    def rank_estimate(self) -> str:
        t = self.elapsed_min
        s = self.saves_used
        h = self.hp_items_used
        if t < 90  and s <= 3  and h <= 3:  return "S"
        if t < 120 and s <= 7  and h <= 6:  return "A"
        if t < 150 and s <= 10 and h <= 9:  return "B"
        if t < 180:                          return "C"
        return "D"

@dataclass
class BotState:
    running:       bool  = False
    paused:        bool  = False
    mode:          Mode  = Mode.IDLE
    difficulty:    str   = "hard"
    character:     str   = "jill"
    health:        str   = "FINE"
    health_pct:    int   = 100
    threat:        str   = "none"
    in_save_room:  bool  = False
    live_sel_flash:bool  = False
    frame:         int   = 0
    decisions:     int   = 0
    fps:           float = 0.0
    think_ms:      float = 0.0
    # جرد
    ammo_handgun:  int   = 15
    ammo_shotgun:  int   = 0
    ammo_freeze:   int   = 0
    ammo_flame:    int   = 0
    ammo_magnum:   int   = 0
    powder_a:      int   = 0
    powder_b:      int   = 0
    powder_mix_a:  int   = 0   # عداد لـ Enhanced
    powder_mix_b:  int   = 0
    herb_green:    int   = 0
    herb_red:      int   = 0
    ink_ribbons:   int   = 3
    # تتبع
    action_history:deque  = field(default_factory=lambda: deque(maxlen=25))
    last_think:    float  = 0.0
    session_start: float  = field(default_factory=time.time)
    log:           list   = field(default_factory=list)
    progress:      GameProgress = field(default_factory=GameProgress)

S  = BotState()
MODEL_NAME = MODELS["low_gpu"]   # يُحدَّث عند بدء التشغيل

# ════════════════════════ السجل ═════════════════════════════════════════
ICONS = {
    "INFO":"●","WARN":"⚠","ERR":"✖","ACT":"▶",
    "AI":"🤖","NEM":"☠","LIVE":"⚡","CRAFT":"⚗",
    "PUZZLE":"🔑","RANK":"🏆","PROG":"📌",
}
def log(msg:str, lvl:str="INFO"):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {ICONS.get(lvl,'●')} {msg}"
    print(line)
    S.log.append(line)
    if len(S.log) > 120: S.log.pop(0)

# ════════════════════════ التقاط الشاشة ════════════════════════════════
def capture() -> Optional[Image.Image]:
    try:
        import win32gui, win32con
        wins = []
        win32gui.EnumWindows(
            lambda h,r: r.append(h)
            if DUCKSTATION_WIN.lower() in win32gui.GetWindowText(h).lower() else None,
            wins)
        if wins:
            # تفعيل النافذة
            win32gui.SetForegroundWindow(wins[0])
            time.sleep(0.3)
            x,y,x2,y2 = win32gui.GetWindowRect(wins[0])
            with mss.mss() as sc:
                sh = sc.grab({"top":y,"left":x,"width":x2-x,"height":y2-y})
                return Image.frombytes("RGB",sh.size,sh.bgra,"raw","BGRX")
    except Exception:
        pass
    # fallback للشاشة كاملة
    with mss.mss() as sc:
        sh = sc.grab(sc.monitors[1])
        return Image.frombytes("RGB",sh.size,sh.bgra,"raw","BGRX")

def compress(img:Image.Image, w=480, q=62) -> str:
    img.thumbnail((w, int(w*0.75)), Image.LANCZOS)
    b = BytesIO(); img.save(b,"JPEG",quality=q)
    return base64.b64encode(b.getvalue()).decode()

# ════════════════════════ كشف سريع ════════════════════════════════════
def fast_detect(img:Image.Image) -> dict:
    W, H = img.size

    # Live Selection: ومضة بيضاء تملأ المركز
    zone  = img.crop((int(W*.08),int(H*.08),int(W*.92),int(H*.92)))
    pix   = list(zone.convert("L").getdata())
    bright= sum(1 for p in pix if p>226)/len(pix)
    live  = bright > LIVE_SEL_BRIGHT

    # الصحة من HUD أسفل يسار
    hud = img.crop((0,int(H*.875),int(W*.28),H))
    hp  = list(hud.getdata())
    r   = sum(p[0] for p in hp)/len(hp)
    g   = sum(p[1] for p in hp)/len(hp)
    if   g>100 and g>r*1.32: health,pct = "FINE",   85
    elif r>112 and g>78:     health,pct = "CAUTION", 44
    elif r>108 and g<62:     health,pct = "DANGER",  14
    else:                     health,pct = "FINE",   70

    # غرفة آمنة: لون هادئ بدون أحمر في زاوية الشاشة
    corner = img.crop((0,0,int(W*.12),int(H*.12)))
    cpix   = list(corner.getdata())
    cr     = sum(p[0] for p in cpix)/len(cpix)
    save_room = cr < 75

    # كشف القتال: أحمر كثير في المركز (دم أو musuh)
    center = img.crop((int(W*.3),int(H*.3),int(W*.7),int(H*.7)))
    cp = list(center.getdata())
    red_zone = sum(1 for p in cp if p[0] > p[1]*1.5 and p[0] > 120)/len(cp)
    combat_detected = red_zone > 0.15

    # كشف نيميسيس: جسم كبير داكن في اليمين
    nemesis_zone = img.crop((int(W*.6),int(H*.2),int(W*.95),int(H*.8)))
    np = list(nemesis_zone.getdata())
    dark_big = sum(1 for p in np if p[0]<60 and p[1]<60 and p[2]<60)/len(np)
    nemesis_detected = dark_big > 0.20

    return {"live":live,"health":health,"pct":pct,
            "save_room":save_room,"bright":bright,
            "combat":combat_detected,"nemesis":nemesis_detected}

# ════════════════════════ System Prompt ════════════════════════════════
def build_prompt() -> str:
    p     = S.progress
    ls    = LIVE_SELECTIONS[p.live_sel_next] if p.live_sel_next < 10 else None
    nxt_d = NEMESIS_DROPS[p.nemesis_defeated] if p.nemesis_defeated < 7 else None
    craft_hint = ""
    if S.powder_a >= 2 and S.ammo_handgun < 15:
        craft_hint = "لديك A×2 → AA → 35 رصاصة مسدس"
    elif S.powder_a >= 1 and S.powder_b >= 1:
        craft_hint = "A+B → C → ثم CC → 10 قنابل جليد (الأفضل لنيميسيس)"
    elif S.powder_b >= 2 and S.ammo_shotgun < 10:
        craft_hint = "B×2 → BB → 18 قذيفة بندقية"

    return f"""أنت بوت يتحكم في Resident Evil 3 Nemesis الكلاسيك PS1 1999 على DuckStation.
هدفك: إتمام اللعبة 100% على Hard Mode.

═══ حالة اللعبة الحالية ═══
الشخصية: {S.character.upper()} | الصحة: {S.health}
نيميسيس هُزم: {p.nemesis_defeated}/7
المكافأة التالية: {nxt_d['item'] if nxt_d else 'مكتمل!'}
Live Selection التالي: #{p.live_sel_next+1}/10 — {ls['pos'] if ls else 'مكتمل!'}
{'الاختيار الأمثل: ' + ls['label_hard'] + ' ← ' + ls['reason'] if ls else ''}
الرتبة المتوقعة: {p.rank_estimate} ({p.elapsed_min:.0f} دقيقة / حفظ:{p.saves_used} / علاج:{p.hp_items_used})
ذخيرة: مسدس={S.ammo_handgun} بندقية={S.ammo_shotgun} جليد={S.ammo_freeze}
بارود: A={S.powder_a} B={S.powder_b} | {craft_hint}

═══ تحكم PS1 (تانك كونترول) ═══
↑↓←→=حركة | Z=×(فعل) | X=○(جري) | A=□(حقيبة) | S=△(خريطة)
Q=L1(تصويب) | E=R1(إطلاق) | R=R2(تهرب)
↓+Z = استدارة 180° | Q+Z بالتوقيت = تهرب يدوي (Hard فقط)

═══ قواعد 100% ═══
• قاتل نيميسيس كل مرة على Hard للحصول على جميع 7 مكافآت
• لا تُهدر ذخيرة على الغربان أو الديدان الأرضية
• اجمع كل الملفات (Files) → تفتح Jill's Diary
• أعد التحميل دائماً من قائمة الحقيبة (لا auto-reload)
• احفظ Ink Ribbons — محدودة على Hard
• الرتبة S: أقل من 90 دقيقة + 3 حفظ + 3 علاج

═══ الأعداء ═══
زومبي: رأس=قتل فوري، أو تجاوز جانبي
كلاب: إزاحة جانبية + بندقية
Hunter Alpha: ★ تقطع الرأس ★ → تراجع + أطلق من مسافة
Drain Deimos: تسرق أعشابك! → أطلق فور الاقتراب
Brain Sucker: مثل Drain Deimos
Grave Digger (بوس): أطلق على الجزء الأمامي فقط

═══ نيميسيس 100% ═══
• قاتله في كل مشاركة Hard → مكافأة بالترتيب (Eagle→M37→Rifle)
• تكتيك: مرّ من يمينه + أطلق (أو R1+R2 قبل اللكمة)
• قنابل جليد (CC) = الأقوى ضده → يتراجع فوراً
• إذا قبض عليك → اضغط كل الأزرار بسرعة للإفلات
• لا يدخل غرف الحفظ → الهرب إليها إذا الصحة سيئة

═══ البارود ═══
C=A+B أولاً | CC=جليد★ | AC=لهب | BC=حمض | CCC=ماغنوم
بعد 8 مشاركات → Enhanced Ammo (أقوى، يجعل نيميسيس يتراجع)

═══ ألغاز الكلاسيك ═══
برج الساعة: وقت الساعة يحدد الجواهر
23→A,O,C | 22→A,C,O | 21→O,A,C | 19→O,C,A | 18→C,A,O | 17→C,O,A
محوّل الكهرباء: 20V=R,B,B,B | 120V=R,R,R,B
خزنة المستشفى: SAFSPRIN(66%) أو ADRAVIL(22%)
صندوق موسيقي v1.0: UP,DOWN,UP,UP,DOWN,UP

═══ رد بـ JSON فقط (لا نص آخر) ═══
{{
  "health":      "FINE|CAUTION|DANGER",
  "character":   "jill|carlos",
  "threat":      "none|zombie|zombie_dog|hunter|drain_deimos|brain_sucker|nemesis|grave_digger|boss",
  "situation":   "وصف قصير",
  "in_save_room":false,
  "live_sel":    false,
  "live_choice": "top|bottom",
  "puzzle":      false,
  "puzzle_type": "none|clock_tower|electrical|hospital_safe|music_box|water_sample",
  "need_heal":   false,
  "need_craft":  false,
  "action":      "explore|combat|combat_nemesis|flee|heal|craft|puzzle|live_sel|save|interact",
  "keys":        [],
  "hold":        [],
  "dur":         0.22,
  "why":         "سبب"
}}"""

# ════════════════════════ استدعاء Ollama ═══════════════════════════════
def ask_ai(img:Image.Image) -> dict:
    hist = " → ".join(list(S.action_history)[-6:]) or "—"
    ctx  = (f"الصحة:{S.health} | تهديد:{S.threat} | "
            f"{'⚡LIVE!' if S.live_sel_flash else ''} | آخر:{hist}")

    payload = {
        "model":   MODEL_NAME,
        "messages":[
            {"role":"system", "content":build_prompt()},
            {"role":"user",   "content":f"حلّل الشاشة.\n{ctx}",
             "images":[compress(img)]},
        ],
        "stream":  False,
        "options": {"temperature":0.05,"top_p":0.85,"num_predict":130},
    }
    
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        if "message" not in data:
            raise ValueError("No message in response")
        if "content" not in data["message"]:
            raise ValueError("No content in message")
        
        txt = data["message"]["content"].strip()
        if not txt:
            raise ValueError("Empty response from AI")
        
        # استخراج JSON من_response
        txt = txt.strip()
        # إزالة markdown إن وجدت
        if txt.startswith("```"):
            parts = txt.split("```")
            txt = parts[1] if len(parts) > 1 else parts[0]
            if txt.startswith("json"): txt = txt[4:]
        
        txt = txt.strip()
        s = txt.find("{")
        e = txt.rfind("}")
        if s == -1 or e == -1 or e <= s:
            raise ValueError(f"No JSON found in response: {txt[:100]}")
        
        txt = txt[s:e+1]
        return json.loads(txt)
        
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Ollama connection error: {e}")

# ════════════════════════ تعيين المفاتيح ══════════════════════════════
KM = {
    "up":"up","down":"down","left":"left","right":"right",
    "action":"z","cancel":"x","aim":"q","shoot":"e",
    "inventory":"a","map":"s","dodge":"r",
    "start":"enter","select":"backspace",
}
def tap(keys:list, dur:float=0.18):
    r=[KM.get(k,k) for k in keys]
    for k in r: keyboard.press(k)
    time.sleep(max(0.04,dur))
    for k in reversed(r): keyboard.release(k)

def run(hold_k:list, tap_k:list, dur:float=0.44):
    h=[KM.get(k,k) for k in hold_k]; t=[KM.get(k,k) for k in tap_k]
    for k in h: keyboard.press(k)
    time.sleep(0.04)
    for k in t: keyboard.press(k)
    time.sleep(dur)
    for k in t: keyboard.release(k)
    time.sleep(0.04)
    for k in h: keyboard.release(k)

def manual_fallback():
    """تحكم يدوي عند فشل AI"""
    log("↩ تحكم يدوي", "WARN")
    if S.threat == "nemesis":
        if S.health in ("FINE","CAUTION"):
            tap(["right"],0.12); time.sleep(0.05)
            run(["aim"],["shoot"],0.25)
        else:
            tap(["down","action"],0.14); time.sleep(0.05)
            run(["cancel"],["up"],0.60)
    elif S.threat == "enemy":
        tap([random.choice(["left","right"])],0.14)
        run(["aim"],["shoot"],0.22)
    elif S.live_sel_flash:
        p = S.progress
        if p.live_sel_next < 10:
            ls = LIVE_SELECTIONS[p.live_sel_next]
            ch = ls["choice_hard"] if S.difficulty=="hard" else ls["choice_easy"]
            if ch == "bottom": tap(["down"],0.12)
            tap(["action"],0.18)
            S.progress.live_sel_next += 1
    elif S.health == "DANGER":
        tap(["inventory"],0.25)
        S.progress.hp_items_used += 1
    else:
        run(["cancel"],["up"],0.35)
    time.sleep(0.15)

# ════════════════════════ تكتيكات نيميسيس ══════════════════════════════
def nemesis_fight():
    """
    قاتل نيميسيس للحصول على مكافأته على Hard.
    الترتيب: Eagle A → Eagle B → First Aid Box → M37 A → M37 B → ...
    """
    p       = S.progress
    drop    = NEMESIS_DROPS[min(p.nemesis_defeated, 6)]
    tactic  = random.choices(
        ["right","dodge","freeze","magnum"],
        weights=[0.40,0.30,0.20,0.10], k=1)[0]

    log(f"☠ نيميسيس مواجهة #{p.nemesis_defeated+1} → المكافأة: {drop['item']}", "NEM")

    if tactic == "right":
        log("☠ تكتيك: يمين + رصاصة", "NEM")
        tap(["right"],0.14); time.sleep(0.06)
        run(["aim"],["shoot"],0.30)

    elif tactic == "dodge":
        log("☠ تكتيك: تهرب R1+R2", "NEM")
        keyboard.press(KM["shoot"]); keyboard.press(KM["dodge"])
        time.sleep(0.17)
        keyboard.release(KM["shoot"]); keyboard.release(KM["dodge"])
        time.sleep(0.1)
        run(["aim"],["shoot"],0.25)

    elif tactic == "freeze" and S.ammo_freeze >= 2:
        log("☠ تكتيك: قنابل جليد ★", "NEM")
        run(["aim"],["shoot"],0.35)
        S.ammo_freeze = max(0, S.ammo_freeze-2)

    else:  # magnum أو افتراضي
        log("☠ تكتيك: 180° + قذيفة", "NEM")
        tap(["down","action"],0.16); time.sleep(0.08)
        run(["aim"],["shoot"],0.35)

    S.progress.nemesis_defeated += 1
    S.action_history.append(f"nemesis_fight_{p.nemesis_defeated}")

def nemesis_flee():
    """هرب سريع من نيميسيس (إذا الصحة سيئة أو اللعبة على Easy)"""
    log("☠ هرب من نيميسيس!", "NEM")
    tap(["down","action"],0.16); time.sleep(0.07)
    run(["cancel"],[random.choice(["up","left","right"])],0.80)
    S.action_history.append("nemesis_flee")

# ════════════════════════ منفّذ القرار الرئيسي ═════════════════════════
def execute(dec:dict):
    keys   = dec.get("keys",[])
    hold_k = dec.get("hold",[])
    dur    = float(dec.get("dur",0.22))
    action = dec.get("action","explore")
    threat = dec.get("threat","none")
    health = dec.get("health", S.health)

    # ── تحديث الحالة ──
    S.health        = health
    S.threat        = threat
    S.in_save_room  = dec.get("in_save_room",False)
    S.live_sel_flash= dec.get("live_sel",False)
    S.character     = dec.get("character",S.character)

    log(f"🤖 [{S.decisions}] {dec.get('why','?')} ({S.think_ms:.0f}ms)", "AI")

    # ══ أولوية 0: DANGER → علاج فوري ══
    if health == "DANGER" or dec.get("need_heal"):
        log("🔴 DANGER → علاج", "ERR")
        tap(["inventory"],0.30)
        S.mode = Mode.HEAL
        S.progress.hp_items_used += 1
        S.action_history.append("heal_danger")
        return

    # ══ أولوية 1: Live Selection → فوري ══
    if dec.get("live_sel") or S.live_sel_flash:
        p   = S.progress
        idx = p.live_sel_next
        if idx < 10:
            ls     = LIVE_SELECTIONS[idx]
            choice = ls["choice_hard"] if S.difficulty=="hard" else ls["choice_easy"]
            log(f"⚡ Live Sel #{idx+1}: {ls['label_hard']} → {choice}", "LIVE")
        else:
            choice = dec.get("live_choice","top")
        if choice == "bottom":
            tap(["down"],0.14); time.sleep(0.07)
        tap(["action"],0.22)
        S.mode = Mode.LIVESEL
        S.progress.live_sel_next = min(idx+1,10)
        S.action_history.append(f"live_sel_{idx}")
        return

    # ══ أولوية 2: نيميسيس ══
    if threat == "nemesis":
        S.mode = Mode.NEMESIS
        # على Hard → قاتل لأخذ المكافأة (إذا صحة جيدة)
        if S.difficulty == "hard" and health in ("FINE","CAUTION") \
                and S.progress.nemesis_defeated < 7:
            nemesis_fight()
        else:
            nemesis_flee()
        return

    # ══ أولوية 3: بوس ══
    if threat in ("grave_digger","boss"):
        S.mode = Mode.COMBAT
        log("⚔ بوس! أطلق على الجزء الأمامي", "ACT")
        run(["aim"],["shoot"],0.45)
        time.sleep(0.1)
        tap([random.choice(["left","right"])],0.2)
        S.action_history.append("boss")
        return

    # ══ أولوية 4: لغز ══
    if dec.get("puzzle"):
        S.mode = Mode.PUZZLE
        ptype  = dec.get("puzzle_type","other")
        log(f"🔑 لغز: {ptype}", "PUZZLE")
        if keys: tap(keys,dur)
        S.action_history.append(f"puzzle_{ptype}")
        return

    # ══ أولوية 5: صياغة بارود (في غرفة آمنة فقط) ══
    if dec.get("need_craft") and S.in_save_room:
        S.mode = Mode.CRAFT
        log(f"⚗ صياغة (A={S.powder_a}, B={S.powder_b})", "CRAFT")
        tap(["inventory"],0.28); time.sleep(0.55)
        S.action_history.append("craft")
        return

    # ══ أولوية 6: قتال عادي ══
    if action == "combat":
        S.mode = Mode.COMBAT
        if threat == "hunter_alpha":
            tap(["down"],0.2); time.sleep(0.07)
            run(["aim"],["shoot"],0.35)
        elif threat in ("zombie_dog","drain_deimos","brain_sucker"):
            tap([random.choice(["left","right"])],0.16)
            run(["aim"],["shoot"],0.28)
        else:
            run(["aim"],["shoot"],dur)
        S.action_history.append(f"combat_{threat}")
        return

    # ══ أولوية 7: تهرب يدوي (Hard) ══
    if action == "combat_nemesis" and S.difficulty == "hard":
        log("↪ تهرب يدوي L1+×", "ACT")
        keyboard.press(KM["aim"]); time.sleep(0.04)
        keyboard.press(KM["action"]); time.sleep(0.14)
        keyboard.release(KM["action"]); keyboard.release(KM["aim"])
        S.action_history.append("manual_dodge")
        return

    # ══ أولوية 8: هروب ══
    if action == "flee":
        S.mode = Mode.FLEE
        dk = keys[0] if keys else "up"
        run(["cancel"],[dk],dur)
        S.action_history.append(f"flee_{dk}")
        return

    # ══ أولوية 9: استكشاف / افتراضي ══
    S.mode = Mode.EXPLORE
    if hold_k and keys:
        run(hold_k, keys, dur)
    elif keys:
        tap(keys, dur)
    else:
        hist  = list(S.action_history)[-6:]
        dirs  = ["up","up","left","right","up","up"]
        chosen= next((d for d in dirs if f"auto_{d}" not in hist),"up")
        run(["cancel"],[chosen],0.42)
        S.action_history.append(f"auto_{chosen}")
        return

    S.action_history.append(f"{action}:{','.join(keys)}")
    time.sleep(0.10 if threat!="none" else 0.18)

# ════════════════════════ معدل التفكير ════════════════════════════════
def think_rate() -> float:
    if S.live_sel_flash:            return THINK_LIVE_SEL
    if S.threat == "nemesis":       return THINK_NEMESIS
    if S.health == "DANGER":        return THINK_COMBAT
    if S.mode in (Mode.COMBAT,Mode.FLEE): return THINK_COMBAT
    return THINK_EXPLORE

# ════════════════════════ الحلقة الرئيسية ══════════════════════════════
def bot_loop():
    log(f"═══ RE3 Final Bot — نموذج:{MODEL_NAME} ═══")
    times = []
    while S.running:
        if S.paused: time.sleep(0.5); continue

        t0 = time.time(); S.frame += 1

        img = capture()
        if img is None:
            log("فشل التقاط الشاشة","WARN"); time.sleep(1); continue

        fd = fast_detect(img)
        S.live_sel_flash = fd["live"]
        S.health         = fd["health"]
        S.health_pct     = fd["pct"]
        S.in_save_room   = fd["save_room"]

        # كشف_fast للمعارك
        if fd.get("combat") and S.threat == "none":
            S.threat = "enemy"
            log("⚔ عدو مكتشف!", "ACT")
        if fd.get("nemesis") and S.threat == "none":
            S.threat = "nemesis"
            log("☠ نيميسيس!", "NEM")

        if S.live_sel_flash:
            log(f"⚡ Live Selection! (بياض {fd['bright']:.0%})","LIVE")

        now = time.time()
        if now - S.last_think >= think_rate() or S.live_sel_flash:
            try:
                ai0       = time.time()
                dec       = ask_ai(img)
                S.think_ms= (time.time()-ai0)*1000
                S.decisions += 1
                S.last_think = time.time()
                execute(dec)
            except json.JSONDecodeError as je:
                log(f"JSON:{je}","ERR")
                manual_fallback()
            except requests.ConnectionError:
                log("Ollama غير متصل!","ERR")
                manual_fallback()
            except Exception as ex:
                log(f"خطأ:{ex}","ERR")
                manual_fallback()

        elapsed = time.time()-t0
        times.append(elapsed)
        if len(times)>30: times.pop(0)
        S.fps = round(1/(sum(times)/len(times)),1) if times else 0
        time.sleep(max(0, CAPTURE_SEC-elapsed))

    log("═══ البوت توقف ═══")

def status_loop():
    while S.running:
        time.sleep(10)
        p  = S.progress
        up = int(time.time()-S.session_start)
        m, s = divmod(up,60)
        print(f"\n{'═'*60}")
        print(f"  الوضع: {S.mode.name} | الصحة: {S.health} | {S.character.upper()}")
        print(f"  نيميسيس: {p.nemesis_defeated}/7 هزيمة | Live: #{p.live_sel_next}/10")
        print(f"  Eagle Parts: {p.eagle_parts}/2 | M37 Parts: {p.m37_parts}/2")
        print(f"  مسدس:{S.ammo_handgun} بندقية:{S.ammo_shotgun} جليد:{S.ammo_freeze}")
        print(f"  بارود A:{S.powder_a} B:{S.powder_b}")
        print(f"  الرتبة: {p.rank_estimate} | {p.elapsed_min:.0f}د | حفظ:{p.saves_used} | علاج:{p.hp_items_used}")
        print(f"  AI:{S.think_ms:.0f}ms | FPS:{S.fps} | وقت:{m}د{s}ث")
        print(f"{'═'*60}\n")

# ════════════════════════ الإعداد والتشغيل ══════════════════════════════
def run_setup():
    global MODEL_NAME
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  RE3: NEMESIS CLASSIC (PS1 1999) — FINAL AI BOT                       ║
║  100% Completion ★ Hard Mode ★ Local AI ★ No Internet                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║  اوامر: [ENTER] بدء | [P] توقف | [Q] خروج | [S] حالة | [?] مساعدة    ║
╚═══════════════════════════════════════════════════════════════════════╝
""")

    # 0. تشغيل تلقائي
    if AUTO_LAUNCH:
        launch_game()

    # 1. GPU
    print("[1/4] كشف GPU...")
    gpu = detect_gpu()
    if gpu["ok"]:
        print(f"  ✅ {gpu['name']} | {gpu['vram']} GB VRAM")
    else:
        print("  ℹ️  CPU فقط — سيعمل بـ moondream (الأسرع على CPU)")

    MODEL_NAME = pick_model(gpu)
    print(f"\n  النموذج المقترح: {MODEL_NAME}")
    custom = input("  اكتب اسم نموذج آخر أو ENTER للقبول: ").strip()
    if custom: MODEL_NAME = custom

    # 2. Ollama
    print("\n[2/4] فحص Ollama...")
    if not ollama_running():
        print("""
  ❌ Ollama لا يعمل!
  ─────────────────────────────────────────
  1. حمّل Ollama: https://ollama.com/download
  2. ثبّته وشغّله: ollama serve
  3. ثم أعد تشغيل البوت
        """)
        input("ENTER للخروج...")
        return
    print("  ✅ Ollama يعمل")

    # 3. النموذج
    print(f"\n[3/4] فحص النموذج {MODEL_NAME}...")
    installed = installed_models()
    base = MODEL_NAME.split(":")[0]
    has  = any(base in m for m in installed)
    if not has:
        yn = input(f"  النموذج غير مثبت. تحميل {MODEL_NAME}؟ (y/n): ").strip().lower()
        if yn == "y":
            if not pull_model(MODEL_NAME): return
        else:
            print("  النماذج المتاحة:", ", ".join(installed) or "لا يوجد")
            MODEL_NAME = input("  اكتب اسم نموذج مثبت: ").strip()
    else:
        print(f"  ✅ {MODEL_NAME} جاهز")

    # 4. الإعدادات
    diff = CONFIG.get("difficulty", "hard")
    if CONFIG.get("auto_start"):
        S.difficulty = diff
        print(f"  ★ Difficulty: {S.difficulty.upper()}")
    else:
        diff = input("  الصعوبة (hard/easy) [hard]: ").strip().lower()
        S.difficulty = "easy" if diff == "easy" else "hard"
    
    if S.difficulty == "hard":
        print("  ★ Hard Mode: تهرب يدوي + نيميسيس يعطي مكافآت + Ranking + Epilogues")
    else:
        print("  ℹ Easy Mode: تهرب تلقائي — لكن لا رتبة ولا مكافآت نيميسيس")

    print(f"""
  ╔═══════════════════════════════════╗
  ║  نموذج AI: {MODEL_NAME:<23}║
  ║  الصعوبة: {S.difficulty.upper():<24}║
  ║  هدف الرتبة: S (< 90د, ≤3 حفظ)  ║
  ╚═══════════════════════════════════╝""")

    if CONFIG.get("auto_start"):
        print("\n  ⏩ بدء تلقائي...")
        start_bot()
    else:
        input("\n  [ENTER للبدء]\n")
        start_bot()

def start_bot():
    S.running       = True
    S.session_start = time.time()
    S.progress.start_time = time.time()
    S.mode          = Mode.EXPLORE

    for t in [
        threading.Thread(target=bot_loop,   daemon=True),
        threading.Thread(target=status_loop, daemon=True),
    ]: t.start()

# قائمة الأوامر
    help_text = """
  اوامر التحكم:
  ─────────────────────────────────────────
  [ENTER]          : بدء / استئناف
  P                : ايقاف مؤقت / استئناف
  Q                : إنهاء البوت
  S                : عرض الحالة الكاملة
  I                : عرض الجرد
  R                : عرض تقدم 100% و الرتبة
  N                : نيميسيس هُزم يدوياً (+1)
  D [name]         : تغيير النموذج
  ammo gun N       : تحديث ذخيرة (gun=handgun/shotgun/freeze)
  powder a N       : تحديث بارود A
  powder b N       : تحديث بارود B
  save             : تسجيل حفظ (+1 للرتبة)
  M                : تحكم يدوي (تبديل)
  UP/DOWN/LEFT/RIGHT : حركة يدوية
  Z               : زر × (فعل)
  X               : زر ○ (جري)
  A               : زر □ (حقيبة)
  ?                : عرض هذه المساعدة
  ─────────────────────────────────────────
  [ENTER]          : بدء / استئناف
  P                : إيقاف مؤقت / استئناف
  Q                : إنهاء البوت
  S                : عرض الحالة الكاملة
  I                : عرض الجرد
  R                : عرض تقدم 100% و الرتبة
  N                : نيميسيس هُزم يدوياً (+1)
  D [name]         : تغيير النموذج
  ammo gun N       : تحديث ذخيرة (gun=handgun/shotgun/freeze)
  powder a N       : تحديث بارود A
  powder b N       : تحديث بارود B
  save             : تسجيل حفظ (+1 للرتبة)
  ?                : عرض هذه المساعدة
  ─────────────────────────────────────────"""

    try:
        while S.running:
            cmd = input().strip()
            c   = cmd.lower()

            if c in ("q","quit","exit"):
                S.running = False

            elif c == "p":
                S.paused = not S.paused
                log("⏸ مؤقت" if S.paused else "▶ مستأنف")

            elif c == "s":
                p = S.progress
                print(f"\n  الوضع:{S.mode.name} | الصحة:{S.health} | AI:{S.think_ms:.0f}ms")
                print(f"  نيميسيس:{p.nemesis_defeated}/7 | Live Sel:{p.live_sel_next}/10")
                print(f"  الرتبة:{p.rank_estimate} | {p.elapsed_min:.0f}د | حفظ:{p.saves_used}")
                if p.nemesis_defeated < 7:
                    nd = NEMESIS_DROPS[p.nemesis_defeated]
                    print(f"  المكافأة التالية من نيميسيس: {nd['item']}")
                if p.live_sel_next < 10:
                    ls = LIVE_SELECTIONS[p.live_sel_next]
                    print(f"  Live Selection التالي: #{ls['n']} {ls['pos']}")
                    print(f"  الخيار الأمثل: {ls['label_hard']}")

            elif c == "i":
                print(f"\n  مسدس:{S.ammo_handgun} | بندقية:{S.ammo_shotgun}")
                print(f"  جليد:{S.ammo_freeze} | لهب:{S.ammo_flame} | ماغنوم:{S.ammo_magnum}")
                print(f"  بارود A:{S.powder_a} B:{S.powder_b}")
                print(f"  أعشاب: خضراء={S.herb_green} حمراء={S.herb_red}")
                print(f"  Ink Ribbons:{S.ink_ribbons}")

            elif c == "r":
                p = S.progress
                print(f"\n  ══ تقدم 100% ══")
                print(f"  Eagle Parts: {p.eagle_parts}/2 {'→ Eagle 6.0 ✅' if p.eagle_parts>=2 else ''}")
                print(f"  M37 Parts:   {p.m37_parts}/2  {'→ M37 ✅' if p.m37_parts>=2 else ''}")
                print(f"  نيميسيس:     {p.nemesis_defeated}/7 هزيمة")
                print(f"  Live Sel:    {p.live_sel_next}/10")
                print(f"  ══ الرتبة ══")
                print(f"  وقت:{p.elapsed_min:.1f}د | حفظ:{p.saves_used} | علاج:{p.hp_items_used}")
                print(f"  الرتبة المتوقعة: {p.rank_estimate}")

            elif c == "n":
                S.progress.nemesis_defeated = min(S.progress.nemesis_defeated+1,7)
                d = NEMESIS_DROPS[min(S.progress.nemesis_defeated-1,6)]
                log(f"☠ نيميسيس #{S.progress.nemesis_defeated}: {d['item']}","NEM")

            elif c.startswith("d "):
                MODEL_NAME = c[2:].strip()
                log(f"نموذج → {MODEL_NAME}")

            # ── تحكم يدوي ──
            elif c == "m":
                S.paused = True
                S.mode = Mode.MANUAL
                log("⌨ تحكم يدوي - اكتب UP/DOWN/LEFT/RIGHT/Z/X/A/Q/E/R")

            elif S.mode == Mode.MANUAL:
                if c == "up":     tap(["up"], 0.15)
                elif c == "down":   tap(["down"], 0.15)
                elif c == "left":   tap(["left"], 0.15)
                elif c == "right":  tap(["right"], 0.15)
                elif c == "z":     tap(["action"], 0.12)
                elif c == "x":     tap(["cancel"], 0.12)
                elif c == "a":     tap(["inventory"], 0.15)
                elif c == "s":     tap(["map"], 0.12)
                elif c == "q":     tap(["aim"], 0.10)
                elif c == "e":     tap(["shoot"], 0.20)
                elif c == "r":     tap(["dodge"], 0.15)
                elif c == "p":
                    S.mode = Mode.EXPLORE
                    S.paused = False
                    log("▶ استئناف AI")
                else:
                    print(f" 的方向键: UP|DOWN|LEFT|RIGHT | الأزرار: Z|X|A|S|Q|E|R | P=خروج")

            elif c == "save":
                S.progress.saves_used += 1
                S.ink_ribbons = max(0,S.ink_ribbons-1)
                log(f"💾 حفظ #{S.progress.saves_used} | Ink Ribbons:{S.ink_ribbons}")

            elif c.startswith("ammo "):
                p = c.split()
                if len(p)==3:
                    v=int(p[2])
                    if p[1]=="handgun":  S.ammo_handgun=v
                    elif p[1]=="shotgun": S.ammo_shotgun=v
                    elif p[1]=="freeze":  S.ammo_freeze=v
                    elif p[1]=="flame":   S.ammo_flame=v
                    log(f"ذخيرة {p[1]}={v}")

            elif c.startswith("powder "):
                p = c.split()
                if len(p)==3:
                    v=int(p[2])
                    if p[1]=="a": S.powder_a=v
                    elif p[1]=="b": S.powder_b=v
                    log(f"بارود {p[1]}={v}")

            elif c == "?":
                print(help_text)

    except KeyboardInterrupt:
        S.running = False

    # ملخص نهائي
    p = S.progress
    print(f"""
╔══════════════════════════════════════════════╗
║           ملخص الجلسة النهائي                ║
╠══════════════════════════════════════════════╣
║  نيميسيس هُزم: {p.nemesis_defeated}/7                        ║
║  Live Selections: {p.live_sel_next}/10                ║
║  Eagle 6.0: {'✅' if p.eagle_parts>=2 else '—'} | M37: {'✅' if p.m37_parts>=2 else '—'}              ║
║  الرتبة: {p.rank_estimate} | الوقت: {p.elapsed_min:.0f} دقيقة        ║
║  حفظ: {p.saves_used} | علاج: {p.hp_items_used}                    ║
╚══════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    run_setup()
