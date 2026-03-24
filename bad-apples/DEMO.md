# Bad Apples Orchard - Demo Guide

This document describes how to use the Bad Apples application for demonstrating observability patterns with New Relic.

## Demo Overview

Bad Apples is a Python microservices ecommerce application that contains three realistic performance anti-patterns commonly found in production code. Unlike artificial demos with hard-coded error endpoints, these issues look and behave like real bugs that developers might introduce.

### Performance Issues Demonstrated

1. **N+1 SQL Query Problem** - Query pattern that works fine in development but causes severe performance degradation in production
2. **Silent Errors** - Business logic errors that are logged but don't surface as failures in APM
3. **User Frustration Patterns** - Frontend UX issues that create rage clicks and poor Core Web Vitals scores

**Bonus:** Browser errors from failed third-party integrations (analytics tracking pixel)

---

## Load Generation

The application includes a Selenium-based load generator that creates realistic traffic patterns:

### Traffic Distribution

- **70% Browse and Order Journey**:
  1. Visit homepage (triggers N+1 query)
  2. Browse catalog
  3. Add 2-3 items to cart (random quantities: 0.5-5.0 lbs)
  4. Navigate to checkout
  5. Fill form and submit (triggers rage clicks)
  6. Order processed (~10-15% trigger stock errors)

- **30% Quick Browse Journey**:
  1. Visit homepage (triggers N+1 query)
  2. Browse catalog
  3. View 1-3 product details
  4. Exit

### Configuration

- **3 concurrent users** running continuously
- **5 second intervals** between journeys (with ±1s jitter)
- **~360-450 journeys per hour** across all users
- **~1,000-1,200 page loads per hour** (Browse and Order: 3 pages, Quick Browse: 2 pages)
- **~250-315 orders per hour** (70% of journeys complete checkout)

### Customization

Edit `.env` to adjust load generation:

```bash
SELENIUM_USERS=3              # Number of concurrent users
SELENIUM_REQUEST_INTERVAL=5   # Seconds between journeys
```

---

## Problem 1: N+1 SQL Query

### Location

`inventory-service/app.py` - `GET /api/orders/recent` endpoint

### How It Works

The endpoint fetches recent orders in two steps:
1. Query all orders (1 query)
2. For each order, query its items (N queries)

**The Problem**: With 500 orders, this results in **501 separate database queries** instead of 1 optimized JOIN query.

**Important**: This is a **deeper architectural issue**, not a slow transaction. The response time may be fast (200-500ms) because PostgreSQL is highly optimized. The issue is the **excessive number of queries**, which:
- Scales linearly with data (500 orders = 501 queries, 1000 orders = 1001 queries)
- Consumes database connections inefficiently
- Creates network overhead between application and database
- Would become a serious bottleneck under higher load or slower database conditions

### Triggering the Issue

**Option 1: Homepage Load**
```bash
# Visit homepage - loads recent orders widget
open http://localhost:5000
```

**Option 2: Direct API Call**
```bash
curl http://localhost:5001/api/orders/recent?limit=500
# or
curl http://localhost:5001/api/orders/recent?limit=1000
```

### Production vs Development

- **Development mode** (`SEED_MODE=development`):
  - 5 orders in database
  - 6 SQL queries total (1 + 5)
  - ~50ms response time
  - Issue not noticeable

- **Production mode** (`SEED_MODE=production`):
  - 1,000+ orders in database
  - 501 or 1,001 SQL queries total depending on limit (1 + 500 or 1 + 1000)
  - 200-500ms response time (PostgreSQL is fast locally)
  - **Issue visible in query count, not necessarily response time**

### New Relic Detection

**Note**: The transaction may appear fast (200-500ms), so you need to **dig deeper** to find the problem.

1. Go to **APM → bad-apples_inventory → Distributed tracing**
2. Click `app:get_recent_orders` transaction
3. **Important**: The transaction time may not look alarming - this is intentional
4. Select any transaction trace (they all show the problem)
5. Click the **Expand all** button:
   - **This is where the issue becomes obvious**
   - **Total query count**: ~501-502 individual database calls

