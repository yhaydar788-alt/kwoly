"""Her sigorta şirketi için bir 'adapter' yazılır.

Adapter iki türden biri olur:
  - API adapter  : Şirketin acentelere verdiği web servise (SOAP/REST) bağlanır.
  - ROBOT adapter: Şirketin acente portalını tarayıcıyla açıp formu doldurur.

İkisi de aynı arayüzü uygular; sistemin geri kalanı farkı bilmez.
"""
from abc import ABC, abstractmethod
from ..models import TeklifIstegi, TeklifSonucu


class SirketAdapter(ABC):
    ad: str = "TANIMSIZ"
    yontem: str = "ROBOT"
    desteklenen_branslar: tuple = ("TRAFIK",)

    def __init__(self, ad: str, kimlik: dict, ortam=None):
        # ad     : sirketler.json'daki görünen ad
        # kimlik : kasadan gelen kullanıcı adı/şifre, API anahtarı vb.
        # ortam  : OturumYoneticisi (oturum dosyası, kilit, SMS kodu isteme)
        self.ad = ad
        self.kimlik = kimlik
        self.ortam = ortam

    @abstractmethod
    async def teklif_al(self, istek: TeklifIstegi) -> TeklifSonucu:
        ...

    async def on_sorgu(self, istek: TeklifIstegi) -> dict:
        """Plaka + TC ile araç/sahip bilgisini getirir (şirket SBM'den çeker).
        Desteklemeyen adapter boş döner."""
        return {}
