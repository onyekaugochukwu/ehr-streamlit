import duckdb
from datetime import datetime
import pandas as pd # Import pandas for DataFrame operations

DB_FILE = "clinical_logs.duckdb"

def init_db():
    """
    Initializes the DuckDB database and creates all necessary tables
    (patients, encounters, documents, vitals, ai_logs) with sequences
    for auto-incrementing primary keys.
    """
    con = duckdb.connect(DB_FILE)

    # Create sequences for each table's primary key.
    # These sequences will generate unique, sequential IDs for each new record.
    con.execute("CREATE SEQUENCE IF NOT EXISTS patients_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS encounters_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS documents_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS vitals_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS ai_logs_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS ai_conversations_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS medications_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS prescriptions_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS appointments_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS lab_results_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS allergies_id_seq START 1;")
    con.execute("CREATE SEQUENCE IF NOT EXISTS immunizations_id_seq START 1;")

    # Patients table: Stores patient demographic information.
    con.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY DEFAULT nextval('patients_id_seq'), -- Auto-incrementing ID
            name VARCHAR,
            dob DATE,
            gender VARCHAR,
            contact VARCHAR,
            address VARCHAR,
            emergency_contact VARCHAR,
            blood_type VARCHAR,
            marital_status VARCHAR,
            employment VARCHAR,
            insurance_provider VARCHAR,
            insurance_policy_number VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Encounters table: Stores details of patient visits/interactions.
    # Added follow_up_of_encounter_id for linking follow-up encounters to original ones.
    con.execute("""
        CREATE TABLE IF NOT EXISTS encounters (
            id INTEGER PRIMARY KEY DEFAULT nextval('encounters_id_seq'), -- Auto-incrementing ID
            patient_id INTEGER,
            date DATE, -- Changed to DATE for consistency with st.date_input
            type VARCHAR, -- e.g., 'Consultation', 'Follow-up'
            notes VARCHAR,
            doctor VARCHAR,
            follow_up_of_encounter_id INTEGER, -- New column: ID of the encounter this is a follow-up to
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(follow_up_of_encounter_id) REFERENCES encounters(id) -- Self-referencing foreign key
        )
    """)

    # Documents table: Stores metadata about uploaded patient documents (scans, reports).
    con.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY DEFAULT nextval('documents_id_seq'), -- Auto-incrementing ID
            patient_id INTEGER,
            encounter_id INTEGER,
            type VARCHAR, -- e.g., 'PDF', 'TXT', 'JPEG'
            file_path VARCHAR, -- Path to the stored file
            text_content VARCHAR, -- Extracted text content from the document
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of upload
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(encounter_id) REFERENCES encounters(id)
        )
    """)

    # Vitals table: Stores patient vital signs over time.
    con.execute("""
        CREATE TABLE IF NOT EXISTS vitals (
            id INTEGER PRIMARY KEY DEFAULT nextval('vitals_id_seq'), -- Auto-incrementing ID
            patient_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of vital measurement
            heart_rate INTEGER,
            bp VARCHAR, -- Blood pressure (e.g., "120/80")
            temp FLOAT, -- Temperature
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # AI logs table: Stores records of AI interactions (e.g., suggestions, prompts).
    con.execute("""
        CREATE TABLE IF NOT EXISTS ai_logs (
            id INTEGER PRIMARY KEY DEFAULT nextval('ai_logs_id_seq'), -- Auto-incrementing ID
            patient_id INTEGER,
            encounter_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            prompt VARCHAR,
            ai_response VARCHAR,
            context_type VARCHAR, -- e.g., 'document_analysis', 'triage_chat'
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(encounter_id) REFERENCES encounters(id)
        )
    """)

    # AI Conversations table: Stores detailed chat history for AI triage/consultation.
    # This is separate from ai_logs to store individual chat turns for a continuous conversation.
    con.execute("""
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id INTEGER PRIMARY KEY DEFAULT nextval('ai_conversations_id_seq'),
            patient_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role VARCHAR, -- 'user' or 'assistant'
            content VARCHAR,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # Medications table: Stores medication information and interaction data
    con.execute("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY DEFAULT nextval('medications_id_seq'),
            name VARCHAR NOT NULL,
            generic_name VARCHAR,
            drug_class VARCHAR,
            description VARCHAR,
            contraindications VARCHAR,
            side_effects VARCHAR,
            interactions VARCHAR,
            dosage_form VARCHAR, -- tablet, capsule, liquid, etc.
            strength VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Prescriptions table: Links patients to medications with dosing instructions
    con.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY DEFAULT nextval('prescriptions_id_seq'),
            patient_id INTEGER,
            medication_id INTEGER,
            encounter_id INTEGER,
            dosage VARCHAR,
            frequency VARCHAR,
            route VARCHAR, -- oral, IV, IM, etc.
            start_date DATE,
            end_date DATE,
            prescribed_by VARCHAR,
            status VARCHAR, -- active, discontinued, completed
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(medication_id) REFERENCES medications(id),
            FOREIGN KEY(encounter_id) REFERENCES encounters(id)
        )
    """)

    # Appointments table: Manages patient appointments and scheduling
    con.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY DEFAULT nextval('appointments_id_seq'),
            patient_id INTEGER,
            provider_id INTEGER, -- Could reference users table in future
            appointment_type VARCHAR, -- consultation, follow-up, procedure, etc.
            appointment_date TIMESTAMP,
            duration INTEGER, -- in minutes
            status VARCHAR, -- scheduled, completed, cancelled, no-show
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # Lab Results table: Stores laboratory test results
    con.execute("""
        CREATE TABLE IF NOT EXISTS lab_results (
            id INTEGER PRIMARY KEY DEFAULT nextval('lab_results_id_seq'),
            patient_id INTEGER,
            encounter_id INTEGER,
            test_name VARCHAR,
            test_category VARCHAR, -- CBC, Chemistry, Hematology, etc.
            result_value VARCHAR,
            reference_range VARCHAR,
            unit VARCHAR,
            status VARCHAR, -- normal, abnormal, critical
            performed_date DATE,
            reported_date TIMESTAMP,
            performed_by VARCHAR,
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(encounter_id) REFERENCES encounters(id)
        )
    """)

    # Allergies table: Stores patient allergy information
    con.execute("""
        CREATE TABLE IF NOT EXISTS allergies (
            id INTEGER PRIMARY KEY DEFAULT nextval('allergies_id_seq'),
            patient_id INTEGER,
            allergen VARCHAR, -- medication, food, environmental, etc.
            allergen_type VARCHAR,
            reaction VARCHAR,
            severity VARCHAR, -- mild, moderate, severe
            status VARCHAR, -- active, resolved
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    # Immunizations table: Stores patient immunization records
    con.execute("""
        CREATE TABLE IF NOT EXISTS immunizations (
            id INTEGER PRIMARY KEY DEFAULT nextval('immunizations_id_seq'),
            patient_id INTEGER,
            vaccine_name VARCHAR,
            vaccine_type VARCHAR,
            dose_number INTEGER,
            administered_date DATE,
            administered_by VARCHAR,
            next_due_date DATE,
            lot_number VARCHAR,
            site VARCHAR, -- injection site
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    con.close()

# --- Patient Management Functions ---
def add_patient(name, dob, gender, contact, address):
    """Adds a new patient record to the database."""
    con = duckdb.connect(DB_FILE)
    # ID is auto-generated by the sequence, so it's omitted from the INSERT statement.
    con.execute(
        "INSERT INTO patients (name, dob, gender, contact, address) VALUES (?, ?, ?, ?, ?)",
        [name, dob, gender, contact, address]
    )
    con.close()

def get_patients():
    """Retrieves all patient records, ordered by name."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM patients ORDER BY name").df()
    con.close()
    return df

def get_patient_by_id(patient_id):
    """Retrieves a single patient record by their ID."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM patients WHERE id = ?", [patient_id]).df()
    con.close()
    return df.iloc[0] if not df.empty else None

# --- Encounter Management Functions ---
def add_encounter(patient_id, date, type_, notes, doctor, follow_up_of_encounter_id=None):
    """
    Adds a new encounter record for a patient.
    Can link to a previous encounter via follow_up_of_encounter_id.
    """
    con = duckdb.connect(DB_FILE)
    con.execute(
        "INSERT INTO encounters (patient_id, date, type, notes, doctor, follow_up_of_encounter_id) VALUES (?, ?, ?, ?, ?, ?)",
        [patient_id, date, type_, notes, doctor, follow_up_of_encounter_id]
    )
    con.close()

def get_encounters(patient_id):
    """
    Retrieves all encounters for a specific patient, ordered by date (descending).
    Includes details of the encounter it's following up on (if applicable).
    """
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT
            e1.id,
            e1.patient_id,
            e1.date,
            e1.type,
            e1.notes,
            e1.doctor,
            e1.follow_up_of_encounter_id,
            e2.date AS followed_up_date,
            e2.notes AS followed_up_notes,
            e2.type AS followed_up_type
        FROM encounters e1
        LEFT JOIN encounters e2 ON e1.follow_up_of_encounter_id = e2.id
        WHERE e1.patient_id = ?
        ORDER BY e1.date DESC
    """, [patient_id]).df()
    con.close()
    return df

# --- Document Management Functions ---
def add_document(patient_id, encounter_id, type_, file_path, text_content):
    """Adds a new document record."""
    con = duckdb.connect(DB_FILE)
    con.execute(
        "INSERT INTO documents (patient_id, encounter_id, type, file_path, text_content) VALUES (?, ?, ?, ?, ?)",
        [patient_id, encounter_id, type_, file_path, text_content]
    )
    con.close()

def get_documents(patient_id):
    """Retrieves all documents for a specific patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM documents WHERE patient_id = ? ORDER BY upload_time DESC", [patient_id]).df()
    con.close()
    return df

# --- Vitals Management Functions (Placeholder - implement add_vitals, get_vitals if needed) ---
def add_vitals(patient_id, heart_rate, bp, temp):
    """Adds new vital signs for a patient."""
    con = duckdb.connect(DB_FILE)
    con.execute(
        "INSERT INTO vitals (patient_id, heart_rate, bp, temp) VALUES (?, ?, ?, ?)",
        [patient_id, heart_rate, bp, temp]
    )
    con.close()

def get_vitals(patient_id):
    """Retrieves vital signs for a specific patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM vitals WHERE patient_id = ? ORDER BY timestamp DESC", [patient_id]).df()
    con.close()
    return df

# --- AI Log Functions ---
def add_ai_log(patient_id, encounter_id, prompt, ai_response, context_type):
    """
    Logs an AI interaction, linking it to a patient and optionally an encounter.
    """
    con = duckdb.connect(DB_FILE)
    con.execute(
        "INSERT INTO ai_logs (patient_id, encounter_id, timestamp, prompt, ai_response, context_type) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)",
        [patient_id, encounter_id, prompt, ai_response, context_type]
    )
    con.close()

def get_ai_logs(patient_id):
    """Retrieves all AI logs for a specific patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM ai_logs WHERE patient_id = ? ORDER BY timestamp DESC", [patient_id]).df()
    con.close()
    return df

# --- AI Conversation Functions ---
def add_ai_conversation_entry(patient_id, role, content):
    """Adds a single turn to the AI conversation history for a patient."""
    con = duckdb.connect(DB_FILE)
    con.execute(
        "INSERT INTO ai_conversations (patient_id, timestamp, role, content) VALUES (?, CURRENT_TIMESTAMP, ?, ?)",
        [patient_id, role, content]
    )
    con.close()

def get_ai_conversation_history(patient_id):
    """Retrieves the full AI conversation history for a specific patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT role, content FROM ai_conversations WHERE patient_id = ? ORDER BY timestamp ASC", [patient_id]).df()
    con.close()
    # Convert DataFrame to list of dictionaries for Streamlit chat_history
    return df.to_dict('records') if not df.empty else []

# --- Analytics Functions ---
def get_encounter_counts_by_type():
    """Returns a DataFrame with the count of each encounter type."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT type, COUNT(*) as count FROM encounters GROUP BY type ORDER BY count DESC").df()
    con.close()
    return df

def get_patient_age_distribution():
    """
    Calculates and returns the distribution of patient ages into groups.
    Note: Assumes DOB is a DATE type.
    """
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT
            CASE
                WHEN dob IS NULL THEN 'Unknown'
                -- The boolean result of the comparison needs to be cast to INTEGER (0 or 1)
                WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) < 18 THEN '0-17'
                WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) BETWEEN 18 AND 30 THEN '18-30'
                WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) BETWEEN 31 AND 50 THEN '31-50'
                WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) > 50 THEN '50+'
                ELSE 'Other'
            END AS age_group,
            COUNT(*) as count
        FROM patients
        GROUP BY age_group
        ORDER BY age_group;
    """).df()
    con.close()
    return df

def get_recent_patient_activity(limit=10):
    """Retrieves a DataFrame of recent patient encounters."""
    con = duckdb.connect(DB_FILE)
    df = con.execute(f"""
        SELECT
            p.name AS patient_name,
            e.date AS encounter_date,
            e.type AS encounter_type,
            e.notes AS encounter_notes,
            e.doctor AS doctor
        FROM encounters e
        JOIN patients p ON e.patient_id = p.id
        ORDER BY e.date DESC
        LIMIT {limit};
    """).df()
    con.close()
    return df

# --- Enhanced Patient Management Functions ---
def add_patient_enhanced(name, dob, gender, contact, address, emergency_contact=None,
                        blood_type=None, marital_status=None, employment=None,
                        insurance_provider=None, insurance_policy_number=None):
    """Adds a new enhanced patient record to the database."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO patients (name, dob, gender, contact, address, emergency_contact,
                             blood_type, marital_status, employment, insurance_provider,
                             insurance_policy_number, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, [name, dob, gender, contact, address, emergency_contact, blood_type,
          marital_status, employment, insurance_provider, insurance_policy_number])
    con.close()

