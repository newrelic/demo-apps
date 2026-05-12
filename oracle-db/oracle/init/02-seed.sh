#!/bin/sh
# ReliPeople HR Self-Service Portal - Seed Data
# Sourced by gvenzl container-entrypoint. Connects as APP_USER to seed data in FREEPDB1.
# Volumes: LOCATIONS(30) JOB_GRADES(20) DEPARTMENTS(50) EMPLOYEES(50K)
#          SALARY_HISTORY(200K) PERFORMANCE_REVIEWS(150K) LEAVE_REQUESTS(100K)
sqlplus -s "${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/${ORACLE_DATABASE:-FREEPDB1}" << 'SQLEOF'

-- ---------------------------------------------------------------------------
-- LOCATIONS: 30 rows cycling through 10 US cities
-- ---------------------------------------------------------------------------
INSERT INTO LOCATIONS (city, state, country_id)
SELECT
    CASE MOD(ROWNUM - 1, 10)
        WHEN 0 THEN 'New York'
        WHEN 1 THEN 'Los Angeles'
        WHEN 2 THEN 'Chicago'
        WHEN 3 THEN 'Houston'
        WHEN 4 THEN 'Phoenix'
        WHEN 5 THEN 'Philadelphia'
        WHEN 6 THEN 'San Antonio'
        WHEN 7 THEN 'San Diego'
        WHEN 8 THEN 'Dallas'
        WHEN 9 THEN 'San Jose'
    END AS city,
    CASE MOD(ROWNUM - 1, 10)
        WHEN 0 THEN 'NY'
        WHEN 1 THEN 'CA'
        WHEN 2 THEN 'IL'
        WHEN 3 THEN 'TX'
        WHEN 4 THEN 'AZ'
        WHEN 5 THEN 'PA'
        WHEN 6 THEN 'TX'
        WHEN 7 THEN 'CA'
        WHEN 8 THEN 'TX'
        WHEN 9 THEN 'CA'
    END AS state,
    'US' AS country_id
FROM DUAL CONNECT BY LEVEL <= 30;

