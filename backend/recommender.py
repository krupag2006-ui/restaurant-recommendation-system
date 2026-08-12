import os
import re
import glob
import math
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")


# =========================================================
# FIND DATASET AUTOMATICALLY
# =========================================================

def find_dataset():
    csv_files = glob.glob(
        os.path.join(DATASET_DIR, "*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            "No CSV dataset found inside the dataset folder."
        )

    required_columns = {
        "name",
        "cuisines",
        "location"
    }

    for file in csv_files:
        try:
            temp = pd.read_csv(file, encoding="utf-8")

            if required_columns.issubset(
                set(temp.columns)
            ):
                return file

        except Exception:
            pass

    # Fallback to first CSV
    return csv_files[0]


DATASET_PATH = find_dataset()

print(f"Loading dataset: {DATASET_PATH}")


# =========================================================
# LOAD DATA
# =========================================================

try:
    df = pd.read_csv(
        DATASET_PATH,
        encoding="utf-8"
    )
except UnicodeDecodeError:
    df = pd.read_csv(
        DATASET_PATH,
        encoding="latin1"
    )


# =========================================================
# ENCODING CLEANUP
# =========================================================

def fix_encoding(text):

    if pd.isna(text):
        return text

    text = str(text)

    # Common mojibake markers
    bad_markers = (
        "Ã",
        "Â",
        "â",
        "ð",
        "�"
    )

    # Fix multiple levels of corruption
    for _ in range(3):

        if not any(
            marker in text
            for marker in bad_markers
        ):
            break

        try:
            fixed = text.encode(
                "latin1"
            ).decode(
                "utf-8"
            )

            if fixed == text:
                break

            text = fixed

        except (
            UnicodeEncodeError,
            UnicodeDecodeError
        ):
            break

    return text


TEXT_COLUMNS = [
    "name",
    "cuisines",
    "rest_type",
    "location",
    "restaurant_profile"
]


for column in TEXT_COLUMNS:

    if column in df.columns:

        df[column] = (
            df[column]
            .apply(fix_encoding)
            .fillna("")
        )


# =========================================================
# CLEAN COLUMN VALUES
# =========================================================

for column in [
    "name",
    "cuisines",
    "rest_type",
    "location",
    "restaurant_profile"
]:

    if column in df.columns:

        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
        )


# =========================================================
# NUMERIC COLUMNS
# =========================================================

if "rate" in df.columns:

    df["rate"] = (
        df["rate"]
        .astype(str)
        .str.extract(
            r"(\d+(?:\.\d+)?)"
        )[0]
    )

    df["rate"] = pd.to_numeric(
        df["rate"],
        errors="coerce"
    )

else:

    df["rate"] = 0.0


if "votes" in df.columns:

    df["votes"] = pd.to_numeric(
        df["votes"],
        errors="coerce"
    )

else:

    df["votes"] = 0


df["rate"] = df["rate"].fillna(0)

df["votes"] = df["votes"].fillna(0)


# =========================================================
# NORMALIZATION HELPERS
# =========================================================

def normalize_text(value):

    if pd.isna(value):
        return ""

    value = str(value).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def normalize_name(value):

    value = normalize_text(value)

    value = re.sub(
        r"[^a-z0-9\s]",
        "",
        value
    )

    return value


df["_normalized_name"] = (
    df["name"]
    .apply(normalize_name)
)


# =========================================================
# QUALITY SCORE
# =========================================================

# Rating contribution
rate_score = (
    df["rate"] / 5.0
).clip(
    lower=0,
    upper=1
)


# Popularity contribution
log_votes = np.log1p(
    df["votes"]
)

if log_votes.max() > 0:

    vote_score = (
        log_votes /
        log_votes.max()
    )

else:

    vote_score = 0


# Quality = 70% rating + 30% popularity
df["quality_score"] = (
    0.70 * rate_score +
    0.30 * vote_score
).clip(
    lower=0,
    upper=1
)


# =========================================================
# TEXT USED FOR TF-IDF
# =========================================================

def build_profile(row):

    parts = []

    for column in [
        "cuisines",
        "rest_type",
        "location",
        "restaurant_profile"
    ]:

        if column in row.index:

            value = str(
                row[column]
            ).strip()

            if value and value.lower() != "nan":

                parts.append(value)

    return " ".join(parts)


df["_profile_text"] = (
    df.apply(
        build_profile,
        axis=1
    )
)


# =========================================================
# TF-IDF MODEL
# =========================================================

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    min_df=2,
    max_features=10000
)


tfidf_matrix = vectorizer.fit_transform(
    df["_profile_text"]
)


print(
    f"Final dataset shape: {df.shape}"
)

print(
    f"TF-IDF matrix shape: {tfidf_matrix.shape}"
)


# =========================================================
# SEARCH RESTAURANT
# =========================================================

