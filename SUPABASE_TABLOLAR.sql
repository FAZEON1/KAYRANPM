-- KAYRANPM — Supabase Tablo Kurulumu
-- Supabase Dashboard → SQL Editor → buraya yapıştır → Run

CREATE TABLE IF NOT EXISTS urunler (
    sku TEXT PRIMARY KEY,
    urun_adi TEXT,
    kategori TEXT DEFAULT '',
    marka TEXT DEFAULT '',
    satis_fiyati REAL DEFAULT 0,
    alis_fiyati REAL DEFAULT 0,
    hedef_kar_marji REAL DEFAULT 0,
    ozellikler TEXT DEFAULT '',
    bizim_stok INTEGER DEFAULT 0,
    trendyol_stok INTEGER DEFAULT 0,
    ilk_giris_tarihi TEXT,
    guncelleme_tarihi TEXT
);

CREATE TABLE IF NOT EXISTS firma_stok (
    id BIGSERIAL PRIMARY KEY,
    firma TEXT NOT NULL,
    sku TEXT NOT NULL,
    urun_adi TEXT,
    stok_miktari INTEGER DEFAULT 0,
    haftalik_satis INTEGER DEFAULT 0,
    yukleme_tarihi TEXT,
    UNIQUE(firma, sku, yukleme_tarihi)
);

CREATE TABLE IF NOT EXISTS satin_alma_gecmisi (
    id BIGSERIAL PRIMARY KEY,
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
);

CREATE TABLE IF NOT EXISTS yoldaki_urunler (
    sku TEXT PRIMARY KEY,
    urun_adi TEXT,
    yoldaki_miktar INTEGER DEFAULT 0,
    tahmini_varis_tarihi TEXT,
    yoldaki_tedarikci TEXT,
    yukleme_tarihi TEXT
);

CREATE TABLE IF NOT EXISTS stok_yas (
    sku TEXT PRIMARY KEY,
    ilk_gorulen_tarih TEXT
);

CREATE TABLE IF NOT EXISTS siparis_onerileri (
    id BIGSERIAL PRIMARY KEY,
    firma TEXT,
    sku TEXT,
    urun_adi TEXT,
    oneri_miktari INTEGER DEFAULT 0,
    durum TEXT DEFAULT 'bekliyor',
    olusturma_tarihi TEXT,
    onay_tarihi TEXT
);

CREATE TABLE IF NOT EXISTS kampanyalar (
    id BIGSERIAL PRIMARY KEY,
    kampanya_adi TEXT NOT NULL,
    firma TEXT NOT NULL,
    baslangic_tarihi TEXT,
    bitis_tarihi TEXT,
    durum TEXT DEFAULT 'aktif',
    notlar TEXT,
    olusturma_tarihi TEXT
);

CREATE TABLE IF NOT EXISTS kampanya_urunler (
    id BIGSERIAL PRIMARY KEY,
    kampanya_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    urun_adi TEXT,
    pacal_maliyet REAL DEFAULT 0,
    satis_fiyati REAL DEFAULT 0,
    birim_firma_destek REAL DEFAULT 0,
    birim_ek_destek REAL DEFAULT 0,
    satilan_adet INTEGER DEFAULT 0,
    notlar TEXT
);

CREATE TABLE IF NOT EXISTS bildirim_ayarlari (
    id BIGSERIAL PRIMARY KEY,
    email TEXT,
    smtp_server TEXT,
    smtp_port INTEGER DEFAULT 587,
    smtp_user TEXT,
    smtp_password TEXT,
    aktif BOOLEAN DEFAULT false
);
