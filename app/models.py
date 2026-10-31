from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class TeklifIstegi:
    """Kullanıcının bir kez girdiği, tüm şirketlere dağıtılan bilgiler."""
    brans: str                      # "TRAFIK" | "KASKO"
    plaka: str
    tc_vkn: str
    belge_seri: str = ""
    belge_no: str = ""
    dogum_tarihi: str = ""          # GG.AA.YYYY
    telefon: str = ""
    # Ön sorgudan (şirket portalı / SBM) dolabilecek alanlar
    marka: str = ""
    model: str = ""
    model_yili: str = ""
    kullanim_tarzi: str = ""


@dataclass
class TeklifSonucu:
    sirket: str
    yontem: str                     # "API" | "ROBOT" | "DEMO"
    durum: str                      # "OK" | "HATA" | "ATLANDI"
    fiyat: Optional[float] = None
    komisyon: Optional[float] = None
    teklif_no: str = ""
    mesaj: str = ""
    sure_sn: float = 0.0

    def dict(self):
        return asdict(self)
