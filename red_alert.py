#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Red Alert Monitor v3.0  -  התרעות צבע אדום
Real-time IDF Home Front Command alerts
"""
import sys, os, json, time, math, threading, subprocess, ctypes, winreg
from datetime import datetime
from collections import deque

# ── Elevation (run as admin) ─────────────────────────────────────
def _ensure_admin():
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable,
                f'"{os.path.abspath(__file__)}"', None, 1)
            sys.exit(0)
    except Exception:
        pass

_ensure_admin()

# ── auto-install ─────────────────────────────────────────────────
for _pkg in ["requests", "PyQt5"]:
    try:
        __import__(_pkg)
    except ImportError:
        subprocess.check_call([sys.executable,"-m","pip","install",_pkg,"--quiet"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QSystemTrayIcon, QMenu, QAction, QDialog,
    QListWidget, QListWidgetItem, QLineEdit, QAbstractItemView,
    QDesktopWidget, QSizeGrip, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QLinearGradient,
    QIcon, QPixmap, QPainterPath
)

_HAS_WEB = False
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    _HAS_WEB = True
except ImportError:
    pass

APP_VERSION = "3.0.0"
APP_NAME    = "התרעות צבע אדום"
POLL_MS     = 2000
OREF_URL    = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
API_HEADERS = {
    "Referer":          "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Accept-Language":  "he-IL,he;q=0.9",
}
CFG_PATH    = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                           "RedAlert", "config.json")
AUTORUN_REG = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ════════════════════════════════════════════════════════════════
#  CITY COORDINATES
# ════════════════════════════════════════════════════════════════
CITY_COORDS = {
    "תל אביב - מרכז העיר":(32.080,34.781),"תל אביב - דרום העיר":(32.053,34.761),
    "תל אביב - צפון העיר":(32.100,34.792),"ירושלים":(31.768,35.214),
    "חיפה":(32.794,34.990),"באר שבע":(31.252,34.791),"אשדוד":(31.804,34.655),
    "אשקלון":(31.669,34.574),"נתניה":(32.329,34.856),"רחובות":(31.894,34.811),
    "בת ים":(32.017,34.750),"חולון":(32.011,34.774),"רמת גן":(32.068,34.824),
    "בני ברק":(32.084,34.834),"פתח תקווה":(32.094,34.888),"ראשון לציון":(31.973,34.801),
    "הרצליה":(32.166,34.844),"כפר סבא":(32.176,34.908),"רעננה":(32.185,34.871),
    "הוד השרון":(32.150,34.894),"נס ציונה":(31.930,34.799),"לוד":(31.952,34.895),
    "רמלה":(31.930,34.868),"מודיעין-מכבים-רעות":(31.893,35.010),
    "קריית שמונה":(33.207,35.571),"נהריה":(33.004,35.095),"עכו":(32.921,35.068),
    "חדרה":(32.434,34.918),"נתיבות":(31.418,34.590),"שדרות":(31.526,34.597),
    "אופקים":(31.315,34.622),"דימונה":(31.068,35.033),"ירוחם":(30.989,34.931),
    "ערד":(31.259,35.213),"מצפה רמון":(30.610,34.801),"אילת":(29.558,34.948),
    "טבריה":(32.792,35.531),"צפת":(32.965,35.496),"עפולה":(32.607,35.290),
    "בית שאן":(32.499,35.500),"נצרת":(32.700,35.304),"קריית אתא":(32.813,35.110),
    "קריית ביאליק":(32.835,35.078),"קריית מוצקין":(32.839,35.076),
    "קריית ים":(32.853,35.067),"טירת כרמל":(32.761,34.973),"נשר":(32.775,35.033),
    "גדרה":(31.812,34.773),"יבנה":(31.877,34.744),"ראש העין":(32.095,34.958),
    "פרדס חנה-כרכור":(32.476,34.974),"זכרון יעקב":(32.571,34.953),
    "מגדל העמק":(32.676,35.238),"יקנעם עילית":(32.659,35.106),
    "קריית מלאכי":(31.729,34.743),"גן יבנה":(31.790,34.707),
    "כרמיאל":(32.914,35.294),"שפרעם":(32.806,35.167),"יסוד המעלה":(33.051,35.594),
    "קצרין":(32.994,35.691),"בית שמש":(31.755,34.992),"קריית גת":(31.610,34.770),
    "נוף הגליל":(32.708,35.325),"רמת השרון":(32.147,34.839),"גבעתיים":(32.071,34.810),
    "אור יהודה":(32.029,34.853),"יהוד-מונוסון":(32.034,34.889),
    "קריית אונו":(32.063,34.869),"גבעת שמואל":(32.080,34.850),
    "תל מונד":(32.261,34.924),"בנימינה-גבעת עדה":(32.524,34.945),
    "כפר קרע":(32.507,35.106),"אום אל-פחם":(32.516,35.154),
    "באקה אל-גרבייה":(32.416,35.040),"טייבה":(32.308,34.996),
    "קלנסווה":(32.282,34.986),"רהט":(31.394,34.754),"תל שבע":(31.250,34.730),
    "עומר":(31.270,34.853),"להבים":(31.370,34.819),"ניצן":(31.720,34.629),
    "נחל עוז":(31.476,34.487),"כפר עזה":(31.490,34.530),"בארי":(31.460,34.490),
    "רעים":(31.515,34.513),"מפלסים":(31.600,34.570),"יד מרדכי":(31.630,34.551),
    "זיקים":(31.648,34.535),"שרשרת":(31.598,34.543),"מגן":(31.280,34.470),
    "נבטים":(31.170,34.650),"חצרים":(31.268,34.786),"מיתר":(31.220,34.940),
    "כרמים":(31.470,34.790),"ביתר עילית":(31.696,35.123),"מודיעין עילית":(31.931,35.043),
    "אריאל":(32.106,35.167),"מעלה אדומים":(31.777,35.299),
    "גוש עציון":(31.650,35.110),"בית אל":(31.940,35.220),"אלון שבות":(31.666,35.110),
    "אפרת":(31.651,35.154),"דולב":(31.956,35.143),"קדומים":(32.156,35.159),
    "אלקנה":(32.108,35.029),"כוכב יאיר":(32.210,34.967),"שוהם":(31.999,34.957),
    "אור עקיבא":(32.504,34.920),"קיסריה":(32.497,34.893),"כפר יונה":(32.315,34.937),
    "חצור הגלילית":(32.979,35.399),"ראש פינה":(32.972,35.545),
    "מגדל":(32.832,35.508),"עין גב":(32.783,35.628),
    "מרום גולן":(33.121,35.767),"מג'דל שמס":(33.272,35.771),
    "אשקלון - מרכז":(31.668,34.574),"אשקלון - צפון":(31.693,34.573),
    "חוף אשקלון":(31.710,34.553),"לכיש":(31.550,34.850),
    "שפיר":(31.620,34.760),"יואב":(31.680,34.730),
    "קריית עקרון":(31.870,34.820),"מזכרת בתיה":(31.855,34.837),
    "נס הרים":(31.717,34.982),"צור הדסה":(31.713,35.086),
    "גבעת ברנר":(31.840,34.820),"ניר עם":(31.510,34.528),
}
ALL_CITIES = sorted(CITY_COORDS.keys())

# ════════════════════════════════════════════════════════════════
#  CATEGORIES
# ════════════════════════════════════════════════════════════════
CATEGORIES = {
    "1":  {"name":"ירי רקטות וטילים","icon":"🚀","color":"#FF2020","dark":"#3D0000","shelter":10,"anim":"bounce","origin":"south"},
    "2":  {"name":"חדירת כלי טייס עוין","icon":"✈","color":"#FF6600","dark":"#3D1500","shelter":60,"anim":"fly","origin":"north"},
    "3":  {"name":"רעידת אדמה","icon":"🌍","color":"#FF8800","dark":"#2a1a00","shelter":None,"anim":"shake","origin":None},
    "4":  {"name":"חומרים מסוכנים","icon":"☢","color":"#FFAA00","dark":"#2a2000","shelter":None,"anim":"pulse","origin":None},
    "5":  {"name":"חדירת מחבלים","icon":"⚠","color":"#FF0044","dark":"#3D0011","shelter":None,"anim":"bounce","origin":None},
    "6":  {"name":"צונאמי","icon":"🌊","color":"#0088FF","dark":"#001133","shelter":None,"anim":"wave","origin":None},
    "7":  {"name":"חשד לרעידת אדמה","icon":"🌍","color":"#FF8800","dark":"#2a1a00","shelter":None,"anim":"shake","origin":None},
    "13": {"name":"ירי רקטות וטילים","icon":"🚀","color":"#FF2020","dark":"#3D0000","shelter":10,"anim":"bounce","origin":"south"},
    "101":{"name":"בדיקה","icon":"🔔","color":"#888888","dark":"#222222","shelter":None,"anim":"pulse","origin":None},
}
DEFAULT_CAT = {"name":"התרעה","icon":"🔴","color":"#FF0000","dark":"#3D0000","shelter":None,"anim":"bounce","origin":None}

# ── Origin sources ───────────────────────────────────────────────
# Each entry: (flag, short_name, full_name, color)
ORIGINS = {
    "gaza":     ("🇵🇸", "עזה",               "רצועת עזה — חמאס / ג'יהאד אסלאמי",  "#FF3030"),
    "lebanon":  ("🇱🇧", "לבנון",             "לבנון — חיזבאללה",                    "#FF6600"),
    "houthis":  ("🇾🇪", "חות'ים / תימן",    "תימן — חות'ים",                        "#FFAA00"),
    "iran":     ("🇮🇷", "איראן",             "איראן — כוח קודס / שיבוכים",          "#FF8000"),
    "westbank": ("🏴", "גדה המערבית",        "גדה המערבית — טרור מקומי",             "#FF2266"),
    "syria":    ("🇸🇾", "סוריה",             "סוריה",                                "#DD6600"),
    "unknown":  ("❓", "מקור לא ידוע",       "מקור לא ידוע",                         "#888888"),
}

# ── City keyword → origin key ────────────────────────────────────
# Rules checked top-to-bottom; first match wins.
# Each rule: (list_of_keywords_in_city_name, origin_key)
_CITY_ORIGIN_RULES = [
    # Deep south / Gaza envelope
    (["נחל עוז","כפר עזה","בארי","רעים","ניר עם","כיסופים","נחל עוז",
      "מגן","שדרות","נתיבות","אופקים","סופה","אבשלום","גבים",
      "מפלסים","שרשרת","יד מרדכי","זיקים","ניצן","שפיר","לכיש",
      "קריית גת","תל-שבע","חצרים","נבטים","רהט","תל שבע",
      "אשקלון","אשדוד","ניצנים","גן יבנה","קריית מלאכי","גדרה",
      "יבנה","נס ציונה","ראשון לציון","באר שבע","להבים","עומר",
      "מיתר","ירוחם","דימונה","ערד","בצת","הר עמשה"], "gaza"),

    # North — Lebanon / Hezbollah (Galilee, valleys, Haifa bay)
    (["קריית שמונה","מטולה","שלומי","נהריה","מעלות","כרמיאל","עכו",
      "נהריה","שגב-שלום","חצור הגלילית","ראש פינה","צפת","טבריה",
      "כנרת","יסוד המעלה","מג'דל שמס","מסעדה","בית הלל",
      "ש'פר עם","מעיין ברוך","שניר","דן","אביבים","שלומי",
      "חיפה","קריית אתא","קריית ביאליק","קריית מוצקין","קריית ים",
      "טירת כרמל","נשר","נוף הגליל","נצרת","עפולה","מגדל העמק",
      "בית שאן","גינוסר","עין גב","מגדל","זיכרון יעקב",
      "פרדס חנה","חדרה","גולן","קצרין","מרום גולן"], "lebanon"),

    # Houthis / long-range (center & south, after Oct 7)
    (["תל אביב","רמת גן","בני ברק","פתח תקווה","הרצליה","נתניה",
      "רעננה","כפר סבא","הוד השרון","ראש העין","רמת השרון",
      "גבעתיים","בת ים","חולון","אור יהודה","יהוד","לוד","רמלה",
      "ירושלים","בית שמש","מודיעין","קריית אונו","שוהם",
      "גבעת שמואל","פתח","אילת","מצפה רמון"], "houthis"),

    # West Bank / shooting attacks (Jerusalem suburbs, settlements)
    (["מעלה אדומים","גוש עציון","אפרת","ביתר עילית","בית לחם",
      "קרית ארבע","גבעת זאב","בית אל","ברכה","עלי","שילה",
      "אריאל","אלון שבות","תקוע","אלון מורה","קדומים","דולב",
      "נווה צוף","מודיעין עילית","גן שמואל"], "westbank"),

    # Golan / Syria
    (["קצרין","מג'דל שמס","מסעדה","מרום גולן","חרמון","בני יהודה",
      "קשת","נמרוד","גבת","אל רום","כנף","עין זיוון"], "syria"),
]

def _detect_origin_key(cities: list, default_hint: str) -> str:
    """Return origin key based on city list, falling back to default_hint."""
    cities_str = " ".join(cities)
    for keywords, key in _CITY_ORIGIN_RULES:
        if any(kw in cities_str for kw in keywords):
            return key
    # fallback from category default hint
    if default_hint == "south":   return "gaza"
    if default_hint == "north":   return "lebanon"
    if default_hint == "east":    return "iran"
    return "unknown"

# ════════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════════
class Config:
    DEF = {"locations":[],"sound":True,"auto_fullscreen":True,"show_map":True,
           "autostart":False,"widget_x":None,"widget_y":None,
           "widget_w":262,"widget_h":130,"minimized":False}
    def __init__(self):
        self.data = dict(self.DEF); self._load()
    def _load(self):
        try:
            if os.path.exists(CFG_PATH):
                with open(CFG_PATH,"r",encoding="utf-8") as f:
                    self.data.update(json.load(f))
        except Exception: pass
    def save(self):
        try:
            os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
            with open(CFG_PATH,"w",encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception: pass
    def get(self, k, d=None): return self.data.get(k, self.DEF.get(k,d))
    def set(self, k, v): self.data[k]=v; self.save()
    def set_autostart(self, enable: bool, exe_path: str=""):
        try:
            cmd_str = f'"{exe_path}"' if exe_path else ""
            if enable and cmd_str:
                # Create scheduled task (runs at login with highest privilege)
                xml_path = os.path.join(os.path.dirname(CFG_PATH), "task.xml")
                xml = f"""<?xml version="1.0"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Principals><Principal id="Author">
    <LogonType>InteractiveToken</LogonType>
    <RunLevel>HighestAvailable</RunLevel>
  </Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>
  <Actions><Exec>
    <Command>{exe_path}</Command>
  </Exec></Actions>
