
# Email Classification System

## Overview

This project implements an email classification system designed for a company's support team. The system categorizes incoming support emails into predefined categories (Incident, Request, Change, Problem) while ensuring that Personally Identifiable Information (PII) and Payment Card Industry (PCI) data are masked before processing. The masked data details are provided alongside the classification.

The PII masking is achieved using rule-based methods (Presidio and custom regular expressions) without relying on Large Language Models (LLMs), while the email classification uses a fine-tuned `mdeberta-v3-base` transformer model.

The system is exposed via a Flask API.

## Features

*   **Email Classification**: Classifies emails into one of four categories:
    *   Incident
    *   Request
    *   Change
    *   Problem
*   **PII Masking (Non-LLM)**: Detects and masks the following PII types:
    *   Full Name (`full_name`)
    *   Email Address (`email`)
    *   Phone Number (`phone_number`)
    *   Date of Birth (`dob`)
    *   Aadhar Card Number (`aadhar_num`)
    *   Credit/Debit Card Number (`credit_debit_no`)
    *   CVV Number (`cvv_no`)
    *   Card Expiry Number (`expiry_no`)
*   **API Endpoint**: Provides a `POST /classify` endpoint for processing emails.
*   **Fine-tuned Model**: Utilizes a `microsoft/mdeberta-v3-base` model fine-tuned on a custom email dataset.

## File Structure

```
.
├── .gitattributes                  # Git LFS attributes
├── added_tokens.json               # Tokenizer additional tokens
├── config.json                     # Model configuration
├── emails.csv                      # Dataset for training and testing
├── finetuning_notebook_mdeberta.ipynb # Jupyter notebook for model fine-tuning
├── main.py                         # Flask API application
├── model.safetensors               # Fine-tuned model weights (LFS tracked)
├── models.py                       # Model loading and classification logic
├── requirements.txt                # Python dependencies
├── special_tokens_map.json         # Tokenizer special tokens mapping
├── spm.model                       # SentencePiece model for tokenizer
├── tokenizer.json                  # Main tokenizer file
├── tokenizer_config.json           # Tokenizer configuration
└── utils.py                        # PII masking and text cleaning utilities
```

## Technology Stack

*   **Python 3.10**
*   **Flask**: For the API.
*   **Transformers (Hugging Face)**: For the mDeBERTa-v3 model and tokenizer.
*   **PyTorch**: As the backend for the Transformers model.
*   **Presidio (Analyzer & Anonymizer)**: For PII detection and masking.
*   **Scikit-learn**: For utility functions like class weight computation.
*   **Pandas**: For data manipulation in the notebook.
*   **Spacy**: Dependency for Presidio.

## Setup and Installation

1.  **Prerequisites**:
    *   Git
    *   Git LFS (Large File Storage): Install Git LFS from [here](https://git-lfs.com).
    *   Python 3.11+
    *   A virtual environment (recommended).

2.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd Email-Classification-System
    ```

3.  **Initialize Git LFS and Pull LFS Files**:
    ```bash
    git lfs install
    git lfs pull
    ```
    This will download the `model.safetensors` file.

4.  **Create and Activate a Virtual Environment**:
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

5.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    This will also download necessary Spacy models for Presidio.

## Model Training

The email classification model (`microsoft/mdeberta-v3-base`) was fine-tuned using the `finetuning_notebook_mdeberta.ipynb` notebook. The notebook details the data preprocessing, training arguments, and evaluation steps. The `emails.csv` file is used as the dataset.

The fine-tuned model files (`config.json`, `model.safetensors`, `spm.model`, etc.) are included in this repository, allowing the application to run without retraining.

## PII Masking

PII masking is handled by `utils.py`. It uses:
*   **Presidio Analyzer**: To detect entities like PERSON, EMAIL_ADDRESS, etc.
*   **Custom PatternRecognizers**: For Aadhar numbers, credit card numbers, expiry dates, DOBs, and phone numbers using regular expressions.
*   **Contextual CVV Detection**: Custom logic to identify CVV numbers based on keywords and proximity to card-related terms.
*   **Post-processing**: To disambiguate date types (DOB vs. Expiry) and resolve overlapping entities.
*   **Presidio Anonymizer**: To replace detected PII with placeholders (e.g., `[full_name]`).

## API Usage

### Running the API

To start the Flask API server:
```bash
python main.py
```
The API will be available at `http://127.0.0.1:5000`.

### Endpoint

*   **URL**: `/classify`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

### Request Body

The API expects a JSON payload with the following structure:
```json
{
  "input_email_body": "string containing the email text"
}
```

**Example:**
```json
{
  "input_email_body": "Hello, my name is John Doe, my email is john.doe@example.com and my phone is 123-456-7890. I need help with my account. My card ending 1234 expires 12/25, CVV 789."
}
```

### Response Body

The API returns a JSON response with the following structure:

```json
{
  "input_email_body": "string containing the original email",
  "list_of_masked_entities": [
    {
      "position": [start_index, end_index],
      "classification": "entity_type",
      "entity": "original_entity_value"
    }
    // ... more entities
  ],
  "masked_email": "string containing the email with PII masked",
  "category_of_the_email": "string containing the predicted class"
}
```

**Example Response:**
```json
{
    "input_email_body": "Hello, my name is John Doe, my email is john.doe@example.com and my phone is 123-456-7890. I need help with my account. My card ending 1234 expires 12/25, CVV 789.",
    "list_of_masked_entities": [
        {
            "position": [18, 26],
            "classification": "full_name",
            "entity": "John Doe"
        },
        {
            "position": [39, 59],
            "classification": "email",
            "entity": "john.doe@example.com"
        },
        {
            "position": [75, 87],
            "classification": "phone_number",
            "entity": "123-456-7890"
        },
        {
            "position": [131, 136],
            "classification": "expiry_no",
            "entity": "12/25"
        },
        {
            "position": [143, 146],
            "classification": "cvv_no",
            "entity": "789"
        }
    ],
    "masked_email": "Hello, my name is [full_name], my email is [email] and my phone is [phone_number]. I need help with my account. My card ending 1234 expires [expiry_no], CVV [cvv_no].",
    "category_of_the_email": "Request"
}
```
*(Note: The exact masked entities and classification may vary based on the model's and Presidio's behavior.)*

### Example Request using `curl`

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{
  "input_email_body": "Hello, my name is Jane Smith, born on 01/01/1990. My Aadhar is 1234 5678 9012. Please reset my password. My credit card is 4567-8901-2345-6789."
}' \
http://127.0.0.1:5000/classify
```

## Deployment


This application is deployed on **Hugging Face Spaces**.
*   **API Endpoint**: [https://milanchndr-email-support-system.hf.space/classify](https://milanchndr-email-support-system.hf.space/classify)

```
