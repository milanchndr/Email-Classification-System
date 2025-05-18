import os
from pathlib import Path
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# ------------------------TRAINING/FINETUNING------------------------

# refer to notebook for the training

# ------------------------INFERENCE------------------------

# Load fine-tuned model and tokenizer
MODEL_PATH = os.getenv("MODEL_PATH", Path(__file__).parent)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

#use this to directly access the finetuned classification model from huggingface
#model = AutoModelForSequenceClassification.from_pretrained("milanchndr/email-classification-model")
#tokenizer = AutoTokenizer.from_pretrained("milanchndr/email-classification-model")

model.eval()

label_map = {0: "Incident", 1: "Request", 2: "Change", 3: "Problem"}


def classify_email(email: str) -> str:
    """Classify an email into a support category using a fine-tuned model.

    Args:
        email (str): The email text to classify.

    Returns:
        str: The predicted category (Incident, Request, Change, or Problem).
    """
    inputs = tokenizer(
        email, padding=True, truncation=True, max_length=512, return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)
        pred = torch.argmax(probs, dim=1).item()
    return label_map[pred]
