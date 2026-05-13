<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Leave Backlog Report
    <span class="page-badge">Heavy Query — Correlated Subquery</span>
</h1>
<p style="color:#666; margin-top:-8px;">Department leave summary with confirmed pending count via correlated subquery.</p>

<c:choose>
    <c:when test="${empty leaveBacklogData}">
        <div class="card empty-state"><p>No leave backlog data available.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Department</th>
                    <th class="num">Total Employees</th>
                    <th class="num">Total Leaves</th>
                    <th class="num">Pending</th>
                    <th class="num">Avg Days</th>
                    <th class="num">Confirmed Pending</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="row" items="${leaveBacklogData}">
                    <tr>
                        <td><c:out value="${row.deptName}"/></td>
                        <td class="num"><c:out value="${row.totalEmployees}"/></td>
                        <td class="num"><c:out value="${row.totalLeaves}"/></td>
                        <td class="num"><c:out value="${row.pendingCount}"/></td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.avgLeaveDays}">—</c:when>
                                <c:otherwise><fmt:formatNumber value="${row.avgLeaveDays}" maxFractionDigits="1"/></c:otherwise>
                            </c:choose>
                        </td>
                        <td class="num"><c:out value="${row.confirmedPending}"/></td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
