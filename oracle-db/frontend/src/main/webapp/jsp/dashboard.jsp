<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ include file="header.jspf" %>

<h1>HR Dashboard</h1>
<p style="color:#666; margin-top:-8px;">Self-service portal overview</p>

<div class="stat-grid">
    <div class="stat-card">
        <div class="stat-label">Total Employees</div>
        <div class="stat-value">
            <c:out value="${stats.totalEmployees != null ? stats.totalEmployees : '—'}"/>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Total Departments</div>
        <div class="stat-value">
            <c:out value="${stats.totalDepts != null ? stats.totalDepts : '—'}"/>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Recent Hires (90d)</div>
        <div class="stat-value">
            <c:out value="${stats.recentHires != null ? stats.recentHires : '—'}"/>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Pending Leaves</div>
        <div class="stat-value">
            <c:out value="${stats.pendingLeaves != null ? stats.pendingLeaves : '—'}"/>
        </div>
    </div>
</div>

<%@ include file="footer.jspf" %>
