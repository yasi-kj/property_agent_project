from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

creds = Credentials.from_authorized_user_file("token.json", SCOPES)

service = build("gmail", "v1", credentials=creds)

results = service.users().labels().list(userId="me").execute()

labels = results.get("labels", [])

for label in labels:
    print(f"{label['name']} -> {label['id']}")