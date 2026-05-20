SCHEMA = """
Table: customers
Columns: customerNumber (INTEGER), customerName (VARCHAR), contactLastName (VARCHAR), contactFirstName (VARCHAR), phone (VARCHAR), addressLine1 (VARCHAR), addressLine2 (VARCHAR), city (VARCHAR), state (VARCHAR), postalCode (VARCHAR), country (VARCHAR), salesRepEmployeeNumber (INTEGER), creditLimit (DECIMAL)

Table: employees
Columns: employeeNumber (INTEGER), lastName (VARCHAR), firstName (VARCHAR), extension (VARCHAR), email (VARCHAR), officeCode (VARCHAR), reportsTo (INTEGER), jobTitle (VARCHAR)

Table: offices
Columns: officeCode (VARCHAR), city (VARCHAR), phone (VARCHAR), addressLine1 (VARCHAR), addressLine2 (VARCHAR), state (VARCHAR), country (VARCHAR), postalCode (VARCHAR), territory (VARCHAR)

Table: orderdetails
Columns: orderNumber (INTEGER), productCode (VARCHAR), quantityOrdered (INTEGER), priceEach (DECIMAL), orderLineNumber (SMALLINT)

Table: orders
Columns: orderNumber (INTEGER), orderDate (DATE), requiredDate (DATE), shippedDate (DATE), status (VARCHAR), comments (TEXT), customerNumber (INTEGER)

Table: payments
Columns: customerNumber (INTEGER), checkNumber (VARCHAR), paymentDate (DATE), amount (DECIMAL)

Table: productlines
Columns: productLine (VARCHAR), textDescription (VARCHAR), htmlDescription (TEXT), image (BYTEA)

Table: products
Columns: productCode (VARCHAR), productName (VARCHAR), productLine (VARCHAR), productScale (VARCHAR), productVendor (VARCHAR), productDescription (TEXT), quantityInStock (SMALLINT), buyPrice (DECIMAL), MSRP (DECIMAL)
"""

DECOMPOSE_PROMPT = """You are an expert SQL analyst. Break down the user's natural language question into a structured JSON representation.

Database Schema:
{schema}

User Question: {question}

Return ONLY valid JSON matching this exact structure (no markdown formatting, no explanations):
{{
  "intent": "brief description of what the user wants",
  "tables": ["table1", "table2"],
  "columns": ["col1", "col2"],
  "filters": ["condition1", "condition2"],
  "joins": ["join condition 1"],
  "group_by": ["col1"],
  "aggregation": "SUM|COUNT|AVG|MIN|MAX|none",
  "order_by": "col DESC|none",
  "limit": 10
}}
"""

GENERATE_PROMPT = """You are an expert PostgreSQL developer. Write a valid SQL query based on the following structured decomposition.

Database Schema:
{schema}

Decomposition:
{decomposition}

Return ONLY the raw SQL query. Do not wrap in markdown tags like ```sql. Do not add any explanations.
"""

FIX_PROMPT = """You are an expert PostgreSQL developer. The following SQL query failed with an error. Fix it.

Database Schema:
{schema}

User Question: {question}

Failed SQL Query:
{sql}

Database Error:
{error}

Return ONLY the fixed raw SQL query. Do not wrap in markdown tags like ```sql. Do not add any explanations.
"""
