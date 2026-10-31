"""HAR kaydını paylaşmadan önce gizli bilgileri temizler.

Kullanım:  python araclar/har_temizle.py anadolu.har  →  anadolu.temiz.har

Temizlenenler:
  - Cookie / Set-Cookie / Authorization / token içeren başlıklar
  - Şifre, kullanıcı, token, otp/sms alanları (JSON, form, URL parametreleri)
  - 11 haneli TC, 10 haneli VKN, telefon, e-posta, plaka benzeri değerler
Temizlik sonrası dosyayı yine de göz ile kontrol edin.
"""
import json
import re
import sys

GIZLI_BASLIK = re.compile(r"cookie|authorization|token|session|csrf|xsrf|auth", re.I)
GIZLI_ALAN = re.compile(r"pass|sifre|şifre|parola|user|kullanici|token|otp|sms|kod|code|secret|session|tckn|tcno|kimlik|vkn|telefon|phone|gsm|email|eposta|ad_?soyad|name|adi|soyad|unvan|sahip|sigortali|sigortalı|musteri|müşteri|owner|insured|customer|adres|address|dogum|birth|plaka|plate|sase|sasi|chassis|motor", re.I)
DESENLER = [
    (re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)"), "<TC>"),
    (re.compile(r"(?<!\d)\d{10}(?!\d)"), "<VKN_VEYA_TEL>"),
    (re.compile(r"(?<!\d)0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?!\d)"), "<TEL>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EPOSTA>"),
    (re.compile(r"\b(0[1-9]|[1-7]\d|8[01])\s?[A-ZÇĞİÖŞÜ]{1,3}\s?\d{2,5}\b"), "<PLAKA>"),
]


def metin(s: str) -> str:
    for d, y in DESENLER:
        s = d.sub(y, s)
    return s


def nesne(o):
    if isinstance(o, dict):
        return {k: ("<GIZLI>" if GIZLI_ALAN.search(k) and not isinstance(v, (dict, list)) else nesne(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [nesne(x) for x in o]
    return metin(o) if isinstance(o, str) else o


def govde(t: str) -> str:
    try:
        return json.dumps(nesne(json.loads(t)), ensure_ascii=False)
    except Exception:
        t = re.sub(r"((?:%s)[^=&]*=)[^&]*" % GIZLI_ALAN.pattern, r"\1<GIZLI>", t, flags=re.I)
        return metin(t)


def temizle(har: dict) -> dict:
    for e in har.get("log", {}).get("entries", []):
        for yon in ("request", "response"):
            r = e.get(yon, {})
            r["cookies"] = []
            r["headers"] = [h for h in r.get("headers", []) if not GIZLI_BASLIK.search(h["name"])]
        q = e["request"]
        q["url"] = govde(q["url"]) if "?" in q["url"] else q["url"]
        q["queryString"] = [{"name": x["name"], "value": "<GIZLI>" if GIZLI_ALAN.search(x["name"]) else metin(x["value"])}
                            for x in q.get("queryString", [])]
        if q.get("postData", {}).get("text"):
            q["postData"]["text"] = govde(q["postData"]["text"])
        q.get("postData", {}).pop("params", None)
        c = e["response"].get("content", {})
        if c.get("text"):
            if c.get("encoding") == "base64" or not re.search(r"json|text|xml|html", c.get("mimeType", "")):
                c["text"] = "<İKİLİ İÇERİK SİLİNDİ>"; c.pop("encoding", None)
            else:
                c["text"] = govde(c["text"])
    return har


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    kaynak = sys.argv[1]
    hedef = re.sub(r"\.har$", "", kaynak) + ".temiz.har"
    with open(kaynak, encoding="utf-8") as f:
        har = json.load(f)
    with open(hedef, "w", encoding="utf-8") as f:
        json.dump(temizle(har), f, ensure_ascii=False, indent=1)
    print("Temizlendi →", hedef)
