#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABTINMAP Package v2
ساختار جدید:
- فایل پایه کشور
- manifest نسخه
- patch افزایشی
- آماده برای مصرف اپ (بدون tile generation در گوشی)

این لایه روی builder فعلی قرار می گیرد و خروجی های قابل آپدیت تولید می کند.
"""
import argparse, hashlib, json, os, time

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    a=argparse.ArgumentParser()
    a.add_argument("map")
    a.add_argument("--code",required=True)
    a.add_argument("--out",default="manifest.json")
    x=a.parse_args()
    s=os.path.getsize(x.map)
    json.dump({
        "format":"ABTINMAP2",
        "country":x.code,
        "ready_display":True,
        "phone_renderer":False,
        "routing":"offline_graph",
        "search":"offline_index",
        "features":["tiles","routing","poi","speed","camera","restriction"],
        "file":{"name":os.path.basename(x.map),"size":s,"sha256":sha(x.map)},
        "created":int(time.time())
    },open(x.out,"w"),indent=2)
if __name__=="__main__": main()
