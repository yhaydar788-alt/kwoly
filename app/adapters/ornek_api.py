"""ŞABLON: Web servis (API) veren bir şirket için adapter.

Şirketten alınacak entegrasyon dokümanına göre URL, alan adları ve
kimlik doğrulama doldurulur. Aşağıdaki alan adları örnektir.
"""
import time
from .base import SirketAdapter
from ..models import TeklifIstegi, TeklifSonucu


class OrnekApiAdapter(SirketAdapter):
    yontem = "API"

    async def teklif_al(self, istek: TeklifIstegi) -> TeklifSonucu:
        import httpx  # yalnızca API adapter kullanılınca gerekir
        t0 = time.time()
        govde = {  # Şirketin dokümanındaki şemaya göre düzenlenecek
            "plate": istek.plaka,
            "identityNo": istek.tc_vkn,
            "documentSerial": istek.belge_seri,
            "documentNo": istek.belge_no,
            "product": istek.brans,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(self.kimlik["url"], json=govde,
                                 headers={"Authorization": f"Bearer {self.kimlik['token']}"})
                r.raise_for_status()
                v = r.json()
            return TeklifSonucu(self.ad, self.yontem, "OK",
                                fiyat=v.get("grossPremium"),
                                komisyon=v.get("commission"),
                                teklif_no=str(v.get("proposalNo", "")),
                                sure_sn=round(time.time() - t0, 1))
        except Exception as e:
            return TeklifSonucu(self.ad, self.yontem, "HATA", mesaj=str(e),
                                sure_sn=round(time.time() - t0, 1))
