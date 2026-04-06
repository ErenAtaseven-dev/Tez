import pandas as pd
import requests
import time
import json
import re
import logging
from datetime import datetime

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analiz_ollama.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ollama lokal endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

# 2. ANAYASA
sistem_mesaji = """Sen bir Dijital Beşeri Bilimler uzmanısın. 
Aşağıda verilen 'TEZ KODLAMA REHBERİ' kurallarına %100 sadık kalarak sosyal medya yorumlarını analiz edeceksin.

--- TEZ KODLAMA REHBERİ ---
1. Kategori: Destekleyici ve Dayanıklılık Telkinleri
- Tanım: Yas tutan aileye destek olmayı, psikolojik direnç aşılamayı amaçlar.
- Belirleyiciler: "Güçlü ol", "zamanla geçer", "başaracaksınız", "diren", "ayağa kalk", "hayat devam ediyor".

2. Kategori: Duyarsız ve Olumsuz Söylemler (H3)
- Tanım: Acıyı sıradanlaştıran, empati yoksunu ifadeler.
- Belirleyiciler: "Tek ölen senin çocuğun değil", "abartma".

3. Kategori: Kaderci ve Otomatikleşmiş Taziye Kalıpları (H4)
- Tanım: Dini/kültürel metanet mesajları.
- Belirleyiciler: "Mekanı cennet olsun", "Allah sabır versin", "Başınız sağ olsun".

4. Kategori: Eleştirel / Adalet Arayışı
- Tanım: Hukuki sürece ve faillere yönelik öfke, adalet talebi.
- Belirleyiciler: "Adalet yerini bulsun", "En ağır cezayı alsınlar", "İdam".

HİBRİT KURALI: Eğer bir yorum "Mekanı cennet olsun" gibi kaderci başlayıp sonrasında hukuki süreci eleştiriyorsa, Birincil Kategori mutlaka "Eleştirel / Adalet Arayışı" olmalıdır.
---------------------------

Çıktıyı SADECE şu JSON formatında ver:
{
  "Birincil_Kategori": "Kategori",
  "Ikincil_Kategori": "Kategori veya Yok",
  "Kanit_Alinti": "Karara neden olan anahtar kelime/fiil",
  "Analiz_Notu": "Rehberdeki kurama dayanan akademik tahlil"
}"""

# 3. EXCEL OKUMA VE PANDAS KORUMASI
try:
    df = pd.read_excel('Tez_Analiz_v2.xlsx')
    logger.info(f"Excel dosyası okundu: {len(df)} satır")
except FileNotFoundError:
    logger.error("Tez_Analiz_v2.xlsx dosyası bulunamadı!")
    exit(1)

for col in ['Birincil_Kategori', 'Ikincil_Kategori', 'Kanit_Alinti', 'Analiz_Notu']:
    if col not in df.columns:
        df[col] = None
    df[col] = df[col].astype('object')

logger.info("Çıktı sütunları başlatıldı")
logger.info("Analiz başlıyor... (OLLAMA - Sınırsız, Hızlı)")

# Rate limit konfigürasyonu
BASE_WAIT = 0.5  # Ollama lokal olduğu için çok az bekleme

for index, row in df.iterrows():
    yorum = str(row['yorum'])
    sadece_metin = re.sub(r'[^\w\s]', '', yorum)
    
    if len(sadece_metin.split()) < 4:
        df.at[index, 'Analiz_Notu'] = "Yetersiz Uzunluk"
        logger.debug(f"[{index+1}] Atlanacak - Yetersiz uzunluk")
        continue 
    
    try:
        # Ollama API çağrısı
        prompt = f"{sistem_mesaji}\n\nAnaliz edilecek yorum: {yorum}\n\nJSON ÇIKTISI:"
        
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "dolphin-mixtral",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3  # Daha deterministik cevaplar
            },
            timeout=120
        )
        
        if response.status_code != 200:
            logger.error(f"[{index+1}] Ollama Hatası: HTTP {response.status_code}")
            df.at[index, 'Analiz_Notu'] = f"Ollama Hatası ({response.status_code})"
            continue
        
        # JSON parsing
        response_data = response.json()
        ham_cevap = response_data.get('response', '')
        
        # Cevaptan JSON payını çıkart
        try:
            json_start = ham_cevap.find('{')
            json_end = ham_cevap.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = ham_cevap[json_start:json_end]
                veri = json.loads(json_str)
            else:
                raise ValueError("JSON formatı bulunamadı")
        except json.JSONDecodeError as e:
            logger.warning(f"[{index+1}] JSON Parse Hatası: {str(e)[:100]}")
            df.at[index, 'Analiz_Notu'] = "JSON Parse Hatası"
            continue
        
        # Verileri ata
        df.at[index, 'Birincil_Kategori'] = str(veri.get('Birincil_Kategori', '')).strip() or None
        df.at[index, 'Ikincil_Kategori'] = str(veri.get('Ikincil_Kategori', '')).strip() or None
        df.at[index, 'Kanit_Alinti'] = str(veri.get('Kanit_Alinti', '')).strip() or None
        df.at[index, 'Analiz_Notu'] = str(veri.get('Analiz_Notu', '')).strip() or None
        
        logger.info(f"[{index+1}/1050] Başarı: {veri.get('Birincil_Kategori')}")
        
    except requests.exceptions.ConnectionError:
        logger.error(f"[{index+1}] OLLAMA BAĞLANTISI YOK! Ollama çalışıyor mu kontrol et.")
        df.at[index, 'Analiz_Notu'] = "Ollama Bağlantı Hatası"
        break
    except Exception as e:
        logger.error(f"[{index+1}] Hata: {str(e)[:100]}")
        df.at[index, 'Analiz_Notu'] = "İşlem Hatası"
    
    # Minimal bekleme (lokal olduğu için)
    time.sleep(BASE_WAIT)

# Sonuçları kaydet
try:
    output_file = f"Tez_Analizi_Final_Cikti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(output_file, index=False)
    logger.info(f"\n✓ İşlem Tamamlandı! Dosya kaydedildi: {output_file}")
    logger.info(f"Toplam satır: {len(df)} | İşlenen: {len(df[df['Analiz_Notu'].notna()])}")
except Exception as e:
    logger.error(f"Dosya yazme hatası: {e}")
    exit(1)