-- ---------------------------------------------------------------------------
-- JOB_GRADES: 20 rows (explicit INSERTs for clarity)
-- ---------------------------------------------------------------------------
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('HR_REP',    'HR Representative',           45000,  70000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('HR_MGR',    'HR Manager',                  80000, 120000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('RECRUITER', 'Talent Recruiter',            50000,  85000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SW_ENG_I',  'Software Engineer I',         70000,  95000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SW_ENG_II', 'Software Engineer II',        90000, 125000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SW_ENG_SR', 'Senior Software Engineer',   120000, 170000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SW_STAFF',  'Staff Software Engineer',    150000, 210000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SW_MGR',    'Engineering Manager',        140000, 200000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('DATA_ENG',  'Data Engineer',               95000, 140000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('DATA_SCI',  'Data Scientist',             100000, 150000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('PM_I',      'Product Manager I',           85000, 120000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('PM_SR',     'Senior Product Manager',     125000, 175000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('DESIGNER',  'Product Designer',            80000, 125000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SALES_REP', 'Sales Representative',        55000,  95000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SALES_MGR', 'Sales Manager',              110000, 160000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('FIN_ANLST', 'Financial Analyst',           70000, 105000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('ACCT',      'Accountant',                  60000,  95000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('MKT_SPEC',  'Marketing Specialist',        55000,  90000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('SUPPORT',   'Customer Support Specialist', 40000,  70000);
INSERT INTO JOB_GRADES (job_id, job_title, min_salary, max_salary) VALUES ('OPS_ANLST', 'Operations Analyst',          65000, 100000);

-- ---------------------------------------------------------------------------
-- DEPARTMENTS: 50 rows
-- ---------------------------------------------------------------------------
INSERT INTO DEPARTMENTS (dept_name, manager_id, location_id)
SELECT
    CASE MOD(ROWNUM - 1, 10)
        WHEN 0 THEN 'Engineering - Division '    || TO_CHAR(ROWNUM)
        WHEN 1 THEN 'Sales - Division '          || TO_CHAR(ROWNUM)
        WHEN 2 THEN 'Marketing - Division '      || TO_CHAR(ROWNUM)
        WHEN 3 THEN 'Human Resources - Division '|| TO_CHAR(ROWNUM)
        WHEN 4 THEN 'Finance - Division '        || TO_CHAR(ROWNUM)
        WHEN 5 THEN 'Operations - Division '     || TO_CHAR(ROWNUM)
        WHEN 6 THEN 'Customer Support - Division '|| TO_CHAR(ROWNUM)
        WHEN 7 THEN 'Product - Division '        || TO_CHAR(ROWNUM)
        WHEN 8 THEN 'Data Science - Division '   || TO_CHAR(ROWNUM)
        WHEN 9 THEN 'Design - Division '         || TO_CHAR(ROWNUM)
    END AS dept_name,
    NULL AS manager_id,
    MOD(ROWNUM - 1, 30) + 1 AS location_id
FROM DUAL CONNECT BY LEVEL <= 50;

COMMIT;

-- ---------------------------------------------------------------------------
-- EMPLOYEES: 50,000 rows
-- ---------------------------------------------------------------------------
INSERT INTO EMPLOYEES (first_name, last_name, email, dept_id, job_id, hire_date)
SELECT
    CASE MOD(ROWNUM, 20)
        WHEN 0  THEN 'James'    WHEN 1  THEN 'Mary'     WHEN 2  THEN 'Robert'
        WHEN 3  THEN 'Patricia' WHEN 4  THEN 'John'     WHEN 5  THEN 'Jennifer'
        WHEN 6  THEN 'Michael'  WHEN 7  THEN 'Linda'    WHEN 8  THEN 'David'
        WHEN 9  THEN 'Elizabeth'WHEN 10 THEN 'William'  WHEN 11 THEN 'Barbara'
        WHEN 12 THEN 'Richard'  WHEN 13 THEN 'Susan'    WHEN 14 THEN 'Joseph'
        WHEN 15 THEN 'Jessica'  WHEN 16 THEN 'Thomas'   WHEN 17 THEN 'Sarah'
        WHEN 18 THEN 'Charles'  WHEN 19 THEN 'Karen'
    END AS first_name,
    CASE MOD(ROWNUM, 25)
        WHEN 0  THEN 'Smith'     WHEN 1  THEN 'Johnson'  WHEN 2  THEN 'Williams'
        WHEN 3  THEN 'Brown'     WHEN 4  THEN 'Jones'    WHEN 5  THEN 'Garcia'
        WHEN 6  THEN 'Miller'    WHEN 7  THEN 'Davis'    WHEN 8  THEN 'Rodriguez'
        WHEN 9  THEN 'Martinez'  WHEN 10 THEN 'Hernandez'WHEN 11 THEN 'Lopez'
        WHEN 12 THEN 'Gonzalez'  WHEN 13 THEN 'Wilson'   WHEN 14 THEN 'Anderson'
        WHEN 15 THEN 'Thomas'    WHEN 16 THEN 'Taylor'   WHEN 17 THEN 'Moore'
        WHEN 18 THEN 'Jackson'   WHEN 19 THEN 'Martin'   WHEN 20 THEN 'Lee'
        WHEN 21 THEN 'Perez'     WHEN 22 THEN 'Thompson' WHEN 23 THEN 'White'
        WHEN 24 THEN 'Harris'
    END AS last_name,
    LOWER(
        CASE MOD(ROWNUM, 20)
            WHEN 0  THEN 'james'    WHEN 1  THEN 'mary'     WHEN 2  THEN 'robert'
            WHEN 3  THEN 'patricia' WHEN 4  THEN 'john'     WHEN 5  THEN 'jennifer'
            WHEN 6  THEN 'michael'  WHEN 7  THEN 'linda'    WHEN 8  THEN 'david'
            WHEN 9  THEN 'elizabeth'WHEN 10 THEN 'william'  WHEN 11 THEN 'barbara'
            WHEN 12 THEN 'richard'  WHEN 13 THEN 'susan'    WHEN 14 THEN 'joseph'
            WHEN 15 THEN 'jessica'  WHEN 16 THEN 'thomas'   WHEN 17 THEN 'sarah'
            WHEN 18 THEN 'charles'  WHEN 19 THEN 'karen'
        END
        || ROWNUM || '@relipeople.internal'
    ) AS email,
    MOD(ROWNUM, 50) + 1 AS dept_id,
    CASE MOD(ROWNUM, 20)
        WHEN 0  THEN 'HR_REP'    WHEN 1  THEN 'HR_MGR'    WHEN 2  THEN 'RECRUITER'
        WHEN 3  THEN 'SW_ENG_I'  WHEN 4  THEN 'SW_ENG_II' WHEN 5  THEN 'SW_ENG_SR'
        WHEN 6  THEN 'SW_STAFF'  WHEN 7  THEN 'SW_MGR'    WHEN 8  THEN 'DATA_ENG'
        WHEN 9  THEN 'DATA_SCI'  WHEN 10 THEN 'PM_I'      WHEN 11 THEN 'PM_SR'
        WHEN 12 THEN 'DESIGNER'  WHEN 13 THEN 'SALES_REP' WHEN 14 THEN 'SALES_MGR'
        WHEN 15 THEN 'FIN_ANLST' WHEN 16 THEN 'ACCT'      WHEN 17 THEN 'MKT_SPEC'
        WHEN 18 THEN 'SUPPORT'   WHEN 19 THEN 'OPS_ANLST'
    END AS job_id,
    TRUNC(SYSDATE) - MOD(ROWNUM * 7, 5000) AS hire_date
FROM (SELECT LEVEL rn FROM DUAL CONNECT BY LEVEL <= 50000);

COMMIT;

-- ---------------------------------------------------------------------------
-- SALARY_HISTORY: 200,000 rows (4 per employee)
-- ---------------------------------------------------------------------------
INSERT INTO SALARY_HISTORY (emp_id, salary, effective_date)
SELECT
    e.emp_id,
    ROUND(
        jg.min_salary
        + ((jg.max_salary - jg.min_salary) * (s.raise_num - 1) / 4)
        + MOD(e.emp_id, 500),
        2
    ) AS salary,
    TRUNC(e.hire_date) + (s.raise_num - 1) * 365 AS effective_date
FROM EMPLOYEES e
JOIN JOB_GRADES jg ON jg.job_id = e.job_id
CROSS JOIN (SELECT LEVEL raise_num FROM DUAL CONNECT BY LEVEL <= 4) s;

COMMIT;

-- ---------------------------------------------------------------------------
-- PERFORMANCE_REVIEWS: 150,000 rows (3 per employee)
-- ---------------------------------------------------------------------------
INSERT INTO PERFORMANCE_REVIEWS (emp_id, review_year, score, comments)
SELECT
    e.emp_id,
    2022 + y.yr_offset AS review_year,
    ROUND(2.5 + MOD(e.emp_id + y.yr_offset, 26) / 10, 1) AS score,
    CASE MOD(e.emp_id + y.yr_offset, 5)
        WHEN 0 THEN 'Exceeded expectations; strong contributor this cycle.'
        WHEN 1 THEN 'Met all goals; consistent performance throughout the year.'
        WHEN 2 THEN 'Below expectations on two objectives; development plan in place.'
        WHEN 3 THEN 'Outstanding impact on cross-functional initiatives.'
        WHEN 4 THEN 'Solid execution; opportunities identified for growth next cycle.'
    END AS comments
FROM EMPLOYEES e
CROSS JOIN (SELECT LEVEL - 1 yr_offset FROM DUAL CONNECT BY LEVEL <= 3) y;

COMMIT;

-- ---------------------------------------------------------------------------
-- LEAVE_REQUESTS: 100,000 rows (2 per employee)
-- ---------------------------------------------------------------------------
INSERT INTO LEAVE_REQUESTS (emp_id, dept_id, start_date, end_date, status)
SELECT
    e.emp_id,
    e.dept_id,
    TRUNC(SYSDATE) - MOD(e.emp_id * l.lv_num, 365) AS start_date,
    TRUNC(SYSDATE) - MOD(e.emp_id * l.lv_num, 365) + MOD(e.emp_id, 10) + 1 AS end_date,
    CASE MOD(e.emp_id + l.lv_num, 3)
        WHEN 0 THEN 'PENDING'
        WHEN 1 THEN 'APPROVED'
        WHEN 2 THEN 'DENIED'
    END AS status
FROM EMPLOYEES e
CROSS JOIN (SELECT LEVEL lv_num FROM DUAL CONNECT BY LEVEL <= 2) l;

COMMIT;
EXIT
SQLEOF
