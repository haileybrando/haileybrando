import os
import requests
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Route to handle Shopify OAuth callback
@app.route("/auth/callback")
def auth_callback():
    # Retrieve parameters from the query string
    shop = request.args.get("shop")
    code = request.args.get("code")
    app = request.args.get("app", "default")  # Optional: Add 'app' parameter to differentiate between apps if needed
   
    # If 'shop' or 'code' are not provided, return an error
    if not shop or not code:
        return jsonify({"error": "Invalid request, missing 'shop' or 'code' parameter"}), 400
   
    # Use the appropriate app's credentials (check if 'app' is 'new_app', otherwise use default)
    if app == "new_app":
        api_key = os.getenv("NEW_SHOPIFY_API_KEY")
        api_secret = os.getenv("NEW_SHOPIFY_API_SECRET")
    else:
        api_key = os.getenv("SHOPIFY_API_KEY")
        api_secret = os.getenv("SHOPIFY_API_SECRET")

    # Prepare the URL to exchange the authorization code for an access token
    token_url = f"https://{shop}/admin/oauth/access_token"
   
    # Prepare payload to exchange the code for an access token
    payload = {
        "client_id": api_key,
        "client_secret": api_secret,
        "code": code,
    }
   
    # Send the request to Shopify to exchange the code for an access token
    response = requests.post(token_url, json=payload)

    # Check if the response is successful
    if response.status_code != 200:
        return jsonify({"error": "Error retrieving access token", "details": response.json()}), 400

    # Extract the access token from the response
    access_token = response.json().get("access_token")

    # Print the access token to the console (or log it for debugging)
    print(f"Access Token for shop {shop}: {access_token}")

    # Return the access token and shop details in the response (for debugging purposes)
    return jsonify(
        {
            "message": "Authorization successful",
            "shop": shop,
            "access_token": access_token,
# To run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
