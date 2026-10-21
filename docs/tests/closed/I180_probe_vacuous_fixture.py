from problems.utils import validate_image_file


def test_vacuous():
    assert callable(validate_image_file)
