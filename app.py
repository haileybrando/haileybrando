import os
import requests
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Shopify API credentials (replace these with your actual credentials)
SHOPIFY_STORE = "embroidery-library-store.myshopify.com"  # Replace with your shop's domain
SHOPIFY_API_KEY = "a2864994dba16baa5174280483d4d3c4"
SHOPIFY_API_SECRET = "c74a38999e1578218de359ec4cbeb847"
ACCESS_TOKEN = "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"  # Admin Access Token

# Shopify GraphQL endpoint URL
GRAPHQL_URL = f"https://{SHOPIFY_STORE}/admin/api/2023-01/graphql.json"

# Headers for authentication and content type
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# GraphQL Mutation to update customer info
def create_update_customer_mutation(customer_id, first_name, last_name, email, birthday, billing_address):
    mutation = """
    mutation {
        customerUpdate(input: {
            id: "gid://shopify/Customer/%s",
            firstName: "%s",
            lastName: "%s",
            email: "%s",
            birthday: "%s",
            defaultAddress: {
                address1: "%s",
                city: "%s",
                province: "%s",
                country: "%s",
                zip: "%s"
            }
        }) {
            customer {
                id
                firstName
                lastName
                email
                birthday
            }
            userErrors {
                field
                message
            }
        }
    }
    """ % (
        customer_id, first_name, last_name, email, birthday,
        billing_address.get("address1", ""),
        billing_address.get("city", ""),
        billing_address.get("province", ""),
        billing_address.get("country", ""),
        billing_address.get("zip", "")
    )
    return mutation

@app.route("/update-customer", methods=["POST"])
def update_customer_info():
    # Get the request data (JSON payload)
    data = request.get_json()

    # Required fields from the payload
    customer_id = data.get("customer_id")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    birthday = data.get("birthday")  # Optional, in format 'YYYY-MM-DD'
    billing_address = data.get("billing_address", {})

    # Check for missing required fields
    if not customer_id or not first_name or not last_name or not email:
        return jsonify({"error": "Missing required fields: customer_id, first_name, last_name, email"}), 400

    # Prepare the GraphQL mutation
    mutation = create_update_customer_mutation(
        customer_id, first_name, last_name, email, birthday, billing_address
    )

    # Send the request to Shopify's GraphQL API
    response = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": mutation})

    # Check if the response was successful
    if response.status_code != 200:
        return jsonify({"error": "Failed to update customer", "details": response.json()}), 400

    # Parse the response JSON
    response_data = response.json()

    # Check for user errors in the response
    if "data" in response_data and "customerUpdate" in response_data["data"]:
        user_errors = response_data["data"]["customerUpdate"]["userErrors"]
        if user_errors:
            return jsonify({"error": "User errors during update", "details": user_errors}), 400

    # Return success message with updated customer info
    updated_customer = response_data["data"]["customerUpdate"]["customer"]
    return jsonify({
        "message": "Customer information updated successfully",
        "customer": updated_customer
    })

if __name__ == "__main__":
    app.run(debug=True)
