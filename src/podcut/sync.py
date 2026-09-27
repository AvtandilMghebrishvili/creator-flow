"""Audio-derived clock fits: source_seconds = offset + rate * reference_seconds."""
import numpy as np
import soundfile as sf
from scipy.signal import stft, correlate, fftconvolve, butter, sosfilt
from .core import load, source, sources, extract_audio, write, require_mapping, worker, state, digest

SR = 8000

def features(x):
    _, _, z = stft(x, SR, nperseg=256, noverlap=176, boundary=None, padded=False)
    z = abs(z)
    bands = [(4, 8), (8, 14), (14, 23), (23, 37), (37, 60), (60, 95)]
    a = np.array([np.log(np.maximum(np.sqrt(np.mean(z[lo:hi] ** 2, axis=0)), 1e-6)) for lo, hi in bands])
    return np.clip(np.diff(a, axis=1), -2, 2).astype("float32")

def match(ref, template, ref_features=None):
    rf = features(ref) if ref_features is None else ref_features
    tf = features(template)
    n = tf.shape[1]
    if n < 20 or rf.shape[1] < n:
        raise ValueError("Reference is too short for synchronization.")
    scores = np.zeros(rf.shape[1] - n + 1)
    for a, b in zip(rf, tf):
        energy = fftconvolve(a*a, np.ones(n, dtype="float32"), mode="valid")
        scores += correlate(a, b, mode="valid", method="fft") / np.sqrt(np.maximum(energy * np.sum(b*b), 1e-16))
    scores /= len(tf)
    idx = int(np.argmax(scores))
    peak = float(scores[idx])
    rivals = scores.copy()
    rivals[max(0, idx-200):idx+201] = -1
    rival = max(0, float(np.max(rivals)))
    coarse = idx * .01
    lo = max(0, int((coarse-.35)*SR))
    hi = min(len(ref), int((coarse+len(template)/SR+.35)*SR))
    sos = butter(3, [200, 2500], fs=SR, btype="bandpass", output="sos")
    rr, xx = sosfilt(sos, ref[lo:hi]), sosfilt(sos, template)
    cc = correlate(rr, xx, mode="valid", method="fft")
    ii = int(np.argmax(abs(cc)))
    yy = rr[ii:ii+len(xx)]
    wave = float(np.dot(yy, xx) / np.sqrt(np.dot(yy, yy)*np.dot(xx, xx)+1e-20))
    return {"reference": (lo+ii)/SR, "spectral_score": peak, "peak_margin": peak-rival, "wave_correlation": wave}

def fit(points):
    if len(points) < 2:
        raise ValueError("At least two separated clock anchors are required; use three for long recordings.")
    x = np.array([q["reference"] for q in points], dtype=float)
    y = np.array([q["source"] for q in points], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(x<0) or np.any(y<0):
        raise ValueError('Anchor times must be finite, nonnegative source/reference seconds.')
    if np.ptp(x) < 1:
        raise ValueError("Clock anchors are not sufficiently separated.")
    slope, offset = np.polyfit(x, y, 1)
    if slope <= 0:
        raise ValueError('Clock anchors must advance in the same direction.')
    residual = float(np.max(abs(y-offset-slope*x)))
    return {"offset": float(offset), "rate": float(slope), "max_residual_ms": residual*1000,
            "points": points, "verified": False,
            "needs_attention": bool(abs(slope-1) > .001 or residual > .03)}

def analysis_audio(s, root):
    path = root / "audio" / f"analysis_{s['id']}_{digest([s['fingerprint'],s.get('channel'),s.get('audio_stream')])[:12]}.wav"
    if not path.exists():
        extract_audio(s, path, SR)
    return path

def run_sync(project):
    p, root = load(project)
    require_mapping(p)
    ref_source = source(p, p["reference_id"])
    with worker(root):
        ref, _ = sf.read(analysis_audio(ref_source, root), dtype="float32")
        rf = features(ref)
        p["sync"][ref_source["id"]] = {"offset": 0., "rate": 1., "verified": True, "points": [], "note": "Reference clock"}
        for s in sources(p):
            if s["id"] == p["reference_id"]:
                continue
            old = p["sync"].get(s["id"], {})
            if old.get("verified"):
                continue
            if not s["audio_channels"] or s["duration"] < 8:
                p["sync"][s["id"]] = {"verified": False, "note": "No usable scratch audio / too short. Provide manual anchors."}
                continue
            span = min(24., s["duration"]/4)
            times = np.linspace(min(30., s["duration"]*.1), s["duration"]-span-1, 3)
            points = []
            for t in times:
                sample = root / "audio" / f"sync_{s['id']}_{t:.3f}.wav"
                extract_audio(s, sample, SR, float(t), span)
                x, _ = sf.read(sample, dtype="float32")
                row = match(ref, x, rf)
                row["source"] = float(t)
                points.append(row)
            model = fit(points)
            model["needs_attention"] |= any(q["spectral_score"] < .12 or q["peak_margin"] < .025 for q in points)
            model["equation"] = "source_seconds = offset + rate * reference_seconds"
            p["sync"][s["id"]] = model
            write(project, p)
            print(s["id"], "offset", round(model["offset"], 4), "drift ppm", round((model["rate"]-1)*1e6, 2), "review", model["needs_attention"], flush=True)
        write(project, p)
        state(root, "sync_review", "Clock models calculated. Inspect early/middle/late evidence, investigate weak matches, then record verified=true and a review note. No edits rendered.")

def coverage(s, model):
    return -model["offset"]/model["rate"], (s["duration"]-model["offset"])/model["rate"]

def require_sync(p, ids=None):
    for s in sources(p):
        if ids is not None and s["id"] not in ids:
            continue
        m = p["sync"].get(s["id"], {})
        if not m.get("verified") or m.get("rate", 0) <= 0:
            raise ValueError(f"Unverified synchronization for {s['id']}. Verify evidence or supply manual anchors first.")
