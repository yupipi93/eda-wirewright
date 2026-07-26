from wirewright.geometry import BBox, collinear_overlap_len, parallel_gap, segment_crosses_box


def test_segment_crosses_box_interior():
    box = BBox(0, 0, 100, 100)
    assert segment_crosses_box((-10, 50), (110, 50), box)      # straight through
    assert not segment_crosses_box((-10, 0), (110, 0), box)    # along the top edge = touch
    assert not segment_crosses_box((-10, 50), (-5, 50), box)   # outside


def test_collinear_overlap():
    assert collinear_overlap_len((0, 10), (100, 10), (40, 10), (60, 10)) == 20   # horizontal
    assert collinear_overlap_len((5, 0), (5, 100), (5, 40), (5, 90)) == 50       # vertical
    assert collinear_overlap_len((0, 10), (100, 10), (0, 20), (100, 20)) == 0    # parallel, not collinear


def test_parallel_gap():
    assert parallel_gap((0, 10), (100, 10), (0, 25), (100, 25)) == 15   # 15px apart, overlapping x
    assert parallel_gap((0, 10), (100, 10), (200, 25), (300, 25)) is None  # no x overlap
