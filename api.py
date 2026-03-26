from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import mariadb
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import date, datetime
import os
import time

app = FastAPI(title="Contract Management System API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# DATABASE CONFIG
# ========================
DB_HOST = "192.168.100.85"
DB_NAME = "Contract Management System"
DB_USER = "root"
DB_PASSWORD = "P@ssword"

# ========================
# MODELS
# ========================

# Login Models (validate against `vendors`)
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

# Contracts Models
class ContractBase(BaseModel):
    contract_number: str
    title: str
    description: Optional[str] = None
    start_date: date
    vendor_id: int
    status: str  # Active, Expired, Terminated, Pending
    renewal_type: str  # Manual, Auto-Renew

class Contract(ContractBase):
    contract_id: int
    created_at: Optional[datetime] = None

class ContractUpdate(BaseModel):
    contract_number: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    vendor_id: Optional[int] = None
    status: Optional[str] = None
    renewal_type: Optional[str] = None

# Contract Documents Models
class ContractDocumentBase(BaseModel):
    contract_id: int
    file_path: str
    file_type: str

class ContractDocument(ContractDocumentBase):
    doc_id: int
    uploaded_at: Optional[datetime] = None

class ContractDocumentUpdate(BaseModel):
    contract_id: Optional[int] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None

# Notifications Models
class NotificationBase(BaseModel):
    contract_id: int
    remind_before_days: int
    notification_date: date
    is_sent: bool = False

class Notification(NotificationBase):
    notify_id: int
    last_sent_at: Optional[datetime] = None

class NotificationUpdate(BaseModel):
    contract_id: Optional[int] = None
    remind_before_days: Optional[int] = None
    notification_date: Optional[date] = None
    is_sent: Optional[bool] = None

# Vendors Models
class VendorBase(BaseModel):
    vendor_name: str
    contact_person: str
    email: str
    phone: str

class Vendor(VendorBase):
    vendor_id: int

class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

# ========================
# DB CONNECTION
# ========================
def get_connection():
    try:
        conn = mariadb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=3306,
            database=DB_NAME
        )
        return conn
    except mariadb.Error as e:
        print("❌ DB ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# AUTH / LOGIN
# ========================
@app.post("/user_login", response_model=LoginResponse)
def user_login(payload: LoginRequest):
    """
    Simple login for the mobile UI.
    Validates credentials against `vendors`:
    - username -> vendors.email
    - password -> vendors.phone
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT vendor_id FROM vendors WHERE email = %s AND phone = %s",
            (payload.username, payload.password),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        return {"success": True, "message": "Login successful"}
    finally:
        conn.close()

# ========================
# CONTRACTS ENDPOINTS
# ========================

@app.get("/contracts", response_model=list[Contract])
def get_all_contracts():
    """Get all contracts"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contracts")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/contracts/{contract_id}", response_model=Contract)
def get_contract_by_id(contract_id: int):
    """Get contract by ID"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Contract not found")

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/contracts", response_model=Contract)
def create_contract(contract: ContractBase):
    """Create a new contract"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO contracts
               (contract_number, title, description, start_date, vendor_id, status, renewal_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (contract.contract_number, contract.title, contract.description,
             contract.start_date, contract.vendor_id, contract.status, contract.renewal_type)
        )
        conn.commit()

        contract_id = cursor.lastrowid
        cursor.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
        new_contract = cursor.fetchone()

        return new_contract
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/contracts/{contract_id}", response_model=Contract)
def update_contract(contract_id: int, contract_update: ContractUpdate):
    """Update a contract"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Check if contract exists
        cursor.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Build update query dynamically
        update_fields = []
        values = []
        for field, value in contract_update.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = %s")
            values.append(value)

        if not update_fields:
            return existing  # No changes

        values.append(contract_id)
        query = f"UPDATE contracts SET {', '.join(update_fields)} WHERE contract_id = %s"

        cursor.execute(query, values)
        conn.commit()

        cursor.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
        updated_contract = cursor.fetchone()

        return updated_contract
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/contracts/{contract_id}", response_model=Contract)
def delete_contract(contract_id: int):
    """Delete a contract"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Contract not found")

        cursor.execute("DELETE FROM contracts WHERE contract_id = %s", (contract_id,))
        conn.commit()

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ========================
# CONTRACT DOCUMENTS ENDPOINTS
# ========================

