import os
import smtplib
from email.mime.text import MIMEText
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


@chat_bp.route("/email-debug", methods=["GET"])
def email_debug():
    """Diagnostic endpoint — tests SMTP config and optionally sends a test email.

    Usage:
      GET /api/email-debug              — show config + test SMTP connection
      GET /api/email-debug?to=a@b.com  — also send a test email to that address
    """
    info = {}

    server = current_app.config.get("MAIL_SERVER", "localhost")
    port   = int(current_app.config.get("MAIL_PORT", 25))
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@colloquyai.com")

    info["smtp_server"] = server
    info["smtp_port"]   = port
    info["sender"]      = sender

    # 1. Test TCP connection + EHLO
    try:
        with smtplib.SMTP(server, port, timeout=8) as smtp:
            code, ehlo_msg = smtp.ehlo()
            info["smtp_connected"] = True
            info["smtp_ehlo_code"] = code
            info["smtp_ehlo"]      = ehlo_msg.decode(errors="replace")
    except Exception as e:
        info["smtp_connected"] = False
        info["smtp_error"]     = str(e)
        return jsonify(info)

    # 2. Optional test send
    to_addr = request.args.get("to", "").strip()
    if to_addr:
        try:
            mime = MIMEText(
                "This is a test email from Prezent.Energy to verify SMTP delivery.", "plain", "utf-8"
            )
            mime["Subject"] = "Prezent.Energy — SMTP test"
            mime["From"]    = sender
            mime["To"]      = to_addr
            with smtplib.SMTP(server, port, timeout=8) as smtp:
                smtp.sendmail(sender, [to_addr], mime.as_string())
            info["test_email_sent"] = True
            info["test_email_to"]   = to_addr
        except Exception as e:
            info["test_email_sent"]  = False
            info["test_email_error"] = str(e)

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
