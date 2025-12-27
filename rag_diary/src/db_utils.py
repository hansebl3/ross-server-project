"""
RAG Diary Database Utilities
----------------------------
This module handles all interactions with MariaDB (SQL Database).
It provides functions to:
1.  Connect to the database.
2.  Initialize tables based on the category configuration.
3.  Save diary entries dynamically to the correct table.
"""

import pymysql
import os
import streamlit as st
import category_config
from shared.db.mariadb import MariaDBConnector

MARIADB_DB = os.getenv("MARIADB_DB", "rag_diary_db")

def get_db_connection(db_name=None):
    """Establishes a connection to the MariaDB database."""
    # If db_name is provided, use it. If not, use shared lib default (from env).
    # To support original behavior of 'no db selected' used in init_db, we need to handle that.
    # The original code's get_db_connection() did NOT select a DB.
    # But save_to_mariadb() did 'USE {MARIADB_DB}'.
    # Let's map this:
    # If we want the connection for 'init_db' (create db), we pass db_name=""
    connector = MariaDBConnector()
    if db_name is None:
        # Original 'get_db_connection' logic was NO DB selected.
        # But 'save_to_mariadb' function uses this and expects a connection, then does 'USE'.
        # So we can safely return a connection to the default DB if it exists, or No DB if we want?
        # Actually, if we connect TO the DB, 'USE' is redundant but fine.
        # However, init_db probably wants NO DB.
        # Let's verify how init_db uses it.
        pass

    # Simplified approach:
    # We default to NO DB selection to match legacy behavior, allowing caller to USE or init_db to work?
    # NO, shared lib defaults to ENV DB.
    # Let's change the default behavior of this project to use the env DB unless specified.
    
    # Wait, save_to_mariadb() below does `cursor.execute(f"USE {MARIADB_DB}")`.
    # If we are already connected to MARIADB_DB, this is fine.
    
    # init_db() calls get_db_connection(), then `CREATE DATABASE ...`.
    # If we connect to MARIADB_DB and it doesn't exist, it fails.
    # So init_db needs a connection WITHOUT DB selected.
    
    return connector.get_connection(db_name=db_name if db_name is not None else "")

def init_db():
    """Initializes the database and creates tables based on config."""
    # Connect without selecting DB to check/create it
    conn = get_db_connection(db_name="")
    if conn:
        try:
            with conn.cursor() as cursor:
                # Create Database if not exists
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MARIADB_DB}")
                cursor.execute(f"USE {MARIADB_DB}")
                
                # Iterate through all categories and create their specific tables
                for cat_key, config in category_config.CATEGORY_CONFIG.items():
                    table_name = config.get("table_name")
                    table_schema = config.get("table_schema")
                    
                    if table_name and table_schema:
                        create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({table_schema})"
                        # st.write(f"Creating table: {table_name}") # Debug
                        cursor.execute(create_query)
                        
            conn.commit()
        except pymysql.MySQLError as e:
            st.error(f"Error initializing DB: {e}")
            st.error(f"Query was: {create_query}")
        finally:
            conn.close()

def save_to_mariadb(table_name, data_dict):
    """
    Saves the log entry to the specific MariaDB table dynamically.
    
    Args:
        table_name (str): Name of the table to insert into.
        data_dict (dict): Dictionary of column_name: value.

    Returns:
        int or None: The `id` of the inserted row if successful, None otherwise.
    """
    conn = get_db_connection(db_name=MARIADB_DB)
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"USE {MARIADB_DB}")
                
                # Dynamic Insert Construction
                
                # [Safety Feature] Fetch valid columns to prevent "Unknown column" errors
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                valid_columns = {row['Field'] for row in cursor.fetchall()}
                
                # Filter data_dict to only include valid columns
                filtered_data = {k: v for k, v in data_dict.items() if k in valid_columns}
                
                if not filtered_data:
                    st.warning(f"No valid data fields found for table {table_name}.")
                    return None

                columns = list(filtered_data.keys())
                placeholders = ["%s"] * len(columns)
                values = list(filtered_data.values())
                
                col_str = ", ".join(columns)
                val_str = ", ".join(placeholders)
                
                insert_query = f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str})"
                
                cursor.execute(insert_query, values)
                
                # For Hybrid Schema with UUID, lastrowid might be 0.
                if 'uuid' in filtered_data:
                    inserted_id = filtered_data['uuid']
                else:
                    inserted_id = cursor.lastrowid 
            
            conn.commit()
            return inserted_id # Return ID/UUID
        except pymysql.MySQLError as e:
            st.error(f"Error saving to MariaDB Table '{table_name}': {e}")
            return None
        finally:
            conn.close()
    return None