</Task>"""
                with open(xml_path,"w",encoding="utf-8") as f: f.write(xml)
                subprocess.run(
                    f'schtasks /create /f /tn "RedAlertMonitor" /xml "{xml_path}"',
                    shell=True, capture_output=True)
            else:
                subprocess.run('schtasks /delete /f /tn "RedAlertMonitor"',
                               shell=True, capture_output=True)
            self.set("autostart", enable)
        except Exception: pass

# ════════════════════════════════════════════════════════════════
#  ALERT
# ════════════════════════════════════════════════════════════════
class Alert:
    def __init__(self, raw: dict):
        self.id     = str(raw.get("id", time.time()))
        self.cat    = str(raw.get("cat","1"))
        self.title  = raw.get("title","התרעה")
        self.cities = raw.get("data",[])
        self.ts     = datetime.now()
        self.info   = CATEGORIES.get(self.cat, DEFAULT_CAT)
    @property
    def icon(self):      return self.info["icon"]
    @property
    def color(self):     return self.info["color"]
    @property
    def dark(self):      return self.info["dark"]
    @property
    def time_str(self):  return self.ts.strftime("%H:%M:%S")
    @property
    def shelter_text(self):
        t = self.info.get("shelter")
        return f"היכנסו למרחב המוגן ושהו {t} דקות" if t else ""
    @property
    def origin(self):
        """Returns (flag, short_name, full_name, color) or None if not applicable."""
        hint = self.info.get("origin")
        if hint is None: return None
        key = _detect_origin_key(self.cities, hint)
        o = ORIGINS.get(key, ORIGINS["unknown"])
        return o  # (flag, short, full, color)

    @property
    def origin_key(self):
        hint = self.info.get("origin")
        if hint is None: return None
        return _detect_origin_key(self.cities, hint)

    def map_markers(self):
        o = self.origin
        origin_str = f"{o[0]} {o[1]}" if o else ""
        out=[]
        for city in self.cities:
            if city in CITY_COORDS:
                lat,lng = CITY_COORDS[city]
                out.append({"city":city,"lat":lat,"lng":lng,
                            "icon":self.icon,"color":self.color,
                            "type":self.title,"time":self.time_str,
                            "origin": origin_str,
                            "origin_full": o[2] if o else ""})
        return out

# ════════════════════════════════════════════════════════════════
#  NETWORK WORKER
# ════════════════════════════════════════════════════════════════
class AlertWorker(QThread):
    new_alert     = pyqtSignal(dict)
    alert_cleared = pyqtSignal()
    conn_error    = pyqtSignal(str)
    conn_ok       = pyqtSignal()
    def __init__(self, config: Config):
        super().__init__(); self.config=config; self._running=True; self._last_id=None; self._had_err=False
    def run(self):
        sess = requests.Session(); sess.headers.update(API_HEADERS)
        while self._running:
            try:
                r    = sess.get(OREF_URL, timeout=4)
                text = r.text.strip().lstrip("\ufeff")
                if self._had_err: self._had_err=False; self.conn_ok.emit()
                if not text or len(text)<5 or text in ("{}","null",""):
                    if self._last_id is not None: self._last_id=None; self.alert_cleared.emit()
                else:
                    try: data=json.loads(text)
                    except Exception: data={}
                    if data and "id" in data:
                        aid = str(data["id"])
                        if aid != self._last_id:
                            self._last_id = aid
                            locs=self.config.get("locations",[]); cities=data.get("data",[])
                            if not locs or any(c in locs for c in cities):
                                self.new_alert.emit(data)
                    else:
                        if self._last_id is not None: self._last_id=None; self.alert_cleared.emit()
            except requests.exceptions.ConnectionError:
                if not self._had_err: self._had_err=True; self.conn_error.emit("אין חיבור לאינטרנט")
            except Exception: pass
            time.sleep(POLL_MS/1000)
    def stop(self): self._running=False; self.quit(); self.wait(2000)

# ════════════════════════════════════════════════════════════════
#  SOUND
# ════════════════════════════════════════════════════════════════
class SoundPlayer:
    def __init__(self): self._busy=False
    def play(self):
        if self._busy: return
        self._busy=True; threading.Thread(target=self._t, daemon=True).start()
    def _t(self):
        try:
            import winsound
            for _ in range(3): winsound.Beep(800,160); time.sleep(0.04); winsound.Beep(1100,160); time.sleep(0.04); winsound.Beep(1400,160); time.sleep(0.07)
            winsound.Beep(800,500)
        except Exception:
            try: sys.stdout.write("\a\a\a"); sys.stdout.flush()
            except Exception: pass
        finally: self._busy=False

# ════════════════════════════════════════════════════════════════
#  MAP WINDOW  (Leaflet.js via QWebEngineView)
# ════════════════════════════════════════════════════════════════
MAP_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body,#map{width:100%;height:100%;background:#120000;}
.am{font-size:24px;filter:drop-shadow(0 0 7px #FF2020);
    animation:pulse 0.9s ease-in-out infinite alternate;}
@keyframes pulse{from{transform:scale(1) rotate(-5deg);}to{transform:scale(1.4) rotate(5deg);}}
.leaflet-popup-content-wrapper{
  background:rgba(20,0,0,0.95);color:#fff;
  border:1px solid #FF4040;border-radius:8px;
  backdrop-filter:blur(4px);}
.leaflet-popup-tip{background:rgba(20,0,0,0.95);}
.leaflet-popup-content{font-family:Arial,sans-serif;font-size:13px;
  direction:rtl;text-align:right;min-width:130px;}
.leaflet-control-attribution{background:rgba(0,0,0,0.55)!important;color:#666!important;}
#status{position:fixed;top:10px;right:10px;background:rgba(0,0,0,0.7);
  color:#888;padding:8px 14px;border-radius:6px;
  font-family:Arial;font-size:12px;direction:rtl;z-index:999;}
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head><body>
<div id="status">אין התרעות פעילות</div>
<div id="map"></div>
<script>
var map = L.map('map',{center:[31.5,34.9],zoom:8,zoomControl:true});
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{
  attribution:'&copy; OpenStreetMap &copy; CARTO',maxZoom:19}).addTo(map);
var layer = L.layerGroup().addTo(map);

function updateAlerts(j){
  layer.clearLayers();
  var st = document.getElementById('status');
  var a;
  try{ a=JSON.parse(j); }catch(e){ return; }
  if(!a||a.length===0){ st.textContent='אין התרעות פעילות'; st.style.color='#888'; return; }
  st.textContent='⚠  '+a.length+' ישובים מוזהרים'; st.style.color='#FF5555';
  var bounds=[];
  a.forEach(function(m){
    var ico = L.divIcon({
      html:'<div class="am" style="color:#fff;font-size:26px;text-shadow:0 0 10px '+m.color+'">'+m.icon+'</div>',
      iconSize:[34,34],iconAnchor:[17,17],className:''});
    var mk = L.marker([m.lat,m.lng],{icon:ico}).addTo(layer);
    mk.bindPopup(
      '<b style="font-size:14px;color:'+m.color+'">'+m.icon+' '+m.type+'</b><br/>'+
      '<span style="font-size:13px;">'+m.city+'</span><br/>'+
      (m.origin ? '<span style="color:#ffcc66;font-size:12px;">🎯 '+m.origin+'</span><br/>' : '')+
      '<small style="color:#aaa;">'+m.time+'</small>');
    bounds.push([m.lat,m.lng]);
    // pulse circle
    L.circle([m.lat,m.lng],{
      radius:4000,color:m.color,fillColor:m.color,
      fillOpacity:0.12,weight:1.5,opacity:0.6}).addTo(layer);
  });
  if(bounds.length===1) map.setView(bounds[0],13,{animate:true});
  else if(bounds.length>1) map.fitBounds(bounds,{padding:[50,50],maxZoom:12,animate:true});
}
window.updateAlerts = updateAlerts;
</script></body></html>"""

class MapWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("מפת התרעות  —  Red Alert")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.resize(920, 680)
        self.setStyleSheet("background:#120000;")
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)
        # header
        hdr=QWidget(); hdr.setFixedHeight(44)
        hdr.setStyleSheet("background:#1a0000;border-bottom:1px solid #440000;")
        hl=QHBoxLayout(hdr); hl.setContentsMargins(16,0,16,0)
        lbl=QLabel("🗺  מפת התרעות בזמן אמת")
        lbl.setFont(QFont("Arial",12,QFont.Bold)); lbl.setStyleSheet("color:white;")
        lbl.setLayoutDirection(Qt.RightToLeft)
        cb=QPushButton("✕"); cb.setFixedSize(30,30)
        cb.setStyleSheet("QPushButton{background:rgba(255,255,255,0.1);color:white;"
                         "border:none;border-radius:15px;font-size:13px;}"
                         "QPushButton:hover{background:#FF2020;}")
        cb.clicked.connect(self.hide)
        hl.addWidget(cb); hl.addStretch(); hl.addWidget(lbl)
        v.addWidget(hdr)
        if _HAS_WEB:
            self._web=QWebEngineView(); self._web.setHtml(MAP_HTML); v.addWidget(self._web,1)
        else:
            info=QLabel("להתקנת המפה:\n\npy -m pip install PyQtWebEngine\n\nלאחר מכן הפעל מחדש.")
            info.setAlignment(Qt.AlignCenter); info.setFont(QFont("Arial",13))
            info.setStyleSheet("color:#FF8888;padding:40px;"); info.setLayoutDirection(Qt.RightToLeft)
            v.addWidget(info,1); self._web=None
    def update_alerts(self, markers: list):
        if self._web and _HAS_WEB:
            js=json.dumps(markers,ensure_ascii=False)
            self._web.page().runJavaScript(f"updateAlerts({repr(js)})")
    def clear(self): self.update_alerts([])

