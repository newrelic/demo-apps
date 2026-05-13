<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Performance Trends</h1>
<p style="color:#666; margin-top:-8px;">Review score aggregates by year, department, and role (with rollups).</p>

<c:choose>
    <c:when test="${empty performanceData}">
        <div class="card empty-state"><p>No performance data available.</p></div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Year</th>
                    <th>Department</th>
                    <th>Role</th>
                    <th class="num">Reviews</th>
                    <th class="num">Avg Score</th>
                    <th class="num">Min</th>
                    <th class="num">Max</th>
                    <th class="num">High Performers</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="row" items="${performanceData}">
                    <c:set var="yearLabel" value="${empty row.reviewYear ? 'ALL YEARS' : row.reviewYear}"/>
                    <c:set var="deptLabel" value="${empty row.deptName ? 'ALL DEPTS' : row.deptName}"/>
                    <c:set var="jobLabel"  value="${empty row.jobTitle ? 'ALL ROLES' : row.jobTitle}"/>
                    <c:set var="isRollup"  value="${empty row.reviewYear or empty row.deptName or empty row.jobTitle}"/>
                    <tr<c:if test="${isRollup}"> class="rollup-row"</c:if>>
                        <td><c:out value="${yearLabel}"/></td>
                        <td><c:out value="${deptLabel}"/></td>
                        <td><c:out value="${jobLabel}"/></td>
                        <td class="num"><c:out value="${row.reviewCount}"/></td>
                        <td class="num">
                            <c:choose>
                                <c:when test="${empty row.avgScore}">—</c:when>
                                <c:otherwise>
                                    <fmt:formatNumber value="${row.avgScore}" maxFractionDigits="2" minFractionDigits="2"/>
                                </c:otherwise>
                            </c:choose>
                        </td>
                        <td class="num"><c:out value="${empty row.minScore ? '—' : row.minScore}"/></td>
                        <td class="num"><c:out value="${empty row.maxScore ? '—' : row.maxScore}"/></td>
                        <td class="num"><c:out value="${row.highPerformers}"/></td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
