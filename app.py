import streamlit as st
import openai
from dotenv import load_dotenv
import os
from db import (
    init_db, add_patient, get_patients, get_patient_by_id,
    add_encounter, get_encounters, add_document, get_documents,
    add_ai_log, get_ai_logs, add_ai_conversation_entry, get_ai_conversation_history,
    get_encounter_counts_by_type, get_patient_age_distribution, get_recent_patient_activity
)
from datetime import datetime
import shutil # For file operations
from PIL import Image # For image processing
import pytesseract # For OCR (if Tesseract is installed and path configured)
import PyPDF2 # For PDF text extraction
import glob # For listing files
import pandas as pd # Import pandas for DataFrame operations
import base64 # For image encoding
import mimetypes # For guessing MIME type

# --- Configuration and Initialization ---
# Load API key from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
if openai_api_key:
    client = openai.OpenAI(api_key=openai_api_key)
else:
    st.error("OPENAI_API_KEY not found in environment variables. Please set it up.")
    client = None # Set client to None if API key is missing

# Initialize the DuckDB database (creates tables if they don't exist)
init_db()

# --- Streamlit App Title and Navigation ---
st.set_page_config(layout="wide", page_title="EHR System Demo")
st.title("EHR System Demo (OpenAI Powered)")

st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Go to",
    [
        "Patient Management",
        "Patient Timeline",
        "AI Tools (Document Analysis & Chat)", # Renamed this section
        "Reports & Analytics"
    ]
)

# --- Helper Function for Patient Selection (to avoid repetition) ---
def get_selected_patient(key_prefix):
    """Helper to get selected patient and their ID for various sections."""
    patients = get_patients()
    patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients.iterrows()}

    if not patient_options:
        st.info("No patients registered yet. Please register a patient in 'Patient Management' first.")
        return None, None, None

    selected_display = st.selectbox(
        "Select Patient",
        list(patient_options.keys()),
        key=f"{key_prefix}_patient_select"
    )
    patient_id = patient_options[selected_display]
    patient_info = get_patient_by_id(patient_id) # This returns a Series or None
    return patient_id, patient_info, patients # Return patients df too for consistency

# --- Section: Patient Management ---
if section == "Patient Management":
    st.header("Patient Record Management")

    with st.expander("Register New Patient"):
        with st.form("register_patient_form", clear_on_submit=True):
            name = st.text_input("Full Name", key="reg_name")
            dob = st.date_input("Date of Birth", key="reg_dob", min_value=datetime(1950, 1, 1).date())
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="reg_gender")
            contact = st.text_input("Contact Info", key="reg_contact")
            address = st.text_area("Address", key="reg_address")
            submit_patient = st.form_submit_button("Register Patient")

            if submit_patient and name:
                add_patient(name, dob, gender, contact, address)
                st.success(f"Patient '{name}' registered successfully.")
                st.rerun() # Rerun to update the patient list immediately

    st.subheader("All Patients")
    patients_df = get_patients()
    if not patients_df.empty:
        st.dataframe(patients_df, use_container_width=True)
    else:
        st.info("No patients registered yet.")

# --- Section: Patient Timeline ---
elif section == "Patient Timeline":
    st.header("Patient Timeline & Encounters")

    patient_id, patient, _ = get_selected_patient("timeline")

    # Fix: Check if patient is not None
    if patient is not None:
        st.markdown(f"### Patient Details: {patient['name']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**DOB:** {patient['dob']}")
            st.markdown(f"**Gender:** {patient['gender']}")
        with col2:
            st.markdown(f"**Contact:** {patient['contact']}")
        with col3:
            st.markdown(f"**Address:** {patient['address']}")

        st.subheader("Add New Encounter or Follow-up")
        with st.form("add_encounter_form", clear_on_submit=True):
            date = st.date_input("Encounter Date", value=datetime.now().date(), key="enc_date")
            encounter_mode = st.radio("Encounter Type", ["New Consultation", "Follow-up"], key="enc_mode")

            # Get previous consultations for follow-up selection
            prev_encounters = get_encounters(patient_id)
            consults = prev_encounters[prev_encounters['type'] == "Consultation"]

            selected_consult_id = None
            if encounter_mode == "Follow-up":
                if not consults.empty:
                    # Create display options for selectbox, including a snippet of notes
                    consult_options = {
                        f"{row['date'].strftime('%Y-%m-%d')} - {row['notes'][:70]}...": row['id']
                        for _, row in consults.iterrows()
                    }
                    selected_consult_display = st.selectbox(
                        "Select Previous Consultation to Follow Up",
                        list(consult_options.keys()),
                        key=f"enc_followup_select_{patient_id}" # Unique key for this widget
                    )
                    selected_consult_id = consult_options.get(selected_consult_display)
                else:
                    st.info("No previous consultations to follow up for this patient.")
                    # If no consults, default back to New Consultation to avoid confusion
                    encounter_mode = "New Consultation"
                    st.radio("Encounter Type", ["New Consultation", "Follow-up"], index=0, key="enc_mode_fallback") # Re-render radio with default

            notes = st.text_area(
                "Consultation/Follow-up Details / Case Notes",
                key=f"enc_notes_{encounter_mode}_{patient_id}" # Unique key based on mode and patient
            )
            doctor = st.text_input(
                "Doctor/Provider",
                key=f"enc_doctor_{encounter_mode}_{patient_id}" # Unique key based on mode and patient
            )
            submit_encounter = st.form_submit_button("Add Encounter")

            if submit_encounter:
                if encounter_mode == "New Consultation":
                    add_encounter(patient_id, date, "Consultation", notes, doctor)
                    st.success("New Consultation added.")
                elif encounter_mode == "Follow-up" and selected_consult_id:
                    add_encounter(patient_id, date, "Follow-up", notes, doctor, follow_up_of_encounter_id=selected_consult_id)
                    st.success("Follow-up added.")
                else:
                    st.warning("Please select a consultation to follow up, or switch to 'New Consultation'.")
                st.rerun() # Rerun to update the encounter list

        st.subheader("Patient Encounters")
        encounters_df = get_encounters(patient_id)
        if not encounters_df.empty:
            # Display follow-up details clearly
            display_df = encounters_df.copy()
            display_df['Follows Up'] = display_df.apply(
                lambda row: f"ID: {int(row['follow_up_of_encounter_id'])} ({row['followed_up_type']} on {row['followed_up_date'].strftime('%Y-%m-%d')})"
                if pd.notna(row['follow_up_of_encounter_id']) else "N/A", axis=1
            )
            st.dataframe(display_df[['date', 'type', 'doctor', 'notes', 'Follows Up']], use_container_width=True)
        else:
            st.info("No encounters recorded for this patient yet.")

