"""Pinned, local ASR assets. Downloading weights never uploads episode audio."""
import hashlib
from importlib.metadata import version
from pathlib import Path

from .core import fingerprint

OMNI_REPO = 'csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-int8-2025-11-12'
OMNI_REVISION = '6abf1ece20cd2308bdb7d13cd78ec1c44fa4c094'
OMNI_HASHES = {
    'model.int8.onnx': 'e7c4e54ee4c4c47829cc6667d5d00ed8ea7bef1dcfeef0fce766f77752a2726c',
    'tokens.txt': 'a7a044c52cb29cbe8b0dc1953e92cefd4ca16b0ed968177b6beab21f9a7d0b31',
    'LICENSE': 'a70a523bafbb595c2844104feb313d204904dac91c3d186c05f22a10a71c7a94',
}


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def resolve_meta_model(allow_download=False):
    try:
        import sherpa_onnx
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise ValueError('Meta ASR needs the transcription dependencies. Run the installer or '
                         'python -m pip install -e ".[transcribe]".') from exc
    if not hasattr(sherpa_onnx.OfflineRecognizer, 'from_omnilingual_asr_ctc'):
        raise ValueError('This sherpa-onnx build lacks Omnilingual ASR. Re-run the installer.')
    try:
        assets = {}
        for name, expected in OMNI_HASHES.items():
            path = Path(hf_hub_download(OMNI_REPO, name, revision=OMNI_REVISION,
                                      local_files_only=not allow_download))
            if sha256(path) != expected:
                raise ValueError(f'Meta asset checksum mismatch: {name}. Preserve and inspect the cache.')
            assets[name] = str(path)
    except (OSError, RuntimeError) as exc:
        raise ValueError('ASR weights unavailable. Use --allow-download for the first setup, '
                         'or restore the cached models. ' + str(exc)) from exc
    return {'name': 'omniASR_CTC_300M (int8 ONNX, original November 2025 weights)',
            'runtime': 'sherpa-onnx', 'runtime_version': version('sherpa-onnx'),
            'repository': OMNI_REPO, 'revision': OMNI_REVISION,
            'sha256': OMNI_HASHES, 'assets': assets, 'device': 'cpu',
            'language_conditioning': False, 'license': 'Apache-2.0',
            'timing': 'CTC token emission times; approximate word boundaries'}


def resolve_models(whisper_model, allow_download=False, device='cpu'):
    """Explicit comparison setup; the default Meta path never imports Whisper."""
    meta = resolve_meta_model(allow_download)
    try:
        from faster_whisper.utils import download_model
    except ImportError as exc:
        raise ValueError('Whisper comparison is optional. Install it with '
                         'python -m pip install -e ".[transcribe,whisper]" or use Meta only.') from exc
    model_path = Path(whisper_model).expanduser()
    try:
        if not model_path.is_dir():
            model_path = Path(download_model(whisper_model, local_files_only=not allow_download))
    except (OSError, RuntimeError) as exc:
        raise ValueError('Whisper weights unavailable. Use --allow-download or a cached model. ' + str(exc)) from exc
    if not (model_path / 'model.bin').is_file():
        raise ValueError('Whisper model directory is incomplete: model.bin is missing.')
    files = sorted(p for p in model_path.iterdir() if p.is_file())
    return {'whisper': {'name': str(whisper_model), 'runtime': 'faster-whisper',
                       'runtime_version': version('faster-whisper'),
                       'ctranslate2_version': version('ctranslate2'),
                       'path': str(model_path.resolve()), 'files': [fingerprint(p) for p in files],
                       'device': device, 'compute_type': 'int8' if device == 'cpu' else 'float16',
                       'timing': 'estimated word boundaries'},
            'meta': meta}