def update_patient(patient_id, **kwargs):
    """Updates patient record with provided fields."""
    if not kwargs:
        return

    # Build dynamic update query
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [patient_id]

    con = duckdb.connect(DB_FILE)
    con.execute(f"""
        UPDATE patients SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, values)
    con.close()

# --- Medication Management Functions ---
def add_medication(name, generic_name=None, drug_class=None, description=None,
                   contraindications=None, side_effects=None, interactions=None,
                   dosage_form=None, strength=None):
    """Adds a new medication to the database."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO medications (name, generic_name, drug_class, description,
                                contraindications, side_effects, interactions,
                                dosage_form, strength)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [name, generic_name, drug_class, description, contraindications,
          side_effects, interactions, dosage_form, strength])
    con.close()

def get_medications():
    """Retrieves all medications."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("SELECT * FROM medications ORDER BY name").df()
    con.close()
    return df

def add_prescription(patient_id, medication_id, encounter_id, dosage, frequency,
                     route, start_date, end_date, prescribed_by, notes=None):
    """Adds a new prescription for a patient."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO prescriptions (patient_id, medication_id, encounter_id, dosage,
                                   frequency, route, start_date, end_date,
                                   prescribed_by, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
    """, [patient_id, medication_id, encounter_id, dosage, frequency, route,
          start_date, end_date, prescribed_by, notes])
    con.close()

def get_prescriptions(patient_id, status=None):
    """Retrieves prescriptions for a patient."""
    con = duckdb.connect(DB_FILE)
    if status:
        df = con.execute("""
            SELECT p.*, m.name as medication_name, m.generic_name
            FROM prescriptions p
            JOIN medications m ON p.medication_id = m.id
            WHERE p.patient_id = ? AND p.status = ?
            ORDER BY p.start_date DESC
        """, [patient_id, status]).df()
    else:
        df = con.execute("""
            SELECT p.*, m.name as medication_name, m.generic_name
            FROM prescriptions p
            JOIN medications m ON p.medication_id = m.id
            WHERE p.patient_id = ?
            ORDER BY p.start_date DESC
        """, [patient_id]).df()
    con.close()
    return df

def check_medication_interactions(medication_ids):
    """Checks for potential interactions between medications."""
    con = duckdb.connect(DB_FILE)
    placeholders = ",".join(["?" for _ in medication_ids])
    df = con.execute(f"""
        SELECT name, interactions FROM medications
        WHERE id IN ({placeholders})
    """, medication_ids).df()
    con.close()
    return df

# --- Appointment Management Functions ---
def add_appointment(patient_id, provider_id, appointment_type, appointment_date,
                    duration, notes=None):
    """Adds a new appointment."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO appointments (patient_id, provider_id, appointment_type,
                                 appointment_date, duration, status, notes)
        VALUES (?, ?, ?, ?, ?, 'scheduled', ?)
    """, [patient_id, provider_id, appointment_type, appointment_date,
          duration, notes])
    con.close()

def get_appointments(patient_id=None, provider_id=None, status=None):
    """Retrieves appointments with optional filters."""
    con = duckdb.connect(DB_FILE)
    query = """
        SELECT a.*, p.name as patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE 1=1
    """
    params = []

    if patient_id:
        query += " AND a.patient_id = ?"
        params.append(patient_id)

    if provider_id:
        query += " AND a.provider_id = ?"
        params.append(provider_id)

    if status:
        query += " AND a.status = ?"
        params.append(status)

    query += " ORDER BY a.appointment_date ASC"

    df = con.execute(query, params).df()
    con.close()
    return df

def update_appointment_status(appointment_id, status):
    """Updates appointment status."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        UPDATE appointments SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, [status, appointment_id])
    con.close()

