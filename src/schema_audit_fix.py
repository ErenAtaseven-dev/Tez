import os
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from macro_nlp_pipeline import kategori_bul, kelime_say

files = [
    os.path.join(BASE_DIR, 'sample_outputs', 'Tez_ALTIN_ORNEKLER_50_BEST.xlsx'),
    os.path.join(BASE_DIR, 'sample_outputs', 'Tez_ANALIZ_1050_DETAYLI.xlsx'),
]

for f in files:
    try:
        df = pd.read_excel(f)
        print(f"\nProcessing {f.split('/')[-1]}...")
        
        # Sütunları bul
        yorum_col = None
        for col in df.columns:
            if col.lower() == 'yorum':
                yorum_col = col
                break
        
        cat_col = None
        for col in df.columns:
            if col.lower() in ['baskın', 'baskin', 'kategori']:
                cat_col = col
                break
                
        if yorum_col is None:
            print(f"Uyarı: {f} içerisinde yorum kolonu bulunamadı. Atlıyorum.")
            continue
            
        if cat_col is None:
            print(f"Uyarı: {f} içerisinde kategori/Baskın kolonu bulunamadı, veriler sıfırdan analiz edilip eklenecek.")
            cat_col = 'Kategori'
            df[cat_col] = 'Nötr'
            
        original_duyarsiz = df[df[cat_col].astype(str).str.upper() == 'DUYARSIZ'].shape[0]
        print(f"Önceki DUYARSIZ sayısı: {original_duyarsiz}")
        
        degisen = [0]
        def guncelle(row):
            mevcut = str(row[cat_col]).upper()
            if mevcut == 'DUYARSIZ' or mevcut == 'NÖTR':
                metin = str(row[yorum_col])
                k_n = kelime_say(metin)
                yeni = kategori_bul(metin, k_n).upper()
                if mevcut == 'DUYARSIZ' and yeni != 'DUYARSIZ':
                    degisen[0] += 1
                return yeni
            return row[cat_col]
            
        df[cat_col] = df.apply(guncelle, axis=1)
        
        new_duyarsiz = df[df[cat_col].astype(str).str.upper() == 'DUYARSIZ'].shape[0]
        new_sistem = df[df[cat_col].astype(str).str.upper() == 'SISTEM_ELESTIRISI'].shape[0]
        
        print(f"Sonraki DUYARSIZ sayısı: {new_duyarsiz}")
        print(f"Yeni SİSTEM_ELEŞTİRİSİ sayısı: {new_sistem}")
        print(f"Değiştirilen kayıt sayısı: {degisen[0]}")
        
        df.to_excel(f, index=False)
        print(f"Güncellendi ve kaydedildi: {f}")
        
    except Exception as e:
        print(f"HATA {f}: {e}")

