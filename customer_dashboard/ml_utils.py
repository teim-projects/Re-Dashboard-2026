import pandas as pd
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class BreakdownMLAnalyzer:
    def __init__(self, similarity_threshold=0.60, days_window=8):
        """
        ML module for repetitive breakdown detection using TF-IDF.
        Includes severity classification using similarity + day gap.
        """
        self.similarity_threshold = similarity_threshold
        self.days_window = days_window
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.data = None

    # ---------------------------------------------------------
    # LOAD & CLEAN DATA
    # ---------------------------------------------------------
    def load_dataframe(self, df: pd.DataFrame):
        """Normalize and clean dataframe."""
        if df is None or df.empty:
            raise ValueError("Input DataFrame is empty.")

        df.columns = [
            str(column).strip().lower().replace(" ", "_")
            for column in df.columns
        ]

        header_aliases = {
            "gen_date": ("gen_date", "date", "generation_date", "breakdown_date"),
            "loc_no": ("loc_no", "location_no", "wtg", "wtg_no", "wec", "machine"),
            "breakdown_remarks": (
                "breakdown_remarks",
                "remarks",
                "remark",
                "breakdown_details",
                "description",
            ),
        }
        for canonical, aliases in header_aliases.items():
            if canonical not in df.columns:
                source = next((alias for alias in aliases if alias in df.columns), None)
                if source:
                    df = df.rename(columns={source: canonical})

        required = {"gen_date", "loc_no", "breakdown_remarks"}
        if not required.issubset(df.columns):
            raise KeyError(f"Missing columns: {required - set(df.columns)}")

        df["gen_date"] = pd.to_datetime(df["gen_date"], errors="coerce")
        df = df.dropna(subset=["gen_date", "loc_no", "breakdown_remarks"])
        df = df.sort_values(by=["loc_no", "gen_date"]).reset_index(drop=True)

        self.data = df
        return df

    # ---------------------------------------------------------
    # SEVERITY LOGIC (Improved)
    # ---------------------------------------------------------
    def classify_severity(self, similarity, day_gap):
        """
        Severity based on similarity + time gap.
        More realistic and avoids everything becoming Critical.
        """

        # CRITICAL: very high similarity within 2 days
        if similarity >= 0.85 and day_gap <= 2:
            return "Critical"

        # HIGH: very high similarity but not immediate
        if similarity >= 0.85 and day_gap > 2:
            return "High"

        # MEDIUM
        if similarity >= 0.70:
            return "Medium"

        # LOW
        return "Low"

    # ---------------------------------------------------------
    # DETECTION ENGINE
    # ---------------------------------------------------------
    def detect_repetitions(self):
        """
        Detect repetitive breakdowns using TF-IDF + Cosine Similarity.
        Returns list of alerts with message + severity.
        """

        if self.data is None:
            raise ValueError("Call load_dataframe() first.")

        alerts = []

        # Process each WTG
        for machine in self.data["loc_no"].unique():
            mdf = self.data[self.data["loc_no"] == machine].reset_index(drop=True)

            for i in range(len(mdf)):
                cur_date = mdf.loc[i, "gen_date"]
                cur_remark = mdf.loc[i, "breakdown_remarks"]
                current_rds_code = mdf.loc[i, "rds_code"] if "rds_code" in mdf else None
                if pd.isna(current_rds_code):
                    current_rds_code = None

                # Filter: previous remarks within time window
                window_df = mdf[
                    (mdf["gen_date"] < cur_date)
                    & (mdf["gen_date"] >= cur_date - timedelta(days=self.days_window))
                ]
                if window_df.empty:
                    continue

                # Prepare TF-IDF comparison list
                remarks_list = window_df["breakdown_remarks"].tolist() + [cur_remark]
                tfidf_matrix = self.vectorizer.fit_transform(remarks_list)

                similarities = cosine_similarity(
                    tfidf_matrix[-1], tfidf_matrix[:-1]
                )[0]

                # Evaluate each match
                for j, sim in enumerate(similarities):
                    if sim >= self.similarity_threshold:

                        previous_record = window_df.iloc[j]
                        prev_date = previous_record["gen_date"]
                        day_gap = abs((cur_date - prev_date).days)
                        severity = self.classify_severity(sim, day_gap)
                        rds_code = current_rds_code
                        system_name = mdf.loc[i, "system_name"] if "system_name" in mdf else None
                        subsystem_name = mdf.loc[i, "subsystem_name"] if "subsystem_name" in mdf else None
                        standard_component = mdf.loc[i, "standard_component"] if "standard_component" in mdf else None
                        system_name = None if pd.isna(system_name) else system_name
                        subsystem_name = None if pd.isna(subsystem_name) else subsystem_name
                        standard_component = (
                            None if pd.isna(standard_component) else standard_component
                        )

                        alerts.append({
                            "machine": str(machine),
                            "severity": severity,
                            "similarity": round(float(sim), 2),
                            "date": str(cur_date.date()),
                            "previous_date": str(prev_date.date()),
                            "rds_code": rds_code,
                            "system_name": system_name,
                            "subsystem_name": subsystem_name,
                            "standard_component": standard_component,
                            "day_gap": day_gap,
                            "message": (
                                f"⚠️ WTG {machine}: '{cur_remark}' repeated within last "
                                f"{self.days_window} days (previous on {prev_date.date()}, "
                                f"similarity={sim:.2f})"
                            ),
                        })

        return alerts