# --- Lab Results Functions ---
def add_lab_result(patient_id, encounter_id, test_name, test_category,
                   result_value, reference_range=None, unit=None, status=None,
                   performed_date=None, performed_by=None, notes=None):
    """Adds a new lab result."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO lab_results (patient_id, encounter_id, test_name, test_category,
                                result_value, reference_range, unit, status,
                                performed_date, performed_by, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [patient_id, encounter_id, test_name, test_category, result_value,
          reference_range, unit, status or 'normal', performed_date or datetime.now().date(),
          performed_by, notes])
    con.close()

def get_lab_results(patient_id, test_category=None):
    """Retrieves lab results for a patient."""
    con = duckdb.connect(DB_FILE)
    if test_category:
        df = con.execute("""
            SELECT * FROM lab_results
            WHERE patient_id = ? AND test_category = ?
            ORDER BY performed_date DESC
        """, [patient_id, test_category]).df()
    else:
        df = con.execute("""
            SELECT * FROM lab_results
            WHERE patient_id = ?
            ORDER BY performed_date DESC
        """, [patient_id]).df()
    con.close()
    return df

# --- Allergy Management Functions ---
def add_allergy(patient_id, allergen, allergen_type, reaction, severity,
                notes=None):
    """Adds a new allergy record for a patient."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO allergies (patient_id, allergen, allergen_type, reaction,
                               severity, status, notes)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
    """, [patient_id, allergen, allergen_type, reaction, severity, notes])
    con.close()

def get_allergies(patient_id, status='active'):
    """Retrieves allergies for a patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT * FROM allergies
        WHERE patient_id = ? AND status = ?
        ORDER BY created_at DESC
    """, [patient_id, status]).df()
    con.close()
    return df

# --- Immunization Functions ---
def add_immunization(patient_id, vaccine_name, vaccine_type, dose_number,
                     administered_date, administered_by, next_due_date=None,
                     lot_number=None, site=None, notes=None):
    """Adds a new immunization record."""
    con = duckdb.connect(DB_FILE)
    con.execute("""
        INSERT INTO immunizations (patient_id, vaccine_name, vaccine_type,
                                   dose_number, administered_date, administered_by,
                                   next_due_date, lot_number, site, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [patient_id, vaccine_name, vaccine_type, dose_number, administered_date,
          administered_by, next_due_date, lot_number, site, notes])
    con.close()

