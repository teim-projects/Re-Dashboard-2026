from django.db import migrations


CATALOG_DATA = [
    {
        "rds_code": "MDA10",
        "system_code": "MDA",
        "system_name": "Rotor System (MDA)",
        "standard_component": "Rotor Blade & Blade Bearing",
        "description": "Blade shell, root bolts, pitch bearing raceway",
    },
    {
        "rds_code": "MDA20",
        "system_code": "MDA",
        "system_name": "Rotor System (MDA)",
        "standard_component": "Pitch Motor / Drive / Converter",
        "description": "Pitch motor, pitch drive, axis controller, pitch battery",
    },
    {
        "rds_code": "MDK10",
        "system_code": "MDK",
        "system_name": "Drive Train (MDK)",
        "standard_component": "Main Shaft & Main Bearing",
        "description": "Main bearing housing, pillow block, main shaft seal",
    },
    {
        "rds_code": "MDK20",
        "system_code": "MDK",
        "system_name": "Drive Train (MDK)",
        "standard_component": "Gearbox & Mechanical Brake",
        "description": "High speed shaft, planetary stage, mechanical brake disk",
    },
    {
        "rds_code": "MDK30",
        "system_code": "MDK",
        "system_name": "Drive Train (MDK)",
        "standard_component": "Gearbox & Oil Filter / Pump",
        "description": "Inline oil filter, lubrication pump motor, oil heat exchanger",
    },
    {
        "rds_code": "MDE10",
        "system_code": "MDE",
        "system_name": "Generator System (MDE)",
        "standard_component": "Generator Stator / Winding / Slipring",
        "description": "Stator winding, rotor slipring, carbon brushes, insulation",
    },
    {
        "rds_code": "MDE20",
        "system_code": "MDE",
        "system_name": "Generator System (MDE)",
        "standard_component": "Generator DE / NDE Bearing",
        "description": "Drive end (DE) and Non-drive end (NDE) bearings",
    },
    {
        "rds_code": "MDE30",
        "system_code": "MDE",
        "system_name": "Generator System (MDE)",
        "standard_component": "Generator Cooling Fan / Heat Exchanger",
        "description": "Cooling fan motor, heat exchanger radiator, air ducts",
    },
    {
        "rds_code": "MDY10",
        "system_code": "MDY",
        "system_name": "Yaw System (MDY)",
        "standard_component": "Yaw Motor & Yaw Drive",
        "description": "Yaw pinion, yaw drive motor, yaw counter sensor",
    },
    {
        "rds_code": "MDY20",
        "system_code": "MDY",
        "system_name": "Yaw System (MDY)",
        "standard_component": "Yaw Bearing & Hydraulic Brake",
        "description": "Yaw bearing rim, hydraulic yaw brake pucks, cable twist sensor",
    },
    {
        "rds_code": "MHD10",
        "system_code": "MHD",
        "system_name": "Hydraulic System (MHD)",
        "standard_component": "Hydraulic Power Unit & Accumulator",
        "description": "HPU motor, hydraulic oil reservoir, pressure relief valve, accumulator",
    },
    {
        "rds_code": "MSA10",
        "system_code": "MSA",
        "system_name": "Electrical System (MSA)",
        "standard_component": "Power Converter & IGBT Module",
        "description": "IGBT stack, converter capacitor bank, grid choke, water cooling unit",
    },
    {
        "rds_code": "MSA20",
        "system_code": "MSA",
        "system_name": "Electrical System (MSA)",
        "standard_component": "Internal Feeder & Protection Relay",
        "description": "Vacuum circuit breaker (VCB), E/F relay, O/C relay, CT/PT metering",
    },
    {
        "rds_code": "MSA30",
        "system_code": "MSA",
        "system_name": "Electrical System (MSA)",
        "standard_component": "Main Transformer & Busbar",
        "description": "Nacelle/Pad-mounted transformer, HV busbar, Buchholz protection",
    },
    {
        "rds_code": "MKC10",
        "system_code": "MKC",
        "system_name": "Control & Safety (MKC)",
        "standard_component": "Main PLC & Wind Sensors",
        "description": "Main nacelle/tower PLC, ultrasonic anemometer, wind vane, safety chain",
    },
    {
        "rds_code": "MXA10",
        "system_code": "MXA",
        "system_name": "Grid & Environmental (MXA)",
        "standard_component": "External Grid Line Outage / Load Shedding",
        "description": "External 33kV line trip, utility substation failure, load shedding",
    },
    {
        "rds_code": "UMD10",
        "system_code": "UMD",
        "system_name": "Tower & Structure (UMD)",
        "standard_component": "Tower, Nacelle Frame & Foundation",
        "description": "Tower shell, flange bolts, bedplate frame, foundation anchor bolts",
    },
]


def seed_rds_catalog(apps, schema_editor):
    RDSCatalog = apps.get_model("accounts", "RDSCatalog")
    for entry in CATALOG_DATA:
        RDSCatalog.objects.update_or_create(
            rds_code=entry["rds_code"],
            defaults={
                "system_code": entry["system_code"],
                "system_name": entry["system_name"],
                "standard_component": entry["standard_component"],
                "description": entry["description"],
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_rdscatalog"),
    ]

    operations = [
        migrations.RunPython(seed_rds_catalog, migrations.RunPython.noop),
    ]