6. **What You'll See**: New Relic will show **3 unique SQL statement types** in the spans:

   **Statement 1**: `Postgres orders select` (appears **once**):
   ```sql
   SELECT id, customer_name, customer_email, total_amount, status, created_at
   FROM orders
   ORDER BY created_at DESC
   LIMIT $?
   ```
   ✅ This query is fine - fetches 500 orders in a single call

   **Statement 2**: `Postgres select` (connection cleanup - normal asyncpg behavior):
   ```sql
   SELECT pg_advisory_unlock_all();
   CLOSE ALL;
   UNLISTEN *;
   RESET ALL;
   ```
   ✅ This is normal PostgreSQL connection pooling cleanup

   **Statement 3**: `Postgres order_items select` (appears **500 times** - ⚠️ THIS IS THE PROBLEM):
   ```sql
   SELECT oi.id, oi.variety_id, av.name as variety_name,
          oi.quantity_lbs, oi.unit_price, oi.subtotal
   FROM order_items oi
   JOIN apple_varieties av ON oi.variety_id = av.id
   WHERE oi.order_id = $?
   ```
   ⚠️ **N+1 Anti-Pattern**: This query executes 500 separate times, once for each order, with different `order_id` values (1, 2, 3, 4... 500)

7. **The Problem**: Instead of 1 optimized JOIN query to fetch all order items at once, the code makes 500 separate round-trips to the database
8. **Teaching moment**: Fast transactions can still have architectural problems!

### Expected Metrics

- **Transaction duration**: 200-500ms (may seem acceptable at first glance)
- **Database time**: 80-95% of total transaction time
- **Total query count**: **~501-502 queries** - **THIS IS THE KEY METRIC**
- **Unique statements**: 3 (but one repeats 500 times)
- **Query pattern**: Statement #3 repeats with incrementing `order_id` values (1, 2, 3, 4... 500)

**Key Insight**: The transaction might be fast enough that it doesn't trigger alerts or appear in "slow transaction" reports. This demonstrates why you need to **investigate beyond response time** and examine the actual database query patterns. A fast transaction with 501 queries is still a problem waiting to happen at scale.

**What Should Happen Instead**: The 500 repetitive queries should be replaced with a single optimized query:
```sql
SELECT o.*, oi.*, av.name
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN apple_varieties av ON oi.variety_id = av.id
WHERE o.id IN (list of 500 order IDs)
```
This would reduce 501 queries down to just 2 queries total.

---

## Problem 2: Silent Errors (Insufficient Stock)

### Location

`order-service/app.py` - Lines 65-76 in the `POST /api/orders` endpoint

### How It Works

**The Problem**: The order processing code validates stock availability but doesn't act on the validation result. Here's the actual code:

```python
# Check current stock levels
current_stock = get_current_stock(variety_id)

# Log stock issues for monitoring
# TODO: Should we block orders when stock is insufficient?
# For now, logging for ops team to track oversell situations
if current_stock < quantity_lbs:
    logger.error(
        f"Error occurred: Insufficient stock for variety {variety_id}. "
        f"Requested: {quantity_lbs}lbs, Available: {current_stock}lbs. "
        f"Order will proceed anyway (overselling inventory)."
    )

# Calculate price (fetch from inventory service)
# ... continues to process order regardless of stock ...
```

**What's Wrong**:
1. ✅ Code correctly checks if `current_stock < quantity_lbs`
2. ✅ Code logs an error message with `logger.error()`
3. ❌ **Code does NOT raise an exception or return an error response**
4. ❌ Order processing continues normally
5. ❌ Returns HTTP 200 (success) to the client

This creates a dangerous situation where:
- APM shows **0% error rate** (all HTTP 200 responses)
- Logs are full of **"Error occurred"** messages
- Business logic failures are hidden from monitoring
- Inventory gets oversold without triggering alerts

### Triggering the Issue

Orders are automatically triggered by Selenium. Pink Lady apple variety has only **3 lbs** in stock, while orders request 0.5-5.0 lbs randomly. This creates a ~10-15% error rate naturally.

