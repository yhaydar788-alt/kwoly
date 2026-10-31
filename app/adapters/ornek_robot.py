"""ŞABLON: API'si olmayan bir şirket için portal robotu (Playwright).

Seçiciler (#kullanici, #plaka ...) şirketin portalı incelenerek (F12 > Elements)
doldurulur. Portal değişince yalnızca bu dosya güncellenir.

Kurulum:  pip install playwright && playwright install chromium
Kasa:     python -m app.kasa ekle "SIRKET_X" kullanici=... sifre=... portal_url=https://...
"""
import os
import time
from .base import SirketAdapter
from ..models import TeklifIstegi, TeklifSonucu


class OrnekRobotAdapter(SirketAdapter):
    yontem = "ROBOT"

    async def _giris_gerekli_mi(self, s) -> bool:
        return await s.locator("#kullanici").count() > 0

    async def _giris_yap(self, s):
        await s.fill("#kullanici", self.kimlik["kullanici"])
        await s.fill("#sifre", self.kimlik["sifre"])
        await s.click("#giris")
        if await s.locator("#smsKodu").count():               # SMS doğrulaması
            kod = await self.ortam.kod_iste(self.ad, f"{self.ad} portalına gelen SMS kodunu girin")
            await s.fill("#smsKodu", kod)
            await s.click("#smsOnay")

    async def teklif_al(self, istek: TeklifIstegi) -> TeklifSonucu:
        from playwright.async_api import async_playwright
        t0 = time.time()
        oturum = self.ortam.oturum_dosyasi(self.ad)
        try:
            async with async_playwright() as p:
                tarayici = await p.chromium.launch(headless=True)
                ctx = await tarayici.new_context(storage_state=oturum if os.path.exists(oturum) else None)
                s = await ctx.new_page()
                await s.goto(self.kimlik["portal_url"])

                if await self._giris_gerekli_mi(s):
                    async with self.ortam.kilit(self.ad):     # aynı anda tek giriş
                        await self._giris_yap(s)
                        await ctx.storage_state(path=oturum)

                await s.click("text=Trafik Teklifi")
                await s.fill("#plaka", istek.plaka)
                await s.fill("#tckn", istek.tc_vkn)
                await s.fill("#belgeSeri", istek.belge_seri)
                await s.fill("#belgeNo", istek.belge_no)
                await s.click("#sorgula")                      # şirket SBM'den aracı getirir
                await s.click("#teklifHesapla")

                fiyat_metni = await s.locator("#brutPrim").inner_text(timeout=90_000)
                teklif_no = await s.locator("#teklifNo").inner_text()
                await ctx.storage_state(path=oturum)
                await tarayici.close()

            fiyat = float(fiyat_metni.replace(".", "").replace(",", ".").replace("TL", "").strip())
            return TeklifSonucu(self.ad, self.yontem, "OK", fiyat=fiyat, teklif_no=teklif_no,
                                sure_sn=round(time.time() - t0, 1))
        except Exception as e:
            return TeklifSonucu(self.ad, self.yontem, "HATA", mesaj=str(e)[:200],
                                sure_sn=round(time.time() - t0, 1))
