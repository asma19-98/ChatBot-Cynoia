import streamlit as st
import urllib.request
import json
import ssl
import os
from datetime import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
system_prompt="""
[conversation history]
Guidelines:
-Always prioritize the current query, but refer to chat history when it adds value or clarity.
-Stay strictly within the predefined context. Do not deviate or bring in unrelated topics, even if mentioned in the chat history.
-Avoid repetitive information unless explicitly asked for reiteration or clarification.
-If the user asks a question that conflicts with the context, politely clarify and guide the conversation back on track.
-If the user shares any personal information, such as their first and last name, age, or location, save this information securely. Use it to enhance the relevance and personalization of your responses when appropriate. Ensure that your answers are tailored to align them.


Example format for generating responses:

If history is relevant: "Based on our earlier discussion about [topic], here's the answer..."
If history provides additional clarity: "As you mentioned previously, [point], this relates to..."
If history is not relevant: "Let’s focus on your current query: [question]."
Chat history for reference:
{history}
[Background]
1. Cynoia is an end-to-end collaboration system.
2. Cynoia's mission is to provide a cutting-edge, all-in-one SaaS solution that simplifies collaboration and communication for teams worldwide. We are dedicated to amplifying results for our users by fostering seamless and efficient teamwork.
3. Cynoia's vision is to empower teams to thrive in a dynamic world by providing innovative solutions that unlock the full potential of every individual. We strive to revolutionize the way teams collaborate, communicate seamlessly, and unleash their creativity.
[Input Classification Rules]
1. Before responding, determine if the user's input is related to Cynoia platform.
2. For non-Cynoia related queries, classify as "not-related" and respond with the default message.
3. For Cynoia-related queries, classify as "related" and provide appropriate assistance.
[Output Format]
Response must be in JSON format with two fields:
- "class": Either "related" or "not-related"
- "response": The appropriate response text
[Few-shot Examples]
Input: "How do I create a new project in Cynoia?"
Output: {{
   "class": "related",
   "answer": "To create a new project in Cynoia, click on 'Projects' in the sidebar. You will see all existing projects. Then, click on the 'Create Project' button and enter your project details: name, description, visibility settings, and initial team members. Would you like me to guide you through the additional project settings?"
}}
Input: "Puis-je suivre mes délais dans Cynoia ?"
Output: {{
   "class": "related",
   "answer": "Oui, la Calendrier vous permet de programmer des événements et de fixer des rappels. Vous recevrez des notifications à l'approche des échéances, ce qui vous permettra de rester sur la bonne voie et de ne jamais manquer une échéance. "
}}
Input: "Quelle est la meilleure recette de gâteau au chocolat ?"
Output: {{
   "class": "not-related",
   "answer": "Je suis là pour vous aider avec vos questions sur Cynoia. Pourriez-vous me poser une question spécifique à la plateforme ?"
}}
Input: "What's the weather like today?"
Output: {{
   "class": "not-related",
   "answer": "I'm here to assist with questions about Cynoia. Could you ask something specific to the platform?"
}}
[Task]
You are an intelligent and proactive assistant chatbot designed to facilitate seamless collaboration within the Cynoia Platform. Your primary objectives are to enhance productivity, streamline communication, and support users in managing tasks, projects, and interactions efficiently.
[Conditions and Rules]
1. Always maintain a professional and supportive tone.
2. Confirm actions and provide clear, actionable feedback.
3. Be proactive in offering assistance and suggesting improvements.
4. Ensure responses are concise yet comprehensive, avoiding unnecessary jargon and must strictly follow the provided context.
5. When encountering unclear or ambiguous user requests, ask clarifying questions to ensure accurate assistance.
6. Stay updated on Cynoia's new features and updates to provide the most current and relevant guidance.
[Important]
Do not give any information about procedures and service features that are not mentioned in the PROVIDED CONTEXT."""

# Azure configuration
AZURE_ML_ENDPOINT_URL = "https://ai-training-models-pyrtn.germanywestcentral.inference.ml.azure.com/score"  # Replace with your Azure endpoint URL
AZURE_ML_API_KEY = "USTWLOQI4tBegvMRfipYeVg2zdEc96Qv"  # Replace with your Azure API key

# Function to allow self-signed HTTPS
def allow_self_signed_https(allowed):
    if allowed and not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(ssl, "_create_unverified_context", None):
        ssl._create_default_https_context = ssl._create_unverified_context

allow_self_signed_https(True)


# Modify the Google Sheets client function
def get_google_sheets_client():
    try:
        # Try to get credentials from environment variable
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if credentials_path and os.path.exists(credentials_path):
            # Scope for Google Sheets and Google Drive
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            # Load credentials from the specified path
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        else:
            # Fallback to reading from environment variable content
            credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            
            if not credentials_json:
                raise ValueError("No Google Sheets credentials found")
            
            # Parse the JSON credentials
            creds_dict = json.loads(credentials_json)
            
            # Scope for Google Sheets and Google Drive
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            # Create credentials from JSON
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        # Authorize the client
        client = gspread.authorize(creds)
        return client
    
    except Exception as e:
        st.error(f"Error initializing Google Sheets client: {e}")
        return None
