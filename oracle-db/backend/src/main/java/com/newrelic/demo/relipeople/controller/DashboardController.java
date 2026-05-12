package com.newrelic.demo.relipeople.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
@CrossOrigin
public class DashboardController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();

        Integer totalEmployees = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM EMPLOYEES", Integer.class);
        Integer totalDepts = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM DEPARTMENTS", Integer.class);
        Integer recentHires = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM EMPLOYEES WHERE hire_date >= SYSDATE - 90",
                Integer.class);
        Integer pendingLeaves = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM LEAVE_REQUESTS WHERE status = 'PENDING'",
                Integer.class);

        stats.put("totalEmployees", totalEmployees);
        stats.put("totalDepts", totalDepts);
        stats.put("recentHires", recentHires);
        stats.put("pendingLeaves", pendingLeaves);

        return ResponseEntity.ok(stats);
    }
}
