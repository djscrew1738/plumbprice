#!/bin/bash

echo "Starting backend optimization script..."

# --- Step 1: Ensure structlog is installed (attempt to resolve previous issue) ---
echo "Attempting to install structlog..."
# This command is run from the 'api' directory, where requirements.txt is located.
# It assumes you are running this script from the project root or have 'api' in your PATH.
pip install structlog || { echo "Failed to install structlog. Please investigate your Python environment."; exit 1; }
echo "structlog installation attempt complete."

# --- Step 2: Generate the Alembic migration ---
echo "Generating Alembic migration for tax_rates table and indexes..."
# Navigate to the api directory for alembic commands
cd api || { echo "Failed to change directory to api/. Please ensure you are in the correct project root."; exit 1; }

# Generate the revision. This might still fail if the structlog issue persists or other Pydantic issues resurface.
# MANUAL REVIEW: After this step, you MUST review the generated migration file in api/alembic/versions/
# to ensure it correctly creates the tax_rates table and adds all intended indexes.
alembic -c alembic.ini revision --autogenerate -m "add tax_rates table and indexes" || { echo "Failed to generate Alembic migration. Please check the error messages and manually resolve."; exit 1; }
echo "Alembic migration generation attempt complete. PLEASE REVIEW THE GENERATED MIGRATION FILE MANUALLY!"

# --- Step 3: Apply the Alembic migration ---
echo "Applying Alembic migration..."
# This command will apply the newly generated migration to your database.
# Ensure your database is running and accessible with the credentials configured in alembic.ini or environment variables.
alembic -c alembic.ini upgrade head || { echo "Failed to apply Alembic migration. Please check database connection and migration file."; exit 1; }
echo "Alembic migration applied."

# --- Step 4: Seed the tax_rates, markup_rules, and labor_templates tables ---
echo "Seeding configuration data into the database..."
# Note: These INSERT statements assume a PostgreSQL database.
# They are NOT idempotent. Running this script multiple times without
# careful consideration might lead to duplicate data.
# In a real-world scenario, consider using ON CONFLICT clauses or checking for existence.

# Seeding tax_rates
echo "Seeding tax_rates..."
# Extract tax rates from pricing_engine.py if possible, or use hardcoded values
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Dallas', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Tarrant', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Collin', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Denton', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Rockwall', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Parker', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO tax_rates (county, rate) VALUES ('Kaufman', 0.0825) ON CONFLICT (county) DO UPDATE SET rate = EXCLUDED.rate;"
echo "tax_rates seeded."

# Seeding markup_rules
echo "Seeding markup_rules..."
# These are example inserts. You'll need to adapt them to the actual structure of your markup_rules table
# and the data from pricing_engine.py
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO markup_rules (name, job_type, markup_type, labor_markup_pct, materials_markup_pct, misc_flat, is_active, notes) VALUES ('Default Service Markup', 'service', 'percentage', 0.0, 0.30, 45.0, TRUE, NULL) ON CONFLICT (name) DO UPDATE SET job_type = EXCLUDED.job_type, markup_type = EXCLUDED.markup_type, labor_markup_pct = EXCLUDED.labor_markup_pct, materials_markup_pct = EXCLUDED.materials_markup_pct, misc_flat = EXCLUDED.misc_flat, is_active = EXCLUDED.is_active, notes = EXCLUDED.notes;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO markup_rules (name, job_type, markup_type, labor_markup_pct, materials_markup_pct, misc_flat, is_active, notes) VALUES ('Default Construction Markup', 'construction', 'percentage', 0.0, 0.20, 0.0, TRUE, NULL) ON CONFLICT (name) DO UPDATE SET job_type = EXCLUDED.job_type, markup_type = EXCLUDED.markup_type, labor_markup_pct = EXCLUDED.labor_markup_pct, materials_markup_pct = EXCLUDED.materials_markup_pct, misc_flat = EXCLUDED.misc_flat, is_active = EXCLUDED.is_active, notes = EXCLUDED.notes;"
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO markup_rules (name, job_type, markup_type, labor_markup_pct, materials_markup_pct, misc_flat, is_active, notes) VALUES ('Default Commercial Markup', 'commercial', 'percentage', 0.0, 0.25, 0.0, TRUE, NULL) ON CONFLICT (name) DO UPDATE SET job_type = EXCLUDED.job_type, markup_type = EXCLUDED.markup_type, labor_markup_pct = EXCLUDED.labor_markup_pct, materials_markup_pct = EXCLUDED.materials_markup_pct, misc_flat = EXCLUDED.misc_flat, is_active = EXCLUDED.is_active, notes = EXCLUDED.notes;"
echo "markup_rules seeded."

# Seeding labor_templates
echo "Seeding labor_templates..."
# This part is complex due to the nested structure of LaborTemplateData.
# It would typically involve a Python script to iterate through LABOR_TEMPLATES
# and insert them into the database. For a shell script, this is highly simplified.
# You will likely need to write a dedicated Python script for this.
echo "WARNING: Seeding labor_templates is complex for a shell script."
echo "         Please consider writing a Python script to parse api/app/services/labor_engine.py"
echo "         and insert data into the 'labor_templates' table programmatically."
echo "         Example: TOILET_REPLACE_STANDARD, WH_50G_GAS_STANDARD, etc."
# Example for one labor template - you would need many more based on labor_engine.py
psql -d plumbprice -U plumbprice -h localhost -p 5432 -c "INSERT INTO labor_templates (code, name, category, base_hours, lead_rate, helper_required, helper_rate, disposal_hours, notes, is_active) VALUES ('TOILET_REPLACE_STANDARD', 'Toilet Replace — Standard', 'service', 1.5, 95.0, FALSE, 50.0, 0.25, 'Includes remove & replace. Wax ring, closet bolts, supply line in kit.', TRUE) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category, base_hours = EXCLUDED.base_hours, lead_rate = EXCLUDED.lead_rate, helper_required = EXCLUDED.helper_required, helper_rate = EXCLUDED.helper_rate, disposal_hours = EXCLUDED.disposal_hours, notes = EXCLUDED.notes, is_active = EXCLUDED.is_active;"
echo "labor_templates seeding (partial/manual) complete."

# Return to original directory
cd ..

echo "Backend optimization script finished. Please review any error messages and the generated migration file."
echo "Once the manual database seeding for labor_templates is complete, please let me know to proceed with code modifications."