def get_immunizations(patient_id):
    """Retrieves immunization records for a patient."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT * FROM immunizations
        WHERE patient_id = ?
        ORDER BY administered_date DESC
    """, [patient_id]).df()
    con.close()
    return df

# --- Analytics Functions ---
def get_prescription_analytics():
    """Get prescription analytics and trends."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT
            m.name as medication_name,
            COUNT(*) as prescription_count,
            AVG(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_rate
        FROM prescriptions p
        JOIN medications m ON p.medication_id = m.id
        GROUP BY m.name
        ORDER BY prescription_count DESC
        LIMIT 20
    """).df()
    con.close()
    return df

def get_appointment_analytics():
    """Get appointment statistics and trends."""
    con = duckdb.connect(DB_FILE)
    df = con.execute("""
        SELECT
            appointment_type,
            COUNT(*) as total_count,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count,
            SUM(CASE WHEN status = 'no-show' THEN 1 ELSE 0 END) as no_show_count
        FROM appointments
        GROUP BY appointment_type
        ORDER BY total_count DESC
    """).df()
    con.close()
    return df

# Example of how to initialize the database if this script is run directly
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with updated schema.")
    # You can add some test data here if you wish














# import duckdb
# from datetime import datetime
# import pandas as pd # Import pandas for DataFrame operations