def find_restaurant(
    restaurant_name
):

    query = normalize_name(
        restaurant_name
    )

    if not query:
        return None


    # -----------------------------------------
    # Exact match
    # -----------------------------------------

    exact = df[
        df["_normalized_name"] == query
    ]

    if not exact.empty:

        # If duplicates exist,
        # choose highest quality
        return exact[
            "quality_score"
        ].idxmax()


    # -----------------------------------------
    # Partial match
    # -----------------------------------------

    partial = df[
        df["_normalized_name"]
        .str.contains(
            query,
            regex=False,
            na=False
        )
    ]

    if partial.empty:
        return None


    return partial[
        "quality_score"
    ].idxmax()


# =========================================================
# RECOMMENDATION REASONS
# =========================================================

def generate_recommendation_reasons(
    restaurant_name,
    recommendation
):

    reasons = []


    source_matches = df[
        df["_normalized_name"]
        == normalize_name(
            restaurant_name
        )
    ]


    if source_matches.empty:

        # Partial search fallback
        source_idx = find_restaurant(
            restaurant_name
        )

        if source_idx is None:

            return [
                "Strong overall match"
            ]

        source = df.loc[
            source_idx
        ]

    else:

        source = source_matches.iloc[0]


    # =====================================================
    # CUISINE
    # =====================================================

    source_cuisines = set(
        normalize_text(
            source.get(
                "cuisines",
                ""
            )
        )
        .replace(",", " ")
        .split()
    )


    recommendation_cuisines = set(
        normalize_text(
            recommendation.get(
                "cuisines",
                ""
            )
        )
        .replace(",", " ")
        .split()
    )


    common_cuisines = (
        source_cuisines &
        recommendation_cuisines
    )


    if common_cuisines:

        reasons.append(
            "Similar cuisine"
        )


    # =====================================================
    # LOCATION
    # =====================================================

    source_location = normalize_text(
        source.get(
            "location",
            ""
        )
    )


    recommendation_location = normalize_text(
        recommendation.get(
            "location",
            ""
        )
    )


    if (
        source_location
        and recommendation_location
        and source_location
        == recommendation_location
    ):

        reasons.append(
            "Nearby area"
        )


    # =====================================================
    # QUALITY
    # =====================================================

    quality_score = float(
        recommendation.get(
            "quality_score",
            0
        )
    )


    if quality_score >= 0.70:

        reasons.append(
            "High quality"
        )


    # =====================================================
    # POPULARITY
    # =====================================================

    votes = float(
        recommendation.get(
            "votes",
            0
        )
    )


    if votes >= 500:

        reasons.append(
            "Popular"
        )


    # =====================================================
    # SIMILARITY
    # =====================================================

    similarity_score = float(
        recommendation.get(
            "similarity_score",
            0
        )
    )


    if (
        similarity_score >= 0.70
        and "Similar cuisine"
        not in reasons
    ):

        reasons.append(
            "Highly similar"
        )


    # =====================================================
    # FALLBACK
    # =====================================================

    if not reasons:

        reasons.append(
            "Strong overall match"
        )


    return reasons[:3]


# =========================================================
# MAIN HYBRID RECOMMENDER
# =========================================================