@app.get("/contract-documents", response_model=list[ContractDocument])
def get_all_contract_documents():
    """Get all contract documents"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contract_documents")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/contract-documents/{doc_id}", response_model=ContractDocument)
def get_contract_document_by_id(doc_id: int):
    """Get contract document by ID"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Contract document not found")

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/contract-documents", response_model=ContractDocument)
def create_contract_document(document: ContractDocumentBase):
    """Create a new contract document"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO contract_documents (contract_id, file_path, file_type)
               VALUES (%s, %s, %s)""",
            (document.contract_id, document.file_path, document.file_type)
        )
        conn.commit()

        doc_id = cursor.lastrowid
        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        new_document = cursor.fetchone()

        return new_document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/contract-documents/{doc_id}", response_model=ContractDocument)
def update_contract_document(doc_id: int, document_update: ContractDocumentUpdate):
    """Update a contract document"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Check if document exists
        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Contract document not found")

        # Build update query dynamically
        update_fields = []
        values = []
        for field, value in document_update.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = %s")
            values.append(value)

        if not update_fields:
            return existing  # No changes

        values.append(doc_id)
        query = f"UPDATE contract_documents SET {', '.join(update_fields)} WHERE doc_id = %s"

        cursor.execute(query, values)
        conn.commit()

        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        updated_document = cursor.fetchone()

        return updated_document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/contract-documents/{doc_id}", response_model=ContractDocument)
def delete_contract_document(doc_id: int):
    """Delete a contract document"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Contract document not found")

        cursor.execute("DELETE FROM contract_documents WHERE doc_id = %s", (doc_id,))
        conn.commit()

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ========================
# CONTRACT DOCUMENT UPLOAD
# ========================

CONTRACT_DOCUMENT_UPLOAD_DIR = os.environ.get("CONTRACT_DOCUMENT_UPLOAD_DIR", "uploads/contract_documents")