# --- Section: AI Tools (Document Analysis & Chat) ---
elif section == "AI Tools (Document Analysis & Chat)":
    st.header("AI-Powered Document Analysis & Consultation Chat")
    st.write("Upload a scan/report (PDF, TXT, or JPEG image) and get AI suggestions based on the document and patient features. You can then chat with the AI for further insights.")

    patient_id, patient, _ = get_selected_patient("ai_doc_analysis_chat")

    if patient is not None:
        upload_dir = f"patient_uploads/patient_{patient_id}"
        os.makedirs(upload_dir, exist_ok=True) # Ensure patient-specific upload directory exists

        # Select relevant consultation/encounter for this upload
        encounters = get_encounters(patient_id)
        consults = encounters[encounters['type'] == "Consultation"]
        selected_consult_id = None
        if not consults.empty:
            consult_options = {
                f"{row['date'].strftime('%Y-%m-%d')} - {row['notes'][:50]}...": row['id']
                for _, row in consults.iterrows()
            }
            selected_consult_display = st.selectbox(
                "Select Consultation this upload/scan pertains to",
                list(consult_options.keys()),
                key=f"ai_consult_doc_{patient_id}"
            )
            selected_consult_id = consult_options.get(selected_consult_display)
        else:
            st.warning("No consultations available for this patient. Please add a consultation first in 'Patient Timeline'.")

        st.markdown("---")
        uploaded_file = st.file_uploader("Upload Scan/Report (PDF, TXT, JPEG, PNG)", type=["pdf", "txt", "jpeg", "jpg", "png"], key="ai_file_uploader")
        report_text_input = st.text_area("Or paste the text of the report here", key="ai_report_text_input")

        file_text_extracted = ""
        file_path_saved = None
        image_for_ai = None

        if uploaded_file is not None:
            file_path_saved = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path_saved, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Process uploaded file based on type
            if uploaded_file.type == "text/plain":
                file_text_extracted = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/pdf":
                try:
                    reader = PyPDF2.PdfReader(file_path_saved)
                    file_text_extracted = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                except Exception as e:
                    st.error(f"PDF extraction error: {e}. Ensure the PDF is not password protected or corrupted.")
            elif uploaded_file.type in ["image/jpeg", "image/jpg", "image/png"]:
                image_for_ai = file_path_saved # Path to image for AI vision model
                st.info(f"Image '{uploaded_file.name}' uploaded. It will be sent to the AI for visual analysis.")
                # No OCR needed here, relying on AI vision
            
            # Save document metadata to DB
            if selected_consult_id:
                add_document(patient_id, selected_consult_id, uploaded_file.type, file_path_saved, file_text_extracted)
                st.success(f"File '{uploaded_file.name}' uploaded and processed.")
            else:
                st.warning("File uploaded, but no consultation selected. Document not linked in database.")

        # --- AI Suggestion Button ---
        if st.button("Get AI Suggestion", key="ai_suggest_btn") and client and selected_consult_id:
            # Combine all available context for the AI
            patient_info_str = f"Name: {patient['name']}\nAge: {datetime.now().year - patient['dob'].year if patient['dob'] else 'N/A'}\nGender: {patient['gender']}\nContact: {patient['contact']}\nAddress: {patient['address']}"

            consult_row = consults[consults['id'] == selected_consult_id].iloc[0]
            consult_details_str = f"Consultation Date: {consult_row['date'].strftime('%Y-%m-%d')}\nNotes: {consult_row['notes']}\nDoctor: {consult_row['doctor']}"

            # Get all previous uploads and their extracted text for RAG
            previous_uploads_text = []
            docs_df = get_documents(patient_id)
            for _, doc_row in docs_df.iterrows():
                # Exclude the current upload if it's already processed
                if file_path_saved and os.path.abspath(doc_row['file_path']) == os.path.abspath(file_path_saved):
                    continue
                previous_uploads_text.append(f"Previous Document (Type: {doc_row['type']}, Upload Time: {doc_row['upload_time'].strftime('%Y-%m-%d %H:%M')}, File: {os.path.basename(doc_row['file_path'])}):\n{doc_row['text_content']}")
            uploads_context = "\n\n".join(previous_uploads_text) if previous_uploads_text else "No previous documents."

            current_report_content = file_text_extracted or report_text_input
            if not current_report_content and not image_for_ai:
                st.warning("Please upload a file or paste text to get an AI suggestion.")
                st.stop()

            context = f"""
            --- Patient Information ---
            {patient_info_str}

            --- Selected Consultation Details ---
            {consult_details_str}

            --- Previous Medical Documents ---
            {uploads_context}

            --- Current Report/Scan Content ---
            {current_report_content if current_report_content else 'No text content provided. Analyzing image if available.'}
            """

            # Enhanced System Prompt for detailed clinical suggestions
            system_prompt = """
            You are a highly experienced clinical decision support AI. Your task is to analyze the provided patient information, relevant consultation details, previous medical documents, and the current report/scan (text or image). Based on this comprehensive context, you should provide:

            1.  **Suggested Diagnoses:** List potential diagnoses with brief justifications, considering all provided information.
            2.  **Recommended Treatment Plan:** Propose a treatment plan, including medications, therapies, or interventions. Be specific where possible.
            3.  **Course of Action/Next Steps:** Outline immediate and future steps (e.g., further investigations, referrals, follow-up schedule, patient education).
            4.  **Important Considerations:** Any caveats, risk factors, or patient-specific considerations (e.g., allergies, comorbidities).

            Present your response clearly and concisely, using bullet points or numbered lists where appropriate.
            If an image is provided, **it is a medical scan or x-ray**. You MUST analyze the image and integrate its findings into your suggestions, explicitly mentioning what you observe in the image.
            """
            with st.spinner("Getting AI suggestion..."):
                try:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": context}
                        ]}
                    ]
                    if image_for_ai:
                        # base64 and mimetypes are imported at the top
                        with open(image_for_ai, "rb") as img_f:
                            img_bytes = img_f.read()
                        mime_type, _ = mimetypes.guess_type(image_for_ai)
                        if mime_type is None:
                            mime_type = "application/octet-stream" # Fallback if mimetype can't be guessed
                        b64_img = base64.b64encode(img_bytes).decode("utf-8")
                        image_url = f"data:{mime_type};base64,{b64_img}"
                        messages[1]["content"].append({"type": "image_url", "image_url": {"url": image_url}})
                        st.info("Image data successfully encoded and added to AI request.")
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini", # Confirm this is the model you intend to use for vision
                        messages=messages,
                        max_tokens=700, # Increased max_tokens for more comprehensive output
                        temperature=0.2 # Lower temperature for factual, less creative responses
                    )
                    ai_response = response.choices[0].message.content.strip()
                    st.success("AI Suggestion:")
                    st.markdown(ai_response) # Use markdown to render AI's formatted output

                    # Store the initial AI suggestion in session state for chat context
                    st.session_state[f"initial_ai_suggestion_{patient_id}"] = ai_response
                    
                    # Refinement 1: Save the initial AI suggestion to the chat history database
                    add_ai_conversation_entry(patient_id, "assistant", ai_response)

                    # Log the AI interaction
                    add_ai_log(patient_id, selected_consult_id, context, ai_response, "document_analysis")

                except Exception as e:
                    st.error(f"AI request failed: {e}. Please check your API key, network connection, and ensure the image file is valid.")
                    st.exception(e) # Display full exception for debugging
        
        # --- AI Chat Section (integrated here) ---
        st.subheader("Chat with AI for Further Consultation")
        st.write("Continue the conversation with the AI based on the document analysis and patient context.")

        if client:
            # Initialize chat history in session state for the current patient
            chat_key = f"chat_history_{patient_id}"
            # Always reload from DB to ensure persistence and include initial suggestion
            st.session_state[chat_key] = get_ai_conversation_history(patient_id)
            
            # If no history was loaded (e.g., first time for this patient),
            # and an initial AI suggestion was just made, add a specific greeting
            if not st.session_state[chat_key] and f"initial_ai_suggestion_{patient_id}" in st.session_state:
                # The initial suggestion is already added to DB and will be loaded above.
                # Just add a follow-up greeting if the chat is truly empty.
                st.session_state[chat_key].append({"role": "assistant", "content": f"How else can I assist you regarding {patient['name']} based on the analysis?"})
            elif not st.session_state[chat_key]: # If no history and no initial suggestion
                st.session_state[chat_key] = [{"role": "assistant", "content": f"Hello! How can I assist you regarding patient {patient['name']}'s health concerns today?"}]

            # Display chat messages from history
            for message in st.session_state[chat_key]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input for user
            if prompt := st.chat_input("Ask a follow-up question or provide more details..."):
                st.session_state[chat_key].append({"role": "user", "content": prompt})
                add_ai_conversation_entry(patient_id, "user", prompt) # Save user message to DB

                with st.chat_message("user"):
                    st.markdown(prompt)

                # Generate AI response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking...\n(If the AI responds with an error, it will NOT be saved to history.)"):
                        # Build context for AI, including patient info and conversation history
                        patient_context = f"Patient Name: {patient['name']}, Age: {datetime.now().year - patient['dob'].year if patient['dob'] else 'N/A'}, Gender: {patient['gender']}. Contact: {patient['contact']}. Address: {patient['address']}. "
                        
                        # The initial suggestion is now part of the loaded chat history, so no need to explicitly add it here
                        # initial_suggestion_context = "" 
                        # if f"initial_ai_suggestion_{patient_id}" in st.session_state and \
                        #    not any(msg.get("content") == st.session_state[f"initial_ai_suggestion_{patient_id}"] for msg in st.session_state[chat_key]):
                        #     initial_suggestion_context = f"\n\nInitial document analysis suggestion: {st.session_state[f'initial_ai_suggestion_{patient_id}']}"

                        system_prompt_chat = f"""
                        You are a helpful and empathetic medical assistant for a medic. You are discussing patient {patient['name']}.
                        Your current conversation is a follow-up to a document analysis you just performed.
                        Answer medical questions, suggest potential issues, and guide towards next steps based on patient's context and previous discussion.
                        Always prioritize safety and recommend consulting a qualified medical professional for definitive diagnosis/treatment.
                        Patient background: {patient_context}
                        """ # Removed initial_suggestion_context as it's now in chat history

                        messages_for_api = [{"role": "system", "content": system_prompt_chat}]

                        # Append previous chat turns to maintain conversation context for the AI
                        for msg in st.session_state[chat_key]:
                            if msg["role"] in ["user", "assistant"]:
                                messages_for_api.append({"role": msg["role"], "content": msg["content"]})

                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=messages_for_api,
                                max_tokens=300, # Adjust as needed for chat length
                                temperature=0.7 # Higher temperature for more conversational and less rigid responses
                            )
                            ai_response_content = response.choices[0].message.content
                            st.markdown(ai_response_content)
                            st.session_state[chat_key].append({"role": "assistant", "content": ai_response_content})
                            add_ai_conversation_entry(patient_id, "assistant", ai_response_content) # Save AI message to DB

                        except Exception as e:
                            st.error(f"AI chat failed: {e}. Please check your API key and try again.")
                            # Refinement 2: Do NOT append error message to chat history
                            # st.session_state[chat_key].append({"role": "assistant", "content": "I apologize, but I encountered an error. Please try again."})
                            st.exception(e)
        else:
            st.warning("OpenAI API client is not initialized. Please ensure OPENAI_API_KEY is set to enable chat.")
    else:
        st.info("Please select a patient to use AI Tools.")

