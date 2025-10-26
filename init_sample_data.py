#!/usr/bin/env python3
"""
Sample Data Initialization Script for Enhanced EHR System
Populates the database with realistic sample data for demonstration purposes.
"""

import sys
import os
from datetime import datetime, timedelta
import random
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import (
    init_db, add_patient_enhanced, add_encounter, add_medication, add_prescription,
    add_appointment, add_lab_result, add_allergy, add_immunization
)

# Sample data
FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
               "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
               "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
               "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
              "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"]

MEDICATIONS = [
    ("Lisinopril", "Lisinopril", "ACE Inhibitor", "Used for hypertension and heart failure",
     "Angioedema, pregnancy", "Cough, dizziness, headache", "NSAIDs, potassium supplements",
     "Tablet", "10mg"),
    ("Metformin", "Metformin hydrochloride", "Biguanide", "First-line treatment for type 2 diabetes",
     "Severe renal impairment, metabolic acidosis", "GI upset, lactic acidosis (rare)", "Contrast dye",
     "Tablet", "500mg"),
    ("Amlodipine", "Amlodipine besylate", "Calcium Channel Blocker", "Treats hypertension and angina",
     "Severe aortic stenosis", "Edema, dizziness, flushing", "CYP3A4 inhibitors",
     "Tablet", "5mg"),
    ("Albuterol", "Albuterol sulfate", "Beta-2 Agonist", "Bronchodilator for asthma and COPD",
     "None significant", "Tremor, tachycardia, nervousness", "Beta blockers",
     "Inhaler", "90mcg"),
    ("Omeprazole", "Omeprazole", "Proton Pump Inhibitor", "Treats GERD and stomach ulcers",
     "None significant", "Headache, diarrhea, abdominal pain", "Clopidogrel",
     "Capsule", "20mg"),
    ("Atorvastatin", "Atorvastatin calcium", "Statin", "Lowers cholesterol and triglycerides",
     "Active liver disease", "Myopathy, liver enzyme elevation", "Grapefruit juice",
     "Tablet", "20mg"),
    ("Sertraline", "Sertraline hydrochloride", "SSRI", "Treats depression and anxiety disorders",
     "MAO inhibitors", "Insomnia, sexual dysfunction, nausea", "MAO inhibitors, NSAIDs",
     "Tablet", "50mg"),
    ("Levothyroxine", "Levothyroxine sodium", "Thyroid Hormone", "Treats hypothyroidism",
     "Untreated thyrotoxicosis", "Palpitations, insomnia, weight loss", "Calcium supplements, iron",
     "Tablet", "50mcg"),
    ("Gabapentin", "Gabapentin", "Anticonvulsant", "Treats neuropathic pain and seizures",
     "None significant", "Drowsiness, dizziness, ataxia", "Antacids",
     "Capsule", "300mg"),
    ("Hydrochlorothiazide", "HCTZ", "Thiazide Diuretic", "Treats hypertension and edema",
     "Anuria, sulfa allergy", "Hypokalemia, hyponatremia, hyperglycemia", "NSAIDs, digoxin",
     "Tablet", "25mg")
]

CONDITIONS = [
    "Hypertension", "Type 2 Diabetes", "Hyperlipidemia", "Asthma", "GERD",
    "Depression", "Anxiety", "Hypothyroidism", "Osteoarthritis", "Migraine",
    "Allergic Rhinitis", "COPD", "Coronary Artery Disease", "Heart Failure", "CKD"
]

