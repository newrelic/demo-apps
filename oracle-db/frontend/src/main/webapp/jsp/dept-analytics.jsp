<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Department Analytics</h1>
<p style="color:#666; margin-top:-8px;">Headcount, compensation, and total payroll by department (with company-wide rollup).</p>

<c:choose>
    <c:when test="${empty deptData}">
        <div class="card empty-state"><p>No department data available.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Department</th>
                    <th>City</th>
                    <th>State</th>
                    <th class="num">Headcount</th>
                    <th class="num">Avg Salary</th>
                    <th class="num">Total Payroll</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="row" items="${deptData}">
                    <c:set var="isRollup" value="${row.deptName == 'ALL DEPARTMENTS'}"/>
                    <tr<c:if test="${isRollup}"> class="rollup-row"</c:if>>
                        <td><c:out value="${row.deptName}"/></td>
                        <td><c:out value="${empty row.city ? '—' : row.city}"/></td>
                        <td><c:out value="${empty row.state ? '—' : row.state}"/></td>
                        <td class="num"><c:out value="${row.headcount}"/></td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.avgCurrentSalary}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.avgCurrentSalary}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
                                </c:otherwise>
                            </c:choose>
                        </td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.totalPayroll}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.totalPayroll}" type="currency" currencySymbol="$" maxFractionDigits="0"/>
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
