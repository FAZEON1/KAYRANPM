# Streamlit Cloud — Kullanıcı Şifresi Kurulum Kılavuzu

## Adım 1 — Streamlit Cloud'a giriş yap
https://share.streamlit.io adresine git ve hesabına gir.

## Adım 2 — Uygulamanı bul
Uygulamanın yanındaki **"⋮"** (üç nokta) → **"Settings"** tıkla.

## Adım 3 — Secrets bölümüne git
Sol menüden **"Secrets"** sekmesine tıkla.

## Adım 4 — Kullanıcıları ekle
Aşağıdaki formatı kopyalayıp yapıştır ve kendi kullanıcı adı/şifrelerini yaz:

```toml
[kullanicilar]
ibrahim = "sifreniz123"
ekip_uyesi = "baska_sifre456"
ahmet = "ahmet_sifre789"
```

## Adım 5 — Kaydet
**"Save"** butonuna tıkla. Streamlit uygulamayı otomatik yeniden başlatır.

## Artık hazır!
Program açılınca giriş ekranı çıkacak.
Kullanıcı adı ve şifreyi girdikten sonra program açılır.

---

## Notlar
- Şifreler GitHub'a **YÜKLENMEZ** — tamamen güvenli.
- İstediğin zaman yeni kullanıcı ekleyebilir veya şifre değiştirebilirsin.
- Kullanıcı adları Türkçe karakter içermemeli (ibrahim ✅, İbrahim ❌).
