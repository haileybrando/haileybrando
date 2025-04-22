import os
import requests
from flask import Flask, request, jsonify, redirect, session, url_for
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Shopify API credentials
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv(
    "SHOPIFY_SCOPES",
    "read_customers,write_orders,read_orders,read_own_subscription_contracts,write_own_subscription_contracts,manage_orders_information,read_orders,write_orders",
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Example: Store access tokens in-memory for simplicity (use database in production)
ACCESS_TOKENS = {}

# Shopify OAuth URL
SHOPIFY_OAUTH_URL = "https://{shop}/admin/oauth/authorize"


@app.route("/")
def home():
    return "Shopify OAuth App is running!"


@app.route("/auth")
def auth():
    shop = request.args.get("shop")
    if not shop:
        return jsonify({"error": "Missing shop parameter"}), 400

    # Redirect user to Shopify OAuth authorization URL
    oauth_url = f"https://{shop}/admin/oauth/authorize?client_id={SHOPIFY_API_KEY}&scope={SCOPES}&redirect_uri={REDIRECT_URI}"
    return redirect(oauth_url)


@app.route("/auth/callback")
def auth_callback():
    shop = request.args.get("shop")
    code = request.args.get("code")

    if not shop or not code:
        return jsonify({"error": "Missing shop or code parameter"}), 400

    # Exchange the code for an access token
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }
   
    try:
        # Send the request to Shopify's access token endpoint
        response = requests.post(f"https://{shop}/admin/oauth/access_token", data=payload)
        data = response.json()

        if "access_token" not in data:
            return jsonify({"error": "Failed to retrieve access token"}), 400

        # Store the access token (for this example, we store it in memory)
        ACCESS_TOKENS[shop] = data["access_token"]

        return jsonify({"message": "Access token retrieved successfully!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def query_shopify_graphql(shop, access_token, query):
    """
    Function to send a GraphQL query to Shopify API
    """
    url = f"https://{shop}/admin/api/2023-01/graphql.json"  # Adjust the API version if necessary

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json={"query": query})

    if response.status_code != 200:
        raise Exception(f"GraphQL query failed with status {response.status_code}: {response.text}")

    return response.json()


@app.route("/customer/update-name", methods=["POST"])
def update_customer_name():
    shop = request.args.get("shop")
   
    if not shop:
        return jsonify({"error": "Missing shop parameter"}), 400
   
    access_token = ACCESS_TOKENS.get(shop)
    if not access_token:
        return jsonify({"error": "Access token is missing or expired. Please authenticate."}), 401

    data = request.get_json()
    customer_id = data.get("customer_id")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    if not customer_id or not first_name or not last_name:
        return jsonify({"error": "Missing required fields: customer_id, first_name, last_name"}), 400

    mutation = """
    mutation {
      customerUpdate(input: {
        id: "gid://shopify/Customer/%s",
        firstName: "%s",
        lastName: "%s"
      }) {
        customer {
          id
          firstName
          lastName
        }
        userErrors {
          field
          message
        }
      }
    }
    """ % (customer_id, first_name, last_name)

    try:
        response = query_shopify_graphql(shop, access_token, mutation)

        if "userErrors" in response["data"]["customerUpdate"] and response["data"]["customerUpdate"]["userErrors"]:
            return jsonify({
                "error": "Failed to update customer name",
                "details": response["data"]["customerUpdate"]["userErrors"]
            }), 400

        updated_customer = response["data"]["customerUpdate"]["customer"]
        return jsonify({
            "message": "Customer name updated successfully",
            "customer": updated_customer
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
