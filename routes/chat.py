from flask import Blueprint, request, jsonify
from agents.chatbot import get_chat_response
from agents.news_agent import query_news_agent

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])

    if not messages or not isinstance(messages, list):
        return jsonify({"error": "messages array is required"}), 400

    # Validate basic structure
    for msg in messages:
        if msg.get("role") not in ("user", "assistant") or not msg.get("content"):
            return jsonify({"error": "each message needs role and content"}), 400

    try:
        reply = get_chat_response(messages)
        return jsonify({"reply": reply})
    except Exception as e:
        current_app_logger_safe(e)
        return jsonify({"error": "AI service unavailable"}), 503


@chat_bp.route("/news-query", methods=["POST"])
def news_query():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    history = data.get("history", [])

    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        answer = query_news_agent(query, history)
        return jsonify({"answer": answer})
    except Exception as e:
        current_app_logger_safe(e)
        return jsonify({"error": "AI service unavailable"}), 503


def current_app_logger_safe(e):
    try:
        from flask import current_app
        current_app.logger.error(str(e))
    except Exception:
        print(str(e))
