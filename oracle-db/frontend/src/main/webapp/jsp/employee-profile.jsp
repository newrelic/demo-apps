<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<p><a href="/employees" style="color:#1a3a5c; text-decoration:none;">&larr; Back to Employees</a></p>

<c:choose>
    <c:when test="${empty employee or empty employee.empId}">
        <div class="card empty-state">
            <p>Employee not found.</p>
        </div>
    </c:when>
    <c:otherwise>
        <div class="card">
            <h1 style="margin-bottom:4px;">
                <c:out value="${employee.firstName}"/> <c:out value="${employee.lastName}"/>
            </h1>
            <p style="color:#666; margin-top:0; font-size:15px;">
                <c:out value="${employee.jobTitle}"/> &middot; <c:out value="${employee.deptName}"/>
            </p>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:18px; margin-top:20px;">
                <div>
                    <div class="stat-label">Employee ID</div>
                    <div style="font-size:16px; margin-top:4px;"><c:out value="${employee.empId}"/></div>
                </div>
                <div>
                    <div class="stat-label">Email</div>
                    <div style="font-size:16px; margin-top:4px;"><c:out value="${employee.email}"/></div>
                </div>
                <div>
                    <div class="stat-label">Hire Date</div>
                    <div style="font-size:16px; margin-top:4px;"><c:out value="${employee.hireDate}"/></div>
                </div>
                <div>
                    <div class="stat-label">Current Salary</div>
                    <div style="font-size:16px; margin-top:4px;">
                        <c:choose>
                            <c:when test="${empty employee.currentSalary}">—</c:when>
                            <c:otherwise>
                                <fmt:formatNumber value="${employee.currentSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                            </c:otherwise>
                        </c:choose>
                    </div>
                </div>
            </div>
        </div>

        <h2>Salary History</h2>
        <c:choose>
            <c:when test="${empty salaryHistory}">
                <div class="card empty-state"><p>No salary history available.</p></div>
            </c:when>
            <c:otherwise>
                <table>
                    <thead>
                        <tr>
                            <th>Effective Date</th>
                            <th class="num">Salary</th>
                        </tr>
                    </thead>
                    <tbody>
                        <c:forEach var="sal" items="${salaryHistory}">
                            <tr>
                                <td><c:out value="${sal.effectiveDate}"/></td>
                                <td class="num">
                                    <fmt:formatNumber value="${sal.salary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                                </td>
                            </tr>
                        </c:forEach>
                    </tbody>
                </table>
            </c:otherwise>
        </c:choose>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