# --- Section: Reports & Analytics ---
elif section == "Reports & Analytics":
    st.header("Clinical Reports & Analytics")
    st.write("Gain insights into patient data and encounter trends.")

    st.subheader("Encounter Type Distribution")
    encounter_counts_df = get_encounter_counts_by_type()
    if not encounter_counts_df.empty:
        st.bar_chart(encounter_counts_df.set_index('type'), use_container_width=True)
    else:
        st.info("No encounter data to display charts.")

    st.subheader("Patient Age Distribution")
    age_distribution_df = get_patient_age_distribution()
    if not age_distribution_df.empty:
        st.bar_chart(age_distribution_df.set_index('age_group'), use_container_width=True)
    else:
        st.info("No patient age data to display charts.")

    st.subheader("Recent Patient Activity (Last 10 Encounters)")
    recent_activity_df = get_recent_patient_activity(limit=10)
    if not recent_activity_df.empty:
        # Format date for better display
        recent_activity_df['encounter_date'] = recent_activity_df['encounter_date'].dt.strftime('%Y-%m-%d')
        st.dataframe(recent_activity_df, use_container_width=True)
    else:
        st.info("No recent patient activity recorded.")

    # You can add more complex reports here, e.g., vitals trends, common diagnoses (if you add a diagnosis field)
    # st.subheader("Vitals Trends (Example)")
    # patient_id_for_vitals, patient_for_vitals, _ = get_selected_patient("vitals_report")
    # if patient_id_for_vitals:
    #     vitals_df = get_vitals(patient_id_for_vitals)
    #     if not vitals_df.empty:
    #         st.line_chart(vitals_df.set_index('timestamp')[['heart_rate', 'temp']], use_container_width=True)
    #     else:
    #         st.info(f"No vitals data for {patient_for_vitals['name']}.")








