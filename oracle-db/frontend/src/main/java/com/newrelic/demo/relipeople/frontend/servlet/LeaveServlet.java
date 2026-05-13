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
import java.util.List;
import java.util.Map;

@WebServlet("/leaves")
public class LeaveServlet extends HttpServlet {

    private static final String BACKEND_URL = System.getenv().getOrDefault("BACKEND_URL", "http://backend:8080");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String status = request.getParameter("status");
        String page = request.getParameter("page");
        if (status == null) status = "";
        if (page == null || page.isEmpty()) page = "0";

        String endpoint = "/api/leaves?status=" +
                URLEncoder.encode(status, StandardCharsets.UTF_8) +
                "&page=" + URLEncoder.encode(page, StandardCharsets.UTF_8) +
                "&size=50";

        List<Map<String, Object>> leaves;
        try {
            leaves = fetchList(endpoint);
        } catch (IOException e) {
            leaves = Collections.emptyList();
            request.setAttribute("error", "Unable to load leave requests: " + e.getMessage());
        }

        request.setAttribute("leaves", leaves);
        request.setAttribute("statusFilter", status);
        request.getRequestDispatcher("/jsp/leaves.jsp").forward(request, response);
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
}
