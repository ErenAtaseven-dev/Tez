import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

def stage1_isolation(file_path):
    df = pd.read_excel(file_path)
    puan_col = [c for c in df.columns if 'puan' in c.lower()][0]
    h_cols = ['H1', 'H2', 'H3', 'H4']
    for h in h_cols:
        if h in df.columns:
            df[h] = df[h].astype(int)
    return df, puan_col, h_cols

def stage2_correlation(df, puan_col, h_cols):
    cols_to_correlate = [puan_col] + [h for h in h_cols if h in df.columns]
    
    pearson_matrix = df[cols_to_correlate].corr(method='pearson')
    spearman_matrix = df[cols_to_correlate].corr(method='spearman')
    
    print("--- PEARSON KORELASYON MATRİSİ ---")
    print(pearson_matrix.round(3))
    
    print("\n--- SPEARMAN KORELASYON MATRİSİ ---")
    print(spearman_matrix.round(3))
    
    return pearson_matrix, spearman_matrix

def stage3_and_4(df, puan_col):
    zirve = df[df[puan_col] >= 7]
    orta = df[(df[puan_col] >= 5) & (df[puan_col] <= 6)]
    dusuk = df[df[puan_col] <= 4]
    
    print("\n--- AŞAMA 3 & 4: ZİRVE SEGMENTASYON VE DÜŞÜK PUAN SAĞLAMASI ---")
    print(f"Zirve Örneklem (7-9 Puan): {len(zirve)} yorum")
    print(f"-> H2 (Umut/Kabullenme) Varlığı: %{zirve['H2'].mean()*100:.1f}")
    print(f"-> H3 (Metaforik Dil) Varlığı:   %{zirve['H3'].mean()*100:.1f}")
    
    return zirve, orta, dusuk

def stage5_visualization(df, pearson_matrix, spearman_matrix, zirve, orta, dusuk):
    print("\nAşama 5: Görselleştirmeler kaydediliyor...")
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(pearson_matrix, annot=True, cmap='coolwarm', fmt=".2f", vmin=-1, vmax=1)
    plt.title('Hipotezler ve Altın Puan Bağıntısı (Pearson)')
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, 'tez_pearson_heatmap.png'), dpi=300)
    plt.close()
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(spearman_matrix, annot=True, cmap='viridis', fmt=".2f", vmin=-1, vmax=1)
    plt.title('Hipotezler ve Altın Puan Bağıntısı (Spearman - Sıralı Veri)')
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, 'tez_spearman_heatmap.png'), dpi=300)
    plt.close()
    
    segments = ['Düşük Puan\n(0-4)', 'Orta Puan\n(5-6)', 'Zirve Puan\n(7-9)']
    h2_rates = [dusuk['H2'].mean()*100, orta['H2'].mean()*100, zirve['H2'].mean()*100]
    h3_rates = [dusuk['H3'].mean()*100, orta['H3'].mean()*100, zirve['H3'].mean()*100]
    
    x = range(len(segments))
    width = 0.35
    
    plt.figure(figsize=(10, 6))
    plt.bar([i - width/2 for i in x], h2_rates, width, label='H2: Umut / Kabullenme', color='skyblue')
    plt.bar([i + width/2 for i in x], h3_rates, width, label='H3: Metaforik Dil', color='salmon')
    
    plt.ylabel('Bulunma Oranı (%)')
    plt.title('Puan Segmentasyonuna Göre İyileşme (Resilience) Mekanizmaları')
    plt.xticks(x, segments)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(ASSETS_DIR, 'tez_segment_dagilimi.png'), dpi=300)
    plt.close()
    
    print("-> tez_pearson_heatmap.png kaydedildi.")
    print("-> tez_spearman_heatmap.png kaydedildi.")
    print("-> tez_segment_dagilimi.png kaydedildi.")

if __name__ == "__main__":
    file_path = os.path.join(BASE_DIR, 'sample_outputs', 'Tez_ANALIZ_1050_DETAYLI.xlsx')
    df, puan_col, h_cols = stage1_isolation(file_path)
    pearson_matrix, spearman_matrix = stage2_correlation(df, puan_col, h_cols)
    zirve, orta, dusuk = stage3_and_4(df, puan_col)
    stage5_visualization(df, pearson_matrix, spearman_matrix, zirve, orta, dusuk)
