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

        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Expected mapping
        col_map = {
            "gen_date": "date",
            "loc_no": "machine",
            "breakdown_remarks": "remarks",
        }

        for old, new in col_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})

        # Ensure required columns exist
        required = {"date", "machine", "remarks"}
        if not required.issubset(df.columns):
            raise KeyError(f"Missing columns: {required - set(df.columns)}")

        # Clean & format
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "machine", "remarks"])
        df = df.sort_values(by=["machine", "date"]).reset_index(drop=True)

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
        for machine in self.data["machine"].unique():
            mdf = self.data[self.data["machine"] == machine].reset_index(drop=True)

            for i in range(len(mdf)):
                cur_date = mdf.loc[i, "date"]
                cur_remark = mdf.loc[i, "remarks"]

                # Filter: previous remarks within time window
                window_df = mdf[
                    (mdf["date"] < cur_date)
                    & (mdf["date"] >= cur_date - timedelta(days=self.days_window))
                ]

                if window_df.empty:
                    continue

                # Prepare TF-IDF comparison list
                remarks_list = window_df["remarks"].tolist() + [cur_remark]
                tfidf_matrix = self.vectorizer.fit_transform(remarks_list)

                similarities = cosine_similarity(
                    tfidf_matrix[-1], tfidf_matrix[:-1]
                )[0]

                # Evaluate each match
                for j, sim in enumerate(similarities):
                    if sim >= self.similarity_threshold:

                        prev_date = window_df.iloc[j]["date"]
                        day_gap = abs((cur_date - prev_date).days)
                        severity = self.classify_severity(sim, day_gap)

                        alerts.append({
                            "machine": str(machine),
                            "severity": severity,
                            "similarity": round(float(sim), 2),
                            "date": str(cur_date.date()),
                            "previous_date": str(prev_date.date()),
                            "day_gap": day_gap,
                            "message": (
                                f"⚠️ WTG {machine}: '{cur_remark}' repeated within last "
                                f"{self.days_window} days (previous on {prev_date.date()}, "
                                f"similarity={sim:.2f})"
                            )
                        })

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