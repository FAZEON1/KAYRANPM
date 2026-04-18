import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stok_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_connection()
    c = conn.cursor()

    # Ana ürün kataloğu (bizim stoğumuz)
    c.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            sku TEXT PRIMARY KEY,
            urun_adi TEXT NOT NULL,
            kategori TEXT,
            marka TEXT,
            satis_fiyati REAL,
            alis_fiyati REAL,
            hedef_kar_marji REAL,
            ozellikler TEXT,
            ilk_giris_tarihi TEXT,
            bizim_stok INTEGER DEFAULT 0,
            trendyol_stok INTEGER DEFAULT 0,
            guncelleme_tarihi TEXT
        )
    """)
    # Eski tablolarda eksik kolonları ekle (migration)
    for kolon, tip in [("alis_fiyati","REAL"), ("hedef_kar_marji","REAL"), ("satis_fiyati","REAL")]:
        try:
            c.execute(f"ALTER TABLE urunler ADD COLUMN {kolon} {tip}")
        except:
            pass

    # Firma stokları ve satışları (haftalık yüklenen)
    c.execute("""
        CREATE TABLE IF NOT EXISTS firma_stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma TEXT NOT NULL,
            sku TEXT NOT NULL,
            urun_adi TEXT,
            stok_miktari INTEGER DEFAULT 0,
            haftalik_satis INTEGER DEFAULT 0,
            yukleme_tarihi TEXT,
            UNIQUE(firma, sku, yukleme_tarihi)
        )
    """)

    # Yoldaki ürünler
    c.execute("""
        CREATE TABLE IF NOT EXISTS yoldaki_urunler (
            sku TEXT PRIMARY KEY,
            urun_adi TEXT,
            yoldaki_miktar INTEGER DEFAULT 0,
            tahmini_varis_tarihi TEXT,
            yoldaki_tedarikci TEXT,
            yukleme_tarihi TEXT
        )
    """)
    try:
        c.execute("ALTER TABLE yoldaki_urunler ADD COLUMN yoldaki_tedarikci TEXT")
    except:
        pass

    # Satın alma geçmişi
    c.execute("""
        CREATE TABLE IF NOT EXISTS satin_alma_gecmisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            urun_adi TEXT,
            tedarikci TEXT,
            satin_alma_tarihi TEXT,
            adet INTEGER DEFAULT 0,
            alis_fiyati REAL DEFAULT 0,
            maliyet_yuzdesi REAL DEFAULT 0,
            toplam_maliyet REAL DEFAULT 0,
            notlar TEXT,
            kayit_tarihi TEXT
        )
    """)
    # Eski tablolara eksik kolonları ekle
    for kolon, tip in [("alis_fiyati","REAL"), ("maliyet_yuzdesi","REAL")]:
        try:
            c.execute(f"ALTER TABLE satin_alma_gecmisi ADD COLUMN {kolon} {tip}")
        except:
            pass

    # Stok yaşı takibi (ilk görüldüğü tarih)
    c.execute("""
        CREATE TABLE IF NOT EXISTS stok_yas (
            sku TEXT PRIMARY KEY,
            ilk_gorulen_tarih TEXT NOT NULL
        )
    """)

    # Satın alma geçmişi
    c.execute("""
        CREATE TABLE IF NOT EXISTS satin_alma_gecmisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            urun_adi TEXT,
            tedarikci TEXT,
            satin_alma_tarihi TEXT,
            adet INTEGER DEFAULT 0,
            birim_alis_fiyati REAL DEFAULT 0,
            toplam_maliyet REAL DEFAULT 0,
            birim_maliyet REAL DEFAULT 0,
            notlar TEXT,
            kayit_tarihi TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS siparis_onerileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma TEXT NOT NULL,
            sku TEXT NOT NULL,
            urun_adi TEXT,
            oneri_miktari INTEGER,
            durum TEXT DEFAULT 'beklemede',
            olusturma_tarihi TEXT,
            onay_tarihi TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def upsert_urun(sku, urun_adi, kategori="", marka="", satis_fiyati=0.0, alis_fiyati=0.0, hedef_kar_marji=0.0, ozellikler="", bizim_stok=0, trendyol_stok=0):
    conn = get_connection()
    c = conn.cursor()
    bugun = get_today()
    c.execute("SELECT ilk_giris_tarihi FROM urunler WHERE sku=?", (sku,))
    row = c.fetchone()
    ilk_tarih = row["ilk_giris_tarihi"] if row and row["ilk_giris_tarihi"] else bugun

    c.execute("""
        INSERT INTO urunler (sku, urun_adi, kategori, marka, satis_fiyati, alis_fiyati, hedef_kar_marji, ozellikler, ilk_giris_tarihi, bizim_stok, trendyol_stok, guncelleme_tarihi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            urun_adi=excluded.urun_adi,
            kategori=excluded.kategori,
            marka=excluded.marka,
            satis_fiyati=excluded.satis_fiyati,
            alis_fiyati=excluded.alis_fiyati,
            hedef_kar_marji=excluded.hedef_kar_marji,
            ozellikler=excluded.ozellikler,
            bizim_stok=excluded.bizim_stok,
            trendyol_stok=excluded.trendyol_stok,
            guncelleme_tarihi=excluded.guncelleme_tarihi
    """, (sku, urun_adi, kategori, marka, satis_fiyati, alis_fiyati, hedef_kar_marji, ozellikler, ilk_tarih, bizim_stok, trendyol_stok, bugun))

    c.execute("INSERT OR IGNORE INTO stok_yas (sku, ilk_gorulen_tarih) VALUES (?, ?)", (sku, bugun))
    conn.commit()
    conn.close()

