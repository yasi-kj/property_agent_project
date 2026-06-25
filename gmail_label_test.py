from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

LABEL_ID = "Label_259017680108222467"

creds = Credentials.from_authorized_user_file(
    "token.json",
    SCOPES
)

service = build("gmail", "v1", credentials=creds)

results = service.users().messages().list(
    userId="me",
    labelIds=[LABEL_ID],
    maxResults=20
).execute()

messages = results.get("messages", [])

print(f"Found {len(messages)} emails")

for msg in messages:
    message = service.users().messages().get(
        userId="me",
        id=msg["id"],
        format="metadata",
        metadataHeaders=["Subject"]
    ).execute()

    headers = message["payload"]["headers"]

    subject = next(
        (h["value"] for h in headers if h["name"] == "Subject"),
        "(No Subject)"
    )

    print(subject)