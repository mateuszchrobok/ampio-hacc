"""Tests for the project database reader."""

from custom_components.ampio.project_db import (
    IGNORED_COMPONENT_TYPES,
    item_type_for,
    optional_int,
    parse_devices,
    parse_objects,
    parse_project_db,
)


def _devices_payload(code: int = 22) -> dict:
    """One device: project id 1, user MAC 34266 == 0x85DA."""
    return {"List": [{"id": 1, "mac": 34266, "typ_urzadzenia": code}]}


def _object_row(**overrides) -> dict:
    """One project object row, overridable per test."""
    row = {
        "id": 10,
        "id_urzadzenia": 1,
        "typ_komponentu": "bit8",
        "funkcja": 3,
        "opis_menu": "Tryb pracy",
    }
    row.update(overrides)
    return row


class TestOptionalInt:
    """Tests for the min/max column coercion."""

    def test_int_passes_through(self):
        """Test an int is returned as is."""
        assert optional_int(7) == 7

    def test_numeric_string_is_coerced(self):
        """Test the project's string columns are coerced."""
        assert optional_int("12") == 12

    def test_empty_string_is_none(self):
        """Test an unbounded object yields None, not 0."""
        assert optional_int("") is None

    def test_none_is_none(self):
        """Test a null column yields None."""
        assert optional_int(None) is None

    def test_garbage_is_none(self):
        """Test a non-numeric column yields None rather than raising."""
        assert optional_int("brak") is None


class TestItemTypeFor:
    """Tests for the project component type mapping."""

    def test_bit8_maps_to_afu8(self):
        """Test 8-bit flags map to the afu8 topic type."""
        assert item_type_for("bit8", 22) == "afu8"

    def test_bit8_is_not_ignored(self):
        """Test bit8 is no longer on the ignore list."""
        assert "bit8" not in IGNORED_COMPONENT_TYPES

    def test_bit16_is_still_ignored(self):
        """Test 16-bit flags stay unmapped - no known write format."""
        assert "bit16" in IGNORED_COMPONENT_TYPES
        assert item_type_for("bit16", 22) is None

    def test_flaga_still_maps_to_binary_flag(self):
        """Test the binary flag mapping is untouched."""
        assert item_type_for("flaga", 22) == "f"


class TestParseObjectsAnalogFlag:
    """Tests for building afu8 names out of the objects table."""

    def test_bit8_row_becomes_an_afu8_name(self):
        """Test a bit8 row lands under afu8 at its 1-based index."""
        devices = parse_devices(_devices_payload())
        names = parse_objects({"List": [_object_row()]}, devices)

        assert list(names) == ["85DA"]
        assert list(names["85DA"]) == ["afu8"]
        item = names["85DA"]["afu8"][3]
        assert item.name == "Tryb pracy"

    def test_project_min_max_are_carried(self):
        """Test the project's own bounds reach the ItemName."""
        devices = parse_devices(_devices_payload())
        names = parse_objects({"List": [_object_row(min=0, max=4)]}, devices)

        item = names["85DA"]["afu8"][3]
        assert item.value_min == 0
        assert item.value_max == 4

    def test_absent_min_max_are_none(self):
        """Test an unbounded object carries no bounds."""
        devices = parse_devices(_devices_payload())
        names = parse_objects({"List": [_object_row(min="", max="")]}, devices)

        item = names["85DA"]["afu8"][3]
        assert item.value_min is None
        assert item.value_max is None

    def test_placeholder_name_is_skipped(self):
        """Test an unconfigured flag produces no entity."""
        devices = parse_devices(_devices_payload())
        names = parse_objects({"List": [_object_row(opis_menu="ND")]}, devices)

        assert names == {}

    def test_flags_and_relays_still_parse_alongside(self):
        """Test adding bit8 does not disturb the existing types."""
        devices = parse_devices(_devices_payload(code=4))
        names = parse_project_db(
            _devices_payload(code=4),
            {
                "List": [
                    _object_row(id=10, typ_komponentu="przekaznik", funkcja=1, opis_menu="Lampa"),
                    _object_row(id=11, typ_komponentu="flaga", funkcja=2, opis_menu="Nieobecnosc"),
                    _object_row(id=12, funkcja=3, opis_menu="Tryb pracy"),
                ]
            },
        )
        assert devices[1].mac == "85DA"
        assert set(names["85DA"]) == {"o", "f", "afu8"}
        assert names["85DA"]["o"][1].name == "Lampa"
        assert names["85DA"]["f"][2].name == "Nieobecnosc"
        assert names["85DA"]["afu8"][3].name == "Tryb pracy"