# Function to save conversation to Google Sheets
def save_conversation_to_google_sheets(user_question, bot_response, feedback):
    try:
        # Get the Google Sheets client
        client = get_google_sheets_client()
        if client is None:
            st.error("Could not initialize Google Sheets client")
            return False
        # Open the specific spreadsheet (replace with your spreadsheet name)
        # If the spreadsheet doesn't exist, you'll need to create it first
        spreadsheet = client.open('Cynoia Conversations')

        # Select the first worksheet (or create one if it doesn't exist)
        try:
            worksheet = spreadsheet.worksheet('Conversations')
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title='Conversations', rows=1000, cols=10)
            # Add headers if it's a new worksheet
            worksheet.append_row(['Timestamp', 'User Question', 'Bot Response', 'Feedback'])

        # Prepare the row to be added
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            user_question,
            bot_response,
            'Positive' if feedback else 'Negative'
        ]

        # Append the row to the worksheet
        worksheet.append_row(row)

        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
        return False



# Function to save conversation data
#def save_conversation_to_excel(user_question, bot_response, feedback):
#    try:
#        # Check if file exists, if not create a new DataFrame
#        try:
#            df = pd.read_excel('cynoia_conversations.xlsx')
#        except FileNotFoundError:
#            df = pd.DataFrame(columns=['Timestamp', 'User Question', 'Bot Response', 'Feedback'])
#
#        # Create a new row with conversation data
#        new_row = pd.DataFrame({
#            'Timestamp': [datetime.now()],
#            'User Question': [user_question],
#            'Bot Response': [bot_response],
#            'Feedback': [feedback]
#        })

#        # Append the new row to the existing DataFrame
#        df = pd.concat([df, new_row], ignore_index=True)

#        # Save to Excel file
#        df.to_excel('cynoia_conversations.xlsx', index=False)

#        return True
#   except Exception as e:
#        st.error(f"Error saving conversation: {e}")
#        return False


# Function to send request to Azure ML
def send_request_to_azure(system_prompt: str, user_prompt: str, temperature: float = 0.8, max_new_tokens: int = 200):
    sysprompt = system_prompt.format(history=user_prompt)
    data = {
        "input_data": {
            "input_string": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "parameters": {
                "temperature": temperature,
                "top_p": 0.8,
                "do_sample": True,
                "max_new_tokens": max_new_tokens
            }
        }
    }
    body = str.encode(json.dumps(data))
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + AZURE_ML_API_KEY
    }
    try:
        req = urllib.request.Request(AZURE_ML_ENDPOINT_URL, body, headers)
        response = urllib.request.urlopen(req)
        result = response.read().decode("utf-8")

        parsed_result = json.loads(result)
        response_text = parsed_result.get("output", '')
        generated_text = json.loads(response_text)
        return generated_text.get("answer", "")

    except urllib.error.HTTPError as e:
        return f"HTTPError: {e.code} - {e.read().decode('utf8', 'ignore')}"
    except Exception as e:
        return f"Error: {str(e)}"

# Streamlit UI
def main():
    st.title("ChatBot Cynoia")

    # Initialize session state for messages and feedback
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "message_feedbacks" not in st.session_state:
        st.session_state.message_feedbacks = {}

    # Display chat history
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Add feedback buttons for assistant messages
            if message["role"] == "assistant":
                col1, col2 = st.columns(2)
                with col1:
                    like = st.button("👍", key=f"like_{i}")
                with col2:
                    dislike = st.button("👎", key=f"dislike_{i}")

                # Handle feedback
                if like:
                    st.session_state.message_feedbacks[i] = True
                    # Ensure there's a previous user message to reference
                    if i > 0 and st.session_state.messages[i-1]["role"] == "user":
                        save_conversation_to_google_sheets(
                            st.session_state.messages[i-1]["content"],  # User question
                            message["content"],  # Bot response
                            True  # Positive feedback
                        )
                    st.success("Thank you for your positive feedback!")

                if dislike:
                    st.session_state.message_feedbacks[i] = False
                    # Ensure there's a previous user message to reference
                    if i > 0 and st.session_state.messages[i-1]["role"] == "user":
                        save_conversation_to_google_sheets(
                            st.session_state.messages[i-1]["content"],  # User question
                            message["content"],  # Bot response
                            False  # Negative feedback
                        )
                    st.warning("Thank you for your feedback. We'll work on improving!")

    # User input
    user_input = st.chat_input("Type your message here:")
    if user_input:
        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Send user input to Azure model
        with st.chat_message("assistant"):
            response = send_request_to_azure(system_prompt, user_input)
            st.markdown(response)

        # Add bot response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})

# Run the Streamlit app
if __name__ == "__main__":
    main()


