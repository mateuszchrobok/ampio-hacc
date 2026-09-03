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
    own component type and ``opis_menu`` is the human name.
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
PLACEHOLDER_NAMES = frozenset({"", "ND", "N/D", "-"})

# Component types deliberately not turned into entities:
#   satel_*      the Satel alarm is already exposed as an alarm_control_panel, and
#                these rows alone number in the thousands
#   lin_wej      MSENS channels, built from fixed topics by MSENSModuleInfo
#   rgbw         built from fixed topics by MRGBu1ModuleInfo
#   custom, event, bit8, bit16, flaga_liniowa, tekst_can, kamera_rtsp,
#   stacja_elsner, symulacja, detekcja, wykres
#                project-side constructs with no Ampio state topic of their own
IGNORED_COMPONENT_TYPES = frozenset(
    {
        "satel_wej",
        "satel_wyj",
        "satel_alarm",
        "lin_wej",
        "rgbw",
        "custom",
        "event",
        "bit8",
        "bit16",
        "flaga_liniowa",
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
    names: dict[str, dict[str, dict[int, ItemName]]] = defaultdict(
        lambda: defaultdict(dict)
    )
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

        if (
            component == "temp"
            and index == 1
            and device.code in FIXED_TEMPERATURE_CODES
        ):
            skipped["fixed temperature sensor"] += 1
            continue

        bucket = names[device.mac][item_type]
        if index in bucket:
            skipped["duplicate index"] += 1
            continue
        bucket[index] = ItemName(base64encode(label))

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
