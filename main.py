from flask import Flask, request, jsonify
from utils import mask_pii, clean_text
from models import classify_email

app = Flask(__name__)


@app.route("/classify", methods=["POST"])
def email_processing_api():

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    input_email_body = data.get("input_email_body")

    if not input_email_body or not isinstance(input_email_body, str):
        return jsonify({"error": "Invalid or missing 'input_email_body'"}), 400

    try:
        # 1st we clean the text of html tags and normalize spaces
        cleaned_email_body = clean_text(input_email_body)

        # 2nd We do PII Masking
        # The mask_pii function in utils.py returns dictionary with
        # masked email and list of the entities

        masked_data = mask_pii(cleaned_email_body)
        masked_email_text = masked_data["masked_email"]
        list_of_entities = masked_data["list_of_masked_entities"]

        # 3rd we do classication of the masked email on a fined tuned model

        email_category = classify_email(masked_email_text)

        # then we give the response data in given api format

        response_data = {
            "input_email_body": input_email_body,
            "list_of_masked_entities": list_of_entities,
            "masked_email": masked_email_text,
            "category_of_the_email": email_category,
        }
        return jsonify(response_data), 200

    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error during /classify: {str(e)}")
        return (
            jsonify({"error": "An internal server error occurred", "details": str(e)}),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
