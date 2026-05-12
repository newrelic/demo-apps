package com.newrelic.demo.relipeople.frontend.servlet;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.EntityUtils;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@WebServlet(urlPatterns = {"/employees", "/employees/*"})
public class EmployeeServlet extends HttpServlet {

    private static final String BACKEND_URL = System.getenv().getOrDefault("BACKEND_URL", "http://backend:8080");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String pathInfo = request.getPathInfo();

        if (pathInfo != null && pathInfo.length() > 1) {
            String empId = pathInfo.substring(1);
            if (empId.endsWith("/")) {
                empId = empId.substring(0, empId.length() - 1);
            }
            handleEmployeeProfile(request, response, empId);
        } else {
            handleEmployeeList(request, response);
        }
    }

    private void handleEmployeeList(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String search = request.getParameter("search");
        String page = request.getParameter("page");
        if (search == null) search = "";
        if (page == null || page.isEmpty()) page = "0";

        String endpoint = "/api/employees?search=" +
                URLEncoder.encode(search, StandardCharsets.UTF_8) +
                "&page=" + URLEncoder.encode(page, StandardCharsets.UTF_8) +
                "&size=50";

        List<Map<String, Object>> employees;
        try {
            employees = fetchList(endpoint);
        } catch (IOException e) {
            employees = Collections.emptyList();
            request.setAttribute("error", "Unable to load employees: " + e.getMessage());
        }

        request.setAttribute("employees", employees);
        request.setAttribute("search", search);
        request.getRequestDispatcher("/jsp/employees.jsp").forward(request, response);
    }

    private void handleEmployeeProfile(HttpServletRequest request, HttpServletResponse response, String empId)
            throws ServletException, IOException {
        Map<String, Object> employee;
        List<Map<String, Object>> salaryHistory;
        try {
            employee = fetchMap("/api/employees/" + URLEncoder.encode(empId, StandardCharsets.UTF_8));
            salaryHistory = fetchList("/api/employees/" + URLEncoder.encode(empId, StandardCharsets.UTF_8) + "/salary-history");
        } catch (IOException e) {
            employee = new HashMap<>();
            salaryHistory = Collections.emptyList();
            request.setAttribute("error", "Unable to load employee: " + e.getMessage());
        }

        request.setAttribute("employee", employee);
        request.setAttribute("salaryHistory", salaryHistory);
        request.getRequestDispatcher("/jsp/employee-profile.jsp").forward(request, response);
    }

    private List<Map<String, Object>> fetchList(String endpoint) throws IOException {
        try (CloseableHttpClient client = HttpClients.createDefault()) {
            HttpGet get = new HttpGet(BACKEND_URL + endpoint);
            return client.execute(get, resp -> {
                String body = EntityUtils.toString(resp.getEntity());
                return MAPPER.readValue(body, new TypeReference<List<Map<String, Object>>>() {});
            });
        }
    }

    private Map<String, Object> fetchMap(String endpoint) throws IOException {
        try (CloseableHttpClient client = HttpClients.createDefault()) {
            HttpGet get = new HttpGet(BACKEND_URL + endpoint);
            return client.execute(get, resp -> {
                String body = EntityUtils.toString(resp.getEntity());
                return MAPPER.readValue(body, new TypeReference<Map<String, Object>>() {});
            });
        }
    }
}
