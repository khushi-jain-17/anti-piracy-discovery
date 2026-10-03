from pathlib import Path

from PIL import Image, ImageDraw

from evidence.logo_matcher import LogoMatcher, dhash, hamming


def _logo(fg, bg, size=(120, 40)):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 8, 40, 32], fill=fg)
    d.ellipse([55, 8, 85, 32], fill=fg)
    d.polygon([(95, 32), (105, 8), (115, 32)], fill=fg)
    return img


def _matcher(tmp_path: Path) -> LogoMatcher:
    ref_dir = tmp_path / "refs"
    ref_dir.mkdir()
    _logo((247, 255, 0), (12, 12, 12)).save(ref_dir / "dazn_test.png")
    return LogoMatcher(reference_dir=ref_dir)


def test_hash_identical_and_different():
    a = _logo((247, 255, 0), (12, 12, 12))
    b = Image.new("RGB", (120, 40), (128, 128, 128))
    assert hamming(dhash(a), dhash(a)) == 0
    assert hamming(dhash(a), dhash(b)) > 10


def test_logo_found_inside_noisy_screenshot_at_different_scale(tmp_path):
    matcher = _matcher(tmp_path)
    shot = Image.new("RGB", (800, 600), (30, 60, 90))
    ImageDraw.Draw(shot).rectangle([0, 0, 800, 50], fill=(200, 200, 200))
    shot.paste(_logo((247, 255, 0), (12, 12, 12), size=(120, 40)).resize((180, 60)), (400, 300))
    p = tmp_path / "shot.png"
    shot.save(p)
    res = matcher.match_image(str(p))
    assert res.matched
    assert res.matches[0].reference == "dazn_test"


def test_no_match_on_unrelated_image(tmp_path):
    matcher = _matcher(tmp_path)
    shot = Image.new("RGB", (800, 600), (240, 240, 240))
    ImageDraw.Draw(shot).text((100, 100), "unrelated page", fill=(0, 0, 0))
    p = tmp_path / "other.png"
    shot.save(p)
    assert not matcher.match_image(str(p)).matched


def test_missing_reference_dir_is_safe(tmp_path):
    m = LogoMatcher(reference_dir=tmp_path / "nope")
    assert not m.match_image("whatever.png").matched

def _busy_page(seed: int = 0, size=(1280, 1200)) -> Image.Image:
    """Noisy page of random coloured rectangles - the case that exposed false positives."""
    import random
    rnd = random.Random(seed)
    page = Image.new("RGB", size, (235, 235, 235))
    d = ImageDraw.Draw(page)
    for _ in range(250):
        x, y = rnd.randint(0, size[0] - 80), rnd.randint(0, size[1] - 50)
        d.rectangle([x, y, x + rnd.randint(10, 200), y + rnd.randint(5, 40)],
                    fill=tuple(rnd.randint(0, 255) for _ in range(3)))
    return page


def _wordmark_matcher(tmp_path: Path):
    """Matcher using a thin-text style reference (hardest case for 8x8 hashes)."""
    from PIL import ImageFont
    ref_dir = tmp_path / "wm"
    ref_dir.mkdir()
    ref = Image.new("RGB", (240, 80), (12, 12, 12))
    d = ImageDraw.Draw(ref)
    try:
        font = ImageFont.truetype("arialbd.ttf", 52)
    except OSError:
        font = ImageFont.load_default()
    d.text((20, 10), "DAZN", font=font, fill=(247, 255, 0))
    ref.save(ref_dir / "wordmark.png")
    return LogoMatcher(reference_dir=ref_dir), ref


def test_busy_page_without_logo_has_no_false_positive(tmp_path):
    matcher, _ = _wordmark_matcher(tmp_path)
    for seed in range(2):
        p = tmp_path / f"neg{seed}.png"
        _busy_page(seed).save(p)
        assert not matcher.match_image(str(p)).matched


def test_logo_found_at_correct_location_and_scales(tmp_path):
    matcher, ref = _wordmark_matcher(tmp_path)
    for (w, h, pos) in [(120, 40, (803, 57)), (180, 60, (301, 703)), (360, 120, (411, 503))]:
        page = _busy_page(0)
        page.paste(ref.resize((w, h)), pos)
        p = tmp_path / f"pos_{w}.png"
        page.save(p)
        res = matcher.match_image(str(p))
        assert res.matched, f"logo {w}x{h} not found"
        left, top, right, bottom = res.matches[0].bbox
        assert abs(left - pos[0]) <= 6 and abs(top - pos[1]) <= 6
        assert abs((right - left) - w) <= 2
        assert res.best_similarity > 0.85