### New Relic Detection

**Note**: This demonstrates the critical importance of **Logs in Context** - correlating log messages with APM transactions.

**Step 1: Check APM Error Rate**
1. Go to **APM → bad-apples_orders → Errors (errors inbox)**
2. Observe: **0% error rate** ✅
3. All transactions show as successful (HTTP 200/201 responses)
4. **First impression**: Everything looks healthy!

**Step 2: Check Application Logs** (This is where the problem reveals itself)
1. Go to **Logs** (main navigation)
2. Filter by: `"Error occurred"` (exact phrase in quotes)
3. **What You'll See**:
   - **30 minute window (default)**: ~12-23 log entries with ERROR level
   - **1 hour window**: ~25-47 log entries
   - **Longer periods**: Hundreds or thousands of error logs accumulate
4. **Notice**: Logs show "Error occurred: Insufficient stock..." messages

**Step 3: Correlate Logs to Transactions** (The "Aha!" moment)
1. Click on any log entry with "Error occurred"
2. Examine the log details:
   ```
   Error occurred: Insufficient stock for variety 5.
   Requested: 4.2lbs, Available: 3lbs.
   Order will proceed anyway (overselling inventory).
   ```
3. Click the **Explore** button next to the associated distributed trace
   - Trace name will be something like: `POST flask-frontend:5000/api/checkout`
4. **Key Observation**:
   - The distributed trace shows **successful transaction** (green, no errors)
   - Response code: **200 OK**
   - Transaction completed normally
   - **But the log shows a critical business logic error!**

**Step 4: Understand the Disconnect**
1. **APM perspective**: Transaction succeeded, customer got order confirmation
2. **Logs perspective**: Order was processed despite insufficient stock
3. **Business impact**: Inventory oversold, can't fulfill order
4. **Monitoring blind spot**: Traditional APM error tracking completely misses this!

### Expected Metrics

- **APM Error Rate**: **0%** (all transactions successful)
- **APM Success Rate**: **100%** (all HTTP 200/201 responses)
- **Log Error Count**: **~10-15% of orders** (~25-47 error logs per hour)
- **Log Level**: ERROR (but not surfacing as transaction errors)
- **Business Impact**: Inventory oversold, customer fulfillment issues, operational blind spot

**The Discrepancy**:
- Traditional monitoring: ✅ "All systems operational"
- Reality: ⚠️ 10-15% of orders have business logic failures

### Example Log Message

```
Error occurred: Insufficient stock for variety 5.
Requested: 4.2lbs, Available: 3lbs.
Order will proceed anyway (overselling inventory).
```

### What Should Happen Instead

The code **should raise an exception** or **return an error response** when stock is insufficient:

**Option 1: Raise an exception (recommended)**
```python
# Check current stock levels
current_stock = get_current_stock(variety_id)

if current_stock < quantity_lbs:
    logger.error(
        f"Insufficient stock for variety {variety_id}. "
        f"Requested: {quantity_lbs}lbs, Available: {current_stock}lbs."
    )
    # IMPORTANT: Raise exception to fail the transaction
    raise ValueError(
        f"Insufficient stock for variety {variety_id}. "
        f"Only {current_stock}lbs available, but {quantity_lbs}lbs requested."
    )

# Continue with order processing...
```

**Option 2: Return error response**
```python
if current_stock < quantity_lbs:
    logger.error(f"Insufficient stock for variety {variety_id}")
    return jsonify({
        'error': 'Insufficient stock',
        'variety_id': variety_id,
        'requested': quantity_lbs,
        'available': current_stock
    }), 400  # HTTP 400 Bad Request
```

**Result of Fix**:
- APM error rate would show **10-15%** (matching reality)
- Transactions would properly fail with HTTP 400/500
- Monitoring alerts would trigger on high error rates
- Customers would see "Out of Stock" message instead of false confirmation

### Key Insight

This problem demonstrates a common anti-pattern: **logging an error without handling it**. The developer:
1. ✅ Identified the problem (insufficient stock)
2. ✅ Logged it for debugging
3. ❌ **Forgot to actually fail the transaction**

