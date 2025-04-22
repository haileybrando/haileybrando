import os
import requests
from flask import Flask, request, jsonify
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
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")  # Store access token after OAuth

# Initialize Flask app
app = Flask(__name__)

def query_shopify_graphql(shop, access_token, query):
    """
    Function to send a GraphQL query to Shopify API
    """
    # Shopify GraphQL endpoint
    url = f"https://{shop}/admin/api/2023-01/graphql.json"  # You might need to adjust the API version

    # Headers to include the access token for authentication
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    # Send the request to Shopify's GraphQL API
    response = requests.post(url, headers=headers, json={"query": query})

    # Check for errors in the response
    if response.status_code != 200:
        raise Exception(f"GraphQL query failed with status {response.status_code}: {response.text}")

    # Return the response as JSON
    return response.json()

@app.route("/")
def home():
    return "Shopify OAuth App is running!"

# Example: Create Subscription (Step 2)
@app.route("/customer/<customer_id>/create-subscription", methods=["POST"])
def create_subscription(customer_id):
    shop = request.args.get("shop")
   
    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400
   
    subscription_mutation = f"""
    mutation {{
      subscriptionContractCreate(
        input: {{
          customerId: "gid://shopify/Customer/{customer_id}",
          nextBillingDate: "2025-04-05",
          currencyCode: USD,
          contract: {{
            note: "Note Attributes",
            status: ACTIVE,
            paymentMethodId: "gid://shopify/CustomerPaymentMethod/7d6c00b9085e977610b9a9d091bf3f20",
            billingPolicy: {{
              interval: WEEK,
              intervalCount: 1,
              minCycles: 3
            }},
            deliveryPolicy: {{
              interval: WEEK,
              intervalCount: 1
            }},
            deliveryPrice: 0.00,
            deliveryMethod: {{
              shipping: {{
                address: {{
                  firstName: "Nick",
                  lastName: "Murphy",
                  address1: "1353 South Glenmare Street",
                  address2: "#77",
                  city: "Salt Lake City",
                  province: "Utah",
                  country: "USA",
                  zip: "84105"
                }}
              }}
            }}
          }}
        }}
      ) {{
        draft {{
          id
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
   
    # Send GraphQL request to create subscription contract
    try:
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_mutation)
       
        # Log the response for debugging
        print("Shopify API Response:", response)

        # Check if the response contains user errors
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error creating subscription contract", "details": response["userErrors"]}), 400
       
        # If 'data' key doesn't exist, return an error with the whole response
        if "data" not in response:
            return jsonify({"error": "No data found in the response", "details": response}), 400

        # Return the draft ID
        draft_id = response["data"]["subscriptionContractCreate"]["draft"]["id"]
        return jsonify({"message": "Subscription contract draft created", "draft_id": draft_id})
   
    except Exception as e:
        # Catch any exceptions and return an error message
        return jsonify({"error": str(e)}), 500
       
@app.route("/customer/<customer_id>/subscription-contracts", methods=["GET"])
def get_subscription_contracts(customer_id):
    shop = request.args.get("shop")
    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400
   
    query = f"""
    query {{
      subscriptionContracts(first: 10, query: "customer:{customer_id}") {{
        edges {{
          node {{
            id
            createdAt
            status
            nextBillingDate
            customer {{
              firstName
              lastName
            }}
            billingPolicy {{
              interval
              intervalCount
            }}
            deliveryPolicy {{
              interval
              intervalCount
            }}
          }}
        }}
      }}
    }}
    """
   
    try:
        response = query_shopify_graphql(shop, ACCESS_TOKEN, query)
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error fetching subscription contracts", "details": response["userErrors"]}), 400
        if "data" not in response or not response["data"]["subscriptionContracts"]["edges"]:
            return jsonify({"error": "No subscription contracts found for this customer"}), 404
       
        contracts = response["data"]["subscriptionContracts"]["edges"]
        contract_data = [
            {
                "id": contract["node"]["id"],
                "createdAt": contract["node"]["createdAt"],
                "status": contract["node"]["status"],
                "nextBillingDate": contract["node"]["nextBillingDate"],
                "customer": contract["node"]["customer"],
                "billingPolicy": contract["node"]["billingPolicy"],
                "deliveryPolicy": contract["node"]["deliveryPolicy"]
            }
            for contract in contracts
        ]
       
        return jsonify({"subscription_contracts": contract_data})
   
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customer/<customer_id>/update-subscription", methods=["POST"])
def update_subscription(customer_id):
    shop = request.args.get("shop")
   
    # Get the parameters from the request body
    subscription_contract_id = request.json.get("subscription_contract_id")
    product_variant_id = request.json.get("product_variant_id")
    quantity = request.json.get("quantity")
    price = request.json.get("price")
   
    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400
   
    if not subscription_contract_id or not product_variant_id or quantity is None or price is None:
        return jsonify({"error": "Missing required parameters"}), 400
   
    # Step 1: Create a draft for the subscription contract
    subscription_contract_update_mutation = """
    mutation {
      subscriptionContractUpdate(
        contractId: \"%s\"
      ) {
        draft {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """ % subscription_contract_id
   
    try:
        # Send the mutation to update the subscription contract and create a draft
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_contract_update_mutation)
       
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error creating draft for subscription contract", "details": response["userErrors"]}), 400
       
        if "data" not in response or not response["data"]["subscriptionContractUpdate"]["draft"]:
            return jsonify({"error": "No draft returned in the response", "details": response}), 400
       
        # Get the draft ID from the response
        draft_id = response["data"]["subscriptionContractUpdate"]["draft"]["id"]

        # Step 2: Add the line to the draft (add product variant, price, quantity)
        subscription_draft_line_add_mutation = """
        mutation {
          subscriptionDraftLineAdd(
            draftId: \"%s\"
            input: {
              productVariantId: \"%s\"
              quantity: %d
              currentPrice: %f
            }
          ) {
            lineAdded {
              id
              quantity
              productId
              variantId
              variantImage {
                id
              }
              title
              variantTitle
              currentPrice {
                amount
                currencyCode
              }
              requiresShipping
              sku
              taxable
            }
            draft {
              id
            }
            userErrors {
              field
              message
              code
            }
          }
        }
        """ % (draft_id, product_variant_id, quantity, price)
       
        # Send the mutation to add a line to the draft
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_draft_line_add_mutation)
       
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error adding line to subscription draft", "details": response["userErrors"]}), 400
       
        if "data" not in response or not response["data"]["subscriptionDraftLineAdd"]["draft"]:
            return jsonify({"error": "No draft found after adding line", "details": response}), 400
       
        # Step 3: Commit the draft
        subscription_draft_commit_mutation = """
        mutation {
          subscriptionDraftCommit(draftId: \"%s\") {
            contract {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """ % draft_id
       
        # Send the mutation to commit the draft
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_draft_commit_mutation)
       
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error committing the draft", "details": response["userErrors"]}), 400
       
        if "data" not in response or not response["data"]["subscriptionDraftCommit"]["contract"]:
            return jsonify({"error": "No contract found after committing draft", "details": response}), 400
       
        # Return the contract ID of the committed draft
        contract_id = response["data"]["subscriptionDraftCommit"]["contract"]["id"]
       
        return jsonify({
            "message": "Subscription updated and committed successfully.",
            "contract_id": contract_id
        })
   
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customer/<customer_id>/add-line-to-subscription-draft", methods=["POST"])
def add_line_to_subscription_draft(customer_id):
    shop = request.args.get("shop")
   
    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400
   
    # Get the draft_id from the request body (you can also pass this via URL)
    draft_id = request.json.get("draft_id")
    product_variant_id = request.json.get("product_variant_id")
    quantity = request.json.get("quantity")
    price = request.json.get("price")
   
    if not draft_id or not product_variant_id or quantity is None or price is None:
        return jsonify({"error": "Missing required parameters"}), 400
   
    # Step: Add the line to the draft (add product variant, price, quantity)
    subscription_draft_line_add_mutation = """
    mutation {
      subscriptionDraftLineAdd(
        draftId: \"%s\"
        input: {
          productVariantId: \"%s\"
          quantity: %d
          currentPrice: %f
        }
      ) {
        lineAdded {
          id
          quantity
          productId
          variantId
          variantImage {
            id
          }
          title
          variantTitle
          currentPrice {
            amount
            currencyCode
          }
          requiresShipping
          sku
          taxable
        }
        draft {
          id
        }
        userErrors {
          field
          message
          code
        }
      }
    }
    """ % (draft_id, product_variant_id, quantity, price)
   
    try:
        # Send the mutation to add a line to the draft
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_draft_line_add_mutation)
       
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error adding line to subscription draft", "details": response["userErrors"]}), 400
       
        if "data" not in response or not response["data"]["subscriptionDraftLineAdd"]["draft"]:
            return jsonify({"error": "No draft found after adding line", "details": response}), 400
       
        # Return the draft ID of the updated draft
        updated_draft_id = response["data"]["subscriptionDraftLineAdd"]["draft"]["id"]
       
        return jsonify({
            "message": "Line added to subscription draft successfully.",
            "updated_draft_id": updated_draft_id
        })
   
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/customer/<customer_id>/commit-subscription-draft", methods=["POST"])
def commit_subscription_draft(customer_id):
    shop = request.args.get("shop")
    draft_id = request.json.get("draft_id")
   
    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400

    if not draft_id:
        return jsonify({"error": "Missing draft_id parameter"}), 400

    # GraphQL mutation to commit the subscription draft
    subscription_draft_commit_mutation = """
    mutation {{
      subscriptionDraftCommit(draftId: "{draft_id}") {{
        contract {{
          id
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
   
    try:
        # Send the GraphQL request to commit the draft
        response = query_shopify_graphql(shop, ACCESS_TOKEN, subscription_draft_commit_mutation)
       
        # Check for any user errors in the response
        if "userErrors" in response and response["userErrors"]:
            return jsonify({"error": "Error committing the subscription draft", "details": response["userErrors"]}), 400
       
        if "data" not in response or not response["data"]["subscriptionDraftCommit"]["contract"]:
            return jsonify({"error": "No contract returned after committing draft", "details": response}), 400
       
        # Return the contract ID after committing the draft
        contract_id = response["data"]["subscriptionDraftCommit"]["contract"]["id"]
       
        return jsonify({
            "message": "Subscription draft committed successfully.",
            "contract_id": contract_id
        })
   
    except Exception as e:
        # Catch any exceptions and return an error message
        return jsonify({"error": str(e)}), 500

@app.route("/customer/update-name", methods=["POST"])
def update_customer_name():
    shop = request.args.get("shop")

    if not shop or not ACCESS_TOKEN:
        return jsonify({"error": "Missing shop parameter or access token"}), 400

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
        response = query_shopify_graphql(shop, ACCESS_TOKEN, mutation)

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
