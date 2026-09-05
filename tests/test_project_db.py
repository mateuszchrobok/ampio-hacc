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


class TestParseObjectsSatelZone:
    """Tests for building Satel zone names out of the objects table.

    ``satel_wej`` is the largest row type in a real project by an order of
    magnitude, and almost none of it is real. These tests pin the filters that
    turn thousands of rows into a handful of entities, because losing one of
    them would flood Home Assistant with unnamed sensors that never report.
    """

    def _satel_row(self, **overrides) -> dict:
        """One Satel zone row on an M-CON with INTEGRA firmware."""
        row = {
            "id": 2432,
            "id_urzadzenia": 1,
            "typ_komponentu": "satel_wej",
            "funkcja": 1,
            "opis_menu": "PIR Wejście",
        }
        row.update(overrides)
        return row

    def test_satel_wej_maps_to_the_bi_topic_type(self):
        """Test a Satel zone lands under bi, the segment its state topic uses."""
        assert item_type_for("satel_wej", 25) == "bi"

    def test_satel_wej_is_not_ignored(self):
        """Test Satel zones are no longer dropped wholesale."""
        assert "satel_wej" not in IGNORED_COMPONENT_TYPES

    def test_satel_outputs_and_alarm_rows_stay_ignored(self):
        """Test only the zone rows were unlocked, not the rest of the Satel block."""
        assert "satel_wyj" in IGNORED_COMPONENT_TYPES
        assert "satel_alarm" in IGNORED_COMPONENT_TYPES
        assert item_type_for("satel_wyj", 25) is None
        assert item_type_for("satel_alarm", 25) is None

    def test_zone_row_becomes_a_bi_name(self):
        """Test a named zone lands under bi at its 1-based index."""
        devices = parse_devices(_devices_payload(code=25))
        names = parse_objects({"List": [self._satel_row()]}, devices)

        assert list(names["85DA"]) == ["bi"]
        assert names["85DA"]["bi"][1].name == "PIR Wejście"

    def test_unnamed_zone_rows_are_skipped(self):
        """Test Designer's pre-allocated blank zones produce nothing.

        This is the filter that keeps the reference installation's 2403 rows
        from becoming 2403 entities: 2385 of them carry an empty name.
        """
        devices = parse_devices(_devices_payload(code=25))
        names = parse_objects({"List": [self._satel_row(opis_menu="")]}, devices)

        assert names == {}

    def test_zero_index_zone_rows_are_skipped(self):
        """Test the unallocated rows, which all carry funkcja 0, are skipped."""
        devices = parse_devices(_devices_payload(code=25))
        rows = [self._satel_row(id=i, funkcja=0, opis_menu="Rezerwa") for i in range(2337, 2347)]
        names = parse_objects({"List": rows}, devices)

        assert names == {}

    def test_the_first_row_to_claim_an_index_wins(self):
        """Test a zone renamed later in the project does not double up.

        The reference project names zone 7 twice -- "PIR Garaż" at id 2438 and
        "pirGaraz" at id 2933 -- and there is only one topic behind them.
        """
        devices = parse_devices(_devices_payload(code=25))
        names = parse_objects(
            {
                "List": [
                    self._satel_row(id=2933, funkcja=7, opis_menu="pirGaraz"),
                    self._satel_row(id=2438, funkcja=7, opis_menu="PIR Garaż"),
                ]
            },
            devices,
        )

        assert list(names["85DA"]["bi"]) == [7]
        assert names["85DA"]["bi"][7].name == "PIR Garaż"

    def test_zones_do_not_collide_with_the_modules_own_inputs(self):
        """Test satel_wej and wej at one index stay separate items.

        They are different signals on one module: ``state/bi/1`` is the alarm
        panel's zone, ``state/i/1`` is the M-CON's own input.
        """
        devices = parse_devices(_devices_payload(code=25))
        names = parse_objects(
            {
                "List": [
                    self._satel_row(id=1, funkcja=1, opis_menu="PIR Wejście"),
                    self._satel_row(
                        id=2, typ_komponentu="wej", funkcja=1, opis_menu="Wejście M-CON"
                    ),
                ]
            },
            devices,
        )

        assert names["85DA"]["bi"][1].name == "PIR Wejście"
        assert names["85DA"]["i"][1].name == "Wejście M-CON"