def upsert_firma_stok(firma, sku, urun_adi, stok_miktari, haftalik_satis):
    conn = get_connection()
    c = conn.cursor()
    bugun = get_today()
    c.execute("""
        INSERT INTO firma_stok (firma, sku, urun_adi, stok_miktari, haftalik_satis, yukleme_tarihi)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(firma, sku, yukleme_tarihi) DO UPDATE SET
            stok_miktari=excluded.stok_miktari,
            haftalik_satis=excluded.haftalik_satis,
            urun_adi=excluded.urun_adi
    """, (firma, sku, urun_adi, stok_miktari, haftalik_satis, bugun))
    conn.commit()
    conn.close()

def get_all_dashboard_data():
    """Dashboard için tüm verileri hesaplayarak getirir"""
    conn = get_connection()
    c = conn.cursor()

    # Tüm ürünler
    c.execute("SELECT * FROM urunler ORDER BY urun_adi")
    urunler = [dict(r) for r in c.fetchall()]

    # Tüm firma stokları (son yükleme tarihi)
    firma_listesi = ["ITOPYA", "HB", "VATAN", "MONDAY", "KANAL", "DIGER"]
    firma_data = {}
    for firma in firma_listesi:
        c.execute("""
            SELECT fs.* FROM firma_stok fs
            WHERE fs.firma = ? AND fs.yukleme_tarihi = (
                SELECT MAX(yukleme_tarihi) FROM firma_stok WHERE firma = ?
            )
        """, (firma, firma))
        rows = c.fetchall()
        firma_data[firma] = {r["sku"]: dict(r) for r in rows}

    # Stok yaşları
    c.execute("SELECT * FROM stok_yas")
    stok_yaslar = {r["sku"]: r["ilk_gorulen_tarih"] for r in c.fetchall()}

    conn.close()
    return urunler, firma_data, stok_yaslar

