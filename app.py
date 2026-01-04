from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
from mysql.connector import Error

# Configure your MySQL connection here
DB_CONFIG = {
    "host": "localhost",        # e.g. "localhost"
    "user": "root",  # e.g. "root"
    "password": "",# e.g. "mypassword"
    "database": "clinic_db"     # DATABASE NAME
}

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main HTML page."""
    return send_from_directory(".", "index.html")


@app.route("/styles.css")
def styles():
    """Serve the CSS file."""
    return send_from_directory(".", "styles.css")


def get_db_connection():
    """Create and return a new MySQL connection using DB_CONFIG.

    In a small project like this we can open a connection per request
    and close it after we are done.
    """
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/api/patients", methods=["GET"])
def list_patients():
    """Return all patients as JSON."""
    conn = None
    cursor = None
    patients = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT patient_id, name, dob, gender, phone, address
            FROM Patient
            ORDER BY name
            """
        )
        patients = cursor.fetchall()
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify(patients)


@app.route("/api/patients", methods=["POST"])
def create_patient():
    """Create a new patient from JSON data.

    Expects JSON like:
    {
      "name": "John Doe",
      "dob": "1990-05-15",
      "gender": "M",
      "phone": "555-1234",
      "address": "123 Elm St"
    }
    """
    data = request.get_json(silent=True) or {}

    required_fields = ["name", "dob", "gender", "phone", "address"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Patient (name, dob, gender, phone, address)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                data["name"],
                data["dob"],
                data["gender"],
                data["phone"],
                data["address"],
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Patient created", "patient_id": new_id}), 201


@app.route("/api/patients/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):
    """Update an existing patient.

    Expects JSON with any of: name, dob, gender, phone, address.
    """
    data = request.get_json(silent=True) or {}

    allowed_fields = ["name", "dob", "gender", "phone", "address"]
    fields_to_update = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

    if not fields_to_update:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clause = ", ".join(f"{field} = %s" for field in fields_to_update.keys())
    values = list(fields_to_update.values())
    values.append(patient_id)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE Patient SET {set_clause} WHERE patient_id = %s", values)
        if cursor.rowcount == 0:
            return jsonify({"error": "Patient not found"}), 404
        conn.commit()
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Patient updated"})


@app.route("/api/patients/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):
    """Delete a patient by ID."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Delete related appointments first to satisfy foreign key constraints
        cursor.execute("DELETE FROM Appointment WHERE patient_id = %s", (patient_id,))
        cursor.execute("DELETE FROM Patient WHERE patient_id = %s", (patient_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Patient not found"}), 404
        conn.commit()
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Patient deleted"})


# ----------------------
# Doctor endpoints
# ----------------------

@app.route("/api/doctors", methods=["GET"])
def list_doctors():
    """Return all doctors as JSON."""
    conn = None
    cursor = None
    doctors = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT doctor_id, name, phone, email, specialization
            FROM Doctor
            ORDER BY name
            """
        )
        doctors = cursor.fetchall()
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify(doctors)


@app.route("/api/doctors", methods=["POST"])
def create_doctor():
    """Create a new doctor from JSON data."""
    data = request.get_json(silent=True) or {}

    required_fields = ["name", "phone", "email", "specialization"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing,
        }), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Doctor (name, phone, email, specialization)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["name"],
                data["phone"],
                data["email"],
                data["specialization"],
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Doctor created", "doctor_id": new_id}), 201


@app.route("/api/doctors/<int:doctor_id>", methods=["PUT"])
def update_doctor(doctor_id):
    """Update an existing doctor."""
    data = request.get_json(silent=True) or {}

    allowed_fields = ["name", "phone", "email", "specialization"]
    fields_to_update = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

    if not fields_to_update:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clause = ", ".join(f"{field} = %s" for field in fields_to_update.keys())
    values = list(fields_to_update.values())
    values.append(doctor_id)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE Doctor SET {set_clause} WHERE doctor_id = %s", values)
        if cursor.rowcount == 0:
            return jsonify({"error": "Doctor not found"}), 404
        conn.commit()
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Doctor updated"})


@app.route("/api/doctors/<int:doctor_id>", methods=["DELETE"])
def delete_doctor(doctor_id):
    """Delete a doctor by ID (and their appointments)."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Delete related appointments first to satisfy foreign key constraints
        cursor.execute("DELETE FROM Appointment WHERE doctor_id = %s", (doctor_id,))
        cursor.execute("DELETE FROM Doctor WHERE doctor_id = %s", (doctor_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Doctor not found"}), 404
        conn.commit()
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Doctor deleted"})


# ----------------------
# Appointment endpoints
# ----------------------

@app.route("/api/appointments", methods=["GET"])
def list_appointments():
    """Return all appointments with patient and doctor names."""
    conn = None
    cursor = None
    appts = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT a.appointment_id,
                   a.date,
                   a.time,
                   p.name AS patient_name,
                   d.name AS doctor_name
            FROM Appointment a
            JOIN Patient p ON a.patient_id = p.patient_id
            JOIN Doctor d ON a.doctor_id = d.doctor_id
            ORDER BY a.date, a.time
            """
        )
        appts = cursor.fetchall()
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify(appts)


@app.route("/api/appointments/today", methods=["GET"])
def list_todays_appointments():
    """Return today's appointments with patient and doctor names."""
    conn = None
    cursor = None
    appts = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT a.appointment_id,
                   a.date,
                   a.time,
                   p.name AS patient_name,
                   d.name AS doctor_name
            FROM Appointment a
            JOIN Patient p ON a.patient_id = p.patient_id
            JOIN Doctor d ON a.doctor_id = d.doctor_id
            WHERE a.date = CURDATE()
            ORDER BY a.date, a.time
            """
        )
        appts = cursor.fetchall()
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify(appts)


@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    """Create a new appointment from JSON data."""
    data = request.get_json(silent=True) or {}

    required_fields = ["patient_id", "doctor_id", "date", "time"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing,
        }), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Appointment (patient_id, doctor_id, date, time)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["patient_id"],
                data["doctor_id"],
                data["date"],
                data["time"],
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Appointment created", "appointment_id": new_id}), 201


@app.route("/api/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    """Delete an appointment by ID."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Appointment WHERE appointment_id = %s", (appointment_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Appointment not found"}), 404
        conn.commit()
    except Error as e:
        if conn is not None:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return jsonify({"message": "Appointment deleted"})


if __name__ == "__main__":
    # Enable debug during development only
    app.run(debug=True)
