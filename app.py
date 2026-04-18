import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os, sys
from datetime import datetime, date
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (initialize_db, onayla_siparis, reddet_siparis,
                      get_siparis_onerileri, ekle_siparis_onerisi,
                      get_gecmis_satis_firma_bazli, get_urun_detay,
                      ekle_satin_alma, guncelle_satin_alma, sil_satin_alma,
                      get_satin_alma_gecmisi, get_tum_tedarikciler)
from analitik import dashboard_hesapla, muadil_bul, genel_analiz_hesapla, kar_marji_analizi
from excel_islemler import (excel_yukle_ana_stok, excel_yukle_firma_stoklari,
                            excel_yukle_yoldaki_urunler, create_sample_excel_bytes)
from bildirim import (get_bildirim_ayarlari, kaydet_bildirim_ayarlari, email_gonder)

# ── Sayfa ayarları ──────────────────────────────────────────────────
st.set_page_config(
    page_title="KAYRANPM | Stok Yönetimi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_db()

# ── Giriş Sistemi ────────────────────────────────────────────────────
def giris_kontrol():
    """Kullanıcı giriş doğrulaması. st.secrets'tan kullanıcıları okur."""
    if "giris_yapildi" not in st.session_state:
        st.session_state.giris_yapildi = False
    if "aktif_kullanici" not in st.session_state:
        st.session_state.aktif_kullanici = ""
    return st.session_state.giris_yapildi

def giris_ekrani():
    """Giriş ekranını gösterir."""
    st.markdown("""
    <style>
    .giris-kart {
        max-width: 420px; margin: 80px auto 0;
        background: white; border-radius: 16px;
        padding: 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        border: 1px solid #E0E0E0;
    }
    .giris-baslik { font-size: 24px; font-weight: 800; color: #1F4E79; margin-bottom: 4px; }
    .giris-alt { font-size: 13px; color: #757575; margin-bottom: 28px; }
    </style>
    <div class="giris-kart">
      <div class="giris-baslik">📦 KAYRANPM</div>
      <div class="giris-alt">Devam etmek için giriş yapın</div>
    </div>
    """, unsafe_allow_html=True)

    # Ortaya hizalı form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.form("giris_form"):
            st.markdown("### 🔐 Giriş Yap")
            kullanici = st.text_input("Kullanıcı Adı", placeholder="kullanici_adi")
            sifre = st.text_input("Şifre", type="password", placeholder="••••••••")
            giris_btn = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)

        if giris_btn:
            # Secrets'tan kullanıcıları kontrol et
            try:
                kullanicilar = st.secrets.get("kullanicilar", {})
                if not kullanicilar:
                    # Secrets yoksa geliştirici modu — sadece uyarı göster
                    st.warning("⚠️ Kullanıcı ayarları henüz yapılandırılmamış. Streamlit Cloud → Settings → Secrets bölümünden kullanıcıları ekleyin.")
                    st.code("""
# Streamlit Secrets'a eklenecek format:
[kullanicilar]
ibrahim = "sifreniz123"
ekip_uyesi = "baska_sifre"
                    """)
                    return

                if kullanici in kullanicilar and kullanicilar[kullanici] == sifre:
                    st.session_state.giris_yapildi = True
                    st.session_state.aktif_kullanici = kullanici
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı.")
            except Exception as e:
                st.error(f"Giriş sistemi hatası: {e}")

# Giriş kontrolü yap
if not giris_kontrol():
    giris_ekrani()
    st.stop()