def hybrid_recommend_restaurants(
    restaurant_name,
    top_n=10,
    cuisine=None,
    location=None,
    min_rating=None,
    min_votes=None
):

    if not restaurant_name:
        return None


    # -----------------------------------------
    # Clean top_n
    # -----------------------------------------

    try:

        top_n = int(top_n)

    except:

        top_n = 10


    top_n = max(
        1,
        min(top_n, 50)
    )


    # -----------------------------------------
    # Find source restaurant
    # -----------------------------------------

    source_idx = find_restaurant(
        restaurant_name
    )


    if source_idx is None:

        return None


    # -----------------------------------------
    # Query TF-IDF
    # -----------------------------------------

    query_vector = tfidf_matrix[
        source_idx
    ]


    # IMPORTANT:
    # Only calculate similarity against
    # the single query vector.
    #
    # We DO NOT calculate the complete
    # 41K x 41K similarity matrix.

    similarity_scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    ).flatten()


    # -----------------------------------------
    # Candidate dataframe
    # -----------------------------------------

    candidates = df.copy()


    candidates[
        "similarity_score"
    ] = similarity_scores


    # -----------------------------------------
    # Remove same restaurant
    # -----------------------------------------

    source_normalized = normalize_name(
        restaurant_name
    )


    candidates = candidates[
        candidates["_normalized_name"]
        != source_normalized
    ]


    # -----------------------------------------
    # Cuisine filter
    # -----------------------------------------

    if cuisine:

        cuisine_query = normalize_text(
            cuisine
        )

        candidates = candidates[
            candidates["cuisines"]
            .apply(
                lambda x:
                cuisine_query
                in normalize_text(x)
            )
        ]


    # -----------------------------------------
    # Location filter
    # -----------------------------------------

    if location:

        location_query = normalize_text(
            location
        )

        candidates = candidates[
            candidates["location"]
            .apply(
                lambda x:
                location_query
                in normalize_text(x)
            )
        ]


    # -----------------------------------------
    # Rating filter
    # -----------------------------------------

    if min_rating is not None:

        try:

            min_rating = float(
                min_rating
            )

            candidates = candidates[
                candidates["rate"]
                >= min_rating
            ]

        except:

            pass


    # -----------------------------------------
    # Votes filter
    # -----------------------------------------

    if min_votes is not None:

        try:

            min_votes = int(
                min_votes
            )

            candidates = candidates[
                candidates["votes"]
                >= min_votes
            ]

        except:

            pass


    if candidates.empty:

        return pd.DataFrame()


    # -----------------------------------------
    # Hybrid score
    # -----------------------------------------

    candidates[
        "hybrid_score"
    ] = (
        0.70
        * candidates["similarity_score"]
        +
        0.30
        * candidates["quality_score"]
    )


    # -----------------------------------------
    # Sort
    # -----------------------------------------

    candidates = candidates.sort_values(
        by="hybrid_score",
        ascending=False
    )


    # -----------------------------------------
    # Remove duplicate restaurant names
    # -----------------------------------------

    candidates = candidates.drop_duplicates(
        subset=["_normalized_name"],
        keep="first"
    )


    # -----------------------------------------
    # Top N
    # -----------------------------------------

    recommendations = candidates.head(
        top_n
    ).copy()


    # -----------------------------------------
    # Round scores
    # -----------------------------------------

    for column in [
        "similarity_score",
        "quality_score",
        "hybrid_score"
    ]:

        recommendations[column] = (
            recommendations[column]
            .round(6)
        )


    # -----------------------------------------
    # Select useful columns
    # -----------------------------------------

    output_columns = [
        "name",
        "cuisines",
        "rest_type",
        "location",
        "rate",
        "votes",
        "similarity_score",
        "quality_score",
        "hybrid_score"
    ]


    output_columns = [
        column
        for column in output_columns
        if column in recommendations.columns
    ]


    return recommendations[
        output_columns
    ].reset_index(
        drop=True
    )


# =========================================================
# FILTER OPTIONS
# =========================================================

def get_filter_options():

    cuisines = set()

    locations = set()


    # -----------------------------------------
    # Cuisines
    # -----------------------------------------

    if "cuisines" in df.columns:

        for value in df["cuisines"].dropna():

            for cuisine in str(
                value
            ).split(","):

                cuisine = cuisine.strip()

                if cuisine:

                    cuisines.add(
                        cuisine
                    )


    # -----------------------------------------
    # Locations
    # -----------------------------------------

    if "location" in df.columns:

        for value in df["location"].dropna():

            location = str(
                value
            ).strip()

            if location:

                locations.add(
                    location
                )


    return {
        "cuisines": sorted(
            cuisines,
            key=str.lower
        ),

        "locations": sorted(
            locations,
            key=str.lower
        )
    }


# =========================================================
# EVALUATION
# =========================================================

def evaluate_recommendations(
    recommendations
):

    if (
        recommendations is None
        or len(recommendations) == 0
    ):

        return {
            "count": 0,
            "average_similarity": 0,
            "average_quality": 0,
            "average_hybrid": 0,
            "unique_restaurants": 0,
            "unique_locations": 0
        }


    result = recommendations.copy()


    # -----------------------------------------
    # Averages
    # -----------------------------------------

    average_similarity = float(
        result[
            "similarity_score"
        ].mean()
    )


    average_quality = float(
        result[
            "quality_score"
        ].mean()
    )


    average_hybrid = float(
        result[
            "hybrid_score"
        ].mean()
    )


    # -----------------------------------------
    # Diversity / coverage
    # -----------------------------------------

    unique_restaurants = int(
        result[
            "name"
        ].nunique()
    )


    if "location" in result.columns:

        unique_locations = int(
            result[
                "location"
            ].nunique()
        )

    else:

        unique_locations = 0


    # -----------------------------------------
    # Score spread
    # -----------------------------------------

    if len(result) > 1:

        score_std = float(
            result[
                "hybrid_score"
            ].std()
        )

    else:

        score_std = 0


    return {

        "count": int(
            len(result)
        ),

        "average_similarity": round(
            average_similarity,
            4
        ),

        "average_quality": round(
            average_quality,
            4
        ),

        "average_hybrid": round(
            average_hybrid,
            4
        ),

        "unique_restaurants":
            unique_restaurants,

        "unique_locations":
            unique_locations,

        "hybrid_score_std": round(
            score_std,
            4
        )
    }


# =========================================================
# STARTUP INFO
# =========================================================

print(
    f"Loaded {len(df)} restaurants."
)

print(
    f"Suspicious encoding rows: "
    f"{sum(df['name'].astype(str).str.contains('Ã|Â|â|�', regex=True, na=False))}"
)