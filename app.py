from flask import Flask, render_template, jsonify, request
from terraria_engine import TerrariaEngine
import os

app = Flask(__name__)

# Global Terraria Engine instance
engine = TerrariaEngine()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify(engine.get_status())

@app.route("/api/init/models", methods=["POST"])
def init_models():
    success = engine.init_models()
    return jsonify({
        "success": success,
        "status": engine.get_status()
    })

@app.route("/api/init/dbs", methods=["POST"])
def init_dbs():
    success = engine.init_databases()
    return jsonify({
        "success": success,
        "status": engine.get_status()
    })

@app.route("/api/init/index", methods=["POST"])
def init_index():
    success = engine.build_wiki_index()
    return jsonify({
        "success": success,
        "status": engine.get_status()
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    
    if not question:
        return jsonify({"error": "Question is empty"}), 400
        
    try:
        response = engine.ask(question)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Ensure templates directory exists
    os.makedirs("templates", exist_ok=True)
    
    print("--------------------------------------------------")
    print(" Terraria Chat RAG Application starting...")
    print(" Point your browser to http://127.0.0.1:5000")
    print("--------------------------------------------------")
    app.run(host="127.0.0.1", port=5000, debug=True)
