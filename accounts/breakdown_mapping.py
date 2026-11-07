import pandas as pd

from accounts.breakdown_event_category import normalize_event_category


MULTI_SOURCE_BREAKDOWN_FIELDS = {
    "loc_no": "_",
    "breakdown_remarks": "_",
}

REQUIRED_BREAKDOWN_FIELDS = {"gen_date", "loc_no", "breakdown_remarks"}


def canonicalize_breakdown_dataframe(dataframe, mappings):
    source_to_canonical = {
        mapping.source_header: mapping.canonical_header
        for mapping in mappings
    }
    available_mappings = {
        source: canonical
        for source, canonical in source_to_canonical.items()
        if source in dataframe.columns
    }
    missing_fields = REQUIRED_BREAKDOWN_FIELDS - set(available_mappings.values())
    if missing_fields:
        raise ValueError(
            "Breakdown sheet is missing mapped source columns for: "
            + ", ".join(sorted(missing_fields))
        )

    canonical_sources = {}
    for source, canonical in available_mappings.items():
        canonical_sources.setdefault(canonical, []).append(source)

    result = dataframe.copy()
    for canonical, sources in canonical_sources.items():
        if len(sources) == 1:
            result[canonical] = dataframe[sources[0]]
            continue

        separator = MULTI_SOURCE_BREAKDOWN_FIELDS.get(canonical)
        if separator is None:
            raise ValueError(
                f"Only these canonical fields support combining source columns: "
                f"{', '.join(sorted(MULTI_SOURCE_BREAKDOWN_FIELDS))}."
            )

        result[canonical] = dataframe[sources].apply(
            lambda row: separator.join(
                str(value).strip()
                for value in row
                if pd.notna(value) and str(value).strip()
            ),
            axis=1,
        ).replace("", None)

    if "event_category" in result:
        result["event_category"] = result["event_category"].map(
            normalize_event_category
        )

    return result, available_mappings
