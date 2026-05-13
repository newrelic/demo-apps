<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Leave Requests</h1>
<p style="color:#666; margin-top:-8px;">All employee leave requests across the organization.</p>

<div class="search-row" style="gap:8px;">
    <a href="/leaves" class="badge"
       style="background:#e9eef4; color:#1a3a5c; text-decoration:none;"
       data-testid="filter-all">All</a>
    <a href="/leaves?status=PENDING" class="badge badge-pending"
       style="text-decoration:none;"
       data-testid="filter-pending">Pending</a>
    <a href="/leaves?status=APPROVED" class="badge badge-approved"
       style="text-decoration:none;"
       data-testid="filter-approved">Approved</a>
    <a href="/leaves?status=DENIED" class="badge badge-rejected"
       style="text-decoration:none;"
       data-testid="filter-denied">Denied</a>
</div>

<c:choose>
    <c:when test="${empty leaves}">
        <div class="card empty-state"><p>No leave requests found.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Employee</th>
                    <th>Department</th>
                    <th>Start</th>
                    <th>End</th>
                    <th class="num">Duration (days)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="lv" items="${leaves}">
                    <c:set var="statusStr" value="${lv.status}"/>
                    <c:set var="badgeClass" value="badge-pending"/>
                    <c:if test="${statusStr == 'APPROVED'}"><c:set var="badgeClass" value="badge-approved"/></c:if>
                    <c:if test="${statusStr == 'DENIED'}"><c:set var="badgeClass" value="badge-rejected"/></c:if>
                    <tr>
                        <td><c:out value="${lv.requestId}"/></td>
                        <td><c:out value="${lv.empName}"/></td>
                        <td><c:out value="${lv.deptName}"/></td>
                        <td><c:out value="${lv.startDate}"/></td>
                        <td><c:out value="${lv.endDate}"/></td>
                        <td class="num"><c:out value="${lv.durationDays}"/></td>
                        <td>
                            <span class="badge ${badgeClass}">
                                <c:out value="${statusStr}"/>
                            </span>
                        </td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