# ════════════════════════════════════════════════════════════════
#  FLOATING WIDGET  (resizable, fixed multi-select)
# ════════════════════════════════════════════════════════════════
class FloatingWidget(QWidget):
    sig_fullscreen = pyqtSignal()
    sig_settings   = pyqtSignal()
    sig_map        = pyqtSignal()
    MIN_W, MIN_H   = 235, 85

    def __init__(self, config: Config):
        super().__init__()
        self.config     = config
        self._alerts    = deque(maxlen=60)
        self._active    = None
        self._pulse     = False
        self._step      = 0
        self._drag_pos  = None
        self._minimized = config.get("minimized", False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMinimumSize(self.MIN_W, self.MIN_H)
        w = max(self.MIN_W, config.get("widget_w",262))
        h = max(self.MIN_H, config.get("widget_h",130))
        self.resize(w, h)
        self._build()
        self._position()
        QTimer(self).timeout.connect(self._tick); self._timer=QTimer(self)
        self._timer.timeout.connect(self._tick); self._timer.start(450)

    def _build(self):
        root=QVBoxLayout(self); root.setContentsMargins(8,8,8,14); root.setSpacing(4)
        # header
        hdr=QWidget(); hdr.setFixedHeight(30)
        hl=QHBoxLayout(hdr); hl.setContentsMargins(4,0,4,0); hl.setSpacing(4)
        def sb(t,tip):
            b=QPushButton(t); b.setFixedSize(24,24); b.setToolTip(tip)
            b.setStyleSheet("QPushButton{background:rgba(255,255,255,0.14);color:white;"
                            "border:none;border-radius:12px;font-size:12px;}"
                            "QPushButton:hover{background:rgba(255,255,255,0.30);}")
            return b
        self._bc=sb("⚙","הגדרות"); self._bm=sb("🗺","מפה"); self._bx=sb("−","מזעור")
        self._bc.clicked.connect(self.sig_settings)
        self._bm.clicked.connect(self.sig_map)
        self._bx.clicked.connect(self._toggle_min)
        self._lt=QLabel("🔴  התרעות")
        self._lt.setFont(QFont("Arial",9,QFont.Bold)); self._lt.setStyleSheet("color:white;")
        self._lt.setLayoutDirection(Qt.RightToLeft)
        hl.addWidget(self._bc); hl.addWidget(self._bm); hl.addWidget(self._bx)
        hl.addStretch(); hl.addWidget(self._lt)
        # idle label
        self._idle=QLabel("אין התרעות פעילות")
        self._idle.setAlignment(Qt.AlignCenter); self._idle.setFont(QFont("Arial",9))
        self._idle.setStyleSheet("color:rgba(255,255,255,0.42);padding:10px 0;")
        self._idle.setLayoutDirection(Qt.RightToLeft)
        # scroll
        self._scroll=QScrollArea(); self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
            "QScrollBar:vertical{background:rgba(255,255,255,0.07);width:4px;border-radius:2px;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.26);border-radius:2px;}")
        self._scroll.hide()
        self._iw=QWidget(); self._iw.setStyleSheet("background:transparent;")
        self._il=QVBoxLayout(self._iw); self._il.setContentsMargins(0,0,0,0)
        self._il.setSpacing(3); self._il.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._iw)
        # conn
        self._lconn=QLabel(""); self._lconn.setAlignment(Qt.AlignCenter)
        self._lconn.setFont(QFont("Arial",7)); self._lconn.setFixedHeight(14)
        self._lconn.setStyleSheet("color:rgba(255,220,0,0.75);")
        # resize grip
        self._grip=QSizeGrip(self); self._grip.setStyleSheet("background:transparent;")
        root.addWidget(hdr); root.addWidget(self._idle)
        root.addWidget(self._scroll,1); root.addWidget(self._lconn)

    def _position(self):
        sc=QApplication.desktop().availableGeometry()
        x=self.config.get("widget_x"); y=self.config.get("widget_y")
        if x is None: x=sc.right()-self.width()-12
        if y is None: y=sc.top()+60
        self.move(x,y)

    def resizeEvent(self,e):
        super().resizeEvent(e)
        gw=16; self._grip.move(self.width()-gw,self.height()-gw); self._grip.resize(gw,gw)
        if not self._minimized:
            self.config.set("widget_w",self.width()); self.config.set("widget_h",self.height())

    def _toggle_min(self):
        self._minimized=not self._minimized
        self.config.set("minimized",self._minimized)
        if self._minimized:
            self.setFixedHeight(50); self._idle.hide(); self._scroll.hide(); self._bx.setText("+")
        else:
            self.setMinimumHeight(self.MIN_H); self.setMaximumHeight(16777215)
            self.resize(self.width(), max(self.MIN_H, self.config.get("widget_h",130)))
            self._bx.setText("−"); self._refresh_content()

    def _refresh_content(self):
        if self._minimized: return
        if not self._alerts: self._idle.show(); self._scroll.hide()
        else: self._idle.hide(); self._scroll.show()

    def add_alert(self, a: Alert):
        self._active=a; self._alerts.appendleft(a); self._rebuild(); self._refresh_content()

    def clear_alerts(self):
        self._active=None; self._rebuild()

    def _rebuild(self):
        for i in reversed(range(self._il.count())):
            w=self._il.itemAt(i).widget()
            if w: w.setParent(None)
        for a in list(self._alerts)[:12]: self._il.addWidget(self._make_row(a))

    def _make_row(self, a: Alert):
        act=(self._active and self._active.id==a.id)
        f=QFrame(); f.setMinimumHeight(60)
        f.setCursor(Qt.PointingHandCursor)
        bg=(f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {a.color},stop:1 rgba(60,0,0,0.92))"
            if act else "rgba(48,4,4,0.88)")
        brd="rgba(255,255,255,0.38)" if act else "rgba(255,255,255,0.09)"
        f.setStyleSheet(f"QFrame{{background:{bg};border-radius:8px;border:1px solid {brd};}}")
        lay=QHBoxLayout(f); lay.setContentsMargins(8,6,8,6); lay.setSpacing(8)
        li=QLabel(a.icon); li.setFont(QFont("Segoe UI Emoji",18)); li.setFixedWidth(30); li.setAlignment(Qt.AlignCenter)
        col=QVBoxLayout(); col.setSpacing(2)
        t1=QLabel(a.title); t1.setFont(QFont("Arial",8,QFont.Bold)); t1.setStyleSheet("color:white;"); t1.setLayoutDirection(Qt.RightToLeft)
        cs="  |  ".join(a.cities[:3])
        if len(a.cities)>3: cs+=f"  +{len(a.cities)-3}"
        t2=QLabel(cs); t2.setFont(QFont("Arial",7)); t2.setStyleSheet("color:rgba(255,255,255,0.80);"); t2.setLayoutDirection(Qt.RightToLeft); t2.setWordWrap(True)
        col.addWidget(t1); col.addWidget(t2)
        # origin tag
        if act and a.origin:
            flag, short, full, ocol = a.origin
            t3=QLabel(f"{flag} {short}")
            t3.setFont(QFont("Segoe UI Emoji",7))
            t3.setStyleSheet(f"color:{ocol};background:rgba(0,0,0,0.3);border-radius:3px;padding:1px 4px;")
            t3.setLayoutDirection(Qt.RightToLeft)
            col.addWidget(t3)
        col.addStretch()
        tt=QLabel(a.time_str); tt.setFont(QFont("Arial",6)); tt.setStyleSheet("color:rgba(255,255,255,0.42);"); tt.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        lay.addWidget(li); lay.addLayout(col,1); lay.addWidget(tt,0,Qt.AlignTop)
        # double-click on row → fullscreen
        f.mouseDoubleClickEvent = lambda e: self.sig_fullscreen.emit()
        return f

    def set_conn_error(self,m): self._lconn.setText(f"⚠ {m}")
    def set_conn_ok(self):      self._lconn.setText("")

    def _tick(self): self._pulse=not self._pulse; self._step=(self._step+1)%360; self.update()

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r=self.rect().adjusted(2,2,-2,-2)
        path=QPainterPath(); path.addRoundedRect(QRectF(r),13,13)
        if self._active and self._pulse:
            c=QColor(self._active.color); c.setAlpha(215)
            g=QLinearGradient(0,0,0,r.height()); g.setColorAt(0,c)
            dk=QColor(self._active.dark); dk.setAlpha(225); g.setColorAt(1,dk)
            p.fillPath(path,g); p.setPen(QPen(QColor(self._active.color),2))
        elif self._active:
            c2=QColor(self._active.color); c2.setAlpha(100)
            g2=QLinearGradient(0,0,0,r.height()); g2.setColorAt(0,c2)
            dk2=QColor(self._active.dark); dk2.setAlpha(220); g2.setColorAt(1,dk2)
            p.fillPath(path,g2); p.setPen(QPen(QColor(255,255,255,35),1))
        else:
            g3=QLinearGradient(0,0,0,r.height()); g3.setColorAt(0,QColor(26,4,4,215)); g3.setColorAt(1,QColor(12,2,2,215))
            p.fillPath(path,g3); p.setPen(QPen(QColor(255,255,255,25),1))
        p.drawPath(path)

    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag_pos=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self,e):
        if e.buttons()==Qt.LeftButton and self._drag_pos: self.move(e.globalPos()-self._drag_pos)
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.LeftButton and self._drag_pos:
            self.config.set("widget_x",self.x()); self.config.set("widget_y",self.y()); self._drag_pos=None
    def mouseDoubleClickEvent(self,e): self.sig_fullscreen.emit()

