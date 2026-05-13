package com.newrelic.demo.relipeople.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/leaves")
@CrossOrigin
public class LeaveController {

    @Autowired
    private NamedParameterJdbcTemplate namedJdbc;

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> listLeaves(
            @RequestParam(name = "status", required = false) String status,
            @RequestParam(name = "dept", required = false) String dept,
            @RequestParam(name = "page", required = false, defaultValue = "0") int page,
            @RequestParam(name = "size", required = false, defaultValue = "50") int size) {

        String sql = "SELECT lr.request_id AS \"requestId\", "
                + "       e.first_name || ' ' || e.last_name AS \"empName\", "
                + "       d.dept_name AS \"deptName\", "
                + "       lr.start_date AS \"startDate\", "
                + "       lr.end_date AS \"endDate\", "
                + "       lr.status AS \"status\", "
                + "       TRUNC(lr.end_date) - TRUNC(lr.start_date) AS \"durationDays\" "
                + "FROM LEAVE_REQUESTS lr "
                + "JOIN EMPLOYEES e ON lr.emp_id = e.emp_id "
                + "JOIN DEPARTMENTS d ON lr.dept_id = d.dept_id "
                + "WHERE (:status IS NULL OR lr.status = :status) "
                + "  AND (:dept IS NULL OR d.dept_name LIKE '%' || :dept || '%') "
                + "ORDER BY lr.start_date DESC "
                + "OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY";

        MapSqlParameterSource params = new MapSqlParameterSource()
                .addValue("status", (status == null || status.isBlank()) ? null : status)
                .addValue("dept", (dept == null || dept.isBlank()) ? null : dept)
                .addValue("offset", (long) page * size)
                .addValue("size", size);

        List<Map<String, Object>> rows = namedJdbc.queryForList(sql, params);
        return ResponseEntity.ok(rows);
    }
}
