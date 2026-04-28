from flask import Flask, jsonify, request
from requests.exceptions import RequestException

from scraper import scrape_product


app = Flask(__name__)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/api/scrape")
def scrape() -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Missing 'url' in request body."}), 400

    try:
        result = scrape_product(url)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RequestException as exc:
        return jsonify({"error": f"Failed to fetch URL: {exc}"}), 502
    except Exception:
        return jsonify({"error": "Unexpected scraper error."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