# ════════════════════════════════════════════════════════════════
#  FULL SCREEN
# ════════════════════════════════════════════════════════════════
class FullScreen(QWidget):
    def __init__(self, history: deque, active: Alert=None):
        super().__init__()
        self.history=list(history); self.active=active or(self.history[0] if self.history else None)
        self._step=0; self._setup()
        self._tmr=QTimer(self); self._tmr.timeout.connect(self._tick); self._tmr.start(40)

    def _setup(self):
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint)
        sc=QApplication.desktop().screenGeometry(); self.setGeometry(sc)
        self.setStyleSheet("background:#080000;"); self.setLayoutDirection(Qt.RightToLeft)
        self.setAttribute(Qt.WA_DeleteOnClose)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        a=self.active
        if a:
            ban=QWidget(); ban.setFixedHeight(118)
            ban.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {a.color},stop:1 rgba(80,0,0,0.97));")
            bl=QHBoxLayout(ban); bl.setContentsMargins(50,8,50,8); bl.setSpacing(18)
            self._ico=QLabel(a.icon); self._ico.setFont(QFont("Segoe UI Emoji",50)); self._ico.setAlignment(Qt.AlignCenter); self._ico.setFixedWidth(100)
            tc=QVBoxLayout(); tc.setSpacing(3)
            t0=QLabel("🔴  התרעת צבע אדום!"); t0.setFont(QFont("Arial",27,QFont.Bold)); t0.setStyleSheet("color:white;")
            t1=QLabel(a.title); t1.setFont(QFont("Arial",14)); t1.setStyleSheet("color:white;")
            tc.addWidget(t0); tc.addWidget(t1)
            if a.origin:
                flag, short, full, ocol = a.origin
                orig_box = QWidget()
                orig_box.setStyleSheet(f"background:rgba(0,0,0,0.35);border-radius:6px;border:1px solid {ocol};")
                obl = QHBoxLayout(orig_box); obl.setContentsMargins(10,4,10,4); obl.setSpacing(8)
                lbl_flag = QLabel(flag); lbl_flag.setFont(QFont("Segoe UI Emoji",18)); lbl_flag.setFixedWidth(32)
                lbl_src = QLabel(f"מקור הירי:  {full}"); lbl_src.setFont(QFont("Arial",13,QFont.Bold))
                lbl_src.setStyleSheet(f"color:{ocol};"); lbl_src.setLayoutDirection(Qt.RightToLeft)
                obl.addWidget(lbl_src,1); obl.addWidget(lbl_flag)
                tc.addWidget(orig_box)
            tc.addStretch()
            cb=QPushButton("✕"); cb.setFixedSize(40,40)
            cb.setStyleSheet("QPushButton{background:rgba(0,0,0,0.3);color:white;border:none;border-radius:20px;font-size:16px;}QPushButton:hover{background:rgba(0,0,0,0.6);}")
            cb.clicked.connect(self.close)
            bl.addWidget(self._ico); bl.addLayout(tc,1); bl.addWidget(cb,0,Qt.AlignTop)
            root.addWidget(ban)
            if a.shelter_text:
                sb=QWidget(); sb.setFixedHeight(46); sb.setStyleSheet("background:#1b0000;")
                sl=QHBoxLayout(sb); ls=QLabel(f"🏠  {a.shelter_text}")
                ls.setFont(QFont("Arial",13,QFont.Bold)); ls.setStyleSheet("color:#FFE040;"); ls.setAlignment(Qt.AlignCenter); sl.addWidget(ls)
                root.addWidget(sb)
            # cities
            cw=QWidget(); cw.setStyleSheet("background:#110000;")
            cv=QVBoxLayout(cw); cv.setContentsMargins(50,12,50,12); cv.setSpacing(8)
            ch=QLabel(f"ישובים מוזהרים  ({len(a.cities)}):"); ch.setFont(QFont("Arial",11,QFont.Bold)); ch.setStyleSheet("color:rgba(255,255,255,0.68);"); cv.addWidget(ch)
            csc=QScrollArea(); csc.setWidgetResizable(True); csc.setFixedHeight(180)
            csc.setStyleSheet("QScrollArea{border:none;background:transparent;}QScrollBar:vertical{background:rgba(255,255,255,0.06);width:4px;}QScrollBar::handle:vertical{background:rgba(255,255,255,0.20);}")
            cc=QWidget(); cc.setStyleSheet("background:transparent;")
            fl2=QVBoxLayout(cc); fl2.setContentsMargins(0,0,0,0); fl2.setSpacing(5)
            rw=None; rl=None
            for i,city in enumerate(a.cities):
                if i%5==0:
                    rw=QWidget(); rw.setStyleSheet("background:transparent;")
                    rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5); fl2.addWidget(rw)
                lb=QLabel(f"  {city}  "); lb.setFont(QFont("Arial",11,QFont.Bold))
                lb.setStyleSheet(f"color:white;background:{a.color};border-radius:5px;padding:4px 8px;")
                lb.setAlignment(Qt.AlignCenter); lb.setLayoutDirection(Qt.RightToLeft); rl.addWidget(lb)
            if rl and rl.count()%5!=0: rl.addStretch()
            csc.setWidget(cc); cv.addWidget(csc); root.addWidget(cw)
        if len(self.history)>1:
            hw=QWidget(); hw.setStyleSheet("background:#0c0000;")
            hv=QVBoxLayout(hw); hv.setContentsMargins(50,10,50,10); hv.setSpacing(3)
            hv.addWidget(QLabel("היסטוריה:").__class__("היסטוריית התרעות אחרונות:"))
            hsc=QScrollArea(); hsc.setWidgetResizable(True); hsc.setFixedHeight(100)
            hsc.setStyleSheet("QScrollArea{border:none;background:transparent;}")
            hco=QWidget(); hco.setStyleSheet("background:transparent;")
            hla=QVBoxLayout(hco); hla.setContentsMargins(0,0,0,0); hla.setSpacing(2)
            for alt in self.history[:13]:
                skip=a and alt.id==a.id
                rw2=QWidget(); rw2.setStyleSheet("background:transparent;"); rl2=QHBoxLayout(rw2); rl2.setContentsMargins(0,1,0,1); rl2.setSpacing(8)
                tl=QLabel(alt.time_str); tl.setFont(QFont("Arial",9)); tl.setStyleSheet(f"color:rgba(255,255,255,{'0.28' if skip else '0.5'});"); tl.setFixedWidth(60)
                il=QLabel(alt.icon); il.setFont(QFont("Segoe UI Emoji",11)); il.setFixedWidth(22)
                cl=QLabel(", ".join(alt.cities[:5])); cl.setFont(QFont("Arial",9)); cl.setStyleSheet(f"color:rgba(255,255,255,{'0.28' if skip else '0.62'});"); cl.setLayoutDirection(Qt.RightToLeft)
                rl2.addWidget(tl); rl2.addWidget(il); rl2.addWidget(cl,1); hla.addWidget(rw2)
            hsc.setWidget(hco); hv.addWidget(hsc); root.addWidget(hw)
        root.addStretch()
        bot=QWidget(); bot.setFixedHeight(34); bot.setStyleSheet("background:#050000;border-top:1px solid rgba(255,255,255,0.06);")
        bl2=QHBoxLayout(bot); bl2.setContentsMargins(28,0,28,0)
        self._clk=QLabel(datetime.now().strftime("%H:%M:%S")); self._clk.setFont(QFont("Arial",9)); self._clk.setStyleSheet("color:rgba(255,255,255,0.28);")
        el=QLabel("ESC / לחיצה כפולה לסגירה"); el.setFont(QFont("Arial",9)); el.setStyleSheet("color:rgba(255,255,255,0.20);")
        bl2.addStretch(); bl2.addWidget(el); bl2.addStretch(); bl2.addWidget(self._clk)
        root.addWidget(bot)

    def _tick(self):
        self._step=(self._step+1)%360; self._clk.setText(datetime.now().strftime("%H:%M:%S"))
        if hasattr(self,"_ico") and self.active:
            anim=self.active.info.get("anim","bounce")
            off=int(math.sin(math.radians(self._step*(12 if anim=="shake" else 6 if anim=="bounce" else 3)))*6)
            self._ico.setContentsMargins(0,off,0,-off)
        self.update()
    def paintEvent(self,e):
        super().paintEvent(e); p=QPainter(self)
        p.setPen(QPen(QColor(255,0,0,8),1)); p.drawLine(0,int((self._step/360)*self.height()),self.width(),int((self._step/360)*self.height()))
    def keyPressEvent(self,e):
        if e.key()==Qt.Key_Escape: self.close()
    def mouseDoubleClickEvent(self,e): self.close()
    def closeEvent(self,e): self._tmr.stop(); super().closeEvent(e)

