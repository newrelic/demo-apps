package com.newrelic.demo.relipeople.frontend.servlet;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.util.Timeout;

import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@WebServlet(urlPatterns = {"/reports/payroll", "/reports/departments", "/reports/performance",
        "/reports/leave-backlog", "/reports/salary-progression"})
public class ReportServlet extends HttpServlet {

    private static final String BACKEND_URL = System.getenv().getOrDefault("BACKEND_URL", "http://backend:8080");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final RequestConfig LONG_TIMEOUT = RequestConfig.custom()
            .setConnectTimeout(Timeout.ofSeconds(10))
            .setResponseTimeout(Timeout.ofSeconds(120))
            .setConnectionRequestTimeout(Timeout.ofSeconds(10))
            .build();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String path = request.getServletPath();

        String endpoint;
        String attrName;
        String jspPath;

        switch (path) {
            case "/reports/payroll":
                endpoint = "/api/reports/payroll?limit=200";
                attrName = "payrollData";
                jspPath = "/jsp/payroll-report.jsp";
                break;
            case "/reports/departments":
                endpoint = "/api/reports/departments";
                attrName = "deptData";
                jspPath = "/jsp/dept-analytics.jsp";
                break;
            case "/reports/performance":
                endpoint = "/api/reports/performance";
                attrName = "performanceData";
                jspPath = "/jsp/performance-report.jsp";
                break;
            case "/reports/leave-backlog":
                endpoint = "/api/reports/leave-backlog";
                attrName = "leaveBacklogData";
                jspPath = "/jsp/leave-backlog-report.jsp";
                break;
            case "/reports/salary-progression":
                endpoint = "/api/reports/salary-progression";
                attrName = "salaryProgressionData";
                jspPath = "/jsp/salary-progression-report.jsp";
                break;
            default:
                response.sendError(HttpServletResponse.SC_NOT_FOUND);
                return;
        }

        List<Map<String, Object>> data;
        try {
            data = fetchList(endpoint);
        } catch (IOException e) {
            data = Collections.emptyList();
            request.setAttribute("error", "Unable to load report: " + e.getMessage());
        }

        request.setAttribute(attrName, data);
        request.getRequestDispatcher(jspPath).forward(request, response);
    }

    private List<Map<String, Object>> fetchList(String endpoint) throws IOException {
        try (CloseableHttpClient client = HttpClients.custom()
                .setDefaultRequestConfig(LONG_TIMEOUT)
                .build()) {
            HttpGet get = new HttpGet(BACKEND_URL + endpoint);
            return client.execute(get, resp -> {
                String body = EntityUtils.toString(resp.getEntity());
                return MAPPER.readValue(body, new TypeReference<List<Map<String, Object>>>() {});
            });
        }
    }
}
