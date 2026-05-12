<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Payroll Report
    <span class="page-badge">Heavy Query — May Take 10–30s</span>
</h1>
<p style="color:#666; margin-top:-8px;">Detailed payroll view with department benchmarks and previous salary comparison.</p>

<c:choose>
    <c:when test="${empty payrollData}">
        <div class="card empty-state"><p>No payroll data available.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Job Title</th>
                    <th class="num">Current Salary</th>
                    <th class="num">Dept Avg</th>
                    <th class="num">Dept Headcount</th>
                    <th class="num">Previous Salary</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="row" items="${payrollData}">
                    <tr>
                        <td><c:out value="${row.empId}"/></td>
                        <td><c:out value="${row.fullName}"/></td>
                        <td><c:out value="${row.deptName}"/></td>
                        <td><c:out value="${row.jobTitle}"/></td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.currentSalary}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.currentSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                                </c:otherwise>
                            </c:choose>
                        </td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.deptAvgSalary}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.deptAvgSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                                </c:otherwise>
                            </c:choose>
                        </td>
                        <td class="num"><c:out value="${row.deptHeadcount}"/></td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.previousSalary}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.previousSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                                </c:otherwise>
                            </c:choose>
                        </td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