# ════════════════════════════════════════════════════════════════
#  LOCATIONS DIALOG  (proper checkbox multi-select)
# ════════════════════════════════════════════════════════════════
class LocationsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config=config; self._sel=set(config.get("locations",[]))
        self.setWindowTitle("בחירת ישובים"); self.setLayoutDirection(Qt.RightToLeft)
        self.resize(560,640)
        self.setStyleSheet("""
            QDialog{background:#160000;color:white;}
            QLabel{color:white;font-size:12px;}
            QLineEdit{background:#260000;color:white;border:1px solid #555;border-radius:5px;padding:7px;font-size:13px;}
            QListWidget{background:#1d0000;color:white;border:1px solid #444;border-radius:5px;font-size:12px;outline:0;}
            QListWidget::item{padding:6px 10px;border-radius:3px;}
            QListWidget::item:hover{background:rgba(255,50,50,0.12);}
            QPushButton{background:#FF2020;color:white;border:none;border-radius:6px;padding:8px 16px;font-size:12px;}
            QPushButton:hover{background:#FF4040;}
            QCheckBox{color:white;font-size:12px;spacing:8px;}
            QCheckBox::indicator{width:16px;height:16px;border-radius:3px;border:1px solid #777;background:#260000;}
            QCheckBox::indicator:checked{background:#FF2020;border-color:#FF4040;}
        """)
        v=QVBoxLayout(self); v.setContentsMargins(22,20,22,20); v.setSpacing(10)
        ti=QLabel("📍  בחירת ישובים להתרעה"); ti.setFont(QFont("Arial",14,QFont.Bold)); ti.setAlignment(Qt.AlignCenter); v.addWidget(ti)
        self._ca=QCheckBox("הצג התרעות עבור כל הישובים (ברירת מחדל)")
        self._ca.setChecked(not bool(self._sel)); self._ca.stateChanged.connect(self._on_all); v.addWidget(self._ca)
        self._se=QLineEdit(); self._se.setPlaceholderText("חיפוש ישוב..."); self._se.setEnabled(bool(self._sel)); self._se.textChanged.connect(self._filter); v.addWidget(self._se)
        self._cnt=QLabel(""); self._cnt.setFont(QFont("Arial",9)); self._cnt.setStyleSheet("color:rgba(255,180,180,0.85);"); v.addWidget(self._cnt)
        self._lw=QListWidget(); self._lw.setEnabled(bool(self._sel)); v.addWidget(self._lw,1)
        self._pop(ALL_CITIES)
        rb=QHBoxLayout()
        self._ba=QPushButton("בחר הכל"); self._ba.setEnabled(bool(self._sel))
        self._ba.setStyleSheet("QPushButton{background:#333;color:white;border:none;border-radius:5px;padding:6px 12px;font-size:11px;}QPushButton:hover{background:#444;}")
        self._bd=QPushButton("נקה הכל"); self._bd.setEnabled(bool(self._sel))
        self._bd.setStyleSheet(self._ba.styleSheet())
        self._ba.clicked.connect(self._sel_all); self._bd.clicked.connect(self._desel_all)
        rb.addWidget(self._ba); rb.addWidget(self._bd); rb.addStretch(); v.addLayout(rb)
        sp=QFrame(); sp.setFixedHeight(1); sp.setStyleSheet("background:rgba(255,255,255,0.1);"); v.addWidget(sp)
        bts=QHBoxLayout()
        ca=QPushButton("ביטול"); ca.setStyleSheet("QPushButton{background:#333;color:white;border:none;border-radius:6px;padding:8px 16px;font-size:12px;}QPushButton:hover{background:#444;}")
        sv=QPushButton("שמור"); ca.clicked.connect(self.reject); sv.clicked.connect(self._save)
        bts.addWidget(ca); bts.addWidget(sv); v.addLayout(bts)
        self._lw.itemChanged.connect(self._on_item); self._upd_cnt()

    def _pop(self, cities):
        self._lw.blockSignals(True); self._lw.clear()
        for c in cities:
            it=QListWidgetItem(c)
            it.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if c in self._sel else Qt.Unchecked)
            self._lw.addItem(it)
        self._lw.blockSignals(False); self._upd_cnt()

    def _filter(self,txt): self._pop([c for c in ALL_CITIES if txt in c])
    def _on_all(self,st):
        en=not bool(st)
        for w in [self._lw,self._se,self._ba,self._bd]: w.setEnabled(en)
        self._upd_cnt()
    def _on_item(self,it):
        c=it.text()
        if it.checkState()==Qt.Checked: self._sel.add(c)
        else: self._sel.discard(c)
        self._upd_cnt()
    def _sel_all(self):
        self._lw.blockSignals(True)
        for i in range(self._lw.count()): it=self._lw.item(i); it.setCheckState(Qt.Checked); self._sel.add(it.text())
        self._lw.blockSignals(False); self._upd_cnt()
    def _desel_all(self):
        self._lw.blockSignals(True)
        for i in range(self._lw.count()): it=self._lw.item(i); it.setCheckState(Qt.Unchecked); self._sel.discard(it.text())
        self._lw.blockSignals(False); self._upd_cnt()
    def _upd_cnt(self):
        if self._ca.isChecked(): self._cnt.setText("כל הישובים")
        else: n=len(self._sel); self._cnt.setText(f"{n} ישובים נבחרו" if n else "לא נבחרו ישובים")
    def _save(self):
        if self._ca.isChecked(): self.config.set("locations",[])
        else: self.config.set("locations",list(self._sel))
        self.accept()

