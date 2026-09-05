"""Read Ampio item names from the server's project database.

The legacy per-module handshake (``ampio/to/<mac>/description``) is not answered by
Ampio MQTT bridge 5.x. Every module times out, so ``AmpioModuleInfo.names`` stays
empty and every name-driven platform yields no entities at all -- no switches for
the relay modules, no covers for the roller shutters, no climate for the heating
controller -- even though the state topics for all of them are live and retained.

The current server keeps those names in its project database instead. Publishing a
table name as the payload of ``ampio/control/<user>/config`` makes the server
publish that whole table on ``ampio/fromDB/<user>/config/<table>``. Two tables are
enough to rebuild ``names``:

``devices``
    One row per module. ``id`` is the project-local device id, ``mac`` is the user
    MAC as an integer (34266 -> ``85DA``) and ``typ_urzadzenia`` is the module code.

``objects``
    One row per named item: ``id_urzadzenia`` points back at the device, ``funkcja``
    is the 1-based index used in the state topic, ``typ_komponentu`` is the project's
    own component type, ``opis_menu`` is the human name and ``min``/``max`` bound the
    value where the project bothered to bound it.

A row is not evidence that anything exists. Ampio Designer pre-allocates whole
blocks of rows -- ``satel_wej`` most of all -- and leaves them nameless. The name is
the only signal that a human configured the item, which is why ``PLACEHOLDER_NAMES``
is a correctness filter here and not a cosmetic one.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from .models import ItemName, ItemTypes, base64encode

_LOGGER = logging.getLogger(__name__)

# Request one table by publishing its name; the server answers on the matching
# ``ampio/fromDB/<user>/config/<table>`` topic.
TOPIC_PROJECT_REQUEST = "ampio/control/{user}/config"
TOPIC_PROJECT_RESPONSE = "ampio/fromDB/{user}/config/{table}"

TABLE_DEVICES = "devices"
TABLE_OBJECTS = "objects"
PROJECT_TABLES = (TABLE_DEVICES, TABLE_OBJECTS)

# Project component type -> Ampio item type. Both ``przekaznik`` and
# ``roleta_procenty`` are binary outputs; the module class decides whether that
# becomes a switch or a cover, and no module in practice carries both.
# ``reg`` are the heating controller's zones, which MRT-16s reads as temperatures.
COMPONENT_TYPES: dict[str, str] = {
    "przekaznik": ItemTypes.BinaryOutput.value,
    "roleta_procenty": ItemTypes.BinaryOutput.value,
    "wej": ItemTypes.BinaryInput.value,
    "flaga": ItemTypes.BinaryFlag.value,
    "temp": ItemTypes.Temperature.value,
    "reg": ItemTypes.Temperature.value,
    "led": ItemTypes.BinaryOutput.value,  # see LED_ANALOG_CODES
    # An 8-bit flag: one byte of state, read on ``state/afu8/<n>``. The project
    # calls it ``bit8``; the wire calls it ``afu8``.
    "bit8": ItemTypes.AnalogFlag8.value,
    # The same wire type under a second project name. ``flaga_liniowa`` is what
    # Ampio Designer writes for an 8-bit flag placed on a module that is not a
    # bare I/O board, and on this installation it is the name that matters: the
    # ``bit8`` rows here sit on two M-CON modules that publish no ``afu8`` at
    # all, while every live ``afu8`` topic belongs to a ``flaga_liniowa`` row.
    # Mapping only ``bit8`` therefore produces entities that are permanently
    # ``unknown`` and misses every flag that carries a value.
    "flaga_liniowa": ItemTypes.AnalogFlag8.value,
    # A zone of a Satel alarm panel behind an M-CON bridge, read on
    # ``state/bi/<n>``. This is by far the most numerous row type in a project
    # and almost all of it is unused allocation -- see PLACEHOLDER_NAMES.
    "satel_wej": ItemTypes.SatelInput.value,
}

# MLED-1 and MLED-s drive their channels over ``au/<n>``; every other module that
# carries ``led`` rows (MOC-4, MDIM-8s, the generic ones) uses ``o/<n>``.
LED_ANALOG_CODES = frozenset({17, 19})

# METEO-1s, MSENS and MSENS-LITE build their own ``t/1`` sensor from a fixed topic,
# with the right device class and unit. The project also carries a ``temp`` row at
# index 1 for those modules, and it would win the unique-id race and replace a
# working sensor with an unclassified one. Higher temp indices are real extra
# probes and are kept.
FIXED_TEMPERATURE_CODES = frozenset({34, 44, 45})

# Rows whose name is one of these are unconfigured placeholders in the project
# ("ND" = nie dotyczy). They would otherwise become entities with no meaning.
#
# This is load-bearing for ``satel_wej``. Ampio Designer allocates a full block of
# Satel zone rows per M-CON whether or not a panel is attached, so the row count is
# not a count of anything real: the reference installation carries 2403 of them
# across four M-CONs, and 2384 have an empty ``opis_menu``. 2062 of those sit on a
# module that bridges a heat pump over RS-485 and has no alarm panel at all.
# Combined with the ``funkcja >= 1`` and duplicate-index checks below, 2403 rows
# become 15 items. Anything that weakens this filter re-arms that number.
PLACEHOLDER_NAMES = frozenset({"", "ND", "N/D", "-"})

# Component types deliberately not turned into entities:
#   satel_wyj    a Satel panel output, on ``state/bo/<n>``. Live, but what the
#                index means is not established: the reference project names
#                outputs 1, 2, 3 and 20 while 1, 2, 3 and *4* read high, so the
#                obvious index mapping is already contradicted by the wire.
#   satel_alarm  per-zone arm/alarm state. Already carried by the
#                alarm_control_panel entity's armed/alarm/entrytime topics.
#   lin_wej      MSENS channels, built from fixed topics by MSENSModuleInfo
#   rgbw         built from fixed topics by MRGBu1ModuleInfo
#   bit16        the 16-bit flag. Its state topic (``afi16``) is live, but no
#                write format for it is known: Ampio's own Node-RED node has an
#                ``afu8`` branch and no ``afi16`` one, and its generic fallback
#                (``.../afi16/<n>/cmd``) is unattested. Exposing it writable
#                would mean guessing a frame at real hardware.
#   custom, event, flaga_liniowa, tekst_can, kamera_rtsp,
#   stacja_elsner, symulacja, detekcja, wykres
#                project-side constructs with no Ampio state topic of their own
IGNORED_COMPONENT_TYPES = frozenset(
    {
        "satel_wyj",
        "satel_alarm",
        "lin_wej",
        "rgbw",
        "custom",
        "event",
        "bit16",
        "tekst_can",
        "kamera_rtsp",
        "stacja_elsner",
        "symulacja",
        "detekcja",
        "wykres",
    }
)


@dataclass(frozen=True)
class ProjectDevice:
    """A row of the project ``devices`` table, reduced to what names need."""

    mac: str
    code: int


def optional_int(value: Any) -> int | None:
    """Coerce a project column to int, or None when it is empty or not a number.

    The project stores ``min``/``max`` as free-form columns: they arrive as ints,
    as numeric strings, as ``""`` for an object nobody bounded, and as null.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def item_type_for(component: str | None, code: int) -> str | None:
    """Return the Ampio item type for a project component type, or None to skip."""
    if not component or component in IGNORED_COMPONENT_TYPES:
        return None
    if component == "led":
        if code in LED_ANALOG_CODES:
            return ItemTypes.AnalogOutput.value
        return ItemTypes.BinaryOutput.value
    return COMPONENT_TYPES.get(component)