st.markdown("""
<style>
/* Genel arka plan */
.main { background-color: #F4F6F9; }

/* Metric kartları */
[data-testid="metric-container"] {
    background: white;
    border-radius: 10px;
    padding: 16px;
    border: 1px solid #E0E0E0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}

/* Başlık */
.baslik {
    font-size: 26px; font-weight: 800;
    color: #1F4E79; margin-bottom: 4px;
}
.alt-baslik {
    font-size: 13px; color: #757575; margin-bottom: 20px;
}

/* Renk etiketleri */
.tag-kirmizi  { background:#FFCCCC; color:#C62828; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.tag-turuncu  { background:#FFE0B2; color:#E65100; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.tag-sari     { background:#FFF9C4; color:#F57F17; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.tag-yesil    { background:#C8E6C9; color:#2E7D32; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.tag-gri      { background:#F0F0F0; color:#616161; padding:3px 10px; border-radius:12px; font-size:12px; }

.uyari-box { background:#FFF3E0; border-left:4px solid #FF6F00;
             padding:10px 16px; border-radius:4px; margin:6px 0; font-size:13px; }
.muadil-box { background:#F3E5F5; border-left:4px solid #7B1FA2;
              padding:10px 16px; border-radius:4px; margin:6px 0; font-size:13px; }
.info-box   { background:#E3F2FD; border-left:4px solid #1565C0;
              padding:10px 16px; border-radius:4px; margin:6px 0; font-size:13px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #1F4E79 !important; }
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stRadio label { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── Yardımcı fonksiyonlar ────────────────────────────────────────────
STOK_YAS_ETIKET = {
    "kirmizi": '<span class="tag-kirmizi">🔴 {g} gün</span>',
    "turuncu": '<span class="tag-turuncu">🟠 {g} gün</span>',
    "sari":    '<span class="tag-sari">🟡 {g} gün</span>',
    "yesil":   '<span class="tag-yesil">🟢 {g} gün</span>',
    "yok":     '<span class="tag-gri">—</span>',
}
GUN_ETIKET = {
    "kirmizi": '<span class="tag-kirmizi">🔴 {g} gün</span>',
    "turuncu": '<span class="tag-turuncu">🟠 {g} gün</span>',
    "yesil":   '<span class="tag-yesil">🟢 {g} gün</span>',
    "yok":     '<span class="tag-gri">—</span>',
}
PERF_ETIKET = {
    "Çok İyi": '<span class="tag-yesil">⭐ Çok İyi</span>',
    "İyi":     '<span class="tag-sari">👍 İyi</span>',
    "Düşük":   '<span class="tag-kirmizi">📉 Düşük</span>',
    "veri yok":'<span class="tag-gri">—</span>',
}
YOL_ETIKET = {
    "yesil":   "🟢",
    "sari":    "🟡",
    "kirmizi": "🔴",
    "yok":     "—",
}

def stok_yas_html(renk, gun):
    return STOK_YAS_ETIKET.get(renk, STOK_YAS_ETIKET["yok"]).format(g=gun)

def gun_html(renk, gun):
    if gun is None: return '<span class="tag-gri">—</span>'
    return GUN_ETIKET.get(renk, GUN_ETIKET["yok"]).format(g=gun)

def perf_html(perf):
    return PERF_ETIKET.get(perf, PERF_ETIKET["veri yok"])

# ── Sidebar navigasyon ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 KAYRANPM")
    # Kullanıcı bilgisi
    aktif_kullanici = st.session_state.get("aktif_kullanici", "")
    if aktif_kullanici:
        st.markdown(f"""
        <div style="background:#163C5E; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
          <span style="color:#90CAF9; font-size:11px;">👤 Giriş yapan</span><br>
          <span style="color:white; font-weight:bold; font-size:13px;">{aktif_kullanici}</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.giris_yapildi = False
            st.session_state.aktif_kullanici = ""
            st.rerun()
    st.markdown("---")
    sayfa = st.radio("", [
        "📊  Dashboard",
        "🔍  Ürün Detay",
        "📈  Genel Analiz",
        "💰  Kar Marjı",
        "🛒  Satın Alma Geçmişi",
        "📦  Sipariş Yönetimi",
        "📂  Veri Yükleme",
        "📄  Raporlar",
        "🔔  Bildirim Ayarları",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"<small>🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}</small>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# 1) DASHBOARD
# ════════════════════════════════════════════════════════════════════
if sayfa == "📊  Dashboard":
    st.markdown('<div class="baslik">📊 KAYRANPM — Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="alt-baslik">Stok durumu, satış performansı ve uyarılar</div>', unsafe_allow_html=True)

    # Filtreler
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        filtre_firma = st.selectbox("Firma Filtresi", ["Tüm Firmalar", "ITOPYA", "HB", "VATAN", "MONDAY", "KANAL", "DİĞER"])
    with col_f2:
        arama = st.text_input("🔍 SKU veya ürün adı ara...", "")
    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)
        yenile = st.button("🔄 Yenile", use_container_width=True)

    # Veri yükle
    try:
        veri = dashboard_hesapla()
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        st.stop()

    # Filtrele
    gosterilecek = []
    for urun in veri:
        for fd in urun["firma_detay"]:
            firma_adi = fd["firma"]
            if filtre_firma != "Tüm Firmalar":
                hedef = filtre_firma.replace("İ","I").replace("Ğ","G").replace("Ü","U").replace("Ş","S").replace("Ç","C").replace("Ö","O")
                kaynak = firma_adi.replace("İ","I").replace("Ğ","G").replace("Ü","U").replace("Ş","S").replace("Ç","C").replace("Ö","O")
                if hedef not in kaynak:
                    continue
            if arama:
                if arama.lower() not in urun["sku"].lower() and arama.lower() not in urun["urun_adi"].lower():
                    continue
            gosterilecek.append((urun, fd))

    # İstatistik kartları
    toplam_sku = len(set(u["sku"] for u in veri))
    uyari_sayisi = sum(1 for u, fd in gosterilecek if fd["siparis_uyarisi"])
    kritik_sayisi = sum(1 for u in veri if u["stok_renk"] == "kirmizi")
    muadil_sayisi = sum(1 for u, fd in gosterilecek if fd["muadil_gerekli"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Toplam Ürün", toplam_sku)
    m2.metric("⚠️ Sipariş Gerekli", uyari_sayisi, delta="Acil" if uyari_sayisi > 0 else None, delta_color="inverse")
    m3.metric("🔴 Kritik Stok (90g+)", kritik_sayisi, delta="Dikkat" if kritik_sayisi > 0 else None, delta_color="inverse")
    m4.metric("🔄 Muadil Gerekli", muadil_sayisi)

    # ACİL SİPARİŞ BANNER
    acil_urunler = [u for u in veri if u.get("siparis_durum") == "acil"]
    yaklasan_urunler = [u for u in veri if u.get("siparis_durum") == "yaklasıyor"]
    if acil_urunler:
        acil_isimler = ", ".join(f"**{u['urun_adi']}**" for u in acil_urunler[:5])
        if len(acil_urunler) > 5:
            acil_isimler += f" ve {len(acil_urunler)-5} ürün daha"
        st.error(f"🚨 **ACİL SİPARİŞ GEREKİYOR!** {len(acil_urunler)} ürün için stok 135 günden az: {acil_isimler}")
    if yaklasan_urunler:
        yak_isimler = ", ".join(u['urun_adi'] for u in yaklasan_urunler[:3])
        st.warning(f"⚠️ **30 gün içinde sipariş verilmeli:** {yak_isimler}" + (f" ve {len(yaklasan_urunler)-3} ürün daha" if len(yaklasan_urunler) > 3 else ""))

    # Tarayıcı bildirimi (JS)
    if acil_urunler:
        st.markdown(f"""
        <script>
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {{
            new Notification('🚨 Stok Yönetimi', {{
                body: '{len(acil_urunler)} ürün için ACİL sipariş gerekiyor!',
                icon: '📦'
            }});
        }} else if (typeof Notification !== 'undefined' && Notification.permission !== 'denied') {{
            Notification.requestPermission().then(function(p) {{
                if (p === 'granted') {{
                    new Notification('🚨 Stok Yönetimi', {{
                        body: '{len(acil_urunler)} ürün için ACİL sipariş gerekiyor!',
                    }});
                }}
            }});
        }}
        </script>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Renk açıklaması
    st.markdown("""
    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px;">
      <span class="tag-kirmizi">🔴 ACİL / 90+ gün stok yaşı</span>
      <span class="tag-turuncu">🟠 Yaklaşıyor / 60-90 gün</span>
      <span class="tag-sari">🟡 Planlama / 30-60 gün</span>
      <span class="tag-yesil">🟢 Normal / Sağlıklı</span>
    </div>
    """, unsafe_allow_html=True)

    if not gosterilecek:
        st.info("Gösterilecek veri bulunamadı. Lütfen önce 'Veri Yükleme' sekmesinden veri yükleyin.")
    else:
        satirlar = []
        for urun, fd in gosterilecek:
            y = urun["yayilim"]
            yayilim = f"TY:{y.get('TRENDYOL',0)} | HB:{y.get('HB',0)} | IT:{y.get('ITOPYA',0)} | VT:{y.get('VATAN',0)}"
            yol_renk = urun.get("yol_renk", "yok")
            yol_mesaj = urun.get("yol_mesaj", "")
            yol_miktar = urun.get("yol_miktar", 0)
            yol_metin = f"{YOL_ETIKET.get(yol_renk,'—')} {yol_miktar} adet | {yol_mesaj}" if yol_renk != "yok" else "—"
            uyari = "⚠️ SİPARİŞ ÖNER!" if fd["siparis_uyarisi"] else ("🔄 MUADİL" if fd["muadil_gerekli"] else "")
            olu_durum = urun.get("olu_stok_durum", "normal")
            olu_mesaj = urun.get("olu_stok_mesaj", "")
            satirlar.append({
                "SKU": urun["sku"],
                "Ürün Adı": urun["urun_adi"],
                "Kategori": urun["kategori"],
                "Bizim Stok": urun["bizim_stok"],
                "Ort. Hft. Satış": urun.get("ortalama_haftalik_satis", 0),
                "Satış Trendi": urun.get("trend_mesaji", "—"),
                "Trend Yön": urun.get("trend_yon", "yetersiz_veri"),
                "📋 Sipariş Takvimi": urun.get("siparis_mesaj", "—"),
                "Sipariş Durum": urun.get("siparis_durum", "veri_yok"),
                "📦 Önerilen Sipariş": f"{urun.get('oneri_miktar',0)} adet" if urun.get("oneri_miktar",0) > 0 else "✅ Yeterli",
                "⚡ Risk Skoru": urun.get("risk_skor", 0),
                "Risk Etiketi": urun.get("risk_etiketi", "—"),
                "🪦 Stok Durumu": olu_mesaj if olu_mesaj else "—",
                "Ölü Durum": olu_durum,
                "Firma": fd["firma"],
                "Firma Stok": fd["stok"],
                "Haftalık Satış": fd["satis"],
                "Stok Yaşı": f"{urun['stok_gun']} gün",
                "Stok Renk": urun["stok_renk"],
                "Performans": fd["performans"],
                "Yoldaki Durum": yol_metin,
                "Yol Renk": yol_renk,
                "Stok Yayılımı": yayilim,
                "Uyarı": uyari,
                "_sku": urun["sku"], "_firma": fd["firma"], "_urun_adi": urun["urun_adi"],
                "_siparis_uyarisi": fd["siparis_uyarisi"], "_muadil_gerekli": fd["muadil_gerekli"],
            })

        df = pd.DataFrame(satirlar)

        def renk_uygula(df_goster):
            def satir_rengi(row):
                styles = [""] * len(row)
                cols = list(row.index)
                sp_renk = {"acil":"#FFCCCC","yaklasıyor":"#FFE0B2","planlama":"#FFF9C4","normal":"#E8F5E9","veri_yok":"#F5F5F5"}
                if "📋 Sipariş Takvimi" in cols:
                    r = sp_renk.get(row.get("Sipariş Durum",""),"")
                    if r: styles[cols.index("📋 Sipariş Takvimi")] = f"background-color:{r}; font-weight:bold"
                yas_renk = {"kirmizi":"#FFCCCC","turuncu":"#FFE0B2","sari":"#FFF9C4","yesil":"#C8E6C9","yok":""}
                if "Stok Yaşı" in cols:
                    r = yas_renk.get(row.get("Stok Renk",""),"")
                    if r: styles[cols.index("Stok Yaşı")] = f"background-color:{r}"
                trend_renk = {"yukseliyor":"#C8E6C9","dusuyor":"#FFCCCC","stabil":"#FFF9C4","yetersiz_veri":"#F5F5F5"}
                if "Satış Trendi" in cols:
                    r = trend_renk.get(row.get("Trend Yön",""),"")
                    if r: styles[cols.index("Satış Trendi")] = f"background-color:{r}"
                if "⚡ Risk Skoru" in cols:
                    skor = row.get("⚡ Risk Skoru", 0)
                    if skor >= 70: styles[cols.index("⚡ Risk Skoru")] = "background-color:#FFCCCC; font-weight:bold"
                    elif skor >= 45: styles[cols.index("⚡ Risk Skoru")] = "background-color:#FFE0B2"
                    elif skor >= 25: styles[cols.index("⚡ Risk Skoru")] = "background-color:#FFF9C4"
                    else: styles[cols.index("⚡ Risk Skoru")] = "background-color:#C8E6C9"
                if "🪦 Stok Durumu" in cols:
                    d = row.get("Ölü Durum","normal")
                    if d == "olu": styles[cols.index("🪦 Stok Durumu")] = "background-color:#FFCCCC; font-weight:bold"
                    elif d == "yavas": styles[cols.index("🪦 Stok Durumu")] = "background-color:#FFE0B2"
                perf_renk = {"Çok İyi":"#C8E6C9","İyi":"#FFF9C4","Düşük":"#FFCCCC","veri yok":"#F0F0F0"}
                if "Performans" in cols:
                    r = perf_renk.get(row.get("Performans",""),"")
                    if r: styles[cols.index("Performans")] = f"background-color:{r}"
                yol_renk_map = {"yesil":"#C8E6C9","sari":"#FFF9C4","kirmizi":"#FFCCCC","yok":""}
                if "Yoldaki Durum" in cols:
                    r = yol_renk_map.get(row.get("Yol Renk",""),"")
                    if r: styles[cols.index("Yoldaki Durum")] = f"background-color:{r}"
                if "Uyarı" in cols and row.get("Uyarı",""):
                    if "SİPARİŞ" in str(row.get("Uyarı","")): styles[cols.index("Uyarı")] = "background-color:#FFCCCC; font-weight:bold"
                    elif "MUADİL" in str(row.get("Uyarı","")): styles[cols.index("Uyarı")] = "background-color:#F3E5F5"
                return styles

            goster = ["SKU","Ürün Adı","Kategori","Bizim Stok","Ort. Hft. Satış","Satış Trendi",
                      "📋 Sipariş Takvimi","📦 Önerilen Sipariş","⚡ Risk Skoru","🪦 Stok Durumu",
                      "Firma","Firma Stok","Haftalık Satış","Stok Yaşı","Performans",
                      "Yoldaki Durum","Stok Yayılımı","Uyarı"]
            gizli = [k for k in ["Stok Renk","Yol Renk","Sipariş Durum","Trend Yön","Risk Etiketi","Ölü Durum"] if k in df_goster.columns]
            styled = df_goster[goster + gizli].style.apply(satir_rengi, axis=1)
            styled = styled.hide(axis="columns", subset=gizli)
            st.dataframe(styled, use_container_width=True, height=480)

        tab1, tab2, tab3, tab4 = st.tabs(["⚡ En Riskli","📈 En Çok Satan","📉 En Az Satan","🕐 Stok Yaşına Göre"])
        with tab1:
            st.caption("Risk skoru en yüksek ürünler önce")
            renk_uygula(df.drop_duplicates("SKU").sort_values("⚡ Risk Skoru", ascending=False))
        with tab2:
            st.caption("4 haftalık ortalamaya göre en çok satan ürünler")
            renk_uygula(df.drop_duplicates("SKU").sort_values("Ort. Hft. Satış", ascending=False))
        with tab3:
            st.caption("En az satan / yavaş hareket eden ürünler")
            renk_uygula(df.drop_duplicates("SKU").sort_values("Ort. Hft. Satış", ascending=True))
        with tab4:
            st.caption("En eski stok yaşına sahip ürünler önce")
            renk_uygula(df.drop_duplicates("SKU").sort_values("Stok Yaşı", ascending=False))

                # Sipariş ve muadil işlemleri
        uyari_listesi = [(u, fd) for u, fd in gosterilecek if fd["siparis_uyarisi"] or fd["muadil_gerekli"]]
        if uyari_listesi:
            st.markdown("### 🚨 Aksiyon Gerektiren Ürünler")
            for urun, fd in uyari_listesi:
                if fd["siparis_uyarisi"]:
                    with st.container():
                        st.markdown(f'<div class="uyari-box">⚠️ <b>{urun["urun_adi"]}</b> — {fd["firma"]} stoğu azalmış (Firma stok: {fd["stok"]} | Bizim stok: {urun["bizim_stok"]})</div>', unsafe_allow_html=True)
                        col1, col2 = st.columns([3,1])
                        with col2:
                            miktar = st.number_input("Miktar", min_value=1, value=10, key=f"sp_{urun['sku']}_{fd['firma']}")
                            if st.button("📦 Sipariş Önerisi Ekle", key=f"btn_{urun['sku']}_{fd['firma']}"):
                                ekle_siparis_onerisi(fd["firma"], urun["sku"], urun["urun_adi"], miktar)
                                st.success("Sipariş önerisi oluşturuldu!")
                                st.rerun()

                if fd["muadil_gerekli"]:
                    muadiller = muadil_bul(urun["sku"])
                    if muadiller:
                        isimler = ", ".join(m["urun_adi"] for m in muadiller[:3])
                        st.markdown(f'<div class="muadil-box">🔄 <b>{urun["urun_adi"]}</b> — {fd["firma"]} ve depomuzda stok yok. Muadil öneri: <b>{isimler}</b></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="muadil-box">🔄 <b>{urun["urun_adi"]}</b> — Stok yok, muadil bulunamadı.</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# 2) ÜRÜN DETAY
# ════════════════════════════════════════════════════════════════════
elif sayfa == "🔍  Ürün Detay":
    st.markdown('<div class="baslik">🔍 Ürün Detay & Satış Analizi</div>', unsafe_allow_html=True)

    # Ürün seçimi
    try:
        veri = dashboard_hesapla()
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        st.stop()

    if not veri:
        st.info("Önce 'Veri Yükleme' sekmesinden veri yükleyin.")
        st.stop()

    sku_listesi = {f"{u['sku']} — {u['urun_adi']}": u['sku'] for u in veri}
    secim = st.selectbox("Ürün Seçin", list(sku_listesi.keys()))
    secilen_sku = sku_listesi[secim]
    urun = next(u for u in veri if u["sku"] == secilen_sku)

    st.markdown("---")

    # Üst bilgi kartları
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Bizim Stok", urun["bizim_stok"])
    c2.metric("📊 Ort. Hft. Satış", urun.get("ortalama_haftalik_satis", 0))
    c3.metric("⚡ Risk Skoru", f"{urun.get('risk_skor',0)}/100")
    c4.metric("📅 Stok Biter", f"{urun.get('stok_bitis_gun','-')} gün")
    c5.metric("📦 Sipariş Önerisi", f"{urun.get('oneri_miktar',0)} adet")

    # Sipariş durumu banner
    siparis_durum = urun.get("siparis_durum", "veri_yok")
    siparis_mesaj = urun.get("siparis_mesaj", "")
    if siparis_durum == "acil":
        st.error(f"🚨 {siparis_mesaj} | {urun.get('oneri_mesaj','')}")
    elif siparis_durum == "yaklasıyor":
        st.warning(f"⚠️ {siparis_mesaj} | {urun.get('oneri_mesaj','')}")
    elif siparis_durum == "planlama":
        st.info(f"📋 {siparis_mesaj}")
    else:
        st.success(f"✅ {siparis_mesaj}")

    st.markdown("---")

    # Geçmiş satış verileri
    gecmis_raw = get_gecmis_satis_firma_bazli(secilen_sku)

    if not gecmis_raw:
        st.info("Bu ürün için henüz geçmiş satış verisi bulunmuyor. Haftalık veri yükledikçe grafikler oluşacak.")
    else:
        df_gecmis = pd.DataFrame(gecmis_raw)
        tarihler = sorted(df_gecmis["yukleme_tarihi"].unique())
        firmalar = sorted(df_gecmis["firma"].unique())

        # TAB 1: Toplam satış trendi
        # TAB 2: Firma bazında satış
        # TAB 3: Stok seviyeleri
        gtab1, gtab2, gtab3 = st.tabs(["📈 Toplam Satış Trendi", "🏪 Firma Bazında Satış", "📦 Stok Seviyeleri"])

        with gtab1:
            # Haftalık toplam satış
            toplam_df = df_gecmis.groupby("yukleme_tarihi")["haftalik_satis"].sum().reset_index()
            toplam_df.columns = ["Tarih", "Toplam Satış"]
            toplam_df = toplam_df.sort_values("Tarih")

            fig = go.Figure()

            # Satış çizgisi
            fig.add_trace(go.Scatter(
                x=toplam_df["Tarih"],
                y=toplam_df["Toplam Satış"],
                mode="lines+markers",
                name="Haftalık Satış",
                line=dict(color="#1F4E79", width=3),
                marker=dict(size=8),
            ))

            # 4 haftalık ortalama çizgisi
            if len(toplam_df) >= 2:
                ort = toplam_df["Toplam Satış"].mean()
                fig.add_hline(
                    y=ort,
                    line_dash="dash",
                    line_color="#FF6F00",
                    annotation_text=f"4 Hft Ort: {ort:.1f}",
                    annotation_position="right"
                )

            # Trend yönü rengi
            trend_yon = urun.get("trend_yon", "stabil")
            trend_renk = {"yukseliyor": "#2E7D32", "dusuyor": "#C62828", "stabil": "#F57C00"}.get(trend_yon, "#666")

            fig.update_layout(
                title=dict(text=f"Haftalık Toplam Satış Trendi — {urun['urun_adi']}", font=dict(size=15)),
                xaxis_title="Hafta",
                yaxis_title="Satış Adedi",
                height=380,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
                showlegend=True,
                annotations=[dict(
                    x=0.01, y=0.97, xref="paper", yref="paper",
                    text=f"Trend: {urun.get('trend_mesaji','—')}",
                    showarrow=False,
                    font=dict(size=13, color=trend_renk),
                    bgcolor="white",
                    bordercolor=trend_renk,
                    borderwidth=1,
                    borderpad=4,
                )]
            )
            st.plotly_chart(fig, use_container_width=True)

            # Haftalık tablo
            with st.expander("📋 Haftalık Satış Tablosu"):
                st.dataframe(toplam_df.sort_values("Tarih", ascending=False), use_container_width=True)

        with gtab2:
            # Firma bazında satış karşılaştırması
            fig2 = go.Figure()

            renkler = {
                "ITOPYA": "#1F4E79",
                "HB": "#FF6F00",
                "VATAN": "#2E7D32",
                "MONDAY": "#7B1FA2",
                "KANAL": "#C62828",
                "DIGER": "#546E7A",
            }

            for firma in firmalar:
                firma_df = df_gecmis[df_gecmis["firma"] == firma].sort_values("yukleme_tarihi")
                if firma_df["haftalik_satis"].sum() == 0:
                    continue
                fig2.add_trace(go.Bar(
                    x=firma_df["yukleme_tarihi"],
                    y=firma_df["haftalik_satis"],
                    name=firma,
                    marker_color=renkler.get(firma, "#888"),
                ))

            fig2.update_layout(
                title=dict(text=f"Firma Bazında Haftalık Satış — {urun['urun_adi']}", font=dict(size=15)),
                xaxis_title="Hafta",
                yaxis_title="Satış Adedi",
                barmode="group",
                height=380,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Firma performans özeti
            st.markdown("**Firma Performans Özeti (Toplam Satış)**")
            firma_ozet = df_gecmis.groupby("firma")["haftalik_satis"].agg(["sum","mean"]).reset_index()
            firma_ozet.columns = ["Firma", "Toplam Satış", "Ort. Haftalık"]
            firma_ozet = firma_ozet.sort_values("Toplam Satış", ascending=False)
            firma_ozet["Ort. Haftalık"] = firma_ozet["Ort. Haftalık"].round(1)
            st.dataframe(firma_ozet, use_container_width=True, hide_index=True)

        with gtab3:
            # Bizim stok + firma stok seviyeleri
            fig3 = go.Figure()

            # Bizim stok (depo)
            bizim_stok_df = df_gecmis.groupby("yukleme_tarihi")["stok_miktari"].sum().reset_index()
            bizim_stok_df = bizim_stok_df.sort_values("yukleme_tarihi")

            for firma in firmalar:
                firma_df = df_gecmis[df_gecmis["firma"] == firma].sort_values("yukleme_tarihi")
                if firma_df["stok_miktari"].sum() == 0:
                    continue
                fig3.add_trace(go.Scatter(
                    x=firma_df["yukleme_tarihi"],
                    y=firma_df["stok_miktari"],
                    mode="lines+markers",
                    name=f"{firma} Stok",
                    line=dict(color=renkler.get(firma, "#888"), width=2),
                    marker=dict(size=6),
                ))

            fig3.update_layout(
                title=dict(text=f"Firma Stok Seviyeleri — {urun['urun_adi']}", font=dict(size=15)),
                xaxis_title="Hafta",
                yaxis_title="Stok Adedi",
                height=380,
                plot_bgcolor="white",
                paper_bgcolor="white",
                hovermode="x unified",
            )
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # Yoldaki durum
    st.subheader("🚢 Yoldaki Ürün Durumu")
    yol_renk = urun.get("yol_renk", "yok")
    if yol_renk == "yesil":
        st.success(f"🟢 {urun.get('yol_miktar',0)} adet yolda | {urun.get('yol_mesaj','')}")
    elif yol_renk == "sari":
        st.warning(f"🟡 {urun.get('yol_miktar',0)} adet yolda | {urun.get('yol_mesaj','')}")
    elif yol_renk == "kirmizi":
        st.error(f"🔴 {urun.get('yol_mesaj','')}")
    else:
        st.info("Yolda ürün kaydı bulunmuyor.")

    # Muadil öneriler
    st.markdown("---")
    st.subheader("🔄 Muadil Ürün Önerileri")
    muadiller = muadil_bul(secilen_sku)
    if muadiller:
        df_m = pd.DataFrame([{
            "SKU": m["sku"],
            "Ürün Adı": m["urun_adi"],
            "Marka": m.get("marka",""),
            "Kategori": m.get("kategori",""),
            "Bizim Stok": m.get("bizim_stok",0),
        } for m in muadiller])
        st.dataframe(df_m, use_container_width=True, hide_index=True)
    else:
        st.info("Aynı kategoride stokta muadil ürün bulunamadı.")

# ════════════════════════════════════════════════════════════════════
# 3) GENEL ANALİZ
# ════════════════════════════════════════════════════════════════════
elif sayfa == "📈  Genel Analiz":
    st.markdown('<div class="baslik">📈 Genel Analiz Merkezi</div>', unsafe_allow_html=True)
    st.markdown('<div class="alt-baslik">Kategori, marka, ölü stok ve sipariş önceliklendirme</div>', unsafe_allow_html=True)

    try:
        analiz = genel_analiz_hesapla()
    except Exception as e:
        st.error(f"Analiz yüklenemedi: {e}")
        st.stop()

    urunler = analiz["urunler"]
    if not urunler:
        st.info("Veri bulunamadı. Lütfen önce veri yükleyin.")
        st.stop()

    # Üst özet metrikler
    toplam_urun = len(urunler)
    acil_sayisi = sum(1 for u in urunler if u.get("siparis_durum") == "acil")
    olu_sayisi = sum(1 for u in urunler if u.get("olu_stok_durum") == "olu")
    yavas_sayisi = sum(1 for u in urunler if u.get("olu_stok_durum") == "yavas")
    toplam_siparis_oneri = sum(u.get("oneri_miktar", 0) for u in urunler)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📦 Toplam Ürün", toplam_urun)
    m2.metric("🚨 Acil Sipariş", acil_sayisi)
    m3.metric("🪦 Ölü Stok", olu_sayisi)
    m4.metric("🐢 Yavaş Satan", yavas_sayisi)
    m5.metric("📋 Toplam Sipariş Önerisi", f"{toplam_siparis_oneri:,} adet")

    st.markdown("---")

    atab1, atab2, atab3, atab4 = st.tabs([
        "🎯 Öncelikli Sipariş Listesi",
        "🪦 Ölü & Yavaş Stok",
        "📂 Kategori Analizi",
        "🏷️ Marka Analizi",
    ])

    # ── TAB 1: Öncelikli sipariş listesi ──
    with atab1:
        st.markdown("**Sipariş verilmesi gereken ürünler — risk ve aciliyete göre sıralı**")
        siparis_listesi = analiz["siparis_listesi"]
        if not siparis_listesi:
            st.success("✅ Tüm ürünlerde yeterli stok var, sipariş gerekmüyor.")
        else:
            rows = []
            for u in siparis_listesi:
                rows.append({
                    "SKU": u["sku"],
                    "Ürün Adı": u["urun_adi"],
                    "Kategori": u.get("kategori",""),
                    "Bizim Stok": u["bizim_stok"],
                    "Ort. Hft. Satış": u.get("ortalama_haftalik_satis", 0),
                    "Stok Biter": f"{u.get('stok_bitis_gun','-')} gün",
                    "Sipariş Durumu": u.get("siparis_mesaj",""),
                    "📦 Önerilen Miktar": u.get("oneri_miktar", 0),
                    "Trend": u.get("trend_mesaji",""),
                    "Risk": u.get("risk_skor", 0),
                    "_durum": u.get("siparis_durum",""),
                })

            df_sp = pd.DataFrame(rows)

            def sp_rengi(row):
                durum = row.get("_durum","")
                renk_map = {"acil":"#FFCCCC","yaklasıyor":"#FFE0B2","planlama":"#FFF9C4","normal":"#E8F5E9"}
                renk = renk_map.get(durum, "")
                return [f"background-color:{renk}" if renk else "" for _ in row]

            goster = ["SKU","Ürün Adı","Kategori","Bizim Stok","Ort. Hft. Satış",
                      "Stok Biter","Sipariş Durumu","📦 Önerilen Miktar","Trend","Risk"]
            styled = df_sp[goster + ["_durum"]].style.apply(sp_rengi, axis=1)
            styled = styled.hide(axis="columns", subset=["_durum"])
            st.dataframe(styled, use_container_width=True, height=450)

            # Toplam sipariş özeti
            st.markdown(f"""
            <div class="info-box">
            📋 <b>Toplam {len(siparis_listesi)} ürün</b> için sipariş önerilmektedir.
            Toplam önerilen miktar: <b>{sum(u.get('oneri_miktar',0) for u in siparis_listesi):,} adet</b>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 2: Ölü & Yavaş Stok ──
    with atab2:
        olu_urunler = [u for u in urunler if u.get("olu_stok_durum") in ("olu", "yavas")]
        if not olu_urunler:
            st.success("✅ Ölü veya yavaş hareket eden stok tespit edilmedi.")
        else:
            st.warning(f"⚠️ {len(olu_urunler)} ürün için ölü/yavaş stok tespit edildi.")

            rows_olu = []
            for u in olu_urunler:
                rows_olu.append({
                    "SKU": u["sku"],
                    "Ürün Adı": u["urun_adi"],
                    "Kategori": u.get("kategori",""),
                    "Marka": u.get("marka",""),
                    "Bizim Stok": u["bizim_stok"],
                    "Ort. Hft. Satış": u.get("ortalama_haftalik_satis", 0),
                    "Stok Yaşı": f"{u['stok_gun']} gün",
                    "Durum": u.get("olu_stok_mesaj",""),
                    "_olu": u.get("olu_stok_durum",""),
                })

            df_olu = pd.DataFrame(rows_olu)

            def olu_rengi(row):
                d = row.get("_olu","")
                if d == "olu": return ["background-color:#FFCCCC"]*len(row)
                if d == "yavas": return ["background-color:#FFE0B2"]*len(row)
                return [""]*len(row)

            goster_olu = ["SKU","Ürün Adı","Kategori","Marka","Bizim Stok","Ort. Hft. Satış","Stok Yaşı","Durum"]
            styled_olu = df_olu[goster_olu+["_olu"]].style.apply(olu_rengi, axis=1)
            styled_olu = styled_olu.hide(axis="columns", subset=["_olu"])
            st.dataframe(styled_olu, use_container_width=True, height=400)

            st.markdown("""
            <div class="uyari-box">
            💡 <b>Öneri:</b> Ölü stok ürünler için indirim kampanyası, paket satış veya muadil ürünle birlikte promosyon değerlendirilebilir.
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 3: Kategori Analizi ──
    with atab3:
        kategori_ozet = analiz["kategori_ozet"]
        if not kategori_ozet:
            st.info("Kategori verisi bulunamadı.")
        else:
            df_kat = pd.DataFrame([{
                "Kategori": k,
                "Ürün Sayısı": v["urun_sayisi"],
                "Toplam Stok": v["toplam_stok"],
                "Ort. Hft. Satış": round(v["toplam_satis"], 1),
                "Acil Sipariş": v["acil_sayisi"],
                "Ölü/Yavaş Stok": v["olu_sayisi"],
                "Ort. Risk Skoru": v["ort_risk"],
            } for k, v in kategori_ozet.items()]).sort_values("Ort. Risk Skoru", ascending=False)

            st.dataframe(df_kat, use_container_width=True, hide_index=True)

            # Grafik
            if len(df_kat) > 1:
                fig_kat = px.bar(
                    df_kat, x="Kategori", y="Ort. Hft. Satış",
                    color="Ort. Risk Skoru",
                    color_continuous_scale=["#C8E6C9","#FFF9C4","#FFE0B2","#FFCCCC"],
                    title="Kategori Bazında Haftalık Satış & Risk",
                    height=350,
                )
                fig_kat.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_kat, use_container_width=True)

    # ── TAB 4: Marka Analizi ──
    with atab4:
        marka_ozet = analiz["marka_ozet"]
        if not marka_ozet:
            st.info("Marka verisi bulunamadı.")
        else:
            df_marka = pd.DataFrame([{
                "Marka": m,
                "Ürün Sayısı": v["urun_sayisi"],
                "Ort. Hft. Satış": round(v["toplam_satis"], 1),
                "Acil Sipariş": v["acil_sayisi"],
            } for m, v in marka_ozet.items()]).sort_values("Ort. Hft. Satış", ascending=False)

            col_m1, col_m2 = st.columns([1, 1])
            with col_m1:
                st.dataframe(df_marka, use_container_width=True, hide_index=True)
            with col_m2:
                if len(df_marka) > 1:
                    fig_marka = px.pie(
                        df_marka, names="Marka", values="Ort. Hft. Satış",
                        title="Marka Bazında Satış Dağılımı",
                        height=350,
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig_marka.update_layout(paper_bgcolor="white")
                    st.plotly_chart(fig_marka, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# 4) KAR MARJI ANALİZİ
# ════════════════════════════════════════════════════════════════════
elif sayfa == "💰  Kar Marjı":
    st.markdown('<div class="baslik">💰 Kar Marjı Analizi</div>', unsafe_allow_html=True)
    st.markdown('<div class="alt-baslik">Ürün bazında karlılık, stok değeri ve hedef karşılaştırması</div>', unsafe_allow_html=True)

    try:
        kar_data = kar_marji_analizi()
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        st.stop()

    fiyatli = [u for u in kar_data if u["kar_marji"] is not None]

    if not fiyatli:
        st.info("Henüz fiyat verisi girilmemiş. G5F STOK Excel sekmesine 'Satış Fiyatı' ve 'Alış Fiyatı' kolonlarını ekleyip yükleyin.")
        st.markdown("""
        **Şablondaki G5F STOK sekmesine şu kolonlar eklenmiştir:**
        - **Satış Fiyatı (₺)** — müşteriye satış fiyatı
        - **Alış Fiyatı (₺)** — üreticiden alış maliyeti
        - **Hedef Kar Marjı (%)** — örn: 30 (yüzde olarak)
        """)
        st.stop()

    # Özet metrikler
    toplam_stok_degeri = sum(u["stok_degeri_satis"] for u in fiyatli)
    toplam_maliyet = sum(u["stok_degeri_maliyet"] for u in fiyatli)
    toplam_potansiyel_kar = sum(u["potansiyel_kar"] for u in fiyatli)
    ort_marj = sum(u["kar_marji"] for u in fiyatli) / len(fiyatli)
    zarar_sayisi = sum(1 for u in fiyatli if u["kar_marji_durum"] == "zarar")
    dusuk_sayisi = sum(1 for u in fiyatli if u["kar_marji_durum"] == "dusuk")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📦 Stok Değeri (Satış)", f"₺{toplam_stok_degeri:,.0f}")
    m2.metric("💸 Toplam Maliyet", f"₺{toplam_maliyet:,.0f}")
    m3.metric("💰 Potansiyel Kar", f"₺{toplam_potansiyel_kar:,.0f}")
    m4.metric("📊 Ort. Kar Marjı", f"%{ort_marj:.1f}")
    m5.metric("⚠️ Zarar/Düşük Marj", f"{zarar_sayisi + dusuk_sayisi} ürün",
              delta="Dikkat" if zarar_sayisi > 0 else None, delta_color="inverse")

    if zarar_sayisi > 0:
        st.error(f"🚨 {zarar_sayisi} ürün zarar marjında satılıyor! Fiyatlandırmayı kontrol edin.")

    st.markdown("---")

    ktab1, ktab2, ktab3 = st.tabs([
        "📋 Ürün Bazında Kar Marjı",
        "🎯 Hedef Karşılaştırması",
        "📊 Stok Değer Analizi",
    ])

    with ktab1:
        rows_kar = []
        for u in sorted(fiyatli, key=lambda x: x["kar_marji"] or 0):
            rows_kar.append({
                "SKU": u["sku"],
                "Ürün Adı": u["urun_adi"],
                "Kategori": u.get("kategori",""),
                "Marka": u.get("marka",""),
                "Alış Fiyatı (₺)": f"₺{u['alis_fiyati']:,.0f}" if u['alis_fiyati'] else "—",
                "Satış Fiyatı (₺)": f"₺{u['satis_fiyati']:,.0f}" if u['satis_fiyati'] else "—",
                "Kar Marjı (%)": f"%{u['kar_marji']:.1f}" if u['kar_marji'] is not None else "—",
                "Durum": {"yuksek":"🟢 Yüksek","normal":"🟡 Normal","dusuk":"🟠 Düşük","zarar":"🔴 ZARAR"}.get(u["kar_marji_durum"],"—"),
                "_renk": u["kar_marji_renk"],
            })

        df_kar = pd.DataFrame(rows_kar)

        def kar_rengi(row):
            renk_map = {"yesil":"#C8E6C9","sari":"#FFF9C4","turuncu":"#FFE0B2","kirmizi":"#FFCCCC","yok":""}
            r = renk_map.get(row.get("_renk",""), "")
            return [f"background-color:{r}" if r else "" for _ in row]

        goster_kar = ["SKU","Ürün Adı","Kategori","Marka","Alış Fiyatı (₺)","Satış Fiyatı (₺)","Kar Marjı (%)","Durum"]
        styled_kar = df_kar[goster_kar+["_renk"]].style.apply(kar_rengi, axis=1)
        styled_kar = styled_kar.hide(axis="columns", subset=["_renk"])
        st.dataframe(styled_kar, use_container_width=True, height=450)

        # Bar grafik
        df_grafik = pd.DataFrame([{
            "Ürün": u["urun_adi"][:20],
            "Kar Marjı (%)": round(u["kar_marji"], 1),
            "Renk": {"yuksek":"#388E3C","normal":"#F9A825","dusuk":"#EF6C00","zarar":"#C62828"}.get(u["kar_marji_durum"],"#888")
        } for u in fiyatli if u["kar_marji"] is not None])

        if len(df_grafik) > 0:
            fig_kar = go.Figure(go.Bar(
                x=df_grafik["Ürün"],
                y=df_grafik["Kar Marjı (%)"],
                marker_color=df_grafik["Renk"],
                text=df_grafik["Kar Marjı (%)"].apply(lambda x: f"%{x:.1f}"),
                textposition="outside",
            ))
            fig_kar.update_layout(
                title="Ürün Bazında Kar Marjı",
                xaxis_title="Ürün", yaxis_title="Kar Marjı (%)",
                height=380, plot_bgcolor="white", paper_bgcolor="white",
            )
            fig_kar.add_hline(y=0, line_color="red", line_dash="dash", annotation_text="Başabaş")
            st.plotly_chart(fig_kar, use_container_width=True)

    with ktab2:
        hedefli = [u for u in fiyatli if u.get("hedef_kar_marji", 0) > 0]
        if not hedefli:
            st.info("Hedef kar marjı girilmemiş. G5F STOK sekmesindeki 'Hedef Kar Marjı (%)' kolonunu doldurun.")
        else:
            rows_hedef = []
            for u in hedefli:
                fark = (u["kar_marji"] or 0) - u["hedef_kar_marji"]
                rows_hedef.append({
                    "SKU": u["sku"],
                    "Ürün Adı": u["urun_adi"],
                    "Hedef Marj (%)": f"%{u['hedef_kar_marji']:.1f}",
                    "Gerçek Marj (%)": f"%{u['kar_marji']:.1f}" if u['kar_marji'] is not None else "—",
                    "Fark": f"{fark:+.1f}%",
                    "Durum": {"hedef_ustu":"✅ Hedefe Ulaştı","hedefe_yakin":"⚠️ Hedefe Yakın","hedefin_altinda":"❌ Hedefin Altında"}.get(u["hedef_durum"],"—"),
                    "_hd": u["hedef_durum"],
                })

            df_hedef = pd.DataFrame(rows_hedef)
            def hedef_rengi(row):
                d = row.get("_hd","")
                if d == "hedef_ustu": return ["background-color:#C8E6C9"]*len(row)
                if d == "hedefe_yakin": return ["background-color:#FFF9C4"]*len(row)
                if d == "hedefin_altinda": return ["background-color:#FFCCCC"]*len(row)
                return [""]*len(row)

            goster_h = ["SKU","Ürün Adı","Hedef Marj (%)","Gerçek Marj (%)","Fark","Durum"]
            styled_h = df_hedef[goster_h+["_hd"]].style.apply(hedef_rengi, axis=1)
            styled_h = styled_h.hide(axis="columns", subset=["_hd"])
            st.dataframe(styled_h, use_container_width=True, height=400)

    with ktab3:
        st.markdown("**Depodaki stoğun toplam değeri (satış ve maliyet bazında)**")

        rows_deger = sorted([{
            "SKU": u["sku"],
            "Ürün Adı": u["urun_adi"],
            "Stok Adedi": u["bizim_stok"],
            "Stok Değeri (Satış ₺)": u["stok_degeri_satis"],
            "Stok Maliyeti (₺)": u["stok_degeri_maliyet"],
            "Potansiyel Kar (₺)": u["potansiyel_kar"],
            "Kar Marjı (%)": round(u["kar_marji"],1) if u["kar_marji"] else 0,
        } for u in fiyatli], key=lambda x: x["Potansiyel Kar (₺)"], reverse=True)

        df_deger = pd.DataFrame(rows_deger)
        for col in ["Stok Değeri (Satış ₺)","Stok Maliyeti (₺)","Potansiyel Kar (₺)"]:
            df_deger[col] = df_deger[col].apply(lambda x: f"₺{x:,.0f}")

        st.dataframe(df_deger, use_container_width=True, hide_index=True, height=400)

        # Pasta grafik — stok değeri dağılımı
        df_pasta = pd.DataFrame([{"Ürün": u["urun_adi"][:20], "Değer": u["stok_degeri_satis"]}
                                  for u in fiyatli if u["stok_degeri_satis"] > 0])
        if len(df_pasta) > 0:
            fig_pasta = px.pie(df_pasta, names="Ürün", values="Değer",
                               title="Stok Değer Dağılımı (Satış Fiyatı Bazlı)",
                               height=350, color_discrete_sequence=px.colors.qualitative.Set3)
            fig_pasta.update_layout(paper_bgcolor="white")
            st.plotly_chart(fig_pasta, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# 5) SATIN ALMA GEÇMİŞİ
# ════════════════════════════════════════════════════════════════════
elif sayfa == "🛒  Satın Alma Geçmişi":
    st.markdown('<div class="baslik">🛒 Satın Alma Geçmişi</div>', unsafe_allow_html=True)
    st.markdown('<div class="alt-baslik">Tedarikçi, adet, alış fiyatı ve gerçek maliyet takibi</div>', unsafe_allow_html=True)

    # Ürün listesini veritabanından al
    from database import get_connection as _gc
    def _get_urunler():
        c = _gc(); cur = c.cursor()
        cur.execute("SELECT sku, urun_adi FROM urunler ORDER BY urun_adi")
        rows = [dict(r) for r in cur.fetchall()]; c.close(); return rows
    urun_listesi = _get_urunler()

    stab1, stab2, stab3 = st.tabs(["➕ Yeni Satın Alma Ekle", "📋 Tüm Geçmiş", "📊 Özet Rapor"])

    with stab1:
        st.subheader("Yeni Satın Alma Kaydı")
        if not urun_listesi:
            st.warning("Önce 'Veri Yükleme' sekmesinden ürün yükleyin.")
        else:
            sku_secenekler = {f"{u['sku']} — {u['urun_adi']}": u['sku'] for u in urun_listesi}
            onceki_tedarikciler = get_tum_tedarikciler()

            with st.form("satin_alma_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    secim = st.selectbox("Ürün *", list(sku_secenekler.keys()))
                    tedarikci = st.text_input("Tedarikçi / Üretici *",
                        placeholder="örn: ABC Elektronik Ltd.",
                        help=f"Önceki tedarikçiler: {', '.join(onceki_tedarikciler[:5])}" if onceki_tedarikciler else "")
                    satin_alma_tarihi = st.date_input("Satın Alma Tarihi *", value=date.today())
                    notlar = st.text_area("Notlar (opsiyonel)", placeholder="Sipariş no, kargo firması...")

                with col2:
                    adet = st.number_input("Adet *", min_value=1, value=100, step=1)
                    birim_alis = st.number_input("Birim Alış Fiyatı (₺) *", min_value=0.0, value=0.0, step=0.01, format="%.2f",
                        help="Üreticiye ödenen birim fiyat")
                    maliyet_yuzdesi = st.number_input(
                        "Ek Maliyet Yüzdesi (%) *",
                        min_value=0.0, max_value=200.0, value=0.0, step=0.5, format="%.1f",
                        help="Nakliye + gümrük + diğer masrafların alış fiyatına oranı. Örn: %20 → ₺100 alış + %20 = ₺120 toplam maliyet")

                    # Canlı hesaplama
                    if birim_alis > 0:
                        toplam_birim = birim_alis * (1 + maliyet_yuzdesi / 100)
                        toplam_siparis = toplam_birim * adet
                        st.markdown(f"""
                        <div class="info-box">
                        💡 <b>Hesaplama:</b><br>
                        Birim alış: ₺{birim_alis:,.2f}<br>
                        Ek maliyet (+%{maliyet_yuzdesi:.1f}): ₺{birim_alis * maliyet_yuzdesi/100:,.2f}<br>
                        <b>Birim toplam maliyet: ₺{toplam_birim:,.2f}</b><br>
                        <b>Toplam sipariş maliyeti: ₺{toplam_siparis:,.0f}</b>
                        </div>
                        """, unsafe_allow_html=True)

                submitted = st.form_submit_button("💾 Kaydet", type="primary", use_container_width=True)

            if submitted:
                if not tedarikci.strip():
                    st.error("Tedarikçi adı zorunludur.")
                elif birim_alis <= 0:
                    st.error("Birim alış fiyatı girilmesi zorunludur.")
                else:
                    secilen_sku = sku_secenekler[secim]
                    urun_adi = next(u["urun_adi"] for u in urun_listesi if u["sku"] == secilen_sku)
                    ekle_satin_alma(secilen_sku, urun_adi, tedarikci.strip(),
                                    str(satin_alma_tarihi), adet, birim_alis,
                                    maliyet_yuzdesi, notlar.strip())
                    birim_mal = birim_alis * (1 + maliyet_yuzdesi / 100)
                    st.success(f"✅ Kayıt eklendi! {urun_adi} — {adet} adet | Birim maliyet: ₺{birim_mal:,.2f}")
                    st.rerun()

    with stab2:
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filtre_sku = st.selectbox("Ürün Filtresi",
                ["Tüm Ürünler"] + [f"{u['sku']} — {u['urun_adi']}" for u in urun_listesi],
                key="gecmis_filtre")
        with col_f2:
            ara = st.text_input("Tedarikçi ara...", key="tedarikci_ara")

        if filtre_sku == "Tüm Ürünler":
            kayitlar = get_satin_alma_gecmisi()
        else:
            secilen_sku_f = filtre_sku.split(" — ")[0]
            kayitlar = get_satin_alma_gecmisi(secilen_sku_f)

        if ara:
            kayitlar = [k for k in kayitlar if ara.lower() in (k.get("tedarikci","") or "").lower()]

        if not kayitlar:
            st.info("Kayıt bulunamadı. 'Yeni Satın Alma Ekle' sekmesinden kayıt girebilirsiniz.")
        else:
            tm1, tm2, tm3, tm4 = st.columns(4)
            tm1.metric("📋 Toplam Sipariş", len(kayitlar))
            tm2.metric("📦 Toplam Adet", f"{sum(k['adet'] for k in kayitlar):,}")
            tm3.metric("💸 Toplam Maliyet (Alış)", f"₺{sum((k['alis_fiyati'] or 0)*k['adet'] for k in kayitlar):,.0f}")
            tm4.metric("💰 Toplam Maliyet (Gerçek)", f"₺{sum(k['toplam_maliyet'] or 0 for k in kayitlar):,.0f}")

            st.markdown("---")

            rows_s = []
            for k in kayitlar:
                birim_mal = k.get("toplam_maliyet", 0) / k["adet"] if k["adet"] > 0 else 0
                rows_s.append({
                    "ID": k["id"],
                    "Tarih": k.get("satin_alma_tarihi",""),
                    "SKU": k["sku"],
                    "Ürün Adı": k.get("urun_adi",""),
                    "Tedarikçi": k.get("tedarikci",""),
                    "Adet": k["adet"],
                    "Birim Alış (₺)": f"₺{k['alis_fiyati']:,.2f}" if k.get("alis_fiyati") else "—",
                    "Ek Maliyet (%)": f"%{k['maliyet_yuzdesi']:.1f}" if k.get("maliyet_yuzdesi") else "%0",
                    "Birim Toplam Maliyet (₺)": f"₺{birim_mal:,.2f}" if birim_mal else "—",
                    "Toplam Sipariş Mal. (₺)": f"₺{k['toplam_maliyet']:,.0f}" if k.get("toplam_maliyet") else "—",
                    "Notlar": k.get("notlar","") or "",
                })

            df_s = pd.DataFrame(rows_s)
            st.dataframe(df_s.drop(columns=["ID"]), use_container_width=True, height=420, hide_index=True)

            with st.expander("🗑️ Kayıt Sil (Yanlış Giriş İçin)"):
                st.caption("Yanlış girilen kayıtları buradan silebilirsiniz.")
                silme_id = st.number_input("Silinecek Kayıt ID", min_value=1, step=1, key="silme_id")
                if st.button("🗑️ Kaydı Sil", type="secondary"):
                    sil_satin_alma(int(silme_id))
                    st.success(f"Kayıt #{silme_id} silindi.")
                    st.rerun()

    with stab3:
        tum_kayitlar = get_satin_alma_gecmisi()
        if not tum_kayitlar:
            st.info("Henüz satın alma kaydı yok.")
        else:
            st.markdown("**Ürün bazında satın alma özeti**")

            # SKU bazında grupla
            from collections import defaultdict
            sku_ozet = defaultdict(lambda: {"urun_adi":"","siparis_sayisi":0,"toplam_adet":0,
                                             "toplam_alis":0,"toplam_maliyet":0,"tedarikciler":set(),
                                             "ilk_tarih":"","son_tarih":""})
            for k in tum_kayitlar:
                s = sku_ozet[k["sku"]]
                s["urun_adi"] = k.get("urun_adi","")
                s["siparis_sayisi"] += 1
                s["toplam_adet"] += k["adet"]
                s["toplam_alis"] += (k.get("alis_fiyati") or 0) * k["adet"]
                s["toplam_maliyet"] += k.get("toplam_maliyet") or 0
                s["tedarikciler"].add(k.get("tedarikci","") or "")
                t = k.get("satin_alma_tarihi","")
                if t:
                    if not s["ilk_tarih"] or t < s["ilk_tarih"]: s["ilk_tarih"] = t
                    if not s["son_tarih"] or t > s["son_tarih"]: s["son_tarih"] = t

            rows_oz = []
            for sku, o in sorted(sku_ozet.items()):
                ort_birim_mal = o["toplam_maliyet"] / o["toplam_adet"] if o["toplam_adet"] else 0
                ort_birim_alis = o["toplam_alis"] / o["toplam_adet"] if o["toplam_adet"] else 0
                rows_oz.append({
                    "SKU": sku,
                    "Ürün Adı": o["urun_adi"],
                    "Sipariş Sayısı": o["siparis_sayisi"],
                    "Toplam Alınan Adet": f"{o['toplam_adet']:,}",
                    "Ort. Birim Alış (₺)": f"₺{ort_birim_alis:,.2f}",
                    "Ort. Birim Maliyet (₺)": f"₺{ort_birim_mal:,.2f}",
                    "Toplam Maliyet (₺)": f"₺{o['toplam_maliyet']:,.0f}",
                    "Tedarikçiler": ", ".join(t for t in o["tedarikciler"] if t),
                    "İlk Satın Alma": o["ilk_tarih"],
                    "Son Satın Alma": o["son_tarih"],
                })

            df_oz = pd.DataFrame(rows_oz)
            st.dataframe(df_oz, use_container_width=True, height=400, hide_index=True)

            # Tedarikçi bazında pasta grafik
            ted_maliyet = {}
            for k in tum_kayitlar:
                t = k.get("tedarikci","Diğer") or "Diğer"
                ted_maliyet[t] = ted_maliyet.get(t,0) + (k.get("toplam_maliyet") or 0)

            if ted_maliyet:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    df_ted = pd.DataFrame([{"Tedarikçi":k,"Toplam Maliyet":v} for k,v in ted_maliyet.items()])
                    fig_ted = px.pie(df_ted, names="Tedarikçi", values="Toplam Maliyet",
                                     title="Tedarikçi Bazında Maliyet Dağılımı",
                                     height=320, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_ted.update_layout(paper_bgcolor="white")
                    st.plotly_chart(fig_ted, use_container_width=True)

                with col_g2:
                    # Ürün bazında maliyet
                    urun_maliyet = {}
                    for k in tum_kayitlar:
                        un = k.get("urun_adi","") or k["sku"]
                        urun_maliyet[un[:20]] = urun_maliyet.get(un[:20],0) + (k.get("toplam_maliyet") or 0)
                    df_um = pd.DataFrame([{"Ürün":k,"Toplam Maliyet":v} for k,v in urun_maliyet.items()])
                    fig_um = px.bar(df_um, x="Ürün", y="Toplam Maliyet",
                                    title="Ürün Bazında Toplam Maliyet",
                                    height=320, color_discrete_sequence=["#1F4E79"])
                    fig_um.update_layout(plot_bgcolor="white", paper_bgcolor="white")
                    st.plotly_chart(fig_um, use_container_width=True)
# ════════════════════════════════════════════════════════════════════
# 6) SİPARİŞ YÖNETİMİ
# ════════════════════════════════════════════════════════════════════
elif sayfa == "📦  Sipariş Yönetimi":
    st.markdown('<div class="baslik">📦 Sipariş Önerisi Yönetimi</div>', unsafe_allow_html=True)

    durum_filtre = st.selectbox("Durum Filtresi", ["Tümü", "beklemede", "onaylandi", "reddedildi"])
    durum_arg = None if durum_filtre == "Tümü" else durum_filtre
    onerileri = get_siparis_onerileri(durum_arg)

    if not onerileri:
        st.info("Henüz sipariş önerisi bulunmuyor.")
    else:
        for sp in onerileri:
            durum_renk = {"beklemede":"🟡","onaylandi":"🟢","reddedildi":"🔴"}.get(sp["durum"],"⚪")
            with st.expander(f"{durum_renk} [{sp['firma']}] {sp.get('urun_adi','') or sp['sku']} — {sp['oneri_miktari']} adet | {sp['olusturma_tarihi']}"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**SKU:** {sp['sku']}")
                col2.write(f"**Miktar:** {sp['oneri_miktari']} adet")
                col3.write(f"**Durum:** {sp['durum']}")

                if sp["durum"] == "beklemede":
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Onayla", key=f"onayla_{sp['id']}", use_container_width=True):
                            onayla_siparis(sp["id"])
                            st.success("Onaylandı!")
                            st.rerun()
                    with c2:
                        if st.button("❌ Reddet", key=f"reddet_{sp['id']}", use_container_width=True):
                            reddet_siparis(sp["id"])
                            st.warning("Reddedildi.")
                            st.rerun()

# ════════════════════════════════════════════════════════════════════
# 7) VERİ YÜKLEME
# ════════════════════════════════════════════════════════════════════
elif sayfa == "📂  Veri Yükleme":
    st.markdown('<div class="baslik">📂 Veri Yükleme Merkezi</div>', unsafe_allow_html=True)

    # Şablon indir
    with st.expander("📋 Excel Şablonunu İndir (ilk kez kullanıyorsanız buradan başlayın)", expanded=False):
        st.write("Aşağıdaki butona tıklayarak örnek şablonu indirin, doldurun ve yükleyin.")
        sablon_bytes = create_sample_excel_bytes()
        st.download_button("📥 Şablonu İndir", sablon_bytes, "SABLON_STOK_TAKIP.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")

    st.subheader("📤 G5F STOK — Haftalık Veri Yükleme")
    st.caption("""Tek Excel dosyasında tüm sekmeler: 
    **G5F STOK** (bizim depo) | **ITOPYA, HB, VATAN, MONDAY, KANAL, DIGER** (firma stokları) | **YOLDAKI** (yoldaki ürünler)""")

    dosya = st.file_uploader("Excel Dosyasını Seç", type=["xlsx","xls"], key="tek_dosya")
    if dosya:
        if st.button("⬆️ Tüm Veriyi Yükle", type="primary", use_container_width=True):
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(dosya.read())
                tmp_path = tmp.name

            sonuclar = []

            # G5F STOK (ana stok)
            basari, mesaj = excel_yukle_ana_stok(tmp_path)
            sonuclar.append(("G5F STOK", basari, mesaj))

            # Firma stokları
            basari2, mesaj2 = excel_yukle_firma_stoklari(tmp_path)
            sonuclar.append(("Firma Stokları", basari2, mesaj2))

            # Yoldaki ürünler
            basari3, mesaj3 = excel_yukle_yoldaki_urunler(tmp_path)
            sonuclar.append(("Yoldaki Ürünler", basari3, mesaj3))

            os.unlink(tmp_path)

            for baslik, basari, mesaj in sonuclar:
                if basari:
                    st.success(f"**{baslik}:** {mesaj}")
                else:
                    st.warning(f"**{baslik}:** {mesaj}")

    st.markdown("---")
    st.markdown("""
    **📋 Excel Sekme Yapısı:**
    | Sekme | İçerik | Kolonlar |
    |-------|--------|----------|
    | G5F STOK | Bizim depo stoğumuz | SKU, Ürün Adı, Kategori, Marka, Fiyat, Özellikler, Bizim Stok, Trendyol Stok |
    | ITOPYA / HB / VATAN / MONDAY / KANAL / DIGER | Firma stokları | SKU, Ürün Adı, Stok Miktarı, Haftalık Satış |
    | YOLDAKI | Yoldaki ürünler | SKU, Ürün Adı, Yoldaki Miktar, Tahmini Varış Tarihi |
    """)


# ════════════════════════════════════════════════════════════════════
# 8) RAPORLAR
# ════════════════════════════════════════════════════════════════════
elif sayfa == "📄  Raporlar":
    st.markdown('<div class="baslik">📄 Rapor Oluşturma</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Excel Raporu")
        st.write("Dashboard, Stok Yayılımı ve Sipariş Önerileri — 3 sekme, renkli, tam detaylı.")
        if st.button("📊 Excel Raporu Oluştur", use_container_width=True, type="primary"):
            from rapor import excel_rapor_olustur
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp_path = tmp.name
            basari, mesaj = excel_rapor_olustur(tmp_path)
            if basari:
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "⬇️ Excel İndir",
                        f.read(),
                        f"Stok_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                os.unlink(tmp_path)
            else:
                st.error(mesaj)

    with col2:
        st.subheader("📑 PDF Raporu")
        st.write("A4 yatay formatta yazdırmaya hazır özet rapor.")
        if st.button("📑 PDF Raporu Oluştur", use_container_width=True):
            from rapor import pdf_rapor_olustur
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp_path = tmp.name
            basari, mesaj = pdf_rapor_olustur(tmp_path)
            if basari:
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "⬇️ PDF İndir",
                        f.read(),
                        f"Stok_Raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                os.unlink(tmp_path)
            else:
                st.error(mesaj)

# ════════════════════════════════════════════════════════════════════
# 9) BİLDİRİM AYARLARI
# ════════════════════════════════════════════════════════════════════
elif sayfa == "🔔  Bildirim Ayarları":
    st.markdown('<div class="baslik">🔔 Bildirim Ayarları</div>', unsafe_allow_html=True)
    st.markdown('<div class="alt-baslik">Günlük e-posta bildirimi için SMTP ayarlarını yapın</div>', unsafe_allow_html=True)

    mevcut = get_bildirim_ayarlari()

    with st.expander("📧 E-posta Ayarları", expanded=True):
        st.caption("Gmail kullanıyorsanız: smtp_host=smtp.gmail.com, port=587, uygulama şifresi gereklidir.")

        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Bildirim Gönderilecek E-posta", value=mevcut.get("email","") if mevcut else "")
            smtp_host = st.text_input("SMTP Host", value=mevcut.get("smtp_host","smtp.gmail.com") if mevcut else "smtp.gmail.com")
            smtp_port = st.number_input("SMTP Port", value=int(mevcut.get("smtp_port",587)) if mevcut else 587)
        with col2:
            smtp_user = st.text_input("SMTP Kullanıcı (Gönderen E-posta)", value=mevcut.get("smtp_user","") if mevcut else "")
            smtp_pass = st.text_input("SMTP Şifre / Uygulama Şifresi", type="password", value=mevcut.get("smtp_pass","") if mevcut else "")
            aktif = st.checkbox("Günlük bildirimleri aktif et", value=bool(mevcut.get("aktif",0)) if mevcut else False)

        if mevcut and mevcut.get("son_gonderim"):
            st.info(f"Son gönderim: {mevcut['son_gonderim']}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Ayarları Kaydet", type="primary", use_container_width=True):
                if email and smtp_user and smtp_pass:
                    kaydet_bildirim_ayarlari(email, smtp_host, smtp_port, smtp_user, smtp_pass, int(aktif))
                    st.success("Ayarlar kaydedildi!")
                else:
                    st.error("E-posta, kullanıcı adı ve şifre zorunludur.")
        with col_b:
            if st.button("📧 Test E-postası Gönder", use_container_width=True):
                veri = dashboard_hesapla()
                ok, msg = email_gonder(veri)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("---")
    st.subheader("📋 Sipariş Takvimi Özeti")
    st.caption("Tüm ürünlerin sipariş durumu — 135 gün üretim süresi baz alınarak hesaplanmıştır.")

    try:
        veri = dashboard_hesapla()
        # Ürün başına tek satır (firma tekrarı olmasın)
        sku_goruldu = set()
        ozetler = []
        for u in veri:
            if u["sku"] not in sku_goruldu:
                sku_goruldu.add(u["sku"])
                ozetler.append(u)

        durum_sirasi = {"acil": 0, "yaklasıyor": 1, "planlama": 2, "normal": 3, "veri_yok": 4}
        ozetler.sort(key=lambda x: durum_sirasi.get(x.get("siparis_durum","veri_yok"), 4))

        df_ozet = pd.DataFrame([{
            "SKU": u["sku"],
            "Ürün Adı": u["urun_adi"],
            "Bizim Stok": u["bizim_stok"],
            "Hft. Satış": u.get("toplam_haftalik_satis", 0),
            "Stok Biter (Gün)": u.get("stok_bitis_gun", "-") or "-",
            "Sipariş Son Gün": u.get("siparis_son_gun", "-") or "-",
            "Durum": u.get("siparis_mesaj", "—"),
        } for u in ozetler])

        def ozet_rengi(row):
            durum = row.get("Durum","")
            if "ACİL" in str(durum): return ["background-color:#FFCCCC"]*len(row)
            if "🟠" in str(durum): return ["background-color:#FFE0B2"]*len(row)
            if "🟡" in str(durum): return ["background-color:#FFF9C4"]*len(row)
            if "🟢" in str(durum): return ["background-color:#E8F5E9"]*len(row)
            return [""]*len(row)

        st.dataframe(df_ozet.style.apply(ozet_rengi, axis=1), use_container_width=True, height=400)
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")

