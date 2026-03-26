# Contract Management System API

This project is a FastAPI application that connects to a MariaDB database named "Contract Management System". It provides a comprehensive API to manage contracts, contract documents, notifications, and vendors, allowing users to perform CRUD (Create, Read, Update, Delete) operations on all tables.

## Project Structure

```
contract-management-api
├── api.py                  # FastAPI application with API endpoints
├── requirements.txt        # Project dependencies
├── README.md               # Project documentation
└── env/                    # Virtual environment
```

## Database Configuration

The API connects to MariaDB with the following configuration:
- **Host**: 192.168.100.85
- **Database**: Contract Management System
- **User**: root
- **Password**: P@ssw0rd

## Tables

### contracts
- contract_id: INT (Primary Key)
- contract_number: VARCHAR
- title: VARCHAR
- description: TEXT
- start_date: DATE
- vendor_id: INT (Foreign Key)
- status: ENUM (Active, Expired, Terminated, Pending)
- renewal_type: ENUM (Manual, Auto-Renew)
- created_at: TIMESTAMP

### contract_documents
- doc_id: INT (Primary Key)
- contract_id: INT (Foreign Key)
- file_path: VARCHAR
- file_type: VARCHAR
- uploaded_at: TIMESTAMP

### notifications
- notify_id: INT (Primary Key)
- contract_id: INT (Foreign Key)
- remind_before_days: INT
- notification_date: DATE
- is_sent: BOOLEAN
- last_sent_at: DATETIME

### vendors
- vendor_id: INT (Primary Key)
- vendor_name: VARCHAR
- contact_person: VARCHAR
- email: VARCHAR
- phone: VARCHAR

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd contract-management-api
   ```

2. **Activate virtual environment:**
   ```
   env\Scripts\activate  # On Windows
   ```

3. **Install dependencies:**
   Make sure you have Python 3.7 or higher installed. Then, install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. **Configure the Database:**
   Ensure that you have a MariaDB server running at 192.168.100.85 with the "Contract Management System" database created and the tables set up as described above.

## Usage

To run the FastAPI application, use the following command:
```
uvicorn api:app --reload
```

You can access the API documentation at `http://127.0.0.1:8000/docs`.

## API Endpoints

### Contracts
- `GET /contracts` - Get all contracts
- `GET /contracts/{contract_id}` - Get contract by ID
- `POST /contracts` - Create a new contract
- `PUT /contracts/{contract_id}` - Update a contract
- `DELETE /contracts/{contract_id}` - Delete a contract

### Contract Documents
- `GET /contract-documents` - Get all contract documents
- `GET /contract-documents/{doc_id}` - Get contract document by ID
- `POST /contract-documents` - Create a new contract document
- `PUT /contract-documents/{doc_id}` - Update a contract document
- `DELETE /contract-documents/{doc_id}` - Delete a contract document

### Notifications
- `GET /notifications` - Get all notifications
- `GET /notifications/{notify_id}` - Get notification by ID
- `POST /notifications` - Create a new notification
- `PUT /notifications/{notify_id}` - Update a notification
- `DELETE /notifications/{notify_id}` - Delete a notification

### Vendors
- `GET /vendors` - Get all vendors
- `GET /vendors/{vendor_id}` - Get vendor by ID
- `POST /vendors` - Create a new vendor
- `PUT /vendors/{vendor_id}` - Update a vendor
- `DELETE /vendors/{vendor_id}` - Delete a vendor

## Example API Usage

### Create a Vendor
```json
POST /vendors
{
  "vendor_name": "ABC Corp",
  "contact_person": "John Doe",
  "email": "john@abc.com",
  "phone": "+1234567890"
}
```

### Create a Contract
```json
POST /contracts
{
  "contract_number": "CON-001",
  "title": "Software License Agreement",
  "description": "Annual software license",
  "start_date": "2024-01-01",
  "vendor_id": 1,
  "status": "Active",
  "renewal_type": "Auto-Renew"
}
```

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Success
- 404: Resource not found
- 500: Internal server error

All endpoints include proper error handling and database connection management.

- **GET /books**: Retrieve all books.
- **GET /books/{id}**: Retrieve a book by its ID.
- **POST /books**: Add a new book.
- **PUT /books/{id}**: Update an existing book by its ID.
- **DELETE /books/{id}**: Delete a book by its ID.

## License

This project is licensed under the MIT License. See the LICENSE file for details.