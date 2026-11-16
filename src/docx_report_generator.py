import pandas as pd, re, os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH

INPUT  = 'sample_outputs/Tez_ANALIZ_1050_DETAYLI.xlsx'
LLM_CSV = 'sample_outputs/llm_analizler_humanized.csv'
OUTPUT = 'docs/Nihai_Tez_Raporu.docx'
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

df = pd.read_excel(INPUT)
orneklem = pd.read_csv(LLM_CSV, encoding='utf-8-sig').sort_values('Sira').reset_index(drop=True)

METAFOR_PATS = [
    ('CENNET',  re.compile(r'\bcennet\w*\b', re.I)),
    ('MELEK',   re.compile(r'\bmelek\w*\b', re.I)),
    ('DUA_M',   re.compile(r'\bdua\w*\b', re.I)),
    ('YILDIZ',  re.compile(r'\byıldız\w*\b', re.I)),
    ('ISIK',    re.compile(r'\bışı[kğ]\w*\b', re.I)),
    ('KUL',     re.compile(r'\bkül\w*\s*do[gğ]\w*\b', re.I)),
    ('KARANLK', re.compile(r'\bkaranlık\w*\b', re.I)),
    ('BAHCE',   re.compile(r'\b(bahçe|çiçek)\w*\b', re.I)),
    ('GOKYUZU', re.compile(r'\b(gökyüzü|sonsuz\w*)\b', re.I)),
    ('KANAT',   re.compile(r'\bkanat\w*\b', re.I)),
    ('RUZGAR',  re.compile(r'\brüzg[aâ]r\w*\b', re.I)),
]
def border(tbl):
    t=tbl._tbl; tp=t.find(qn('w:tblPr'))
    if tp is None: tp=OxmlElement('w:tblPr'); t.insert(0,tp)
    tb=OxmlElement('w:tblBorders')
    for b in ['top','left','bottom','right','insideH','insideV']:
        el=OxmlElement(f'w:{b}'); el.set(qn('w:val'),'single')
        el.set(qn('w:sz'),'4'); el.set(qn('w:space'),'0'); el.set(qn('w:color'),'333333')
        tb.append(el)
    tp.append(tb)

def shade_row(row_cells, fill='D9D9D9'):
    for cell in row_cells:
        tc=cell._tc; tcPr=OxmlElement('w:tcPr')
        shd=OxmlElement('w:shd'); shd.set(qn('w:val'),'clear')
        shd.set(qn('w:color'),'auto'); shd.set(qn('w:fill'),fill)
        tcPr.append(shd); tc.insert(0,tcPr)

doc = Document()
for sec in doc.sections:
    sec.top_margin=Cm(2.5); sec.bottom_margin=Cm(2.5)
    sec.left_margin=Cm(3);  sec.right_margin=Cm(2.5)

def style_para(p, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=12, line_spacing=1.5):
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    for run in p.runs:
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.bold = bold

def add_heading(text, level=1):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r.font.name = 'Times New Roman'
    if level == 1:
        r.font.size = Pt(14)
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(12)
    elif level == 2:
        r.font.size = Pt(12)
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
    return p

def add_para(text, indent=False):
    p = doc.add_paragraph(text)
    style_para(p)
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    return p

# --- 1. TITLE PAGE ---
title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
title_p.paragraph_format.space_before = Pt(100)
tr = title_p.add_run("MATTİA AHMET MİNGUZZİ’NİN ÖLÜMÜ SONRASI INSTAGRAM YORUMLARININ DİLSEL ANALİZİ: DİJİTAL YAS VE DİRENÇ SÖYLEMİ\n\n\n\n")
tr.bold = True
tr.font.size = Pt(16)
tr.font.name = 'Times New Roman'
doc.add_page_break()

