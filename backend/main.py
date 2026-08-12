from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.recommender import (
    hybrid_recommend_restaurants,
    generate_recommendation_reasons
)

app = FastAPI(
    title="Hybrid Restaurant Recommendation API",
    description="API for the Hybrid Restaurant Recommendation System",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "Restaurant Recommendation API is running!"
    }


@app.get("/recommend/{restaurant_name}")
def recommend(
    restaurant_name: str,
    top_n: int = 10
):
    recommendations = hybrid_recommend_restaurants(
        restaurant_name,
        top_n
    )

    if recommendations is None:
        return {
            "error": f"Restaurant '{restaurant_name}' not found"
        }

    results = []

    for _, row in recommendations.iterrows():

        item = row.to_dict()

        item["reasons"] = generate_recommendation_reasons(
            restaurant_name,
            item
        )

        results.append(item)

    return {
        "restaurant": restaurant_name,
        "count": len(results),
        "recommendations": results
    }