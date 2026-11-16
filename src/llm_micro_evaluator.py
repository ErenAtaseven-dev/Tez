"""
TEZ GEMMA ANALİZ — MORFOLOJI KATMANI (v_final)
===============================================
Input  : Tez_Direnç_Dili_1050_LİNGUİSTİK_FINAL.xlsx
Model  : gemma2:9b (local)
Output : Tez_ANALIZ_1050_DETAYLI.xlsx + Tez_ALTIN_ORNEKLER_50_BEST.xlsx

MİMARİ:
  [xlsx] → [Zemberek/Regex Morfoloji] → [Feature Extraction]
         → [Zenginleştirilmiş Prompt] → [Gemma2 — hipotez başına ayrı call]
         → [Consistency Vote] → [Drift Detection] → [xlsx output]

KURULUM:
  Java 17+ gerekli (zemberek için)
  pip install zemberek-python jpype1

  Zemberek yoksa otomatik olarak regex engine devreye girer.
  Her iki engine de aynı feature dict döndürür — model kodu değişmez.
"""

import pandas as pd
import ollama
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

# ───────────────────────────────────────
# AYARLAR
# ───────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALISMA_DIR     = os.path.join(BASE_DIR, 'sample_outputs')
INPUT_FILE      = os.path.join(CALISMA_DIR, 'Tez_Direnç_Dili_1050_LİNGUİSTİK_FINAL.xlsx')
ANALIZ_FILE     = os.path.join(CALISMA_DIR, 'Tez_ANALIZ_1050_DETAYLI.xlsx')
ALTIN_FILE      = os.path.join(CALISMA_DIR, 'Tez_ALTIN_ORNEKLER_50_BEST.xlsx')
CHECKPOINT_FILE = os.path.join(CALISMA_DIR, 'checkpoint_morfo.json')
LOG_FILE        = os.path.join(CALISMA_DIR, 'analiz_log_morfo.log')

MODEL                  = "gemma2:9b"
BATCH_SIZE             = 20
ALTIN_SAYISI           = 50
CONSISTENCY_THRESHOLD  = 7   # Bu puan ve üzeri → 3x majority vote
DRIFT_WINDOW           = 100  # Her N yorumda rolling average kontrolü

# ───────────────────────────────────────
# LOGGING
# ───────────────────────────────────────

def setup_logger() -> logging.Logger:
    logger = logging.getLogger('tez_morfo')
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        logger.handlers.clear()
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s',
                             datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

logger = setup_logger()

# ───────────────────────────────────────
# CHECKPOINT
# ───────────────────────────────────────

def checkpoint_yukle() -> dict:
    if not os.path.exists(CHECKPOINT_FILE):
        return {}
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Checkpoint: {len(data)} kayıt yüklendi")
        return data
    except Exception as e:
        logger.warning(f"Checkpoint okunamadı: {e}")
        return {}

def checkpoint_kaydet(data: dict):
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Checkpoint kaydedilemedi: {e}")

def checkpoint_temizle():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        logger.info("Checkpoint temizlendi")

# ═══════════════════════════════════════════════════════════════
# MORFOLOJİ MOTORU — Zemberek önce, regex fallback
# ═══════════════════════════════════════════════════════════════

# ── Zemberek entegrasyon denemesi ──────────────────────────────
ZEMBEREK_AKTIF = False
_morphology = None

def _zemberek_yukle():
    """
    Zemberek'i yüklemeyi dene. Başarısızsa sessizce geç.
    Kurulum: pip install zemberek-python jpype1
    """
    global ZEMBEREK_AKTIF, _morphology
    try:
        from zemberek import TurkishMorphology  # type: ignore
        _morphology = TurkishMorphology.create_with_defaults()
        ZEMBEREK_AKTIF = True
        logger.info("Zemberek yüklendi — morfolojik analiz aktif")
    except ImportError:
        logger.info("Zemberek bulunamadı — regex engine devrede")
    except Exception as e:
        logger.warning(f"Zemberek yüklenemedi ({e}) — regex engine devrede")

_zemberek_yukle()

# ── H1 için Zemberek morph tag'leri ───────────────────────────
# Zemberek çıktısından hangi tag'leri aradığımız:
ZEMBEREK_H1_TAGS = {'Neces', 'Fut', 'Neg', 'Able', 'Cond', 'Opt', 'Past+Neg'}
ZEMBEREK_H2_TAGS = {'Imp', 'Neces'}

