"""Şifre kasası: şirket kullanıcı adı/şifreleri şifreli dosyada tutulur.

Anahtar KWOLY_ANAHTAR ortam değişkeninden okunur. Yoksa ilk çalıştırmada
data/.anahtar oluşturulur (yalnızca geliştirme için; canlıda ortam değişkeni
veya bir anahtar yönetim servisi kullanılmalı).

Komut satırı:
  python -m app.kasa ekle "ALLIANZ" kullanici=12345 sifre=xxx portal_url=https://...
  python -m app.kasa liste
  python -m app.kasa sil "ALLIANZ"
"""
import json
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet

VERI = Path(__file__).resolve().parent.parent / "data"
KASA_DOSYA = VERI / "kasa.enc"
ANAHTAR_DOSYA = VERI / ".anahtar"


def _anahtar() -> bytes:
    if os.environ.get("KWOLY_ANAHTAR"):
        return os.environ["KWOLY_ANAHTAR"].encode()
    VERI.mkdir(exist_ok=True)
    if not ANAHTAR_DOSYA.exists():
        ANAHTAR_DOSYA.write_bytes(Fernet.generate_key())
        os.chmod(ANAHTAR_DOSYA, 0o600)
    return ANAHTAR_DOSYA.read_bytes().strip()


class Kasa:
    def __init__(self):
        self._f = Fernet(_anahtar())

    def _oku(self) -> dict:
        if not KASA_DOSYA.exists():
            return {}
        return json.loads(self._f.decrypt(KASA_DOSYA.read_bytes()))

    def _yaz(self, veri: dict):
        VERI.mkdir(exist_ok=True)
        KASA_DOSYA.write_bytes(self._f.encrypt(json.dumps(veri).encode()))
        os.chmod(KASA_DOSYA, 0o600)

    def al(self, sirket: str) -> dict:
        return self._oku().get(sirket, {})

    def koy(self, sirket: str, bilgiler: dict):
        v = self._oku()
        v[sirket] = {**v.get(sirket, {}), **bilgiler}
        self._yaz(v)

    def sil(self, sirket: str):
        v = self._oku()
        v.pop(sirket, None)
        self._yaz(v)

    def sirketler(self) -> list[str]:
        return sorted(self._oku())


if __name__ == "__main__":
    k = Kasa()
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    if komut == "ekle" and len(sys.argv) >= 3:
        k.koy(sys.argv[2], dict(a.split("=", 1) for a in sys.argv[3:]))
        print(f"{sys.argv[2]} kaydedildi.")
    elif komut == "liste":
        for s in k.sirketler():
            print(s, "→", ", ".join(k.al(s)))   # yalnızca alan adları, değerler gösterilmez
    elif komut == "sil" and len(sys.argv) == 3:
        k.sil(sys.argv[2]); print("silindi")
    else:
        print(__doc__)