# ════════════════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ════════════════════════════════════════════════════════════════
class SettingsDialog(QDialog):
    request_test=pyqtSignal()
    def __init__(self, config: Config, parent=None):
        super().__init__(parent); self.config=config; self._setup()
    def _setup(self):
        self.setWindowTitle(f"הגדרות  —  {APP_NAME}  v{APP_VERSION}")
        self.setLayoutDirection(Qt.RightToLeft); self.resize(400,380)
        self.setStyleSheet("""
            QDialog{background:#160000;color:white;}
            QLabel{color:white;}
            QPushButton{background:#FF2020;color:white;border:none;border-radius:6px;padding:9px 20px;font-size:12px;}
            QPushButton:hover{background:#FF4040;}
            QCheckBox{color:white;font-size:12px;spacing:8px;}
            QCheckBox::indicator{width:17px;height:17px;border-radius:3px;border:1px solid #777;background:#260000;}
            QCheckBox::indicator:checked{background:#FF2020;border-color:#FF4040;}
        """)
        v=QVBoxLayout(self); v.setContentsMargins(28,22,28,22); v.setSpacing(14)
        ti=QLabel(f"⚙  הגדרות  —  גרסה {APP_VERSION}"); ti.setFont(QFont("Arial",13,QFont.Bold)); ti.setAlignment(Qt.AlignCenter); v.addWidget(ti)
        def sep(): f=QFrame(); f.setFixedHeight(1); f.setStyleSheet("background:rgba(255,255,255,0.1);"); return f
        v.addWidget(sep())
        self._cs=QCheckBox("🔊  נגן צלילי התרעה"); self._cs.setChecked(self.config.get("sound",True)); v.addWidget(self._cs)
        self._cf=QCheckBox("🖥  פתח מסך מלא אוטומטית"); self._cf.setChecked(self.config.get("auto_fullscreen",True)); v.addWidget(self._cf)
        self._cm=QCheckBox("🗺  פתח מפה אוטומטית בהתרעה"); self._cm.setChecked(self.config.get("show_map",True)); v.addWidget(self._cm)
        self._ck=QCheckBox("🚀  הפעל עם Windows (כמנהל)"); self._ck.setChecked(self.config.get("autostart",False)); v.addWidget(self._ck)
        v.addWidget(sep())
        lb=QPushButton("📍  בחר ישובים להתרעה"); lb.clicked.connect(lambda: LocationsDialog(self.config,self).exec_()); v.addWidget(lb)
        tb=QPushButton("🔔  שלח התרעת בדיקה")
        tb.setStyleSheet("QPushButton{background:#333;color:white;border:none;border-radius:6px;padding:9px 20px;font-size:12px;}QPushButton:hover{background:#444;}")
        tb.clicked.connect(self._test); v.addWidget(tb)
        v.addStretch(); v.addWidget(sep())
        bts=QHBoxLayout()
        ca=QPushButton("ביטול"); ca.setStyleSheet("QPushButton{background:#333;color:white;border:none;border-radius:6px;padding:9px 20px;font-size:12px;}QPushButton:hover{background:#444;}")
        sv=QPushButton("שמור"); ca.clicked.connect(self.reject); sv.clicked.connect(self._save)
        bts.addWidget(ca); bts.addWidget(sv); v.addLayout(bts)
    def _test(self): self._save(); self.accept(); self.request_test.emit()
    def _save(self):
        self.config.set("sound",self._cs.isChecked()); self.config.set("auto_fullscreen",self._cf.isChecked())
        self.config.set("show_map",self._cm.isChecked())
        ns=self._ck.isChecked()
        if ns!=self.config.get("autostart",False):
            self.config.set_autostart(ns, sys.executable)
        self.accept()

