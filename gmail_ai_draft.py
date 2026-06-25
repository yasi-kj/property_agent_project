import json
import base64
from pathlib import Path
from email.mime.text import MIMEText

from bs4 import BeautifulSoup
from openai import OpenAI

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import os.path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose"
]

LABEL_ID = "Label_259017680108222467"

client = OpenAI()
MODEL = "gpt-4.1-mini"


def get_gmail_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def decode_base64url(data):
    decoded_bytes = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    return decoded_bytes.decode("utf-8", errors="ignore")


def extract_body(payload):
    if "body" in payload and payload["body"].get("data"):
        text = decode_base64url(payload["body"]["data"])
        if payload.get("mimeType") == "text/html":
            return BeautifulSoup(text, "html.parser").get_text("\n")
        return text

    for part in payload.get("parts", []):
        result = extract_body(part)
        if result:
            return result

    return ""


def analyze_email(email_text):
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": "You are an AI property maintenance coordination assistant."
            },
            {
                "role": "user",
                "content": f"""
Analyze this tenant maintenance email.

Rules:
- Do not send emails.
- Create drafts only for human review.
- Do not invent missing information.
- If the issue is unclear, mark as NEEDS REVIEW.

Priority rules:
HIGH:
- no heat
- flooding
- water on the floor
- active leak causing damage
- burning smell
- electrical danger
- lockout
- safety concern
- refrigerator not cooling and food is spoiling

MEDIUM:
- leak without water damage
- appliance not working
- no hot water
- repeated maintenance issue
- keypad or building access issue that does not fully lock tenant out
- outlets/lights not working without danger indicators

LOW:
- dripping faucet
- cosmetic issue
- general question
- non-urgent scheduling

NEEDS REVIEW:
- issue is unclear
- unit/property is missing
- email does not describe what is broken
- multiple unrelated issues are mentioned

Contractor routing:
- Plumbing, leaks, flooding, dripping faucet, no hot water → Plumber
- Electrical outlets, breaker issues, burning smell, lights → Licensed Electrician
- No heat, AC issues, furnace noise, heating/cooling → HVAC Technician
- Dishwasher, fridge, stove, washer/dryer → Appliance Repair Technician
- Lockout, lost key, keypad, door access → Locksmith or Access Control Technician
- Unknown issue → No contractor until clarified

Return valid JSON only with:
request_type, issue_category, priority, priority_reason, unit_or_property,
tenant_name, issue_summary, missing_information, recommended_contractor_type,
recommended_action, draft_tenant_response, draft_contractor_message, status,
confidence_score.

Email:
{email_text}
"""
            }
        ],
        text={"format": {"type": "json_object"}}
    )

    return json.loads(response.output_text)


def create_gmail_draft(service, to_email, subject, body_text):
    message = MIMEText(body_text)
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw_message
        }
    }

    draft = service.users().drafts().create(
        userId="me",
        body=draft_body
    ).execute()

    return draft


def get_header(headers, name, default=""):
    return next(
        (h["value"] for h in headers if h["name"].lower() == name.lower()),
        default
    )


def main():
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        labelIds=[LABEL_ID],
        maxResults=10
    ).execute()

    messages = results.get("messages", [])

    print(f"Found {len(messages)} emails")

    output_folder = Path("gmail_ai_outputs")
    output_folder.mkdir(exist_ok=True)

    for msg in messages:
        full_msg = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = full_msg["payload"]["headers"]

        subject = get_header(headers, "Subject", "(No Subject)")
        sender = get_header(headers, "From", "")
        body = extract_body(full_msg["payload"])

        assembled_email = f"""
Subject: {subject}
From: {sender}

{body}
"""

        print(f"Analyzing: {subject}")

        analysis = analyze_email(assembled_email)

        output_path = output_folder / f"{msg['id']}.json"
        output_path.write_text(
            json.dumps(analysis, indent=2),
            encoding="utf-8"
        )

        draft_subject = f"Re: {subject}"

        draft_body = f"""
Hi,

{analysis.get("draft_tenant_response")}

---

AI Review Summary:
Request Type: {analysis.get("request_type")}
Issue Category: {analysis.get("issue_category")}
Priority: {analysis.get("priority")}
Reason: {analysis.get("priority_reason")}
Unit/Property: {analysis.get("unit_or_property")}
Recommended Contractor: {analysis.get("recommended_contractor_type")}
Confidence: {analysis.get("confidence_score")}

Recommended Action:
{analysis.get("recommended_action")}

Note: This draft was generated by the Property Maintenance AI Agent and should be reviewed before sending.
"""

        draft = create_gmail_draft(
            service=service,
            to_email=sender,
            subject=draft_subject,
            body_text=draft_body
        )

        print(f"Draft created: {draft.get('id')}")

    print("Done. Check your Gmail Drafts folder.")


if __name__ == "__main__":
    main()