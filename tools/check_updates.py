"""
check_updates.py — بررسی می‌کند کدام کشورها در Geofabrik داده‌ی تازه‌تر از
آخرین ریلیز دارند و فقط همان‌ها را برای بازسازی برمی‌گرداند.

روش: هدر HTTP فایل .osm.pbf را با درخواست HEAD می‌خواند (فیلد Last-Modified)
و آن را با تاریخ ذخیره‌شده‌ی state.json (زمان آخرین ساخت موفق هر کشور) مقایسه
می‌کند. اگر state.json نبود یا کشور در آن نبود، «نیاز به ساخت» در نظر گرفته می‌شود.

اجرا:
  python3 check_updates.py --state tools/build_state.json \
      --out-changed changed.txt --out-state-new state_new.json
"""
import argparse
import json
import sys
import urllib.request
from email.utils import parsedate_to_datetime


def fetch_last_modified(url: str) -> str | None:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            lm = resp.headers.get("Last-Modified")
            if not lm:
                return None
            return parsedate_to_datetime(lm).isoformat()
    except Exception as e:
        print(f"::warning::HEAD ناموفق برای {url}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="tools/countries.json")
    ap.add_argument("--state", default="tools/build_state.json",
                     help="فایل وضعیت آخرین ساخت هر کشور (در ریپو نگه‌داری می‌شود)")
    ap.add_argument("--force", default="",
                     help="کدهای کشور که صرف‌نظر از تاریخ باید دوباره ساخته شوند (کاما-جدا)، یا 'all'")
    ap.add_argument("--out-changed", default="changed.txt")
    ap.add_argument("--out-state-new", default="state_new.json")
    a = ap.parse_args()

    with open(a.countries, encoding="utf-8") as f:
        countries = json.load(f)["countries"]

    try:
        with open(a.state, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}

    force = {c.strip().upper() for c in a.force.split(",") if c.strip()}
    force_all = "ALL" in force

    changed = []
    new_state = dict(state)

    for c in countries:
        code = c["code"]
        if force_all or code in force:
            print(f"{code}: ساخت اجباری")
            changed.append(code)
            continue

        remote_lm = fetch_last_modified(c["pbf_url"])
        prev = state.get(code, {})
        prev_lm = prev.get("source_last_modified")

        if remote_lm is None:
            if code not in state:
                print(f"{code}: تاریخ منبع نامعلوم، اولین ساخت")
                changed.append(code)
            else:
                print(f"{code}: تاریخ منبع نامعلوم، از قبلی صرف‌نظر شد")
            continue

        if prev_lm is None or remote_lm > prev_lm:
            print(f"{code}: داده‌ی تازه‌تر یافت شد ({prev_lm} -> {remote_lm})")
            changed.append(code)
            new_state[code] = {"source_last_modified": remote_lm}
        else:
            print(f"{code}: تغییری نکرده ({prev_lm})")

    with open(a.out_changed, "w", encoding="utf-8") as f:
        f.write(",".join(changed))

    with open(a.out_state_new, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    print(f"\nکشورهای نیازمند بازسازی: {changed if changed else '(هیچ‌کدام)'}")


if __name__ == "__main__":
    main()