# ════════════════════════════════════════════════════════════════
#  MAIN APP
# ════════════════════════════════════════════════════════════════
class RedAlertApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)
        self.setApplicationName(APP_NAME); self.setQuitOnLastWindowClosed(False)
        self.config=Config(); self.history=deque(maxlen=100)
        self.sound=SoundPlayer(); self._fs=None
        self.widget=FloatingWidget(self.config)
        self.widget.sig_fullscreen.connect(self._fullscreen)
        self.widget.sig_settings.connect(self._settings)
        self.widget.sig_map.connect(self._show_map)
        self.widget.show()
        self.map_win=MapWindow()
        self._tray_setup()
        self.worker=AlertWorker(self.config)
        self.worker.new_alert.connect(self._on_alert)
        self.worker.alert_cleared.connect(self._on_clear)
        self.worker.conn_error.connect(self.widget.set_conn_error)
        self.worker.conn_ok.connect(self.widget.set_conn_ok)
        self.worker.start()

    def _tray_setup(self):
        px=QPixmap(22,22); px.fill(Qt.transparent)
        p=QPainter(px); p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor("#FF2020"))); p.setPen(Qt.NoPen); p.drawEllipse(2,2,18,18); p.end()
        self._tray=QSystemTrayIcon(QIcon(px),self); self._tray.setToolTip(f"🔴  {APP_NAME}")
        menu=QMenu()
        menu.setLayoutDirection(Qt.RightToLeft)
        menu.setStyleSheet("QMenu{background:#1a0000;color:white;border:1px solid #440000;border-radius:6px;padding:4px;}"
                           "QMenu::item{padding:7px 22px;border-radius:4px;}QMenu::item:selected{background:#FF2020;}"
                           "QMenu::separator{height:1px;background:rgba(255,255,255,0.12);margin:3px 0;}")
        for lbl,cb in [("🖥  מסך מלא",self._fullscreen),("🗺  מפה",self._show_map),(None,None),
                       ("⚙  הגדרות",self._settings),("🔔  בדיקה",self._test),(None,None),("❌  יציאה",self._exit)]:
            if lbl is None: menu.addSeparator()
            else: a=QAction(lbl,self); a.triggered.connect(cb); menu.addAction(a)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(lambda r: self.widget.show() or self.widget.raise_()
                                     if r in(QSystemTrayIcon.DoubleClick,QSystemTrayIcon.Trigger) else None)
        self._tray.show()

    def _on_alert(self, data: dict):
        a=Alert(data); self.history.appendleft(a); self.widget.add_alert(a)
        if self.config.get("sound",True): self.sound.play()
        if self.config.get("auto_fullscreen",True): self._fullscreen()
        markers=[m for al in list(self.history)[:5] for m in al.map_markers()]
        self.map_win.update_alerts(markers)
        if self.config.get("show_map",True): self._show_map()
        origin_txt = ""
        if a.origin: origin_txt = f"\n{a.origin[0]} מקור: {a.origin[1]}"
        self._tray.showMessage(f"{a.icon}  {a.title}",
                               "  |  ".join(a.cities[:5]) + origin_txt,
                               QSystemTrayIcon.Critical, 5000)

    def _on_clear(self): self.widget.clear_alerts(); self.map_win.clear()

    def _fullscreen(self):
        if self._fs and self._fs.isVisible(): self._fs.close()
        self._fs=FullScreen(self.history, self.history[0] if self.history else None)
        self._fs.show()

    def _show_map(self): self.map_win.show(); self.map_win.raise_()
    def _settings(self):
        d=SettingsDialog(self.config,self.widget); d.request_test.connect(self._test); d.exec_()
    def _test(self):
        self._on_alert({"id":f"T{int(time.time())}","cat":"1","title":"ירי רקטות וטילים",
                        "data":["תל אביב - מרכז העיר","רמת גן","בני ברק","חולון","גבעתיים"]})
    def _exit(self): self.worker.stop(); self.quit()

if __name__=="__main__":
    app=RedAlertApp(); sys.exit(app.exec_())