# import streamlit as st
# import openai
# from dotenv import load_dotenv
# import os
# from db import (
#     init_db, add_patient, get_patients, get_patient_by_id,
#     add_encounter, get_encounters, add_document, get_documents,
#     add_ai_log, get_ai_logs, add_ai_conversation_entry, get_ai_conversation_history,
#     get_encounter_counts_by_type, get_patient_age_distribution, get_recent_patient_activity
# )
# from datetime import datetime
# import shutil # For file operations
# from PIL import Image # For image processing
# import pytesseract # For OCR (if Tesseract is installed and path configured)
# import PyPDF2 # For PDF text extraction
# import glob # For listing files
# import pandas as pd # Import pandas for DataFrame operations
# import base64 # For image encoding

# # --- Configuration and Initialization ---
# # Load API key from .env file
# load_dotenv()
# openai_api_key = os.getenv("OPENAI_API_KEY")

# # Initialize OpenAI client
# if openai_api_key:
#     client = openai.OpenAI(api_key=openai_api_key)
# else:
#     st.error("OPENAI_API_KEY not found in environment variables. Please set it up.")
#     client = None # Set client to None if API key is missing

# # Initialize the DuckDB database (creates tables if they don't exist)
# init_db()

# # --- Streamlit App Title and Navigation ---
# st.set_page_config(layout="wide", page_title="EHR System Demo")
# st.title("EHR System Demo (OpenAI Powered)")