def get_siparis_onerileri(durum=None):
    conn = get_connection()
    c = conn.cursor()
    if durum:
        c.execute("SELECT * FROM siparis_onerileri WHERE durum=? ORDER BY olusturma_tarihi DESC", (durum,))
    else:
        c.execute("SELECT * FROM siparis_onerileri ORDER BY olusturma_tarihi DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def ekle_siparis_onerisi(firma, sku, urun_adi, oneri_miktari):
    conn = get_connection()
    c = conn.cursor()
    bugun = get_today()
    c.execute("""
        INSERT INTO siparis_onerileri (firma, sku, urun_adi, oneri_miktari, durum, olusturma_tarihi)
        VALUES (?, ?, ?, ?, 'beklemede', ?)
    """, (firma, sku, urun_adi, oneri_miktari, bugun))
    conn.commit()
    conn.close()

def onayla_siparis(siparis_id):
    conn = get_connection()
    c = conn.cursor()
    bugun = get_today()
    c.execute("UPDATE siparis_onerileri SET durum='onaylandi', onay_tarihi=? WHERE id=?", (bugun, siparis_id))
    conn.commit()
    conn.close()

def reddet_siparis(siparis_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE siparis_onerileri SET durum='reddedildi' WHERE id=?", (siparis_id,))
    conn.commit()
    conn.close()

def upsert_yoldaki_urun(sku, urun_adi, yoldaki_miktar, tahmini_varis_tarihi, yoldaki_tedarikci=""):
    conn = get_connection()
    c = conn.cursor()
    bugun = get_today()
    c.execute("""
        INSERT INTO yoldaki_urunler (sku, urun_adi, yoldaki_miktar, tahmini_varis_tarihi, yoldaki_tedarikci, yukleme_tarihi)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            urun_adi=excluded.urun_adi,
            yoldaki_miktar=excluded.yoldaki_miktar,
            tahmini_varis_tarihi=excluded.tahmini_varis_tarihi,
            yoldaki_tedarikci=excluded.yoldaki_tedarikci,
            yukleme_tarihi=excluded.yukleme_tarihi
    """, (sku, urun_adi, yoldaki_miktar, tahmini_varis_tarihi, yoldaki_tedarikci, bugun))
    conn.commit()
    conn.close()

def get_yoldaki_urunler():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM yoldaki_urunler")
    rows = {r["sku"]: dict(r) for r in c.fetchall()}
    conn.close()
    return rows

def get_gecmis_satis(sku, hafta_sayisi=4):
    """Son N haftanın toplam haftalık satışını (tüm firmalar) tarih sıralamasıyla döndürür"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT yukleme_tarihi, SUM(haftalik_satis) as toplam_satis
        FROM firma_stok
        WHERE sku = ?
        GROUP BY yukleme_tarihi
        ORDER BY yukleme_tarihi DESC
        LIMIT ?
    """, (sku, hafta_sayisi))
    rows = [{"tarih": r["yukleme_tarihi"], "satis": r["toplam_satis"]} for r in c.fetchall()]
    conn.close()
    return rows  # En yeni tarih önce

def get_tum_gecmis_satislar(hafta_sayisi=4):
    """Tüm SKU'lar için son N haftanın geçmiş satışlarını döndürür"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT sku, yukleme_tarihi, SUM(haftalik_satis) as toplam_satis
        FROM firma_stok
        GROUP BY sku, yukleme_tarihi
        ORDER BY sku, yukleme_tarihi DESC
    """)
    rows = c.fetchall()
    conn.close()

    sonuc = {}
    for r in rows:
        sku = r["sku"]
        if sku not in sonuc:
            sonuc[sku] = []
        if len(sonuc[sku]) < hafta_sayisi:
            sonuc[sku].append({
                "tarih": r["yukleme_tarihi"],
                "satis": r["toplam_satis"] or 0
            })
    return sonuc

def ekle_satin_alma(sku, urun_adi, tedarikci, tarih, adet, alis_fiyati, maliyet_yuzdesi, notlar=""):
    """Yeni satın alma kaydı ekler. toplam_maliyet = alis_fiyati * (1 + maliyet_yuzdesi/100)"""
    conn = get_connection()
    c = conn.cursor()
    toplam_birim_maliyet = alis_fiyati * (1 + maliyet_yuzdesi / 100)
    toplam_maliyet = toplam_birim_maliyet * adet
    c.execute("""
        INSERT INTO satin_alma_gecmisi
        (sku, urun_adi, tedarikci, satin_alma_tarihi, adet, alis_fiyati, maliyet_yuzdesi, toplam_maliyet, notlar, kayit_tarihi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sku, urun_adi, tedarikci, tarih, adet, alis_fiyati, maliyet_yuzdesi,
          toplam_maliyet, notlar, get_today()))
    conn.commit()
    conn.close()

def guncelle_satin_alma(kayit_id, tedarikci, tarih, adet, alis_fiyati, maliyet_yuzdesi, notlar=""):
    """Mevcut satın alma kaydını günceller"""
    conn = get_connection()
    c = conn.cursor()
    toplam_maliyet = alis_fiyati * (1 + maliyet_yuzdesi / 100)
    c.execute("""
        UPDATE satin_alma_gecmisi SET
            tedarikci=?, satin_alma_tarihi=?, adet=?, alis_fiyati=?,
            maliyet_yuzdesi=?, toplam_maliyet=?, notlar=?
        WHERE id=?
    """, (tedarikci, tarih, adet, alis_fiyati, maliyet_yuzdesi, toplam_maliyet, notlar, kayit_id))
    conn.commit()
    conn.close()

def sil_satin_alma(kayit_id):
    """Satın alma kaydını siler"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM satin_alma_gecmisi WHERE id=?", (kayit_id,))
    conn.commit()
    conn.close()

