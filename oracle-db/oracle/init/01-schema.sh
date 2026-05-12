#!/bin/sh
# ReliPeople HR Self-Service Portal - Schema
# Sourced by gvenzl container-entrypoint, so $APP_USER and $APP_USER_PASSWORD are available.
# Connects as APP_USER in FREEPDB1 so tables land in the app user's schema, not SYS@CDB$ROOT.
# Note: Foreign-key columns are intentionally left unindexed to force full table scans (better telemetry).
sqlplus -s "${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/${ORACLE_DATABASE:-FREEPDB1}" << 'SQLEOF'

CREATE TABLE LOCATIONS (
    location_id NUMBER(6) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city        VARCHAR2(50) NOT NULL,
    state       VARCHAR2(50),
    country_id  CHAR(2) NOT NULL
);

CREATE TABLE JOB_GRADES (
    job_id     VARCHAR2(10) PRIMARY KEY,
    job_title  VARCHAR2(100) NOT NULL,
    min_salary NUMBER(10,2) NOT NULL,
    max_salary NUMBER(10,2) NOT NULL
);

CREATE TABLE DEPARTMENTS (
    dept_id     NUMBER(6) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dept_name   VARCHAR2(100) NOT NULL,
    manager_id  NUMBER(8),
    location_id NUMBER(6) REFERENCES LOCATIONS (location_id)
);

CREATE TABLE EMPLOYEES (
    emp_id     NUMBER(8) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name VARCHAR2(50) NOT NULL,
    last_name  VARCHAR2(50) NOT NULL,
    email      VARCHAR2(100) NOT NULL,
    dept_id    NUMBER(6) REFERENCES DEPARTMENTS (dept_id),
    job_id     VARCHAR2(10) REFERENCES JOB_GRADES (job_id),
    hire_date  DATE NOT NULL
);

CREATE TABLE SALARY_HISTORY (
    salary_id      NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id         NUMBER(8) REFERENCES EMPLOYEES (emp_id),
    salary         NUMBER(10,2) NOT NULL,
    effective_date DATE NOT NULL
);

CREATE TABLE PERFORMANCE_REVIEWS (
    review_id   NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id      NUMBER(8) REFERENCES EMPLOYEES (emp_id),
    review_year NUMBER(4) NOT NULL,
    score       NUMBER(2,1) NOT NULL,
    comments    VARCHAR2(500)
);

CREATE TABLE LEAVE_REQUESTS (
    request_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    emp_id     NUMBER(8) REFERENCES EMPLOYEES (emp_id),
    dept_id    NUMBER(6) REFERENCES DEPARTMENTS (dept_id),
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    status     VARCHAR2(20) DEFAULT 'PENDING'
);

COMMIT;
EXIT
SQLEOF