# st.sidebar.title("Navigation")
# section = st.sidebar.radio(
#     "Go to",
#     [
#         "Patient Management",
#         "Patient Timeline",
#         "AI Tools (Document Analysis & Chat)", # Renamed this section
#         "Reports & Analytics"
#     ]
# )

# # --- Helper Function for Patient Selection (to avoid repetition) ---
# def get_selected_patient(key_prefix):
#     """Helper to get selected patient and their ID for various sections."""
#     patients = get_patients()
#     patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients.iterrows()}

#     if not patient_options:
#         st.info("No patients registered yet. Please register a patient in 'Patient Management' first.")
#         return None, None, None

#     selected_display = st.selectbox(
#         "Select Patient",
#         list(patient_options.keys()),
#         key=f"{key_prefix}_patient_select"
#     )
#     patient_id = patient_options[selected_display]
#     patient_info = get_patient_by_id(patient_id) # This returns a Series or None
#     return patient_id, patient_info, patients # Return patients df too for consistency

# # --- Section: Patient Management ---
# if section == "Patient Management":
#     st.header("Patient Record Management")

#     with st.expander("Register New Patient"):
#         with st.form("register_patient_form", clear_on_submit=True):
#             name = st.text_input("Full Name", key="reg_name")
#             dob = st.date_input("Date of Birth", key="reg_dob")
#             gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="reg_gender")
#             contact = st.text_input("Contact Info", key="reg_contact")
#             address = st.text_area("Address", key="reg_address")
#             submit_patient = st.form_submit_button("Register Patient")

#             if submit_patient and name:
#                 add_patient(name, dob, gender, contact, address)
#                 st.success(f"Patient '{name}' registered successfully.")
#                 st.rerun() # Rerun to update the patient list immediately

#     st.subheader("All Patients")
#     patients_df = get_patients()
#     if not patients_df.empty:
#         st.dataframe(patients_df, use_container_width=True)
#     else:
#         st.info("No patients registered yet.")

# # --- Section: Patient Timeline ---
# elif section == "Patient Timeline":
#     st.header("Patient Timeline & Encounters")

#     patient_id, patient, _ = get_selected_patient("timeline")

#     # Fix: Check if patient is not None
#     if patient is not None:
#         st.markdown(f"### Patient Details: {patient['name']}")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.markdown(f"**DOB:** {patient['dob']}")
#             st.markdown(f"**Gender:** {patient['gender']}")
#         with col2:
#             st.markdown(f"**Contact:** {patient['contact']}")
#         with col3:
#             st.markdown(f"**Address:** {patient['address']}")

#         st.subheader("Add New Encounter or Follow-up")
#         with st.form("add_encounter_form", clear_on_submit=True):
#             date = st.date_input("Encounter Date", value=datetime.now().date(), key="enc_date")
#             encounter_mode = st.radio("Encounter Type", ["New Consultation", "Follow-up"], key="enc_mode")

#             # Get previous consultations for follow-up selection
#             prev_encounters = get_encounters(patient_id)
#             consults = prev_encounters[prev_encounters['type'] == "Consultation"]

#             selected_consult_id = None
#             if encounter_mode == "Follow-up":
#                 if not consults.empty:
#                     # Create display options for selectbox, including a snippet of notes
#                     consult_options = {
#                         f"{row['date'].strftime('%Y-%m-%d')} - {row['notes'][:70]}...": row['id']
#                         for _, row in consults.iterrows()
#                     }
#                     selected_consult_display = st.selectbox(
#                         "Select Previous Consultation to Follow Up",
#                         list(consult_options.keys()),
#                         key=f"enc_followup_select_{patient_id}" # Unique key for this widget
#                     )
#                     selected_consult_id = consult_options.get(selected_consult_display)
#                 else:
#                     st.info("No previous consultations to follow up for this patient.")
#                     # If no consults, default back to New Consultation to avoid confusion
#                     encounter_mode = "New Consultation"
#                     st.radio("Encounter Type", ["New Consultation", "Follow-up"], index=0, key="enc_mode_fallback") # Re-render radio with default

#             notes = st.text_area(
#                 "Consultation/Follow-up Details / Case Notes",
#                 key=f"enc_notes_{encounter_mode}_{patient_id}" # Unique key based on mode and patient
#             )
#             doctor = st.text_input(
#                 "Doctor/Provider",
#                 key=f"enc_doctor_{encounter_mode}_{patient_id}" # Unique key based on mode and patient
#             )
#             submit_encounter = st.form_submit_button("Add Encounter")

