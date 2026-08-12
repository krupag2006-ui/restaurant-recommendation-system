import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [restaurant, setRestaurant] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const getRecommendations = async (restaurantName = restaurant) => {
    const name = restaurantName.trim();

    if (!name) {
      setError("Please enter a restaurant name.");
      setRecommendations([]);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/recommend/${encodeURIComponent(name)}?top_n=10`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.error || "Unable to fetch recommendations."
        );
      }

      if (data.error) {
        setError(data.error);
        setRecommendations([]);
        return;
      }

      // API returns:
      // {
      //   restaurant: "...",
      //   count: 10,
      //   recommendations: [...]
      // }

      setRecommendations(data.recommendations || data);
    } catch (err) {
      console.error("Recommendation error:", err);

      setError(
        "Something went wrong. Please make sure the recommendation API is running."
      );

      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    getRecommendations();
  };

  const handleSuggestion = (name) => {
    setRestaurant(name);
    getRecommendations(name);
  };

  const handleClear = () => {
    setRestaurant("");
    setRecommendations([]);
    setError("");
  };

  const getMatchPercentage = (item) => {
    const hybrid = Number(item.hybrid_score || 0);

    return Math.round(
      Math.max(0, Math.min(hybrid * 100, 100))
    );
  };

  const getRecommendationReasons = (item) => {
    const reasons = [];

    const similarity = Number(
      item.similarity_score || 0
    );

    const quality = Number(
      item.quality_score || 0
    );

    const votes = Number(
      item.votes || 0
    );

    if (similarity >= 0.65) {
      reasons.push("Similar cuisine");
    }

    if (quality >= 0.70) {
      reasons.push("High quality");
    }

    if (votes >= 500) {
      reasons.push("Popular");
    }

    if (item.location) {
      reasons.push("Nearby area");
    }

    // Always give the user at least one explanation.
    if (reasons.length === 0) {
      reasons.push("Similar restaurants");
    }

    return reasons.slice(0, 3);
  };

  return (
    <div className="app">

      {/* =====================================================
          HERO SECTION
      ===================================================== */}

      <section className="hero">

        <div className="hero-content">

          <div className="hero-badge">
            RESTAURANT RECOMMENDATION SYSTEM
          </div>

          <h1>
            Find your next
            <span> favorite restaurant.</span>
          </h1>

          <p className="hero-description">
            
          </p>

          {/* SEARCH */}

          <form
            className="search-form"
            onSubmit={handleSubmit}
          >

            <div className="search-input-wrapper">

              <span className="search-icon">
                ⌕
              </span>

              <input
                type="text"
                value={restaurant}
                onChange={(event) =>
                  setRestaurant(event.target.value)
                }
                placeholder="Enter a restaurant name..."
                aria-label="Restaurant name"
              />

              {restaurant && (
                <button
                  type="button"
                  className="clear-button"
                  onClick={handleClear}
                  aria-label="Clear restaurant"
                >
                  ×
                </button>
              )}

            </div>

            <button
              type="submit"
              className="recommend-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="button-spinner"></span>
                  Finding...
                </>
              ) : (
                <>
                  Recommend
                  <span>→</span>
                </>
              )}
            </button>

          </form>

          

          

        </div>

      </section>


      {/* =====================================================
          RESULTS SECTION
      ===================================================== */}

      <section className="results-section">

        <div className="results-container">

          <div className="results-header">

            <div>
              <div className="section-eyebrow">
                 Recommended Restaurants
              </div>

              
            </div>

            {recommendations.length > 0 && (
              <div className="recommendation-count">
                {recommendations.length} recommendations
              </div>
            )}

          </div>


          {/* ERROR */}

          {error && (
            <div className="error-message">
              <span>!</span>
              {error}
            </div>
          )}


          {/* LOADING */}

          {loading && (
            <div className="loading-container">

              <div className="loading-spinner"></div>

              <p>
                Finding the best restaurants for you...
              </p>

            </div>
          )}


          {/* EMPTY STATE */}

          {!loading &&
            !error &&
            recommendations.length === 0 && (
              <div className="empty-state">

                <div className="empty-icon">
                  🍽️
                </div>

                <h3>
                  Ready to discover something new?
                </h3>

                <p>
                  Search for a restaurant to get
                  personalized recommendations.
                </p>

              </div>
            )}


          {/* =================================================
              RECOMMENDATION CARDS
          ================================================= */}

          {!loading &&
            recommendations.length > 0 && (

              <div className="recommendations-grid">

                {recommendations.map(
                  (item, index) => {

                    const matchPercentage =
                      getMatchPercentage(item);

                    const reasons =
                      getRecommendationReasons(item);

                    const similarity =
                      Number(
                        item.similarity_score || 0
                      );

                    const quality =
                      Number(
                        item.quality_score || 0
                      );

                    const hybrid =
                      Number(
                        item.hybrid_score || 0
                      );

                    return (
                      <article
                        key={`${item.name}-${index}`}
                        className={`restaurant-card ${
                          index === 0
                            ? "best-match"
                            : ""
                        }`}
                      >

                        {/* RANK */}

                        <div className="card-top">

                          <div className="rank">
                            #{index + 1}
                          </div>

                          {index === 0 && (
                            <div className="best-match-badge">
                              ★ BEST MATCH
                            </div>
                          )}

                        </div>


                        {/* RESTAURANT INFORMATION */}

                        <div className="restaurant-info">

                          <h3 className="restaurant-name">
                            {item.name}
                          </h3>

                          <p className="restaurant-cuisines">
                            {item.cuisines ||
                              "Various cuisines"}
                          </p>

                          {item.location && (
                            <div className="restaurant-location">
                              <span>⌖</span>
                              {item.location}
                            </div>
                          )}

                        </div>


                        {/* RESTAURANT STATS */}

                        <div className="restaurant-stats">

                          <div className="stat-box">

                            <span className="stat-icon rating-icon">
                              ★
                            </span>

                            <div>
                              <span className="stat-value">
                                {item.rate !== null &&
                                item.rate !== undefined
                                  ? Number(
                                      item.rate
                                    ).toFixed(1)
                                  : "N/A"}
                              </span>

                              <span className="stat-label">
                                Rating
                              </span>
                            </div>

                          </div>


                          <div className="stat-box">

                            <span className="stat-icon votes-icon">
                              ♥
                            </span>

                            <div>
                              <span className="stat-value">
                                {Number(
                                  item.votes || 0
                                ).toLocaleString()}
                              </span>

                              <span className="stat-label">
                                Votes
                              </span>
                            </div>

                          </div>

                        </div>


                        {/* =================================================
                            WHY RECOMMENDED
                        ================================================= */}

                        <div className="why-recommended">
  <div className="why-title">
    <span>✦</span>
    Why recommended?
  </div>

  <div className="reason-tags">
  {item.reasons?.map((reason, i) => (
    <span key={i}>
      {reason}
      {i < item.reasons.length - 1 ? "," : ""}
    </span>
  ))}
</div>
</div>


                        {/* =================================================
                            MATCH SCORE
                            Percentage + progress bar ONLY
                        ================================================= */}

                        <div className="match-section">

                          <div className="match-row">

                            <strong className="match-percentage">
                              {matchPercentage}%
                            </strong>

                            <div className="progress-bar">

                              <div
                                className="progress-fill"
                                style={{
                                  width: `${matchPercentage}%`,
                                }}
                              />

                            </div>

                          </div>


                          {/* MODEL METRICS */}

                          <div className="score-details">

                            <div className="score-box">
                              <span>
                                Similarity
                              </span>

                              <strong>
                                {similarity.toFixed(3)}
                              </strong>
                            </div>

                            <div className="score-box">
                              <span>
                                Quality
                              </span>

                              <strong>
                                {quality.toFixed(3)}
                              </strong>
                            </div>

                            <div className="score-box">
                              <span>
                                Hybrid
                              </span>

                              <strong>
                                {hybrid.toFixed(3)}
                              </strong>
                            </div>

                          </div>

                        </div>

                      </article>
                    );
                  }
                )}

              </div>
            )}

        </div>

      </section>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      

    </div>
  );
}

export default App;