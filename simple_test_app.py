"""Simple test version of Flask app to isolate issues."""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Simple test app working"})

@app.route('/')
def root():
    return jsonify({"message": "Simple Flask test app"})

if __name__ == '__main__':
    print("Starting simple test Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)