def _zemberek_analiz(yorum: str) -> dict:
    """
    Zemberek ile gerçek morfolojik analiz.
    Token başına tag listesi üretir, H1-H4 sinyal tespiti yapar.
    """
    h1_tags_found = []
    h2_imp_found  = []

    try:
        results = _morphology.analyze_sentence(yorum)
        for word_analysis in results:
            token = word_analysis.word_analysis[0] if word_analysis.word_analysis else None
            if token is None:
                continue
            token_str = str(word_analysis)
            tags = set(re.findall(r'\b([A-Z][a-zA-Z]+)\b', token_str))

            if tags & ZEMBEREK_H1_TAGS:
                h1_tags_found.append(word_analysis.inp)
            if 'Imp' in tags or 'Neces' in tags:
                h2_imp_found.append(word_analysis.inp)
    except Exception as e:
        logger.debug(f"Zemberek token analiz hatası: {e}")

    return {
        'h1_zemberek_tokens': h1_tags_found,
        'h2_zemberek_tokens': h2_imp_found,
    }

# ── Regex kural seti (fallback + H3/H4 için her zaman aktif) ──
_RE = {
    'h1_gereklilik': re.compile(
        r'\b\w+(?:malı|meli|malıyım|meliyim|malısın|melisin|malıdır|melidir)\b', re.I),
    'h1_gelecek': re.compile(
        r'\b\w+(?:acak|ecek|acağım|eceğim|acaksın|eceksin|cem|cam|caz|cez|caksın|ceksin)\b', re.I),
    'h1_olumsuzluk': re.compile(
        r'\b\w+(?:maz|mez|mayacak|meyecek|mamak|memek|madı|medi|mıyor|miyor|micam|mıycak|miycek|miycem|miycan)\b'
        r'|\b(?:değil|hiç|asla|kesinlikle)\b', re.I),
    'h1_modal': re.compile(
        r'\b(?:zorunda|gerek|lazım|şart|mecbur|ihtiyaç var)\b', re.I),
    'h1_donusum': re.compile(
        r'\b(?:artık|eskisi gibi değil|değiştim|farklıyım|değişti|'
        r'dönüştüm|büyüdüm|güçlendim|iyileştim)\b', re.I),
    'h2_sabir': re.compile(
        r'\b(?:güçlü ol|sabret|sabır|metanet|dayan|dayanmalı|dayanman|'
        r'pes etme|vazgeçme|savaş|mücadele|diren)\b', re.I),
    'h2_dini': re.compile(
        r'\b(?:allah|kader|imtihan|nasip|inşallah|sabır ver|kadere|'
        r'takdir|rabb|bismillah|maşallah)\b', re.I),
    'h2_zaman': re.compile(
        r'\b(?:zamanla|zaman geçtikçe|vakit geçince|'
        r'günler geçer|unutulur|iyileşir|geçecek)\b', re.I),
    'h3_kiyaslama': re.compile(
        r'\b(?:tek ölen|herkes ölür|sadece sen değil|başkaları da|'
        r'daha kötüsü|ne kadar da|herkese olur)\b', re.I),
    'h3_siradan': re.compile(
        r'\b(?:abartma|böyle şeyler|normal|alışırsın|geçer gider|'
        r'olur böyle şeyler|herkes yaşıyor)\b', re.I),
    'h4_tekrar': re.compile(r'\b(\w{3,})\b(?:\W+\1){1,}', re.I),
    # Bonus: ironi/sarcasm sinyalleri (manuel review flag'i için)
    'ironi_sinyal': re.compile(
        r'(?:!{2,}|\?{2,}|\.{3,})|'
        r'\b(?:tabii ki|elbette|kesinlikle|tabi|aynen|kesin|aynen canım|he he|aynen aynen)\b.*\b(?:değil|yok|olmaz|öyledir|kesin)\b', re.I),
}

