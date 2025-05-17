import re
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """
    Remove HTML tags and normalize whitespace in the input text.
    """
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def setup_presidio_analyzer():
    analyzer = AnalyzerEngine()

    # Aadhar number pattern recognization
    aadhar_pattern = Pattern(
        name="AADHAR_PATTERN", 
        regex=r"\b\d{4}\s\d{4}\s\d{4}\b", 
        score=0.9
    )
    aadhar_recognizer = PatternRecognizer(
        supported_entity="AADHAR_NUM", 
        patterns=[aadhar_pattern]
    )

    #  credit card: 16 digits in groups of 4 
    credit_card_pattern = Pattern(
        name="CREDIT_CARD_PATTERN", 
        regex=r"\b(?:\d{4}[-\s]?){3}\d{4}\b", 
        score=0.85
    )
    credit_card_recognizer = PatternRecognizer(
        supported_entity="CREDIT_DEBIT_NO", 
        patterns=[credit_card_pattern]
    )

    # Expiry date: MM/YY or MM/YYYY
    expiry_pattern = Pattern(
        name="EXPIRY_PATTERN", 
        regex=r"\b(0[1-9]|1[0-2])[/\-](0?[0-9]|[0-9]{2}|[0-9]{4})\b", 
        score=0.8
    )
    expiry_recognizer = PatternRecognizer(
        supported_entity="EXPIRY_NO", 
        patterns=[expiry_pattern]
    )

    # DOB: DD-MM-YYYY or DD/MM/YYYY
    dob_pattern = Pattern(
        name="DOB_PATTERN", 
        regex=r"\b(0[1-9]|[12][0-9]|3[01])[-/](0[1-9]|1[0-2])[-/](19|20)\d{2}\b", 
        score=0.9
    )
    dob_recognizer = PatternRecognizer(
        supported_entity="DOB", 
        patterns=[dob_pattern]
    )

    # Phone number
    phone_pattern = Pattern(
        name="PHONE_PATTERN", 
        regex=r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", 
        score=0.8
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER", 
        patterns=[phone_pattern]
    )

    # Register recognizers
    analyzer.registry.add_recognizer(credit_card_recognizer)
    analyzer.registry.add_recognizer(aadhar_recognizer)
    analyzer.registry.add_recognizer(expiry_recognizer)
    analyzer.registry.add_recognizer(dob_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)

    return analyzer


def post_process_dates(text: str, entities: List[Dict]) -> List[Dict]:
    """Reclassify dates based on context keywords."""
    for entity in entities:
        if entity["entity_type"] in ["DOB", "EXPIRY_NO"]:
            start, end = entity["start"], entity["end"]
            context_start = max(0, start - 30)
            context_end = min(len(text), end + 30)
            snippet = text[context_start:context_end].lower()
            
            # Keywords for DOB
            dob_keywords = ["born", "birth", "dob", "date of birth"]
            # Keywords for expiry
            expiry_keywords = ["expiry", "exp", "expires", "valid until", "valid till"]
            
            if any(keyword in snippet for keyword in dob_keywords):
                entity["entity_type"] = "DOB"
            elif any(keyword in snippet for keyword in expiry_keywords):
                entity["entity_type"] = "EXPIRY_NO"
    
    return entities


def resolve_overlapping_entities(entities: List[Dict]) -> List[Dict]:
    """Remove overlapping entities, keeping the one with higher confidence."""
    if not entities:
        return entities
    
    # Sort by start position
    entities.sort(key=lambda x: x["start"])
    
    resolved_entities = []
    for current in entities:
        if not resolved_entities:
            resolved_entities.append(current)
            continue
        
        last = resolved_entities[-1]
        
        # Check for overlap
        if current["start"] < last["end"]:
            current_score = current.get("score", 0)
            last_score = last.get("score", 0)
            current_length = current["end"] - current["start"]
            last_length = last["end"] - last["start"]
            
            if (current_score > last_score or 
                (current_score == last_score and current_length > last_length)):
                # Replace last with current
                resolved_entities[-1] = current
        else:
            # No overlap, add current entity
            resolved_entities.append(current)
    
    return resolved_entities


