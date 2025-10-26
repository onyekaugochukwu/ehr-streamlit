import streamlit as st
import openai
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import mimetypes
import PyPDF2
from PIL import Image
import io

# Import custom modules
from auth import (
    login_user, register_user, logout, get_current_user, require_auth,
    require_role, get_user_role, log_audit_event, get_audit_logs
)
from ui_components import (
    set_custom_theme, modern_metric_card, patient_summary_card,
    create_activity_timeline, create_health_dashboard, smart_search_bar,
    notification_system, theme_toggle, loading_animation, progress_bar_with_percentage
)
from db import (
    init_db, add_patient_enhanced, update_patient, get_patients, get_patient_by_id,
    add_encounter, get_encounters, add_document, get_documents,
    add_ai_log, get_ai_logs, add_ai_conversation_entry, get_ai_conversation_history,
    get_encounter_counts_by_type, get_patient_age_distribution, get_recent_patient_activity,
    add_medication, get_medications, add_prescription, get_prescriptions,
    check_medication_interactions, add_appointment, get_appointments, update_appointment_status,
    add_lab_result, get_lab_results, add_allergy, get_allergies, add_immunization,
    get_immunizations, get_prescription_analytics, get_appointment_analytics
)

# Configuration
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
if openai_api_key:
    client = openai.OpenAI(api_key=openai_api_key)
else:
    client = None

