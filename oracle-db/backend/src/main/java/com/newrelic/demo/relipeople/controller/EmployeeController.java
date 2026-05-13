package com.newrelic.demo.relipeople.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/employees")
@CrossOrigin
public class EmployeeController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private NamedParameterJdbcTemplate namedJdbc;

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listEmployees(
            @RequestParam(name = "search", required = false, defaultValue = "") String search,
            @RequestParam(name = "page", required = false, defaultValue = "0") int page,
            @RequestParam(name = "size", required = false, defaultValue = "50") int size) {

        // Double-quoted aliases preserve camelCase casing through Oracle JDBC
        String sql = "SELECT e.emp_id AS \"empId\", "
                + "       e.first_name || ' ' || e.last_name AS \"fullName\", "
                + "       e.email AS \"email\", "
                + "       d.dept_name AS \"deptName\", "
                + "       jg.job_title AS \"jobTitle\", "
                + "       e.hire_date AS \"hireDate\" "
                + "FROM EMPLOYEES e "
                + "JOIN DEPARTMENTS d ON e.dept_id = d.dept_id "
                + "JOIN JOB_GRADES jg ON e.job_id = jg.job_id "
                + "WHERE LOWER(e.last_name) LIKE '%' || LOWER(:search) || '%' "
                + "ORDER BY e.last_name, e.first_name "
                + "OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY";

        MapSqlParameterSource params = new MapSqlParameterSource()
                .addValue("search", search == null ? "" : search)
                .addValue("offset", (long) page * size)
                .addValue("size", size);

        List<Map<String, Object>> rows = namedJdbc.queryForList(sql, params);
        return ResponseEntity.ok(rows);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getEmployee(@PathVariable("id") long id) {
        String employeeSql = "SELECT e.emp_id AS \"empId\", "
                + "       e.first_name AS \"firstName\", "
                + "       e.last_name AS \"lastName\", "
                + "       e.first_name || ' ' || e.last_name AS \"fullName\", "
                + "       e.email AS \"email\", "
                + "       e.hire_date AS \"hireDate\", "
                + "       d.dept_id AS \"deptId\", "
                + "       d.dept_name AS \"deptName\", "
                + "       jg.job_id AS \"jobId\", "
                + "       jg.job_title AS \"jobTitle\" "
                + "FROM EMPLOYEES e "
                + "JOIN DEPARTMENTS d ON e.dept_id = d.dept_id "
                + "JOIN JOB_GRADES jg ON e.job_id = jg.job_id "
                + "WHERE e.emp_id = ?";

        List<Map<String, Object>> employees = jdbcTemplate.queryForList(employeeSql, id);
        if (employees.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        Map<String, Object> employee = employees.get(0);

        String salarySql = "SELECT sh.salary AS \"salary\", sh.effective_date AS \"effectiveDate\" "
                + "FROM SALARY_HISTORY sh "
                + "WHERE sh.emp_id = ? "
                + "ORDER BY sh.effective_date DESC "
                + "FETCH FIRST 1 ROW ONLY";

        List<Map<String, Object>> salaries = jdbcTemplate.queryForList(salarySql, id);

        Map<String, Object> result = new LinkedHashMap<>(employee);
        if (!salaries.isEmpty()) {
            result.put("currentSalary", salaries.get(0).get("salary"));
            result.put("salaryEffectiveDate", salaries.get(0).get("effectiveDate"));
        } else {
            result.put("currentSalary", null);
            result.put("salaryEffectiveDate", null);
        }

        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}/salary-history")
    public ResponseEntity<List<Map<String, Object>>> getSalaryHistory(@PathVariable("id") long id) {
        String sql = "SELECT sh.salary_id AS \"salaryId\", sh.emp_id AS \"empId\", "
                + "       sh.salary AS \"salary\", sh.effective_date AS \"effectiveDate\" "
                + "FROM SALARY_HISTORY sh "
                + "WHERE sh.emp_id = ? "
                + "ORDER BY sh.effective_date DESC";

        List<Map<String, Object>> rows = jdbcTemplate.queryForList(sql, id);
        return ResponseEntity.ok(rows);
    }
}
