import os
from flask import Blueprint, request, jsonify, current_app
from agents.chatbot import get_chat_response
from agents.news_agent import query_news_agent

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat-debug", methods=["GET"])
def chat_debug():
    """Diagnostic endpoint — visit in browser to check server-side config."""
    info = {}

    # 1. API key presence
    api_key = current_app.config.get("ANTHROPIC_API_KEY", "")
    info["api_key_set"] = bool(api_key)
    info["api_key_prefix"] = api_key[:8] + "..." if api_key else "(empty)"

    # 2. anthropic package
    try:
        import anthropic as _a
        info["anthropic_version"] = _a.__version__
    except Exception as e:
        info["anthropic_import_error"] = str(e)

    # 3. Quick API call (haiku, 5 tokens)
    if api_key:
        try:
            import anthropic as _a
            c = _a.Anthropic(api_key=api_key)
            r = c.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            info["api_call"] = "ok — " + r.content[0].text
        except Exception as e:
            info["api_call_error"] = str(e)

    # 4. env file path check
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    info["env_file_exists"] = os.path.isfile(os.path.normpath(env_path))

    return jsonify(info)


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
        # Use 200 so Apache/cPanel doesn't intercept and replace the JSON body
        return jsonify({"error": "AI service unavailable"}), 200


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
        # Use 200 so Apache/cPanel doesn't intercept and replace the JSON body
        return jsonify({"error": "AI service unavailable"}), 200


def current_app_logger_safe(e):
    try:
        from flask import current_app
        current_app.logger.error(str(e))
    except Exception:
        print(str(e))