def _regex_analiz(yorum: str) -> dict:
    """Regex tabanlı morfolojik özellik çıkarımı."""
    def match_tokens(pattern_key: str) -> list[str]:
        return [m.group() for m in _RE[pattern_key].finditer(yorum)]

    return {
        'h1_gereklilik_kipi':    bool(_RE['h1_gereklilik'].search(yorum)),
        'h1_gelecek_kararlilik': bool(_RE['h1_gelecek'].search(yorum)),
        'h1_olumsuzluk':         bool(_RE['h1_olumsuzluk'].search(yorum)),
        'h1_modal':              bool(_RE['h1_modal'].search(yorum)),
        'h1_donusum':            bool(_RE['h1_donusum'].search(yorum)),
        'h2_sabir_kalip':        bool(_RE['h2_sabir'].search(yorum)),
        'h2_dini':               bool(_RE['h2_dini'].search(yorum)),
        'h2_zaman':              bool(_RE['h2_zaman'].search(yorum)),
        'h3_kiyaslama':          bool(_RE['h3_kiyaslama'].search(yorum)),
        'h3_siradan':            bool(_RE['h3_siradan'].search(yorum)),
        'h4_tekrar':             bool(_RE['h4_tekrar'].search(yorum)),
        'ironi_sinyal':          bool(_RE['ironi_sinyal'].search(yorum)),
        'h1_eslesen': match_tokens('h1_gereklilik') + match_tokens('h1_olumsuzluk') +
                      match_tokens('h1_modal') + match_tokens('h1_donusum'),
        'h2_eslesen': match_tokens('h2_sabir') + match_tokens('h2_dini'),
        'h3_eslesen': match_tokens('h3_kiyaslama') + match_tokens('h3_siradan'),
        'h4_eslesen': match_tokens('h4_tekrar'),
    }

def morfolojik_analiz(yorum: str) -> dict:
    """
    Ana morfoloji arayüzü — Zemberek veya regex, dışarıdan bakıldığında fark yok.
    Her zaman aynı feature dict döner.
    """
    features = _regex_analiz(yorum)  # Temel: regex her zaman çalışır

    # Zemberek aktifse H1/H2 token listelerini zenginleştir
    if ZEMBEREK_AKTIF:
        z = _zemberek_analiz(yorum)
        # Zemberek tokenlarını regex bulgularına ekle (union, tekrarsız)
        features['h1_eslesen'] = list(set(
            features['h1_eslesen'] + z['h1_zemberek_tokens']
        ))
        features['h2_eslesen'] = list(set(
            features['h2_eslesen'] + z['h2_zemberek_tokens']
        ))
        # Zemberek H1 buldu ama regex bulmadıysa → override
        if z['h1_zemberek_tokens'] and features['h1_sinyal_gucu'] == 0:
            features['h1_olumsuzluk'] = True  # En az bir H1 sinyali

    features['h1_sinyal_gucu'] = sum([
        features['h1_gereklilik_kipi'], features['h1_gelecek_kararlilik'],
        features['h1_olumsuzluk'], features['h1_modal'], features['h1_donusum']
    ])
    features['morfo_engine'] = 'zemberek' if ZEMBEREK_AKTIF else 'regex'
    return features

def kanit_blogu_olustur(yorum: str, features: dict) -> str:
    """
    Morfolojik kanıtları model için okunabilir kanıt bloğuna çevirir.
    Model artık kör değil: hangi tokenlarda ne gördüğünü biliyor.
    Yüksek sinyal → model cevabını bu kanıta dayandırır.
    Düşük sinyal → model bağlamsal yoruma odaklanır.
    """
    bloklar = []

    if features['h1_sinyal_gucu'] > 0 or features['h1_eslesen']:
        bloklar.append(
            f"H1 MORFOLOJİK KANITLAR [{features['morfo_engine']}]:\n"
            f"  Sinyal gücü: {features['h1_sinyal_gucu']}/5\n"
            f"  Tespit edilen tokenlar: {features['h1_eslesen'] or 'yok'}\n"
            f"  Gereklilik kipi(-malı/-meli): {'✓' if features['h1_gereklilik_kipi'] else '✗'} | "
            f"Olumsuzluk: {'✓' if features['h1_olumsuzluk'] else '✗'} | "
            f"Modal(zorunda/lazım): {'✓' if features['h1_modal'] else '✗'} | "
            f"Dönüşüm söylemi: {'✓' if features['h1_donusum'] else '✗'}"
        )

    if any([features['h2_sabir_kalip'], features['h2_dini'], features['h2_zaman']]):
        bloklar.append(
            f"H2 MORFOLOJİK KANITLAR [{features['morfo_engine']}]:\n"
            f"  Tespit edilen tokenlar: {features['h2_eslesen'] or 'yok'}\n"
            f"  Sabır kalıbı: {'✓' if features['h2_sabir_kalip'] else '✗'} | "
            f"Dini teslimiyet: {'✓' if features['h2_dini'] else '✗'} | "
            f"Zaman reçetesi: {'✓' if features['h2_zaman'] else '✗'}"
        )

    if features['h3_kiyaslama'] or features['h3_siradan']:
        bloklar.append(
            f"H3 MORFOLOJİK KANITLAR [{features['morfo_engine']}]:\n"
            f"  Tespit edilen tokenlar: {features['h3_eslesen'] or 'yok'}\n"
            f"  Kıyaslama: {'✓' if features['h3_kiyaslama'] else '✗'} | "
            f"Sıradanlaştırma: {'✓' if features['h3_siradan'] else '✗'}"
        )

    if features['h4_tekrar']:
        bloklar.append(
            f"H4 MORFOLOJİK KANITLAR [{features['morfo_engine']}]:\n"
            f"  Tekrar kalıbı: ✓\n"
            f"  Tespit edilen: {features['h4_eslesen']}"
        )

    if features.get('ironi_sinyal'):
        bloklar.append(
            "⚠ İRONİ/KINAYE SİNYALİ TESPİT EDİLDİ — Bu yorum bağlamsal olarak yüksek bir 'örtük direnç' taşıyor olabilir."
        )

    return '\n\n'.join(bloklar) if bloklar else "Otomatik morfolojik kanıt bulunamadı — bağlamsal analiz yeterli."

