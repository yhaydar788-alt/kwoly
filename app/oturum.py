"""Şirket oturumları ve SMS doğrulama kodu (OTP) aracısı.

- Her şirketin tarayıcı oturumu data/oturumlar/<şirket>.json içinde saklanır
  (Playwright storage_state). Böylece her sorguda yeniden giriş/SMS gerekmez.
- Aynı şirkete aynı anda iki giriş yapılmasın diye şirket başına kilit vardır.
- Robot SMS koduna ihtiyaç duyunca `kod_iste` çağırır; arayüz bekleyen istekleri
  gösterir, kullanıcı kodu girer, robot kaldığı yerden devam eder.
"""
import asyncio
import itertools
import re
import time
from pathlib import Path

OTURUM_DIZINI = Path(__file__).resolve().parent.parent / "data" / "oturumlar"


class KodZamanAsimi(Exception):
    pass


class OturumYoneticisi:
    def __init__(self):
        OTURUM_DIZINI.mkdir(parents=True, exist_ok=True)
        self._kilitler: dict[str, asyncio.Lock] = {}
        self._bekleyen: dict[int, dict] = {}
        self._sayac = itertools.count(1)

    # --- oturum dosyaları ---
    def oturum_dosyasi(self, sirket: str) -> str:
        guvenli = re.sub(r"[^A-Za-z0-9_-]", "_", sirket)
        return str(OTURUM_DIZINI / f"{guvenli}.json")

    def oturum_var_mi(self, sirket: str) -> bool:
        return Path(self.oturum_dosyasi(sirket)).exists()

    def kilit(self, sirket: str) -> asyncio.Lock:
        return self._kilitler.setdefault(sirket, asyncio.Lock())

    # --- SMS kodu ---
    async def kod_iste(self, sirket: str, mesaj: str = "SMS ile gelen kodu girin",
                       sure_sn: int = 180) -> str:
        no = next(self._sayac)
        fut = asyncio.get_running_loop().create_future()
        self._bekleyen[no] = {"id": no, "sirket": sirket, "mesaj": mesaj,
                              "bitis": time.time() + sure_sn, "_fut": fut}
        try:
            return await asyncio.wait_for(fut, timeout=sure_sn)
        except asyncio.TimeoutError:
            raise KodZamanAsimi(f"{sirket}: SMS kodu girilmedi")
        finally:
            self._bekleyen.pop(no, None)

    def bekleyen_kodlar(self) -> list[dict]:
        return [{k: v for k, v in b.items() if k != "_fut"} for b in self._bekleyen.values()]

    def kod_gir(self, no: int, kod: str) -> bool:
        b = self._bekleyen.get(no)
        if not b or b["_fut"].done():
            return False
        b["_fut"].set_result(kod.strip())
        return True

    def iptal(self, no: int) -> bool:
        b = self._bekleyen.get(no)
        if not b or b["_fut"].done():
            return False
        b["_fut"].set_exception(KodZamanAsimi(f"{b['sirket']}: kullanıcı iptal etti"))
        return True