def detect_extended_breakdowns(events, history=None):
    """Flag events whose duration exceeds the prior P90 for their component."""
    if events is None or events.empty:
        return []
    if history is None:
        history = events

    required = {"gen_date", "loc_no", "duration_hours"}
    missing_columns = (required - set(events.columns)) | (
        required - set(history.columns)
    )
    if missing_columns:
        raise KeyError(f"Missing columns: {missing_columns}")

    def component_for(row):
        rds_value = row.get("rds_code")
        component_value = row.get("standard_component")
        rds_code = "" if pd.isna(rds_value) else str(rds_value).strip()
        component = (
            "" if pd.isna(component_value) else str(component_value).strip()
        )
        unusable = {"", "uncategorized", "unmapped", "unmapped remark", "unknown"}
        if rds_code.casefold() not in unusable:
            display_component = (
                component if component.casefold() not in unusable else rds_code
            )
            return ("rds", rds_code.casefold()), display_component, rds_code
        if component.casefold() not in unusable:
            return ("component", component.casefold()), component, ""
        return None, "", ""

    history_rows = []
    for _, row in history.iterrows():
        component_key, component, rds_code = component_for(row)
        event_date = pd.to_datetime(row["gen_date"], errors="coerce")
        duration = pd.to_numeric(row["duration_hours"], errors="coerce")
        if (
            component_key is None
            or pd.isna(event_date)
            or pd.isna(duration)
            or duration <= 0
        ):
            continue
        history_rows.append({
            "row": row,
            "component_key": component_key,
            "component": component,
            "rds_code": rds_code,
            "event_date": event_date,
            "duration": float(duration),
        })

    selected_indices = set(events.index)
    history_rows.sort(key=lambda item: item["event_date"])
    prior_durations = {}
    alerts = []
    index = 0

    while index < len(history_rows):
        event_date = history_rows[index]["event_date"]
        end_index = index
        while (
            end_index < len(history_rows)
            and history_rows[end_index]["event_date"] == event_date
        ):
            end_index += 1

        same_day_rows = history_rows[index:end_index]
        for item in same_day_rows:
            row = item["row"]
            if row.name not in selected_indices:
                continue
            previous_durations = prior_durations.get(item["component_key"], [])
            if not previous_durations:
                continue

            p90_hours = float(pd.Series(previous_durations).quantile(0.9))
            if item["duration"] <= p90_hours:
                continue

            machine = str(row.get("loc_no", "Unknown"))
            duration_hours = item["duration"]
            alerts.append({
                "machine": machine,
                "date": str(item["event_date"].date()),
                "severity": "Extended",
                "is_extended": True,
                "component": item["component"],
                "rds_code": item["rds_code"],
                "duration_hours": round(duration_hours, 2),
                "p90_hours": round(p90_hours, 2),
                "excess_hours": round(duration_hours - p90_hours, 2),
                "message": (
                    f"{item['component']} breakdown lasted {duration_hours:.2f} hours, "
                    f"exceeding its historical component P90 of {p90_hours:.2f} hours."
                ),
            })

        for item in same_day_rows:
            prior_durations.setdefault(item["component_key"], []).append(
                item["duration"]
            )
        index = end_index

    return alerts





import numpy as np
from sklearn.ensemble import RandomForestRegressor

def train_dsm_model(X, y):
    """
    Train RandomForest model for DSM deviation prediction
    """
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )
    model.fit(X, y)
    return model


def predict_deviation(model, X_future):
    """
    Predict deviation using trained model
    """
    return model.predict(X_future)