# ═══════════════════════════════════════════════════════════════
# PYDANTIC SCHEMA — ENUM ENFORCED
# ═══════════════════════════════════════════════════════════════

BASKINTipi = Literal[
    "DILSEL", "NORMATIF", "DUYARSIZ", "KALIP",
    "SORGULAMA", "METAFOR", "KARMA", "BELIRSIZ"
]

class TamAnalizSonucu(BaseModel):
    H1: bool = Field(description="Dilsel Direnç/Güçlenme: Olumsuzluk ekleriyle hayata tutunma ('yıkılamam', 'kalamam') veya iyileşmeye dönük güçlü fiil kipleri var mı?")
    H2: bool = Field(description="Umut ve Kabullenme: Süreci kabullenme, zamana bırakma, sabırlı olma ('zaman ilacıdır', 'acelem yok') göstergeleri var mı?")
    H3: bool = Field(description="Metaforik Dil/Benzetme: Psikolojik iyileşmeyi anlatan mecazlar ('küllerinden doğmak', 'karanlıktan çıkmak') var mı?")
    H4: bool = Field(description="Bilişsel Farkındalık/Olgunlaşma: Zıtlık (gitmek-kalmak) veya geçmiş-gelecek karşılaştırmaları ile içsel farkındalık belirtisi var mı?")
    guven: int = Field(description="Ortalama Güven Skoru: 1=belirsiz, 5=çok emin")
    puan: int  = Field(description="Altın Puan (0-10): Zorlayıcı deneyimlere karşı geliştirilen PSİKOLOJİK SAĞLAMLIK, toparlanma ve duygusal iyileşme belirtisi taşıyan yorumlara YÜKSEK, basit tepkilere DÜŞÜK puan ver.")
    baskin: BASKINTipi = Field(description="Yorumdaki en baskın iyileşme/sağlamlık özelliği (DILSEL, NORMATIF, METAFOR vs)")

TEK_GECIS_PROMPT = """\
Sosyoloji, pskiloji ve dilbilim araştırmacısı olarak bu yorumu TEK SEFERDE analiz et.

YORUM: "{yorum}"

OTOMATİK MORFOLOJİK ÖN-ANALİZ:
{kanit}

{ironi_uyari}
ÖNEMLİ TEZ BİLGİSİ (KAVRAMSAL ÇERÇEVE): 
Bu tezin amacı "Otoriteye argo/küfürle siyasi isyan edenleri" BULMAK DEĞİLDİR! 
Tezin asıl amacı: Bireylerin zorlayıcı yaşam deneyimleri, kayıplar ve travmalar karşısında geliştirdikleri "Psikolojik Sağlamlık (Resilience)", duygusal iyileşme, hayata tutunma ve toparlanma söylemlerini bulmaktır.

Bu yüzden:
- "Zamanla her şey geçer", "Küllerimden doğarım", "Artık hiçbir şey beni yıkamaz", "Belki de gitmek kalmaktan daha cesurcaydı" gibi kabullenme, umut, güçlenme ve metafor içeren yorumlar TEZİN EN KIYMETLİ, ALTIN (10 PUAN) ÖRNEKLERİDİR.
- Agresif, dümdüz hakaret eden veya sadece "çok üzüldüm" diyen empatik fakat dirençsiz metinler düşük puan almalıdır.

YAPMAN GEREKENLER (JSON döndür):
1. H1 (Dilsel Güçlenme), H2 (Umut/Kabullenme), H3 (Metafor), H4 (Farkındalık) analizini yap (bool)
2. Analiz genel ortalama güvenini ver (1-5)
3. Yorum 'Psikolojik Direnç (İyileşme/Sağlamlık)' omurgasına ne kadar uygun, Altın Puan ver (0-10)
4. En baskın karakteristiği şeç.
"""