def detect_cvv_from_context(text: str) -> List[Dict]:
    """
    Detect CVV numbers based on context keywords and patterns
    """
    cvv_entities = []
    
    # CVV keywords that typically precede CVV numbers
    cvv_keywords = [
        r"cvv",
        r"cvc", 
        r"security\s+code",
        r"card\s+verification",
        r"verification\s+code",
        r"card\s+security\s+code",
        r"three\s+digit\s+code",
        r"four\s+digit\s+code"
    ]
    
    # Search keyword patterns
    for keyword in cvv_keywords:
        # keyword followed by optional separators and 3-4 digits
        pattern = rf"(?i){keyword}[\s:,\-]*(\d{{3,4}})"
        
        for match in re.finditer(pattern, text):
            cvv_digits = match.group(1)
            digit_start = match.start(1)
            digit_end = match.end(1)
            
            #validation to ensure it's likely a CVV
            if len(cvv_digits) in [3, 4]:
                # Checking context to avoid false positives
                context_start = max(0, match.start() - 20)
                context_end = min(len(text), match.end() + 20)
                context = text[context_start:context_end].lower()
                
                # Keywords to avoid in cvv dectection
                false_positive_keywords = [
                    "year", "date", "phone", "zip", "postal", 
                    "age", "quantity", "amount", "price"
                ]
                
                # Checking for a false positive
                is_likely_cvv = not any(fp_keyword in context for fp_keyword in false_positive_keywords)
                
                if is_likely_cvv:
                    cvv_entities.append({
                        "entity_type": "CVV_NO",
                        "start": digit_start,
                        "end": digit_end,
                        "entity": cvv_digits,
                        "score": 0.9,
                        "context": context.strip()
                    })
    
    # Also looking for standalone 3-4 digit numbers near card-related keywords
    card_keywords = [
        r"card", r"credit", r"debit", r"payment", r"expire", r"expiry", r"valid"
    ]
    
    # Find all 3-4 digi
    digit_pattern = r"\b(\d{3,4})\b"
    for digit_match in re.finditer(digit_pattern, text):
        digit_text = digit_match.group(1)
        digit_start = digit_match.start(1)
        digit_end = digit_match.end(1)
        
        # Checking if this digit sequence is near card-related keywords
        context_start = max(0, digit_start - 50)
        context_end = min(len(text), digit_end + 50)
        context = text[context_start:context_end].lower()
        
        # Checking if card-related keywords in context
        has_card_context = any(re.search(rf"\b{keyword}\b", context) for keyword in card_keywords)
        
        # Checking for things to avoid card, price or date
        likely_cvv_context = (
            has_card_context and 
            not re.search(r"\d{4}[-/]\d{2}[-/]\d{2,4}", context) and 
            not re.search(r"\$\d+", context) and 
            not re.search(r"\d{4}\s*\d{4}\s*\d{4}\s*\d{4}", context) and 
            len(digit_text) in [3, 4]
        )
        
        if likely_cvv_context:
            # To avoid duplicates
            is_duplicate = any(
                existing["start"] == digit_start and existing["end"] == digit_end 
                for existing in cvv_entities
            )
            
            if not is_duplicate:
                cvv_entities.append({
                    "entity_type": "CVV_NO",
                    "start": digit_start,
                    "end": digit_end,
                    "entity": digit_text,
                    "score": 0.7, 
                    "context": context.strip()
                })
    
    return cvv_entities


def mask_pii(text: str) -> Dict[str, Any]:
    """
    Mask personally identifiable information in the given text.
  
    """
    analyzer = setup_presidio_analyzer()
    anonymizer = AnonymizerEngine()

    # Clean the input text
    cleaned_text = clean_text(text)

    # Detect PII on cleaned text
    analyzer_results = analyzer.analyze(
        text=cleaned_text,
        entities=[
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", 
            "DOB", "AADHAR_NUM", "CREDIT_DEBIT_NO", 
            "EXPIRY_NO"
        ],
        language="en"
    )

    # Map entity types to consistent naming
    entity_mapping = {
        "PERSON": "full_name",
        "EMAIL_ADDRESS": "email",
        "PHONE_NUMBER": "phone_number",
        "DOB": "dob",
        "AADHAR_NUM": "aadhar_num",
        "CREDIT_DEBIT_NO": "credit_debit_no",
        "CVV_NO": "cvv_no",
        "EXPIRY_NO": "expiry_no",
    }

    # Convert analyzer results to our format
    entities = []
    for result in analyzer_results:
        entity_type = result.entity_type
        start, end = result.start, result.end
        entity_text = cleaned_text[start:end]
        score = result.score
        
        entities.append({
            "entity_type": entity_type,
            "start": start,
            "end": end,
            "entity": entity_text,
            "score": score
        })

    # context-based CVV detection
    cvv_entities = detect_cvv_from_context(cleaned_text)
    entities.extend(cvv_entities)

    # Post-process dates based on context
    entities = post_process_dates(cleaned_text, entities)
    
    # Resolving overlapping entities
    entities = resolve_overlapping_entities(entities)

    # final masked entities list
    masked_entities = []
    for entity in entities:
        classification = entity_mapping.get(entity["entity_type"], entity["entity_type"].lower())
        masked_entities.append({
            "position": [entity["start"], entity["end"]],
            "classification": classification,
            "entity": entity["entity"],
        })

    # Sort entities by position
    masked_entities.sort(key=lambda x: x["position"][0])

    # Recreate analyzer results for anonymization with resolved positions
    final_analyzer_results = []
    for entity in entities:
        from presidio_analyzer import RecognizerResult
        result = RecognizerResult(
            entity_type=entity["entity_type"],
            start=entity["start"],
            end=entity["end"],
            score=entity.get("score", 0.9)
        )
        final_analyzer_results.append(result)

    # Anonymize the cleaned text
    anonymized = anonymizer.anonymize(
        text=cleaned_text,
        analyzer_results=final_analyzer_results,
        operators={
            "PERSON": OperatorConfig("replace", {"new_value": "[full_name]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[email]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[phone_number]"}),
            "DOB": OperatorConfig("replace", {"new_value": "[dob]"}),
            "AADHAR_NUM": OperatorConfig("replace", {"new_value": "[aadhar_num]"}),
            "CREDIT_DEBIT_NO": OperatorConfig("replace", {"new_value": "[credit_debit_no]"}),
            "CVV_NO": OperatorConfig("replace", {"new_value": "[cvv_no]"}),
            "EXPIRY_NO": OperatorConfig("replace", {"new_value": "[expiry_no]"}),
        }
    )

    return {
        "masked_email": anonymized.text,
        "list_of_masked_entities": masked_entities,
    }