"""Import reviewed Wikimedia Commons photographs and generate local WebP variants."""

import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "frontend_assets" / "acervo_fotografico.json"
INVENTORY = ROOT / "frontend_assets" / "inventario_campeoes.json"
DIRECTORY = ROOT / "static" / "pitwall-archive"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "PitwallLab/1.0 (https://github.com/mbpaschoal/pitwall-lab; archival image curation)"


class Text(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.parts = []
        self.feed(html)

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return " ".join(" ".join(self.parts).split())


def read(url):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=45) as response:
        return response.read()


def load_metadata(titles):
    query = {
        "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
        "titles": "|".join(titles), "prop": "imageinfo",
        "iiprop": "url|size|mime|sha1|extmetadata",
        "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|Restrictions|ImageDescription",
    }
    response = json.loads(read(API + "?" + urlencode(query)))
    results = {page["title"]: page["imageinfo"][0] for page in response["query"]["pages"] if "imageinfo" in page}
    for item in response["query"].get("normalized", []) + response["query"].get("redirects", []):
        if item["to"] in results:
            results[item["from"]] = results[item["to"]]
    return results


def normalize_url(url, allowed_hosts):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in allowed_hosts:
        raise ValueError(f"Unexpected image or license URL: {url}")
    return urlunsplit(("https", parsed.netloc, parsed.path, "", ""))


def import_photo(key, entry, info):
    if not re.fullmatch(r"[a-z0-9-]+", key):
        raise ValueError(f"Invalid photo ID: {key}")
    if info["mime"] not in {"image/jpeg", "image/png", "image/webp", "image/tiff"}:
        raise ValueError(f"Unsupported photo type: {info['mime']}")
    meta = {field: Text(data["value"]).text() for field, data in info["extmetadata"].items()}
    license_name = meta.get("LicenseShortName", "")
    if not re.fullmatch(r"(?:CC BY(?:-SA)? [234]\.[05](?: [a-zA-Z]+)?|CC0|Public domain)", license_name):
        raise ValueError(f"Unreviewed license for {key}: {license_name}")
    if meta.get("Restrictions"):
        raise ValueError(f"Photo requires individual rights review: {key}")
    license_url = meta.get("LicenseUrl")
    if not license_url and license_name == "Public domain":
        license_url = "https://creativecommons.org/publicdomain/mark/1.0/"
    license_url = normalize_url(license_url or "", {"creativecommons.org", "www.creativecommons.org"})
    author = meta.get("Artist")
    if not author:
        raise ValueError(f"Missing author for {key}")
    original = normalize_url(info["url"], {"upload.wikimedia.org"})
    contents = read(original)
    if hashlib.sha1(contents).hexdigest() != info["sha1"]:
        raise ValueError(f"Source photo bytes differ from Wikimedia metadata: {key}")
    digest = hashlib.sha256(contents).hexdigest()
    with Image.open(io.BytesIO(contents)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    if min(width, height) < 1050 or max(width, height) < 1600:
        raise ValueError(f"Original is too small for the archive: {key} ({width} × {height})")

    variants = []
    for edge in (960, 2400):
        variant = image.copy()
        variant.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        name = f"{key}-{digest[:12]}-{max(variant.size)}.webp"
        path = DIRECTORY / name
        variant.save(path, format="WEBP", quality=91 if edge > 960 else 86, method=6)
        variants.append({"arquivo": path.relative_to(ROOT).as_posix(), "largura": variant.width,
                         "altura": variant.height, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    source = normalize_url(info["descriptionurl"], {"commons.wikimedia.org"})
    return {**entry, "fonte": source, "original": original, "autor": author,
            "licenca": license_name, "licenca_url": license_url, "sha256": digest,
            "largura": width, "altura": height, "variantes": variants}


def associate_models(selection, inventory):
    for photo in selection.values():
        model = photo.get("modelo")
        if not model:
            continue
        seasons = set(photo["temporadas"])
        matches = {row["ano"]: row["equipe"] for row in inventory["campanhas"]
                   if row["ano"] in seasons and model in row["modelos_candidatos"]}
        if set(matches) != seasons or len(set(matches.values())) != 1:
            raise ValueError(f"Photo association does not match the championship inventory: {model}")
        photo["construtor"] = next(iter(matches.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selecao", type=Path, help="JSON with reviewed photo IDs, Wikimedia file titles and captions")
    args = parser.parse_args()
    selection = json.loads(args.selecao.read_text())
    associate_models(selection, json.loads(INVENTORY.read_text()))
    catalog = json.loads(CATALOG.read_text()) if CATALOG.is_file() else {"schema": 1, "fotos": {}}
    DIRECTORY.mkdir(exist_ok=True)
    pending = {key: item for key, item in selection.items() if key not in catalog["fotos"]}
    metadata = load_metadata([item["arquivo_commons"] for item in pending.values()]) if pending else {}
    failures = []
    for key, item in pending.items():
        try:
            catalog["fotos"][key] = import_photo(key, item, metadata[item["arquivo_commons"]])
        except HTTPError as error:
            if error.code == 429:
                retry_after = error.headers.get("Retry-After", "unspecified")
                parser.exit(75, f"Wikimedia rate limit at {key}. Retry-After: {retry_after}\n")
            failures.append(key)
            print(key, error, flush=True)
        except (KeyError, OSError, ValueError) as error:
            failures.append(key)
            print(key, error, flush=True)
        else:
            CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(key, "ok", flush=True)
        time.sleep(1)
    if failures:
        parser.exit(1, f"Review failed imports: {', '.join(failures)}\n")


if __name__ == "__main__":
    main()
