"""
TABAKALI ÖRNEKLEM VE MORFOLOJİK ÖN-FİLTRE MOTORU (Stratified Sampler)
=====================================================================
175.857 satırlık ham veri havuzundan (3 dönem) morfolojik kip/eylem ekleri
ve anahtar kelime matrisine göre anlamlı önerme taşıyan kayıtları süzer;
her dönemden deterministik tohumlama (random_state=42) ile 350'şer kayıt
çekerek 1.050 satırlık çekirdek LLM doğrulama örneklemini oluşturur.
"""

import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv('RAW_DATA_DIR', os.path.join(BASE_DIR, 'data'))
OUTPUT_DIR = os.path.join(BASE_DIR, 'sample_outputs')

# 1. DOSYA YAPILANDIRMASI
files = {
    'A_Olum_Ayi': os.path.join(DATA_DIR, 'yorumlar_tez_1.csv'),
    'B_Durusma': os.path.join(DATA_DIR, 'yorumlar_tez_2.csv'),
    'C_Sonuc': os.path.join(DATA_DIR, 'yorumlar_tez_3.csv')
}

# 2. HİPOTEZ ODAKLI ANAHTAR KELİME HAVUZLARI
# Bu kelimelerden biri geçiyorsa, yorumun bir 'önermesi' olma ihtimali yüksektir.
keywords = (
    r'güçlü|dik|ağla|zorunda|dayan|toparla|metanet|sabret|sabır|abart|'
    r'herkes|tek ölen|yeter|üzülme|allah|kader|vade|cennet|mekan|dua|'
    r'nasip|melek|rabbim|geçe|zaman|hayat|önüne bak|yanında|başınız sağ|'
    r'acı|üzüntü|paylaş|adalet|ceza|katil|lanet'
)

# 3. FİİL/EYLEM KONTROLÜ İÇİN EK HAVUZU (Simple NLP)
# Türkçedeki yaygın çekim ve kip eklerini tarayarak salt nitelemeleri eleriz.
verb_suffixes = (
    r'(sun|ver|ol|dur|yap|et|git|gel|bak|geç|dayan|sabret|kal|bit|'
    r'başa|zorunda|malı|meli|acak|ecek|iyor|ar|er|sın|sin|nız|niz)'
)


def smart_filter(text):
    if not isinstance(text, str):
        return False

    # Emojileri ve gereksiz boşlukları temizle
    clean_text = re.sub(r'[^\w\s]', '', text)
    words = clean_text.split()

    # KRİTER 1: Kelime Sayısı (En az 5 kelime - Kısa kalıpları ve etiketleri eler)
    if len(words) < 5:
        return False

    # KRİTER 2: İçerik Kontrolü (Hipotez kelimelerinden biri geçiyor mu?)
    has_keyword = re.search(keywords, text, re.IGNORECASE)

    # KRİTER 3: Fiil/Eylem Kontrolü (İçinde bir aksiyon veya kip eki var mı?)
    has_verb = re.search(verb_suffixes, text, re.IGNORECASE)

    # Eğer hem anlamlı bir kelime geçiyor hem de bir eylem/kip barındırıyorsa geçerlidir
    return bool(has_keyword and has_verb)


if __name__ == "__main__":
    all_samples = []

    for period, filename in files.items():
        print(f"--- {os.path.basename(filename)} İşleniyor ---")
        try:
            df = pd.read_csv(filename)
            df = df.dropna(subset=['yorum'])

            # Akıllı filtreyi uygula
            df['is_valid'] = df['yorum'].apply(smart_filter)
            df_filtered = df[df['is_valid'] == True].copy()

            # Her dönemden 350 adet rastgele seç (Toplam 1050 - Deterministik Seed)
            sample_count = min(350, len(df_filtered))
            df_sample = df_filtered.sample(n=sample_count, random_state=42)

            df_sample['Donem'] = period
            df_sample['Kategori'] = ""      # Alt katman sınıflandırma alanı
            df_sample['Analiz_Notu'] = ""   # Doğrulama ve kanıt açıklamaları

            all_samples.append(df_sample)
            print(f"{period}: {len(df_filtered)} geçerli yorumdan {sample_count} adet seçildi.")

        except Exception as e:
            print(f"Hata: {filename} işlenemedi. {e}")

    if all_samples:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        final_df = pd.concat(all_samples, ignore_index=True)
        final_df = final_df[['Donem', 'tarih', 'yorum', 'Kategori', 'Analiz_Notu']]

        out_path = os.path.join(OUTPUT_DIR, 'Tez_Analiz_Seti_1050.xlsx')
        final_df.to_excel(out_path, index=False)
        print(f"\nİşlem Tamam! '{out_path}' dosyası hazır.")
    else:
        print("Hiç veri çekilemedi.")