def tek_gecis_call(yorum: str, kanit: str, ironi: bool) -> dict:
    ironi_uyari = (
        "⚠ DİKKAT: İroni veya sarkastik kinaye sinyali tespit edildi. "
        "Bu ifade otorite/sistemle dalga geçerek bağlamsal bir direniş gösteriyor olabilir — altın puanı buna göre yüksek tut.\n"
        if ironi else ""
    )
    prompt = TEK_GECIS_PROMPT.format(yorum=yorum, kanit=kanit, ironi_uyari=ironi_uyari)
    
    try:
        res = ollama.chat(
            model=MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            format=TamAnalizSonucu.model_json_schema(),
            options={'temperature': 0.1}
        )
        p = TamAnalizSonucu.model_validate_json(res['message']['content'])
        baskin = p.baskin if p.baskin in [
            "DILSEL", "NORMATIF", "DUYARSIZ", "KALIP",
            "SORGULAMA", "METAFOR", "KARMA", "BELIRSIZ"
        ] else "BELIRSIZ"
        return {
            'H1': p.H1, 'H2': p.H2, 'H3': p.H3, 'H4': p.H4,
            'guven_ort': p.guven, 'puan': p.puan, 'baskin': baskin
        }
    except Exception as e:
        logger.warning(f"  Tek geçiş call hatası: {str(e)[:60]}")
        return {'H1': False, 'H2': False, 'H3': False, 'H4': False, 'guven_ort': 1, 'puan': 0, 'baskin': 'BELIRSIZ'}

def majority_vote_tek_gecis(yorum: str, kanit: str, ironi: bool, runs: int = 3) -> dict:
    sonuclar = []
    for _ in range(runs):
        sonuclar.append(tek_gecis_call(yorum, kanit, ironi))
        
    h1 = sum([s['H1'] for s in sonuclar]) > (runs/2)
    h2 = sum([s['H2'] for s in sonuclar]) > (runs/2)
    h3 = sum([s['H3'] for s in sonuclar]) > (runs/2)
    h4 = sum([s['H4'] for s in sonuclar]) > (runs/2)
    guven = round(sum([s['guven_ort'] for s in sonuclar]) / runs)
    puan = round(sum([s['puan'] for s in sonuclar]) / runs)
    try:
        baskin = Counter([s['baskin'] for s in sonuclar]).most_common(1)[0][0]
    except:
        baskin = "BELIRSIZ"
    
    return {
        'H1': h1, 'H2': h2, 'H3': h3, 'H4': h4,
        'guven_ort': guven, 'puan': puan, 'baskin': baskin
    }

def tam_analiz(yorum: str, idx: int) -> dict:
    try:
        features = morfolojik_analiz(yorum)
        kanit = kanit_blogu_olustur(yorum, features)
        ironi = features.get('ironi_sinyal', False)

        ilk = tek_gecis_call(yorum, kanit, ironi)
        consistency = False

        if ilk['puan'] >= CONSISTENCY_THRESHOLD:
            ilk = majority_vote_tek_gecis(yorum, kanit, ironi, runs=3)
            consistency = True

        result = {
            'H1': ilk['H1'], 'H2': ilk['H2'], 'H3': ilk['H3'], 'H4': ilk['H4'],
            'G1': ilk['guven_ort'], 'G2': ilk['guven_ort'], 
            'G3': ilk['guven_ort'], 'G4': ilk['guven_ort'],
            'baskin': ilk['baskin'], 'puan': ilk['puan'],
            'h1_sinyal': features['h1_sinyal_gucu'],
            'morfo_engine': features['morfo_engine'],
            'ironi_sinyal': ironi,
            'consistency': consistency,
            'status': 'OK'
        }
        logger.debug(f"idx={idx} | H:{{int(result['H1'])}}{{int(result['H2'])}}{{int(result['H3'])}}{{int(result['H4'])}} | {{result['baskin']}} | puan={{result['puan']}} | sinyal={{features['h1_sinyal_gucu']}} | ironi={{ironi}}")
        return result

    except Exception as e:
        logger.error(f"idx={idx} kritik hata: {str(e)[:50]}")
        return {'H1': False, 'H2': False, 'H3': False, 'H4': False, 'G1': 1, 'G2': 1, 'G3': 1, 'G4': 1, 'baskin': 'BELIRSIZ', 'puan': 0, 'h1_sinyal': 0, 'morfo_engine': 'error', 'ironi_sinyal': False, 'consistency': False, 'status': str(e)[:100]}

