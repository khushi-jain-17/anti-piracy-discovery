"""Perceptual-hash matching of DAZN logos / on-screen graphics in evidence screenshots.

Pipeline (per reference logo, per scale)
----------------------------------------
1. LOCALISE  - FFT-based normalised cross-correlation (template matching) over the whole
               screenshot at a reduced resolution proposes a few candidate positions. This is
               fast (one FFT per scale) and, unlike hashing every window, does not depend on the
               sliding-window grid lining up with the logo.
2. REFINE    - each candidate is refined at full resolution (+-2 reduced pixels) so the window
               aligns with the logo to ~1px. 64-bit hashes are very shift-sensitive, so this
               matters.
3. CONFIRM   - the refined window must pass ALL of:
                 * dHash  (difference hash)  Hamming distance <= LOGO_DHASH_THRESHOLD (of 64 bits)
                 * aHash  (average hash)     Hamming distance <= LOGO_AHASH_THRESHOLD (of 64 bits)
                 * NCC >= NCC_THRESHOLD      (pixel-level agreement; rejects hash collisions)
               Polarity-flipped logos (light-on-dark vs dark-on-light) are tolerated.

Reference images (official logos, watermarks, score-bug graphics) are loaded from
``assets/reference_logos``; every image dropped there is picked up automatically.
"""
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from config import settings

logger = logging.getLogger(__name__)

HASH_SIZE = 8  # 8x8 -> 64-bit fingerprints
SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
NCC_WIDTH = 64            # template width used for correlation (reduced resolution)
NCC_THRESHOLD = 0.85      # min |NCC| on the refined window (measured: chance <=0.68, true >0.95)
LOCALISE_NCC = 0.55       # min |NCC| for a coarse FFT peak to be refined
PEAKS_PER_SCALE = 4       # max candidates refined per scale


# ----------------------------------------------------------------------------- hashing
def _pixels(img: Image.Image, size: Tuple[int, int], box: Optional[Tuple[int, int, int, int]] = None) -> List[int]:
    """Downscale (optionally a sub-box) of an image to ``size`` grayscale pixels."""
    gray = img if img.mode == "L" else img.convert("L")
    return list(gray.resize(size, Image.Resampling.BOX, box=box).tobytes())


def dhash(img: Image.Image, hash_size: int = HASH_SIZE, box=None) -> int:
    """Difference hash: compares each pixel with its right neighbour."""
    px = _pixels(img, (hash_size + 1, hash_size), box)
    bits = 0
    for row in range(hash_size):
        base = row * (hash_size + 1)
        for col in range(hash_size):
            bits = (bits << 1) | (1 if px[base + col] > px[base + col + 1] else 0)
    return bits


def ahash(img: Image.Image, hash_size: int = HASH_SIZE, box=None) -> int:
    """Average hash: each pixel vs. the mean luminance."""
    px = _pixels(img, (hash_size, hash_size), box)
    mean = sum(px) / len(px)
    bits = 0
    for p in px:
        bits = (bits << 1) | (1 if p > mean else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ----------------------------------------------------------------------------- correlation
def _thumb(gray: Image.Image, width: int, height: int, box=None) -> np.ndarray:
    return np.asarray(gray.resize((width, height), Image.Resampling.BOX, box=box), dtype=np.float64).ravel()


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    """Normalised cross-correlation in [-1, 1]; -1 means the same shape with inverted polarity."""
    a, b = a - a.mean(), b - b.mean()
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b) / denom if denom > 1e-6 else 0.0


def _ceil16(n: int) -> int:
    return (n + 15) // 16 * 16


def _ncc_map(image: np.ndarray, tmpl: np.ndarray, min_std: float) -> Optional[np.ndarray]:
    """|NCC| of ``tmpl`` at every valid position of ``image`` (FFT correlation + integral images)."""
    ih, iw = image.shape
    th, tw = tmpl.shape
    if ih < th or iw < tw:
        return None
    t = tmpl - tmpl.mean()
    t_norm = float(np.sqrt((t ** 2).sum()))
    if t_norm < 1e-6:
        return None
    shape = (_ceil16(ih), _ceil16(iw))
    num = np.fft.irfft2(np.fft.rfft2(image, shape) * np.conj(np.fft.rfft2(t, shape)), shape)
    num = num[:ih - th + 1, :iw - tw + 1]

    def window_sums(a: np.ndarray) -> np.ndarray:
        integ = np.zeros((ih + 1, iw + 1))
        integ[1:, 1:] = a.cumsum(0).cumsum(1)
        return integ[th:, tw:] - integ[:-th, tw:] - integ[th:, :-tw] + integ[:-th, :-tw]

    n = th * tw
    var = window_sums(image * image) - window_sums(image) ** 2 / n
    valid = var >= n * min_std ** 2  # skip flat windows (blank areas)
    out = np.zeros_like(num)
    out[valid] = np.abs(num[valid]) / (t_norm * np.sqrt(var[valid]))
    return out


