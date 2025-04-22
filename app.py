
import requests
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Get environment variables for Shopify API credentials
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

@app.route("/auth/callback")
def auth_callback():
    shop = request.args.get("shop")
    code = request.args.get("code")

    if not shop or not code:
        return jsonify({"error": "Invalid request, missing 'shop' or 'code' parameter"}), 400

    # Prepare the URL to exchange the authorization code for an access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }

    # Send request to Shopify to exchange the code for an access token
    response = requests.post(token_url, json=payload)

    # Check if the response is successful
    if response.status_code != 200:
        return jsonify({"error": "Error retrieving access token", "details": response.json()}), 400

    # Extract the access token from the response
    access_token = response.json().get("access_token")

    # Literally print the access token as plain text in the terminal or log
    print(f"Shopify Access Token: {access_token}")

    # Return the access token as part of the response (for debugging)
    return jsonify({
        "message": "Authorization successful",
        "shop": shop,
        "access_token": access_token,
    })

# To run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
