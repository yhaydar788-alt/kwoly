"""Anadolu Sigorta bağlantısı (TASLAK).

Durum: Portal akışı henüz kayıt altına alınmadı. Aşağıdaki seçiciler ve adresler
YER TUTUCUDUR; acentenin portaldan aldığı ekran görüntüleri / temizlenmiş HAR
kaydı geldikten sonra doldurulacak.

Hedef yöntem sırası:
  1) Anadolu Sigorta'nın acentelere verdiği web servis (varsa)  → yontem = "API"
  2) Portalın kendi iç (XHR/JSON) istekleri                     → yontem = "API"
  3) Portal robotu (aşağıdaki sınıf)                            → yontem = "ROBOT"

Kasa:  python -m app.kasa ekle "ANADOLU" kullanici=... sifre=... portal_url=https://...
"""
from .ornek_robot import OrnekRobotAdapter


class AnadoluRobotAdapter(OrnekRobotAdapter):
    yontem = "ROBOT"
    desteklenen_branslar = ("TRAFIK",)      # kasko ikinci aşamada

    # TODO: Portal incelendikten sonra OrnekRobotAdapter'daki adımlar
    # (_giris_gerekli_mi, _giris_yap, teklif_al) burada Anadolu'ya özel yazılacak.