#             if submit_encounter:
#                 if encounter_mode == "New Consultation":
#                     add_encounter(patient_id, date, "Consultation", notes, doctor)
#                     st.success("New Consultation added.")
#                 elif encounter_mode == "Follow-up" and selected_consult_id:
#                     add_encounter(patient_id, date, "Follow-up", notes, doctor, follow_up_of_encounter_id=selected_consult_id)
#                     st.success("Follow-up added.")
#                 else:
#                     st.warning("Please select a consultation to follow up, or switch to 'New Consultation'.")
#                 st.rerun() # Rerun to update the encounter list

#         st.subheader("Patient Encounters")
#         encounters_df = get_encounters(patient_id)
#         if not encounters_df.empty:
#             # Display follow-up details clearly
#             display_df = encounters_df.copy()
#             display_df['Follows Up'] = display_df.apply(
#                 lambda row: f"ID: {int(row['follow_up_of_encounter_id'])} ({row['followed_up_type']} on {row['followed_up_date'].strftime('%Y-%m-%d')})"
#                 if pd.notna(row['follow_up_of_encounter_id']) else "N/A", axis=1
#             )
#             st.dataframe(display_df[['date', 'type', 'doctor', 'notes', 'Follows Up']], use_container_width=True)
#         else:
#             st.info("No encounters recorded for this patient yet.")

# # --- Section: AI Tools (Document Analysis & Chat) ---
# elif section == "AI Tools (Document Analysis & Chat)":
#     st.header("AI-Powered Document Analysis & Consultation Chat")
#     st.write("Upload a scan/report (PDF, TXT, or JPEG image) and get AI suggestions based on the document and patient features. You can then chat with the AI for further insights.")

#     patient_id, patient, _ = get_selected_patient("ai_doc_analysis_chat")

#     if patient is not None:
#         upload_dir = f"patient_uploads/patient_{patient_id}"
#         os.makedirs(upload_dir, exist_ok=True) # Ensure patient-specific upload directory exists

#         # Select relevant consultation/encounter for this upload
#         encounters = get_encounters(patient_id)
#         consults = encounters[encounters['type'] == "Consultation"]
#         selected_consult_id = None
#         if not consults.empty:
#             consult_options = {
#                 f"{row['date'].strftime('%Y-%m-%d')} - {row['notes'][:50]}...": row['id']
#                 for _, row in consults.iterrows()
#             }
#             selected_consult_display = st.selectbox(
#                 "Select Consultation this upload/scan pertains to",
#                 list(consult_options.keys()),
#                 key=f"ai_consult_doc_{patient_id}"
#             )
#             selected_consult_id = consult_options.get(selected_consult_display)
#         else:
#             st.warning("No consultations available for this patient. Please add a consultation first in 'Patient Timeline'.")

#         st.markdown("---")
#         uploaded_file = st.file_uploader("Upload Scan/Report (PDF, TXT, JPEG, PNG)", type=["pdf", "txt", "jpeg", "jpg", "png"], key="ai_file_uploader")
#         report_text_input = st.text_area("Or paste the text of the report here", key="ai_report_text_input")

#         file_text_extracted = ""
#         file_path_saved = None
#         image_for_ai = None

#         if uploaded_file is not None:
#             file_path_saved = os.path.join(upload_dir, uploaded_file.name)
#             with open(file_path_saved, "wb") as f:
#                 f.write(uploaded_file.getbuffer())

#             # Process uploaded file based on type
#             if uploaded_file.type == "text/plain":
#                 file_text_extracted = uploaded_file.read().decode("utf-8")
#             elif uploaded_file.type == "application/pdf":
#                 try:
#                     reader = PyPDF2.PdfReader(file_path_saved)
#                     file_text_extracted = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
#                 except Exception as e:
#                     st.error(f"PDF extraction error: {e}. Ensure the PDF is not password protected or corrupted.")
#             elif uploaded_file.type in ["image/jpeg", "image/jpg", "image/png"]:
#                 image_for_ai = file_path_saved # Path to image for AI vision model
#                 st.info(f"Image '{uploaded_file.name}' uploaded. It will be sent to the AI for visual analysis.")
#                 try:
#                     # Optional: OCR for image text, requires Tesseract installed and configured
#                     # pytesseract.pytesseract.tesseract_cmd = r'/path/to/tesseract' # Uncomment and set if Tesseract not in PATH
#                     # img = Image.open(file_path_saved)
#                     # file_text_extracted = pytesseract.image_to_string(img)
#                     pass # We'll rely on AI vision for image content
#                 except Exception as e:
#                     st.warning(f"OCR (text extraction from image) failed: {e}. AI will still analyze the image visually.")

#             # Save document metadata to DB
#             if selected_consult_id:
#                 add_document(patient_id, selected_consult_id, uploaded_file.type, file_path_saved, file_text_extracted)
#                 st.success(f"File '{uploaded_file.name}' uploaded and processed.")
#             else:
#                 st.warning("File uploaded, but no consultation selected. Document not linked in database.")