# ═══════════════════════════════════════════════════════════════
# DRİFT DETECTION
# ═══════════════════════════════════════════════════════════════

def drift_kontrol(checkpoint: dict, idx: int):
    if idx < DRIFT_WINDOW * 2:
        return
    son = [checkpoint[str(i)]['puan']
           for i in range(idx - DRIFT_WINDOW, idx)
           if str(i) in checkpoint]
    onceki = [checkpoint[str(i)]['puan']
              for i in range(idx - DRIFT_WINDOW * 2, idx - DRIFT_WINDOW)
              if str(i) in checkpoint]
    if not son or not onceki:
        return
    son_ort, onceki_ort = sum(son) / len(son), sum(onceki) / len(onceki)
    if onceki_ort > 0:
        sapma = abs(son_ort - onceki_ort) / onceki_ort
        if sapma > 0.20:
            logger.warning(
                f"DRİFT | idx={idx} | önceki_ort={onceki_ort:.2f} → "
                f"son_ort={son_ort:.2f} | sapma=%{sapma*100:.1f}"
            )

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    logger.info("=" * 65)
    logger.info("TEZ GEMMA ANALİZ — MORFOLOJİ KATMANI")
    logger.info(f"Morfo engine: {'Zemberek' if ZEMBEREK_AKTIF else 'Regex'}")
    logger.info(f"Consistency threshold: {CONSISTENCY_THRESHOLD}+")
    logger.info(f"Drift window: {DRIFT_WINDOW}")
    logger.info("=" * 65)

    # 1. VERİ OKU
    logger.info(f"Veri: {INPUT_FILE}")
    try:
        df = pd.read_excel(INPUT_FILE)
        if 'Dönem' in df.columns:
            df.rename(columns={'Dönem': 'Donem'}, inplace=True)
        logger.info(f"{len(df)} yorum | Kolonlar: {list(df.columns)}")
    except Exception as e:
        logger.error(f"Veri okunamadı: {e}")
        sys.exit(1)

    # 2. CHECKPOINT
    checkpoint = checkpoint_yukle()
    atlanan = len(checkpoint)
    logger.info(f"{atlanan} tamamlandı, {len(df) - atlanan} kaldı")

    # 3. ANALİZ
    start = datetime.now()
    hata_sayisi = 0

    for idx, row in df.iterrows():
        if str(idx) in checkpoint:
            continue
        yorum = str(row.get('Yorum', ''))
        analiz = tam_analiz(yorum, idx)
        if analiz['status'] != 'OK':
            hata_sayisi += 1
        checkpoint[str(idx)] = analiz

        if (idx + 1) % BATCH_SIZE == 0:
            checkpoint_kaydet(checkpoint)
            elapsed = (datetime.now() - start).total_seconds()
            done = idx + 1 - atlanan
            if done > 0:
                kalan_sn = (len(df) - idx - 1) * (elapsed / done)
                logger.info(
                    f"Progress: {idx+1}/{len(df)} | "
                    f"Kalan: {kalan_sn/60:.1f}m | Hata: {hata_sayisi}"
                )
            drift_kontrol(checkpoint, idx)

    checkpoint_kaydet(checkpoint)
    logger.info(f"Analiz bitti | Süre: {datetime.now() - start} | Hata: {hata_sayisi}")

    # 4. BİRLEŞTİR
    analiz_list = [checkpoint[str(i)] for i in range(len(df))]
    analiz_df = pd.DataFrame(analiz_list)
    df_result = pd.concat([df.reset_index(drop=True),
                           analiz_df.reset_index(drop=True)], axis=1)

    df_result['h_toplam'] = (df_result['H1'].astype(int) + df_result['H2'].astype(int) +
                              df_result['H3'].astype(int) + df_result['H4'].astype(int))
    df_result['hybrid'] = df_result['h_toplam'].apply(
        lambda x: 'QUAD' if x >= 3 else ('DUAL' if x == 2 else ('TEK' if x == 1 else 'SPAM'))
    )
    df_result['guven_ort'] = (
        df_result['G1'] + df_result['G2'] + df_result['G3'] + df_result['G4']
    ) / 4.0

    # 5. ÇIKTI 1: DETAYLI
    logger.info(f"Kaydediliyor: {ANALIZ_FILE}")
    cikti = df_result[[
        'Donem', 'Yorum', 'H1', 'H2', 'H3', 'H4', 'h_toplam', 'hybrid',
        'guven_ort', 'h1_sinyal', 'baskin', 'puan',
        'ironi_sinyal', 'consistency', 'morfo_engine', 'status'
    ]].copy()
    cikti.columns = [
        'Dönem', 'Yorum', 'H1', 'H2', 'H3', 'H4', 'Toplam_Hipotez', 'Hybrid',
        'Güven_Ort', 'H1_Sinyal_Gücü', 'Baskın', 'Altın_Puan',
        'İroni_Sinyali', 'Consistency', 'Morfo_Engine', 'Durum'
    ]
    cikti.to_excel(ANALIZ_FILE, index=False)

    # 6. ÇIKTI 2: ALTIN
    logger.info(f"Altın seçimi: Her Dönem İçin Ayrı Top {ALTIN_SAYISI}")
    # İroni, tespit edilmiş en üst örtük dirençtir. Havuzdan çıkarılmaz.
    altin_havuz = df_result
    # Altın seçimini donem bazlı grupla ve her gruptan en yüksek puanlıları çekerek izolasyonu sağla
    altin = altin_havuz.sort_values('puan', ascending=False).groupby('Donem').head(ALTIN_SAYISI).reset_index(drop=True)
    altin_cikti = altin[[
        'Donem', 'Yorum', 'H1', 'H2', 'H3', 'H4',
        'hybrid', 'baskin', 'puan', 'guven_ort', 'consistency'
    ]].copy()
    altin_cikti.columns = [
        'Dönem', 'Yorum', 'H1', 'H2', 'H3', 'H4',
        'Hybrid', 'Baskın', 'Puan', 'Güven_Ort', 'Consistency'
    ]
    altin_cikti.to_excel(ALTIN_FILE, index=False)

    # 7. İSTATİSTİKLER
    n = len(df_result)
    logger.info("─── SONUÇ ───")
    for lbl, col in [('H1 Dilsel', 'H1'), ('H2 Normatif', 'H2'),
                     ('H3 Duyarsız', 'H3'), ('H4 Kalıp', 'H4')]:
        s = df_result[col].sum()
        logger.info(f"  {lbl}: {s}/{n} ({s/n*100:.1f}%)")
    logger.info(f"  Ortalama Güven: {df_result['guven_ort'].mean():.2f}/5")
    logger.info(f"  H1 Ortalama Sinyal Gücü: {df_result['h1_sinyal'].mean():.2f}/5")
    logger.info(f"  İroni sinyali: {df_result['ironi_sinyal'].sum()} yorum → potansiyel örtük direnç olarak işaretlendi")
    logger.info(f"  Consistency uygulandı: {df_result['consistency'].sum()} yorum")
    logger.info(f"  Altın Puan Ort: {df_result['puan'].mean():.2f}/10")
    logger.info("Hybrid:\n" + df_result['hybrid'].value_counts().to_string())
    logger.info("Baskın:\n" + df_result['baskin'].value_counts().to_string())

    # Düşük güven uyarısı
    dusuk = df_result[df_result['guven_ort'] < 2.0]
    if len(dusuk) > 0:
        logger.warning(f"MANUEL REVİEW: {len(dusuk)} yorum güven < 2.0")

    checkpoint_temizle()
    logger.info("=" * 65)
    logger.info(f"Detaylı : {ANALIZ_FILE}")
    logger.info(f"Altın   : {ALTIN_FILE}")
    logger.info(f"Log     : {LOG_FILE}")
    logger.info("=" * 65)


if __name__ == '__main__':
    main()