def _infer_file_type(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return ext or "unknown"


def _safe_filename(filename: str) -> str:
    # Avoid path traversal; keep only basename.
    return os.path.basename(filename or "").replace("..", "")


@app.post("/contract-documents/upload", response_model=ContractDocument)
async def upload_contract_document(
    contract_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload an image/file to be stored as a contract document.

    - Saves the file to local disk under `uploads/contract_documents/contract_{contract_id}/...`
    - Inserts a row into `contract_documents(contract_id, file_path, file_type)`
    """
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")

    file_type = _infer_file_type(file.filename)
    safe_name = _safe_filename(file.filename)
    timestamp = int(time.time())

    # Save on server disk (so the client doesn't depend on its local filesystem path)
    contract_dir = os.path.join(CONTRACT_DOCUMENT_UPLOAD_DIR, f"contract_{contract_id}")
    os.makedirs(contract_dir, exist_ok=True)
    dest_filename = f"{timestamp}_{safe_name}"
    dest_path = os.path.join(contract_dir, dest_filename)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file payload")
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Insert into DB
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Ensure contract exists (nice-to-have integrity check)
        cursor.execute("SELECT contract_id FROM contracts WHERE contract_id = %s", (contract_id,))
        exists = cursor.fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Contract not found")

        cursor.execute(
            """
            INSERT INTO contract_documents (contract_id, file_path, file_type, uploaded_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (contract_id, dest_path, file_type),
        )
        conn.commit()

        doc_id = cursor.lastrowid
        cursor.execute("SELECT * FROM contract_documents WHERE doc_id = %s", (doc_id,))
        new_document = cursor.fetchone()
        return new_document
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ========================
# NOTIFICATIONS ENDPOINTS
# ========================

@app.get("/notifications", response_model=list[Notification])
def get_all_notifications():
    """Get all notifications"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM notifications")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/notifications/{notify_id}", response_model=Notification)
def get_notification_by_id(notify_id: int):
    """Get notification by ID"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM notifications WHERE notify_id = %s", (notify_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/notifications", response_model=Notification)
def create_notification(notification: NotificationBase):
    """Create a new notification"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO notifications (contract_id, remind_before_days, notification_date, is_sent)
               VALUES (%s, %s, %s, %s)""",
            (notification.contract_id, notification.remind_before_days,
             notification.notification_date, notification.is_sent)
        )
        conn.commit()

        notify_id = cursor.lastrowid
        cursor.execute("SELECT * FROM notifications WHERE notify_id = %s", (notify_id,))
        new_notification = cursor.fetchone()

        return new_notification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/notifications/{notify_id}", response_model=Notification)
def update_notification(notify_id: int, notification_update: NotificationUpdate):
    """Update a notification"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Check if notification exists
        cursor.execute("SELECT * FROM notifications WHERE notify_id = %s", (notify_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Notification not found")

        # Build update query dynamically
        update_fields = []
        values = []
        for field, value in notification_update.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = %s")
            values.append(value)

        if not update_fields:
            return existing  # No changes

        values.append(notify_id)
        query = f"UPDATE notifications SET {', '.join(update_fields)} WHERE notify_id = %s"

        cursor.execute(query, values)
        conn.commit()

        cursor.execute("SELECT * FROM notifications WHERE notify_id = %s", (notify_id,))
        updated_notification = cursor.fetchone()

        return updated_notification
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/notifications/{notify_id}", response_model=Notification)
def delete_notification(notify_id: int):
    """Delete a notification"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM notifications WHERE notify_id = %s", (notify_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")

        cursor.execute("DELETE FROM notifications WHERE notify_id = %s", (notify_id,))
        conn.commit()

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ========================
# VENDORS ENDPOINTS
# ========================

@app.get("/vendors", response_model=list[Vendor])
def get_all_vendors():
    """Get all vendors"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vendors")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/vendors/{vendor_id}", response_model=Vendor)
def get_vendor_by_id(vendor_id: int):
    """Get vendor by ID"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vendors WHERE vendor_id = %s", (vendor_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Vendor not found")

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/vendors", response_model=Vendor)
def create_vendor(vendor: VendorBase):
    """Create a new vendor"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO vendors (vendor_name, contact_person, email, phone)
               VALUES (%s, %s, %s, %s)""",
            (vendor.vendor_name, vendor.contact_person, vendor.email, vendor.phone)
        )
        conn.commit()

        vendor_id = cursor.lastrowid
        cursor.execute("SELECT * FROM vendors WHERE vendor_id = %s", (vendor_id,))
        new_vendor = cursor.fetchone()

        return new_vendor
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/vendors/{vendor_id}", response_model=Vendor)
def update_vendor(vendor_id: int, vendor_update: VendorUpdate):
    """Update a vendor"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Check if vendor exists
        cursor.execute("SELECT * FROM vendors WHERE vendor_id = %s", (vendor_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Vendor not found")

        # Build update query dynamically
        update_fields = []
        values = []
        for field, value in vendor_update.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = %s")
            values.append(value)

        if not update_fields:
            return existing  # No changes

        values.append(vendor_id)
        query = f"UPDATE vendors SET {', '.join(update_fields)} WHERE vendor_id = %s"

        cursor.execute(query, values)
        conn.commit()

        cursor.execute("SELECT * FROM vendors WHERE vendor_id = %s", (vendor_id,))
        updated_vendor = cursor.fetchone()

        return updated_vendor
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/vendors/{vendor_id}", response_model=Vendor)
def delete_vendor(vendor_id: int):
    """Delete a vendor"""
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM vendors WHERE vendor_id = %s", (vendor_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Vendor not found")

        cursor.execute("DELETE FROM vendors WHERE vendor_id = %s", (vendor_id,))
        conn.commit()

        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ========================
# ROOT ENDPOINT
# ========================
@app.get("/")
def root():
    return {"message": "Contract Management System API", "version": "1.0.0"}