import subprocess, sys, time, json
subprocess.run([sys.executable,"-m","pip","install","-q","pystac-client","planetary-computer"],check=False)
import requests, pystac_client, planetary_computer as pc
res={}
bbox=[30.85,30.70,31.10,30.95]  # Gharbia (Tanta area)
cat=pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
for coll in ["hls2-s30","hls2-l30"]:
    t=time.time()
    items=list(cat.search(collections=[coll],bbox=bbox,datetime="2016-01-01/2025-12-31",max_items=5000).items())
    res[coll+"_items_2016_2025"]=len(items); res[coll+"_search_s"]=round(time.time()-t,1)
    if items:
        res[coll+"_first"]=min(i.datetime for i in items).isoformat(); res[coll+"_last"]=max(i.datetime for i in items).isoformat()
# download speed: full COG assets from 3 S30 items
items=list(cat.search(collections=["hls2-s30"],bbox=bbox,datetime="2024-01-01/2024-12-31",max_items=3).items())
tot=0;t=time.time()
for it in items:
    for k in ["B04","B8A","Fmask"]:
        if k in it.assets:
            r=requests.get(it.assets[k].href,timeout=300); tot+=len(r.content)
dt=time.time()-t
res["mpc_bytes"]=tot; res["mpc_MBps"]=round(tot/1e6/dt,2); res["mpc_assets_keys"]=list(items[0].assets.keys()) if items else []
# Earthdata reachability (no credentials)
t=time.time()
cmr=requests.get("https://cmr.earthdata.nasa.gov/search/granules.json",params={"short_name":"HLSS30","version":"2.0","bounding_box":",".join(map(str,bbox)),"temporal":"2024-01-01T00:00:00Z,2024-12-31T23:59:59Z","page_size":5},timeout=60)
res["cmr_status"]=cmr.status_code; res["cmr_s"]=round(time.time()-t,1)
try:
    g=cmr.json()["feed"]["entry"]; res["cmr_granules"]=len(g)
    url=[l["href"] for l in g[0]["links"] if l["href"].endswith(".tif")][0]; res["lpdaac_url"]=url
    r=requests.get(url,allow_redirects=False,timeout=60); res["lpdaac_noauth_status"]=r.status_code; res["lpdaac_redirect"]=r.headers.get("Location","")[:80]
except Exception as e: res["cmr_err"]=repr(e)
print("RESULT "+json.dumps(res))
