"""Gerçek bağlantı olmadan arayüzü ve akışı denemek için sahte şirketler."""
import asyncio
import random
from .base import SirketAdapter
from ..models import TeklifIstegi, TeklifSonucu


class DemoAdapter(SirketAdapter):
    yontem = "DEMO"
    desteklenen_branslar = ("TRAFIK", "KASKO")

    async def on_sorgu(self, istek):
        await asyncio.sleep(0.3)
        return {"marka": "DEMO MARKA", "model": "DEMO MODEL",
                "model_yili": "2019", "kullanim_tarzi": "HUSUSI OTOMOBIL"}

    async def teklif_al(self, istek: TeklifIstegi) -> TeklifSonucu:
        await asyncio.sleep(random.uniform(0.5, 2.5))
        if random.random() < 0.1:
            return TeklifSonucu(self.ad, self.yontem, "HATA", mesaj="Portal yanıt vermedi (demo)")
        taban = 9000 if istek.brans == "TRAFIK" else 25000
        fiyat = round(taban * random.uniform(0.8, 1.4), 2)
        return TeklifSonucu(self.ad, self.yontem, "OK", fiyat=fiyat,
                            komisyon=round(fiyat * 0.08, 2),
                            teklif_no=f"D{random.randint(100000, 999999)}")


class DemoSmsAdapter(DemoAdapter):
    """İlk sorguda SMS kodu ister (demo kodu: 123456). Kod bir kez girilince
    oturum açık kalır; gerçek robotlardaki akışı taklit eder."""

    _oturum_acik = False

    async def teklif_al(self, istek):
        async with self.ortam.kilit(self.ad):
            if not self._oturum_acik:
                kod = await self.ortam.kod_iste(self.ad, "Demo SMS kodu: 123456")
                if kod != "123456":
                    return TeklifSonucu(self.ad, self.yontem, "HATA", mesaj="SMS kodu hatalı")
                self._oturum_acik = True
        return await super().teklif_al(istek)