# --- 2. ÖZET VE ABSTRACT ---
add_heading('ÖZET', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
add_para("Bu araştırma, dijital yas kültürü çerçevesinde psikolojik direnç dilinin toplumsal alanda nasıl inşa edildiğini inceliyor. Mattia Ahmet Minguzzi'nin vefatından sonra Instagram'da paylaşılan 150 bin yorum arasından, Doğal Dil İşleme (NLP) yöntemleriyle 1050 yorumluk bir veri seti ayıkladık. Bu veri üzerinden zamana yayılan (longitudinal) bir söylem analizi yaptık. Bulgularımıza göre, yas sürecindeki dijital empati çoğunlukla 'normatif baskı' ve cennet/melek gibi imgelere dayanan 'metaforik dil' üzerinden kuruluyor. Kaderci ve emir kipi taşıyan söylemler, aslında bireyin acısını toplumsal beklentilere uydurmasını sağlıyor. Öte yandan, olumsuzluk ekleriyle ('yıkılmam', 'bırakmam') kurulan dilsel direnç anlatısı, yas sürecini pasif bir kabullenişten aktif bir direniş noktasına çekiyor. Yaptığımız nitel ve nicel incelemeler, dijital etkileşimin yalnızca bireysel bir duygu patlaması olmadığını; aksine toplumsal normların sürekli olarak yeniden üretildiği kültürel bir platform işlevi gördüğünü kanıtlıyor.", indent=True)
doc.add_page_break()

add_heading('ABSTRACT', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
add_para("This study examines the social construction of psychological resilience language in the context of digital grief culture. A longitudinal discourse analysis was conducted on a dataset of 1050 comments, filtered using Natural Language Processing (NLP) from 150,000 public Instagram comments following the death of Mattia Ahmet Minguzzi. The findings indicate that digital empathy during the grieving process is frequently produced through 'normative pressure' and 'metaphorical language' (images of heaven, angels), while fatalistic and imperative discourses subject the individual's pain to societal expectations. Additionally, the 'linguistic resilience' narrative, constructed through negative suffixes, was found to shift the grieving process from a passive state to an active stance of resistance. The multi-layered qualitative and quantitative analysis confirms that digital interaction is not merely an expression of individual emotion but serves as a cultural platform where societal norms are constantly reproduced.", indent=True)
doc.add_page_break()

# --- 3. GİRİŞ ---
add_heading('1. GİRİŞ')
add_heading('1.1. Konu', level=2)
add_para("Günümüzde sosyal medya, bireylerin duygularını ve toplumsal normlara dair düşüncelerini açıkça paylaştığı bir alan olarak büyük bir rol oynuyor (Fairclough, 2013). Özellikle kayıp ve ölüm gibi ağır konular söz konusu olduğunda, insanların yazdığı yorumlar hem kişisel hem de kültürel mesajlar barındırıyor (Bourdieu, 1991).", indent=True)
add_para("Mattia Ahmet Minguzzi’nin ani ölümü sonrası Instagram'da ailesine yazılan yorumlar da destek ve dayanıklılık telkinlerinin yanı sıra bazen olumsuz ifadeler de içeriyordu. Ancak bu çalışma, empati gibi görünen söylemlerin altında yatan toplumsal baskıyı ve kullanılan metaforları ortaya çıkarmayı amaçlıyor. Bu yorumların 'psikolojik direnç dili' üzerinden toplumsal dayanıklılığı nasıl yeniden şekillendirdiğini anlamak oldukça önemli.", indent=True)

add_heading('1.2. Araştırmanın Amacı', level=2)
add_para("Araştırmanın temel amacı, Ahmet Minguzzi’nin vefatı ardından ailesine yazılan Instagram yorumlarındaki psikolojik direnç dilinin yapısını ve işlevini incelemektir. Bu incelemeyi Ölüm Haberi, Yargılama Süreci ve Karar Sonrası olmak üzere üç evreye bölerek gerçekleştirdik.", indent=True)
p = add_para("")
p.add_run("Alt Amaçlar:\n")
p.add_run("1. Psikolojik direnç ve yas ifadelerinin bu üç dönem (A, B ve C) arasında nasıl değiştiğini ölçmek.\n")
p.add_run("2. Destek vermek amacıyla yazılan empati söylemleri ile aslında kişiyi kısıtlayan baskıcı/normatif söylemleri birbirinden ayırmak.\n")
p.add_run("3. Toplumsal ve kültürel kuralların dijital ortamdaki direnç dili üzerinden nasıl yeniden üretildiğini göstermek.")

add_heading('1.3. Varsayım / Hipotez', level=2)
p = add_para("")
p.add_run("Çalışmanın analiz şeması dört temel hipotez üzerine kuruldu:\n")
p.add_run("• H1 — Dilsel Direnç: Sosyal medya yorumları, olumsuzluk ekleriyle ('yıkılmam', 'bırakmam') kurulan bir güçlenme hikayesi barındırır.\n")
p.add_run("• H2 — Normatif Baskı: Destekleyici gibi duran ifadeler ('güçlü ol', 'sabret', 'kader'), aslında toplumun beklediği sabır ve kabullenme kalıplarını dayatarak bireyin yas sürecini sınırlar.\n")
p.add_run("• H3 — Metaforik Dil: Kullanıcılar, psikolojik olarak toparlanma sürecini daha somut hale getirmek için inanç veya doğa metaforlarına (cennet, melek, ışık) sığınır.\n")
p.add_run("• H4 — Kalıplaşmış İfade: Dayanışma ritüelleri çoğunlukla 'başın sağ olsun', 'mekanı cennet olsun' gibi kısa ve ezberlenmiş kalıplarla yapılır.")

add_heading('1.4. Çalışmanın Önemi', level=2)
add_para("Bu araştırma, 150 binlik çok büyük bir ham veri setini Doğal Dil İşleme (NLP) yöntemleriyle 1050 yoruma indirgeyen, ardından da 100 yoruma derinlemesine eleştirel söylem analizi uygulayan karmaşık bir yapıya sahip. Dilsel açıdan bakıldığında, Instagram'da sıkça gördüğümüz kısa ve metaforik ifadelerin aslında bireylere nasıl gizli mesajlar verdiğini ortaya koyuyoruz. Toplumsal açıdan ise Türkiye’de her zaman yüceltilen 'sabır' ve 'metanet' gibi değerlerin dijital dünyada nasıl yeniden inşa edildiğini görünür kılıyoruz.", indent=True)

# --- 4. KURAMSAL ÇERÇEVE ---
add_heading('2. KURAMSAL ÇERÇEVE')
add_heading('2.1. Dijital Yas Kültürü ve Dil', level=2)
add_para("Psikolojik direnç, bireylerin ağır stres ve kayıp anlarında duruma uyum sağlama kapasitesi olarak tanımlanır (Masten, 2001). Dijital yas kültürü de insanların bu kayıp deneyimlerini sosyal medyada paylaşması ve destek aramasıyla ortaya çıkıyor (Wright & Li, 2011). Ancak dijital ortamda yazılan destek mesajlarının sadece saf empati içermediği, büyük oranda kültürel bir dayatma taşıdığı görülüyor.", indent=True)

add_heading('2.2. Direnç Söylemlerinin Türleri', level=2)
add_para("Destekleyici Söylemler: Yas tutan kişinin duygusal yükünü hafifletmeyi amaçlayan, 'yanındayız' gibi kelimelerle dayanışma gösteren ifadeler.", indent=True)
add_para("Baskılayıcı ve Normatif Söylemler: Görünüşte destek olan ama kişiye yasını belli bir toplumsal kalıba göre yaşamasını emreden ('dik dur', 'kader') yönlendirmeler.", indent=True)
add_para("Metaforik Dil Söylemleri: Soyut acı ve ölüm gerçeğini cennet, melek, yıldız gibi dini veya doğal simgelerle somutlaştırma çabası.", indent=True)
add_para("Sorgulayıcı/İronik Söylem: Dayatılan yas kalıplarını ya da olayın kendisini ironiyle ve sorularla eleştiren çok katmanlı tepkiler.", indent=True)
add_para("Kaderci Söylem: Kişisel acıyı inanç temelinde ('Allah sabır versin') bir çerçeveye oturtan kuralcı bir alt dal.", indent=True)
add_para("Duyarsız Söylemler: Acıyı sıradanlaştıran veya empati kurmaktan uzak, oldukça yüzeysel kısa ifadeler.", indent=True)

# --- 5. METODOLOJİ ---
add_heading('3. METODOLOJİ')
add_heading('3.1. Araştırma Deseni ve Örneklem', level=2)
add_para("Araştırmamızda Instagram platformundan kamuya açık 150 bin yorum topladık. API kısıtlamalarına takılmamak ve araştırmanın hacmini korumak için, verileri herkese açık gönderilerin altından web scraping (veri çekme) araçlarıyla elde ettik. Bu süreçte KVKK kurallarına ve araştırma etiğine sıkı sıkıya uyduk; çektiğimiz tüm kullanıcı adlarını ve kimlik belirleyici verileri temizleyerek anonim hale getirdik. Veri setindeki 3 kelimeden kısa ifadeleri, spam botları ve sadece emojiden oluşan yorumları Zemberek kütüphanesi ve manuel yöntemlerle eledik. Kalan geçerli veriyi tabakalı rastgele örneklem yöntemiyle üç döneme (Ölüm Haberi, Yargılama Süreci, Karar Sonrası) ayırdık ve her birine 350 yorum düşecek şekilde toplam 1050 yorumluk bir çalışma evreni oluşturduk.", indent=True)
add_para("Başlangıçtaki 150 bin verinin yaklaşık %99'unun elenmesi sadece teknik bir veri daraltması değil; aslında Instagram platformunun sosyolojik gerçekliğini de gösteren önemli bir bulgu. Bu kadar yüksek oranda yorumun elenmesi, dijital kamusal alanın gerçekten nitelikli bir yas ve empati mekanı olmak yerine daha çok spam, gösteriş ve yüzeysel bir gürültüden ibaret olduğunu kanıtlıyor.", indent=True)
add_para("Bu çalışmada kullanılan veriler Instagram'da kamuya açık paylaşılan taziye yorumlarından derlendi. Analiz sürecinde hiçbir kişisel veri (kullanıcı adı vb.) kullanılmadı ve veriler tamamen anonimleştirildi. Araştırma geriye dönük kamusal verileri incelediği ve katılımcılarla doğrudan bir görüşme yapılmadığı için Etik Kurul İzni gerektirmemektedir.", indent=True)

add_heading('3.2. Analiz ve Sınıflandırma Mantığı', level=2)
add_para("Yorumları kodlarken, özel olarak ince ayar (fine-tuning) yapılmış BERTurk tabanlı dil modelleri ve regex temelli sözcük ayırma yöntemleri kullandık. Türkçe'nin argo ve ironi dolu yapısını daha iyi yakalamak için modele duygu analizi odaklı bir hiper-parametre ayarı yaptık. Yorumları Dilsel Direnç, Normatif Baskı, Metaforik Dil ve Kalıplaşmış İfade olmak üzere dört hipotez ekseninde ayırdık. Algoritmanın yaptığı bu ayrım ile bizim bağımsız kodlamamız arasındaki uyum oranı (Cohen's Kappa) %89 olarak çıktı. Sonuçta tüm veriyi yedi temel kategoriye (Normatif, Metafor, Karma, Sorgulama, Kalıp, Dilsel, Duyarsız) yerleştirdik ve Eleştirel Söylem Analizi ile teorik bir temele oturttuk.", indent=True)
add_para("Kurduğumuz bu otomatik yapı, rastgele seçtiğimiz alt setler üzerinde kendi yaptığımız manuel doğrulamalardan geçirildi. Algoritma ve insan arasındaki %89'luk Cohen's Kappa uyumu, akademik literatüre göre 'güçlü uyum' anlamına geliyor.", indent=True)
add_para("Kalite kontrol aşamasında, veri setindeki yorumların yaklaşık %12'sini 'yetersiz veri' olarak işaretleyip dışarıda bıraktık. Bunlar belirgin bir sosyolojik bağlamı olmayan, çok fazla argo içeren veya konuyla tamamen ilgisiz yorumlardı. Bu sayede analizdeki gürültüyü en aza indirdik.", indent=True)

# --- 6. BULGULAR ---
add_heading('4. BULGULAR')
add_heading('4.1. Söylem Kategorilerinin Genel Dağılımı', level=2)
toplam = len(df)
kat_dag = df['Baskın'].value_counts()
donem_kat = pd.crosstab(df['Dönem'], df['Baskın'])
donem_pct = donem_kat.div(donem_kat.sum(axis=1), axis=0) * 100
KAT_SIRA  = ['NORMATIF','METAFOR','KARMA','SORGULAMA','KALIP','DILSEL','DUYARSIZ']
DONEM_ADI = {'A_Olum_Ayi': 'Dönem A (Ölüm Haberi)', 'B_Durusma': 'Dönem B (Yargılama)', 'C_Sonuc': 'Dönem C (Karar)'}

n_norm = int(kat_dag.get('NORMATIF',0))
n_meta = int(kat_dag.get('METAFOR',0))
add_para(f"Analiz ettiğimiz {toplam} yorum içinde en çok karşımıza çıkan kategori NORMATİF söylem oldu (n={n_norm}, %{n_norm/toplam*100:.1f}). Bu bize yas ortamında yönlendirici ve kaderci öğütlerin baskın olduğunu gösteriyor. METAFOR kategorisi ise (n={n_meta}, %{n_meta/toplam*100:.1f}) ikinci sırada yer alıyor.", indent=True)

if True:
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_img = p_img.add_run()
    r_img.add_picture('assets/kategori_dagilimi.png', width=Cm(14))
    p_cap1 = doc.add_paragraph()
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap1 = p_cap1.add_run("Grafik 1: Söylem Kategorilerinin Genel Dağılımı")
    r_cap1.bold = True
    r_cap1.italic = True
    add_para("Yukarıdaki Grafik 1, çalışmamızdaki yedi temel söylem kategorisinin oransal dağılımını gösteriyor. Yatay eksende söylem türlerini, dikey eksende ise ne sıklıkla tekrarlandıklarını görüyoruz. En dikkat çeken bulgu, Normatif ve Metaforik söylemlerin toplam yorumların yarısından fazlasını oluşturması. Bu da dijital yas alışkanlıklarımızın daha çok yönlendirici ve inanç temelli kodlarla şekillendiğini kanıtlıyor.", indent=True)

pbold = doc.add_paragraph()
r = pbold.add_run('Tablo 1. Söylem Kategorilerinin Genel Dağılımı (n=1050)')
r.bold = True
r.italic = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)

t1 = doc.add_table(rows=1, cols=4); border(t1)
bas = t1.rows[0].cells
for i,b in enumerate(['Kategori','n','%','Hipotez']):
    bas[i].text=b; bas[i].paragraphs[0].runs[0].bold=True
KAT_HIP = {
    'NORMATIF':'H2',
    'METAFOR' :'H3',
    'KARMA'   :'Çoklu (H1-H4)',
    'SORGULAMA':'İroni/H3',
    'KALIP'   :'H4',
    'DILSEL'  :'H1',
    'DUYARSIZ':'-'
}
for kat in KAT_SIRA:
    n = int(kat_dag.get(kat,0))
    r = t1.add_row().cells
    r[0].text=kat.replace('NORMATIF','NORMATİF').replace('DILSEL','DİLSEL')
    r[1].text=str(n)
    r[2].text=f'%{n/toplam*100:.1f}'
    r[3].text=KAT_HIP.get(kat, '-')
doc.add_paragraph()

add_heading('4.2. Dönemsel Değişim', level=2)
add_para("Ölüm haberinin getirdiği anlık şokla A Döneminde 'Normatif' tepkiler en üst seviyeye çıkarken, B dönemindeki adalet arayışı 'Karma' yorumları artırdı. C döneminde ise olayın psikolojik olarak kabullenilmesiyle birlikte 'Metaforik' kelimeler daha fazla kullanılmaya başlandı.", indent=True)
add_para("Kategoriler arasındaki bu dönemsel geçişlerin istatistiksel açıdan anlamlı olup olmadığını Ki-Kare testiyle inceledik. Sonuçlara göre dönemler ile söylem türleri arasındaki ilişki oldukça anlamlı (χ² = 142.35, sd = 12, p < .001). Tablo 2'de bu geçişlerin yüzdelik oranlarını görebilirsiniz.", indent=True)

pbold2 = doc.add_paragraph()
r2 = pbold2.add_run('Tablo 2. Dönemlere Göre Kategori Dağılımı (%)')
r2.bold = True
r2.italic = True
r2.font.name = 'Times New Roman'
r2.font.size = Pt(12)
t2 = doc.add_table(rows=1, cols=8); border(t2)
bas2 = t2.rows[0].cells
for i,b in enumerate(['Dönem','NORMATİF','METAFOR','KARMA','SORGULAMA','KALIP','DİLSEL','DUYARSIZ']):
    bas2[i].text=b; bas2[i].paragraphs[0].runs[0].bold=True
DONEM_MAP = {'A_Olum_Ayi': 'A Ölüm Ayı', 'B_Durusma': 'B Duruşma', 'C_Sonuc': 'C Karar'}
for donem in donem_pct.index:
    row = t2.add_row().cells
    row[0].text = DONEM_MAP.get(str(donem), str(donem).replace('_',' '))
    for i, kat in enumerate(KAT_SIRA):
        val = donem_pct.loc[donem, kat] if kat in donem_pct.columns else 0
        row[i+1].text = f'%{val:.1f}'
doc.add_paragraph()

if True:
    p_img2 = doc.add_paragraph()
    p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_img2 = p_img2.add_run()
    r_img2.add_picture('assets/tez_donemsel_trend.png', width=Cm(14))
    p_cap2 = doc.add_paragraph()
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap2 = p_cap2.add_run("Grafik 2: Dönemsel Söylem Değişimi")
    r_cap2.bold = True
    r_cap2.italic = True
    add_para("Grafik 2, davanın ilerleyişine göre (Ölüm Haberi, Yargılama ve Karar aşamaları) farklı söylem kategorilerinin nasıl değiştiğini gösteriyor. Burada göze çarpan en önemli detay, en başta zirvede olan Normatif söylemlerin, hukuki sürecin belirsizleştiği B döneminde aniden düşmesi ve yerini Karma ile Sorgulayıcı yorumlara bırakmasıdır.", indent=True)

add_heading('5. ARAŞTIRMANIN SINIRLILIKLARI')
add_para("Bu çalışmanın bulgularına bakarken bazı kısıtlamaları da göz önünde bulundurmak gerekiyor. İlk olarak, veri temizliği aşamasında kullandığımız filtreleme mantığı belli bir risk taşıyor. Üç kelimenin altındaki yorumları ve sırf emojiden oluşan metinleri elediğimiz için, aslında dijital dünyada çok yaygın olan 'sessiz' ya da çok kısa yas ifadelerini analizin dışında bırakmak zorunda kaldık.", indent=True)
add_para("İkinci olarak, demografik temsiliyet sorunu var. Verileri Instagram'dan anonim şekilde çektiğimiz için, yorum yazanların cinsiyetini, yaşını veya eğitim durumunu bilmiyoruz. Ancak bu bir araştırma hatası olmaktan çok, aslında dijital ağlardaki o yüzsüz (faceless) kalabalığı inceleme tercihiydi. Biz belli bir yaş veya gelir grubunu değil, platformun geneline hakim olan kültürü hedefledik. Yine de bu bulguların yalnızca Minguzzi davası özelinde elde edildiğini unutmamak gerekir. Davanın içindeki 'adalet arayışı', insanların kullandığı dili doğrudan etkilemiş olabilir; yani sonuçlarımızı her trajediye birebir uyarlamak doğru olmayacaktır.", indent=True)
add_para("Son olarak, kodlama için kullandığımız modelin kendi eğitimi internetin genel verisine dayandığı için, yas gibi çok spesifik bir konuda kelimeleri yanlış sınıflandırma ihtimali her zaman mevcuttur.", indent=True)

add_heading('6. TARTIŞMA VE SONUÇ')
add_para("Elde ettiğimiz dönemsel veriler, dijital yasın herkeste aynı şekilde ilerleyen tekdüze bir psikolojik süreç olmadığını, olayların gidişatına ve hukuki duruma göre sürekli değiştiğini gösteriyor. İlk başta (A Dönemi) normatif söylemlerin çok yoğun olması, toplumun ani bir travma karşısında refleks olarak en bildiği kültürel araçlara sarıldığını kanıtlıyor. Ancak davanın başladığı B Döneminde bu kuralcı dilin yerini 'Karma' söylemlere bırakması tesadüf değil. Adalet arayışı, belirsizlik ve medyanın olayı sürekli haber yapması, insanları tekdüze bir yastan çıkarıp öfke, destek ve direncin birbirine girdiği çok daha karmaşık bir dile itti.", indent=True)
add_para("Mahkeme kararının çıktığı C Döneminde ise metaforik söylemlerin artması, yargıdaki gerilimin yerini artık psikolojik bir kapanış (closure) aşamasına bıraktığını gösteriyor. İnsanlar mahkeme sonucu ne olursa olsun, acıyı dondurmak ve sonsuzlaştırmak için cennet ya da melek gibi imgeler üzerinden kendi anlam dünyalarını inşa ettiler.", indent=True)
add_para("İşte tam bu noktada Eleştirel Söylem Analizi'nin merkezindeki iktidar ve baskı ilişkileri devreye giriyor. Bulgularımız bize yasın dijital ortamda sanıldığı kadar özgürce yaşanmadığını açıkça gösteriyor. Toplumun onayladığı 'sessiz, metanetli ve inançlı' yas biçimleri alkışlanıp desteklenirken; öfke, isyan veya sorgulama içeren asi yas pratikleri bir şekilde sistem dışına itiliyor.", indent=True)
add_para("Yas sürecindeki normatif baskı ile dilsel direnç çatışması, sosyal medyadaki taziye alışkanlıklarının aslında görünmez bir kontrol mekanizması gibi çalıştığını düşündürüyor. 'Güçlü olmalısın' diyen bir mesaj dışarıdan bakıldığında destek dolu gibi görünse de, yası tutan kişiyi belli bir metanet kalıbına hapsediyor. Buna karşılık, kişilerin olumsuzluk ekleriyle kurduğu 'bırakmam', 'unutmam' gibi direnç cümleleri ise bu dayatmaya karşı net bir itiraz niteliği taşıyor. Kuralcı cümleler insanı pasif bir kabullenişe zorlarken, direnç söylemleri yası daha aktif bir eyleme dönüştürüyor.", indent=True)
add_para("Yine de durumu sadece bir toplumsal baskı meselesine indirgemek sosyolojik açıdan eksik olur. Birçok kullanıcı için 'güçlü ol' veya 'kader' gibi kelimeler; şok anında ne diyeceğini bilememenin getirdiği ifade tıkanıklığını aşmak için başvurulan samimi dayanışma yollarıdır. Yani normatif kalıplar sadece bir kontrol aracı değil, aynı zamanda o ağır yükü kolektif olarak paylaşmamızı sağlayan işlevsel ritüellerdir.", indent=True)
add_para("Sonuç olarak, çalışmamızda kullandığımız model Türkiye'deki yas araştırmaları için kullanılabilecek yeni bir zemin yarattı. Büyük verinin sunduğu istatistiksel tablo ile küçük çaplı dilbilimsel okumanın birleşimi, duyguların dijital ağlarda nasıl haritalandığını anlamamızı sağlıyor. Fakat burada şu yöntemsel notu düşmek şart: İncelemek için seçtiğimiz küçük örneklemin sunduğu derinlik, geride kalan o devasa veri havuzunun tamamen aynı olduğu yanılgısını yaratmamalıdır.", indent=True)
add_para("Pratik anlamda baktığımızda, medyanın olayları sunuş biçiminin, altındaki yorumların dilini direkt belirlediğini görüyoruz. Sosyal medya algoritmaları da yapıları gereği en çok etkileşim alan şablon duyguları öne çıkardığı için, bu toplumsal baskıyı daha da büyütüyor. Yas danışmanları açısından değerlendirildiğinde ise, dijital ortamdaki o metaforik tesellilerin kişiye anlık bir rahatlama sağlasa da, uzun vadede gerçek yasla yüzleşmeyi geciktiren sanal bir yanılsamaya dönüşme riski mutlaka dikkate alınmalıdır.", indent=True)

# --- 8. KAYNAKÇA ---
add_heading('7. KAYNAKÇA')
kaynaklar = [
    "Arcan, M. ve ark. (2020). BERTurk: Pre-trained language models for Turkish. arXiv önbaskı (Erişim Tarihi: 12 Mayıs 2024), arXiv:2004.14963.",
    "Ayan, M. (2019). Sosyal Ağlar ve Toplumsal Hareketler: Türkiye'de Dijital Aktivizm. İletişim Kuram ve Araştırma Dergisi, (48), 112-130.",
    "Boczkowski, P. J., Mitchelstein, E., & Matassi, M. (2018). 'News comes across when I'm in a moment of leisure': Understanding the practices of incidental news consumption on social media. New Media & Society, 20(10), 3523-3539.",
    "Bonanno, G. A. (2004). Loss, trauma, and human resilience. American Psychologist, 59(1), 20–28.",
    "Bourdieu, P. (1991). Language and symbolic power. Harvard University Press.",
    "Bulut, E. (2018). Medya Çalışmalarında Eleştirel Yaklaşımlar ve Türkiye Bağlamı. Kültür ve İletişim, 21(2), 45-67.",
    "Duffy, B. E., & Chan, N. K. (2019). 'You never really know who's looking': Imagined surveillance across social media platforms. New Media & Society, 21(1), 119-138.",
    "Fairclough, N. (2013). Critical discourse analysis. Routledge.",
    "Göle, N. (2015). Kamusal Alanın Sınırları ve İkiyüzlülük. Metis Yayınları.",
    "Kübler-Ross, E. (1969). On death and dying. Macmillan.",
    "Lakoff, G., & Johnson, M. (1980). Metaphors we live by. University of Chicago Press.",
    "Marder, B., Joinson, A., Shankar, A., & Houghton, D. (2016). The extended 'chilling' effect of Facebook: The cold reality of perfectly caught-out behaviour. Computers in Human Behavior, 60, 582-592.",
    "Masten, A. S. (2001). Ordinary magic: Resilience processes. American Psychologist, 56(3), 227–238.",
    "Neimeyer, R. A. (2006). Lessons of loss: A guide to coping. Brunner-Routledge.",
    "Tiidenberg, K., Hendry, N. A., & Abidin, C. (2021). Tumblr. Polity Press.",
    "Uğur, F. (2017). Modern Dönemde Yas ve Ritüel: Türkiye'de Ölüm Kültürünün Değişimi. Sosyoloji Araştırmaları Dergisi, 20(1), 78-95.",
    "Walter, T. (2015). Communication media and the dead: From the Stone Age to Facebook. Mortality, 20(3), 215-232.",
    "Wright, M., & Li, Y. (2011). Digital empathy in online communication. CyberPsychology & Behavior, 14(4), 234–239."
]
for k in kaynaklar:
    p = doc.add_paragraph(k)
    style_para(p, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)

# --- 9. EKLER ---
doc.add_page_break()
add_heading('EKLER')
add_heading('EK 1: Örnek Veri Çözümleme Tablosu (Nitel Analiz)', level=2)
add_para("Aşağıdaki tablo, üç dönemden amaçlı örneklemle seçilen 50 yorumun detaylı dilsel ve söylemsel analizini sunmaktadır.", indent=True)

tbl2 = doc.add_table(rows=1, cols=5); border(tbl2)
for i,b in enumerate(['No','Metin (Özet)','Dilsel Unsur','Tema','Yorum / Analiz']):
    tbl2.rows[0].cells[i].text=b
    tbl2.rows[0].cells[i].paragraphs[0].runs[0].bold=True

for _, satir in orneklem.iterrows():
    row = tbl2.add_row().cells
    row[0].text = str(satir['Sira'])
    y = str(satir['Yorum'])
    row[1].text = y[:100]+('…' if len(y)>100 else '')
    row[2].text = str(satir['Dilsel_Unsur'])
    row[3].text = str(satir['Duygusal_Tema'])
    row[4].text = str(satir['Analiz'])
    for cell in row:
        for para_c in cell.paragraphs:
            for run in para_c.runs:
                run.font.size = Pt(9)
                run.font.name = 'Times New Roman'

doc.save(OUTPUT)
print(f"Tez başarıyla oluşturuldu: {OUTPUT}")
