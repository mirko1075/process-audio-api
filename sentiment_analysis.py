from transformers import pipeline
import nltk
nltk.download('punkt_tab', quiet=True)
from nltk.tokenize import sent_tokenize

# Initialize the sentiment pipeline with the Hospital_Reviews model
sentiment_pipeline = pipeline(
    "sentiment-analysis", 
    model="brettclaus/Hospital_Reviews", 
    tokenizer="brettclaus/Hospital_Reviews"
)

def run_sentiment_analysis(text):
    """
    Runs sentiment analysis using the brettclaus/Hospital_Reviews model.
    Splits the input text into sentences and returns a list of tuples
    (sentence, rating, confidence_percentage).
    
    The mapping here is an example:
      - If output label is "POSITIVE", rating is "5 stars"
      - If output label is "NEGATIVE", rating is "1 star"
      - Otherwise, rating is "3 stars"
    """
    sentences = sent_tokenize(text)
    results = []
    for sentence in sentences:
        output = sentiment_pipeline(sentence)[0]
        label = output['label']
        score = output['score']
        if label.upper() == "POSITIVE":
            rating = "5 stars"
        elif label.upper() == "NEGATIVE":
            rating = "1 star"
        else:
            rating = "3 stars"
        results.append((sentence, rating, score * 100))
    return {"sentiment_analysis": results}