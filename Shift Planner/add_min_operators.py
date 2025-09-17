#!/usr/bin/env python3
"""Add min_operators field to machines table"""

import sqlite3

DATABASE = 'shift_planner.db'

def add_min_operators_field():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Add min_operators column to machines table
        c.execute("ALTER TABLE machines ADD COLUMN min_operators INTEGER DEFAULT 1")
        print("Added min_operators column to machines table")
        
        # Set default values (1 for most machines, can be adjusted)
        c.execute("UPDATE machines SET min_operators = 1 WHERE min_operators IS NULL")
        conn.commit()
        print("Set default min_operators to 1 for all machines")
        
        # Show current machine configuration
        c.execute("SELECT id, name, max_operators, min_operators FROM machines")
        machines = c.fetchall()
        
        print("\nCurrent Machine Configuration:")
        print("-" * 60)
        print(f"{'ID':<5} {'Name':<20} {'Min Operators':<15} {'Max Operators':<15}")
        print("-" * 60)
        for machine in machines:
            print(f"{machine[0]:<5} {machine[1]:<20} {machine[3]:<15} {machine[2]:<15}")
            
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("min_operators column already exists")
            
            # Show current configuration
            c.execute("SELECT id, name, max_operators, min_operators FROM machines")
            machines = c.fetchall()
            
            print("\nCurrent Machine Configuration:")
            print("-" * 60)
            print(f"{'ID':<5} {'Name':<20} {'Min Operators':<15} {'Max Operators':<15}")
            print("-" * 60)
            for machine in machines:
                print(f"{machine[0]:<5} {machine[1]:<20} {machine[3]:<15} {machine[2]:<15}")
        else:
            raise
    
    conn.close()

if __name__ == '__main__':
    add_min_operators_field()