The TODO comment `"Should we block orders when stock is insufficient?"` suggests this was meant to be temporary, but became permanent. This is why **Logs in Context** is critical - it reveals business logic errors that don't surface as HTTP errors, helping you find issues that traditional APM would completely miss.

---

## Problem 3: User Frustration (Rage Clicks)

### Location

`flask-frontend/templates/checkout.html` - Lines 77-100 in the checkout form submit handler

### How It Works

**The Problem**: The checkout button has multiple UX anti-patterns that create user frustration. Here's the actual code:

```javascript
document.getElementById('checkout-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-order');

    // TODO: Add loading spinner here
    // TODO: Disable button to prevent double-submission

    const formData = { /* collect form data */ };

    // Update New Relic user tracking with email address
    if (typeof newrelic !== 'undefined' && formData.customer_email) {
        sessionStorage.setItem('nr_user_id', formData.customer_email);
        newrelic.setUserId(formData.customer_email);
    }

    // Add delay to show processing state
    // TODO: Remove this once backend is optimized
    await new Promise(resolve => setTimeout(resolve, 4000));

    try {
        const response = await fetch('/api/checkout', { /* submit order */ });
        // Handle response...
    }
});
```

**What's Wrong**:
1. ❌ **Button NOT disabled** - `submitBtn.disabled = true;` is missing
2. ❌ **No visual feedback** - No loading spinner, no "Processing..." text
3. ❌ **4-second artificial delay** - Before the API call even starts
4. ❌ **No button state changes** - Button looks clickable the entire time

**User Experience**:
1. User fills form and clicks "Place Order"
2. Button accepts the click but provides ZERO feedback
3. User waits 1 second... nothing happens
4. User thinks their click didn't register
5. **User frantically clicks 10-15 more times** (rage clicks)
6. After 4 seconds, order finally processes
7. All those extra clicks were recorded by New Relic Browser monitoring

### Triggering the Issue

**Automatic** (Recommended): Selenium generates rage clicks on every checkout
- **11-16 clicks per checkout** (1 initial + 10-15 rage clicks)
- **Timing**: All clicks happen within 2-3 seconds
- **Frequency**: ~250-315 checkouts per hour = continuous rage click data

**Manual Testing**:
1. Add items to cart at http://localhost:5000/catalog
2. Proceed to http://localhost:5000/checkout
3. Fill form and click "Place Order"
4. **Notice**: No feedback, button stays enabled, no spinner
5. Click button 10+ more times rapidly (simulate frustrated user)
6. Wait 4+ seconds for order to finally process
7. Check New Relic Browser for your session to see the rage clicks recorded

### New Relic Detection

**Note**: This demonstrates how **New Relic Browser monitoring** captures frontend UX issues that backend APM cannot see.

**Step 1: Find Frustrated Sessions**
1. Go to **Browser → bad-apples_frontend → User impact**
2. Look at the **Top affected pages** section
3. **What You'll See**: `/checkout` interactions flagged with rage clicks
4. You can change the **Metric** dropdown at the top to **Dead clicks** as well to show a similar experience based on the button having no action.

**Step 2: Examine User Actions** (The rage click evidence)
1. Click on the **Session replays** counter to open a pre-filtered selection of replays
2. Select any session (click the `/` in the **Starting URL** column)
3. **Key Observations**:
   - Multiple click events on `button#submit-order.btn.btn-primary` element
   - **11-16 clicks within a 2-3 second window**
   - Timestamp pattern shows rapid successive clicks:
     ```
     0.0s: Click button#submit-order.btn.btn-primary
     0.2s: Click button#submit-order.btn.btn-primary
     0.4s: Click button#submit-order.btn.btn-primary
     0.6s: Click button#submit-order.btn.btn-primary
     ...continues...
     2.5s: Click button#submit-order.btn.btn-primary
     ```
   - New Relic automatically flags this as **rage click behavior**

