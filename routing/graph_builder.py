from __future__ import annotations
import json, math, struct
from pathlib import Path
from abm_builder.core import tags_dict, way_geometry, entity_id, haversine_m

ROAD_CLASSES={"motorway","trunk","primary","secondary","tertiary","residential","service","track"}
DEFAULT_SPEED={"motorway":110,"trunk":90,"primary":70,"secondary":60,"tertiary":50,"residential":30,"service":20,"track":15}

def build_graph(ways, relations, out: Path) -> dict:
    nodes={}; edges=[]; restrictions=[]; next_edge=1
    for w in ways:
        t=tags_dict(w)
        if t.get("highway") not in ROAD_CLASSES: continue
        geom=way_geometry(w)
        if len(geom)<2: continue
        # PBF node ids are retained where available; JSONL may provide node_ids.
        ids=list(getattr(w,"nodes",[]) or [])
        if ids and not isinstance(ids[0], int): ids=[getattr(n,"ref",0) for n in ids]
        if isinstance(w,dict): ids=w.get("node_ids", ids)
        if len(ids)!=len(geom): ids=[abs(hash((round(x,7),round(y,7)))) % (2**63-1) for x,y in geom]
        for nid,(lon,lat) in zip(ids,geom): nodes[int(nid)]=(lat,lon)
        oneway=t.get("oneway") in {"yes","1","true"}
        for a,b in zip(ids,ids[1:]):
            dist=haversine_m(nodes[int(a)],nodes[int(b)]); speed=float(''.join(c for c in t.get('maxspeed','') if c.isdigit() or c=='.') or DEFAULT_SPEED[t['highway']])
            edges.append({"id":next_edge,"start":int(a),"end":int(b),"distance_m":dist,"road_class":t['highway'],"speed_kmh":speed,"oneway":oneway,"access":t.get('access','')}); next_edge+=1
            if not oneway: edges.append({"id":next_edge,"start":int(b),"end":int(a),"distance_m":dist,"road_class":t['highway'],"speed_kmh":speed,"oneway":False,"access":t.get('access','')}); next_edge+=1
    for rel in relations:
        t=tags_dict(rel)
        if t.get('type')=='restriction' or t.get('restriction','').startswith('only_') or t.get('restriction','').startswith('no_'):
            restrictions.append({"id":entity_id(rel),"restriction":t.get('restriction',''),"from":t.get('from',''),"via":t.get('via',''),"to":t.get('to','')})
    out.parent.mkdir(parents=True,exist_ok=True)
    payload={"version":1,"nodes":{str(k):v for k,v in nodes.items()},"edges":edges,"turn_restrictions":restrictions}
    raw=json.dumps(payload,separators=(',',':')).encode(); out.write_bytes(b'ABMGRAPH1\n'+struct.pack('!I',len(raw))+raw)
    return {"nodes":len(nodes),"edges":len(edges),"turn_restrictions":len(restrictions)}