ALLERGENS = [
    ("Penicillin", "Medication", "Rash, itching, anaphylaxis", "Severe"),
    ("Peanuts", "Food", "Anaphylaxis, hives, swelling", "Severe"),
    ("Shellfish", "Food", "Hives, abdominal pain, anaphylaxis", "Moderate"),
    ("Latex", "Environmental", "Contact dermatitis, anaphylaxis", "Severe"),
    ("Pollen", "Environmental", "Sneezing, itchy eyes, congestion", "Mild"),
    ("Dust Mites", "Environmental", "Sneezing, coughing, wheezing", "Mild"),
    ("Sulfa Drugs", "Medication", "Rash, fever, organ involvement", "Moderate"),
    ("Codeine", "Medication", "Nausea, constipation, respiratory depression", "Moderate"),
    ("Aspirin", "Medication", "Stomach bleeding, asthma exacerbation", "Moderate"),
    ("Eggs", "Food", "Hives, abdominal pain, anaphylaxis", "Mild")
]

VACCINES = [
    ("COVID-19", "COVID-19", "Pfizer-BioNTech"),
    ("Influenza", "Influenza", "Fluzone"),
    ("Tdap", "Tdap", "Adacel"),
    ("MMR", "MMR", "M-M-R II"),
    ("Hepatitis B", "Hepatitis B", "Engerix-B"),
    ("Pneumococcal", "Pneumococcal", "Prevnar 13"),
    ("Shingles", "Shingles", "Shingrix"),
    ("HPV", "HPV", "Gardasil 9")
]

def generate_random_date(start_date, end_date):
    """Generate a random date between start_date and end_date."""
    time_between = end_date - start_date
    days_between = time_between.days
    random_number_of_days = random.randrange(days_between)
    return start_date + timedelta(days=random_number_of_days)

