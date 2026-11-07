from django.db import migrations


TAXONOMY_DETAILS = {
    "MDA10": (
        "Rotor blades and blade bearings",
        "rotor blade, blade shell, blade bearing, root bolts, blade inspection, "
        "rotor lock, pitch bearing raceway",
    ),
    "MDA20": (
        "Pitch system",
        "pitch motor, pitch drive, pitch converter, axis controller, pitch battery, "
        "pitch system, pitch error, feathering, emergency run",
    ),
    "MDK10": (
        "Main shaft and main bearing",
        "main shaft, main bearing, bearing housing, pillow block, plummer block, "
        "main shaft seal",
    ),
    "MDK20": (
        "Gearbox and mechanical brake",
        "gearbox, high speed shaft, planetary stage, mechanical brake, brake disk",
    ),
    "MDK30": (
        "Gearbox lubrication",
        "oil filter, lubrication pump, oil heat exchanger, gearbox oil, "
        "oil inlet temperature, oil tank",
    ),
    "MDE10": (
        "Generator stator and winding",
        "generator stator, stator winding, generator winding, slipring, slip ring, "
        "carbon brushes, insulation, phase sequence",
    ),
    "MDE20": (
        "Generator bearings",
        "generator bearing, generator drive end bearing, generator non drive end bearing, "
        "DE bearing, NDE bearing",
    ),
    "MDE30": (
        "Generator cooling",
        "generator cooling fan, cooling fan motor, generator heat exchanger, "
        "heat exchanger radiator, air ducts",
    ),
    "MDY10": (
        "Yaw drive",
        "yaw motor, yaw drive, yaw pinion, yaw counter sensor, nacelle position",
    ),
    "MDY20": (
        "Yaw bearing and brake",
        "yaw bearing, hydraulic yaw brake, yaw brake pucks, cable twist sensor",
    ),
    "MHD10": (
        "Hydraulic power unit",
        "hydraulic power unit, hydraulic motor, hydraulic pressure, HPU, accumulator, "
        "hydraulic oil reservoir, pressure relief valve",
    ),
    "MSA10": (
        "Power converter",
        "power converter, converter IGBT, IGBT stack, inverter, DC link, thyristor, "
        "converter capacitor bank, grid choke, water cooling unit",
    ),
    "MSA20": (
        "Internal feeder and protection",
        "internal feeder, protection relay, vacuum circuit breaker, VCB, switchgear, "
        "earth fault relay, overcurrent relay, CT PT metering, RMU",
    ),
    "MSA30": (
        "Transformer and busbar",
        "main transformer, nacelle transformer, busbar, Buchholz protection",
    ),
    "MKC10": (
        "Control, safety and wind sensors",
        "main PLC, nacelle PLC, tower PLC, anemometer, wind vane, safety chain, "
        "safety loop, emergency button, vibration switch",
    ),
    "MXA10": (
        "External grid and load shedding",
        "external grid, utility substation failure, load shedding, 33kV line trip, "
        "grid outage, grid failure, grid fault, grid downtime, external line breakdown",
    ),
    "UMD10": (
        "Tower and structure",
        "tower shell, nacelle frame, bedplate, foundation, anchor bolts",
    ),
}


def enrich_catalog(apps, schema_editor):
    catalog = apps.get_model("accounts", "RDSCatalog")
    for rds_code, (subsystem_name, added_keywords) in TAXONOMY_DETAILS.items():
        entry = catalog.objects.filter(rds_code=rds_code).first()
        if entry is None:
            continue
        existing_keywords = [
            keyword.strip()
            for keyword in (entry.canonical_keywords or "").split(",")
            if keyword.strip()
        ]
        existing_normalized = {keyword.casefold() for keyword in existing_keywords}
        for keyword in added_keywords.split(","):
            keyword = keyword.strip()
            if keyword.casefold() not in existing_normalized:
                existing_keywords.append(keyword)
                existing_normalized.add(keyword.casefold())
        entry.subsystem_name = entry.subsystem_name or subsystem_name
        entry.canonical_keywords = ", ".join(existing_keywords)
        entry.save(update_fields=["subsystem_name", "canonical_keywords"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_seed_rds_catalog_keywords"),
    ]

    operations = [
        migrations.RunPython(enrich_catalog, migrations.RunPython.noop),
    ]