def parse_devices(payload: dict[str, Any]) -> dict[int, ProjectDevice]:
    """Index the project ``devices`` table by its project-local device id."""
    devices: dict[int, ProjectDevice] = {}
    for row in payload.get("List") or []:
        try:
            device_id = int(row["id"])
            mac = int(row["mac"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            code = int(row.get("typ_urzadzenia") or 0)
        except (TypeError, ValueError):
            code = 0
        devices[device_id] = ProjectDevice(mac=f"{mac:04X}", code=code)
    return devices


def parse_objects(
    payload: dict[str, Any], devices: dict[int, ProjectDevice]
) -> dict[str, dict[str, dict[int, ItemName]]]:
    """Build ``{user_mac: {item_type: {index: ItemName}}}`` from the objects table.

    Indices are kept exactly as the project stores them in ``funkcja``: 1-based, the
    same numbering the state topics use, which is what every module builder expects.

    Rows are processed in ``id`` order and the first row to claim an index wins. The
    project also holds group objects -- "Rolety na Parterze", "Cały dom" -- which
    reuse index 1 of a device that already has a physical item there. Those are
    added to the project later, so they carry higher ids and lose the tie.
    """
    names: dict[str, dict[str, dict[int, ItemName]]] = defaultdict(lambda: defaultdict(dict))
    skipped: Counter[str] = Counter()

    def sort_key(row: dict[str, Any]) -> int:
        try:
            return int(row.get("id") or 0)
        except (TypeError, ValueError):
            return 0

    for row in sorted(payload.get("List") or [], key=sort_key):
        device = devices.get(row.get("id_urzadzenia"))
        if device is None:
            skipped["unknown device"] += 1
            continue

        component = row.get("typ_komponentu")
        item_type = item_type_for(component, device.code)
        if item_type is None:
            skipped[str(component)] += 1
            continue

        label = (row.get("opis_menu") or "").strip()
        if label in PLACEHOLDER_NAMES:
            skipped["placeholder"] += 1
            continue

        try:
            index = int(row["funkcja"])
        except (KeyError, TypeError, ValueError):
            skipped["bad index"] += 1
            continue
        if index < 1:
            skipped["bad index"] += 1
            continue

        if component == "temp" and index == 1 and device.code in FIXED_TEMPERATURE_CODES:
            skipped["fixed temperature sensor"] += 1
            continue

        bucket = names[device.mac][item_type]
        if index in bucket:
            skipped["duplicate index"] += 1
            continue
        bucket[index] = ItemName(
            base64encode(label),
            value_min=optional_int(row.get("min")),
            value_max=optional_int(row.get("max")),
        )

    if skipped:
        _LOGGER.debug(
            "Project database: skipped %s",
            ", ".join(f"{count} {reason}" for reason, count in skipped.most_common()),
        )

    return {mac: {t: dict(items) for t, items in types.items()} for mac, types in names.items()}


def parse_project_db(
    devices_payload: dict[str, Any], objects_payload: dict[str, Any]
) -> dict[str, dict[str, dict[int, ItemName]]]:
    """Build the per-module name map from both project tables."""
    devices = parse_devices(devices_payload)
    names = parse_objects(objects_payload, devices)
    _LOGGER.info(
        "Project database: %d devices, names for %d modules (%d items)",
        len(devices),
        len(names),
        sum(len(items) for types in names.values() for items in types.values()),
    )
    return names
