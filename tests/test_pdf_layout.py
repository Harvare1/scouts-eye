import pytest

from pdf_reports import PITCH_LENGTH_TO_WIDTH, _pitch_geometry


def test_pitch_keeps_real_football_proportions_inside_diagram_area():
    area = (36, 53, 356, 407)
    frame_x, frame_y, frame_w, frame_h, pitch_x, pitch_y, pitch_w, pitch_h = _pitch_geometry(*area)

    assert pitch_w / pitch_h == pytest.approx(PITCH_LENGTH_TO_WIDTH)
    assert frame_x >= area[0]
    assert frame_y >= area[1]
    assert frame_x + frame_w <= area[0] + area[2]
    assert frame_y + frame_h <= area[1] + area[3]
    assert pitch_x >= frame_x
    assert pitch_y >= frame_y
