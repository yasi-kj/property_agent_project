from openai import OpenAI
from pathlib import Path
import json

client = OpenAI()

MODEL = "gpt-4.1-mini"

def analyze_email(email_text):
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": """
You are an AI property maintenance coordination assistant.

Your job is to classify tenant maintenance emails, extract key details,
assess priority, recommend the right contractor type, and create draft
messages for human review.

You must be consistent, cautious, and structured.
Do not send emails.
Do not make final decisions.
Do not invent missing information.
"""
            },
            {
                "role": "user",
                "content": f"""
Analyze the tenant email below.

Priority rules:

HIGH priority:
- no heat
- flooding
- water on the floor
- active leak causing damage
- burning smell
- electrical danger
- lockout
- safety concern
- refrigerator not cooling and food is spoiling
- electrical issues are HIGH only if they mention burning smell, sparks, smoke, shock, exposed wires, fire risk, or safety danger. 

MEDIUM priority:
- leak without water damage
- appliance not working
- no hot water
- repeated maintenance issue
- keypad or building access issue that does not fully lock tenant out
- outlets/lights not working without danger indicators

LOW priority:
- dripping faucet
- cosmetic issue
- general maintenance question
- non-urgent scheduling

NEEDS REVIEW:
- issue is unclear
- unit/property is missing
- email does not describe what is broken
- multiple unrelated issues are mentioned

Contractor routing rules:
- Plumbing, leaks, flooding, dripping faucet, no hot water → Plumber
- Electrical outlets, breaker issues, burning smell, lights → Licensed Electrician
- No heat, AC issues, furnace noise, heating/cooling issues → HVAC Technician
- Dishwasher, fridge, stove, washer/dryer → Appliance Repair Technician
- Lockout, lost key, keypad, door access → Locksmith or Access Control Technician
- Unknown issue → No contractor until clarified

Missing information rules:
Only ask for missing information if it is necessary to:
- identify the issue
- determine urgency
- schedule repair
- access the unit
- contact the tenant

Do not over-request information.
If the unit number is provided, do not say unit is missing.
If the issue is clear, do not ask for unnecessary details.

Standardize missing values as:
"Not provided"

Return valid JSON only with these keys:

request_type
issue_category
priority
priority_reason
unit_or_property
tenant_name
issue_summary
missing_information
recommended_contractor_type
recommended_action
draft_tenant_response
draft_contractor_message
status
confidence_score

Confidence score should be between 0 and 1:
- 0.90 to 1.00 = very confident
- 0.70 to 0.89 = needs human review
- below 0.70 = manual triage recommended

Email:
{email_text}
"""
            }
        ],
        text={
            "format": {
                "type": "json_object"
            }
        }
    )

    return json.loads(response.output_text)

def create_output_file(email_name, analysis):
    output_folder = Path("draft_outputs")
    output_folder.mkdir(exist_ok=True)

    confidence = analysis.get("confidence_score", "Not provided")

    output = f"""
AI PROPERTY MAINTENANCE REVIEW

Request Type: {analysis.get("request_type")}
Issue Category: {analysis.get("issue_category")}
Priority: {analysis.get("priority")}
Priority Reason: {analysis.get("priority_reason")}
Confidence Score: {confidence}

Tenant Name: {analysis.get("tenant_name")}
Unit/Property: {analysis.get("unit_or_property")}

Issue Summary:
{analysis.get("issue_summary")}

Missing Information:
{analysis.get("missing_information")}

Recommended Contractor Type:
{analysis.get("recommended_contractor_type")}

Recommended Action:
{analysis.get("recommended_action")}

Draft Tenant Response:
{analysis.get("draft_tenant_response")}

Draft Contractor Message:
{analysis.get("draft_contractor_message")}

Status:
{analysis.get("status")}
"""

    output_path = output_folder / f"{email_name}_draft.txt"
    output_path.write_text(output, encoding="utf-8")
    return output_path

def main():
    input_folder = Path("sample_emails")
    input_folder.mkdir(exist_ok=True)

    email_files = list(input_folder.glob("*.txt"))

    if not email_files:
        print("No sample emails found. Add .txt files to the sample_emails folder.")
        return

    for email_file in email_files:
        print(f"Analyzing {email_file.name}...")
        email_text = email_file.read_text(encoding="utf-8")

        try:
            analysis = analyze_email(email_text)
            output_path = create_output_file(email_file.stem, analysis)
            print(f"Created: {output_path}")
        except Exception as e:
            print(f"Error processing {email_file.name}: {e}")

if __name__ == "__main__":
    main()