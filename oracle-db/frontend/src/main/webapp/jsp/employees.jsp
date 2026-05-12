<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
<%@ include file="header.jspf" %>

<h1>Employee Directory</h1>

<form method="get" action="/employees" class="search-row">
    <input type="text" id="search-input" name="search"
           data-testid="employee-search"
           placeholder="Search by name or email..."
           value="<c:out value='${search}'/>" />
    <button type="submit" id="search-btn">Search</button>
</form>

<c:choose>
    <c:when test="${empty employees}">
        <div class="card empty-state">
            <p>No employees found<c:if test="${not empty search}"> for "<c:out value='${search}'/>"</c:if>.</p>
        </div>
    </c:when>
    <c:otherwise>
        <table>
            <thead>
                <tr>
                    <th>Employee ID</th>
                    <th>Name</th>
                    <th>Department</th>
                    <th>Job Title</th>
                    <th>Email</th>
                    <th>Hire Date</th>
                </tr>
            </thead>
            <tbody>
                <c:forEach var="emp" items="${employees}">
                    <tr data-testid="employee-row">
                        <td><c:out value="${emp.empId}"/></td>
                        <td>
                            <a class="emp-link" data-testid="employee-link"
                               href="/employees/<c:out value='${emp.empId}'/>">
                                <c:out value="${emp.fullName}"/>
                            </a>
                        </td>
                        <td><c:out value="${emp.deptName}"/></td>
                        <td><c:out value="${emp.jobTitle}"/></td>
                        <td><c:out value="${emp.email}"/></td>
                        <td><c:out value="${emp.hireDate}"/></td>
                    </tr>
                </c:forEach>
            </tbody>
        </table>
    </c:otherwise>
</c:choose>

<%@ include file="footer.jspf" %>
