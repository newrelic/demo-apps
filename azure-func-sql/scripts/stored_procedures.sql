-- this script runs the changes necessary to enable full NR instrumentation
-- and turns on the stored procs the app needs to run
-- in a production environment you would also create a 'newrelic' user
-- for least-privileged database access

USE master;
GO

-- Enable Query Store on the AdventureWorks database
ALTER DATABASE AdventureWorks SET QUERY_STORE = ON (QUERY_CAPTURE_MODE = ALL, DATA_FLUSH_INTERVAL_SECONDS = 900);
GO
PRINT 'Enabled Query Store on AdventureWorks database.';

USE AdventureWorks;
GO
PRINT 'Changed database context to AdventureWorks.';

-- =================================================================
-- 1. Normal Query (Fast & Efficient)
-- Scenario: A user looks up recent orders for a specific customer.
-- =================================================================
IF OBJECT_ID('dbo.GetRecentCustomerOrders', 'P') IS NOT NULL
    DROP PROCEDURE dbo.GetRecentCustomerOrders;
GO

CREATE PROCEDURE dbo.GetRecentCustomerOrders
    @CustomerID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP 10
           h.OrderDate,
           h.SalesOrderNumber,
           d.OrderQty,
           d.UnitPrice,
           p.Name AS ProductName
    FROM SalesLT.SalesOrderHeader h
    JOIN SalesLT.SalesOrderDetail d ON h.SalesOrderID = d.SalesOrderID
    JOIN SalesLT.Product p ON d.ProductID = p.ProductID
    WHERE h.CustomerID = @CustomerID
    ORDER BY h.OrderDate DESC;
END;
GO
PRINT 'Created GetRecentCustomerOrders stored procedure.';

-- =================================================================
-- 2. Query with Waits (Simulated Slowdown)
-- Scenario: A manager requests a summary report that simulates a
-- complex calculation by introducing a predictable delay.
-- =================================================================
IF OBJECT_ID('dbo.GenerateSlowSummaryReport', 'P') IS NOT NULL
    DROP PROCEDURE dbo.GenerateSlowSummaryReport;
GO

CREATE PROCEDURE dbo.GenerateSlowSummaryReport
AS
BEGIN
    SET NOCOUNT ON;
    -- Introduce an artificial 5-second delay
    WAITFOR DELAY '00:00:05';

    SELECT pc.Name AS Category,
           p.Name AS Product,
           SUM(d.OrderQty) AS TotalSold
    FROM SalesLT.Product p
    JOIN SalesLT.ProductDescription ps ON p.ProductID = ps.ProductDescriptionID
    JOIN SalesLT.ProductCategory pc ON p.ProductCategoryID = pc.ProductCategoryID
    JOIN SalesLT.SalesOrderDetail d ON p.ProductID = d.ProductID
    GROUP BY pc.Name, p.Name
    ORDER BY pc.Name, TotalSold DESC
END;
GO
PRINT 'Created GenerateSlowSummaryReport stored procedure.';

-- =================================================================
-- 3. Query with Problems (Missing Index)
-- Scenario: A user searches for a person by their last name, a
-- common operation that will be slow without an index.
-- =================================================================

-- First, drop an existing non-clustered index to ensure the query is slow.
-- This simulates a common real-world performance issue.
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Person_LastName_FirstName_MiddleName' AND object_id = OBJECT_ID('Person.Person'))
BEGIN
    DROP INDEX IX_Person_LastName_FirstName_MiddleName ON Person.Person;
    PRINT 'Dropped index on Person.LastName to simulate missing index problem.';
END
GO

IF OBJECT_ID('dbo.FindPersonByLastName', 'P') IS NOT NULL
    DROP PROCEDURE dbo.FindPersonByLastName;
GO

CREATE PROCEDURE dbo.FindPersonByLastName
    @LastName NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT FirstName,
           LastName,
           MiddleName,
           Suffix,
           EmailPromotion
    FROM Person.Person
    WHERE LastName = @LastName;
END;
GO
PRINT 'Created FindPersonByLastName stored procedure.';

-- =================================================================
-- 4. Queries for Blocking Scenario
-- Scenario: Simulate resource contention where one process holds
-- a lock on a product's inventory, blocking another process.
-- !! THIS IS NOT IN USE AT THIS TIME !!
-- =================================================================

-- Procedure to start a transaction and update inventory without committing
IF OBJECT_ID('dbo.UpdateProductInventory', 'P') IS NOT NULL
    DROP PROCEDURE dbo.UpdateProductInventory;
GO
CREATE PROCEDURE dbo.UpdateProductInventory
    @ProductID INT
AS
BEGIN
    -- NOTE: This transaction is intentionally left open to create a block.
    -- The application code is responsible for committing or rolling it back.
    SET NOCOUNT ON;
    UPDATE Production.ProductInventory
    SET Quantity = Quantity - 1
    WHERE ProductID = @ProductID;

    -- Return the current quantity to confirm the update happened
    SELECT Quantity
    FROM Production.ProductInventory
    WHERE ProductID = @ProductID;
END;
GO
PRINT 'Created UpdateProductInventory stored procedure.';

-- Procedure to read the inventory (this will be the "victim" of the block)
IF OBJECT_ID('dbo.GetProductInventory', 'P') IS NOT NULL
    DROP PROCEDURE dbo.GetProductInventory;
GO
CREATE PROCEDURE dbo.GetProductInventory
    @ProductID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT p.Name,
           pi.Quantity
    FROM Production.Product p
    JOIN Production.ProductInventory pi ON p.ProductID = pi.ProductID
    WHERE p.ProductID = @ProductID;
END;
GO
PRINT 'Created GetProductInventory stored procedure.';