# ----------------------------------------------------------------------------- models
@dataclass
class ReferenceLogo:
    name: str
    size: Tuple[int, int]
    gray: Image.Image
    dhash: int
    ahash: int
    dhash_inverted: int  # handles white-on-dark vs dark-on-white variants
    thumb: np.ndarray    # NCC_WIDTH-wide grayscale thumbnail for refinement scoring
    thumb_h: int


@dataclass
class LogoMatch:
    reference: str
    dhash_distance: int
    ahash_distance: int
    bbox: Tuple[int, int, int, int]  # left, top, right, bottom in screenshot pixels
    similarity: float  # 0..1 (mean of hash similarity and NCC)


@dataclass
class LogoMatchResult:
    matched: bool = False
    best_similarity: float = 0.0
    matches: List[LogoMatch] = field(default_factory=list)
    references_checked: int = 0

    @property
    def summary(self) -> str:
        if not self.matches:
            return "No match"
        top = max(self.matches, key=lambda m: m.similarity)
        return f"{top.reference} ({top.similarity:.0%})"

    def to_dict(self) -> Dict:
        return asdict(self)


# ----------------------------------------------------------------------------- matcher
class LogoMatcher:
    """Matches screenshots against a library of reference DAZN logos / graphics."""

    def __init__(
        self,
        reference_dir: Optional[Path] = None,
        dhash_threshold: Optional[int] = None,
        ahash_threshold: Optional[int] = None,
        min_variance: float = 12.0,
        max_scan_height: int = 3000,
        scales: Tuple[float, ...] = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0),
    ):
        self.reference_dir = reference_dir or settings.LOGO_REFERENCE_DIR
        self.dhash_threshold = settings.LOGO_DHASH_THRESHOLD if dhash_threshold is None else dhash_threshold
        self.ahash_threshold = settings.LOGO_AHASH_THRESHOLD if ahash_threshold is None else ahash_threshold
        self.min_variance = min_variance  # skip flat windows (std-dev of luminance)
        self.max_scan_height = max_scan_height
        self.scales = scales
        self.references: List[ReferenceLogo] = self._load_references()

    # -- reference library
    def _load_references(self) -> List[ReferenceLogo]:
        refs: List[ReferenceLogo] = []
        if not self.reference_dir.exists():
            logger.warning(f"[LogoMatcher] Reference directory missing: {self.reference_dir}")
            return refs
        for path in sorted(self.reference_dir.iterdir()):
            if path.suffix.lower() not in SUPPORTED_EXT:
                continue
            try:
                with Image.open(path) as raw:
                    img = self._flatten(raw)
                gray = img.convert("L")
                thumb_h = max(8, round(NCC_WIDTH * img.height / img.width))
                refs.append(ReferenceLogo(
                    name=path.stem,
                    size=img.size,
                    gray=gray,
                    dhash=dhash(gray),
                    ahash=ahash(gray),
                    dhash_inverted=dhash(Image.eval(gray, lambda v: 255 - v)),
                    thumb=_thumb(gray, NCC_WIDTH, thumb_h),
                    thumb_h=thumb_h,
                ))
            except Exception as e:
                logger.warning(f"[LogoMatcher] Could not load reference {path.name}: {e}")
        logger.info(f"[LogoMatcher] Loaded {len(refs)} reference logo(s) from {self.reference_dir}")
        return refs

    @staticmethod
    def _flatten(img: Image.Image) -> Image.Image:
        """Composite transparency onto white so PNG logos hash consistently."""
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            return Image.alpha_composite(bg, rgba).convert("RGB")
        return img.convert("RGB")

    # -- scanning
    def match_image(self, image_path: str) -> LogoMatchResult:
        result = LogoMatchResult(references_checked=len(self.references))
        if not self.references:
            return result
        path = Path(image_path)
        if not path.is_absolute():
            path = settings.BASE_DIR / path
        if not path.exists():
            return result

        try:
            with Image.open(path) as raw:
                shot = self._flatten(raw)
        except Exception as e:
            logger.debug(f"[LogoMatcher] Cannot open {image_path}: {e}")
            return result

        gray = shot.crop((0, 0, shot.width, min(shot.height, self.max_scan_height))).convert("L")

        for ref in self.references:
            best = self._scan_for_reference(gray, ref)
            if best:
                result.matches.append(best)

        if result.matches:
            result.matched = True
            result.best_similarity = max(m.similarity for m in result.matches)
            logger.info(f"[LogoMatcher] Logo match in {path.name}: {result.summary}")
        return result

    def match_images(self, image_paths: List[str]) -> LogoMatchResult:
        """Match several images (e.g. full page + cropped player); return the strongest result."""
        best = LogoMatchResult(references_checked=len(self.references))
        for p in image_paths:
            res = self.match_image(p)
            if res.matched and res.best_similarity >= best.best_similarity:
                best = res
        return best

    def _scan_for_reference(self, gray: Image.Image, ref: ReferenceLogo) -> Optional[LogoMatch]:
        """Multi-scale search: FFT localisation -> refinement -> hash + NCC confirmation."""
        best: Optional[LogoMatch] = None
        full = HASH_SIZE * HASH_SIZE

        for scale in self.scales:
            win_w, win_h = int(ref.size[0] * scale), int(ref.size[1] * scale)
            if win_w < 24 or win_h < 12 or win_w > gray.width or win_h > gray.height:
                continue

            # Stage 1: localise on a reduced-resolution copy (window becomes ~NCC_WIDTH wide)
            f = min(1.0, NCC_WIDTH / win_w)
            small = np.asarray(
                gray.resize((max(1, round(gray.width * f)), max(1, round(gray.height * f))), Image.Resampling.BOX),
                dtype=np.float64)
            tmpl = np.asarray(
                ref.gray.resize((max(4, round(win_w * f)), max(4, round(win_h * f))), Image.Resampling.BOX),
                dtype=np.float64)
            ncc_map = _ncc_map(small, tmpl, self.min_variance)
            if ncc_map is None:
                continue

            th, tw = tmpl.shape
            flat = ncc_map.ravel()
            k = min(PEAKS_PER_SCALE * 40, flat.size)
            top = np.argpartition(flat, -k)[-k:]
            top = top[np.argsort(flat[top])[::-1]]

            peaks: List[Tuple[int, int]] = []
            for idx in top:
                if flat[idx] < LOCALISE_NCC or len(peaks) >= PEAKS_PER_SCALE:
                    break
                y, x = divmod(int(idx), ncc_map.shape[1])
                if any(abs(x - px) < tw // 2 and abs(y - py) < th // 2 for px, py in peaks):
                    continue  # non-max suppression
                peaks.append((x, y))

            for x, y in peaks:
                left, top_px = int(round(x / f)), int(round(y / f))
                radius = int(2 / f) + 1  # +-2 reduced pixels
                # Stage 2: refine at full resolution
                box, ncc = self._refine(gray, ref, left, top_px, win_w, win_h, radius)
                if box is None or ncc < NCC_THRESHOLD:
                    continue
                # Stage 3: confirm with perceptual hashes
                d_raw = min(hamming(dhash(gray, box=box), ref.dhash),
                            hamming(dhash(gray, box=box), ref.dhash_inverted))
                a_raw = hamming(ahash(gray, box=box), ref.ahash)
                a_dist = min(a_raw, full - a_raw)  # tolerate light/dark polarity flip
                if d_raw > self.dhash_threshold or a_dist > self.ahash_threshold:
                    continue
                sim = round((1 - d_raw / full + ncc) / 2, 4)
                if best is None or sim > best.similarity:
                    best = LogoMatch(ref.name, d_raw, a_dist, box, sim)
        return best

    @staticmethod
    def _refine(gray: Image.Image, ref: ReferenceLogo, left: int, top: int,
                win_w: int, win_h: int, radius: int) -> Tuple[Optional[Tuple[int, int, int, int]], float]:
        """Search around a coarse position (coarse-to-fine) for the best-correlating window."""
        best_box, best_ncc = None, -1.0
        cx, cy = left, top
        step = max(1, radius // 2)
        while True:
            for dy in range(-radius, radius + 1, step):
                for dx in range(-radius, radius + 1, step):
                    l, t = cx + dx, cy + dy
                    if l < 0 or t < 0 or l + win_w > gray.width or t + win_h > gray.height:
                        continue
                    box = (l, t, l + win_w, t + win_h)
                    score = abs(_ncc(_thumb(gray, NCC_WIDTH, ref.thumb_h, box), ref.thumb))
                    if score > best_ncc:
                        best_box, best_ncc = box, score
            if step == 1 or best_box is None:
                break
            cx, cy = best_box[0], best_box[1]
            radius, step = step, max(1, step // 2)
        return best_box, best_ncc
