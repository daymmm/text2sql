import json
from database import get_connection

def extract_schema():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    
    schema = {}
    for (table_name,) in tables:
        cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """)
        columns = cursor.fetchall()
        schema[table_name] = [f"{col[0]} ({col[1]})" for col in columns]
        
    for table, cols in schema.items():
        print(f"Table: {table}")
        for col in cols:
            print(f"  - {col}")
    
    conn.close()

if __name__ == "__main__":
    extract_schema()
