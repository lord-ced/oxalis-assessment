# Data Engineering Take-Home Exercise

## Overview

This 2-3 hour exercise demonstrates core data engineering skills using Python, dbt, and PostgreSQL (as a Snowflake substitute) in a containerized environment. You'll build an end-to-end data pipeline locally using Docker.

## Objective

Create a local data pipeline that extracts data from a source, loads it into a PostgreSQL database, transforms it using dbt, and produces analytical outputs.

## Prerequisites

- Docker and Docker Compose installed
- Basic familiarity with Python, SQL, and command line
- Git for version control (optional)

## Exercise Components

### 1. Project Setup

- Create a project directory structure
- Set up Docker Compose configuration
- Configure service containers for Python, PostgreSQL, and dbt

### 2. Data Extraction with Python

Write a Python script that:
- Generates synthetic sales data or reads from a provided CSV
- Performs basic data validation and cleaning
- Loads the data into PostgreSQL staging tables
- Implements proper error handling and logging

### 3. Data Modeling with dbt

Configure a dbt project that:
- Connects to your PostgreSQL database
- Creates a staging model from raw data
- Builds at least one intermediate model
- Produces a final analytical model (e.g., daily sales metrics)
- Includes data tests and basic documentation

### 4. Pipeline Orchestration

Create an orchestration script to:
- Run services in the correct order
- Execute the Python ETL process
- Run dbt models
- Validate the results

### 5. Documentation & Testing

- Document your approach and architecture
- Create basic tests for your pipeline components
- Add a README with setup and execution instructions

## Deliverables

1. A Docker Compose file with all necessary services
2. Python ETL script for data extraction and loading
3. dbt models for data transformation
4. Orchestration script to run the pipeline
5. Documentation describing your solution

## Bonus Challenges (if time permits)

- Implement incremental loading in your dbt models
- Add data quality tests in dbt
- Create a simple dashboard or visualization of the final data
- Implement a lightweight metadata tracking system