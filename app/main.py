import asyncio
import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import gecmis
from .kasa import Kasa
from .models import TeklifIstegi, TeklifSonucu
from .oturum import OturumYoneticisi, KodZamanAsimi
from .adapters.demo import DemoAdapter, DemoSmsAdapter
from .adapters.ornek_api import OrnekApiAdapter
from .adapters.ornek_robot import OrnekRobotAdapter
from .adapters.anadolu import AnadoluRobotAdapter

KOK = Path(__file__).resolve().parent.parent
STATIC = KOK / "static"

# sirketler.json'daki "adapter" alanı → sınıf
ADAPTERLER = {
    "demo": DemoAdapter,
    "demo_sms": DemoSmsAdapter,
    "api": OrnekApiAdapter,
    "robot": OrnekRobotAdapter,
    "anadolu": AnadoluRobotAdapter,
}

ortam = OturumYoneticisi()
kasa = Kasa()


def sirketleri_yukle():
    ayar = json.loads((KOK / "sirketler.json").read_text(encoding="utf-8"))
    liste = [ADAPTERLER[s["adapter"]](s["ad"], kasa.al(s["ad"]), ortam)
             for s in ayar["sirketler"] if s.get("aktif")]
    return liste, ayar.get("on_sorgu_sirasi", [])


SIRKETLER, ON_SORGU_SIRASI = sirketleri_yukle()

app = FastAPI(title="Kwoly API", description="Kwoly teklif motoru")


class IstekGovdesi(BaseModel):
    brans: str = "TRAFIK"
    plaka: str
    tc_vkn: str
    belge_seri: str = ""
    belge_no: str = ""
    dogum_tarihi: str = ""
    telefon: str = ""


class SorguAc(BaseModel):
    brans: str
    plaka: str
    tc_vkn: str
    arac: dict = {}


class KodGovdesi(BaseModel):
    kod: str


def _bul(ad):
    return next((x for x in SIRKETLER if x.ad == ad), None)


@app.get("/")
def anasayfa():
    return FileResponse(STATIC / "index.html")


@app.get("/api/sirketler")
def sirketler():
    return [{"ad": s.ad, "yontem": s.yontem, "branslar": list(s.desteklenen_branslar),
             "oturum": ortam.oturum_var_mi(s.ad)} for s in SIRKETLER]


@app.post("/api/on-sorgu")
async def on_sorgu(g: IstekGovdesi):
    """Plaka + TC ile araç bilgisini sıradaki şirketlerden getirir; biri vermezse diğerini dener."""
    istek = TeklifIstegi(**g.model_dump())
    sira = [_bul(a) for a in ON_SORGU_SIRASI if _bul(a)] or SIRKETLER
    denenen = []
    for s in sira:
        try:
            bilgi = await asyncio.wait_for(s.on_sorgu(istek), timeout=60)
            if bilgi:
                return {"kaynak": s.ad, **bilgi}
            denenen.append(f"{s.ad}: bilgi yok")
        except Exception as e:
            denenen.append(f"{s.ad}: {e}")
    return {"kaynak": None, "denenen": denenen}


async def _tek_sirket(s, istek) -> TeklifSonucu:
    if istek.brans not in s.desteklenen_branslar:
        return TeklifSonucu(s.ad, s.yontem, "ATLANDI", mesaj="Branş desteklenmiyor")
    t0 = time.time()
    try:
        # SMS beklemesi de olabileceği için süre geniş
        sonuc = await asyncio.wait_for(s.teklif_al(istek), timeout=300)
    except asyncio.TimeoutError:
        sonuc = TeklifSonucu(s.ad, s.yontem, "HATA", mesaj="Zaman aşımı")
    except KodZamanAsimi as e:
        sonuc = TeklifSonucu(s.ad, s.yontem, "HATA", mesaj=str(e))
    except Exception as e:
        sonuc = TeklifSonucu(s.ad, s.yontem, "HATA", mesaj=str(e)[:200])
    sonuc.sure_sn = sonuc.sure_sn or round(time.time() - t0, 1)
    return sonuc


# --- sorgu akışı: önce sorgu aç, sonra şirket şirket teklif al (arayüz canlı gösterir) ---
@app.post("/api/sorgu")
def sorgu_ac(g: SorguAc):
    return {"sorgu_id": gecmis.sorgu_ac(g.brans, g.plaka, g.tc_vkn, g.arac)}


@app.post("/api/teklif/{ad}")
async def teklif_tek(ad: str, g: IstekGovdesi, sorgu_id: int | None = None):
    s = _bul(ad)
    if s is None:
        raise HTTPException(404, "Şirket bulunamadı")
    sonuc = (await _tek_sirket(s, TeklifIstegi(**g.model_dump()))).dict()
    if sorgu_id:
        gecmis.sonuc_kaydet(sorgu_id, sonuc)
    return sonuc


@app.post("/api/teklif")
async def teklif_hepsi(g: IstekGovdesi):
    """Tek çağrıda tüm şirketler (dış sistemler/entegrasyonlar için)."""
    istek = TeklifIstegi(**g.model_dump())
    sid = gecmis.sorgu_ac(istek.brans, istek.plaka, istek.tc_vkn)
    sonuclar = await asyncio.gather(*(_tek_sirket(s, istek) for s in SIRKETLER))
    for r in sonuclar:
        gecmis.sonuc_kaydet(sid, r.dict())
    sonuclar = sorted(sonuclar, key=lambda r: (r.fiyat is None, r.fiyat or 0))
    return {"sorgu_id": sid, "sonuclar": [r.dict() for r in sonuclar]}


# --- SMS kodu ---
@app.get("/api/kod")
def bekleyen_kodlar():
    return ortam.bekleyen_kodlar()


@app.post("/api/kod/{no}")
def kod_gir(no: int, g: KodGovdesi):
    if not ortam.kod_gir(no, g.kod):
        raise HTTPException(404, "Bekleyen kod isteği yok")
    return {"ok": True}


@app.delete("/api/kod/{no}")
def kod_iptal(no: int):
    return {"ok": ortam.iptal(no)}


# --- geçmiş ---
@app.get("/api/gecmis")
def gecmis_liste():
    return gecmis.liste()


@app.get("/api/gecmis/{sorgu_id}")
def gecmis_detay(sorgu_id: int):
    d = gecmis.detay(sorgu_id)
    if not d:
        raise HTTPException(404)
    return d


@app.get("/api/gecmis/{sorgu_id}/excel")
def gecmis_excel(sorgu_id: int):
    if not gecmis.detay(sorgu_id):
        raise HTTPException(404)
    return Response(gecmis.csv_metni(sorgu_id), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="kwoly-sorgu-{sorgu_id}.csv"'})
