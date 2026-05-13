<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Salary Progression Report
    <span class="page-badge">Heavy Query — Full Table Scan</span>
</h1>
<p style="color:#666; margin-top:-8px;">Top 500 employees by salary growth — requires full scan of all 200K salary records.</p>

<c:choose>
    <c:when test="${empty salaryProgressionData}">
        <div class="card empty-state"><p>No salary progression data available.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Employee</th>
                    <th>Department</th>
                    <th>Job Title</th>
                    <th class="num">Salary Changes</th>
                    <th class="num">Starting Salary</th>
                    <th class="num">Current Salary</th>
                    <th class="num">Total Growth</th>
                    <th class="num">Growth %</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="row" items="${salaryProgressionData}">
                    <tr>
                        <td><c:out value="${row.employeeName}"/></td>
                        <td><c:out value="${row.deptName}"/></td>
                        <td><c:out value="${row.jobTitle}"/></td>
                        <td class="num"><c:out value="${row.salaryChanges}"/></td>
                        <td class="num">
                            <fmt:formatNumber value="${row.startingSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                        </td>
                        <td class="num">
                            <fmt:formatNumber value="${row.currentSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                        </td>
                        <td class="num">
                            <fmt:formatNumber value="${row.totalGrowth}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                        </td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.growthPct}">—</c:when>
                                <c:otherwise><fmt:formatNumber value="${row.growthPct}" maxFractionDigits="1"/>%</c:otherwise>
                            </c:choose>
                        </td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
