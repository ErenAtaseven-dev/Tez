import pandas as pd
from google import genai
from google.genai import types
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
        logging.FileHandler('analiz.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 1. KURULUM (Dosya yükleme derdi tamamen kaldırıldı)
client = genai.Client(api_key="" \
"")

# 2. ANAYASA DOĞRUDAN KODUN İÇİNE GÖMÜLDÜ!
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
    # String tipi elle belirtilerek dtype hatası önceden engelleniyor
    df[col] = df[col].astype('object')

logger.info("Çıktı sütunları başlatıldı")

logger.info("Analiz başlıyor... (Rate Limit & Retry koruması aktif)")

# Rate limit ve retry konfigürasyonu
MAX_RETRIES = 3
INITIAL_WAIT = 4
BASE_WAIT = 3  # Her istek arasında 3 saniye

for index, row in df.iterrows():
    yorum = str(row['yorum'])
    sadece_metin = re.sub(r'[^\w\s]', '', yorum)
    
    if len(sadece_metin.split()) < 4:
        df.at[index, 'Analiz_Notu'] = "Yetersiz Uzunluk"
        logger.debug(f"[{index+1}] Atlanacak - Yetersiz uzunluk")
        continue 
    
    retry_count = 0
    başarılı = False
    
    while retry_count < MAX_RETRIES and not başarılı:
        try:
            # Gemini 2.5 Flash - En yeni, ücretsiz, hızlı, iyi performans
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{sistem_mesaji}\n\nAnaliz edilecek yorum: {yorum}",
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # JSON parsing - taşkın markdown kodlarını temizle
            ham_cevap = response.text.replace("```json", "").replace("```", "").strip()
            veri = json.loads(ham_cevap)
            
            # Pandas dtype hatalarını önlemek için None yerine boş string kullan
            df.at[index, 'Birincil_Kategori'] = str(veri.get('Birincil_Kategori', '')).strip() or None
            df.at[index, 'Ikincil_Kategori'] = str(veri.get('Ikincil_Kategori', '')).strip() or None
            df.at[index, 'Kanit_Alinti'] = str(veri.get('Kanit_Alinti', '')).strip() or None
            df.at[index, 'Analiz_Notu'] = str(veri.get('Analiz_Notu', '')).strip() or None
            
            logger.info(f"[{index+1}/1050] Başarı: {veri.get('Birincil_Kategori')}")
            başarılı = True
            
        except json.JSONDecodeError as e:
            retry_count += 1
            logger.warning(f"[{index+1}] JSON Hata (Deneme {retry_count}): {str(e)[:100]}")
            if retry_count < MAX_RETRIES:
                wait_time = INITIAL_WAIT * (2 ** retry_count)
                logger.info(f"[{index+1}] {wait_time}s sonra yeniden deneniyor...")
                time.sleep(wait_time)
            else:
                df.at[index, 'Analiz_Notu'] = "JSON Parsing Hatası"
                logger.error(f"[{index+1}] JSON hatası düzeltilemedi")
                
        except Exception as e:
            error_msg = str(e)
            retry_count += 1
            
            # Rate limit kontrolü
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait_time = INITIAL_WAIT * (2 ** retry_count)
                logger.warning(f"[{index+1}] Rate Limit! {wait_time}s bekleniyor...")
                time.sleep(wait_time)
            # Model bulunamama hatası
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                logger.error(f"[{index+1}] Model bulunamadı: {error_msg[:100]}")
                df.at[index, 'Analiz_Notu'] = "Model Bulunamadı"
                break
            else:
                logger.error(f"[{index+1}] API Hatası (Deneme {retry_count}): {error_msg[:100]}")
                if retry_count < MAX_RETRIES:
                    wait_time = INITIAL_WAIT * (2 ** retry_count)
                    logger.info(f"[{index+1}] {wait_time}s sonra yeniden deneniyor...")
                    time.sleep(wait_time)
                else:
                    df.at[index, 'Analiz_Notu'] = "API Hatası"
    
    # Base bekleme - API rate limit koruması
    time.sleep(BASE_WAIT)

# Sonuçları kaydet
try:
    output_file = f"Tez_Analizi_Final_Cikti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(output_file, index=False)
    logger.info(f"\n✓ İşlem Tamamlandı! Dosya kaydedildi: {output_file}")
    logger.info(f"Toplam satır: {len(df)} | Başarılı: {len(df[df['Analiz_Notu'].notna()])}")
except Exception as e:
    logger.error(f"Dosya yazme hatası: {e}")
    exit(1)