# DB_FILE = "clinical_logs.duckdb"

# def init_db():
#     """
#     Initializes the DuckDB database and creates all necessary tables
#     (patients, encounters, documents, vitals, ai_logs) with sequences
#     for auto-incrementing primary keys.
#     """
#     con = duckdb.connect(DB_FILE)

#     # Create sequences for each table's primary key.
#     # These sequences will generate unique, sequential IDs for each new record.
#     con.execute("CREATE SEQUENCE IF NOT EXISTS patients_id_seq START 1;")
#     con.execute("CREATE SEQUENCE IF NOT EXISTS encounters_id_seq START 1;")
#     con.execute("CREATE SEQUENCE IF NOT EXISTS documents_id_seq START 1;")
#     con.execute("CREATE SEQUENCE IF NOT EXISTS vitals_id_seq START 1;")
#     con.execute("CREATE SEQUENCE IF NOT EXISTS ai_logs_id_seq START 1;")
#     con.execute("CREATE SEQUENCE IF NOT EXISTS ai_conversations_id_seq START 1;") # New sequence for AI chat history

#     # Patients table: Stores patient demographic information.
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS patients (
#             id INTEGER PRIMARY KEY DEFAULT nextval('patients_id_seq'), -- Auto-incrementing ID
#             name VARCHAR,
#             dob DATE,
#             gender VARCHAR,
#             contact VARCHAR,
#             address VARCHAR
#         )
#     """)

#     # Encounters table: Stores details of patient visits/interactions.
#     # Added follow_up_of_encounter_id for linking follow-up encounters to original ones.
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS encounters (
#             id INTEGER PRIMARY KEY DEFAULT nextval('encounters_id_seq'), -- Auto-incrementing ID
#             patient_id INTEGER,
#             date DATE, -- Changed to DATE for consistency with st.date_input
#             type VARCHAR, -- e.g., 'Consultation', 'Follow-up'
#             notes VARCHAR,
#             doctor VARCHAR,
#             follow_up_of_encounter_id INTEGER, -- New column: ID of the encounter this is a follow-up to
#             FOREIGN KEY(patient_id) REFERENCES patients(id),
#             FOREIGN KEY(follow_up_of_encounter_id) REFERENCES encounters(id) -- Self-referencing foreign key
#         )
#     """)

#     # Documents table: Stores metadata about uploaded patient documents (scans, reports).
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS documents (
#             id INTEGER PRIMARY KEY DEFAULT nextval('documents_id_seq'), -- Auto-incrementing ID
#             patient_id INTEGER,
#             encounter_id INTEGER,
#             type VARCHAR, -- e.g., 'PDF', 'TXT', 'JPEG'
#             file_path VARCHAR, -- Path to the stored file
#             text_content VARCHAR, -- Extracted text content from the document
#             upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of upload
#             FOREIGN KEY(patient_id) REFERENCES patients(id),
#             FOREIGN KEY(encounter_id) REFERENCES encounters(id)
#         )
#     """)

#     # Vitals table: Stores patient vital signs over time.
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS vitals (
#             id INTEGER PRIMARY KEY DEFAULT nextval('vitals_id_seq'), -- Auto-incrementing ID
#             patient_id INTEGER,
#             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of vital measurement
#             heart_rate INTEGER,
#             bp VARCHAR, -- Blood pressure (e.g., "120/80")
#             temp FLOAT, -- Temperature
#             FOREIGN KEY(patient_id) REFERENCES patients(id)
#         )
#     """)

#     # AI logs table: Stores records of AI interactions (e.g., suggestions, prompts).
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS ai_logs (
#             id INTEGER PRIMARY KEY DEFAULT nextval('ai_logs_id_seq'), -- Auto-incrementing ID
#             patient_id INTEGER,
#             encounter_id INTEGER,
#             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             prompt VARCHAR,
#             ai_response VARCHAR,
#             context_type VARCHAR, -- e.g., 'document_analysis', 'triage_chat'
#             FOREIGN KEY(patient_id) REFERENCES patients(id),
#             FOREIGN KEY(encounter_id) REFERENCES encounters(id)
#         )
#     """)

#     # AI Conversations table: Stores detailed chat history for AI triage/consultation.
#     # This is separate from ai_logs to store individual chat turns for a continuous conversation.
#     con.execute("""
#         CREATE TABLE IF NOT EXISTS ai_conversations (
#             id INTEGER PRIMARY KEY DEFAULT nextval('ai_conversations_id_seq'),
#             patient_id INTEGER,
#             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             role VARCHAR, -- 'user' or 'assistant'
#             content VARCHAR,
#             FOREIGN KEY(patient_id) REFERENCES patients(id)
#         )
#     """)

#     con.close()

# # --- Patient Management Functions ---
# def add_patient(name, dob, gender, contact, address):
#     """Adds a new patient record to the database."""
#     con = duckdb.connect(DB_FILE)
#     # ID is auto-generated by the sequence, so it's omitted from the INSERT statement.
#     con.execute(
#         "INSERT INTO patients (name, dob, gender, contact, address) VALUES (?, ?, ?, ?, ?)",
#         [name, dob, gender, contact, address]
#     )
#     con.close()

# def get_patients():
#     """Retrieves all patient records, ordered by name."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT * FROM patients ORDER BY name").df()
#     con.close()
#     return df

# def get_patient_by_id(patient_id):
#     """Retrieves a single patient record by their ID."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT * FROM patients WHERE id = ?", [patient_id]).df()
#     con.close()
#     return df.iloc[0] if not df.empty else None

# # --- Encounter Management Functions ---
# def add_encounter(patient_id, date, type_, notes, doctor, follow_up_of_encounter_id=None):
#     """
#     Adds a new encounter record for a patient.
#     Can link to a previous encounter via follow_up_of_encounter_id.
#     """
#     con = duckdb.connect(DB_FILE)
#     con.execute(
#         "INSERT INTO encounters (patient_id, date, type, notes, doctor, follow_up_of_encounter_id) VALUES (?, ?, ?, ?, ?, ?)",
#         [patient_id, date, type_, notes, doctor, follow_up_of_encounter_id]
#     )
#     con.close()

# def get_encounters(patient_id):
#     """
#     Retrieves all encounters for a specific patient, ordered by date (descending).
#     Includes details of the encounter it's following up on (if applicable).
#     """
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("""
#         SELECT
#             e1.id,
#             e1.patient_id,
#             e1.date,
#             e1.type,
#             e1.notes,
#             e1.doctor,
#             e1.follow_up_of_encounter_id,
#             e2.date AS followed_up_date,
#             e2.notes AS followed_up_notes,
#             e2.type AS followed_up_type
#         FROM encounters e1
#         LEFT JOIN encounters e2 ON e1.follow_up_of_encounter_id = e2.id
#         WHERE e1.patient_id = ?
#         ORDER BY e1.date DESC
#     """, [patient_id]).df()
#     con.close()
#     return df

# # --- Document Management Functions ---
# def add_document(patient_id, encounter_id, type_, file_path, text_content):
#     """Adds a new document record."""
#     con = duckdb.connect(DB_FILE)
#     con.execute(
#         "INSERT INTO documents (patient_id, encounter_id, type, file_path, text_content) VALUES (?, ?, ?, ?, ?)",
#         [patient_id, encounter_id, type_, file_path, text_content]
#     )
#     con.close()

# def get_documents(patient_id):
#     """Retrieves all documents for a specific patient."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT * FROM documents WHERE patient_id = ? ORDER BY upload_time DESC", [patient_id]).df()
#     con.close()
#     return df

# # --- Vitals Management Functions (Placeholder - implement add_vitals, get_vitals if needed) ---
# def add_vitals(patient_id, heart_rate, bp, temp):
#     """Adds new vital signs for a patient."""
#     con = duckdb.connect(DB_FILE)
#     con.execute(
#         "INSERT INTO vitals (patient_id, heart_rate, bp, temp) VALUES (?, ?, ?, ?)",
#         [patient_id, heart_rate, bp, temp]
#     )
#     con.close()

# def get_vitals(patient_id):
#     """Retrieves vital signs for a specific patient."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT * FROM vitals WHERE patient_id = ? ORDER BY timestamp DESC", [patient_id]).df()
#     con.close()
#     return df

# # --- AI Log Functions ---
# def add_ai_log(patient_id, encounter_id, prompt, ai_response, context_type):
#     """
#     Logs an AI interaction, linking it to a patient and optionally an encounter.
#     """
#     con = duckdb.connect(DB_FILE)
#     con.execute(
#         "INSERT INTO ai_logs (patient_id, encounter_id, timestamp, prompt, ai_response, context_type) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)",
#         [patient_id, encounter_id, prompt, ai_response, context_type]
#     )
#     con.close()

# def get_ai_logs(patient_id):
#     """Retrieves all AI logs for a specific patient."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT * FROM ai_logs WHERE patient_id = ? ORDER BY timestamp DESC", [patient_id]).df()
#     con.close()
#     return df

# # --- AI Conversation Functions ---
# def add_ai_conversation_entry(patient_id, role, content):
#     """Adds a single turn to the AI conversation history for a patient."""
#     con = duckdb.connect(DB_FILE)
#     con.execute(
#         "INSERT INTO ai_conversations (patient_id, timestamp, role, content) VALUES (?, CURRENT_TIMESTAMP, ?, ?)",
#         [patient_id, role, content]
#     )
#     con.close()

# def get_ai_conversation_history(patient_id):
#     """Retrieves the full AI conversation history for a specific patient."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT role, content FROM ai_conversations WHERE patient_id = ? ORDER BY timestamp ASC", [patient_id]).df()
#     con.close()
#     # Convert DataFrame to list of dictionaries for Streamlit chat_history
#     return df.to_dict('records') if not df.empty else []

# # --- Analytics Functions ---
# def get_encounter_counts_by_type():
#     """Returns a DataFrame with the count of each encounter type."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("SELECT type, COUNT(*) as count FROM encounters GROUP BY type ORDER BY count DESC").df()
#     con.close()
#     return df

# def get_patient_age_distribution():
#     """
#     Calculates and returns the distribution of patient ages into groups.
#     Note: Assumes DOB is a DATE type.
#     """
#     con = duckdb.connect(DB_FILE)
#     df = con.execute("""
#         SELECT
#             CASE
#                 WHEN dob IS NULL THEN 'Unknown'
#                 -- The boolean result of the comparison needs to be cast to INTEGER (0 or 1)
#                 WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) < 18 THEN '0-17'
#                 WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) BETWEEN 18 AND 30 THEN '18-30'
#                 WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) BETWEEN 31 AND 50 THEN '31-50'
#                 WHEN (CAST(STRFTIME(CURRENT_DATE, '%Y') AS INTEGER) - CAST(STRFTIME(dob, '%Y') AS INTEGER) - CAST((CAST(STRFTIME(CURRENT_DATE, '%m%d') AS INTEGER) < CAST(STRFTIME(dob, '%m%d') AS INTEGER)) AS INTEGER)) > 50 THEN '50+'
#                 ELSE 'Other'
#             END AS age_group,
#             COUNT(*) as count
#         FROM patients
#         GROUP BY age_group
#         ORDER BY age_group;
#     """).df()
#     con.close()
#     return df

# def get_recent_patient_activity(limit=10):
#     """Retrieves a DataFrame of recent patient encounters."""
#     con = duckdb.connect(DB_FILE)
#     df = con.execute(f"""
#         SELECT
#             p.name AS patient_name,
#             e.date AS encounter_date,
#             e.type AS encounter_type,
#             e.notes AS encounter_notes,
#             e.doctor AS doctor
#         FROM encounters e
#         JOIN patients p ON e.patient_id = p.id
#         ORDER BY e.date DESC
#         LIMIT {limit};
#     """).df()
#     con.close()
#     return df