# Initialize database
init_db()

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="Next-Gen EHR System",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# Authentication check
def show_login_page():
    """Display login/registration page."""
    st.markdown("""
    <div class="header-gradient">
        <h1>🏥 Next-Gen EHR System</h1>
        <p>Advanced Electronic Health Records with AI-Powered Insights</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                success, message = login_user(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.current_user = {"username": username}
                    log_audit_event(username, "login", "User logged in successfully")
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(message)

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("New Username", placeholder="Choose a username")
            new_password = st.text_input("Password", type="password", placeholder="Choose a strong password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name", placeholder="Your full name")
            email = st.text_input("Email", placeholder="your.email@example.com")
            role = st.selectbox("Role", ["doctor", "nurse", "admin"])

            if st.form_submit_button("Register", use_container_width=True):
                if new_password != confirm_password:
                    st.error("Passwords do not match!")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters!")
                else:
                    success, message = register_user(new_username, new_password, full_name, email, role)
                    if success:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error(message)

# Document Processing Functions
def process_document(uploaded_file):
    """Process different document types and extract content."""
    file_content = ""
    file_metadata = {
        "name": uploaded_file.name,
        "type": uploaded_file.type,
        "size": uploaded_file.size
    }

    try:
        if uploaded_file.type == "text/plain":
            # Process TXT files
            file_content = uploaded_file.read().decode("utf-8")
            return file_content, file_metadata, "text"

        elif uploaded_file.type == "application/pdf":
            # Process PDF files
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            file_content = ""

            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():
                    file_content += f"\n--- Page {page_num} ---\n{page_text}\n"

            # Add PDF metadata
            if pdf_reader.metadata:
                file_metadata.update({
                    "title": pdf_reader.metadata.get('/Title', 'Unknown'),
                    "author": pdf_reader.metadata.get('/Author', 'Unknown'),
                    "creator": pdf_reader.metadata.get('/Creator', 'Unknown'),
                    "pages": len(pdf_reader.pages)
                })

            return file_content, file_metadata, "pdf"

        elif uploaded_file.type.startswith("image/"):
            # Process image files
            image = Image.open(io.BytesIO(uploaded_file.read()))

            # Basic image metadata
            original_file_size = file_metadata['size']  # Preserve original file size
            file_metadata.update({
                "format": image.format,
                "mode": image.mode,
                "image_size": image.size,  # Don't overwrite file size
                "width": image.width,
                "height": image.height,
                "file_size": original_file_size  # Keep original file size
            })

            # For medical images, we'll use OCR or base64 encoding for AI analysis
            # Convert image to base64 for API submission
            buffered = io.BytesIO()
            image.save(buffered, format=image.format or "PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # Extract some basic image info
            file_content = f"""
Medical Image Analysis Request
Image Type: {uploaded_file.type}
Image Format: {image.format}
Image Size: {image.width}x{image.height} pixels
Image Mode: {image.mode}
File Size: {uploaded_file.size / 1024:.1f} KB

Note: This is a medical image that requires visual analysis for diagnostic purposes.
The image has been encoded for AI vision analysis.
            """.strip()

            return file_content, file_metadata, "image", img_str

    except Exception as e:
        raise Exception(f"Error processing {uploaded_file.type} file: {str(e)}")

    return None, file_metadata, "unknown"

def get_document_analysis_prompt(file_content, file_metadata, patient_info, doc_type):
    """Generate enhanced analysis prompt based on document type and patient context."""

    base_context = f"""
CLINICAL CONTEXT:
Patient: {patient_info['name']}, {datetime.now().year - patient_info['dob'].year} years old, {patient_info['gender']}
Patient ID: {patient_info['id']}
Contact: {patient_info['contact']}
Address: {patient_info['address']}

DOCUMENT INFORMATION:
Type: {doc_type.upper()}
Filename: {file_metadata['name']}
File Size: {file_metadata['size'] / 1024:.1f} KB
"""

    if doc_type == "pdf" and 'pages' in file_metadata:
        base_context += f"Pages: {file_metadata['pages']}\n"
        if 'title' in file_metadata and file_metadata['title'] != 'Unknown':
            base_context += f"Document Title: {file_metadata['title']}\n"

    if doc_type == "image":
        base_context += f"""
Image Details:
Format: {file_metadata.get('format', 'Unknown')}
Dimensions: {file_metadata.get('width', 'Unknown')}x{file_metadata.get('height', 'Unknown')} pixels
Color Mode: {file_metadata.get('mode', 'Unknown')}
"""

    if doc_type in ["text", "pdf"]:
        base_context += f"""
DOCUMENT CONTENT:
{file_content[:8000]}  # Limit content to avoid token limits
"""
        if len(file_content) > 8000:
            base_context += f"\n[Note: Document truncated - showing first 8000 characters of {len(file_content)} total characters]"

    prompt = f"""
You are an expert clinical AI assistant analyzing medical documents for patient care.

{base_context}

ANALYSIS TASKS:
1. **Document Type Identification**: Identify what type of medical document this is (lab results, imaging report, clinical notes, prescription, etc.)

2. **Key Findings Extraction**:
   - Extract all numerical values, measurements, and test results
   - Identify abnormal or critical values
   - Note any trends or patterns

3. **Clinical Significance Assessment**:
   - Interpret the findings in clinical context
   - Assess severity and urgency
   - Identify potential red flags

4. **Diagnostic Insights**:
   - What conditions or diagnoses might these findings suggest?
   - What differential diagnoses should be considered?
   - Are there findings that require immediate attention?

5. **Recommendations**:
   - Suggested follow-up tests or consultations
   - Treatment considerations based on findings
   - Monitoring recommendations

6. **Risk Assessment**:
   - Identify high-risk findings
   - Assess overall clinical risk level
   - Note any contraindications or warnings

Please provide a comprehensive, structured analysis that would be valuable for clinical decision-making. Use clear medical terminology but explain complex concepts. Highlight any critical findings that require urgent attention.
"""

    return prompt

def perform_document_analysis(patient_id, patient_info, file_content, file_metadata, doc_type, img_base64, analysis_type):
    """Perform AI analysis of uploaded document using OpenAI Responses API."""
    if not client:
        st.error("❌ OpenAI API not configured. Please set OPENAI_API_KEY environment variable.")
        return

    with st.spinner(f"🧠 AI performing {analysis_type.lower()}..."):
        try:
            # Generate tailored prompt based on analysis type
            base_prompt = get_document_analysis_prompt(file_content, file_metadata, patient_info, doc_type)

            if analysis_type == "Quick Summary":
                analysis_prompt = f"""
{base_prompt}

Provide a concise, bulleted summary focusing on:
1. Most important findings (top 3-5)
2. Critical values requiring immediate attention
3. Overall clinical impression
4. Key recommendations

Keep it brief but comprehensive for quick clinical review.
                """
            elif analysis_type == "Diagnostic Focus":
                analysis_prompt = f"""
{base_prompt}

Focus specifically on DIAGNOSTIC INSIGHTS:
1. Most likely diagnoses based on these findings
2. Differential diagnoses to consider
3. Key diagnostic criteria present or absent
4. Recommended confirmatory tests
5. Red flag symptoms or findings that require urgent evaluation

Provide detailed reasoning for each diagnostic consideration.
                """
            elif analysis_type == "Risk Assessment":
                analysis_prompt = f"""
{base_prompt}

Focus specifically on RISK ASSESSMENT:
1. High-risk findings and their clinical significance
2. Mortality/morbidity risk assessment
3. Risk of complications or deterioration
4. Factors that increase or decrease risk
5. Recommended monitoring and follow-up based on risk level
6. Emergency warning signs

Quantify risk where possible (low/medium/high risk).
                """
            elif analysis_type == "Treatment Recommendations":
                analysis_prompt = f"""
{base_prompt}

Focus specifically on TREATMENT RECOMMENDATIONS:
1. Evidence-based treatment options for identified conditions
2. Medication considerations (dosages, contraindications)
3. Lifestyle interventions
4. Referral recommendations
5. Follow-up schedule and monitoring parameters
6. Patient education points

Note: These are suggestions for clinical consideration - use professional judgment.
                """
            else:  # Comprehensive Analysis
                analysis_prompt = base_prompt

            # Prepare messages for Responses API
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert clinical AI assistant providing medical document analysis. Always prioritize patient safety and provide evidence-based insights."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ]

            # Use OpenAI Responses API with chat history
            response = client.responses.create(
                model="gpt-5-nano-2025-08-07",
                input=messages,
                store=True,  # Enable stateful context
                temperature=0.3
            )

            ai_analysis = response.output_text

            # Display the analysis
            st.markdown("### 📊 AI Analysis Results")
            st.markdown("---")
            st.markdown(ai_analysis)

            # Add warning disclaimer
            st.warning("⚠️ **Clinical Disclaimer**: This AI analysis is for informational purposes only and should not replace professional medical judgment. Always use clinical expertise and consider patient context when making medical decisions.")

            # Save analysis to patient record
            try:
                add_document(
                    patient_id,
                    file_metadata['name'],
                    doc_type,
                    ai_analysis,
                    file_metadata['size']
                )

                # Log the analysis
                log_audit_event(
                    st.session_state.current_user['username'],
                    "document_analysis",
                    f"AI analysis of {doc_type} document for patient {patient_id}",
                    patient_id
                )

                st.success("✅ Analysis saved to patient record")

            except Exception as save_error:
                st.warning(f"Analysis completed but couldn't save to record: {save_error}")

        except Exception as e:
            st.error(f"❌ AI Analysis failed: {str(e)}")
            st.info("Please check your OpenAI API configuration and try again.")

def save_document_to_patient_record(patient_id, uploaded_file, file_metadata, doc_type):
    """Save uploaded document to patient record."""
    try:
        # Read file content for storage
        file_content = uploaded_file.read()

        # Convert to base64 for storage if needed
        if isinstance(file_content, bytes):
            file_b64 = base64.b64encode(file_content).decode()
        else:
            file_b64 = str(file_content)

        # Create document summary
        doc_summary = f"""
Document Type: {doc_type.upper()}
Filename: {file_metadata['name']}
File Size: {file_metadata['size'] / 1024:.1f} KB
Upload Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Uploaded by: {st.session_state.current_user['username']}
        """.strip()

        # Save to database
        add_document(
            patient_id,
            file_metadata['name'],
            f"{doc_type} - {file_metadata['size']/1024:.1f}KB",
            doc_summary,
            file_metadata['size']
        )

        st.success("✅ Document saved to patient record!")
        st.balloons()

        # Log the action
        log_audit_event(
            st.session_state.current_user['username'],
            "document_upload",
            f"Uploaded {doc_type} document for patient {patient_id}",
            patient_id
        )

    except Exception as e:
        st.error(f"❌ Failed to save document: {str(e)}")

def perform_multi_document_analysis(patient_id, patient_info, selected_docs, analysis_type):
    """Perform AI analysis on multiple documents simultaneously."""
    if not client:
        st.error("❌ OpenAI API not configured. Please set OPENAI_API_KEY environment variable.")
        return

    with st.spinner(f"🧠 AI analyzing {len(selected_docs)} document(s)..."):
        try:
            # Combine all documents into a comprehensive analysis prompt
            combined_content = f"MULTI-DOCUMENT ANALYSIS REQUEST\n{'='*60}\n\n"
            combined_content += f"Patient: {patient_info['name']}, {datetime.now().year - patient_info['dob'].year} years old, {patient_info['gender']}\n"
            combined_content += f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            combined_content += f"Number of Documents: {len(selected_docs)}\n\n"

            for i, doc in enumerate(selected_docs, 1):
                combined_content += f"DOCUMENT {i}: {doc['metadata']['name']}\n"
                combined_content += f"Type: {doc['type'].upper()}\n"
                combined_content += f"Size: {doc['metadata']['size'] / 1024:.1f} KB\n"

                if doc['type'] == "pdf" and 'pages' in doc['metadata']:
                    combined_content += f"Pages: {doc['metadata']['pages']}\n"

                combined_content += f"Content:\n{doc['content'][:3000]}\n"  # Limit content per doc
                if len(doc['content']) > 3000:
                    combined_content += f"[Document truncated - showing first 3000 of {len(doc['content'])} characters]\n"
                combined_content += "\n" + "-"*60 + "\n\n"

            # Generate tailored analysis prompt
            if analysis_type == "Quick Summary":
                analysis_prompt = f"""
{combined_content}

Provide a comprehensive summary of all documents combined:

1. **Key Findings Across All Documents**: List the most important findings from all documents
2. **Cross-Document Patterns**: Identify correlations or patterns between different documents
3. **Critical Values**: Highlight any abnormal or critical values found
4. **Overall Clinical Picture**: Provide a consolidated clinical overview
5. **Priority Recommendations**: List the most important follow-up actions

Focus on insights that come from analyzing multiple documents together rather than individually.
                """
            elif analysis_type == "Diagnostic Focus":
                analysis_prompt = f"""
{combined_content}

Provide a comprehensive diagnostic analysis considering all documents:

1. **Primary Diagnostic Considerations**: Most likely diagnoses based on collective findings
2. **Supporting Evidence**: Which findings support each diagnostic consideration from which documents
3. **Cross-Referenced Findings**: How findings in one document support or contradict findings in others
4. **Diagnostic Workup Plan**: Recommended tests to confirm or rule out diagnoses
5. **Red Flag Analysis**: Any urgent findings requiring immediate attention across all documents
6. **Specialist Referrals**: Which specialists should be consulted based on combined findings

Emphasize how the combination of documents provides a more complete diagnostic picture.
                """
            elif analysis_type == "Risk Assessment":
                analysis_prompt = f"""
{combined_content}

Provide a comprehensive risk assessment based on all documents:

1. **High-Risk Findings**: Critical values or findings across all documents
2. **Mortality/Morbidity Risk**: Overall risk assessment considering all factors
3. **Complication Risk**: Risk of adverse outcomes based on combined findings
4. **Medication Risks**: Any identified contraindications, interactions, or warnings
5. **Lifestyle Risks**: Risk factors identified from the documents
6. **Monitoring Requirements**: What needs to be monitored based on risk level
7. **Emergency Indicators**: Symptoms or findings requiring immediate medical attention

Quantify risk levels (low/medium/high) where possible.
                """
            elif analysis_type == "Treatment Recommendations":
                analysis_prompt = f"""
{combined_content}

Provide comprehensive treatment recommendations based on all documents:

1. **Evidence-Based Treatment Options**: Recommended treatments based on findings
2. **Medication Recommendations**: Specific medications, dosages, and considerations
3. **Lifestyle Interventions**: Recommended lifestyle changes based on findings
4. **Therapeutic Priorities**: Which issues to address first based on severity
5. **Follow-Up Schedule**: Recommended timeline for monitoring and reassessment
6. **Referral Network**: Which specialists should be involved in care
7. **Patient Education Topics**: Key education points for the patient

Note all treatments should be considered in the context of the complete clinical picture from all documents.
                """
            else:  # Comprehensive Analysis
                analysis_prompt = f"""
{combined_content}

Provide a comprehensive multi-document analysis:

1. **Document Overview**: Summary of each document type and its purpose
2. **Integrated Findings**: How findings across documents create a complete picture
3. **Key Abnormalities**: All abnormal values and their clinical significance
4. **Diagnostic Insights**: What conditions or diagnoses are suggested
5. **Correlations**: How findings in different documents relate to each other
6. **Risk Assessment**: Overall clinical risk based on all findings
7. **Recommendations**: Consolidated recommendations for next steps
8. **Urgent Findings**: Anything requiring immediate attention
9. **Data Quality Assessment**: Any gaps or inconsistencies in the documentation

Provide a structured analysis that synthesizes information from all documents into actionable clinical insights.
                """

            # Use OpenAI Responses API
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert clinical AI assistant specializing in multi-document analysis. Synthesize information from multiple medical documents to provide comprehensive clinical insights. Always prioritize patient safety and consider how findings across documents create a complete clinical picture."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ]

            response = client.responses.create(
                model="gpt-5-nano-2025-08-07",
                input=messages,
                store=True,
                temperature=0.3
            )

            ai_analysis = response.output_text

            # Display the analysis
            st.markdown("### 📊 Multi-Document AI Analysis Results")
            st.markdown("---")
            st.markdown(ai_analysis)

            # Add warning disclaimer
            st.warning("⚠️ **Clinical Disclaimer**: This AI analysis is for informational purposes only and should not replace professional medical judgment. Always use clinical expertise and consider patient context when making medical decisions.")

            # Save analysis to patient record
            try:
                doc_names = ", ".join([doc['metadata']['name'] for doc in selected_docs])
                add_document(
                    patient_id,
                    f"Multi-Document Analysis: {len(selected_docs)} documents",
                    f"AI Analysis - {analysis_type}",
                    f"Analyzed documents: {doc_names}\n\n{ai_analysis}",
                    sum(doc['metadata']['size'] for doc in selected_docs)
                )

                # Log the analysis
                log_audit_event(
                    st.session_state.current_user['username'],
                    "multi_document_analysis",
                    f"AI analysis of {len(selected_docs)} documents for patient {patient_id}",
                    patient_id
                )

                st.success("✅ Multi-document analysis saved to patient record")

            except Exception as save_error:
                st.warning(f"Analysis completed but couldn't save to record: {save_error}")

        except Exception as e:
            st.error(f"❌ Multi-document analysis failed: {str(e)}")
            st.info("Please check your OpenAI API configuration and try again.")

def save_multiple_documents_to_record(patient_id, documents):
    """Save multiple documents to patient record."""
    success_count = 0
    error_count = 0

    with st.spinner("💾 Saving documents to patient record..."):
        for doc in documents:
            try:
                # Create document summary
                doc_summary = f"""
Document Type: {doc['type'].upper()}
Filename: {doc['metadata']['name']}
File Size: {doc['metadata']['size'] / 1024:.1f} KB
Upload Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Uploaded by: {st.session_state.current_user['username']}
Session ID: {doc['session_id']}

Content Preview:
{doc['content'][:500]}...
                """.strip()

                # Save to database
                add_document(
                    patient_id,
                    doc['metadata']['name'],
                    f"{doc['type']} - {doc['metadata']['size']/1024:.1f}KB",
                    doc_summary,
                    doc['metadata']['size']
                )

                success_count += 1

            except Exception as e:
                st.error(f"Failed to save {doc['metadata']['name']}: {str(e)}")
                error_count += 1

        # Display results
        if success_count > 0:
            st.success(f"✅ Successfully saved {success_count} document(s) to patient record!")
            st.balloons()

        if error_count > 0:
            st.warning(f"⚠️ Failed to save {error_count} document(s)")

        # Log the batch save action
        log_audit_event(
            st.session_state.current_user['username'],
            "batch_document_upload",
            f"Saved {success_count} documents for patient {patient_id}",
            patient_id
        )

def display_saved_documents_for_chat(patient_id):
    """Display saved documents and allow selection for chat reference."""
    try:
        st.markdown("### 📚 Saved Patient Documents")

        # Get saved documents
        saved_docs = get_documents(patient_id)

        if saved_docs.empty:
            st.info("No saved documents found for this patient.")
            return

        st.info("📋 Select documents to include in the current chat session for AI context")

        # Filter and sort documents
        saved_docs = saved_docs.sort_values('created_date', ascending=False)

        # Document selection interface
        selected_docs = []

        for i, (_, doc) in enumerate(saved_docs.iterrows()):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                # Document info
                doc_title = f"📄 {doc['document_name']}"
                if doc['document_type']:
                    doc_title += f" ({doc['document_type']})"

                # Add date info
                if hasattr(doc, 'created_date') and pd.notna(doc['created_date']):
                    doc_title += f" - {doc['created_date'].strftime('%Y-%m-%d')}"

                selected = st.checkbox(doc_title, key=f"saved_doc_{i}", help="Include in chat context")

                if selected:
                    selected_docs.append(doc)

                    # Show document preview in expander
                    with st.expander(f"Preview: {doc['document_name']}", expanded=False):
                        if doc['notes']:
                            st.text_area("Content:", value=doc['notes'][:1000], height=150, disabled=True)
                            if len(doc['notes']) > 1000:
                                st.caption(f"Showing first 1000 of {len(doc['notes'])} characters")
                        else:
                            st.info("No content preview available")

        # Action buttons
        if selected_docs:
            st.markdown("---")
            col1, col2 = st.columns([2, 1])

            with col1:
                st.success(f"Selected {len(selected_docs)} document(s) for chat context")

            with col2:
                if st.button("🔄 Add to Chat", type="primary", use_container_width=True):
                    # Add selected documents to session state for chat context
                    if 'chat_context_documents' not in st.session_state:
                        st.session_state.chat_context_documents = []

                    for doc in selected_docs:
                        st.session_state.chat_context_documents.append({
                            'id': doc['id'],
                            'name': doc['document_name'],
                            'type': doc['document_type'],
                            'content': doc['notes'] or "",
                            'added_time': datetime.now()
                        })

                    st.success(f"✅ Added {len(selected_docs)} documents to chat context!")
                    st.session_state.show_saved_documents = False
                    st.rerun()

        # Close button
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_saved_documents = False
            st.rerun()

    except Exception as e:
        st.error(f"❌ Error loading saved documents: {str(e)}")

# Main application
def main():
    """Main enhanced EHR application."""
    # Apply custom theme
    set_custom_theme()

    # Authentication check
    if not st.session_state.get("authenticated"):
        show_login_page()
        return

    # Get current user
    current_user = get_current_user()
    if not current_user:
        logout()
        st.rerun()
        return

    # Header with user info and logout
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div class="header-gradient">
            <h1>🏥 Next-Gen EHR System</h1>
            <p>Welcome, Dr. {current_user.get('name', current_user['username'])} | {current_user.get('role', 'staff').title()}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    with col3:
        if st.button("🚪 Logout"):
            log_audit_event(current_user['username'], "logout", "User logged out")
            logout()
            st.rerun()

    # Sidebar navigation
    with st.sidebar:
        st.markdown("---")
        theme_toggle()
        st.markdown("---")

        navigation_options = [
            "🏠 Dashboard",
            "👥 Patient Management",
            "📅 Appointments",
            "💊 Medications",
            "🧪 Lab Results",
            "🤧 Allergies & Immunizations",
            "📝 Clinical Notes",
            "🤖 AI Assistant",
            "📊 Analytics",
            "⚙️ Settings"
        ]

        section = st.selectbox("Navigation", navigation_options)

    # Render selected section
    if section == "🏠 Dashboard":
        show_dashboard()
    elif section == "👥 Patient Management":
        show_patient_management()
    elif section == "📅 Appointments":
        show_appointments()
    elif section == "💊 Medications":
        show_medications()
    elif section == "🧪 Lab Results":
        show_lab_results()
    elif section == "🤧 Allergies & Immunizations":
        show_allergies_immunizations()
    elif section == "📝 Clinical Notes":
        show_clinical_notes()
    elif section == "🤖 AI Assistant":
        show_ai_assistant()
    elif section == "📊 Analytics":
        show_analytics()
    elif section == "⚙️ Settings":
        show_settings()

def show_dashboard():
    """Enhanced dashboard with key metrics and insights."""
    st.header("📊 Clinical Dashboard")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    # Get metrics
    patients_df = get_patients()
    appointments_df = get_appointments(status="scheduled")
    today = datetime.now().date()
    today_appointments = appointments_df[
        pd.to_datetime(appointments_df['appointment_date']).dt.date == today
    ]

    with col1:
        modern_metric_card(
            "Total Patients",
            f"{len(patients_df)}",
            f"+{len(patients_df) // 10} this month",
            "👥",
            "blue"
        )

    with col2:
        modern_metric_card(
            "Today's Appointments",
            f"{len(today_appointments)}",
            f"{len(appointments_df)} this week",
            "📅",
            "green"
        )

    with col3:
        modern_metric_card(
            "Active Prescriptions",
            "142",
            "8 pending renewal",
            "💊",
            "purple"
        )

    with col4:
        modern_metric_card(
            "Critical Lab Results",
            "3",
            "Require attention",
            "🚨",
            "red"
        )

    st.markdown("---")

    # Recent activity and upcoming appointments
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Recent Patient Activity")
        recent_activity = get_recent_patient_activity(5)
        if not recent_activity.empty:
            for _, activity in recent_activity.iterrows():
                st.markdown(f"""
                <div style="padding: 0.75rem; background: #f8f9fa; border-radius: 8px; margin-bottom: 0.5rem;">
                    <strong>{activity['patient_name']}</strong> - {activity['encounter_type']}<br>
                    <small>{activity['encounter_date']} with Dr. {activity['doctor']}</small>
                </div>
                """, unsafe_allow_html=True)

    with col2:
        st.subheader("📅 Today's Schedule")
        if not today_appointments.empty:
            for _, apt in today_appointments.iterrows():
                time_str = pd.to_datetime(apt['appointment_date']).strftime('%I:%M %p')
                st.markdown(f"""
                <div style="padding: 0.75rem; background: #e8f5e8; border-radius: 8px; margin-bottom: 0.5rem;">
                    <strong>{time_str}</strong> - {apt['patient_name']}<br>
                    <small>{apt['appointment_type']} ({apt['duration']} min)</small>
                </div>
                """, unsafe_allow_html=True)

    # Notifications
    st.markdown("---")
    st.subheader("🔔 Notifications & Alerts")
    notification_system()

def show_patient_management():
    """Enhanced patient management interface."""
    st.header("👥 Patient Management")

    # Search functionality
    patients_df = get_patients()
    filtered_patients, search_term = smart_search_bar(
        patients_df, ['name', 'contact', 'address'], 'patients'
    )

    if search_term:
        st.info(f"Found {len(filtered_patients)} patients matching '{search_term}'")

    # Registration section
    with st.expander("➕ Register New Patient", expanded=False):
        with st.form("register_patient_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Full Name *")
                dob = st.date_input("Date of Birth *")
                gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
                contact = st.text_input("Contact Number *")
                email = st.text_input("Email Address")

            with col2:
                address = st.text_area("Address *")
                emergency_contact = st.text_input("Emergency Contact")
                blood_type = st.selectbox("Blood Type", ["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
                marital_status = st.selectbox("Marital Status", ["", "Single", "Married", "Divorced", "Widowed"])
                employment = st.text_input("Employment")

            col3, col4 = st.columns(2)
            with col3:
                insurance_provider = st.text_input("Insurance Provider")
            with col4:
                insurance_policy = st.text_input("Policy Number")

            submitted = st.form_submit_button("Register Patient", use_container_width=True)

            if submitted and all([name, dob, gender, contact, address]):
                add_patient_enhanced(
                    name, dob, gender, contact, address,
                    emergency_contact, blood_type, marital_status,
                    employment, insurance_provider, insurance_policy
                )
                log_audit_event(
                    st.session_state.current_user['username'],
                    "patient_registration",
                    f"Registered new patient: {name}"
                )
                st.success(f"Patient '{name}' registered successfully!")
                st.rerun()

    # Patient list with enhanced display
    st.subheader("📋 Patient Registry")

    if not filtered_patients.empty:
        # Display patient cards
        for _, patient in filtered_patients.iterrows():
            with st.container():
                patient_summary_card(patient.to_dict())

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button(f"📝 View Details", key=f"view_{patient['id']}"):
                        st.session_state.selected_patient_id = patient['id']
                with col2:
                    if st.button("📅 Schedule", key=f"schedule_{patient['id']}"):
                        st.session_state.schedule_patient_id = patient['id']
                with col3:
                    if st.button("💊 Prescribe", key=f"prescribe_{patient['id']}"):
                        st.session_state.prescribe_patient_id = patient['id']
                with col4:
                    if st.button("📊 Analytics", key=f"analytics_{patient['id']}"):
                        st.session_state.analytics_patient_id = patient['id']

                st.markdown("---")
    else:
        st.info("No patients found. Register your first patient above!")

def show_appointments():
    """Appointment scheduling and management."""
    st.header("📅 Appointment Management")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📅 Schedule New Appointment")

        with st.form("schedule_appointment"):
            patients_df = get_patients()
            patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

            selected_patient = st.selectbox("Select Patient *", list(patient_options.keys()))
            patient_id = patient_options[selected_patient] if selected_patient else None

            appointment_type = st.selectbox(
                "Appointment Type *",
                ["Consultation", "Follow-up", "Procedure", "Emergency", "Vaccination", "Lab Test"]
            )

            col1, col2 = st.columns(2)
            with col1:
                appointment_date = st.date_input("Date *", value=datetime.now().date())
            with col2:
                appointment_time = st.time_input("Time *")

            duration = st.selectbox("Duration (minutes)", [15, 30, 45, 60, 90, 120])
            notes = st.text_area("Notes")

            if st.form_submit_button("Schedule Appointment", use_container_width=True):
                if patient_id and appointment_date and appointment_time:
                    appointment_datetime = datetime.combine(appointment_date, appointment_time)
                    add_appointment(
                        patient_id, 1, appointment_type,
                        appointment_datetime, duration, notes
                    )
                    log_audit_event(
                        st.session_state.current_user['username'],
                        "appointment_scheduled",
                        f"Scheduled {appointment_type} for patient ID: {patient_id}"
                    )
                    st.success("Appointment scheduled successfully!")
                    st.rerun()

    with col2:
        st.subheader("📊 Today's Summary")

        today = datetime.now().date()
        today_appts = get_appointments(status="scheduled")
        today_appts = today_appts[
            pd.to_datetime(today_appts['appointment_date']).dt.date == today
        ]

        modern_metric_card(
            "Today's Appointments",
            f"{len(today_appts)}",
            "Scheduled",
            "📅",
            "blue"
        )

        if not today_appts.empty:
            st.markdown("**Upcoming Today:**")
            for _, apt in today_appts.iterrows():
                time_str = pd.to_datetime(apt['appointment_date']).strftime('%I:%M %p')
                st.markdown(f"• {time_str} - {apt['patient_name']}")

    st.markdown("---")

    # Appointment list
    st.subheader("📋 All Appointments")

    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "scheduled", "completed", "cancelled", "no-show"]
    )

    all_appointments = get_appointments()
    if status_filter != "All":
        all_appointments = all_appointments[all_appointments['status'] == status_filter]

    if not all_appointments.empty:
        # Format datetime for display
        all_appointments['appointment_datetime'] = pd.to_datetime(all_appointments['appointment_date'])
        all_appointments['date'] = all_appointments['appointment_datetime'].dt.date
        all_appointments['time'] = all_appointments['appointment_datetime'].dt.strftime('%I:%M %p')

        display_df = all_appointments[[
            'patient_name', 'appointment_type', 'date', 'time',
            'duration', 'status', 'notes', 'appointment_datetime'
        ]].sort_values('appointment_datetime')

        # Remove appointment_datetime from final display
        display_df = display_df.drop('appointment_datetime', axis=1)

        st.dataframe(display_df, use_container_width=True)

        # Batch actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_to_complete = st.multiselect(
                "Mark as Completed",
                options=all_appointments['id'].tolist(),
                format_func=lambda x: f"ID: {x}"
            )
            if st.button("✅ Mark Completed"):
                for apt_id in selected_to_complete:
                    update_appointment_status(apt_id, "completed")
                st.success("Appointments marked as completed!")
                st.rerun()

        with col2:
            selected_to_cancel = st.multiselect(
                "Cancel Appointments",
                options=all_appointments['id'].tolist(),
                format_func=lambda x: f"ID: {x}"
            )
            if st.button("❌ Cancel Selected"):
                for apt_id in selected_to_cancel:
                    update_appointment_status(apt_id, "cancelled")
                st.success("Appointments cancelled!")
                st.rerun()
    else:
        st.info("No appointments found.")

def show_medications():
    """Medication and prescription management."""
    st.header("💊 Medication Management")

    # Tabs for different medication functions
    tab1, tab2, tab3 = st.tabs(["📋 Prescriptions", "💊 Medication Library", "⚠️ Interactions"])

    with tab1:
        st.subheader("📋 Patient Prescriptions")

        # Patient selection
        patients_df = get_patients()
        patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

        selected_patient = st.selectbox("Select Patient", list(patient_options.keys()))
        patient_id = patient_options[selected_patient] if selected_patient else None

        if patient_id:
            # Add new prescription
            with st.expander("➕ Add New Prescription", expanded=False):
                with st.form("add_prescription"):
                    medications = get_medications()
                    med_options = {f"{row['name']} ({row['strength']})": row['id'] for _, row in medications.iterrows()}

                    selected_med = st.selectbox("Select Medication", list(med_options.keys()))
                    medication_id = med_options[selected_med] if selected_med else None

                    col1, col2 = st.columns(2)
                    with col1:
                        dosage = st.text_input("Dosage (e.g., 10mg)")
                        frequency = st.text_input("Frequency (e.g., Twice daily)")
                    with col2:
                        route = st.selectbox("Route", ["Oral", "IV", "IM", "Topical", "Inhalation"])
                        duration_days = st.number_input("Duration (days)", min_value=1, value=7)

                    start_date = st.date_input("Start Date", value=datetime.now().date())
                    end_date = st.date_input("End Date", value=datetime.now().date() + timedelta(days=duration_days))
                    notes = st.text_area("Notes")

                    if st.form_submit_button("Add Prescription"):
                        if medication_id and dosage and frequency:
                            add_prescription(
                                patient_id, medication_id, None, dosage, frequency,
                                route, start_date, end_date,
                                st.session_state.current_user['username'], notes
                            )
                            log_audit_event(
                                st.session_state.current_user['username'],
                                "prescription_added",
                                f"Added prescription for patient ID: {patient_id}"
                            )
                            st.success("Prescription added successfully!")
                            st.rerun()

            # Display current prescriptions
            st.subheader("Current Prescriptions")
            prescriptions = get_prescriptions(patient_id, status="active")

            if not prescriptions.empty:
                for _, rx in prescriptions.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="padding: 1rem; background: #f0f8ff; border-radius: 8px; margin-bottom: 0.5rem;">
                            <strong>{rx['medication_name']}</strong><br>
                            <small>{rx['dosage']} - {rx['frequency']} ({rx['route']})</small><br>
                            <small>From {rx['start_date']} to {rx['end_date']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if st.button("✅ Complete", key=f"complete_{rx['id']}"):
                            # Update prescription status to completed
                            pass
                    with col3:
                        if st.button("📝 Edit", key=f"edit_{rx['id']}"):
                            # Edit prescription
                            pass
            else:
                st.info("No active prescriptions for this patient.")

    with tab2:
        st.subheader("💊 Medication Library")

        with st.expander("➕ Add New Medication", expanded=False):
            with st.form("add_medication"):
                name = st.text_input("Medication Name *")
                generic_name = st.text_input("Generic Name")
                drug_class = st.text_input("Drug Class")
                description = st.text_area("Description")
                dosage_form = st.selectbox("Dosage Form", ["Tablet", "Capsule", "Liquid", "Injection", "Topical"])
                strength = st.text_input("Strength (e.g., 10mg)")

                col1, col2 = st.columns(2)
                with col1:
                    contraindications = st.text_area("Contraindications")
                    side_effects = st.text_area("Side Effects")
                with col2:
                    interactions = st.text_area("Drug Interactions")

                if st.form_submit_button("Add Medication"):
                    if name:
                        add_medication(
                            name, generic_name, drug_class, description,
                            contraindications, side_effects, interactions,
                            dosage_form, strength
                        )
                        st.success("Medication added to library!")
                        st.rerun()

        # Display medications
        medications = get_medications()
        if not medications.empty:
            st.dataframe(medications[['name', 'generic_name', 'drug_class', 'dosage_form', 'strength']],
                         use_container_width=True)

    with tab3:
        st.subheader("⚠️ Drug Interaction Checker")

        if patient_id:
            current_prescriptions = get_prescriptions(patient_id, status="active")
            if not current_prescriptions.empty:
                medication_ids = current_prescriptions['medication_id'].tolist()

                if len(medication_ids) > 1:
                    interactions = check_medication_interactions(medication_ids)

                    st.warning("⚠️ Potential Interactions Detected:")
                    for _, med in interactions.iterrows():
                        if med['interactions']:
                            st.markdown(f"""
                            <div style="padding: 1rem; background: #fff3cd; border-radius: 8px; margin-bottom: 0.5rem;">
                                <strong>{med['name']}</strong><br>
                                <small>{med['interactions']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("Add more medications to check for interactions.")
            else:
                st.info("No active prescriptions to check.")

def show_lab_results():
    """Lab results management."""
    st.header("🧪 Lab Results Management")

    # Patient selection
    patients_df = get_patients()
    patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

    selected_patient = st.selectbox("Select Patient", list(patient_options.keys()))
    patient_id = patient_options[selected_patient] if selected_patient else None

    if patient_id:
        # Add new lab results
        with st.expander("➕ Add Lab Results", expanded=False):
            with st.form("add_lab_result"):
                test_name = st.text_input("Test Name *")
                test_category = st.selectbox(
                    "Test Category *",
                    ["CBC", "Chemistry", "Hematology", "Endocrinology", "Immunology", "Microbiology", "Other"]
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    result_value = st.text_input("Result Value *")
                    unit = st.text_input("Unit (e.g., mg/dL)")
                with col2:
                    reference_range = st.text_input("Reference Range")
                    status = st.selectbox("Status", ["normal", "abnormal", "critical"])
                with col3:
                    performed_date = st.date_input("Test Date", value=datetime.now().date())
                    performed_by = st.text_input("Performed By")

                notes = st.text_area("Notes")

                if st.form_submit_button("Add Lab Result"):
                    if test_name and result_value:
                        add_lab_result(
                            patient_id, None, test_name, test_category,
                            result_value, reference_range, unit, status,
                            performed_date, performed_by, notes
                        )
                        log_audit_event(
                            st.session_state.current_user['username'],
                            "lab_result_added",
                            f"Added {test_name} result for patient ID: {patient_id}"
                        )
                        st.success("Lab result added successfully!")
                        st.rerun()

        # Display lab results
        st.subheader("📊 Lab Results History")

        # Filter by category
        all_results = get_lab_results(patient_id)
        if not all_results.empty:
            categories = ["All"] + all_results['test_category'].unique().tolist()
            selected_category = st.selectbox("Filter by Category", categories)

            if selected_category != "All":
                filtered_results = all_results[all_results['test_category'] == selected_category]
            else:
                filtered_results = all_results

            # Critical results alert
            critical_results = filtered_results[filtered_results['status'] == 'critical']
            if not critical_results.empty:
                st.error("🚨 CRITICAL RESULTS DETECTED!")
                for _, result in critical_results.iterrows():
                    st.markdown(f"""
                    <div style="padding: 1rem; background: #f8d7da; border-radius: 8px; margin-bottom: 0.5rem;">
                        <strong>{result['test_name']}</strong>: {result['result_value']} {result['unit']}<br>
                        <small>Test Date: {result['performed_date']} | Status: CRITICAL</small>
                    </div>
                    """, unsafe_allow_html=True)

            # Display results table
            display_cols = ['test_name', 'test_category', 'result_value', 'unit',
                           'reference_range', 'status', 'performed_date']
            st.dataframe(filtered_results[display_cols], use_container_width=True)

            # Trend visualization for repeated tests
            if len(filtered_results) > 1:
                st.subheader("📈 Result Trends")

                # Group by test name and create trend charts
                for test_name in filtered_results['test_name'].unique():
                    test_data = filtered_results[filtered_results['test_name'] == test_name]
                    if len(test_data) > 1:
                        try:
                            # Convert result values to numeric if possible
                            numeric_values = pd.to_numeric(test_data['result_value'], errors='coerce')
                            if not numeric_values.isna().all():
                                fig = px.line(
                                    x=test_data['performed_date'],
                                    y=numeric_values,
                                    title=f"{test_name} Trend",
                                    markers=True
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        except:
                            continue
        else:
            st.info("No lab results found for this patient.")

def show_allergies_immunizations():
    """Allergies and immunizations management."""
    st.header("🤧 Allergies & Immunizations")

    tab1, tab2 = st.tabs(["🤧 Allergies", "💉 Immunizations"])

    with tab1:
        # Patient selection
        patients_df = get_patients()
        patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

        selected_patient = st.selectbox("Select Patient", list(patient_options.keys()), key="allergy_patient")
        patient_id = patient_options[selected_patient] if selected_patient else None

        if patient_id:
            # Add new allergy
            with st.expander("➕ Add Allergy", expanded=False):
                with st.form("add_allergy"):
                    allergen = st.text_input("Allergen *")
                    allergen_type = st.selectbox(
                        "Allergen Type *",
                        ["Medication", "Food", "Environmental", "Latex", "Insect", "Other"]
                    )
                    reaction = st.text_input("Reaction *")
                    severity = st.selectbox("Severity *", ["Mild", "Moderate", "Severe"])
                    notes = st.text_area("Additional Notes")

                    if st.form_submit_button("Add Allergy"):
                        if allergen and reaction:
                            add_allergy(patient_id, allergen, allergen_type, reaction, severity, notes)
                            log_audit_event(
                                st.session_state.current_user['username'],
                                "allergy_added",
                                f"Added {allergen} allergy for patient ID: {patient_id}"
                            )
                            st.success("Allergy added successfully!")
                            st.rerun()

            # Display allergies
            st.subheader("🚨 Current Allergies")
            allergies = get_allergies(patient_id)

            if not allergies.empty:
                for _, allergy in allergies.iterrows():
                    severity_color = {"Mild": "#28a745", "Moderate": "#ffc107", "Severe": "#dc3545"}
                    color = severity_color.get(allergy['severity'], "#6c757d")

                    st.markdown(f"""
                    <div style="padding: 1rem; background: {color}20; border-left: 4px solid {color};
                               border-radius: 8px; margin-bottom: 0.5rem;">
                        <strong>{allergy['allergen']}</strong> ({allergy['allergen_type']})<br>
                        <small>Reaction: {allergy['reaction']} | Severity: {allergy['severity']}</small>
                        {f'<br><small>Notes: {allergy["notes"]}</small>' if allergy['notes'] else ''}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No allergies recorded for this patient.")

    with tab2:
        # Patient selection
        selected_patient_imm = st.selectbox("Select Patient", list(patient_options.keys()), key="imm_patient")
        patient_id_imm = patient_options[selected_patient_imm] if selected_patient_imm else None

        if patient_id_imm:
            # Add new immunization
            with st.expander("➕ Add Immunization", expanded=False):
                with st.form("add_immunization"):
                    vaccine_name = st.text_input("Vaccine Name *")
                    vaccine_type = st.selectbox(
                        "Vaccine Type",
                        ["COVID-19", "Influenza", "Hepatitis B", "MMR", "DTaP", "Polio", "Other"]
                    )
                    dose_number = st.number_input("Dose Number", min_value=1, value=1)
                    administered_date = st.date_input("Date Administered", value=datetime.now().date())
                    administered_by = st.text_input("Administered By *")
                    next_due_date = st.date_input("Next Due Date")
                    lot_number = st.text_input("Lot Number")
                    site = st.selectbox("Injection Site", ["Left Arm", "Right Arm", "Left Thigh", "Right Thigh"])
                    notes = st.text_area("Notes")

                    if st.form_submit_button("Add Immunization"):
                        if vaccine_name and administered_by:
                            add_immunization(
                                patient_id_imm, vaccine_name, vaccine_type, dose_number,
                                administered_date, administered_by, next_due_date,
                                lot_number, site, notes
                            )
                            log_audit_event(
                                st.session_state.current_user['username'],
                                "immunization_added",
                                f"Added {vaccine_name} immunization for patient ID: {patient_id_imm}"
                            )
                            st.success("Immunization added successfully!")
                            st.rerun()

            # Display immunizations
            st.subheader("💉 Immunization Record")
            immunizations = get_immunizations(patient_id_imm)

            if not immunizations.empty:
                # Immunization status
                upcoming = immunizations[immunizations['next_due_date'] > datetime.now().date()]
                overdue = immunizations[immunizations['next_due_date'] < datetime.now().date()]

                if not overdue.empty:
                    st.warning("⚠️ Overdue Immunizations:")
                    for _, imm in overdue.iterrows():
                        st.markdown(f"""
                        <div style="padding: 0.75rem; background: #f8d7da; border-radius: 8px; margin-bottom: 0.5rem;">
                            <strong>{imm['vaccine_name']}</strong> - Dose {imm['dose_number']}<br>
                            <small>Due: {imm['next_due_date']} (Overdue)</small>
                        </div>
                        """, unsafe_allow_html=True)

                if not upcoming.empty:
                    st.info("📅 Upcoming Immunizations:")
                    for _, imm in upcoming.iterrows():
                        st.markdown(f"""
                        <div style="padding: 0.75rem; background: #d1ecf1; border-radius: 8px; margin-bottom: 0.5rem;">
                            <strong>{imm['vaccine_name']}</strong> - Dose {imm['dose_number']}<br>
                            <small>Due: {imm['next_due_date']}</small>
                        </div>
                        """, unsafe_allow_html=True)

                # Full immunization history
                st.subheader("📋 Complete History")
                display_cols = ['vaccine_name', 'vaccine_type', 'dose_number', 'administered_date',
                               'administered_by', 'next_due_date', 'lot_number']
                st.dataframe(immunizations[display_cols], use_container_width=True)
            else:
                st.info("No immunizations recorded for this patient.")

def show_clinical_notes():
    """Enhanced clinical notes and encounters."""
    st.header("📝 Clinical Notes & Encounters")

    # Patient selection
    patients_df = get_patients()
    patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

    selected_patient = st.selectbox("Select Patient", list(patient_options.keys()))
    patient_id = patient_options[selected_patient] if selected_patient else None

    if patient_id:
        patient_info = get_patient_by_id(patient_id)

        # Patient summary
        if patient_info is not None:
            patient_summary_card(patient_info.to_dict())

        # Add new encounter
        with st.expander("➕ Add Clinical Encounter", expanded=False):
            with st.form("add_encounter"):
                encounter_type = st.selectbox(
                    "Encounter Type *",
                    ["Consultation", "Follow-up", "Emergency", "Procedure", "Telemedicine"]
                )

                col1, col2 = st.columns(2)
                with col1:
                    encounter_date = st.date_input("Date *", value=datetime.now().date())
                    doctor = st.text_input("Doctor/Provider *")
                with col2:
                    chief_complaint = st.text_input("Chief Complaint")

                # SOAP note structure
                st.markdown("### SOAP Note")
                subjective = st.text_area("Subjective (S)", height=100,
                    help="Patient's reported symptoms, feelings, history")
                objective = st.text_area("Objective (O)", height=100,
                    help="Vital signs, exam findings, test results")
                assessment = st.text_area("Assessment (A)", height=100,
                    help="Diagnosis, differential diagnoses")
                plan = st.text_area("Plan (P)", height=100,
                    help="Treatment plan, medications, follow-up")

                if st.form_submit_button("Save Encounter"):
                    # Combine SOAP notes
                    notes = f"""
CHIEF COMPLAINT: {chief_complaint}

SUBJECTIVE:
{subjective}

OBJECTIVE:
{objective}

ASSESSMENT:
{assessment}

PLAN:
{plan}
                    """.strip()

                    add_encounter(
                        patient_id, encounter_date, encounter_type, notes, doctor
                    )
                    log_audit_event(
                        st.session_state.current_user['username'],
                        "encounter_added",
                        f"Added {encounter_type} encounter for patient ID: {patient_id}"
                    )
                    st.success("Clinical encounter saved successfully!")
                    st.rerun()

        # Display encounters
        st.subheader("📋 Encounter History")
        encounters = get_encounters(patient_id)

        if not encounters.empty:
            # Create activity timeline
            create_activity_timeline(encounters)

            # Detailed encounter view
            st.subheader("📄 Detailed Notes")
            for _, encounter in encounters.iterrows():
                with st.expander(f"{encounter['date'].strftime('%Y-%m-%d')} - {encounter['type']} with Dr. {encounter['doctor']}"):
                    st.markdown(f"""
                    <div style="white-space: pre-wrap; padding: 1rem; background: #f8f9fa;
                               border-radius: 8px; line-height: 1.6;">
                    {encounter['notes']}
                    </div>
                    """, unsafe_allow_html=True)

                    # Document attachments
                    docs = get_documents(patient_id)
                    encounter_docs = docs[docs['encounter_id'] == encounter['id']]
                    if not encounter_docs.empty:
                        st.markdown("**📎 Attached Documents:**")
                        for _, doc in encounter_docs.iterrows():
                            st.markdown(f"• {os.path.basename(doc['file_path'])} ({doc['type']})")
        else:
            st.info("No encounters recorded for this patient.")

def show_ai_assistant():
    """AI-powered clinical assistant."""
    st.header("🤖 AI Clinical Assistant")

    if not client:
        st.error("AI Assistant is not available. Please configure OpenAI API key.")
        return

    # Patient selection
    patients_df = get_patients()
    patient_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in patients_df.iterrows()}

    selected_patient = st.selectbox("Select Patient", list(patient_options.keys()))
    patient_id = patient_options[selected_patient] if selected_patient else None

    if patient_id:
        patient_info = get_patient_by_id(patient_id)

        # AI assistant tabs
        tab1, tab2, tab3 = st.tabs(["💬 Clinical Chat", "📋 Document Analysis", "🔍 Differential Diagnosis"])

        with tab1:
            st.subheader("💬 Clinical Consultation Chat")

            # Initialize chat history
            chat_key = f"ai_chat_{patient_id}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = get_ai_conversation_history(patient_id)

            # Chat controls and document context
            col1, col2, col3 = st.columns([3, 1, 1])
            with col2:
                if st.button("🗑️ Clear Chat", type="secondary"):
                    st.session_state[chat_key] = []
                    st.rerun()
            with col3:
                if st.button("📚 Add Documents", type="secondary"):
                    st.session_state.show_saved_documents = True
                    st.rerun()

            # Display active document context
            if st.session_state.get('chat_context_documents'):
                with st.expander("📄 Active Document Context", expanded=False):
                    st.info(f"🔗 {len(st.session_state.chat_context_documents)} document(s) are included in chat context")
                    for doc in st.session_state.chat_context_documents:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"**{doc['name']}** ({doc['type']})")
                            st.caption(f"Added: {doc['added_time'].strftime('%H:%M:%S')}")
                        with col2:
                            if st.button("🗑️", key=f"remove_doc_{doc['id']}", help="Remove from context"):
                                st.session_state.chat_context_documents = [
                                    d for d in st.session_state.chat_context_documents
                                    if d['id'] != doc['id']
                                ]
                                st.rerun()

            # Display chat messages
            for message in st.session_state[chat_key][-10:]:  # Show last 10 messages
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if prompt := st.chat_input("Ask clinical questions or request analysis..."):
                # Add user message
                st.session_state[chat_key].append({"role": "user", "content": prompt})
                add_ai_conversation_entry(patient_id, "user", prompt)

                with st.chat_message("user"):
                    st.markdown(prompt)

                # Generate AI response
                with st.chat_message("assistant"):
                    with st.spinner("AI Assistant is thinking..."):
                        # Build patient context
                        patient_context = f"""
Patient: {patient_info['name']}, {datetime.now().year - patient_info['dob'].year} years old, {patient_info['gender']}
Contact: {patient_info['contact']}
                        """.strip()

                        # Get recent encounters for context
                        recent_encounters = get_encounters(patient_id).head(3)
                        encounters_context = ""
                        if not recent_encounters.empty:
                            encounters_context = "\n".join([
                                f"Recent {enc['type']} on {enc['date']}: {enc['notes'][:200]}..."
                                for _, enc in recent_encounters.iterrows()
                            ])

                        # Get patient documents for additional context
                        document_context = ""

                        # Add chat context documents first (highest priority)
                        if st.session_state.get('chat_context_documents'):
                            document_context += "**SELECTED DOCUMENTS FOR CHAT CONTEXT:**\n"
                            for doc in st.session_state.chat_context_documents:
                                document_context += f"- {doc['name']} ({doc['type']}): {doc['content'][:500]}...\n"
                            document_context += "\n"

                        # Add recent patient documents
                        patient_documents = get_documents(patient_id)
                        if not patient_documents.empty:
                            recent_docs = patient_documents.tail(3)  # Last 3 documents
                            document_context += "**RECENT PATIENT DOCUMENTS:**\n"
                            for _, doc in recent_docs.iterrows():
                                document_context += f"- {doc['document_name']} ({doc['document_type']}): {doc['notes'][:100]}...\n"

                        enhanced_system_prompt = f"""
You are an expert clinical AI assistant with specialized knowledge in diagnostics, treatment planning, and clinical decision support. You are assisting with patient care for {patient_info['name']}.

COMPREHENSIVE PATIENT CONTEXT:
{patient_context}

RECENT CLINICAL ENCOUNTERS:
{encounters_context}

RECENT DOCUMENTS & TEST RESULTS:
{document_context}

CLINICAL GUIDELINES:
1. **Diagnostic Excellence**: Consider differential diagnoses systematically, from common to rare conditions
2. **Safety First**: Always identify red flag symptoms and conditions requiring urgent attention
3. **Evidence-Based**: Provide clinical reasoning based on current medical guidelines and evidence
4. **Context-Aware**: Consider patient age, gender, comorbidities, and medical history
5. **Risk Assessment**: Evaluate potential risks, benefits, and contraindications for recommendations

RESPONSE REQUIREMENTS:
- Provide specific, actionable clinical insights rather than general advice
- When discussing diagnoses, explain the reasoning and key diagnostic criteria
- Highlight any abnormal values or critical findings that need attention
- Suggest specific follow-up tests, referrals, or monitoring parameters
- Consider medication interactions, allergies, and contraindications
- Provide differential diagnoses with likelihood ranking when appropriate
- Include evidence levels for recommendations where applicable

SAFETY PROTOCOLS:
- Always include "Red Flag Warning" section for symptoms requiring immediate care
- Specify when emergency care is warranted
- Recommend specialist consultation when appropriate
- Consider drug-gene interactions and pharmacogenomics when relevant

PROFESSIONAL RESPONSIBILITY:
- Use clear, professional medical terminology while explaining complex concepts
- Provide references to clinical guidelines when possible
- Encourage shared decision-making with patients
- Maintain patient-centered approach in all recommendations

Remember: You are assisting a qualified healthcare professional. Provide insights that enhance their clinical judgment while respecting their ultimate authority in patient care decisions.
                        """

                        try:
                            # Prepare full conversation history for context
                            conversation_history = [
                                {"role": "system", "content": enhanced_system_prompt}
                            ]

                            # Add recent messages for context (last 10 messages)
                            for msg in st.session_state[chat_key][-10:]:
                                conversation_history.append({
                                    "role": msg["role"],
                                    "content": msg["content"]
                                })

                            # Use OpenAI Responses API with full conversation context
                            response = client.responses.create(
                                model="gpt-5-nano-2025-08-07",
                                input=conversation_history,
                                store=True,  # Enable stateful context for better continuity
                            )

                            ai_response = response.output_text

                            st.markdown(ai_response)

                            # Save to session and database
                            st.session_state[chat_key].append({"role": "assistant", "content": ai_response})
                            add_ai_conversation_entry(patient_id, "assistant", ai_response)

                            log_audit_event(
                                st.session_state.current_user['username'],
                                "ai_chat_interaction",
                                f"AI chat with patient {patient_id}",
                                patient_id
                            )

                        except Exception as e:
                            st.error(f"AI Assistant error: {e}")
                            st.info("Please check your OpenAI API configuration and try again.")

            # Show saved documents dialog if requested
            if st.session_state.get('show_saved_documents', False):
                st.markdown("---")
                display_saved_documents_for_chat(patient_id)

        with tab2:
            st.subheader("📋 Document Analysis")
            st.write("Upload medical documents for AI analysis and insights.")

            # Multi-document upload section
            st.markdown("### 📁 Upload Documents")
            st.info("💡 **Tip**: You can upload multiple documents at once (e.g., lab results + radiologist report + clinical notes)")

            uploaded_files = st.file_uploader(
                "Upload Medical Documents",
                type=["pdf", "txt", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                help="Upload lab results, imaging reports, clinician notes, or other medical documents"
            )

            # Initialize session state for processed documents
            if 'processed_documents' not in st.session_state:
                st.session_state.processed_documents = []
            if 'document_session_id' not in st.session_state:
                st.session_state.document_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if uploaded_files:
                # Process each uploaded file
                processed_docs = []
                for uploaded_file in uploaded_files:
                    try:
                        with st.spinner(f"📄 Processing {uploaded_file.name}..."):
                            result = process_document(uploaded_file)

                        if result[0] is not None:
                            if len(result) == 4:  # Image file
                                file_content, file_metadata, doc_type, img_base64 = result
                            else:  # Text or PDF file
                                file_content, file_metadata, doc_type = result
                                img_base64 = None

                            # Add to processed documents
                            processed_docs.append({
                                'file': uploaded_file,
                                'content': file_content,
                                'metadata': file_metadata,
                                'type': doc_type,
                                'base64': img_base64,
                                'session_id': st.session_state.document_session_id
                            })

                    except Exception as e:
                        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")

                if processed_docs:
                    st.session_state.processed_documents.extend(processed_docs)
                    st.success(f"✅ Successfully processed {len(processed_docs)} document(s)!")

            # Display processed documents
            if st.session_state.processed_documents:
                st.markdown("### 📋 Processed Documents")

                # Document selection for analysis
                doc_names = [f"{doc['metadata']['name']} ({doc['type'].upper()})"
                           for doc in st.session_state.processed_documents]

                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.subheader("Current Session Documents")
                with col2:
                    if st.button("🗑️ Clear All", type="secondary"):
                        st.session_state.processed_documents = []
                        st.rerun()
                with col3:
                    if st.button("📥 Load Saved", type="secondary"):
                        st.session_state.show_saved_documents = True

                # Display each document with options
                for i, doc in enumerate(st.session_state.processed_documents):
                    with st.expander(f"📄 {doc['metadata']['name']} ({doc['type'].upper()})", expanded=(i == len(st.session_state.processed_documents) - 1)):
                        # Document metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Type", doc['type'].upper())
                            # Use file_size for images, size for other document types
                            file_size = doc['metadata'].get('file_size', doc['metadata'].get('size', 0))
                            if isinstance(file_size, (int, float)):
                                st.metric("Size", f"{file_size / 1024:.1f} KB")
                            else:
                                st.metric("Size", "N/A")
                        with col2:
                            if doc['type'] == "pdf" and 'pages' in doc['metadata']:
                                st.metric("Pages", doc['metadata']['pages'])
                            if doc['type'] == "image":
                                st.metric("Dimensions", f"{doc['metadata'].get('width', 'N/A')}x{doc['metadata'].get('height', 'N/A')}")
                        with col3:
                            st.checkbox("Include in Analysis", key=f"include_doc_{i}", value=True)

                        # Preview content
                        if doc['type'] in ["text", "pdf"] and doc['content'].strip():
                            preview_length = 1000
                            preview_content = doc['content'][:preview_length]
                            st.text_area(f"Preview:", value=preview_content, height=150, disabled=True)
                            if len(doc['content']) > preview_length:
                                st.caption(f"Showing first {preview_length} of {len(doc['content'])} characters")
                        elif doc['type'] == "image":
                            st.image(doc['file'], caption=f"📷 {doc['metadata']['name']}", use_column_width=True)

                # Analysis section
                st.markdown("---")
                analysis_col1, analysis_col2 = st.columns([2, 1])

                with analysis_col1:
                    st.subheader("🔍 AI Analysis Options")
                    analysis_type = st.selectbox(
                        "Select Analysis Type:",
                        ["Comprehensive Analysis", "Quick Summary", "Diagnostic Focus", "Risk Assessment", "Treatment Recommendations"]
                    )

                with analysis_col2:
                    st.subheader("⚡ Actions")
                    if st.button("🚀 Analyze Selected Documents", type="primary", use_container_width=True):
                        selected_docs = [doc for i, doc in enumerate(st.session_state.processed_documents)
                                       if st.session_state.get(f"include_doc_{i}", True)]
                        if selected_docs:
                            perform_multi_document_analysis(patient_id, patient_info, selected_docs, analysis_type)
                        else:
                            st.warning("Please select at least one document to analyze.")

                    if st.button("💾 Save All to Patient Record", use_container_width=True):
                        save_multiple_documents_to_record(patient_id, st.session_state.processed_documents)

            # Show saved documents section
            if st.session_state.get('show_saved_documents', False):
                display_saved_documents_for_chat(patient_id)

        with tab3:
            st.subheader("🔍 Differential Diagnosis Helper")

            with st.form("ddx_form"):
                symptoms = st.text_area(
                    "Patient Symptoms & Findings",
                    height=150,
                    placeholder="Describe the patient's symptoms, physical exam findings, lab results..."
                )

                duration = st.text_input("Duration of Symptoms")
                key_findings = st.text_area("Key Positive Findings")
                negative_findings = st.text_area("Key Negative Findings")

                if st.form_submit_button("🔍 Generate Differential Diagnosis"):
                    if symptoms:
                        with st.spinner("AI is generating differential diagnosis..."):
                            try:
                                ddx_prompt = f"""
Generate a differential diagnosis for this patient:

PATIENT: {patient_info['name']}, {datetime.now().year - patient_info['dob'].year}y, {patient_info['gender']}

SYMPTOMS: {symptoms}
DURATION: {duration}

KEY POSITIVE FINDINGS:
{key_findings}

KEY NEGATIVE FINDINGS:
{negative_findings}

Provide:
1. Most likely diagnoses (with reasoning)
2. Important can't-miss diagnoses to rule out
3. Recommended diagnostic workup
4. Red flag symptoms requiring immediate attention
                                """

                                # Use OpenAI Responses API for differential diagnosis
                                messages = [
                                    {
                                        "role": "system",
                                        "content": "You are an expert clinical diagnostician providing differential diagnosis analysis. Always prioritize patient safety and consider urgent conditions first."
                                    },
                                    {
                                        "role": "user",
                                        "content": ddx_prompt
                                    }
                                ]

                                response = client.responses.create(
                                    model="gpt-5-nano-2025-08-07",
                                    input=messages,
                                    store=True,
                                    temperature=0.2
                                )

                                ddx = response.output_text
                                st.markdown("### 🩺 Differential Diagnosis")
                                st.markdown(ddx)

                                # Save the interaction
                                add_ai_log(patient_id, None, ddx_prompt, ddx, "differential_diagnosis")

                            except Exception as e:
                                st.error(f"Diagnosis generation failed: {e}")

def show_analytics():
    """Comprehensive analytics dashboard."""
    st.header("📊 Practice Analytics Dashboard")

    # Key performance indicators
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        modern_metric_card("Total Patients", f"{len(get_patients())}", "+12% this month", "👥", "blue")
    with col2:
        modern_metric_card("Monthly Visits", "247", "+8% vs last month", "📅", "green")
    with col3:
        modern_metric_card("Active Prescriptions", "189", "23 pending renewal", "💊", "purple")
    with col4:
        modern_metric_card("Lab Tests", "1,423", "97% completed", "🧪", "orange")

    st.markdown("---")

    # Analytics tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Practice Overview", "💊 Medication Analytics", "📅 Appointment Analytics", "👥 Patient Demographics"])

    with tab1:
        st.subheader("📈 Practice Performance Overview")

        # Patient demographics
        col1, col2 = st.columns(2)

        with col1:
            age_dist = get_patient_age_distribution()
            if not age_dist.empty:
                fig = px.bar(age_dist, x='age_group', y='count', title="Patient Age Distribution")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            encounter_counts = get_encounter_counts_by_type()
            if not encounter_counts.empty:
                fig = px.pie(encounter_counts, values='count', names='type', title="Visit Types Distribution")
                st.plotly_chart(fig, use_container_width=True)

        # Recent activity trend
        st.subheader("📊 Activity Trends")
        recent_activity = get_recent_patient_activity(30)

        if not recent_activity.empty:
            # Convert date to datetime and extract date
            recent_activity['date'] = pd.to_datetime(recent_activity['encounter_date']).dt.date
            daily_counts = recent_activity.groupby('date').size().reset_index(name='visits')

            fig = px.line(daily_counts, x='date', y='visits', title="Daily Patient Visits (Last 30 Days)")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("💊 Medication Analytics")

        prescription_analytics = get_prescription_analytics()

        if not prescription_analytics.empty:
            # Top prescribed medications
            fig = px.bar(
                prescription_analytics.head(10),
                x='prescription_count',
                y='medication_name',
                orientation='h',
                title="Top 10 Prescribed Medications"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Medication categories
            st.subheader("📋 Medication Categories")
            meds = get_medications()
            if not meds.empty and 'drug_class' in meds.columns:
                class_counts = meds['drug_class'].value_counts().head(10)
                fig = px.pie(values=class_counts.values, names=class_counts.index, title="Medication Classes")
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📅 Appointment Analytics")

        appointment_analytics = get_appointment_analytics()

        if not appointment_analytics.empty:
            # Appointment completion rates
            appointment_analytics['completion_rate'] = (
                appointment_analytics['completed_count'] / appointment_analytics['total_count'] * 100
            )

            fig = px.bar(
                appointment_analytics,
                x='appointment_type',
                y=['completed_count', 'cancelled_count', 'no_show_count'],
                title="Appointment Outcomes by Type",
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Show/no-show rates
            col1, col2 = st.columns(2)
            with col1:
                total_shown = appointment_analytics['completed_count'].sum()
                total_missed = appointment_analytics['cancelled_count'].sum() + appointment_analytics['no_show_count'].sum()

                show_rate = total_shown / (total_shown + total_missed) * 100 if (total_shown + total_missed) > 0 else 0

                modern_metric_card(
                    "Show Rate",
                    f"{show_rate:.1f}%",
                    f"{total_shown} shown, {total_missed} missed",
                    "✅",
                    "green"
                )

            with col2:
                # Average appointment duration
                st.markdown("**Average Appointment Duration**")
                st.markdown("### 28 minutes")
                st.markdown("Across all appointment types")

    with tab4:
        st.subheader("👥 Patient Demographics")

        patients = get_patients()

        if not patients.empty:
            col1, col2 = st.columns(2)

            with col1:
                # Gender distribution
                gender_counts = patients['gender'].value_counts()
                fig = px.pie(values=gender_counts.values, names=gender_counts.index, title="Gender Distribution")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # New patients over time
                if 'created_at' in patients.columns:
                    patients['created_date'] = pd.to_datetime(patients['created_at']).dt.date
                    new_patients_by_month = patients.groupby('created_date').size().reset_index(name='new_patients')

                    if not new_patients_by_month.empty:
                        fig = px.line(new_patients_by_month, x='created_date', y='new_patients',
                                     title="New Patient Registrations")
                        st.plotly_chart(fig, use_container_width=True)

def show_settings():
    """Settings and configuration."""
    st.header("⚙️ Settings & Configuration")

    tab1, tab2, tab3 = st.tabs(["👤 User Settings", "🔧 System Settings", "📊 Audit Logs"])

    with tab1:
        st.subheader("👤 User Profile")

        current_user = get_current_user()

        st.markdown(f"""
        <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px;">
            <strong>Username:</strong> {current_user['username']}<br>
            <strong>Role:</strong> {current_user.get('role', 'staff').title()}<br>
            <strong>Name:</strong> {current_user.get('name', 'N/A')}<br>
            <strong>Email:</strong> {current_user.get('email', 'N/A')}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Preferences")
        theme = st.selectbox(
            "Theme Preference",
            ["light", "dark"],
            index=0 if st.session_state.get("theme") == "light" else 1
        )

        if st.button("Save Preferences"):
            st.session_state.theme = theme
            st.success("Preferences saved!")
            st.rerun()

    with tab2:
        st.subheader("🔧 System Configuration")

        st.markdown("### Database Information")
        st.info("Database: DuckDB (Embedded)")
        st.info("Location: clinical_logs.duckdb")

        st.markdown("### AI Configuration")
        if openai_api_key:
            st.success("✅ OpenAI API configured")
        else:
            st.error("❌ OpenAI API not configured")

        st.markdown("### System Maintenance")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Refresh All Data"):
                st.rerun()

        with col2:
            if st.button("🗑️ Clear Cache"):
                st.cache_data.clear()
                st.success("Cache cleared!")

    with tab3:
        st.subheader("📊 Audit Logs")

        logs = get_audit_logs(50)

        if not logs.empty:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                action_filter = st.selectbox(
                    "Filter by Action",
                    ["All"] + logs['action'].unique().tolist()
                )
            with col2:
                user_filter = st.selectbox(
                    "Filter by User",
                    ["All"] + logs['user_id'].unique().tolist()
                )

            # Apply filters
            filtered_logs = logs.copy()
            if action_filter != "All":
                filtered_logs = filtered_logs[filtered_logs['action'] == action_filter]
            if user_filter != "All":
                filtered_logs = filtered_logs[filtered_logs['user_id'] == user_filter]

            # Display logs
            for log in filtered_logs.itertuples():
                st.markdown(f"""
                <div style="padding: 0.75rem; background: #f8f9fa; border-radius: 8px; margin-bottom: 0.5rem;">
                    <small>{log.timestamp}</small><br>
                    <strong>{log.user_id}</strong> - {log.action}<br>
                    {f"<small>{log.details}</small>" if log.details else ""}
                    {f"<br><small>Patient ID: {log.patient_id}</small>" if log.patient_id else ""}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No audit logs found.")

# Run the main application
if __name__ == "__main__":
    main()
