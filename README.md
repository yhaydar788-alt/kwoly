# Kwoly – Teklif Motoru

Okunuşu: "kuo-li". Müşteri bilgisi bir kez girilir, tüm sigorta şirketlerinden
paralel teklif alınır, sonuçlar canlı olarak en ucuzdan pahalıya gösterilir.

## Çalıştırma
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    # tarayıcı: http://localhost:8000   ·   API dokümanı: http://localhost:8000/docs

## Yapı
    sirketler.json              Hangi şirketler aktif, hangi yöntemle (demo/api/robot), ön sorgu sırası
    app/main.py                 Kwoly API uçları
    app/kasa.py                 Şifreli kasa (şirket kullanıcı adı/şifreleri)
    app/oturum.py               Şirket oturumları, aynı anda tek giriş kilidi, SMS kodu aracısı
    app/gecmis.py               Sorgu geçmişi (SQLite, TC maskeli) + Excel (CSV) çıktısı
    app/adapters/base.py        Tüm şirket bağlantılarının ortak arayüzü
    app/adapters/demo.py        Demo şirketler (DEMO SMS: kod 123456)
    app/adapters/ornek_api.py   ŞABLON: web servisi olan şirket
    app/adapters/ornek_robot.py ŞABLON: portalı robotla dolduran şirket
    static/index.html           Arayüz
    data/                       Kasa, anahtar, oturumlar, veritabanı (git'e girmez)

## Şifre kasası
    python -m app.kasa ekle "ALLIANZ" kullanici=... sifre=... portal_url=https://...
    python -m app.kasa liste          # sadece alan adlarını gösterir, şifreleri değil
    python -m app.kasa sil "ALLIANZ"
Anahtar `KWOLY_ANAHTAR` ortam değişkeninden okunur; yoksa geliştirme için
`data/.anahtar` üretilir. Canlıda anahtar mutlaka ortam değişkeni / KMS'te tutulmalı.

## SMS doğrulaması
Robot SMS koduna ihtiyaç duyunca `ortam.kod_iste()` çağırır. Arayüzün sağ altında
şirket adıyla bir kart çıkar, kullanıcı kodu girer, robot devam eder (180 sn süre).
Oturum `data/oturumlar/` altında saklanır; oturum açık kaldıkça SMS tekrar istenmez.

## Yeni şirket ekleme
1. `ornek_robot.py` (veya `ornek_api.py`) kopyalanır, seçiciler/alanlar şirkete göre doldurulur.
2. `main.py` içindeki `ADAPTERLER` sözlüğüne kaydedilir.
3. `sirketler.json`'a eklenir, kimlikleri kasaya girilir.

## API (dış sistemler için)
    POST /api/on-sorgu              plaka+TC → araç bilgisi (sıradaki şirketlerden)
    POST /api/teklif                tüm şirketlerden tek çağrıda teklif
    POST /api/sorgu + /api/teklif/{şirket}?sorgu_id=   canlı akış (arayüz bunu kullanır)
    GET  /api/kod  ·  POST /api/kod/{no}               bekleyen SMS kodları
    GET  /api/gecmis  ·  /api/gecmis/{id}  ·  /api/gecmis/{id}/excel

## KVKK notları
- TC/VKN geçmişte maskeli tutulur (12*******01).
- Şifreler yalnızca şifreli kasada; kod ve loglarda yer almaz.
