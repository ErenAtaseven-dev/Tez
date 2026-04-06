import pandas as pd
import re

# 1. DOSYA YAPILANDIRMASI
files = {
    'A_Olum_Ayi': 'yorumlar_tez_1.csv',
    'B_Durusma': 'yorumlar_tez_2.csv',
    'C_Sonuc': 'yorumlar_tez_3.csv'
}

# 2. HİPOTEZ ODAKLI ANAHTAR KELİME HAVUZLARI
# Bu kelimelerden biri geçiyorsa, yorumun bir 'önermesi' olma ihtimali yüksektir.
keywords = r'güçlü|dik|ağla|zorunda|dayan|toparla|metanet|sabret|sabır|abart|herkes|tek ölen|yeter|üzülme|allah|kader|vade|cennet|mekan|dua|nasip|melek|rabbim|geçe|zaman|hayat|önüne bak|yanında|başınız sağ|acı|üzüntü|paylaş|adalet|ceza|katil|lanet'

# 3. FİİL/EYLEM KONTROLÜ İÇİN EK HAVUZU (Simple NLP)
# Türkçedeki yaygın çekim ve kip eklerini tarayarak 'Melek kuzu' gibi nitelemeleri eleriz.
verb_suffixes = r'(sun|ver|ol|dur|yap|et|git|gel|bak|geç|dayan|sabret|kal|bit|başa|zorunda|malı|meli|acak|ecek|iyor|ar|er|sın|sin|nız|niz)'

def smart_filter(text):
    if not isinstance(text, str): return False
    
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
    return has_keyword and has_verb

# 4. İŞLEME VE ÖRNEKLEM OLUŞTURMA
all_samples = []

for period, filename in files.items():
    print(f"--- {filename} İşleniyor ---")
    try:
        df = pd.read_csv(filename)
        df = df.dropna(subset=['yorum'])
        
        # Akıllı filtreyi uygula
        df['is_valid'] = df['yorum'].apply(smart_filter)
        df_filtered = df[df['is_valid'] == True].copy()
        
        # Her dönemden 350 adet rastgele seç (Toplam 1050)
        sample_count = min(350, len(df_filtered))
        df_sample = df_filtered.sample(n=sample_count, random_state=42)
        
        df_sample['Donem'] = period
        df_sample['Kategori'] = "" # Şevval burayı manuel dolduracak
        df_sample['Analiz_Notu'] = "" # Örneklem açıklamaları için
        
        all_samples.append(df_sample)
        print(f"{period}: {len(df_filtered)} geçerli yorumdan {sample_count} adet seçildi.")
        
    except Exception as e:
        print(f"Hata: {filename} işlenemedi. {e}")

# 5. SONUÇLARI KAYDET
if all_samples:
    final_df = pd.concat(all_samples, ignore_index=True)
    final_df = final_df[['Donem', 'tarih', 'yorum', 'Kategori', 'Analiz_Notu']]
    
    # Excel olarak dışa aktar (Şevval'in rahat çalışması için)
    final_df.to_excel('Tez_Analiz_Seti_1050.xlsx', index=False)
    print("\nİşlem Tamam! 'Tez_Analiz_Seti_1050.xlsx' dosyası hazır.")
else:
    print("Hiç veri çekilemedi.")