#         # --- AI Suggestion Button ---
#         if st.button("Get AI Suggestion", key="ai_suggest_btn") and client and selected_consult_id:
#             # Combine all available context for the AI
#             patient_info_str = f"Name: {patient['name']}\nAge: {datetime.now().year - patient['dob'].year if patient['dob'] else 'N/A'}\nGender: {patient['gender']}\nContact: {patient['contact']}\nAddress: {patient['address']}"

#             consult_row = consults[consults['id'] == selected_consult_id].iloc[0]
#             consult_details_str = f"Consultation Date: {consult_row['date'].strftime('%Y-%m-%d')}\nNotes: {consult_row['notes']}\nDoctor: {consult_row['doctor']}"

#             # Get all previous uploads and their extracted text for RAG
#             previous_uploads_text = []
#             docs_df = get_documents(patient_id)
#             for _, doc_row in docs_df.iterrows():
#                 # Exclude the current upload if it's already processed
#                 if file_path_saved and os.path.abspath(doc_row['file_path']) == os.path.abspath(file_path_saved):
#                     continue
#                 previous_uploads_text.append(f"Previous Document (Type: {doc_row['type']}, Upload Time: {doc_row['upload_time'].strftime('%Y-%m-%d %H:%M')}, File: {os.path.basename(doc_row['file_path'])}):\n{doc_row['text_content']}")
#             uploads_context = "\n\n".join(previous_uploads_text) if previous_uploads_text else "No previous documents."

#             current_report_content = file_text_extracted or report_text_input
#             if not current_report_content and not image_for_ai:
#                 st.warning("Please upload a file or paste text to get an AI suggestion.")
#                 st.stop()

#             context = f"""
#             --- Patient Information ---
#             {patient_info_str}

#             --- Selected Consultation Details ---
#             {consult_details_str}

#             --- Previous Medical Documents ---
#             {uploads_context}

#             --- Current Report/Scan Content ---
#             {current_report_content if current_report_content else 'No text content provided. Analyzing image if available.'}
#             """

#             # Enhanced System Prompt for detailed clinical suggestions
#             system_prompt = """
#             You are a highly experienced clinical decision support AI. Your task is to analyze the provided patient information, relevant consultation details, previous medical documents, and the current report/scan (text or image). Based on this comprehensive context, you should provide:

#             1.  **Suggested Diagnoses:** List potential diagnoses with brief justifications, considering all provided information.
#             2.  **Recommended Treatment Plan:** Propose a treatment plan, including medications, therapies, or interventions. Be specific where possible.
#             3.  **Course of Action/Next Steps:** Outline immediate and future steps (e.g., further investigations, referrals, follow-up schedule, patient education).
#             4.  **Important Considerations:** Any caveats, risk factors, or patient-specific considerations (e.g., allergies, comorbidities).

#             Present your response clearly and concisely, using bullet points or numbered lists where appropriate.
#             If an image is provided, **it is a medical scan or x-ray**. You MUST analyze the image and integrate its findings into your suggestions, explicitly mentioning what you observe in the image.
#             """
#             with st.spinner("Getting AI suggestion..."):
#                 try:
#                     messages = [
#                         {"role": "system", "content": system_prompt},
#                         {"role": "user", "content": [
#                             {"type": "text", "text": context}
#                         ]}
#                     ]
#                     if image_for_ai:
#                         # Ensure base64 is imported
#                         # import base64 # Already imported at the top
#                         import mimetypes
#                         with open(image_for_ai, "rb") as img_f:
#                             img_bytes = img_f.read()
#                         mime_type, _ = mimetypes.guess_type(image_for_ai)
#                         if mime_type is None:
#                             mime_type = "application/octet-stream" # Fallback if mimetype can't be guessed
#                         b64_img = base64.b64encode(img_bytes).decode("utf-8")
#                         image_url = f"data:{mime_type};base64,{b64_img}"
#                         messages[1]["content"].append({"type": "image_url", "image_url": {"url": image_url}})
#                         st.info("Image data successfully encoded and added to AI request.")

#                     response = client.chat.completions.create(
#                         model="gpt-4.1", # Using gpt-4.1 for cost-effectiveness; gpt-4.1 could provide more depth
#                         messages=messages,
#                         max_tokens=700, # Increased max_tokens for more comprehensive output
#                         temperature=0.2 # Lower temperature for factual, less creative responses
#                     )
#                     ai_response = response.choices[0].message.content.strip()
#                     st.success("AI Suggestion:")
#                     st.markdown(ai_response) # Use markdown to render AI's formatted output

#                     # Store the initial AI suggestion in session state for chat context
#                     st.session_state[f"initial_ai_suggestion_{patient_id}"] = ai_response

#                     # Log the AI interaction
#                     add_ai_log(patient_id, selected_consult_id, context, ai_response, "document_analysis")

#                 except Exception as e:
#                     st.error(f"AI request failed: {e}. Please check your API key, network connection, and ensure the image file is valid.")
#                     st.exception(e) # Display full exception for debugging
        
#         # --- AI Chat Section (integrated here) ---
#         st.subheader("Chat with AI for Further Consultation")
#         st.write("Continue the conversation with the AI based on the document analysis and patient context.")

