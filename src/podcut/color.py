"""Create portable per-camera LUTs and genuine source-frame color comparisons."""
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image, ImageDraw
from .core import load, sources, read, write, ffmpeg, worker, state, digest, fingerprint

LOOKS = {"natural": (1., 1., [1., 1., 1.]), "warm": (1.02, .97, [1.025, 1., .975]), "contrast": (1.10, .92, [1., 1., 1.])}

def preview_signature(p):
    return digest([dict({k:s.get(k) for k in ("id","fingerprint","color_space","input_lut","color_correction","review_times")}, input_lut_fingerprint=fingerprint(s['input_lut']) if s.get('input_lut') else None) for s in sources(p,"camera")])

def read_cube(path):
    size = None
    rows = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("TITLE"):
            continue
        parts = line.split()
        if parts[0] == "LUT_3D_SIZE":
            size = int(parts[1])
        elif parts[0] in ("DOMAIN_MIN", "DOMAIN_MAX"):
            expected = 0 if parts[0] == "DOMAIN_MIN" else 1
            if any(float(x) != expected for x in parts[1:]):
                raise ValueError("Only 0..1 CUBE domains are supported; convert this LUT with your color tool first.")
        elif parts[0].startswith("LUT_"):
            raise ValueError("Only standalone 3D CUBE LUTs are supported.")
        else:
            rows.append([float(x) for x in parts])
    if not size or len(rows) != size**3 or any(len(r) != 3 for r in rows):
        raise ValueError("Invalid 3D CUBE file")
    return np.asarray(rows).reshape(size,size,size,3)

def apply_cube(rgb, cube):
    n = cube.shape[0]
    coords = np.array([rgb[...,2].ravel(),rgb[...,1].ravel(),rgb[...,0].ravel()])*(n-1)
    return np.stack([map_coordinates(cube[...,c],coords,order=1,mode="nearest") for c in range(3)],axis=-1).reshape(rgb.shape)

def make_cube(path, look, base=None, exposure=0., balance=(1.,1.,1.), size=33):
    b,g,r = np.meshgrid(*([np.linspace(0,1,size)]*3), indexing="ij")
    rgb = np.stack([r,g,b],axis=-1)
    if base:
        rgb = apply_cube(rgb, read_cube(base))
    contrast, saturation, warmth = LOOKS[look]
    rgb = np.clip(rgb*2**exposure*np.array(balance)*np.array(warmth),0,1)
    rgb = (rgb-.5)*contrast+.5
    luma = np.sum(rgb*np.array([.2126,.7152,.0722]),axis=-1,keepdims=True)
    rgb = np.clip(luma+(rgb-luma)*saturation,0,1)
    with Path(path).open("w",encoding="ascii") as f:
        f.write(f'TITLE "Podcut {look}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f,rgb.reshape(-1,3),fmt="%.7f")

def lut_filter(path):
    # Avoid filter-language interpolation of user paths: caller copies LUT to a safe cwd filename.
    if Path(path).name != str(path) or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in str(path)):
        raise ValueError("Use a safe local LUT filename in a controlled working directory.")
    return f"lut3d=file={path}:interp=tetrahedral"

def previews(project):
    p, root = load(project)
    if p["decisions"].get("color_requested") is not True:
        raise ValueError("Ask whether color correction is wanted before preparing looks. Do not grade already-finished footage twice.")
    cams = sources(p,"camera")
    if not cams:
        raise ValueError("Select camera roles first.")
    signature = preview_signature(p)
    if (root / 'color_options.json').exists():
        previous = read(root / 'color_options.json')
        if previous.get('signature') == signature and all(Path(x).exists() for x in previous['samples']):
            expected = previous.get('lut_fingerprints', {})
            if expected and all(Path(path).exists() and fingerprint(path) == fp for path,fp in expected.items()):
                return previous
    out = root / "color" / signature[:12]
    out.mkdir(parents=True,exist_ok=True)
    catalog = {"signature":signature,"looks":{},"samples":[]}
    with worker(root):
        for s in cams:
            if s["color_space"] not in ("rec709","log"):
                raise ValueError(f"Confirm the actual recording profile for {s['id']}. A BT.709 metadata tag alone does not rule out log.")
            if s["color_space"] == "log" and not s.get("input_lut"):
                raise ValueError(f"Supply the correct manufacturer log/gamut-to-Rec.709 input_lut for {s['id']} first.")
            correction = s.get("color_correction",{})
            for look in LOOKS:
                cube = out / f"{s['id']}_{look}.cube"
                make_cube(cube,look,s.get("input_lut"),correction.get("exposure",0),correction.get("balance",[1,1,1]))
                catalog["looks"].setdefault(look,{})[s["id"]]=str(cube)
            times = s.get("review_times") or [min(max(1,s["duration"]*.25),s["duration"]-.1),max(0,s["duration"]*.7)]
            for t in times:
                row = []
                for look in ["original",*LOOKS]:
                    dest = out/f"{s['id']}_{t:.2f}_{look}.jpg"
                    filters = ["scale=640:-2"]
                    if look != "original":
                        filters.insert(0,lut_filter(f"{s['id']}_{look}.cube"))
                    # Execute in the LUT directory so filter paths never contain shell/filter metacharacters.
                    from .core import process,binary
                    process([binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin","-threads","2","-filter_threads","1","-ss",str(t),"-i",s["path"],"-frames:v","1","-vf",",".join(filters),"-y",str(dest)],cwd=out)
                    row.append((look,dest))
                thumb_height = Image.open(row[0][1]).height
                sheet = Image.new("RGB",(1280,2*(thumb_height+32)),"#161b22")
                draw = ImageDraw.Draw(sheet)
                for i,(label,path) in enumerate(row):
                    x,y=i%2*640,i//2*(thumb_height+32)
                    sheet.paste(Image.open(path),(x,y+32))
                    draw.text((x+10,y+10),f"{s['id']} / {label} / source {t:.2f}s",fill="white")
                sheetpath=out/f"{s['id']}_{t:.2f}_compare.jpg"
                sheet.save(sheetpath,quality=95)
                catalog["samples"].append(str(sheetpath))
        catalog['lut_fingerprints'] = {path:fingerprint(path) for look in catalog['looks'].values() for path in look.values()}
        write(root/"color_options.json",catalog)
        state(root,"color_choice","Actual-frame comparisons prepared: original, natural, warm, contrast. Show them and wait for the user's choice; do not choose on their behalf.")
    return catalog

def approve(project,look):
    from .core import read
    p,root=load(project)
    if look=="original":
        p["color"]={"approved":"original","luts":{}}
    else:
        options=read(root/"color_options.json")
        if options['signature'] != preview_signature(p):
            raise ValueError('Color options are stale. Generate and review fresh previews before approving.')
        if any(fingerprint(path) != fp for path,fp in options.get('lut_fingerprints',{}).items()):
            raise ValueError('A preview LUT changed. Generate and review fresh previews before approving.')
        if look not in options["looks"]:
            raise ValueError("Unknown look")
        p["color"]={"approved":look,"luts":options["looks"][look],"preview_signature":options["signature"],"lut_fingerprints":{k:fingerprint(v) for k,v in options['looks'][look].items()}}
    write(project,p)