**Step 3: Check Core Web Vitals** (Interesting observation)
1. In the same session trace, view **Core Web Vitals** section
2. **INP (Interaction to Next Paint)**: Typically **~20ms** (good - <200ms)
   - **Important Note**: INP measures time from user interaction to visual update
   - The click handler executes immediately (good INP score)
   - **But the actual processing takes 4+ seconds with no feedback**
   - This shows that **good Core Web Vitals don't guarantee good UX**
   - INP Reference: Good (<200ms), Needs Improvement (200-500ms), Poor (>500ms)
3. **Key Insight**: Traditional performance metrics look fine, but rage clicks reveal the real problem
4. **CLS (Cumulative Layout Shift)**: Should be low/good
5. **LCP (Largest Contentful Paint)**: Should be acceptable

**Step 4: Analyze Page Frustration Metrics**
1. Go to **Browser → bad-apples_frontend → Page Views**
2. Filter by **Frustration Level**: Select "Frustrated"
3. **What You'll See**:
   - Checkout page (`/checkout`) appears frequently
   - ~70% of checkout sessions marked as frustrated
   - High rage click count per session

**Step 5: Session Replay** (Visual confirmation)
1. If Session Replay is enabled, click **Play Session**
2. **Watch**:
   - User fills out form
   - User clicks "Place Order" button
   - Button doesn't change appearance (no spinner, no disabled state)
   - User clicks 10+ more times rapidly
   - After 4+ seconds, page finally transitions
3. **Visual Evidence**: You can literally see the user frustration

### User Tracking

Sessions are tracked with `newrelic.setUserId()` (implemented in the code above):

- **Anonymous**: `session-1737584123-abc7def` (first page load)
- **Identified**: `customer123@example.com` (after checkout)

Filter sessions by user ID in New Relic to see complete user journeys including rage clicks.

### Expected Metrics

- **Rage Clicks per Checkout**: **11-16 clicks** (1 initial + 10-15 rage clicks)
- **Click Timing**: All within **2-3 seconds**
- **INP Score**: **~20ms** (good - <200ms) ⚠️ **This is misleading!**
- **Actual User Wait Time**: **4+ seconds** with zero feedback
- **Frustrated Sessions**: **~70% of checkout pages**
- **Checkouts per Hour**: ~250-315 (all creating rage clicks)

**The Numbers**:
- At 250 checkouts/hour × 13 average clicks = **~3,250 total button clicks/hour**
- At 250 checkouts/hour × 12 rage clicks = **~3,000 rage clicks/hour**
- This creates a massive dataset in New Relic showing clear user frustration

**Critical Insight**:
The INP score is technically "good" (20ms) because the JavaScript click handler responds immediately. However, this is a **false positive** - the INP metric doesn't capture the 4-second processing delay with no user feedback. This demonstrates why **rage click detection is essential** - it reveals UX problems that traditional performance metrics completely miss. You can have perfect Core Web Vitals and still have a terrible user experience!

### What Should Happen Instead

The checkout form **should provide immediate feedback** and **disable the button** during processing:

**Complete Fix (all three issues addressed)**:
```javascript
document.getElementById('checkout-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-order');
    const originalText = submitBtn.textContent;

    // IMPORTANT: Disable button immediately to prevent double-submission
    submitBtn.disabled = true;

    // IMPORTANT: Show visual feedback with spinner and loading text
    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
    submitBtn.classList.add('loading');

    const formData = { /* collect form data */ };

    // Update New Relic user tracking
    if (typeof newrelic !== 'undefined' && formData.customer_email) {
        sessionStorage.setItem('nr_user_id', formData.customer_email);
        newrelic.setUserId(formData.customer_email);
    }

    // REMOVED: No artificial delay needed with proper feedback
    // await new Promise(resolve => setTimeout(resolve, 4000));

    try {
        const response = await fetch('/api/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            showNotification('Order placed successfully!', 'success');
            // Keep button disabled during redirect
            setTimeout(() => {
                window.location.href = '/order/' + result.order_id;
            }, 1500);
        } else {
            // Re-enable button on error
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
            submitBtn.classList.remove('loading');
            showNotification(result.error || 'Failed to place order', 'error');
        }
    } catch (error) {
        // Re-enable button on error
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
        submitBtn.classList.remove('loading');
        showNotification('Error placing order', 'error');
    }
});
```

