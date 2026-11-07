from django.db import migrations


CATALOG_KEYWORDS = {
    "MDA10": "rotor blade, blade shell, blade bearing, root bolts, pitch bearing raceway",
    "MDA20": "pitch motor, pitch drive, pitch converter, axis controller, pitch battery, pitch system",
    "MDK10": "main shaft, main bearing, bearing housing, pillow block, main shaft seal",
    "MDK20": "gearbox, high speed shaft, planetary stage, mechanical brake disk",
    "MDK30": "oil filter, lubrication pump, oil heat exchanger, gearbox oil, oil inlet temperature",
    "MDE10": "generator stator, stator winding, generator winding, slipring, carbon brushes, insulation",
    "MDE20": "generator bearing, drive end bearing, non drive end bearing, DE bearing, NDE bearing",
    "MDE30": "generator cooling fan, cooling fan motor, heat exchanger radiator, air ducts",
    "MDY10": "yaw motor, yaw drive, yaw pinion, yaw counter sensor",
    "MDY20": "yaw bearing, hydraulic yaw brake, yaw brake pucks, cable twist sensor",
    "MHD10": "hydraulic power unit, HPU, accumulator, hydraulic oil reservoir, pressure relief valve",
    "MSA10": "power converter, IGBT, converter capacitor bank, grid choke, water cooling unit",
    "MSA20": "internal feeder, protection relay, vacuum circuit breaker, VCB, earth fault relay, overcurrent relay, CT PT metering",
    "MSA30": "main transformer, nacelle transformer, busbar, Buchholz protection",
    "MKC10": "main PLC, nacelle PLC, tower PLC, anemometer, wind vane, safety chain",
    "MXA10": "external grid, utility substation failure, load shedding, 33kV line trip, grid outage",
    "UMD10": "tower shell, nacelle frame, bedplate, foundation, anchor bolts",
}


def seed_keywords(apps, schema_editor):
    catalog = apps.get_model("accounts", "RDSCatalog")
    for rds_code, keywords in CATALOG_KEYWORDS.items():
        catalog.objects.filter(rds_code=rds_code).update(
            canonical_keywords=keywords
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_rdscatalog_canonical_keywords_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_keywords, migrations.RunPython.noop),
    ]