def init_sample_data():
    """Initialize the database with sample data."""
    print("🏥 Initializing Enhanced EHR System with Sample Data...")

    # Initialize database
    init_db()

    # Add medications
    print("💊 Adding medications to library...")
    for med in MEDICATIONS:
        add_medication(*med)

    # Create sample patients
    print("👥 Creating sample patients...")
    patients_created = 0

    for i in range(25):  # Create 25 sample patients
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"

        # Generate random demographics
        birth_year = random.randint(1940, 2005)
        dob = datetime(birth_year, random.randint(1, 12), random.randint(1, 28))
        gender = random.choice(["Male", "Female", "Other"])

        # Contact info
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        email = f"{first_name.lower()}.{last_name.lower()}@email.com"

        # Address
        street_num = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "Pine Ln", "Maple Dr", "Cedar Blvd", "Elm Way"]
        street = random.choice(street_names)
        city = random.choice(["Springfield", "Franklin", "Georgetown", "Madison", "Washington"])
        state = random.choice(["IL", "OH", "KY", "WI", "VA"])
        zip_code = f"{random.randint(10000, 99999)}"
        address = f"{street_num} {street}, {city}, {state} {zip_code}"

        # Additional demographics
        blood_type = random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        marital_status = random.choice(["Single", "Married", "Divorced", "Widowed"])
        employment = random.choice(["Employed", "Self-employed", "Retired", "Student", "Unemployed"])

        # Insurance
        insurance_providers = ["Blue Cross Blue Shield", "Aetna", "UnitedHealth", "Cigna", "Humana"]
        insurance_provider = random.choice(insurance_providers)
        insurance_policy = f"{random.randint(100000000, 999999999)}"

        # Add patient
        add_patient_enhanced(
            name=name,
            dob=dob.date(),
            gender=gender,
            contact=phone,
            address=address,
            emergency_contact=f"{first_name} {last_name} Sr - {phone}",
            blood_type=blood_type,
            marital_status=marital_status,
            employment=employment,
            insurance_provider=insurance_provider,
            insurance_policy_number=insurance_policy
        )

        patients_created += 1
        print(f"  Created patient: {name} (ID: {patients_created})")

        # Add encounters for this patient
        num_encounters = random.randint(1, 5)
        for j in range(num_encounters):
            encounter_date = generate_random_date(dob + timedelta(days=365*18), datetime.now())
            encounter_type = random.choice(["Consultation", "Follow-up", "Emergency", "Procedure"])

            # Generate SOAP note
            chief_complaint = random.choice([
                "Annual checkup", "Chest pain", "Shortness of breath", "Abdominal pain",
                "Headache", "Joint pain", "Fever", "Cough", "Fatigue", "Dizziness"
            ])

            soap_note = f"""
CHIEF COMPLAINT: {chief_complaint}

SUBJECTIVE: Patient presents with {chief_complaint.lower()}. Reports {random.choice(['mild', 'moderate', 'severe'])} symptoms
for {random.randint(1, 14)} days. {random.choice(['No', 'Mild', 'Moderate'])} relief with over-the-counter medications.

OBJECTIVE: Vitals: BP {random.randint(110, 140)}/{random.randint(70, 90)}, HR {random.randint(60, 100)},
RR {random.randint(12, 20)}, Temp {random.randint(97, 99)}.{random.randint(0, 9)}°F.
{random.choice(['Clear lungs bilaterally', 'Decreased breath sounds LLL', 'Wheezing bilaterally'])}.
{random.choice(['Regular S1S2, no murmurs', 'Systolic murmur grade II/VI', 'Irregularly irregular rhythm'])}.

ASSESSMENT: {random.choice(CONDITIONS)}. {random.choice(['Well-controlled', 'Mildly symptomatic', 'Requires treatment optimization'])}.

PLAN: Continue current medications. {random.choice(['Lifestyle modifications advised', 'Start new medication', 'Schedule follow-up in 2 weeks', 'Order lab tests'])}.
            """.strip()

            doctor = random.choice(["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Jones"])

            add_encounter(
                patient_id=patients_created,
                date=encounter_date.date(),
                type_=encounter_type,
                notes=soap_note,
                doctor=doctor
            )

        # Add allergies for some patients
        if random.random() < 0.3:  # 30% of patients have allergies
            num_allergies = random.randint(1, 3)
            for k in range(num_allergies):
                allergen = random.choice(ALLERGENS)
                add_allergy(
                    patient_id=patients_created,
                    allergen=allergen[0],
                    allergen_type=allergen[1],
                    reaction=allergen[2],
                    severity=allergen[3]
                )

        # Add prescriptions for some patients
        if random.random() < 0.6:  # 60% of patients have prescriptions
            num_prescriptions = random.randint(1, 4)
            for k in range(num_prescriptions):
                medication_id = random.randint(1, len(MEDICATIONS))
                dosage_options = {
                    1: "10mg daily", 2: "500mg twice daily", 3: "5mg daily", 4: "2 puffs q4-6h PRN",
                    5: "20mg daily", 6: "20mg at bedtime", 7: "50mg daily", 8: "50mcg daily",
                    9: "300mg three times daily", 10: "25mg daily"
                }
                frequency_options = ["Once daily", "Twice daily", "Three times daily", "As needed", "At bedtime"]

                start_date = generate_random_date(dob + timedelta(days=365*18), datetime.now())
                end_date = start_date + timedelta(days=random.randint(30, 365))

                add_prescription(
                    patient_id=patients_created,
                    medication_id=medication_id,
                    encounter_id=None,
                    dosage=dosage_options.get(medication_id, "Take as directed"),
                    frequency=random.choice(frequency_options),
                    route="Oral",
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    prescribed_by=random.choice(["Dr. Smith", "Dr. Johnson", "Dr. Williams"])
                )

        # Add lab results for some patients
        if random.random() < 0.4:  # 40% of patients have lab results
            num_labs = random.randint(1, 3)
            for k in range(num_labs):
                test_categories = ["CBC", "Chemistry", "Lipid Panel", "HbA1c", "TSH"]
                test_names = {
                    "CBC": "Complete Blood Count",
                    "Chemistry": "Comprehensive Metabolic Panel",
                    "Lipid Panel": "Lipid Panel",
                    "HbA1c": "Hemoglobin A1c",
                    "TSH": "Thyroid Stimulating Hormone"
                }

                category = random.choice(test_categories)
                test_date = generate_random_date(dob + timedelta(days=365*18), datetime.now())

                # Generate realistic lab values
                if category == "CBC":
                    result_value = f"Hgb: {random.uniform(11.0, 16.0):.1f} g/dL, WBC: {random.uniform(4.0, 11.0):.1f} K/μL"
                    unit = "Various"
                    ref_range = "Hgb: 12.0-15.5 g/dL, WBC: 4.5-11.0 K/μL"
                elif category == "Chemistry":
                    result_value = f"Glucose: {random.randint(70, 120)} mg/dL, Creatinine: {random.uniform(0.6, 1.3):.2f} mg/dL"
                    unit = "Various"
                    ref_range = "Glucose: 70-100 mg/dL, Creatinine: 0.6-1.3 mg/dL"
                elif category == "Lipid Panel":
                    result_value = f"Total Cholesterol: {random.randint(150, 250)} mg/dL, LDL: {random.randint(70, 160)} mg/dL"
                    unit = "mg/dL"
                    ref_range = "Total <200, LDL <100"
                elif category == "HbA1c":
                    result_value = f"{random.uniform(5.0, 8.5):.1f}%"
                    unit = "%"
                    ref_range = "4.0-5.6%"
                else:  # TSH
                    result_value = f"{random.uniform(0.4, 5.5):.2f} mIU/L"
                    unit = "mIU/L"
                    ref_range = "0.4-4.0 mIU/L"

                status = random.choice(["normal", "abnormal", "critical"])

                add_lab_result(
                    patient_id=patients_created,
                    encounter_id=None,
                    test_name=test_names[category],
                    test_category=category,
                    result_value=result_value,
                    reference_range=ref_range,
                    unit=unit,
                    status=status,
                    performed_date=test_date.date(),
                    performed_by="Quest Diagnostics"
                )

        # Add immunizations for some patients
        if random.random() < 0.7:  # 70% of patients have immunizations
            num_vaccines = random.randint(1, 5)
            for k in range(num_vaccines):
                vaccine = random.choice(VACCINES)
                vaccine_date = generate_random_date(dob + timedelta(days=365), datetime.now())

                add_immunization(
                    patient_id=patients_created,
                    vaccine_name=vaccine[0],
                    vaccine_type=vaccine[1],
                    dose_number=random.randint(1, 3),
                    administered_date=vaccine_date.date(),
                    administered_by="Dr. Smith",
                    next_due_date=vaccine_date + timedelta(days=random.randint(365, 1825)) if random.random() < 0.5 else None,
                    lot_number=f"LOT{random.randint(1000000, 9999999)}",
                    site=random.choice(["Left Arm", "Right Arm"])
                )

    # Add appointments
    print("📅 Creating sample appointments...")
    for i in range(1, min(26, patients_created + 1)):  # For first 25 patients
        num_appointments = random.randint(1, 3)
        for j in range(num_appointments):
            apt_date = datetime.now() + timedelta(days=random.randint(-30, 30))
            apt_time = apt_date.replace(
                hour=random.choice([9, 10, 11, 14, 15, 16]),
                minute=random.choice([0, 15, 30, 45]),
                second=0
            )

            add_appointment(
                patient_id=i,
                provider_id=1,  # Dr. Smith
                appointment_type=random.choice(["Consultation", "Follow-up", "Procedure", "Vaccination"]),
                appointment_date=apt_time,
                duration=random.choice([15, 30, 45, 60]),
                notes=random.choice(["", "Annual checkup", "Follow-up required", "New patient"])
            )

    print(f"\n✅ Sample data initialization complete!")
    print(f"📊 Summary:")
    print(f"   • Patients created: {patients_created}")
    print(f"   • Medications in library: {len(MEDICATIONS)}")
    print(f"   • Sample appointments, prescriptions, labs, allergies, and immunizations added")
    print(f"\n🚀 You can now run the enhanced EHR application!")
    print(f"   Run: streamlit run app_enhanced.py")
    print(f"   Login with: admin / admin123")

if __name__ == "__main__":
    init_sample_data()