#         if client:
#             # Initialize chat history in session state for the current patient
#             chat_key = f"chat_history_{patient_id}"
#             if chat_key not in st.session_state:
#                 st.session_state[chat_key] = get_ai_conversation_history(patient_id)
#                 # If no history, and an initial AI suggestion was just made, add it
#                 if not st.session_state[chat_key] and f"initial_ai_suggestion_{patient_id}" in st.session_state:
#                     st.session_state[chat_key].append({"role": "assistant", "content": st.session_state[f"initial_ai_suggestion_{patient_id}"]})
#                     st.session_state[chat_key].append({"role": "assistant", "content": f"How else can I assist you regarding {patient['name']}?"})
#                 elif not st.session_state[chat_key]: # If no history and no initial suggestion
#                     st.session_state[chat_key] = [{"role": "assistant", "content": f"Hello! How can I assist you regarding patient {patient['name']}'s health concerns today?"}]

#             # Display chat messages from history
#             for message in st.session_state[chat_key]:
#                 with st.chat_message(message["role"]):
#                     st.markdown(message["content"])

#             # Chat input for user
#             if prompt := st.chat_input("Ask a follow-up question or provide more details..."):
#                 st.session_state[chat_key].append({"role": "user", "content": prompt})
#                 add_ai_conversation_entry(patient_id, "user", prompt) # Save user message to DB

#                 with st.chat_message("user"):
#                     st.markdown(prompt)

#                 # Generate AI response
#                 with st.chat_message("assistant"):
#                     with st.spinner("Thinking..."):
#                         # Build context for AI, including patient info and conversation history
#                         patient_context = f"Patient Name: {patient['name']}, Age: {datetime.now().year - patient['dob'].year if patient['dob'] else 'N/A'}, Gender: {patient['gender']}. Contact: {patient['contact']}. Address: {patient['address']}. "
                        
#                         # Add initial AI suggestion to context if available and not already in chat history
#                         initial_suggestion_context = ""
#                         if f"initial_ai_suggestion_{patient_id}" in st.session_state and \
#                            not any(msg.get("content") == st.session_state[f"initial_ai_suggestion_{patient_id}"] for msg in st.session_state[chat_key]):
#                             initial_suggestion_context = f"\n\nInitial document analysis suggestion: {st.session_state[f'initial_ai_suggestion_{patient_id}']}"

#                         system_prompt_chat = f"""
#                         You are a helpful and empathetic medical assistant for a medic. You are discussing patient {patient['name']}.
#                         Your current conversation is a follow-up to a document analysis you just performed.
#                         Answer medical questions, suggest potential issues, and guide towards next steps based on patient's context and previous discussion.
#                         Always prioritize safety and recommend consulting a qualified medical professional for definitive diagnosis/treatment.
#                         Patient background: {patient_context}
#                         {initial_suggestion_context}
#                         """

#                         messages_for_api = [{"role": "system", "content": system_prompt_chat}]

#                         # Append previous chat turns to maintain conversation context for the AI
#                         for msg in st.session_state[chat_key]:
#                             if msg["role"] in ["user", "assistant"]:
#                                 messages_for_api.append({"role": msg["role"], "content": msg["content"]})

#                         try:
#                             response = client.chat.completions.create(
#                                 model="gpt-4o-mini",
#                                 messages=messages_for_api,
#                                 max_tokens=300, # Adjust as needed for chat length
#                                 temperature=0.7 # Higher temperature for more conversational and less rigid responses
#                             )
#                             ai_response_content = response.choices[0].message.content
#                             st.markdown(ai_response_content)
#                             st.session_state[chat_key].append({"role": "assistant", "content": ai_response_content})
#                             add_ai_conversation_entry(patient_id, "assistant", ai_response_content) # Save AI message to DB

#                         except Exception as e:
#                             st.error(f"AI chat failed: {e}. Please check your API key and try again.")
#                             st.session_state[chat_key].append({"role": "assistant", "content": "I apologize, but I encountered an error. Please try again."})
#                             st.exception(e)
#         else:
#             st.warning("OpenAI API client is not initialized. Please ensure OPENAI_API_KEY is set to enable chat.")
#     else:
#         st.info("Please select a patient to use AI Tools.")

# # --- Section: Reports & Analytics ---
# elif section == "Reports & Analytics":
#     st.header("Clinical Reports & Analytics")
#     st.write("Gain insights into patient data and encounter trends.")

#     st.subheader("Encounter Type Distribution")
#     encounter_counts_df = get_encounter_counts_by_type()
#     if not encounter_counts_df.empty:
#         st.bar_chart(encounter_counts_df.set_index('type'), use_container_width=True)
#     else:
#         st.info("No encounter data to display charts.")

#     st.subheader("Patient Age Distribution")
#     age_distribution_df = get_patient_age_distribution()
#     if not age_distribution_df.empty:
#         st.bar_chart(age_distribution_df.set_index('age_group'), use_container_width=True)
#     else:
#         st.info("No patient age data to display charts.")

#     st.subheader("Recent Patient Activity (Last 10 Encounters)")
#     recent_activity_df = get_recent_patient_activity(limit=10)
#     if not recent_activity_df.empty:
#         # Format date for better display
#         recent_activity_df['encounter_date'] = recent_activity_df['encounter_date'].dt.strftime('%Y-%m-%d')
#         st.dataframe(recent_activity_df, use_container_width=True)
#     else:
#         st.info("No recent patient activity recorded.")

   