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
import java.util.HashMap;
import java.util.Map;

@WebServlet("")
public class DashboardServlet extends HttpServlet {

    private static final String BACKEND_URL = System.getenv().getOrDefault("BACKEND_URL", "http://backend:8080");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        Map<String, Object> stats;
        try {
            stats = fetchMap("/api/dashboard/stats");
        } catch (IOException e) {
            stats = new HashMap<>();
            request.setAttribute("error", "Unable to load dashboard stats: " + e.getMessage());
        }
        request.setAttribute("stats", stats);
        request.getRequestDispatcher("/jsp/dashboard.jsp").forward(request, response);
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