def get_satin_alma_gecmisi(sku=None):
    """Satın alma geçmişini getirir. sku verilirse o ürünün geçmişi, yoksa tümü."""
    conn = get_connection()
    c = conn.cursor()
    if sku:
        c.execute("""
            SELECT * FROM satin_alma_gecmisi
            WHERE sku=? ORDER BY satin_alma_tarihi DESC
        """, (sku,))
    else:
        c.execute("""
            SELECT * FROM satin_alma_gecmisi
            ORDER BY satin_alma_tarihi DESC
        """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_satin_alma_ozet(sku=None):
    """Bir SKU için satın alma özeti. sku=None ise tüm ürünler."""
    conn = get_connection()
    c = conn.cursor()
    if sku:
        c.execute("""
            SELECT
                COUNT(*) as siparis_sayisi,
                SUM(adet) as toplam_adet,
                AVG(alis_fiyati) as ort_alis,
                SUM(toplam_maliyet) / NULLIF(SUM(adet), 0) as ort_maliyet,
                MIN(satin_alma_tarihi) as ilk_satin_alma,
                MAX(satin_alma_tarihi) as son_satin_alma
            FROM satin_alma_gecmisi
            WHERE sku=?
        """, (sku,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    else:
        c.execute("""
            SELECT sku,
                COUNT(*) as siparis_sayisi,
                SUM(adet) as toplam_adet,
                AVG(alis_fiyati) as ort_alis,
                SUM(toplam_maliyet) / NULLIF(SUM(adet), 0) as ort_maliyet,
                MIN(satin_alma_tarihi) as ilk_satin_alma,
                MAX(satin_alma_tarihi) as son_satin_alma
            FROM satin_alma_gecmisi
            GROUP BY sku
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

def get_tum_tedarikciler():
    """Daha önce girilmiş tedarikçi adlarını döndürür (autocomplete için)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT tedarikci FROM satin_alma_gecmisi WHERE tedarikci != '' ORDER BY tedarikci")
    rows = [r["tedarikci"] for r in c.fetchall()]
    conn.close()
    return rows

def get_gecmis_satis_firma_bazli(sku):
    """Bir SKU için firma bazında tüm geçmiş haftalık satışları döndürür"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT firma, yukleme_tarihi, haftalik_satis, stok_miktari
        FROM firma_stok
        WHERE sku = ?
        ORDER BY yukleme_tarihi ASC
    """, (sku,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_urun_detay(sku):
    """Tek bir ürünün tüm detaylarını döndürür"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM urunler WHERE sku=?", (sku,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def ekle_satin_alma(sku, urun_adi, tedarikci, satin_alma_tarihi, adet, birim_alis_fiyati, toplam_maliyet, notlar=""):
    """Yeni satın alma kaydı ekler"""
    conn = get_connection()
    c = conn.cursor()
    birim_maliyet = (toplam_maliyet / adet) if adet > 0 else 0
    c.execute("""
        INSERT INTO satin_alma_gecmisi
        (sku, urun_adi, tedarikci, satin_alma_tarihi, adet, birim_alis_fiyati, toplam_maliyet, birim_maliyet, notlar, kayit_tarihi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sku, urun_adi, tedarikci, satin_alma_tarihi, adet, birim_alis_fiyati, toplam_maliyet, birim_maliyet, notlar, get_today()))
    conn.commit()
    conn.close()

def get_satin_alma_gecmisi(sku=None):
    """SKU bazında veya tüm satın alma geçmişini getirir"""
    conn = get_connection()
    c = conn.cursor()
    if sku:
        c.execute("SELECT * FROM satin_alma_gecmisi WHERE sku=? ORDER BY satin_alma_tarihi DESC", (sku,))
    else:
        c.execute("SELECT * FROM satin_alma_gecmisi ORDER BY satin_alma_tarihi DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def sil_satin_alma(kayit_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM satin_alma_gecmisi WHERE id=?", (kayit_id,))
    conn.commit()
    conn.close()

def get_ortalama_maliyet(sku):
    """Ağırlıklı ortalama birim maliyet hesaplar"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT SUM(toplam_maliyet) as toplam, SUM(adet) as adet_toplam
        FROM satin_alma_gecmisi WHERE sku=? AND adet > 0
    """, (sku,))
    row = c.fetchone()
    conn.close()
    if row and row["adet_toplam"] and row["adet_toplam"] > 0:
        return round(row["toplam"] / row["adet_toplam"], 2)
    return 0.0

def get_muadil_oneriler(sku, kategori, marka, fiyat):
    """Aynı kategori ve benzer fiyat aralığında muadil ürünler önerir"""
    conn = get_connection()
    c = conn.cursor()
    fiyat_min = fiyat * 0.7 if fiyat else 0
    fiyat_maks = fiyat * 1.3 if fiyat else 999999
    c.execute("""
        SELECT * FROM urunler
        WHERE sku != ? AND kategori = ? AND bizim_stok > 0
        AND (fiyat BETWEEN ? AND ? OR fiyat IS NULL OR fiyat = 0)
        ORDER BY bizim_stok DESC
        LIMIT 5
    """, (sku, kategori, fiyat_min, fiyat_maks))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