**Result of Fix**:
- ✅ Button disabled immediately (can't be clicked multiple times)
- ✅ Visual feedback ("Processing..." text + spinner)
- ✅ No artificial delay (processes immediately)
- ✅ Button re-enabled only if error occurs
- ✅ **Rage clicks reduced from 11-16 to 1**
- ✅ **Frustrated sessions reduced from 70% to <5%**
- ✅ **INP score stays good** (~20ms unchanged, but now reflects actual UX)
- ✅ **Console logs provide debugging context** for session replay analysis

### Key Insight

This problem demonstrates a critical frontend anti-pattern: **no user feedback during async operations**. The developer:
1. ✅ Added a TODO comment: "Add loading spinner here"
2. ✅ Added a TODO comment: "Disable button to prevent double-submission"
3. ❌ **Never implemented the TODOs**
4. ❌ Added a 4-second artificial delay (making the problem worse!)
5. ❌ Left the unfinished code in production

**Why This Matters**:
- **Backend APM cannot see this problem** - all transactions succeed (HTTP 200)
- **Traditional performance metrics look fine** - INP is good (20ms), no errors
- **Only Browser monitoring with rage click detection reveals the UX issue**
- **Console logs in session replays** show the full story of user frustration
- **Business impact**: Users think the site is broken, may abandon checkout, poor reviews
- **The TODO comments suggest this was temporary** but became permanent

This is why **New Relic Browser monitoring with Session Replay** is essential - it captures real user frustration that would never appear in backend logs or APM metrics. Traditional monitoring would show "100% success rate" while users are actually having a terrible experience.

---

## Browser Errors (Bonus)

### Location

`flask-frontend/templates/base.html` - Runs on every page load

### How It Works

The application attempts to load an analytics tracking pixel that doesn't exist, creating a non-critical error reported to New Relic Browser monitoring.

- **Frequency**: 6 errors per hour (every 10 minutes)
- **Error Rate**: ~0.5% of page loads (~6 errors out of ~1,000-1,200 page loads/hour)
- **Type**: Failed tracking pixel load
- **Impact**: None (non-critical, doesn't affect functionality)

### Manual Testing

Force an error immediately:

```bash
open http://localhost:5000/?trigger_error=true
```

Open browser console (F12) to see confirmation:
```
[DEBUG] Analytics pixel load failed - reported to monitoring
```

### New Relic Detection

1. Go to **Browser → bad-apples_frontend → Errors**
2. See **"Failed to load analytics tracking pixel"** error
3. Click error to view details:
   - **Custom Attributes**:
     - `errorType`: "non-critical"
     - `component`: "analytics"
     - `reason`: "third-party service unavailable"
     - `manuallyTriggered`: "yes" or "no"
   - **Stack Trace**: Shows image load failure
   - **User ID**: Associated session or email

### Why This Is Useful

- Demonstrates `newrelic.noticeError()` for custom error tracking
- Shows how to add custom attributes to errors
- Realistic scenario: third-party integrations often fail
- Non-critical errors need monitoring but shouldn't page ops

---

## Seed Modes

### Development Mode (Default)

```bash
SEED_MODE=development
```

- **5 apple varieties**
- **3 sample orders**
- **Fast queries** - N+1 problem not noticeable
- **Best for**: Quick testing, development

### Production Mode (Recommended for Demo)

```bash
SEED_MODE=production
```

- **8 apple varieties**
- **1000+ orders**
- **Slow queries** - N+1 problem very noticeable
- **Best for**: Performance demonstrations, realistic load

### Switching Modes

```bash
# Stop and remove data
docker-compose down -v

# Update .env
echo "SEED_MODE=production" >> .env

# Start with new data
docker-compose up -d
```

---

## New Relic Setup

### Required Configuration

1. **License Key**: Set in `.env`
   ```bash
   NEW_RELIC_LICENSE_KEY=your_key_here
   ```

2. **Application Names**: Default names in `.env`
   ```bash
   NEW_RELIC_APP_NAME_FRONTEND=bad-apples_frontend
   NEW_RELIC_APP_NAME_INVENTORY=bad-apples_inventory
   NEW_RELIC_APP_NAME_ORDERS=bad-apples_orders
   ```

### What Gets Instrumented

- **APM**: All three Python services
- **Browser Monitoring**: Frontend (auto-instrumented)
- **Distributed Tracing**: W3C trace context across services
- **Logs in Context**: All application logs forwarded
- **Custom Attributes**: User IDs, error metadata

### Data Latency

- **APM Data**: 1-2 minutes
- **Browser Data**: 1-2 minutes
- **Logs**: 30-60 seconds
- **Traces**: 2-3 minutes for full distributed traces

---

## Demo Script

### 5-Minute Demo Flow

1. **Show the App** (1 min)
   - Open http://localhost:5000
   - Browse catalog, add items to cart
   - "This is our apple orchard ecommerce site"

2. **Problem 1: N+1 Query** (2 min)
   - Open APM → bad-apples_inventory
   - Show slow transaction on `/api/orders/recent`
   - Click into transaction trace
   - Show 1,001 database queries
   - "Classic N+1 problem - works in dev, fails in production"

3. **Problem 2: Silent Errors** (1 min)
   - Open APM → bad-apples_orders → Show 0% error rate
   - Open Logs → Filter "Error occurred"
   - Show Logs in Context linking to successful transactions
   - "Business logic errors hidden from APM"

4. **Problem 3: Rage Clicks** (1 min)
   - Open Browser → Session Traces
   - Filter for frustrated sessions on checkout
   - Show session replay with multiple button clicks
   - "User frustration from poor UX - no visual feedback"

### Advanced Demo Topics

- **Distributed Tracing**: Show trace spanning all three services
- **User Tracking**: Filter by user ID to see full journey
- **Custom Error Attributes**: Browser errors with metadata
- **Logs Correlation**: How logs link to traces

---

## Tips for Effective Demos

1. **Use Production Mode**: Much more dramatic performance differences
2. **Let It Run**: Give Selenium 10-15 minutes to generate interesting data
3. **Pick Good Examples**: Find sessions with clear rage clicks, slow traces
4. **Tell the Story**: "Developer added logging, forgot to return error"
5. **Show Business Impact**: Oversold inventory, frustrated customers
6. **Demonstrate Solutions**: How to fix each issue

---

## Troubleshooting Demos

### "I don't see any data in New Relic"

- Wait 2-3 minutes for initial data
- Check logs: `docker-compose logs flask-frontend | grep -i "new relic"`
- Verify license key is correct in `.env`

### "N+1 problem doesn't look bad"

- Ensure `SEED_MODE=production` in `.env`
- Rebuild: `docker-compose down -v && docker-compose up -d`
- Wait for 1000 orders to seed

### "No rage clicks appearing"

- Wait 10-15 minutes for Selenium to complete several checkouts
- Manually test by rapid-clicking checkout button
- Check Session Traces filters - try removing filters

### "Browser errors not appearing"

- Force one manually: http://localhost:5000/?trigger_error=true
- Check browser console for confirmation
- Errors trigger every 10 minutes (6 per hour) - be patient or use manual trigger

---

## Learning Objectives

After using this demo, you should understand:

1. **N+1 Queries**: How lazy loading creates exponential database calls
2. **Silent Failures**: Why logging without error handling is dangerous
3. **User Frustration Patterns**: How rage clicks, high INP, and poor UX affect customers
4. **Distributed Tracing**: Following requests across microservices
5. **Logs in Context**: Correlating log errors with APM transactions
6. **Browser Monitoring**: Tracking frontend performance, Core Web Vitals, and session replay
7. **Custom Instrumentation**: Using `newrelic.noticeError()` and `setUserId()`

---

## Further Exploration

- Modify Selenium to create different traffic patterns
- Experiment with different load levels (`SELENIUM_USERS`)
- Try fixing the issues and observe metric improvements
- Add your own instrumentation using the New Relic API
- Use NRQL to create custom dashboards for these patterns
